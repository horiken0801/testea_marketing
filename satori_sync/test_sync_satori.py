import csv
import datetime
import os
import tempfile
import unittest
from unittest import mock

import satori_api
import sync_satori

MASTER_CSV = """校舎,問合日,名前,初期対応へのレス,面談実施,体験実施,入会,再入会,メールアドレス,退会日,在籍ステータス,営業・取材・スパムフラグ,送付禁止フラグ
久我山校,2026-07-10 0:00:00,8月で停止,2026/07/11,2026/08/05,,,FALSE,Taro@Example.com,,体験実施済,FALSE,TRUE
久我山校,2017-04-28 0:00:00,旧リスト,,,,,,old@example.com,,未決,FALSE,FALSE
久我山校,2018-01-01,兄(元在),,,,,,ｈａｎａｋｏ＠ｅｘａｍｐｌｅ．ｃｏｍ,,元在,FALSE,FALSE
駒込校,2025-01-01,弟(再入会),,,,,TRUE,hanako@example.com,,入会,FALSE,FALSE
日吉校,2024-01-01,退会,,,,2024/02/01,,a@example.com / b@example.com,2025/03/31,退会,FALSE,TRUE
日吉校,2026-08-20,営業,,,,,,sales@example.com,,未対応,TRUE,FALSE
日吉校,2026-08-25,9月も対応中,,2026/08/28,2026/09/03,,,sept@example.com,,体験実施済,FALSE,FALSE
日吉校,2026-09-02,9月問合せ,,,,,,new@example.com,,未対応,FALSE,FALSE
日吉校,2026-05-30,5月問合せ,,,,,,may@example.com,,未対応,FALSE,FALSE
日吉校,2021-01-01,既に拒否,,,,,,already@example.com,,,FALSE,TRUE
日吉校,2021-01-01,未登録,,,,,,nobody@example.com,,,FALSE,TRUE
田町校,11/20,旧シート,,11/25,,,,md1@example.com,,面談実施済,FALSE,FALSE
田町校,12/15,旧シート,,01/10,,,,md2@example.com,,面談実施済,FALSE,FALSE
田町校,06/10,旧シート,,,,,,md3@example.com,,未対応,FALSE,FALSE
田町校,09/05,旧シート,,,,,,md4@example.com,,未対応,FALSE,FALSE
駒込校,2019-01-01,元在,,,,,,rejoin@example.com,,元在,FALSE,FALSE
駒込校,2026-04-01,再入会,,04/05,,04/20,TRUE,rejoin@example.com,,入会,FALSE,FALSE
"""

SATORI_EMAILS = ["taro@example.com", "old@example.com", "hanako@example.com", "b@example.com",
                 "sales@example.com", "sept@example.com", "new@example.com", "may@example.com",
                 "already@example.com", "md1@example.com", "md2@example.com", "md3@example.com",
                 "md4@example.com", "rejoin@example.com", "other@example.com"]


def satori_row(e):
    permission = "拒否" if e == "already@example.com" else "承認"
    tags = "新規_未決元在" if e == "may@example.com" else "メルマガ読者"
    return f'{e},{permission},正常,WEB検索,"{tags}"\n'


SATORI_CSV = "email,delivery_permission,delivery_status,collection_route,tags\n" + "".join(map(satori_row, SATORI_EMAILS))


class SyncSatoriTest(unittest.TestCase):
    def run_sync(self, satori_encoding="cp932"):
        tmp = tempfile.mkdtemp()
        master = os.path.join(tmp, "master.csv")
        satori = os.path.join(tmp, "satori.csv")
        out = os.path.join(tmp, "out")
        self.last_out = out
        with open(master, "w", encoding="utf-8") as f:
            f.write(MASTER_CSV)
        with open(satori, "w", encoding=satori_encoding) as f:
            f.write(SATORI_CSV)
        sync_satori.main(["--master", master, "--satori", satori, "--out", out, "--as-of", "2026-09-29"])

        def read(name):
            with open(os.path.join(out, name), encoding="utf-8-sig", newline="") as f:
                return list(csv.reader(f))[1:]

        return read

    def test_permission_denied_only_for_flagged_and_not_already_denied(self):
        read = self.run_sync()
        self.assertEqual(read("satori_import_配信拒否.csv"),
                         [["taro@example.com", "拒否"], ["b@example.com", "拒否"]])

    def test_status_rules(self):
        read = self.run_sync()
        self.assertEqual(dict(read("satori_import_現在の状態.csv")), {
            "taro@example.com": "未決",    # 最後の対応が8月
            "old@example.com": "未決",     # 2017年の問合せで対応なし
            "b@example.com": "元在",       # 退会日あり
            "may@example.com": "未決",
            "already@example.com": "未決",  # 2021年の問合せで対応なし
            "rejoin@example.com": "在籍",   # 元在 → 再入会（チェック・入会日あり）
            "hanako@example.com": "在籍",   # 弟が再入会チェックのみ（入会日なし）でも再入会として在籍
            "md1@example.com": "未決",     # 年なし 2025/11/20 問合せ・11/25 面談
            "md2@example.com": "未決",     # 年なし 2025/12/15 問合せ・2026/01/10 面談
            "md3@example.com": "未決",     # 年なし 2026/06/10 問合せ
        })
        # sept(9月も対応中)・new(9月問合せ)・sales(営業)・md4(2025/09/05? → 年推定で2026/09/05) は送らない

    def test_tag_for_recent_pending_without_existing_tag(self):
        read = self.run_sync()
        self.assertEqual(read("satori_import_タグ.csv"),
                         [["taro@example.com", "新規_未決元在"], ["md3@example.com", "新規_未決元在"]])

    def test_combined_import_csv_is_shift_jis_with_blanks(self):
        self.run_sync()
        with open(os.path.join(self.last_out, "satori_import_一括登録.csv"), encoding="cp932", newline="") as f:
            rows = list(csv.reader(f))
        self.assertEqual(rows[0], ["email", "delivery_permission", "custom:custom_situation", "tags"])
        self.assertIn(["taro@example.com", "拒否", "未決", "新規_未決元在"], rows)
        self.assertIn(["old@example.com", "", "未決", ""], rows)
        self.assertIn(["already@example.com", "", "未決", ""], rows)

    def test_rejoined_csv(self):
        self.run_sync()
        with open(os.path.join(self.last_out, "satori_import_再入会_在籍.csv"), encoding="cp932", newline="") as f:
            self.assertEqual(list(csv.reader(f))[1:], [["hanako@example.com", "", "在籍", ""],
                                                       ["rejoin@example.com", "", "在籍", ""]])

    def test_unmatched_do_not_send_reported(self):
        read = self.run_sync()
        self.assertEqual(read("SATORI未登録_送付禁止.csv"), [["a@example.com"], ["nobody@example.com"]])

    def test_reads_utf8_satori_export(self):
        read = self.run_sync(satori_encoding="utf-8")
        self.assertEqual(len(read("変更レポート.csv")), 14)


