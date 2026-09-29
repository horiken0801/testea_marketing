# 新規状況表v2.0 → SATORI カスタマー情報 連携

新規状況表v2.0_マスター の顧客データを、メールアドレスで SATORI のカスタマーと突き合わせて、
SATORI の「CSVインポート（カスタマー更新）」に使うCSVを作ります。

| # | 内容 | 新規状況表の列 | SATORIの項目 |
|---|------|----------------|--------------|
| ① | 送付禁止の人を配信拒否にする | 送付禁止フラグ（チェックあり） | 配信許可 → 「拒否」 |
| ② | 未決・元在などを反映 | 在籍ステータス | 現在の状態 |

## 使い方

1. **新規状況表v2.0** の「新規状況表v2.0_マスター」シートを開き、ファイル → ダウンロード → CSV で保存（例: `master.csv`）
2. **SATORI** のカスタマー一覧から、`メールアドレス`・`配信許可`・`現在の状態` を含む形でCSVをエクスポート（例: `satori.csv`）
3. スクリプトを実行

   ```bash
   python3 sync_satori.py --master master.csv --satori satori.csv --out output
   ```

4. `output/変更レポート.csv` を開いて、変更内容が正しいか確認
5. SATORI のカスタマーインポートで、メールアドレスをキーにして次の2ファイルを取り込む
   - `satori_import_配信拒否.csv`
   - `satori_import_現在の状態.csv`

`SATORI未登録_送付禁止.csv` には、送付禁止なのにSATORIにメールアドレスが見つからなかった人が入ります（必要に応じて確認してください）。

## SATORI APIで直接反映する（`--apply`）

CSVを手でインポートする代わりに、SATORI のカスタマーバルクAPI（upsert）で直接反映できます。
APIキーは **ファイルに書かず、環境変数で渡してください**。

```bash
export SATORI_USER_KEY=...        # ユーザーアクセスキー
export SATORI_USER_SECRET=...     # ユーザーシークレットキー
export SATORI_COMPANY_KEY=...     # カンパニーアクセスキー
export SATORI_COMPANY_SECRET=...  # カンパニーシークレットキー

# まずは --apply なしで実行し、output/変更レポート.csv を確認
python3 sync_satori.py --master master.csv --satori satori.csv
# 問題なければ反映
python3 sync_satori.py --master master.csv --satori satori.csv --apply
```

- SATORI のAPIにはカスタマーを検索する機能がなく、upsert は未登録のメールアドレスを新規登録してしまいます。
  そのため、API で反映する場合も **SATORIのエクスポートCSV（`--satori`）が必要** です（登録済みの人だけに絞るため）。
- 配信許可は `delivery_permission=reject` で送ります。
- 「現在の状態」はカスタム項目なので、`config.json` の `api.status_custom_field` に
  **カスタム項目の識別名**（SATORI管理画面 → カスタム項目設定で確認）を入れると、APIで反映されます。未設定（`null`）の間は配信許可だけを反映します。
- 送信後は処理完了まで待ち、SATORIから返ってきた成功・失敗件数を表示します。

## ルール

- 対象は SATORI に既に登録されているカスタマーだけです（メールアドレスが一致した人）。新しいカスタマーは作りません。
- メールアドレスは大文字・小文字、全角・半角の違いを無視して比較します。1つのセルに複数のアドレスが書かれている場合は、すべてを対象にします。
- 配信許可は **「拒否」への変更だけ** 行います。「拒否」になっている人を「許可」に戻すことはありません。
- `営業・取材・スパムフラグ` が付いた行は、ステータス反映の対象外です。
- 同じメールアドレスが複数の行にある場合（兄弟など）は `status_priority` の順（在籍 ＞ 未決 ＞ 元在）で決め、同じ順位なら下の行（新しい行）を採用します。
- 送付禁止フラグは、どれか1行でもチェックがあれば「拒否」にします。
- 変更が必要な人だけをCSVに出力します（すでに同じ値の人は含みません）。

## 設定（`config.json`）

SATORI の項目名や選択肢の値が実際と違う場合は、`config.json` を修正してください。

- `satori.permission_column` / `permission_denied_value`: 配信許可の列名と「拒否」の値
- `satori.status_column`: 現在の状態の列名
- `status_mapping`: 在籍ステータス → 現在の状態 の対応表。**表にない値は反映しません。**
  初期設定では「入会→在籍」「退会→元在」「未対応・アンケート回答済・面談実施済・体験実施済→未決」にしています。SATORI の「現在の状態」の選択肢に合わせて調整してください。
- `output_encoding`: 出力CSVの文字コード（既定 `utf-8-sig`。SATORIでShift_JISが必要なら `cp932`）

## テスト

```bash
python3 -m unittest test_sync_satori
```
