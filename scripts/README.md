# scripts

マーケティング業務の自動化スクリプトを格納します。

## 現在の内容

- `satori_sync/` — 新規状況表とSATORI（CRM）の連携スクリプト・GASコード
- `sns-automation/` — X/Threads向けトレンド下書き生成ボット（`.github/workflows/`のGitHub Actionsから実行。詳細は`sns-automation/README.md`参照）

APIキーやトークンなどの機密情報はコードに直接書かず、環境変数や設定ファイル（.gitignore対象）で管理してください。
