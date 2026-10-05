from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from socialbot.queue import QueueItem, add_items, due_items, load_queue, save_queue


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "queue.json"
    item = QueueItem(
        platform="x", text="hello", scheduled_time=datetime.now(timezone.utc).isoformat()
    )
    save_queue([item], path=path)

    loaded = load_queue(path=path)
    assert len(loaded) == 1
    assert loaded[0].text == "hello"
    assert loaded[0].id == item.id


def test_add_items_appends(tmp_path: Path) -> None:
    path = tmp_path / "queue.json"
    save_queue([], path=path)
    item = QueueItem(
        platform="threads", text="a", scheduled_time=datetime.now(timezone.utc).isoformat()
    )
    add_items([item], path=path)

    assert len(load_queue(path=path)) == 1


def test_due_items_filters_future_and_non_pending() -> None:
    now = datetime.now(timezone.utc)
    past = QueueItem(platform="x", text="past", scheduled_time=(now - timedelta(hours=1)).isoformat())
    future = QueueItem(
        platform="x", text="future", scheduled_time=(now + timedelta(hours=1)).isoformat()
    )
    posted = QueueItem(
        platform="x",
        text="posted",
        scheduled_time=(now - timedelta(hours=2)).isoformat(),
        status="posted",
    )

    due = due_items([past, future, posted], now=now)

    assert [item.text for item in due] == ["past"]
