from __future__ import annotations

import json
from pathlib import Path

import pytest

from skill_pipeline.extract_artifacts_v2 import (
    detect_extract_artifact_version,
    load_observation_artifacts,
    load_versioned_extract_artifacts,
)
from skill_pipeline.paths import build_skill_paths


def _resolved_date_payload(day: str = "2026-03-31") -> dict:
    return {
        "raw_text": day,
        "normalized_start": day,
        "normalized_end": day,
        "sort_date": day,
        "precision": "exact_day",
        "anchor_event_id": None,
        "anchor_span_id": None,
        "resolution_note": None,
        "is_inferred": False,
    }


def _raw_observation_payload() -> dict:
    return {
        "quotes": [
            {"quote_id": "Q001", "block_id": "B001", "text": "Bidder A"},
            {"quote_id": "Q002", "block_id": "B002", "text": "Three parties advanced"},
            {"quote_id": "Q101", "block_id": "B003", "text": "Bidder A submitted a proposal"},
        ],
        "parties": [
            {
                "party_id": "party_bidder_a",
                "display_name": "Bidder A",
                "canonical_name": "BIDDER A",
                "aliases": [],
                "role": "bidder",
                "bidder_kind": "financial",
                "advisor_kind": None,
                "advised_party_id": None,
                "listing_status": "private",
                "geography": "domestic",
                "quote_ids": ["Q001"],
            }
        ],
        "cohorts": [
            {
                "cohort_id": "cohort_finalists",
                "label": "Finalists",
                "parent_cohort_id": None,
                "exact_count": 3,
                "known_member_party_ids": ["party_bidder_a"],
                "unknown_member_count": 2,
                "membership_basis": "advanced to final round",
                "created_by_observation_id": "obs_status",
                "quote_ids": ["Q002"],
            }
        ],
        "observations": [
            {
                "observation_id": "obs_proposal",
                "obs_type": "proposal",
                "date": _resolved_date_payload(),
                "subject_refs": ["party_bidder_a"],
                "counterparty_refs": ["cohort_finalists"],
                "summary": "Bidder A submitted a proposal.",
                "quote_ids": ["Q101"],
                "requested_by_observation_id": None,
                "revises_observation_id": None,
                "delivery_mode": "written",
                "terms": {
                    "per_share": "21.50",
                    "range_low": None,
                    "range_high": None,
                    "enterprise_value": None,
                    "consideration_type": "cash",
                },
                "mentions_non_binding": True,
                "includes_draft_merger_agreement": False,
                "includes_markup": False,
            }
        ],
        "exclusions": [],
        "coverage": [],
    }


def _canonical_observation_payload() -> dict:
    return {
        "parties": [
            {
                "party_id": "party_bidder_a",
                "display_name": "Bidder A",
                "canonical_name": "BIDDER A",
                "aliases": [],
                "role": "bidder",
                "bidder_kind": "financial",
                "advisor_kind": None,
                "advised_party_id": None,
                "listing_status": "private",
                "geography": "domestic",
                "evidence_span_ids": ["span_0001"],
            }
        ],
        "cohorts": [
            {
                "cohort_id": "cohort_finalists",
                "label": "Finalists",
                "parent_cohort_id": None,
                "exact_count": 3,
                "known_member_party_ids": ["party_bidder_a"],
                "unknown_member_count": 2,
                "membership_basis": "advanced to final round",
                "created_by_observation_id": "obs_status",
                "evidence_span_ids": ["span_0002"],
            }
        ],
        "observations": [
            {
                "observation_id": "obs_proposal",
                "obs_type": "proposal",
                "date": _resolved_date_payload(),
                "subject_refs": ["party_bidder_a"],
                "counterparty_refs": ["cohort_finalists"],
                "summary": "Bidder A submitted a proposal.",
                "evidence_span_ids": ["span_0003"],
                "requested_by_observation_id": None,
                "revises_observation_id": None,
                "delivery_mode": "written",
                "terms": {
                    "per_share": "21.50",
                    "range_low": None,
                    "range_high": None,
                    "enterprise_value": None,
                    "consideration_type": "cash",
                },
                "mentions_non_binding": True,
                "includes_draft_merger_agreement": False,
                "includes_markup": False,
            }
        ],
        "exclusions": [],
        "coverage": [],
    }


