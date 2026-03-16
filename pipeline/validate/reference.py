from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pipeline.config import DEALS_DIR
from pipeline.extract.utils import atomic_write_json
from pipeline.validate.metrics import summarize_reference_metrics


SUMMARY_FILENAME = "reference_summary.json"


def run_reference_validation(
    deal_slugs: list[str],
    *,
    run_id: str,
    deals_dir: Path = DEALS_DIR,
) -> dict[str, Any]:
    per_deal: list[dict[str, Any]] = []
    for deal_slug in deal_slugs:
        metrics_path = deals_dir / deal_slug / "export" / "reference_metrics.json"
        selection_path = deals_dir / deal_slug / "source" / "chronology_selection.json"
        if not metrics_path.exists():
            continue
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        if selection_path.exists():
            selection = json.loads(selection_path.read_text(encoding="utf-8"))
            metrics["source_confidence"] = selection.get("confidence")
            metrics["source_review_required"] = selection.get("review_required")
        per_deal.append(metrics)

    summary = summarize_reference_metrics(per_deal)
    output = {
        "run_id": run_id,
        "deal_slugs": deal_slugs,
        "per_deal": per_deal,
        "summary": summary,
    }
    target_dir = deals_dir.parent / "validate"
    target_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(target_dir / SUMMARY_FILENAME, output)
    return output
