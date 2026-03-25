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
    actors_payload: dict | None = None,
    events_payload: dict | None = None,
) -> None:
    """Write minimal extract artifacts for check tests.

    Defaults to one bidder actor + one proposal event. Parameters can override
    the default payloads for more specific scenarios.
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

    if actors_payload is None:
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

    if events_payload is None:
        nda_event = {
            "event_id": "evt_001",
            "event_type": "nda",
            "date": {"raw_text": "July 1, 2016", "normalized_hint": "2016-07-01"},
            "actor_ids": ["party_a"],
            "summary": "Party A signed a confidentiality agreement.",
            "evidence_refs": [
                {
                    "block_id": "B001",
                    "evidence_id": None,
                    "anchor_text": "Party A signed a confidentiality agreement",
                }
            ],
            "terms": None,
            "formality_signals": None,
            "whole_company_scope": True,
            "drop_reason_text": None,
            "round_scope": None,
            "invited_actor_ids": [],
            "deadline_date": None,
            "executed_with_actor_id": None,
            "boundary_note": None,
            "nda_signed": True,
            "notes": [],
        }
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
            "events": [nda_event, proposal_event],
            "exclusions": [],
            "coverage_notes": [],
        }

    (extract_dir / "actors_raw.json").write_text(json.dumps(actors_payload), encoding="utf-8")
    (extract_dir / "events_raw.json").write_text(json.dumps(events_payload), encoding="utf-8")


def _actor(
    actor_id: str,
    canonical_name: str,
    *,
    role: str = "bidder",
    bidder_kind: str | None = "financial",
    advised_actor_id: str | None = None,
    is_grouped: bool = False,
) -> dict:
    return {
        "actor_id": actor_id,
        "display_name": canonical_name.title(),
        "canonical_name": canonical_name,
        "aliases": [],
        "role": role,
        "advisor_kind": None,
        "advised_actor_id": advised_actor_id,
        "bidder_kind": bidder_kind,
        "listing_status": "private",
        "geography": "domestic",
        "is_grouped": is_grouped,
        "group_size": None,
        "group_label": None,
        "evidence_refs": [{"block_id": "B001", "evidence_id": None, "anchor_text": canonical_name}],
        "notes": [],
    }


def _event(
    event_id: str,
    event_type: str,
    *,
    actor_ids: list[str] | None = None,
    summary: str = "x",
) -> dict:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "date": {"raw_text": "July 5, 2016", "normalized_hint": "2016-07-05"},
        "actor_ids": actor_ids or [],
        "summary": summary,
        "evidence_refs": [{"block_id": "B002", "evidence_id": None, "anchor_text": summary}],
        "terms": None,
        "formality_signals": None,
        "whole_company_scope": True,
        "drop_reason_text": None,
        "round_scope": None,
        "invited_actor_ids": [],
        "deadline_date": None,
        "executed_with_actor_id": None,
        "boundary_note": None,
        "nda_signed": event_type == "nda",
        "notes": [],
    }


def _run_check_report(tmp_path: Path, **fixture_kwargs: object) -> tuple[int, dict]:
    _write_check_fixture(tmp_path, **fixture_kwargs)
    exit_code = run_check("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    return exit_code, json.loads(paths.check_report_path.read_text(encoding="utf-8"))


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


def test_actor_audit_duplicate_canonical_name(tmp_path: Path) -> None:
    exit_code, report = _run_check_report(
        tmp_path,
        actors_payload={
            "actors": [
                _actor("actor_1", "PARTY A", role="activist", bidder_kind=None),
                _actor("actor_2", "PARTY A", role="activist", bidder_kind=None),
            ],
            "count_assertions": [],
            "unresolved_mentions": [],
        },
        events_payload={"events": [], "exclusions": [], "coverage_notes": []},
    )

    assert exit_code == 0
    duplicate = next(finding for finding in report["findings"] if finding["check_id"] == "duplicate_canonical_name")
    assert duplicate["actor_ids"] == ["actor_1", "actor_2"]


def test_actor_audit_bidder_no_nda(tmp_path: Path) -> None:
    exit_code, report = _run_check_report(
        tmp_path,
        actors_payload={
            "actors": [_actor("party_a", "PARTY A")],
            "count_assertions": [],
            "unresolved_mentions": [],
        },
        events_payload={
            "events": [_event("evt_001", "executed", actor_ids=["party_a"], summary="Signed merger agreement")],
            "exclusions": [],
            "coverage_notes": [],
        },
    )

    assert exit_code == 0
    bidder_no_nda = next(finding for finding in report["findings"] if finding["check_id"] == "bidder_no_nda")
    assert bidder_no_nda["actor_ids"] == ["party_a"]


def test_actor_audit_count_gap(tmp_path: Path) -> None:
    exit_code, report = _run_check_report(
        tmp_path,
        actors_payload={
            "actors": [],
            "count_assertions": [
                {
                    "subject": "15 signed NDA",
                    "count": 15,
                    "evidence_refs": [{"block_id": "B001", "evidence_id": None, "anchor_text": "15 signed NDA"}],
                }
            ],
            "unresolved_mentions": [],
        },
        events_payload={
            "events": [_event(f"evt_{index:03d}", "nda", summary=f"NDA {index}") for index in range(1, 13)],
            "exclusions": [],
            "coverage_notes": [],
        },
    )

    assert exit_code == 0
    count_gap = next(finding for finding in report["findings"] if finding["check_id"] == "count_assertion_gap")
    assert count_gap["description"] == "Count assertion '15 signed NDA' expects 15, found 12."


def test_actor_audit_advisor_missing_advised(tmp_path: Path) -> None:
    exit_code, report = _run_check_report(
        tmp_path,
        actors_payload={
            "actors": [_actor("advisor_a", "BANK A", role="advisor", bidder_kind=None, advised_actor_id=None)],
            "count_assertions": [],
            "unresolved_mentions": [],
        },
        events_payload={"events": [], "exclusions": [], "coverage_notes": []},
    )

    assert exit_code == 0
    missing_advised = next(finding for finding in report["findings"] if finding["check_id"] == "advisor_missing_advised")
    assert missing_advised["actor_ids"] == ["advisor_a"]


def test_actor_audit_clean(tmp_path: Path) -> None:
    exit_code, report = _run_check_report(
        tmp_path,
        actors_payload={
            "actors": [_actor("party_a", "PARTY A")],
            "count_assertions": [],
            "unresolved_mentions": [],
        },
        events_payload={
            "events": [_event("evt_001", "nda", actor_ids=["party_a"], summary="Party A signed an NDA")],
            "exclusions": [],
            "coverage_notes": [],
        },
    )

    assert exit_code == 0
    assert report["findings"] == []
