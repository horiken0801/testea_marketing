#!/usr/bin/env python3
"""新規状況表v2.0 の顧客データを SATORI のカスタマー情報へ反映するためのインポートCSVを生成する。

入力:
  - 新規状況表v2.0_マスター をCSVでダウンロードしたもの
  - SATORI のカスタマー一覧をCSVでエクスポートしたもの

出力（--out ディレクトリ）:
  - satori_import_配信拒否.csv   : 送付禁止フラグが付いた顧客の 配信許可 を「拒否」にするインポート用CSV
  - satori_import_現在の状態.csv : 在籍ステータス（未決・元在など）を 現在の状態 に反映するインポート用CSV
  - 変更レポート.csv             : 何をどう変えるかの一覧（確認用）
  - SATORI未登録_送付禁止.csv    : 送付禁止だがSATORIにメールアドレスが見つからなかった顧客

SATORI側に既に存在するカスタマー（メールアドレス一致）だけを対象にし、
配信許可は「拒否」への変更のみ行う（拒否→許可には戻さない）。

--apply を付けると、上記の変更を SATORI のカスタマーバルクAPI（upsert）で直接反映する。
APIキーは環境変数 SATORI_USER_KEY / SATORI_USER_SECRET / SATORI_COMPANY_KEY / SATORI_COMPANY_SECRET で渡す。
"""

import argparse
import csv
import json
import os
import re
import sys
import unicodedata

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
TRUTHY = {"true", "1", "yes", "y", "on", "はい", "済", "○", "〇", "◯", "✓", "✔", "☑", "レ"}
INPUT_ENCODINGS = ("utf-8-sig", "cp932")


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


def build_master_index(rows, config):
    """メールアドレスごとに 送付禁止 と SATORIへ書き込む状態 を集約する。"""
    m = config["master"]
    mapping = {normalize_text(k): v for k, v in config["status_mapping"].items()}
    priority = {s: i for i, s in enumerate(config["status_priority"])}

    index = {}
    for row_no, row in enumerate(rows):
        emails = extract_emails(row.get(m["email_column"], ""))
        if not emails:
            continue
        spam = is_checked(row.get(m.get("spam_column", ""), ""))
        do_not_send = is_checked(row.get(m["do_not_send_column"], ""))
        raw_status = normalize_text(row.get(m["status_column"], ""))
        status = None if spam else mapping.get(raw_status)

        for email in emails:
            entry = index.setdefault(email, {"do_not_send": False, "status": None, "rank": None, "raw_status": ""})
            entry["do_not_send"] = entry["do_not_send"] or do_not_send
            if status is None:
                continue
            rank = (priority.get(status, len(priority)), -row_no)
            if entry["rank"] is None or rank <= entry["rank"]:
                entry.update(status=status, rank=rank, raw_status=raw_status)
    return index


def plan_changes(master_index, satori_rows, config):
    s = config["satori"]
    denied = s["permission_denied_value"]
    permission_updates, status_updates, report = [], [], []
    matched = set()

    for row in satori_rows:
        emails = extract_emails(row.get(s["email_column"], ""))
        if not emails:
            continue
        email = emails[0]
        entry = master_index.get(email)
        if entry is None:
            continue
        matched.add(email)
        original_email = normalize_text(row[s["email_column"]])

        current_permission = normalize_text(row.get(s["permission_column"], ""))
        if entry["do_not_send"] and current_permission != denied:
            permission_updates.append({s["email_column"]: original_email, s["permission_column"]: denied})
            report.append([original_email, s["permission_column"], current_permission, denied, "送付禁止フラグ"])

        current_status = normalize_text(row.get(s["status_column"], ""))
        if entry["status"] and current_status != entry["status"]:
            status_updates.append({s["email_column"]: original_email, s["status_column"]: entry["status"]})
            report.append([original_email, s["status_column"], current_status, entry["status"],
                           f"在籍ステータス: {entry['raw_status']}"])

    unmatched_do_not_send = sorted(e for e, v in master_index.items() if v["do_not_send"] and e not in matched)
    return permission_updates, status_updates, report, unmatched_do_not_send


