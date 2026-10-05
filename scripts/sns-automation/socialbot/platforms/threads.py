from __future__ import annotations

import time

import requests

from ..config import Config
from .base import Platform, PostMetrics

GRAPH_BASE = "https://graph.threads.net/v1.0"

# Threads needs a short delay between creating a media container and publishing
# it while the container finishes processing server-side.
_PUBLISH_DELAY_SECONDS = 5


class ThreadsClient(Platform):
    """Thin wrapper around the Threads API (Meta Graph API) for text posts and insights."""

    name = "threads"

    def __init__(self, config: Config):
        if not config.threads_enabled:
            raise RuntimeError("Threads API credentials are not fully configured")
        self._token = config.threads_access_token
        self._user_id = config.threads_user_id

    def post(self, text: str) -> str:
        container = requests.post(
            f"{GRAPH_BASE}/{self._user_id}/threads",
            data={"media_type": "TEXT", "text": text, "access_token": self._token},
            timeout=30,
        )
        container.raise_for_status()
        creation_id = container.json()["id"]

        time.sleep(_PUBLISH_DELAY_SECONDS)

        publish = requests.post(
            f"{GRAPH_BASE}/{self._user_id}/threads_publish",
            data={"creation_id": creation_id, "access_token": self._token},
            timeout=30,
        )
        publish.raise_for_status()
        return str(publish.json()["id"])

    def recent_metrics(self, limit: int = 20) -> list[PostMetrics]:
        listing = requests.get(
            f"{GRAPH_BASE}/{self._user_id}/threads",
            params={
                "fields": "id,text,timestamp",
                "limit": max(5, min(limit, 100)),
                "access_token": self._token,
            },
            timeout=30,
        )
        listing.raise_for_status()

        metrics: list[PostMetrics] = []
        for item in listing.json().get("data", []):
            insight = requests.get(
                f"{GRAPH_BASE}/{item['id']}/insights",
                params={"metric": "likes,replies,reposts,views", "access_token": self._token},
                timeout=30,
            )
            insight.raise_for_status()
            values = {
                row["name"]: row["values"][0]["value"] for row in insight.json().get("data", [])
            }
            metrics.append(
                PostMetrics(
                    post_id=item["id"],
                    text=item.get("text", ""),
                    created_at=item.get("timestamp", ""),
                    likes=values.get("likes", 0),
                    replies=values.get("replies", 0),
                    reposts=values.get("reposts", 0),
                    views=values.get("views"),
                )
            )
        return metrics
