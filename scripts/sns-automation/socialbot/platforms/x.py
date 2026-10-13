from __future__ import annotations

import tweepy

from ..config import Config
from .base import Platform, PostMetrics


class XClient(Platform):
    """Thin wrapper around the X (Twitter) API v2 for posting and reading own-tweet metrics."""

    name = "x"

    def __init__(self, config: Config):
        if not config.x_enabled:
            raise RuntimeError("X API credentials are not fully configured")
        self._client = tweepy.Client(
            consumer_key=config.x_api_key,
            consumer_secret=config.x_api_secret,
            access_token=config.x_access_token,
            access_token_secret=config.x_access_token_secret,
        )
        self._user_id: str | None = None

    def _me(self) -> str:
        if self._user_id is None:
            self._user_id = str(self._client.get_me().data.id)
        return self._user_id

    def post(self, text: str) -> str:
        response = self._client.create_tweet(text=text)
        return str(response.data["id"])

    def recent_metrics(self, limit: int = 20) -> list[PostMetrics]:
        user_id = self._me()
        response = self._client.get_users_tweets(
            id=user_id,
            max_results=max(5, min(limit, 100)),
            tweet_fields=["created_at", "public_metrics", "text"],
        )
        metrics: list[PostMetrics] = []
        for tweet in response.data or []:
            pm = tweet.public_metrics or {}
            metrics.append(
                PostMetrics(
                    post_id=str(tweet.id),
                    text=tweet.text,
                    created_at=str(tweet.created_at),
                    likes=pm.get("like_count", 0),
                    replies=pm.get("reply_count", 0),
                    reposts=pm.get("retweet_count", 0),
                    views=pm.get("impression_count"),
                )
            )
        return metrics
