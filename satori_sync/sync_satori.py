#!/usr/bin/env python3
"""新規状況表v2.0 の顧客データを SATORI のカスタマー情報へ反映する。

入力:
  - 新規状況表v2.0_マスター をCSVでダウンロードしたもの
  - SATORI のカスタマー一覧をCSVでエクスポートしたもの

出力（--out ディレクトリ）:
  - satori_import_配信拒否.csv   : 送付禁止フラグが付いた顧客の 配信許可 を「拒否」にするインポート用CSV
  - satori_import_現在の状態.csv : 未決・元在・在籍 を 現在の状態 に反映するインポート用CSV
  - satori_import_タグ.csv       : 新たに未決・元在になった最近の問合せ者に付けるタグ
  - satori_import_再入会_在籍.csv : 再入会（再入会にチェック・入会日あり）の人の 現在の状態 を「在籍」にする一括登録用CSV
  - satori_import_一括登録.csv   : 上の3つを1ファイルにまとめたもの（SATORI管理画面の一括登録用・Shift_JIS）
  - 変更レポート.csv             : 何をどう変えるかの一覧（確認用）
  - SATORI未登録_送付禁止.csv    : 送付禁止だがSATORIにメールアドレスが見つからなかった顧客

SATORI側に既に存在するカスタマー（メールアドレス一致）だけを対象にし、
配信許可は「拒否」への変更のみ行う（拒否→許可には戻さない）。

--apply を付けると、上記の変更を SATORI のカスタマーバルクAPI（upsert）で直接反映する。
APIキーは環境変数 SATORI_USER_KEY / SATORI_USER_SECRET / SATORI_COMPANY_KEY / SATORI_COMPANY_SECRET で渡す。
"""

import argparse
import collections
import csv
import datetime
import json
import os
import re
import sys
import unicodedata

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
FULL_DATE_RE = re.compile(r"(\d{4})[-/.年](\d{1,2})[-/.月](\d{1,2})")
MONTH_DAY_RE = re.compile(r"(?<![\d/])(\d{1,2})/(\d{1,2})(?![\d/])")
TRUTHY = {"true", "1", "yes", "y", "on", "はい", "済", "○", "〇", "◯", "✓", "✔", "☑", "レ"}
INPUT_ENCODINGS = ("utf-8-sig", "cp932")
REJOINED = "再入会（再入会にチェック・入会日あり）"
# 年なし日付（MM/DD）が前の行より何日以上「進んで」いたら年をまたいだとみなすか（行を遡りながら判定）
YEAR_WRAP_DAYS = 120


def normalize_text(value):
    return unicodedata.normalize("NFKC", value or "").strip()


def extract_emails(value):
    """セル内のメールアドレスを全て取り出す（全角・複数記載・大文字小文字に対応）。"""
    return [m.lower() for m in EMAIL_RE.findall(normalize_text(value))]


def is_checked(value):
    return normalize_text(value).lower() in TRUTHY


def read_csv(path, required_column):
    """CSVを読み込み、required_column を含む行をヘッダーとして dict のリストを返す。"""
    last_error = None
    for encoding in INPUT_ENCODINGS:
        try:
            with open(path, newline="", encoding=encoding) as f:
                rows = list(csv.reader(f))
            break
        except UnicodeDecodeError as e:
            last_error = e
    else:
        raise SystemExit(f"{path}: 文字コードを判別できません ({last_error})")

    for i, row in enumerate(rows):
        header = [normalize_text(c) for c in row]
        if required_column in header:
            return header, [dict(zip(header, r)) for r in rows[i + 1:] if any(c.strip() for c in r)]
    raise SystemExit(f"{path}: 列「{required_column}」が見つかりません")


# ---------------------------------------------------------------- 日付

def parse_date(value):
    """「2026-08-03 0:00:00」「2026/8/3」などから日付を取り出す。年のない日付や日付以外は None。"""
    m = FULL_DATE_RE.search(normalize_text(value))
    if not m:
        return None
    try:
        return datetime.date(*map(int, m.groups()))
    except ValueError:
        return None


def parse_month_days(value):
    """年なしの「MM/DD」を全て (月, 日) で返す（「8/3 8/10」のような複数記載にも対応）。"""
    text = normalize_text(value)
    if FULL_DATE_RE.search(text):
        return []
    return [(int(m), int(d)) for m, d in MONTH_DAY_RE.findall(text) if 1 <= int(m) <= 12 and 1 <= int(d) <= 31]


def make_date(year, month, day):
    try:
        return datetime.date(year, month, day)
    except ValueError:
        return None


