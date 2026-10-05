from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PostMetrics:
    post_id: str
    text: str
    created_at: str
    likes: int
    replies: int
    reposts: int
    views: int | None = None

    @property
    def engagement(self) -> int:
        return self.likes + self.replies + self.reposts


class Platform(ABC):
    name: str

    @abstractmethod
    def post(self, text: str) -> str:
        """Publish text and return the platform's post id."""

    @abstractmethod
    def recent_metrics(self, limit: int = 20) -> list[PostMetrics]:
        """Fetch metrics for the account's most recent posts."""
