# X専用 参考データ置き場

このフォルダは `scripts/draft_x_posts.py` からのみ読み込まれます（Threads側の生成では読み込まれません）。`data/reference/`（Threads/X共通フォルダ）と合わせて参照されます。

## ファイル一覧

- `x_operation_prompt.md`: **X運用の指示書（最優先で従うルール）**。アカウント実績、投稿スロット設計、カテゴリ設計、HP誘導の実在URL一覧、KPI、禁止事項、出力形式などを網羅。内容が更新されたら、このファイルを上書きするかたちで反映してください
- `00_recent_results.md`: **直近実績サマリ（軽量・週次追記用）**。Xアナリティクスの「アカウント概要」CSVをこのチャットに貼っていただければ、書き起こして追記します

`.md` / `.txt` 以外のファイル、および `README.md` 自体は読み込み対象外です（`data/reference/` と同じ仕様）。

## 誘導先URLについて

`x_operation_prompt.md` の第4節に記載された実在URL一覧に無いURLは、生成コード側（`socialbot/trend_drafts.py`）で自動的に誘導先候補から除外されます。新しいページを誘導先に追加したい場合は、まず実在確認のうえ `x_operation_prompt.md` の一覧に追記してください。
