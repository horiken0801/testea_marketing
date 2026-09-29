import csv
import datetime
import os
import tempfile
import unittest
from unittest import mock

import satori_api
import sync_satori

MASTER_CSV = """校舎,問合日,名前,初期対応へのレス,面談実施,体験実施,入会,再入会,メールアドレス,退会日,在籍ステータス,営業・取材・スパムフラグ,送付禁止フラグ
久我山校,2026-07-10 0:00:00,8月で停止,2026/07/11,2026/08/05,,,,Taro@Example.com,,体験実施済,FALSE,TRUE
久我山校,2017-04-28 0:00:00,旧未決,,,,,,old@example.com,,未決,FALSE,FALSE
久我山校,2018-01-01,兄(元在),,,,,,ｈａｎａｋｏ＠ｅｘａｍｐｌｅ．ｃｏｍ,,元在,FALSE,FALSE
駒込校,2025-01-01,弟(入会),,,,2025/02/01,,hanako@example.com,,入会,FALSE,FALSE
日吉校,2024-01-01,退会,,,,2024/02/01,,a@example.com / b@example.com,2025/03/31,退会,FALSE,TRUE
日吉校,2026-08-20,営業,,,,,,sales@example.com,,未対応,TRUE,FALSE
日吉校,2026-08-25,9月も対応中,,2026/08/28,2026/09/03,,,sept@example.com,,体験実施済,FALSE,FALSE
日吉校,2026-09-02,9月問合せ,,,,,,new@example.com,,未対応,FALSE,FALSE
日吉校,2026-08-30,8月問合せ未対応,,,,,,aug@example.com,,未対応,FALSE,FALSE
日吉校,2026-07-01,7月で停止,,2026/07/20,,,,july@example.com,,面談実施済,FALSE,FALSE
日吉校,2021-01-01,既に拒否,,,,,,already@example.com,,,FALSE,TRUE
日吉校,2021-01-01,未登録,,,,,,nobody@example.com,,,FALSE,TRUE
"""

SATORI_EMAILS = ["taro@example.com", "old@example.com", "hanako@example.com", "b@example.com",
                 "sales@example.com", "sept@example.com", "new@example.com", "aug@example.com",
                 "july@example.com", "already@example.com", "other@example.com"]
SATORI_CSV = "email,delivery_permission,delivery_status\n" + "".join(
    f"{e},{'拒否' if e == 'already@example.com' else '承認'},正常\n" for e in SATORI_EMAILS)


class SyncSatoriTest(unittest.TestCase):
    def run_sync(self, satori_encoding="cp932"):
        tmp = tempfile.mkdtemp()
        master = os.path.join(tmp, "master.csv")
        satori = os.path.join(tmp, "satori.csv")
        out = os.path.join(tmp, "out")
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
        self.assertEqual(read("satori_import_現在の状態.csv"), [
            ["taro@example.com", "未決"],    # 最後の対応が8月で止まっている
            ["hanako@example.com", "在籍"],  # 兄は元在だが弟が入会 → 在籍を優先
            ["b@example.com", "元在"],       # 退会日あり
            ["aug@example.com", "未決"],     # 8月の問合せで対応なし
        ])
        # old(旧リストの未決)・sept(9月も対応中)・new(9月問合せ)・july(7月で停止)・sales(営業) は送らない

    def test_unmatched_do_not_send_reported(self):
        read = self.run_sync()
        self.assertEqual(read("SATORI未登録_送付禁止.csv"), [["a@example.com"], ["nobody@example.com"]])

    def test_reads_utf8_satori_export(self):
        read = self.run_sync(satori_encoding="utf-8")
        self.assertEqual(len(read("変更レポート.csv")), 6)


class PreviousMonthTest(unittest.TestCase):
    def test_january_wraps_to_previous_year(self):
        self.assertEqual(sync_satori.previous_month(datetime.date(2027, 1, 15)),
                         (datetime.date(2026, 12, 1), datetime.date(2026, 12, 31)))

    def test_parse_date_ignores_dates_without_year(self):
        self.assertIsNone(sync_satori.parse_date("02/01"))
        self.assertEqual(sync_satori.parse_date("2026-08-05 0:00:00"), datetime.date(2026, 8, 5))


class ApiRowsTest(unittest.TestCase):
    PERMISSION = [{"メールアドレス": "a@example.com", "配信許可": "拒否"}]
    STATUS = [{"メールアドレス": "a@example.com", "現在の状態": "未決"},
              {"メールアドレス": "b@example.com", "現在の状態": "元在"}]

    def config(self, field):
        return {"satori": {"email_column": "メールアドレス", "status_column": "現在の状態"},
                "api": {"delivery_permission_reject": "reject", "status_custom_field": field}}

    def test_merges_rows_per_email_with_custom_field(self):
        header, rows = sync_satori.build_api_rows(self.PERMISSION, self.STATUS, self.config("current_state"))
        self.assertEqual(header, ["email", "delivery_permission", "custom:current_state"])
        self.assertEqual(rows, [
            {"email": "a@example.com", "delivery_permission": "reject", "custom:current_state": "未決"},
            {"email": "b@example.com", "custom:current_state": "元在"},
        ])
        # 空欄は SATORI 側で上書きされない
        self.assertEqual(satori_api.build_csv(header, rows).decode().splitlines()[2], "b@example.com,,元在")

    def test_status_skipped_without_custom_field(self):
        header, rows = sync_satori.build_api_rows(self.PERMISSION, self.STATUS, self.config(None))
        self.assertEqual(header, ["email", "delivery_permission"])
        self.assertEqual(rows, [{"email": "a@example.com", "delivery_permission": "reject"}])

    def test_upsert_and_wait_polls_until_finished(self):
        creds = dict.fromkeys(["user_key", "user_secret", "company_key", "company_secret"], "x")
        with mock.patch.object(satori_api, "upsert", return_value={"status": 200, "message": {"process_code": "P1"}}) as up, \
                mock.patch.object(satori_api, "status", side_effect=[
                    {"status": 200, "message": {"process_status": "started"}},
                    {"status": 200, "message": {"process_status": "finished", "success_count": 1}}]), \
                mock.patch.object(satori_api.time, "sleep"):
            results = satori_api.upsert_and_wait(creds, ["email"], [{"email": "a@example.com"}])
        self.assertEqual(results, [{"process_status": "finished", "success_count": 1}])
        self.assertEqual(up.call_count, 1)

    def test_missing_credentials(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(SystemExit):
                satori_api.load_credentials()


if __name__ == "__main__":
    unittest.main()
