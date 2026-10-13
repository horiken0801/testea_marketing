#!/usr/bin/env python3
"""Generate draft posts for X and/or Threads and add them to the content queue."""
from __future__ import annotations

import argparse

from socialbot.config import load_config
from socialbot.content_generator import generate_posts
from socialbot.queue import add_items


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate queued posts for X and/or Threads")
    parser.add_argument("--platform", choices=["x", "threads", "both"], default="both")
    parser.add_argument("--count", type=int, default=3, help="Posts to generate per platform")
    args = parser.parse_args()

    config = load_config()
    platforms = ["x", "threads"] if args.platform == "both" else [args.platform]

    generated = []
    for platform in platforms:
        items = generate_posts(config, platform, args.count)
        generated.extend(items)
        print(f"Generated {len(items)} draft(s) for {platform}")

    if generated:
        add_items(generated)
        print(f"Added {len(generated)} item(s) to the queue")
    else:
        print("No items generated")


if __name__ == "__main__":
    main()
