"""Tests for the deterministic check stage."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from skill_pipeline import cli
from skill_pipeline.check import run_check
from skill_pipeline.paths import build_skill_paths


def _write_check_fixture(
    tmp_path: Path,
    *,
    slug: str = "imprivata",
    bidder_kind: str | None = "financial",
    proposal_terms: bool = True,
    proposal_formality_signals: bool = True,
    anchor_text: str = "indication of interest",
) -> None:
    """Write minimal extract artifacts for check tests.

    One bidder actor + one proposal event. Parameters control what to omit
    for each test scenario.
    """
    data_dir = tmp_path / "data"
    deals_source_dir = data_dir / "deals" / slug / "source"
    raw_dir = tmp_path / "raw" / slug
    skill_root = data_dir / "skill" / slug
    extract_dir = skill_root / "extract"

    deals_source_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    extract_dir.mkdir(parents=True, exist_ok=True)

    (data_dir / "seeds.csv").write_text(
        (
            "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
            f"{slug},IMPRIVATA INC,THOMA BRAVO LLC,2016-07-13,https://example.com,false\n"
        ),
        encoding="utf-8",
    )
    (deals_source_dir / "chronology_blocks.jsonl").write_text("{}\n", encoding="utf-8")
    (deals_source_dir / "evidence_items.jsonl").write_text("{}\n", encoding="utf-8")
    (raw_dir / "document_registry.json").write_text("{}", encoding="utf-8")

    actors_payload = {
        "actors": [
            {
                "actor_id": "party_a",
                "display_name": "Party A",
                "canonical_name": "PARTY A",
                "aliases": [],
                "role": "bidder",
                "advisor_kind": None,
                "advised_actor_id": None,
                "bidder_kind": bidder_kind,
                "listing_status": "private",
                "geography": "domestic",
                "is_grouped": False,
                "group_size": None,
                "group_label": None,
                "evidence_refs": [
                    {"block_id": "B001", "evidence_id": None, "anchor_text": "Party A"}
                ],
                "notes": [],
            }
        ],
        "count_assertions": [],
        "unresolved_mentions": [],
    }

    proposal_evidence_refs = [
        {"block_id": "B002", "evidence_id": None, "anchor_text": anchor_text}
    ]

    proposal_event = {
        "event_id": "evt_002",
        "event_type": "proposal",
        "date": {"raw_text": "July 5, 2016", "normalized_hint": "2016-07-05"},
        "actor_ids": ["party_a"],
        "summary": "Party A submitted an indication of interest.",
        "evidence_refs": proposal_evidence_refs,
        "terms": (
            {
                "per_share": 25.0,
                "range_low": None,
                "range_high": None,
                "enterprise_value": None,
                "consideration_type": "cash",
            }
            if proposal_terms
            else None
        ),
        "formality_signals": (
            {
                "contains_range": False,
                "mentions_indication_of_interest": True,
                "mentions_preliminary": False,
                "mentions_non_binding": False,
                "mentions_binding_offer": False,
                "includes_draft_merger_agreement": False,
                "includes_marked_up_agreement": False,
                "requested_binding_offer_via_process_letter": False,
                "after_final_round_announcement": False,
                "after_final_round_deadline": False,
                "is_subject_to_financing": None,
            }
            if proposal_formality_signals
            else None
        ),
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

    events_payload = {
        "events": [proposal_event],
        "exclusions": [],
        "coverage_notes": [],
    }

    (extract_dir / "actors_raw.json").write_text(json.dumps(actors_payload), encoding="utf-8")
    (extract_dir / "events_raw.json").write_text(json.dumps(events_payload), encoding="utf-8")


def test_run_check_fails_on_missing_proposal_terms(tmp_path: Path) -> None:
    _write_check_fixture(
        tmp_path,
        proposal_terms=False,
        proposal_formality_signals=True,
    )
    exit_code = run_check("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    report = json.loads(paths.check_report_path.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert report["summary"]["status"] == "fail"
    assert report["summary"]["blocker_count"] == 1
    assert report["findings"][0]["check_id"] == "proposal_terms_required"


def test_run_check_fails_on_missing_proposal_formality_signals(tmp_path: Path) -> None:
    _write_check_fixture(
        tmp_path,
        proposal_terms=True,
        proposal_formality_signals=False,
    )
    exit_code = run_check("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    report = json.loads(paths.check_report_path.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert report["summary"]["status"] == "fail"
    assert report["summary"]["blocker_count"] == 1
    assert report["findings"][0]["check_id"] == "proposal_terms_required"


def test_run_check_warns_but_passes_on_missing_bidder_kind(tmp_path: Path) -> None:
    _write_check_fixture(tmp_path, bidder_kind=None)
    exit_code = run_check("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    report = json.loads(paths.check_report_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert report["summary"]["status"] == "pass"
    assert report["summary"]["warning_count"] == 1


def test_run_check_fails_on_empty_anchor_text(tmp_path: Path) -> None:
    _write_check_fixture(tmp_path, anchor_text="")
    exit_code = run_check("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    report = json.loads(paths.check_report_path.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert report["summary"]["status"] == "fail"
    assert report["summary"]["blocker_count"] == 1
    assert report["findings"][0]["check_id"] == "empty_anchor_text"


def test_skill_cli_supports_check_subcommand() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(["check", "--deal", "imprivata"])

    assert args.command == "check"
    assert args.deal == "imprivata"


def test_check_cli_invokes_run_check(tmp_path: Path) -> None:
    _write_check_fixture(tmp_path)
    exit_code = cli.main(["check", "--deal", "imprivata", "--project-root", str(tmp_path)])
    assert exit_code == 0