def build_api_rows(permission_updates, status_updates, config):
    """変更内容を バルクAPI 用の行（1メールアドレス1行）にまとめる。"""
    s, api = config["satori"], config["api"]
    status_field = api.get("status_custom_field")
    header = ["email", "delivery_permission"] + ([f"custom:{status_field}"] if status_field else [])
    rows = {}
    for u in permission_updates:
        email = u[s["email_column"]]
        rows.setdefault(email, {"email": email})["delivery_permission"] = api["delivery_permission_reject"]
    if status_field:
        for u in status_updates:
            email = u[s["email_column"]]
            rows.setdefault(email, {"email": email})[f"custom:{status_field}"] = u[s["status_column"]]
    return header, list(rows.values())


def write_csv(path, header, rows, encoding):
    with open(path, "w", newline="", encoding=encoding) as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in rows:
            writer.writerow([row[h] for h in header] if isinstance(row, dict) else row)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--master", required=True, help="新規状況表v2.0_マスター のCSV")
    parser.add_argument("--satori", required=True, help="SATORIからエクスポートしたカスタマーCSV")
    parser.add_argument("--out", default="output", help="出力先ディレクトリ (既定: output)")
    parser.add_argument("--apply", action="store_true", help="SATORI APIで直接反映する（付けなければCSV出力のみ）")
    parser.add_argument("--config", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json"))
    args = parser.parse_args(argv)

    with open(args.config, encoding="utf-8") as f:
        config = json.load(f)
    s = config["satori"]

    _, master_rows = read_csv(args.master, config["master"]["email_column"])
    satori_header, satori_rows = read_csv(args.satori, s["email_column"])
    for col in (s["permission_column"], s["status_column"]):
        if col not in satori_header:
            print(f"警告: SATORIのCSVに列「{col}」がありません。現在値を空として比較します。", file=sys.stderr)

    master_index = build_master_index(master_rows, config)
    permission_updates, status_updates, report, unmatched = plan_changes(master_index, satori_rows, config)

    os.makedirs(args.out, exist_ok=True)
    enc = config.get("output_encoding", "utf-8-sig")
    write_csv(os.path.join(args.out, "satori_import_配信拒否.csv"),
              [s["email_column"], s["permission_column"]], permission_updates, enc)
    write_csv(os.path.join(args.out, "satori_import_現在の状態.csv"),
              [s["email_column"], s["status_column"]], status_updates, enc)
    write_csv(os.path.join(args.out, "変更レポート.csv"),
              ["メールアドレス", "項目", "変更前", "変更後", "理由"], report, enc)
    write_csv(os.path.join(args.out, "SATORI未登録_送付禁止.csv"),
              ["メールアドレス"], [[e] for e in unmatched], enc)

    print(f"マスター: {len(master_rows)}行 / メールアドレス {len(master_index)}件")
    print(f"SATORI: {len(satori_rows)}件")
    print(f"配信許可→「{s['permission_denied_value']}」に変更: {len(permission_updates)}件")
    print(f"現在の状態を更新: {len(status_updates)}件")
    print(f"送付禁止だがSATORI未登録: {len(unmatched)}件")
    print(f"出力先: {os.path.abspath(args.out)}")

    if args.apply:
        apply_via_api(permission_updates, status_updates, config)


def apply_via_api(permission_updates, status_updates, config):
    import satori_api

    header, rows = build_api_rows(permission_updates, status_updates, config)
    if not config["api"].get("status_custom_field") and status_updates:
        print("注意: config.json の api.status_custom_field が未設定のため、現在の状態はAPIで反映しません。")
    if not rows:
        print("SATORIへ反映する変更はありません。")
        return
    credentials = satori_api.load_credentials()
    for result in satori_api.upsert_and_wait(credentials, header, rows):
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
