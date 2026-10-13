#!/usr/bin/env python3
"""Research current 中学受験 trends via web search and draft X posts for manual review."""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from zoneinfo import ZoneInfo

from socialbot.config import REPO_ROOT, load_config
from socialbot.trend_drafts import DraftParseError, render_markdown, research_and_draft

JST = ZoneInfo("Asia/Tokyo")

PLATFORM = "x"
JUKEN_CONFIG_PATH = REPO_ROOT / "data" / "x_juken_config.json"
# data/reference/ はThreadsとの共有フォルダ(関心の強さの参考程度)、
# data/reference_x/ はX専用の運用プロンプト・実績データ
REFERENCE_DIRS = [REPO_ROOT / "data" / "reference", REPO_ROOT / "data" / "reference_x"]
DRAFTS_DIR = REPO_ROOT / "drafts" / "x"


def main() -> None:
    config = load_config()
    now = datetime.now(JST)
    stem = now.strftime("%Y-%m-%d_%H%M")
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        drafts, _raw_text = research_and_draft(config, PLATFORM, JUKEN_CONFIG_PATH, REFERENCE_DIRS)
    except DraftParseError as exc:
        debug_path = DRAFTS_DIR / f"{stem}.raw.txt"
        debug_path.write_text(exc.raw_text, encoding="utf-8")
        print(f"下書きの解析に失敗しました: {exc}")
        print(f"Claudeの応答全文を {debug_path.relative_to(REPO_ROOT)} に保存しました")
        raise SystemExit(1) from exc

    md_path = DRAFTS_DIR / f"{stem}.md"
    md_path.write_text(render_markdown(PLATFORM, drafts, now), encoding="utf-8")

    json_path = DRAFTS_DIR / f"{stem}.json"
    json_path.write_text(
        json.dumps([asdict(d) for d in drafts], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Generated {len(drafts)} draft(s)")
    print(f"- {md_path.relative_to(REPO_ROOT)}")
    print(f"- {json_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