def infer_inquiry_dates(rows, campus_column, inquiry_column, anchor):
    """問合日を行ごとに日付で返す。年なし（MM/DD）の問合日は年を推定する。

    旧シートから統合した行は、校舎ごとに時系列で並んだ「MM/DD」のまとまりになっている。
    まとまりの最後の行を anchor 以前で最も新しい年とし、行を遡りながら
    日付が大きく進んだ（＝年をまたいだ）ところで年を1つ減らす。
    """
    dates = [parse_date(r.get(inquiry_column, "")) for r in rows]
    blocks, current, current_campus = [], None, None
    for i, row in enumerate(rows):
        campus = normalize_text(row.get(campus_column, ""))
        if parse_month_days(row.get(inquiry_column, "")):
            if current is None or campus != current_campus:
                current = []
                blocks.append(current)
            current.append(i)
            current_campus = campus
        elif dates[i] or campus != current_campus:
            current, current_campus = None, None

    for block in blocks:
        later = None
        year = None
        for i in reversed(block):
            month, day = parse_month_days(rows[i][inquiry_column])[0]
            if year is None:
                year = anchor.year if (month, day) <= (anchor.month, anchor.day) else anchor.year - 1
            elif (month - later[0]) * 31 + (day - later[1]) > YEAR_WRAP_DAYS:
                year -= 1
            later = (month, day)
            dates[i] = make_date(year, month, day)
    return dates


def activity_dates(value, inquiry):
    """対応日付のセルを日付のリストにする。年なしは問合日以降で最も近い日付とみなす。"""
    full = parse_date(value)
    if full:
        return [full]
    if inquiry is None:
        return []
    result = []
    for month, day in parse_month_days(value):
        for year in (inquiry.year, inquiry.year + 1):
            d = make_date(year, month, day)
            if d and d >= inquiry - datetime.timedelta(days=7):
                result.append(d)
                break
    return result


def has_date(value):
    return bool(parse_date(value) or parse_month_days(value))


def previous_month_end(as_of):
    """基準日の前月末。9月に実行すると8月31日。"""
    return as_of.replace(day=1) - datetime.timedelta(days=1)


# ---------------------------------------------------------------- 状態の判定

def derive_status(row, inquiry, config, as_of):
    """1行分の顧客データから SATORI の「現在の状態」に書く値と理由を決める。決められなければ (None, "")。

    - 退会日あり                                → 元在
    - 入会日あり・再入会にチェック                → 在籍（再入会＋入会日ありのときだけ REJOINED）
    - 在籍ステータスが「元在」                    → 元在
    - 前月末までの問合せで、問合日・対応日付が
      全て前月末以前（＝前月末までに対応が止まっている） → 未決
    """
    m, values = config["master"], config["status_values"]
    if has_date(row.get(m["withdrawn_column"], "")):
        return values["former"], "退会日あり"
    enrolled_date = has_date(row.get(m["enrollment_date_column"], ""))
    rejoined = is_checked(row.get(m["rejoin_column"], "")) or has_date(row.get(m["rejoin_column"], ""))
    if rejoined and enrolled_date:
        return values["enrolled"], REJOINED
    if enrolled_date or rejoined:
        return values["enrolled"], "入会あり"
    if normalize_text(row.get(m["status_column"], "")) == values["former"]:
        return values["former"], f"在籍ステータス: {values['former']}"

    cutoff = previous_month_end(as_of)
    if inquiry is None or inquiry > cutoff:
        return None, ""
    dates = [inquiry] + [d for c in m["activity_date_columns"] for d in activity_dates(row.get(c, ""), inquiry)]
    last = max(dates)
    if last <= cutoff:
        return values["pending"], f"{cutoff:%Y/%m/%d}までに対応停止（最終 {last:%Y/%m/%d}）"
    return None, ""


def build_master_index(rows, config, as_of):
    """メールアドレスごとに 送付禁止・状態・問合日 を集約する。"""
    m = config["master"]
    priority = {s: i for i, s in enumerate(config["status_priority"])}
    anchor = datetime.date.fromisoformat(config["year_inference_anchor"]) if config.get("year_inference_anchor") else as_of
    inquiries = infer_inquiry_dates(rows, m["campus_column"], m["inquiry_date_column"], anchor)

    index = {}
    for row_no, (row, inquiry) in enumerate(zip(rows, inquiries)):
        emails = extract_emails(row.get(m["email_column"], ""))
        if not emails:
            continue
        do_not_send = is_checked(row.get(m["do_not_send_column"], ""))
        spam = is_checked(row.get(m.get("spam_column", ""), ""))
        status, reason = (None, "") if spam else derive_status(row, inquiry, config, as_of)

        for email in emails:
            entry = index.setdefault(email, {"do_not_send": False, "status": None, "rank": None,
                                             "reason": "", "inquiry": None})
            entry["do_not_send"] = entry["do_not_send"] or do_not_send
            if status is None:
                continue
            rank = (priority.get(status, len(priority)), -row_no)
            if entry["rank"] is None or rank <= entry["rank"]:
                entry.update(status=status, rank=rank, reason=reason, inquiry=inquiry)
    return index


