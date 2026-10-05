# X / Threads 自動運用ボット

X（旧Twitter）とThreadsの運用を支援するツールキットです。現在は **Threads / X 共通の軽量版（中学受験トレンド分析＋下書き生成）** を運用中で、自動投稿を含むフル自動運用の仕組みは一旦保留しています（後述）。

## 今すぐ使える機能: トレンド下書き生成（中学受験）

「中学受験」に関する直近のトレンド・話題をWeb検索で調査し、インサイトを添えた投稿文と推奨投稿日時の下書きを自動生成します。**自動投稿はせず、下書き出力までを行い、投稿は手動**で行う想定です。ThreadsとXそれぞれに専用のスクリプト・設定ファイル・出力先がありますが、ロジック本体（`socialbot/trend_drafts.py`）は共通です。

| | Threads | X |
| --- | --- | --- |
| 実行スクリプト | `scripts/draft_threads_posts.py` | `scripts/draft_x_posts.py` |
| 定期実行ワークフロー | `.github/workflows/threads-trend-drafts.yml`（毎週火・金 07:00 JST） | `.github/workflows/x-trend-drafts.yml`（毎週水・土 07:00 JST） |
| 出力先 | `drafts/threads/YYYY-MM-DD_HHMM.md` / `.json` | `drafts/x/YYYY-MM-DD_HHMM.md` / `.json` |
| 設定ファイル | `data/threads_juken_config.json` | `data/x_juken_config.json` |
| 文字数上限 | 480字 | 260字（280字上限に余白） |

- 参考データ: `data/reference/` に `.md` / `.txt` を置くと、**Threads・X両方の生成で共通して**読み込まれます（過去投稿の反応メモ、DMログ、投稿ルールなど）
- `data/reference_x/` は **X専用**の参考データ置き場です（`draft_x_posts.py` のみが読み込み、Threads側には渡りません）。X運用の指示書（カテゴリ設計・KPI・禁止事項・HP誘導の実在URL一覧など）や、Xアカウント自体の直近実績はこちらに置きます
- ただし文面はプラットフォームごとに**毎回新規で作成**します。Threadsの投稿文をXに転用したり、その逆をしたりはしません（`data/reference/` 側の内容は「保護者がどんな言葉に反応しやすいか」という関心の強さのシグナルとして使うのみ）
- Xの投稿文中でHPへ誘導する場合、`data/reference_x/x_operation_prompt.md` に載っている実在URL一覧に無いリンクはコード側（`socialbot/trend_drafts.py`）で自動的に除去されます（存在しないURLを捏造しないためのガード）
- 定期実行の曜日はThreadsとXでずらしてあります（生成タイミングの分散のため。同時に実行しても問題はありません）

### 必要なもの

- `ANTHROPIC_API_KEY`（Claude API。Web検索ツールを使ってトレンド調査を行うために必須）
- X API / Threads APIキーは **不要**（下書き生成のみのため）

GitHub Secretsに `ANTHROPIC_API_KEY` を登録すれば、各ワークフローのスケジュール実行または手動実行（Actionsタブ > workflow_dispatch）で下書きが `drafts/threads/` または `drafts/x/` にコミットされます。生成された `.md` を確認し、内容に問題なければ手動で投稿してください。

### ローカルでの動作確認

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export ANTHROPIC_API_KEY=sk-ant-...

python scripts/draft_threads_posts.py   # drafts/threads/ に .md と .json が生成される
python scripts/draft_x_posts.py         # drafts/x/ に .md と .json が生成される

pytest  # ネットワーク接続不要のユニットテスト
```

### 項目の分け方について

調査（トレンド分析）と文面生成は1回のAPI呼び出しの中でまとめて行っています。出力（Markdown/JSON）の中で候補トピックごとに項目を分けているので、パイプライン自体を分割しなくてもレビューはしやすい構成です。プラットフォームの違いは `socialbot/trend_drafts.py` 内の文字数上限・プロンプト文言の切り替えで吸収しており、スクリプト・設定ファイル・出力先だけをプラットフォームごとに分けています。

---

## 保留中: フル自動運用（X / Threads 自動投稿・実績分析）

以前に構築した、X・Threads両方への自動投稿＋実績に基づく戦略自動更新の仕組みも残しています。現時点では「ライトに始めたい」という方針のため、該当ワークフローの `schedule` トリガーはコメントアウトして停止していますが、`workflow_dispatch` による手動実行や、必要になった際の再開は可能です。

1. **コンテンツ自動生成**: 戦略ファイル（`data/strategy.json`）のトピック・トーンに沿って投稿文をAIで生成し、`content_queue/queue.json` に予約投稿として積む
2. **予約投稿・自動投稿**: キューの中で投稿時刻が来たものをX / Threadsそれぞれに自動投稿する
3. **インサイト分析**: 直近の投稿の反応（いいね・返信・リポスト等）をX/Threads APIから取得し、傾向から仮説を立てて `data/strategy.json` にフィードバックする

再開する場合は `.github/workflows/generate-content.yml` / `publish-posts.yml` / `analyze-insights.yml` 内の `schedule:` のコメントを外し、X/Threads両方のAPIキーをGitHub Secretsに設定してください（詳細は下記「APIキーの取得」参照）。

## 構成

```
socialbot/
  config.py                    # 環境変数・パス設定
  trend_drafts.py               # [軽量版] トレンド調査＋下書き生成ロジック（Threads/X共通）
  queue.py                      # [保留中] 投稿キューの読み書き
  strategy.py                   # [保留中] 戦略ファイルの読み書き
  content_generator.py          # [保留中] 投稿文の自動生成
  insights_analyzer.py          # [保留中] 投稿実績の分析と戦略ファイルへの反映
  platforms/
    x.py                        # [保留中] X API v2 クライアント
    threads.py                  # [保留中] Threads API クライアント（自動投稿用）
