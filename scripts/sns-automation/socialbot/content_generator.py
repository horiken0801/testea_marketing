from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .config import Config
from .queue import QueueItem
from .strategy import load_strategy

JST = ZoneInfo("Asia/Tokyo")

X_MAX_CHARS = 260  # Xの280字上限からハッシュタグ分の余白を確保
THREADS_MAX_CHARS = 480

SYSTEM_PROMPT = """あなたはSNS運用担当のコピーライターです。
与えられたトーンとトピックに沿って、{platform}向けの投稿文を1件だけ日本語で作成してください。
- 誇張や事実と異なる断定は避ける
- 絵文字は使っても0〜2個まで
- 出力は投稿文の本文のみ。前置きや説明、引用符は不要
"""


def _fallback_text(platform: str, topic: str, tone: str) -> str:
    max_chars = X_MAX_CHARS if platform == "x" else THREADS_MAX_CHARS
    text = f"【{topic}】について発信します。{tone}".strip()
    return text[:max_chars]


def _generate_with_claude(config: Config, platform: str, topic: str, tone: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=config.anthropic_api_key)
    max_chars = X_MAX_CHARS if platform == "x" else THREADS_MAX_CHARS
    message = client.messages.create(
        model=config.anthropic_model,
        max_tokens=300,
        system=SYSTEM_PROMPT.format(platform=platform.upper()),
        messages=[
            {
                "role": "user",
                "content": (f"トピック: {topic}\nトーン: {tone}\n文字数上限: {max_chars}文字"),
            }
        ],
    )
    text = "".join(block.text for block in message.content if block.type == "text").strip()
    return text[:max_chars]


def _next_slot(posting_times: list[str], existing_count: int) -> datetime:
    now = datetime.now(JST)
    slots = posting_times or ["12:00"]
    day_offset, slot_index = divmod(existing_count, len(slots))
    hour, minute = (int(x) for x in slots[slot_index].split(":"))
    target_date = now + timedelta(days=day_offset + 1)
    return target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)


def generate_posts(config: Config, platform: str, count: int) -> list[QueueItem]:
    strategy = load_strategy()
    topics = strategy.get("topics") or [{"name": "お知らせ", "weight": 1.0}]
    tone = strategy.get("tone", "")
    posting_times = strategy.get("posting_times", {}).get(platform, [])
    hashtags = strategy.get("hashtags", {}).get(platform, [])

    items: list[QueueItem] = []
    for i in range(count):
        topic = topics[i % len(topics)]["name"]
        if config.anthropic_api_key:
            text = _generate_with_claude(config, platform, topic, tone)
        else:
            text = _fallback_text(platform, topic, tone)
        if hashtags:
            text = f"{text}\n\n{' '.join(hashtags)}"

        scheduled = _next_slot(posting_times, i)
        items.append(
            QueueItem(
                platform=platform,
                text=text,
                scheduled_time=scheduled.isoformat(),
                topic=topic,
            )
        )
    return items
