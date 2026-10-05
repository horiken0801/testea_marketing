from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .config import Config

JST = ZoneInfo("Asia/Tokyo")

# Xの280字上限からURL等の余白を確保、Threadsは実質上限に近い値を使用
PLATFORM_MAX_CHARS = {
    "threads": 480,
    "x": 260,
}
PLATFORM_LABELS = {
    "threads": "Threads",
    "x": "X（旧Twitter）",
}

_RESULT_PATTERN = re.compile(r"<result>(.*?)</result>", re.DOTALL)
_URL_PATTERN = re.compile(r"https?://[^\s\)\]。、>]+")


class DraftParseError(RuntimeError):
    """Raised when Claude's response doesn't contain the expected <result> JSON block."""

    def __init__(self, message: str, raw_text: str):
        super().__init__(message)
        self.raw_text = raw_text


@dataclass
class DraftPost:
    topic: str
    insight: str
    post_text: str
    suggested_datetime: str
    reasoning: str
    sources: list[str]
    # 以下はカテゴリ制・URL誘導のあるプラットフォーム(Xなど)向けの任意項目。
    # 使わないプラットフォームでは空文字のまま。
    category: str = ""
    expected_engagement: str = ""
    destination_url: str = ""


def load_juken_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_reference_notes(reference_dirs: list[Path]) -> str:
    """Concatenate user-supplied .md/.txt files (excluding README) across one or more dirs."""
    chunks = []
    for reference_dir in reference_dirs:
        if not reference_dir.exists():
            continue
        for path in sorted(reference_dir.glob("*")):
            if path.suffix.lower() not in {".md", ".txt"}:
                continue
            if path.stem.upper() == "README":
                continue
            text = path.read_text(encoding="utf-8").strip()
            if text:
                chunks.append(f"### {path.name}\n{text}")
    return "\n\n".join(chunks)


def _known_urls(reference_notes: str) -> set[str]:
    return {url.rstrip(".,);） 、。") for url in _URL_PATTERN.findall(reference_notes)}


def build_prompt(platform: str, juken_config: dict, reference_notes: str, today: datetime) -> str:
    max_chars = PLATFORM_MAX_CHARS[platform]
    platform_label = PLATFORM_LABELS[platform]

    posts_per_run = juken_config.get("posts_per_run", 3)
    audience = juken_config.get("audience", "")
    tone = juken_config.get("tone", "")
    hashtags = juken_config.get("hashtags", [])
    topic_area = juken_config.get("topic_area", "中学受験")

    hashtags_line = (
        f"\n使用可能なハッシュタグ(任意、使う場合は文末に1〜2個まで): {' '.join(hashtags)}"
        if hashtags
        else ""
    )
    reference_block = (
        f"\n\n# 参考情報(ユーザー提供、可能であれば内容に反映してください)\n{reference_notes}\n"
        if reference_notes
        else ""
    )
    cross_platform_note = (
        "\n注意: 上記の参考情報には複数のプラットフォームのデータが混在している場合があります。"
        "各ファイルの冒頭にどのプラットフォームのデータかが明記されているので確認してください。"
        f"{platform_label}自身の実績データや運用ルールがあれば最優先で従い、他プラットフォームの"
        "データは『保護者がどんな言葉に反応しやすいか』という関心の強さの参考程度に留めてください。"
        f"いずれの場合も、投稿文は他プラットフォームの文面をそのまま流用・要約せず、"
        f"{platform_label}の文化・文字数に合わせて毎回新規で考えてください。"
        if reference_notes
        else ""
    )

    return f"""あなたは「{topic_area}」領域に詳しいSNS運用担当者です。
Web検索を使って、直近の{topic_area}に関するトレンドや話題(ニュース、SNSでの反応、時期的トピックなど)を調査してください。

本日の日付: {today:%Y-%m-%d}(JST)

投稿先: {platform_label}
ターゲット層: {audience}
文体・トーン: {tone}{hashtags_line}
{reference_block}{cross_platform_note}
調査結果をもとに、{platform_label}投稿の下書きを{posts_per_run}件作成してください。各下書きについて次の項目を用意してください。
- topic: 調査で見つけた具体的なトピック
- insight: そのトピックが今なぜ話題/重要なのか、ターゲット層のどんな関心・不安に刺さるかというインサイト
- post_text: {platform_label}投稿文({max_chars}文字以内。誇張や不確かな断定は避け、事実は調査結果に基づくこと。絵文字は0〜2個まで)
- suggested_datetime: 投稿に適した日時(ISO8601形式、JST、本日から2週間以内。参考情報に曜日・時間帯ごとの実績や運用ルールがあればそれに従うこと)
- reasoning: その日時・内容を提案する理由
- sources: 調査で参照した情報源のURL(配列)
- category: 投稿カテゴリ(参考情報にカテゴリ分類の指定がある場合のみ使用。なければ空文字)
- expected_engagement: 想定される反応の目安(参考情報にKPIやインプレッション目標の指定がある場合のみ使用。なければ空文字)
- destination_url: 投稿文中でリンク誘導する場合の誘導先URL(参考情報に許可された誘導先URL一覧がある場合は必ずその中から選ぶこと。存在しないURLを作らない。URL誘導を行わない、または一覧がない場合は空文字のままにする)

必ず最後に、他のテキストを含めず <result> タグの中にJSON配列のみを出力してください。フォーマット:
<result>
[
  {{
    "topic": "...",
    "insight": "...",
    "post_text": "...",
    "suggested_datetime": "2026-08-20T12:30:00+09:00",
    "reasoning": "...",
    "sources": ["https://..."],
    "category": "",
    "expected_engagement": "",
    "destination_url": ""
  }}
]
</result>
"""


