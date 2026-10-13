from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import config as cfg

DEFAULT_STRATEGY = {
    "updated_at": None,
    "tone": "親しみやすく簡潔な日本語。専門用語には一言だけ補足を添える。",
    "topics": [
        {"name": "業界トレンド解説", "weight": 1.0},
        {"name": "実践Tips", "weight": 1.0},
        {"name": "事例紹介", "weight": 1.0},
    ],
    "posting_times": {
        "x": ["09:00", "20:00"],
        "threads": ["12:30"],
    },
    "hashtags": {
        "x": [],
        "threads": [],
    },
    "hypotheses": [],
}


def load_strategy(path: Path | None = None) -> dict:
    path = path or cfg.STRATEGY_PATH
    if not path.exists():
        return json.loads(json.dumps(DEFAULT_STRATEGY))
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_strategy(strategy: dict, path: Path | None = None) -> None:
    path = path or cfg.STRATEGY_PATH
    strategy["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(strategy, f, ensure_ascii=False, indent=2)
        f.write("\n")
