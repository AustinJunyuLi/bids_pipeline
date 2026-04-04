from __future__ import annotations

import json
import logging
from decimal import Decimal
from pathlib import Path

from skill_pipeline.extract_artifacts_v2 import load_observation_artifacts
from skill_pipeline.normalize import normalize_raw_extraction
from skill_pipeline.paths import build_skill_paths


def _resolved_date_payload(day: str = "2026-03-31", *, precision: str = "exact_day") -> dict:
    return {
        "raw_text": day,
        "normalized_start": day,
        "normalized_end": day,
        "sort_date": day,
        "precision": precision,
        "anchor_event_id": None,
        "anchor_span_id": None,
        "resolution_note": None,
        "is_inferred": False,
    }


def _raw_payload() -> dict:
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


def test_renames_observation_type_aliases_to_obs_type() -> None:
    for alias in ("observation_type", "type"):
        payload = _raw_payload()
        payload["observations"][0].pop("obs_type")
        payload["observations"][0][alias] = "proposal"

        normalized = normalize_raw_extraction(payload)

        assert normalized["observations"][0]["obs_type"] == "proposal"
        assert alias not in normalized["observations"][0]


def test_wraps_string_dates_into_resolved_date_payloads() -> None:
    payload = _raw_payload()
    payload["observations"][0]["date"] = "2026-03-31"

    normalized = normalize_raw_extraction(payload)

    assert normalized["observations"][0]["date"] == _resolved_date_payload()


def test_maps_day_precision_to_exact_day() -> None:
    payload = _raw_payload()
    payload["observations"][0]["date"] = _resolved_date_payload(precision="day")

    normalized = normalize_raw_extraction(payload)

    assert normalized["observations"][0]["date"]["precision"] == "exact_day"


def test_renames_party_name_to_display_name() -> None:
    payload = _raw_payload()
    payload["parties"][0]["name"] = payload["parties"][0].pop("display_name")

    normalized = normalize_raw_extraction(payload)

    assert normalized["parties"][0]["display_name"] == "Bidder A"
    assert "name" not in normalized["parties"][0]


def test_renames_cohort_description_to_label() -> None:
    payload = _raw_payload()
    payload["cohorts"][0]["description"] = payload["cohorts"][0].pop("label")

    normalized = normalize_raw_extraction(payload)

    assert normalized["cohorts"][0]["label"] == "Finalists"
    assert "description" not in normalized["cohorts"][0]


def test_renames_cohort_known_members_to_known_member_party_ids() -> None:
    payload = _raw_payload()
    payload["cohorts"][0]["known_members"] = payload["cohorts"][0].pop("known_member_party_ids")

    normalized = normalize_raw_extraction(payload)

    assert normalized["cohorts"][0]["known_member_party_ids"] == ["party_bidder_a"]
    assert "known_members" not in normalized["cohorts"][0]


def test_replaces_coverage_dict_with_empty_list() -> None:
    payload = _raw_payload()
    payload["coverage"] = {"status": "not a list"}

    normalized = normalize_raw_extraction(payload)

    assert normalized["coverage"] == []


def test_renames_exclusion_item_and_reason_fields() -> None:
    payload = _raw_payload()
    payload["exclusions"] = [
        {
            "item": "other",
            "block_ids": ["B009"],
            "reason": "Excluded from output.",
        }
    ]

    normalized = normalize_raw_extraction(payload)

    assert normalized["exclusions"][0] == {
        "category": "other",
        "block_ids": ["B009"],
        "explanation": "Excluded from output.",
    }


def test_renames_terms_price_per_share_to_per_share() -> None:
    payload = _raw_payload()
    terms = payload["observations"][0]["terms"]
    terms["price_per_share"] = terms.pop("per_share")

    normalized = normalize_raw_extraction(payload)

    assert normalized["observations"][0]["terms"]["per_share"] == "21.50"
    assert "price_per_share" not in normalized["observations"][0]["terms"]


def test_normalizes_currency_formatted_per_share_values() -> None:
    payload = _raw_payload()
    payload["observations"][0]["terms"]["per_share"] = "$1,234.50"

    normalized = normalize_raw_extraction(payload)

    assert normalized["observations"][0]["terms"]["per_share"] == Decimal("1234.50")


def test_normalizer_is_idempotent_and_logs_all_counts(caplog) -> None:
    payload = _raw_payload()

    with caplog.at_level(logging.INFO):
        normalized = normalize_raw_extraction(payload)

    assert normalized == payload
    assert normalized is not payload
    assert normalized["observations"][0] is not payload["observations"][0]
    info_messages = [record.message for record in caplog.records if record.levelno == logging.INFO]
    assert len(info_messages) == 10
    assert all(message.endswith("count=0") for message in info_messages)


def test_warns_without_auto_fixing_fuzzy_semantic_issues(caplog) -> None:
    payload = _raw_payload()
    payload["observations"][0]["subject_refs"] = []
    payload["cohorts"][0]["created_by_observation_id"] = ""

    with caplog.at_level(logging.WARNING):
        normalized = normalize_raw_extraction(payload)

    assert normalized["observations"][0]["subject_refs"] == []
    assert normalized["cohorts"][0]["created_by_observation_id"] == ""
    warning_messages = [record.message for record in caplog.records if record.levelno == logging.WARNING]
    assert "normalize_raw_extraction.proposal_empty_subject_refs count=1" in warning_messages
    assert (
        "normalize_raw_extraction.cohort_missing_created_by_observation_id count=1"
        in warning_messages
    )


def test_load_observation_artifacts_validates_normalized_raw_payload(tmp_path: Path) -> None:
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    paths.extract_v2_dir.mkdir(parents=True, exist_ok=True)
    payload = _raw_payload()
    payload["parties"][0]["name"] = payload["parties"][0].pop("display_name")
    payload["cohorts"][0]["description"] = payload["cohorts"][0].pop("label")
    payload["cohorts"][0]["known_members"] = payload["cohorts"][0].pop("known_member_party_ids")
    payload["observations"][0]["observation_type"] = payload["observations"][0].pop("obs_type")
    payload["observations"][0]["date"] = "2026-03-31"
    payload["observations"][0]["terms"]["price_per_share"] = "$21.50"
    payload["observations"][0]["terms"].pop("per_share")
    payload["exclusions"] = [
        {
            "item": "other",
            "block_ids": ["B009"],
            "reason": "Excluded from output.",
        }
    ]
    payload["coverage"] = {"bad": "shape"}
    paths.observations_raw_path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = load_observation_artifacts(paths, mode="quote_first")

    assert loaded.raw_artifact is not None
    assert loaded.raw_artifact.parties[0].display_name == "Bidder A"
    assert loaded.raw_artifact.cohorts[0].label == "Finalists"
    assert loaded.raw_artifact.cohorts[0].known_member_party_ids == ["party_bidder_a"]
    assert loaded.raw_artifact.observations[0].obs_type == "proposal"
    assert loaded.raw_artifact.observations[0].date is not None
    assert loaded.raw_artifact.observations[0].date.precision == "exact_day"
    assert loaded.raw_artifact.observations[0].terms is not None
    assert loaded.raw_artifact.observations[0].terms.per_share == Decimal("21.50")
    assert loaded.raw_artifact.exclusions[0].category == "other"
    assert loaded.raw_artifact.coverage == []
