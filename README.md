# testea_marketing

TESTEA個別指導塾のマーケティング業務を一元管理するリポジトリです。
これまで複数のリポジトリやセッションに分散していたキャンペーン企画・広告運用・CRM連携・SNS運用・進行管理の資産を、ここに集約しています。

## 構成

- `docs/campaigns/` — キャンペーン企画書、LP文言、校舎別施策（秋期キャンペーン、センター南校新規開校、久我山校競合対策など）
- `docs/ads/` — 広告運用（Google広告/Yahoo!広告の除外キーワード、ロケーション設定、運用方針）
- `docs/crm/` — CRM連携仕様（SATORI連携、顧客データフラグ設計など）
- `docs/sns/` — SNS運用ルール、X/Threads自動化、DM対応ケース集
- `docs/operations/` — 運用カレンダー、日報フォーマット、進行管理・タスク管理、過去セッション履歴
- `scripts/` — GAS/Python等の自動化スクリプト（SATORI連携、SNS自動化ボット）
- `data/reference/` — 過去施策の参照データ、ケースログ
- `.claude/skills/` — Claude Code用のマーケティング特化スキル集（広告・SEO・コピーライティング等）

## 運用方針

- 各施策・ドキュメントは該当フォルダ配下にMarkdownやスクリプトとして追加していく
- 校舎別・施策別にサブフォルダを作成して整理する
- 機密性の高い情報（顧客個人情報、APIキー等）はコミットしない
- 過去セッションの経緯・移植状況は `docs/operations/session-history.md` を参照
