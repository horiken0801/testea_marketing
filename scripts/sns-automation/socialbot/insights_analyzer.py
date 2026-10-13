from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .config import Config, INSIGHTS_HISTORY_DIR
from .platforms.base import PostMetrics
from .platforms.threads import ThreadsClient
from .platforms.x import XClient
from .strategy import load_strategy, save_strategy

JST = ZoneInfo("Asia/Tokyo")


def _collect(config: Config) -> dict[str, list[PostMetrics]]:
    results: dict[str, list[PostMetrics]] = {}
    if config.x_enabled:
        results["x"] = XClient(config).recent_metrics(limit=30)
    if config.threads_enabled:
        results["threads"] = ThreadsClient(config).recent_metrics(limit=30)
    return results


def _best_hour(metrics: list[PostMetrics]) -> str | None:
    buckets: dict[int, list[int]] = {}
    for m in metrics:
        try:
            created = datetime.fromisoformat(m.created_at.replace("Z", "+00:00"))
        except ValueError:
            continue
        hour = created.astimezone(JST).hour
        buckets.setdefault(hour, []).append(m.engagement)
    if not buckets:
        return None
    best_hour = max(buckets, key=lambda h: statistics.mean(buckets[h]))
    return f"{best_hour:02d}:00"


def analyze_and_update_strategy(config: Config) -> dict:
    metrics_by_platform = _collect(config)
    strategy = load_strategy()
    hypotheses = strategy.setdefault("hypotheses", [])
    summary: dict = {"generated_at": datetime.now(timezone.utc).isoformat(), "platforms": {}}

    for platform, metrics in metrics_by_platform.items():
        if not metrics:
            continue
        avg_engagement = statistics.mean(m.engagement for m in metrics)
        best_hour = _best_hour(metrics)
        top_post = max(metrics, key=lambda m: m.engagement)
        summary["platforms"][platform] = {
            "post_count": len(metrics),
            "avg_engagement": avg_engagement,
            "best_hour": best_hour,
            "top_post_id": top_post.post_id,
            "top_post_engagement": top_post.engagement,
        }

        if best_hour:
            posting_times = strategy.setdefault("posting_times", {}).setdefault(platform, [])
            if best_hour not in posting_times:
                posting_times.append(best_hour)
            note = f"{platform}: エンゲージメント平均が高い時間帯は{best_hour}台。今後の投稿枠に追加。"
        else:
            note = f"{platform}: 有意な傾向を検出できず。現行の投稿時間を維持。"

        hypotheses.append({"date": summary["generated_at"], "platform": platform, "note": note})

    strategy["hypotheses"] = hypotheses[-50:]
    save_strategy(strategy)

    INSIGHTS_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    history_path = INSIGHTS_HISTORY_DIR / f"{datetime.now(timezone.utc):%Y-%m-%d}.json"
    with history_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return summary
