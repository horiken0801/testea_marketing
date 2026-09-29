# 新規状況表v2.0 → SATORI カスタマー情報 連携

新規状況表v2.0_マスター の顧客データを、メールアドレスで SATORI のカスタマーと突き合わせて、
SATORI の「CSVインポート（カスタマー更新）」に使うCSVを作ります。

| # | 内容 | 新規状況表の列 | SATORIの項目 |
|---|------|----------------|--------------|
| ① | 送付禁止の人を配信拒否にする | 送付禁止フラグ（チェックあり） | 配信許可 → 「拒否」 |
| ② | 未決・元在などを反映 | 問合日・対応日付・入会・退会日 | 現在の状態（`custom:custom_situation`） |

### 現在の状態の決め方

実行日（`--as-of`、既定は今日）の **前月** を判定対象月とします（9月に実行すると8月）。

| 条件 | 現在の状態 |
|------|-----------|
| 退会日あり | 元在 |
| 入会・再入会の日付あり | 在籍 |
| 在籍ステータスが「元在」 | 元在 |
| 判定対象月の末日までの問合せで、問合日・初期対応へのレス・面談実施・体験実施のうち **最後の日付が判定対象月の中**（そこで対応が止まっている） | 未決 |
| 上のどれにも当たらない | 送らない（SATORIの値はそのまま） |

毎月1回、前月分を判定する運用を想定しています。

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
- 「現在の状態」はカスタム項目 `custom_situation` として送ります（`config.json` の `api.status_custom_field`）。
  SATORIのエクスポートCSVには現在の状態が含まれないため、判定できた人には毎回送ります（同じ値なら実質変化なし）。
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
- `status_values`: 現在の状態に書き込む値（未決・元在・在籍）
- `master.activity_date_columns`: 未決判定で「最後の対応日」を見る列
- `output_encoding`: 出力CSVの文字コード（既定 `utf-8-sig`。SATORIでShift_JISが必要なら `cp932`）

## テスト

```bash
python3 -m unittest test_sync_satori
```
