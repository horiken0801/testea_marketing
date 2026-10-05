from __future__ import annotations

from socialbot.config import Config
from socialbot.content_generator import X_MAX_CHARS, generate_posts


def test_generate_posts_falls_back_to_template_without_anthropic_key(monkeypatch) -> None:
    monkeypatch.setattr("socialbot.content_generator.load_strategy", lambda: {
        "tone": "テストトーン",
        "topics": [{"name": "テストトピック", "weight": 1.0}],
        "posting_times": {"x": ["09:00"]},
        "hashtags": {"x": ["#test"]},
    })

    config = Config(anthropic_api_key=None)
    items = generate_posts(config, "x", count=2)

    assert len(items) == 2
    assert all(item.platform == "x" for item in items)
    assert all(len(item.text) <= X_MAX_CHARS + len("\n\n#test") for item in items)
    assert all("#test" in item.text for item in items)
    assert items[0].scheduled_time != items[1].scheduled_time
