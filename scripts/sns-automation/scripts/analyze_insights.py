#!/usr/bin/env python3
"""Pull recent post metrics, derive simple hypotheses, and update the strategy file."""
from __future__ import annotations

import json

from socialbot.config import load_config
from socialbot.insights_analyzer import analyze_and_update_strategy


def main() -> None:
    config = load_config()
    if not (config.x_enabled or config.threads_enabled):
        print("No platform credentials configured; skipping insight analysis")
        return
    summary = analyze_and_update_strategy(config)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
