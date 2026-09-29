import csv
import os
import tempfile
import unittest

import sync_satori

MASTER_CSV = """校舎,問合日,名前,メールアドレス,在籍ステータス,営業・取材・スパムフラグ,送付禁止フラグ
久我山校,2017-04-28,大金,Taro@Example.com,未決,FALSE,TRUE
久我山校,2018-01-01,鈴木,ｈａｎａｋｏ＠ｅｘａｍｐｌｅ．ｃｏｍ,元在,FALSE,FALSE
駒込校,2019-01-01,鈴木弟,hanako@example.com,入会,FALSE,FALSE
日吉校,2020-01-01,佐藤,a@example.com / b@example.com,退会,FALSE,TRUE
日吉校,2020-01-01,営業,sales@example.com,未対応,TRUE,FALSE
日吉校,2021-01-01,田中,already@example.com,未決,FALSE,TRUE
日吉校,2021-01-01,未登録,nobody@example.com,未決,FALSE,TRUE
"""

SATORI_CSV = """メールアドレス,姓,配信許可,現在の状態
taro@example.com,大金,許可,
hanako@example.com,鈴木,許可,元在
b@example.com,佐藤,許可,元在
sales@example.com,営業,許可,
already@example.com,田中,拒否,未決
other@example.com,他,許可,未決
"""


class SyncSatoriTest(unittest.TestCase):
    def run_sync(self, satori_encoding="utf-8"):
        tmp = tempfile.mkdtemp()
        master = os.path.join(tmp, "master.csv")
        satori = os.path.join(tmp, "satori.csv")
        out = os.path.join(tmp, "out")
        with open(master, "w", encoding="utf-8") as f:
            f.write(MASTER_CSV)
        with open(satori, "w", encoding=satori_encoding) as f:
            f.write(SATORI_CSV)
        sync_satori.main(["--master", master, "--satori", satori, "--out", out])

        def read(name):
            with open(os.path.join(out, name), encoding="utf-8-sig", newline="") as f:
                return list(csv.reader(f))[1:]

        return read

    def test_permission_denied_only_for_flagged_and_not_already_denied(self):
        read = self.run_sync()
        self.assertEqual(read("satori_import_配信拒否.csv"),
                         [["taro@example.com", "拒否"], ["b@example.com", "拒否"]])

    def test_status_mapping_priority_and_spam_skip(self):
        read = self.run_sync()
        # hanako: 元在 と 入会(→在籍) の2行 → 在籍優先 / b: 退会→元在 は変更なし / sales: 営業フラグで対象外
        self.assertEqual(read("satori_import_現在の状態.csv"),
                         [["taro@example.com", "未決"], ["hanako@example.com", "在籍"]])

    def test_unmatched_do_not_send_reported(self):
        read = self.run_sync()
        self.assertEqual(read("SATORI未登録_送付禁止.csv"), [["a@example.com"], ["nobody@example.com"]])

    def test_reads_shift_jis_satori_export(self):
        read = self.run_sync(satori_encoding="cp932")
        self.assertEqual(len(read("変更レポート.csv")), 4)


if __name__ == "__main__":
    unittest.main()
