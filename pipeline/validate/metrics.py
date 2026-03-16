from __future__ import annotations

from statistics import mean
from typing import Any


def summarize_reference_metrics(per_deal: list[dict[str, Any]]) -> dict[str, Any]:
    if not per_deal:
        return {
            "deal_count": 0,
            "pass_rate": 0.0,
            "avg_blockers": 0.0,
            "avg_warnings": 0.0,
            "avg_events": 0.0,
        }
    return {
        "deal_count": len(per_deal),
        "pass_rate": sum(1 for row in per_deal if row.get("passes_export_gate")) / len(per_deal),
        "avg_blockers": mean(row.get("blocker_count", 0) for row in per_deal),
        "avg_warnings": mean(row.get("warning_count", 0) for row in per_deal),
        "avg_events": mean(row.get("event_count", 0) for row in per_deal),
    }