class DateTest(unittest.TestCase):
    def test_previous_month_end_wraps_year(self):
        self.assertEqual(sync_satori.previous_month_end(datetime.date(2027, 1, 15)), datetime.date(2026, 12, 31))

    def test_parse_dates(self):
        self.assertIsNone(sync_satori.parse_date("02/01"))
        self.assertEqual(sync_satori.parse_date("2026-08-05 0:00:00"), datetime.date(2026, 8, 5))
        self.assertEqual(sync_satori.parse_month_days("8/3 8/10"), [(8, 3), (8, 10)])
        self.assertEqual(sync_satori.parse_month_days("リスケ"), [])

    def test_infer_years_walks_back_over_year_boundary(self):
        rows = [{"校舎": "A", "問合日": d} for d in ("03/01", "12/20", "01/05", "05/10")]
        rows.append({"校舎": "B", "問合日": "10/01"})
        dates = sync_satori.infer_inquiry_dates(rows, "校舎", "問合日", datetime.date(2026, 9, 29))
        self.assertEqual(dates, [datetime.date(2025, 3, 1), datetime.date(2025, 12, 20), datetime.date(2026, 1, 5),
                                 datetime.date(2026, 5, 10), datetime.date(2025, 10, 1)])

    def test_activity_date_after_inquiry_crosses_year(self):
        self.assertEqual(sync_satori.activity_dates("01/10", datetime.date(2025, 12, 15)), [datetime.date(2026, 1, 10)])


class ApiRowsTest(unittest.TestCase):
    CONFIG = {"api": {"delivery_permission_reject": "reject", "status_custom_field": "custom_situation",
                      "collection_route_fallback": "新規状況表v2.0"}}

    def test_merges_rows_per_email(self):
        header, rows = sync_satori.build_api_rows(
            [{"email": "a@example.com", "value": "拒否"}],
            [{"email": "a@example.com", "value": "未決"}, {"email": "b@example.com", "value": "元在"}],
            [{"email": "b@example.com", "value": "新規_未決元在"}],
            {"a@example.com": "WEB検索", "b@example.com": ""}, self.CONFIG)
        self.assertEqual(header, ["email", "collection_route", "delivery_permission", "custom:custom_situation", "append_tags"])
        self.assertEqual(rows, [
            {"email": "a@example.com", "collection_route": "WEB検索", "delivery_permission": "reject",
             "custom:custom_situation": "未決"},
            {"email": "b@example.com", "collection_route": "新規状況表v2.0", "custom:custom_situation": "元在",
             "append_tags": "新規_未決元在"},
        ])
        # 空欄は SATORI 側で上書きされない
        self.assertEqual(satori_api.build_csv(header, rows).decode().splitlines()[2],
                         "b@example.com,新規状況表v2.0,,元在,新規_未決元在")

    def test_upsert_and_wait_polls_until_finished(self):
        creds = dict.fromkeys(["user_key", "user_secret", "company_key", "company_secret"], "x")
        with mock.patch.object(satori_api, "upsert", return_value={"status": 200, "message": {"process_code": "P1"}}) as up, \
                mock.patch.object(satori_api, "status", side_effect=[
                    {"status": 200, "message": {"process_status": "started"}},
                    {"status": 200, "message": {"process_status": "finished", "succeeded_rows": []}}]), \
                mock.patch.object(satori_api.time, "sleep"):
            results = satori_api.upsert_and_wait(creds, ["email"], [{"email": "a@example.com"}])
        self.assertEqual(results, [{"process_status": "finished", "succeeded_rows": []}])
        self.assertEqual(up.call_count, 1)

    def test_missing_credentials(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                satori_api.load_credentials()


if __name__ == "__main__":
    unittest.main()