# ---------------------------------------------------------------- SATORIとの突き合わせ

def plan_changes(master_index, satori_rows, config):
    s, tag_cfg = config["satori"], config["tag"]
    denied = s["permission_denied_value"]
    tag_since = datetime.date.fromisoformat(tag_cfg["inquiry_since"])
    permission_updates, status_updates, tag_updates, report = [], [], [], []
    matched, routes = set(), {}

    for row in satori_rows:
        emails = extract_emails(row.get(s["email_column"], ""))
        if not emails or emails[0] not in master_index:
            continue
        email = emails[0]
        entry = master_index[email]
        matched.add(email)
        original_email = normalize_text(row[s["email_column"]])
        routes[original_email] = normalize_text(row.get(s["collection_route_column"], ""))

        current_permission = normalize_text(row.get(s["permission_column"], ""))
        if entry["do_not_send"] and current_permission != denied:
            permission_updates.append({"email": original_email, "value": denied})
            report.append([original_email, "配信許可", current_permission, denied, "送付禁止フラグ"])

        current_status = normalize_text(row.get(s["status_column"], ""))
        writable = entry["status"] in config["write_statuses"] or (
            config.get("write_rejoined") and entry["reason"] == REJOINED)
        if writable and current_status != entry["status"]:
            status_updates.append({"email": original_email, "value": entry["status"], "reason": entry["reason"]})
            report.append([original_email, "現在の状態", current_status, entry["status"], entry["reason"]])

        current_tags = [normalize_text(t) for t in row.get(s["tags_column"], "").split(",")]
        if (entry["status"] in tag_cfg["statuses"] and entry["inquiry"] and entry["inquiry"] >= tag_since
                and tag_cfg["name"] not in current_tags):
            tag_updates.append({"email": original_email, "value": tag_cfg["name"]})
            report.append([original_email, "タグ追加", "", tag_cfg["name"],
                           f"{entry['inquiry']:%Y/%m/%d}問合せ・{entry['status']}"])

    unmatched_do_not_send = sorted(e for e, v in master_index.items() if v["do_not_send"] and e not in matched)
    return permission_updates, status_updates, tag_updates, report, unmatched_do_not_send, routes


def build_api_rows(permission_updates, status_updates, tag_updates, routes, config):
    """変更内容を バルクAPI 用の行（1メールアドレス1行）にまとめる。空欄の項目はSATORI側で上書きされない。

    collection_route（情報獲得経路）はAPIで必須のため、SATORIに登録済みの値をそのまま送る。
    """
    api = config["api"]
    status_col = f"custom:{api['status_custom_field']}"
    header = ["email", "collection_route", "delivery_permission", status_col, "append_tags"]
    rows = {}
    for updates, col, value in ((permission_updates, "delivery_permission", lambda u: api["delivery_permission_reject"]),
                                (status_updates, status_col, lambda u: u["value"]),
                                (tag_updates, "append_tags", lambda u: u["value"])):
        for u in updates:
            row = rows.setdefault(u["email"], {"email": u["email"],
                                               "collection_route": routes.get(u["email"]) or api["collection_route_fallback"]})
            row[col] = value(u)
    return header, list(rows.values())


def build_import_rows(permission_updates, status_updates, tag_updates, config):
    """SATORI管理画面の「一括登録」用に、変更内容を1メールアドレス1行にまとめる。

    取り込み時に「カスタマー更新: はい」「空白で上書きする: いいえ」を選ぶこと（空欄の項目は既存の値のまま、タグは追加のみ）。
    """
    status_col = f"custom:{config['api']['status_custom_field']}"
    header = ["email", "delivery_permission", status_col, "tags"]
    rows = {}
    for updates, col in ((permission_updates, "delivery_permission"), (status_updates, status_col), (tag_updates, "tags")):
        for u in updates:
            rows.setdefault(u["email"], dict.fromkeys(header, ""))
            rows[u["email"]].update({"email": u["email"], col: u["value"]})
    return header, [[r[h] for h in header] for r in rows.values()]