def extract_json(text: str) -> list[dict]:
    match = _RESULT_PATTERN.search(text)
    if not match:
        raise DraftParseError("Claudeの応答から <result> タグを検出できませんでした", text)
    try:
        return json.loads(match.group(1).strip())
    except json.JSONDecodeError as exc:
        raise DraftParseError(f"<result> 内のJSON解析に失敗しました: {exc}", text) from exc


def call_claude_research(config: Config, prompt: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=config.anthropic_api_key)
    message = client.messages.create(
        model=config.anthropic_model,
        max_tokens=4096,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(
        block.text for block in message.content if getattr(block, "type", None) == "text"
    )


def research_and_draft(
    config: Config, platform: str, juken_config_path: Path, reference_dirs: list[Path]
) -> tuple[list[DraftPost], str]:
    if platform not in PLATFORM_MAX_CHARS:
        raise ValueError(f"未対応のプラットフォームです: {platform}")
    if not config.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY が設定されていません")

    max_chars = PLATFORM_MAX_CHARS[platform]
    juken_config = load_juken_config(juken_config_path)
    reference_notes = load_reference_notes(reference_dirs)
    known_urls = _known_urls(reference_notes) if reference_notes else set()
    today = datetime.now(JST)
    prompt = build_prompt(platform, juken_config, reference_notes, today)

    full_text = call_claude_research(config, prompt)
    raw_items = extract_json(full_text)

    drafts = []
    for item in raw_items:
        destination_url = item.get("destination_url", "") or ""
        if destination_url and known_urls and destination_url not in known_urls:
            # 参考情報のURL一覧に無い(=捏造の疑いがある)リンクは落とす
            destination_url = ""
        drafts.append(
            DraftPost(
                topic=item.get("topic", ""),
                insight=item.get("insight", ""),
                post_text=item.get("post_text", "")[:max_chars],
                suggested_datetime=item.get("suggested_datetime", ""),
                reasoning=item.get("reasoning", ""),
                sources=item.get("sources", []),
                category=item.get("category", "") or "",
                expected_engagement=item.get("expected_engagement", "") or "",
                destination_url=destination_url,
            )
        )
    return drafts, full_text


def render_markdown(platform: str, drafts: list[DraftPost], generated_at: datetime) -> str:
    platform_label = PLATFORM_LABELS[platform]
    lines = [
        f"# {platform_label}下書き案 ({generated_at:%Y-%m-%d %H:%M} JST生成)",
        "",
        "> 自動生成された下書きです。内容を確認・修正のうえ、手動で投稿してください。",
        "",
    ]
    for i, draft in enumerate(drafts, start=1):
        lines.append(f"## {i}. {draft.topic}")
        lines.append("")

        meta_bits = [f"推奨投稿日時: {draft.suggested_datetime}"]
        if draft.category:
            meta_bits.append(f"カテゴリ: {draft.category}")
        if draft.expected_engagement:
            meta_bits.append(f"想定反応目安: {draft.expected_engagement}")
        if draft.destination_url:
            meta_bits.append(f"誘導先URL: {draft.destination_url}")
        lines.append("**" + " ｜ ".join(meta_bits) + "**")
        lines.append("")

        lines.append(f"**インサイト**: {draft.insight}")
        lines.append("")
        lines.append(f"**設計意図**: {draft.reasoning}")
        lines.append("")
        lines.append("**投稿文案**:")
        lines.append("")
        lines.append("```")
        lines.append(draft.post_text)
        lines.append("```")
        lines.append("")
        if draft.sources:
            lines.append("**参照元**:")
            for src in draft.sources:
                lines.append(f"- {src}")
            lines.append("")
    return "\n".join(lines)