def _spans_payload() -> dict:
    return {
        "spans": [
            {
                "span_id": "span_0001",
                "document_id": "DOC001",
                "accession_number": "DOC001",
                "filing_type": "DEFM14A",
                "start_line": 1,
                "end_line": 1,
                "start_char": None,
                "end_char": None,
                "block_ids": ["B001"],
                "evidence_ids": [],
                "anchor_text": "Bidder A",
                "quote_text": "Bidder A",
                "quote_text_normalized": "bidder a",
                "match_type": "exact",
                "resolution_note": None,
            },
            {
                "span_id": "span_0002",
                "document_id": "DOC001",
                "accession_number": "DOC001",
                "filing_type": "DEFM14A",
                "start_line": 2,
                "end_line": 2,
                "start_char": None,
                "end_char": None,
                "block_ids": ["B002"],
                "evidence_ids": [],
                "anchor_text": "Three parties advanced",
                "quote_text": "Three parties advanced",
                "quote_text_normalized": "three parties advanced",
                "match_type": "exact",
                "resolution_note": None,
            },
            {
                "span_id": "span_0003",
                "document_id": "DOC001",
                "accession_number": "DOC001",
                "filing_type": "DEFM14A",
                "start_line": 3,
                "end_line": 3,
                "start_char": None,
                "end_char": None,
                "block_ids": ["B003"],
                "evidence_ids": [],
                "anchor_text": "Bidder A submitted a proposal",
                "quote_text": "Bidder A submitted a proposal",
                "quote_text_normalized": "bidder a submitted a proposal",
                "match_type": "exact",
                "resolution_note": None,
            },
        ]
    }


def _write_v1_payloads(tmp_path: Path) -> None:
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    paths.extract_dir.mkdir(parents=True, exist_ok=True)
    paths.actors_raw_path.write_text(
        json.dumps(
            {
                "quotes": [{"quote_id": "Q001", "block_id": "B001", "text": "Bidder A"}],
                "actors": [],
                "count_assertions": [],
                "unresolved_mentions": [],
            }
        ),
        encoding="utf-8",
    )
    paths.events_raw_path.write_text(
        json.dumps({"quotes": [], "events": [], "exclusions": [], "coverage_notes": []}),
        encoding="utf-8",
    )


def _write_v2_raw_payload(tmp_path: Path) -> None:
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    paths.extract_v2_dir.mkdir(parents=True, exist_ok=True)
    paths.observations_raw_path.write_text(
        json.dumps(_raw_observation_payload()),
        encoding="utf-8",
    )


def _write_v2_canonical_payload(tmp_path: Path, *, with_spans: bool = True) -> None:
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    paths.extract_v2_dir.mkdir(parents=True, exist_ok=True)
    paths.observations_path.write_text(
        json.dumps(_canonical_observation_payload()),
        encoding="utf-8",
    )
    if with_spans:
        paths.spans_v2_path.write_text(json.dumps(_spans_payload()), encoding="utf-8")


def test_detect_extract_artifact_version_distinguishes_v2_only(tmp_path: Path) -> None:
    _write_v2_raw_payload(tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)

    assert detect_extract_artifact_version(paths) == "v2"


def test_detect_extract_artifact_version_reports_both_when_v1_and_v2_exist(tmp_path: Path) -> None:
    _write_v1_payloads(tmp_path)
    _write_v2_raw_payload(tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)

    assert detect_extract_artifact_version(paths) == "both"


def test_load_observation_artifacts_quote_first_mode_returns_typed_raw_artifact(
    tmp_path: Path,
) -> None:
    _write_v2_raw_payload(tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)

    loaded = load_observation_artifacts(paths, mode="quote_first")

    assert loaded.mode == "quote_first"
    assert loaded.raw_artifact is not None
    assert loaded.observations is None
    assert loaded.raw_artifact.parties[0].quote_ids == ["Q001"]
    assert loaded.raw_artifact.observations[0].quote_ids == ["Q101"]


def test_load_observation_artifacts_requires_spans_for_canonical_payloads(
    tmp_path: Path,
) -> None:
    _write_v2_canonical_payload(tmp_path, with_spans=False)
    paths = build_skill_paths("imprivata", project_root=tmp_path)

    with pytest.raises(FileNotFoundError, match="spans"):
        load_observation_artifacts(paths, mode="canonical")


def test_load_observation_artifacts_canonical_mode_returns_indexes(tmp_path: Path) -> None:
    _write_v2_canonical_payload(tmp_path, with_spans=True)
    paths = build_skill_paths("imprivata", project_root=tmp_path)

    loaded = load_observation_artifacts(paths)

    assert loaded.mode == "canonical"
    assert loaded.raw_artifact is None
    assert set(loaded.party_index) == {"party_bidder_a"}
    assert set(loaded.cohort_index) == {"cohort_finalists"}
    assert set(loaded.observation_index) == {"obs_proposal"}
    assert set(loaded.span_index) == {"span_0001", "span_0002", "span_0003"}


def test_load_versioned_extract_artifacts_refuses_ambiguous_auto_detection(
    tmp_path: Path,
) -> None:
    _write_v1_payloads(tmp_path)
    _write_v2_canonical_payload(tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)

    with pytest.raises(ValueError, match="Both v1 and v2 extract artifacts are present"):
        load_versioned_extract_artifacts(paths)


def test_load_versioned_extract_artifacts_can_explicitly_select_v2(tmp_path: Path) -> None:
    _write_v1_payloads(tmp_path)
    _write_v2_canonical_payload(tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)

    loaded = load_versioned_extract_artifacts(paths, version="v2")

    assert loaded.mode == "canonical"
    assert loaded.observations is not None
    assert loaded.observations.observations[0].observation_id == "obs_proposal"
