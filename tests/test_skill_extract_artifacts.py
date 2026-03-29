from __future__ import annotations

import json
from pathlib import Path

import pytest

from skill_pipeline.extract_artifacts import MixedSchemaError, load_extract_artifacts
from skill_pipeline.paths import build_skill_paths


def _write_extract_payloads(
    tmp_path: Path,
    *,
    actors_payload: dict,
    events_payload: dict,
) -> None:
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    paths.extract_dir.mkdir(parents=True, exist_ok=True)
    paths.actors_raw_path.write_text(json.dumps(actors_payload), encoding="utf-8")
    paths.events_raw_path.write_text(json.dumps(events_payload), encoding="utf-8")


def _canonical_actor_payload() -> dict:
    return {
        "actors": [
            {
                "actor_id": "bidder_a",
                "display_name": "Bidder A",
                "canonical_name": "BIDDER A",
                "aliases": [],
                "role": "bidder",
                "advisor_kind": None,
                "advised_actor_id": None,
                "bidder_kind": "financial",
                "listing_status": "private",
                "geography": "domestic",
                "is_grouped": False,
                "group_size": None,
                "group_label": None,
                "evidence_span_ids": ["span_0001"],
                "notes": [],
            }
        ],
        "count_assertions": [],
        "unresolved_mentions": [],
    }


def _quote_first_actor_payload() -> dict:
    return {
        "quotes": [{"quote_id": "Q001", "block_id": "B001", "text": "Bidder A"}],
        "actors": [
            {
                "actor_id": "bidder_a",
                "display_name": "Bidder A",
                "canonical_name": "BIDDER A",
                "aliases": [],
                "role": "bidder",
                "advisor_kind": None,
                "advised_actor_id": None,
                "bidder_kind": "financial",
                "listing_status": "private",
                "geography": "domestic",
                "is_grouped": False,
                "group_size": None,
                "group_label": None,
                "quote_ids": ["Q001"],
                "notes": [],
            }
        ],
        "count_assertions": [],
        "unresolved_mentions": [],
    }


def _canonical_event_payload() -> dict:
    return {
        "events": [
            {
                "event_id": "evt_001",
                "event_type": "executed",
                "date": {
                    "raw_text": "2016-07-13",
                    "normalized_start": "2016-07-13",
                    "normalized_end": "2016-07-13",
                    "sort_date": "2016-07-13",
                    "precision": "day",
                    "anchor_event_id": None,
                    "anchor_span_id": None,
                    "resolution_note": None,
                    "is_inferred": False,
                },
                "actor_ids": ["bidder_a"],
                "summary": "Executed merger agreement",
                "evidence_span_ids": ["span_0001"],
                "terms": None,
                "formality_signals": None,
                "whole_company_scope": True,
                "drop_reason_text": None,
                "round_scope": None,
                "invited_actor_ids": [],
                "deadline_date": None,
                "executed_with_actor_id": None,
                "boundary_note": None,
                "nda_signed": None,
                "notes": [],
            }
        ],
        "exclusions": [],
        "coverage_notes": [],
    }


def _quote_first_event_payload() -> dict:
    return {
        "quotes": [{"quote_id": "Q101", "block_id": "B001", "text": "Executed merger agreement"}],
        "events": [
            {
                "event_id": "evt_001",
                "event_type": "executed",
                "date": {"raw_text": "2016-07-13", "normalized_hint": "2016-07-13"},
                "actor_ids": ["bidder_a"],
                "summary": "Executed merger agreement",
                "quote_ids": ["Q101"],
                "terms": None,
                "formality_signals": None,
                "whole_company_scope": True,
                "drop_reason_text": None,
                "round_scope": None,
                "invited_actor_ids": [],
                "deadline_date": None,
                "executed_with_actor_id": None,
                "boundary_note": None,
                "nda_signed": None,
                "notes": [],
            }
        ],
        "exclusions": [],
        "coverage_notes": [],
    }


def test_load_extract_artifacts_rejects_canonical_actors_with_quote_first_events(
    tmp_path: Path,
) -> None:
    _write_extract_payloads(
        tmp_path,
        actors_payload=_canonical_actor_payload(),
        events_payload=_quote_first_event_payload(),
    )
    paths = build_skill_paths("imprivata", project_root=tmp_path)

    with pytest.raises(MixedSchemaError, match="actors are canonical but events are quote_first"):
        load_extract_artifacts(paths)


def test_load_extract_artifacts_rejects_quote_first_actors_with_canonical_events(
    tmp_path: Path,
) -> None:
    _write_extract_payloads(
        tmp_path,
        actors_payload=_quote_first_actor_payload(),
        events_payload=_canonical_event_payload(),
    )
    paths = build_skill_paths("imprivata", project_root=tmp_path)

    with pytest.raises(MixedSchemaError, match="actors are quote_first but events are canonical"):
        load_extract_artifacts(paths)


def test_load_extract_artifacts_requires_spans_for_fully_canonical_payloads(
    tmp_path: Path,
) -> None:
    _write_extract_payloads(
        tmp_path,
        actors_payload=_canonical_actor_payload(),
        events_payload=_canonical_event_payload(),
    )
    paths = build_skill_paths("imprivata", project_root=tmp_path)

    with pytest.raises(FileNotFoundError, match="spans"):
        load_extract_artifacts(paths)