def write_csv(path, header, rows, encoding):
    with open(path, "w", newline="", encoding=encoding) as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--master", required=True, help="新規状況表v2.0_マスター のCSV")
    parser.add_argument("--satori", required=True, help="SATORIからエクスポートしたカスタマーCSV")
    parser.add_argument("--out", default="output", help="出力先ディレクトリ (既定: output)")
    parser.add_argument("--as-of", type=datetime.date.fromisoformat, default=datetime.date.today(),
                        help="基準日 YYYY-MM-DD（既定: 今日）。前月末までに対応が止まっている問合せを未決とする")
    parser.add_argument("--apply", action="store_true", help="SATORI APIで直接反映する（付けなければCSV出力のみ）")
    parser.add_argument("--only", action="append", choices=["permission", "status", "tag"],
                        help="--apply で送る内容を絞る（複数指定可。既定: すべて）")
    parser.add_argument("--config", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json"))
    args = parser.parse_args(argv)

    with open(args.config, encoding="utf-8") as f:
        config = json.load(f)
    s = config["satori"]

    _, master_rows = read_csv(args.master, config["master"]["email_column"])
    satori_header, satori_rows = read_csv(args.satori, s["email_column"])
    if s["status_column"] not in satori_header:
        print(f"注意: SATORIのCSVに「{s['status_column']}」が無いため、現在の状態は判定できた人全員に送ります。", file=sys.stderr)

    master_index = build_master_index(master_rows, config, args.as_of)
    permission_updates, status_updates, tag_updates, report, unmatched, routes = plan_changes(master_index, satori_rows, config)

    os.makedirs(args.out, exist_ok=True)
    enc = config.get("output_encoding", "utf-8-sig")
    status_col = f"custom:{config['api']['status_custom_field']}"
    for name, header, updates in (("satori_import_配信拒否.csv", ["email", "delivery_permission"], permission_updates),
                                  ("satori_import_現在の状態.csv", ["email", status_col], status_updates),
                                  ("satori_import_タグ.csv", ["email", "append_tags"], tag_updates)):
        write_csv(os.path.join(args.out, name), header, [[u["email"], u["value"]] for u in updates], enc)
    rejoined_updates = [u for u in status_updates if u["reason"] == REJOINED]
    _, rejoined_rows = build_import_rows([], rejoined_updates, [], config)
    import_header, import_rows = build_import_rows(permission_updates, status_updates, tag_updates, config)
    write_csv(os.path.join(args.out, "satori_import_再入会_在籍.csv"), import_header, rejoined_rows,
              config.get("import_encoding", "cp932"))
    write_csv(os.path.join(args.out, "satori_import_一括登録.csv"), import_header, import_rows,
              config.get("import_encoding", "cp932"))
    write_csv(os.path.join(args.out, "変更レポート.csv"), ["メールアドレス", "項目", "変更前", "変更後", "理由"], report, enc)
    write_csv(os.path.join(args.out, "SATORI未登録_送付禁止.csv"), ["メールアドレス"], [[e] for e in unmatched], enc)

    status_counts = collections.Counter(u["value"] for u in status_updates)
    print(f"マスター: {len(master_rows)}行 / メールアドレス {len(master_index)}件")
    print(f"SATORI: {len(satori_rows)}件")
    print(f"配信許可→「{s['permission_denied_value']}」に変更: {len(permission_updates)}件")
    print(f"現在の状態を送信: {len(status_updates)}件 " + " / ".join(f"{k} {v}件" for k, v in status_counts.most_common()))
    print(f"タグ「{config['tag']['name']}」を追加: {len(tag_updates)}件")
    print(f"送付禁止だがSATORI未登録: {len(unmatched)}件")
    print(f"一括登録用CSV: {len(import_rows)}件（うち再入会→在籍 {len(rejoined_rows)}件は satori_import_再入会_在籍.csv にも出力）")
    print(f"出力先: {os.path.abspath(args.out)}")

    if args.apply:
        only = set(args.only or ["permission", "status", "tag"])
        apply_via_api(permission_updates if "permission" in only else [],
                      status_updates if "status" in only else [],
                      tag_updates if "tag" in only else [], routes, config)


def apply_via_api(permission_updates, status_updates, tag_updates, routes, config):
    import satori_api

    header, rows = build_api_rows(permission_updates, status_updates, tag_updates, routes, config)
    if not rows:
        print("SATORIへ反映する変更はありません。")
        return
    credentials = satori_api.load_credentials()
    for result in satori_api.upsert_and_wait(credentials, header, rows):
        failed = result.get("failed_rows") or []
        print(f"処理完了: 成功 {len(result.get('succeeded_rows') or [])}件 / 失敗 {len(failed)}件")
        for f in failed[:50]:
            print(f"  失敗 行{f.get('row_number')}: {f.get('message')}")


if __name__ == "__main__":
    main()
