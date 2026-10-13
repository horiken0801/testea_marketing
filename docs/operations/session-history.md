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

## 2026-10-13: mainブランチへの統合

上記の資産移植（`claude/nifty-ptolemy-5axa0c`）は、ブランチ上で作られたまま一度も`main`にマージされていなかった。`testea_marketing`・`centerminami_newopen`いずれも、未マージの作業用ブランチが複数残った状態になっていたため、2026-10-13にすべて調査し、`main`へ統合した。

| リポジトリ | 未マージブランチ | 統合内容 |
| --- | --- | --- |
| testea_marketing | `claude/nifty-ptolemy-5axa0c` | 資産移植の本体（スキル・campaigns・scripts一式）。mainのベースとして採用 |
| testea_marketing | `claude/new-session-j9ruh0` | 秋キャンバナーデザイン案(ver.2) → `docs/campaigns/autumn-2026/design-proposals/` |
| testea_marketing | `claude/x-threads-automation-wy4idh` | sns-automationの10/7時点の最新ドラフト・分析結果（nifty-ptolemyより新しい差分のみ） |
| testea_marketing | `claude/awesome-fermat-r8kkcq` / `claude/sweet-edison-w377wj` / `claude/testea-center-minami-page-xfod2q` / `claude/testea-marketing-repo-e88iiv` | 内容を確認し、nifty-ptolemyへ完全に吸収済みであることを確認（追加作業なし） |

また、同日にGoogle Apps Script側で見つかった不具合修正（元在がタグ対象から漏れる問題。詳細は`scripts/satori_sync/gas/README.md`の「既知の修正履歴」）を、本リポジトリの`SatoriLogic.gs`/`SatoriSync.gs`にも反映した。これはApps Scriptエディタ上で先に直接修正・検証した内容を、事後的にリポジトリ側のコピーにも反映したもの。

### 2026-10-05〜10-09 の追加セッション（資産化状況）

| セッション | 概要 | 資産化 |
| --- | --- | --- |
| 顧客データフラグ連携 SATORI（継続） | 誤送信防止の手動チェック、元在タグ漏れの原因調査・修正 | `scripts/satori_sync/gas/README.md`に記録済み |
| テスティーの広告キーワード除外 | 商標保護のための除外キーワード検討 | `docs/ads/trademark-exclusion-keywords.md`として既に移植済み |
| 秋キャンペーン進行管理 | 秋キャン進行状況の管理 | `docs/campaigns/autumn-2026/`に該当（個別の資産追加なし） |
| データ参考性の確認 | データ活用の3方向性を検討（未決定、継続検討） | 資産化せず（検討中のため） |
| リポリトジの作成 | リポジトリ構成自体の整備作業 | 本統合作業の前段 |
| SEO/MEO順位確認の自動化 | 順位確認作業の自動化を検討 | 未着手（継続として記録） |
| テスティー問い合わせ計測シート | 問い合わせ計測シートの整備 | Googleスプレッドシート側で管理（リポジトリ資産化なし） |
| Zoom 録音機能 | Zoom録音機能の確認 | 資産化対象外 |
| センター南校 タスク洗い出し | センター南開校に向けたタスク洗い出し、LPのArtifact化 | `docs/campaigns/center-minami/`に該当（Artifact自体はリポジトリ外） |

## 今後の方針

- 新しい施策は最初からこのリポジトリの該当フォルダに資産を作成し、セッション側のブランチに依存しない運用にする
- 社内の意思決定・承認フロー（Slack `#006_マーケティング部` 等）に関わる機密情報の濃いメモは、リポジトリにそのまま転記せず、必要なエッセンスのみ抜粋して記録する
- **作業用ブランチで資産を作ったら、その場でmainにマージ（またはPR作成）する。ブランチに置いたままにしない**（今回、複数のブランチが未マージのまま残っていたことが「リポジトリが空に見える」混乱の直接の原因になったため）
