from __future__ import annotations

import json
from pathlib import Path

from pipeline.validate.reference import run_reference_validation



def test_run_reference_validation_aggregates_per_deal_metrics(tmp_path: Path):
    deals_dir = tmp_path / "deals"
    for slug, passes, blockers in (("petsmart-inc", True, 0), ("providence-worcester", False, 2)):
        export_dir = deals_dir / slug / "export"
        source_dir = deals_dir / slug / "source"
        export_dir.mkdir(parents=True, exist_ok=True)
        source_dir.mkdir(parents=True, exist_ok=True)
        (export_dir / "reference_metrics.json").write_text(
            json.dumps(
                {
                    "deal_slug": slug,
                    "passes_export_gate": passes,
                    "blocker_count": blockers,
                    "warning_count": 1,
                    "event_count": 10,
                }
            ),
            encoding="utf-8",
        )
        (source_dir / "chronology_selection.json").write_text(
            json.dumps({"confidence": "high", "review_required": False}),
            encoding="utf-8",
        )

    output = run_reference_validation(
        ["petsmart-inc", "providence-worcester"],
        run_id="run-test",
        deals_dir=deals_dir,
    )

    assert output["summary"]["deal_count"] == 2
    assert output["summary"]["pass_rate"] == 0.5
    summary_path = tmp_path / "validate" / "reference_summary.json"
    assert summary_path.exists()
