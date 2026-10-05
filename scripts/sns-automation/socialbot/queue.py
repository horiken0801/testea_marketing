from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from . import config as cfg

Status = Literal["pending", "posted", "failed", "skipped"]


@dataclass
class QueueItem:
    platform: str
    text: str
    scheduled_time: str
    topic: str = ""
    status: Status = "pending"
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    posted_at: str | None = None
    post_id: str | None = None
    source: str = "auto-generated"
    error: str | None = None


def load_queue(path: Path | None = None) -> list[QueueItem]:
    path = path or cfg.QUEUE_PATH
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        raw_items = json.load(f).get("items", [])
    return [QueueItem(**item) for item in raw_items]


def save_queue(items: list[QueueItem], path: Path | None = None) -> None:
    path = path or cfg.QUEUE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump({"items": [asdict(i) for i in items]}, f, ensure_ascii=False, indent=2)
        f.write("\n")


def add_items(new_items: list[QueueItem], path: Path | None = None) -> None:
    items = load_queue(path)
    items.extend(new_items)
    save_queue(items, path)


def due_items(items: list[QueueItem], now: datetime | None = None) -> list[QueueItem]:
    now = now or datetime.now(timezone.utc)
    due = []
    for item in items:
        if item.status != "pending":
            continue
        scheduled = datetime.fromisoformat(item.scheduled_time)
        if scheduled <= now:
            due.append(item)
    return due
