# 過去セッション履歴（資産移植ログ）

このリポジトリが空の状態から構築される以前、複数のリポジトリ（`test`→リネーム後`testea_marketing`、`centerminami_newopen`）やClaude Codeセッションに分散して行われていたマーケティング業務の履歴。2026/10/5時点で確認できた範囲をここに記録する。

## 本リポジトリに資産を移植済み

| 施策 | 元のブランチ/場所 | 移植先 |
| --- | --- | --- |
| 秋期キャンペーン（中学受験準備応援） | `claude/awesome-fermat-r8kkcq` | `docs/campaigns/autumn-2026/` |
| 久我山校 競合対策キャンペーン | `claude/determined-brown-x5u465`（ブランチ削除済み、セッション記録から復元） | `docs/campaigns/kugayama-competitive-2026/` |
| センター南校 新規開校ページ・チラシ戦略・駅広告検討 | `centerminami_newopen` main / `claude/center-minami-flyer-strategy-aha8x4` / `docs/station-ad-planning` | `docs/campaigns/center-minami/` |
| SATORI顧客データフラグ連携 | `claude/sweet-edison-w377wj` | `scripts/satori_sync/` |
| X/Threads自動運用ボット | `claude/x-threads-automation-wy4idh` | `scripts/sns-automation/` |
| 広告キーワード除外（商標保護） | セッション記録から復元（コミットなし） | `docs/ads/trademark-exclusion-keywords.md` |
| マーケティング特化スキル集（Claude Code用） | `claude/testea-marketing-repo-e88iiv` | `.claude/skills/` |

## ブランチが削除済み・資産を復元できなかった/未着手のもの

以下はセッション記録（タイトル・要約）は残っているが、対応するgitブランチが削除済み、またはそもそも成果物がコミットされていなかったため、本リポジトリへの移植ができていない。必要な場合は該当セッションの会話ログを個別に確認すること。

| セッション | 概要 | 備考 |
| --- | --- | --- |
| Google広告ロケーションマネージャーのアドレス変更 | ロケーション設定の調査中で終了（screenshot待ち） | 成果物なし |
| 下半期運用カレンダーと配信文章 | 配信文章v5まで作成、旧版ドキュメントの削除可否が保留 | ブランチ`claude/pensive-newton-ae0d7i`削除済み |
| センター南駅広告 | 駅広告の企画をcenterminami_newopenに提出済み | `docs/station-ad-planning`として移植済み（上表参照） |
| 塾マーケティング業務統合（日報作成） | 日報文面の継続作成（定常業務） | 定型業務のため資産化せず |
| 堀内のタスク整理 | ガントチャート（Artifact）を作成 | Artifactのみ、リポジトリ資産なし |
| X / Threads の自動運用（旧版） | DM対応ケースログ等を追加 | `scripts/sns-automation/`として移植済み（上表参照） |
| ページのnoindex設定 | noindex設定の下書き運用、完全削除は保留中 | ブランチ`claude/noindex-page-hiding-p2luvd`削除済み |
| 新校舎ページ作成（センター南校） | デザイン修正対応 | `docs/campaigns/center-minami/`として移植済み（上表参照） |
| Claude APIキー発行 | API発行手順の説明のみ | 資産化対象外 |
| データ参考性の確認 | データ活用の3方向性（ダッシュボード/異常検知/相関分析）を提案中、未決定 | 要継続検討 |

## 今後の方針

- 新しい施策は最初からこのリポジトリの該当フォルダに資産を作成し、セッション側のブランチに依存しない運用にする
- 社内の意思決定・承認フロー（Slack `#006_マーケティング部` 等）に関わる機密情報の濃いメモは、リポジトリにそのまま転記せず、必要なエッセンスのみ抜粋して記録する
