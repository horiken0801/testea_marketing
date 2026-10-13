from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
QUEUE_DIR = REPO_ROOT / "content_queue"
STRATEGY_PATH = DATA_DIR / "strategy.json"
QUEUE_PATH = QUEUE_DIR / "queue.json"
INSIGHTS_HISTORY_DIR = DATA_DIR / "insights_history"


@dataclass(frozen=True)
class Config:
    x_api_key: str | None = field(default_factory=lambda: os.getenv("X_API_KEY"))
    x_api_secret: str | None = field(default_factory=lambda: os.getenv("X_API_SECRET"))
    x_access_token: str | None = field(default_factory=lambda: os.getenv("X_ACCESS_TOKEN"))
    x_access_token_secret: str | None = field(
        default_factory=lambda: os.getenv("X_ACCESS_TOKEN_SECRET")
    )

    threads_access_token: str | None = field(
        default_factory=lambda: os.getenv("THREADS_ACCESS_TOKEN")
    )
    threads_user_id: str | None = field(default_factory=lambda: os.getenv("THREADS_USER_ID"))

    anthropic_api_key: str | None = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    anthropic_model: str = field(
        default_factory=lambda: os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
    )

    @property
    def x_enabled(self) -> bool:
        return all(
            [self.x_api_key, self.x_api_secret, self.x_access_token, self.x_access_token_secret]
        )

    @property
    def threads_enabled(self) -> bool:
        return all([self.threads_access_token, self.threads_user_id])


def load_config() -> Config:
    return Config()
