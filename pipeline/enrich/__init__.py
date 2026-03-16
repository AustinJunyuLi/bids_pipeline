from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pipeline.config import DEALS_DIR
from pipeline.enrich.classify import classify_proposals
from pipeline.enrich.cycles import assign_event_sequence, order_events, segment_cycles
from pipeline.enrich.features import compute_derived_metrics
from pipeline.extract.utils import atomic_write_json
from pipeline.models.enrichment import DealEnrichment
from pipeline.models.extraction import DealExtraction


ENRICHMENT_FILENAME = "deal_enrichment.json"


def run_enrichment(
    deal_slug: str,
    *,
    run_id: str,
    deals_dir: Path = DEALS_DIR,
) -> dict[str, Any]:
    qa_dir = deals_dir / deal_slug / "qa"
    enrich_dir = deals_dir / deal_slug / "enrich"
    enrich_dir.mkdir(parents=True, exist_ok=True)

    extraction = DealExtraction.model_validate_json((qa_dir / "extraction_canonical.json").read_text(encoding="utf-8"))
    ordered_events = order_events(extraction)
    event_sequence = assign_event_sequence(extraction)
    classifications = classify_proposals(extraction, ordered_events=ordered_events)
    cycles, event_cycle_map, formal_boundary_event_ids = segment_cycles(
        extraction,
        classifications=classifications,
    )
    derived_metrics = compute_derived_metrics(
        extraction,
        classifications=classifications,
        cycles=cycles,
        event_cycle_map=event_cycle_map,
    )

    enrichment = DealEnrichment(
        run_id=run_id,
        deal_slug=deal_slug,
        classifications=classifications,
        cycles=cycles,
        event_sequence=event_sequence,
        event_cycle_map=event_cycle_map,
        formal_boundary_event_ids=formal_boundary_event_ids,
        derived_metrics=derived_metrics,
    )
    atomic_write_json(enrich_dir / ENRICHMENT_FILENAME, enrichment.model_dump(mode="json"))
    return {
        "deal_slug": deal_slug,
        "cycle_count": len(cycles),
        "formal_proposal_count": derived_metrics.proposal_count_formal,
        "informal_proposal_count": derived_metrics.proposal_count_informal,
    }


__all__ = [
    "ENRICHMENT_FILENAME",
    "classify_proposals",
    "compute_derived_metrics",
    "run_enrichment",
    "segment_cycles",
]
