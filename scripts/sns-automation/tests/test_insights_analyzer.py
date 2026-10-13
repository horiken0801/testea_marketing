from __future__ import annotations

from socialbot.insights_analyzer import _best_hour
from socialbot.platforms.base import PostMetrics


def test_best_hour_picks_hour_with_highest_average_engagement() -> None:
    metrics = [
        PostMetrics(
            post_id="1",
            text="a",
            created_at="2026-08-10T00:00:00+00:00",  # 09:00 JST
            likes=10,
            replies=5,
            reposts=1,
        ),
        PostMetrics(
            post_id="2",
            text="b",
            created_at="2026-08-11T09:00:00+00:00",  # 18:00 JST
            likes=1,
            replies=0,
            reposts=0,
        ),
    ]

    assert _best_hour(metrics) == "09:00"


def test_best_hour_returns_none_for_empty_metrics() -> None:
    assert _best_hour([]) is None
