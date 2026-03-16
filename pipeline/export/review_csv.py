from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from pipeline.config import DEALS_DIR
from pipeline.export.alex_compat import ALEX_COMPAT_COLUMNS, build_alex_compat_rows
from pipeline.export.flatten import flatten_review_rows
from pipeline.extract.utils import atomic_write_json
from pipeline.models.enrichment import DealEnrichment
from pipeline.models.extraction import DealExtraction
from pipeline.models.export import ReviewRow
from pipeline.models.qa import QAReport


REVIEW_CSV_FILENAME = "events_long.csv"
ALEX_COMPAT_FILENAME = "alex_compat.csv"
CANONICAL_EXPORT_FILENAME = "canonical_export.json"
REFERENCE_METRICS_FILENAME = "reference_metrics.json"


def run_export(
    deal_slug: str,
    *,
    run_id: str,
    deals_dir: Path = DEALS_DIR,
) -> dict[str, Any]:
    qa_dir = deals_dir / deal_slug / "qa"
    enrich_dir = deals_dir / deal_slug / "enrich"
    export_dir = deals_dir / deal_slug / "export"
    export_dir.mkdir(parents=True, exist_ok=True)

    extraction = DealExtraction.model_validate_json((qa_dir / "extraction_canonical.json").read_text(encoding="utf-8"))
    qa_report = QAReport.model_validate_json((qa_dir / "report.json").read_text(encoding="utf-8"))
    enrichment = DealEnrichment.model_validate_json((enrich_dir / "deal_enrichment.json").read_text(encoding="utf-8"))

    review_rows = flatten_review_rows(extraction, enrichment, qa_report)
    alex_rows = build_alex_compat_rows(extraction, enrichment, qa_report)

    write_review_csv(export_dir / REVIEW_CSV_FILENAME, review_rows)
    write_dict_csv(export_dir / ALEX_COMPAT_FILENAME, alex_rows, fieldnames=ALEX_COMPAT_COLUMNS)
    atomic_write_json(
        export_dir / CANONICAL_EXPORT_FILENAME,
        {
            "run_id": run_id,
            "deal_slug": deal_slug,
            "extraction": extraction.model_dump(mode="json"),
            "qa_report": qa_report.model_dump(mode="json"),
            "enrichment": enrichment.model_dump(mode="json"),
        },
    )
    atomic_write_json(
        export_dir / REFERENCE_METRICS_FILENAME,
        {
            "deal_slug": deal_slug,
            "run_id": run_id,
            "passes_export_gate": qa_report.passes_export_gate,
            "blocker_count": qa_report.blocker_count,
            "warning_count": qa_report.warning_count,
            "actor_count": len(extraction.actors),
            "event_count": len(extraction.events),
            "proposal_count": enrichment.derived_metrics.proposal_count_total,
            "formal_proposal_count": enrichment.derived_metrics.proposal_count_formal,
            "informal_proposal_count": enrichment.derived_metrics.proposal_count_informal,
            "cycle_count": enrichment.derived_metrics.cycle_count,
        },
    )
    return {
        "deal_slug": deal_slug,
        "review_row_count": len(review_rows),
        "alex_row_count": len(alex_rows),
        "passes_export_gate": qa_report.passes_export_gate,
    }


def write_review_csv(path: Path, rows: list[ReviewRow]) -> None:
    fieldnames = list(ReviewRow.model_fields)
    serialised_rows: list[dict[str, Any]] = []
    for row in rows:
        payload = row.model_dump(mode="json")
        payload["qa_flags"] = "; ".join(payload["qa_flags"])
        serialised_rows.append(payload)
    write_dict_csv(path, serialised_rows, fieldnames=fieldnames)


def write_dict_csv(path: Path, rows: list[dict[str, Any]], *, fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})
    temp_path.replace(path)
