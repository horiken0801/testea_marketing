#!/usr/bin/env python3
"""Publish any queued posts whose scheduled time has arrived."""
from __future__ import annotations

from datetime import datetime, timezone

from socialbot.config import load_config
from socialbot.platforms.threads import ThreadsClient
from socialbot.platforms.x import XClient
from socialbot.queue import due_items, load_queue, save_queue


def main() -> None:
    config = load_config()
    clients = {}
    if config.x_enabled:
        clients["x"] = XClient(config)
    if config.threads_enabled:
        clients["threads"] = ThreadsClient(config)

    items = load_queue()
    pending_due = due_items(items)
    if not pending_due:
        print("No posts due")
        return

    for item in pending_due:
        client = clients.get(item.platform)
        if client is None:
            item.status = "skipped"
            item.error = f"{item.platform} credentials not configured"
            print(f"Skipping {item.id}: {item.error}")
            continue
        try:
            post_id = client.post(item.text)
            item.status = "posted"
            item.post_id = post_id
            item.posted_at = datetime.now(timezone.utc).isoformat()
            print(f"Posted {item.id} to {item.platform} -> {post_id}")
        except Exception as exc:  # noqa: BLE001 - record failure on the item and keep going
            item.status = "failed"
            item.error = str(exc)
            print(f"Failed to post {item.id} to {item.platform}: {exc}")

    save_queue(items)


if __name__ == "__main__":
    main()