scripts/
  draft_threads_posts.py        # [軽量版] Threads下書き生成CLI
  draft_x_posts.py               # [軽量版] X下書き生成CLI
  generate_content.py           # [保留中] コンテンツ生成CLI
  publish_posts.py              # [保留中] 予約投稿の実行CLI
  analyze_insights.py           # [保留中] インサイト分析CLI
data/
  threads_juken_config.json     # [軽量版] Threads向けトーン・ターゲット層等の設定
  x_juken_config.json            # [軽量版] X向けトーン・ターゲット層等の設定
  reference/                    # [軽量版] ユーザー提供の参考データ置き場（Threads/X共通）
  reference_x/                  # [軽量版] X専用の参考データ置き場（運用指示書・X自身の実績）
  strategy.json                 # [保留中] 運用戦略
  insights_history/             # [保留中] 分析結果のスナップショット
content_queue/
  queue.json                    # [保留中] 投稿キュー
drafts/
  threads/                      # [軽量版] Threads向け生成済み下書き（.md / .json）
  x/                             # [軽量版] X向け生成済み下書き（.md / .json）
.github/workflows/               # GitHub Actions定期実行の定義
tests/                           # pytestによるユニットテスト（ネットワーク非依存）
```

## APIキーの取得

### Claude API（軽量版で必須）

https://console.anthropic.com/ でAPIキーを発行し、`ANTHROPIC_API_KEY` として登録してください。

### X (Twitter) API（保留中の機能を使う場合のみ）

1. https://developer.x.com/en/portal/dashboard で開発者アカウントを作成し、アプリを作成
2. アプリの権限を **Read and Write** に設定（投稿するため）
3. 「Keys and tokens」から以下を発行
   - API Key / API Key Secret（Consumer Key/Secret）
   - Access Token / Access Token Secret（アプリの権限をRead and Writeにしてから発行すること）
4. 投稿頻度によっては有料プラン（Basic以上）が必要な場合があります

### Threads API（保留中の機能を使う場合のみ）

1. https://developers.facebook.com/ でMetaアプリを作成し、「Threads API」プロダクトを追加
2. 対象のThreadsアカウントを認可し、`threads_basic` `threads_content_publish` `threads_manage_insights` のスコープでアクセストークンを取得
3. 短期トークンを長期トークン（約60日）に交換し、`THREADS_ACCESS_TOKEN` に設定
4. トークンに紐づく `threads_user_id` を取得して `THREADS_USER_ID` に設定
5. 長期トークンは60日で失効するため、定期的な更新運用が必要です

## GitHub Secretsの設定

| Secret名 | 用途 | 現時点で必要か |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | Threads/X下書き生成（Web検索によるトレンド調査） | ✅ 必須 |
| `X_API_KEY` / `X_API_SECRET` / `X_ACCESS_TOKEN` / `X_ACCESS_TOKEN_SECRET` | X自動投稿・指標取得（保留中） | 不要 |
| `THREADS_ACCESS_TOKEN` / `THREADS_USER_ID` | Threads自動投稿・インサイト取得（保留中） | 不要 |

`ANTHROPIC_MODEL` はSecretではなくVariablesに設定すると各ワークフローから参照されます。未設定時は `claude-sonnet-5` を使用します。

## 注意事項

- 各プラットフォームの自動化・スパム防止ポリシーを順守してください
- Threadsの長期アクセストークンは約60日で失効します（保留中機能を使う場合）
- `data/reference/` に置いた参考データはリポジトリにコミットされるため、機密情報は含めないでください
- Xについてはまだ実投稿の実績データがありません。`data/reference/` の内容は現状ほぼThreads実績のため、X向け下書きは「関心の強さの参考」程度に留め、実際に投稿して反応を見ながら育てていく想定です
