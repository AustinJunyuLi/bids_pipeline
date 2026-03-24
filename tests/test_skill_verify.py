"""Tests for the strict deterministic verify stage."""

from __future__ import annotations

import json
from pathlib import Path

from skill_pipeline.pipeline_models.common import QuoteMatchType
from skill_pipeline.paths import build_skill_paths
from skill_pipeline.verify import _resolve_quote_match, run_verify


def _read_findings_list(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    findings = payload["findings"]
    assert isinstance(findings, list)
    return findings


def _write_verify_fixture_for_fuzzy_only_match(tmp_path: Path, *, slug: str = "imprivata") -> None:
    """Create fixture where anchor_text matches only FUZZY (pipeline would resolve, we reject).

    Block raw_text = "Party A submitted a bid on July 5."
    anchor_text = "Party A submitted a bid on July 5 (preliminary)"
    EXACT and NORMALIZED fail; FUZZY would match by stripping parenthetical.
    Verify must treat FUZZY as unresolved and emit a repairable finding.
    """
    doc_id = "DOC001"
    data_dir = tmp_path / "data"
    deals_source_dir = data_dir / "deals" / slug / "source"
    raw_dir = tmp_path / "raw" / slug
    filings_dir = raw_dir / "filings"
    skill_root = data_dir / "skill" / slug
    extract_dir = skill_root / "extract"

    deals_source_dir.mkdir(parents=True, exist_ok=True)
    filings_dir.mkdir(parents=True, exist_ok=True)
    extract_dir.mkdir(parents=True, exist_ok=True)

    (data_dir / "seeds.csv").write_text(
        (
            "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
            f"{slug},IMPRIVATA INC,THOMA BRAVO LLC,2016-07-13,https://example.com,false\n"
        ),
        encoding="utf-8",
    )

    block_raw_text = "Party A submitted a bid on July 5."
    block_start, block_end = 1, 1

    chronology_blocks = [
        {
            "block_id": "B001",
            "document_id": doc_id,
            "ordinal": 1,
            "start_line": block_start,
            "end_line": block_end,
            "raw_text": block_raw_text,
            "clean_text": block_raw_text,
            "is_heading": False,
            "page_break_before": False,
            "page_break_after": False,
        }
    ]
    (deals_source_dir / "chronology_blocks.jsonl").write_text(
        "\n".join(json.dumps(b) for b in chronology_blocks) + "\n",
        encoding="utf-8",
    )

    evidence_items = [
        {
            "evidence_id": f"{doc_id}:E0001",
            "document_id": doc_id,
            "accession_number": doc_id,
            "filing_type": "DEFM14A",
            "start_line": block_start,
            "end_line": block_end,
            "raw_text": block_raw_text,
            "evidence_type": "dated_action",
            "confidence": "high",
            "matched_terms": [],
            "date_text": None,
            "actor_hint": None,
            "value_hint": None,
            "note": None,
        }
    ]
    (deals_source_dir / "evidence_items.jsonl").write_text(
        "\n".join(json.dumps(e) for e in evidence_items) + "\n",
        encoding="utf-8",
    )

    (raw_dir / "document_registry.json").write_text(
        json.dumps(
            {
                "artifact_type": "raw_document_registry",
                "documents": [
                    {
                        "document_id": doc_id,
                        "accession_number": doc_id,
                        "filing_type": "DEFM14A",
                        "txt_path": f"raw/{slug}/filings/{doc_id}.txt",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    filing_content = block_raw_text + "\n"
    (filings_dir / f"{doc_id}.txt").write_text(filing_content, encoding="utf-8")

    anchor_text = "Party A submitted a bid on July 5 (preliminary)"

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
                "bidder_kind": "financial",
                "listing_status": "private",
                "geography": "domestic",
                "is_grouped": False,
                "group_size": None,
                "group_label": None,
                "evidence_refs": [
                    {"block_id": "B001", "evidence_id": None, "anchor_text": anchor_text}
                ],
                "notes": [],
            }
        ],
        "count_assertions": [],
        "unresolved_mentions": [],
    }

    events_payload = {
        "events": [
            {
                "event_id": "evt_001",
                "event_type": "proposal",
                "date": {"raw_text": "July 5, 2016", "normalized_hint": "2016-07-05"},
                "actor_ids": ["party_a"],
                "summary": "Party A submitted a bid.",
                "evidence_refs": [
                    {"block_id": "B001", "evidence_id": None, "anchor_text": anchor_text}
                ],
                "terms": {
                    "per_share": 25.0,
                    "range_low": None,
                    "range_high": None,
                    "enterprise_value": None,
                    "consideration_type": "cash",
                },
                "formality_signals": {
                    "contains_range": False,
                    "mentions_indication_of_interest": False,
                    "mentions_preliminary": True,
                    "mentions_non_binding": False,
                    "mentions_binding_offer": False,
                    "includes_draft_merger_agreement": False,
                    "includes_marked_up_agreement": False,
                    "requested_binding_offer_via_process_letter": False,
                    "after_final_round_announcement": False,
                    "after_final_round_deadline": False,
                    "is_subject_to_financing": None,
                },
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

    (extract_dir / "actors_raw.json").write_text(json.dumps(actors_payload), encoding="utf-8")
    (extract_dir / "events_raw.json").write_text(json.dumps(events_payload), encoding="utf-8")


def _write_verify_fixture_for_clean_pass(tmp_path: Path, *, slug: str = "imprivata") -> None:
    """Create fixture where all evidence refs resolve EXACT or NORMALIZED."""
    doc_id = "DOC002"
    data_dir = tmp_path / "data"
    deals_source_dir = data_dir / "deals" / slug / "source"
    raw_dir = tmp_path / "raw" / slug
    filings_dir = raw_dir / "filings"
    skill_root = data_dir / "skill" / slug
    extract_dir = skill_root / "extract"

    deals_source_dir.mkdir(parents=True, exist_ok=True)
    filings_dir.mkdir(parents=True, exist_ok=True)
    extract_dir.mkdir(parents=True, exist_ok=True)

    (data_dir / "seeds.csv").write_text(
        (
            "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
            f"{slug},IMPRIVATA INC,THOMA BRAVO LLC,2016-07-13,https://example.com,false\n"
        ),
        encoding="utf-8",
    )

    block_raw_text = "Party A signed an NDA and submitted an indication of interest."
    block_start, block_end = 1, 1

    chronology_blocks = [
        {
            "block_id": "B001",
            "document_id": doc_id,
            "ordinal": 1,
            "start_line": block_start,
            "end_line": block_end,
            "raw_text": block_raw_text,
            "clean_text": block_raw_text,
            "is_heading": False,
            "page_break_before": False,
            "page_break_after": False,
        }
    ]
    (deals_source_dir / "chronology_blocks.jsonl").write_text(
        "\n".join(json.dumps(b) for b in chronology_blocks) + "\n",
        encoding="utf-8",
    )

    (deals_source_dir / "evidence_items.jsonl").write_text("", encoding="utf-8")

    (raw_dir / "document_registry.json").write_text(
        json.dumps(
            {
                "artifact_type": "raw_document_registry",
                "documents": [
                    {
                        "document_id": doc_id,
                        "accession_number": doc_id,
                        "filing_type": "DEFM14A",
                        "txt_path": f"raw/{slug}/filings/{doc_id}.txt",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    (filings_dir / f"{doc_id}.txt").write_text(block_raw_text + "\n", encoding="utf-8")

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
                "bidder_kind": "financial",
                "listing_status": "private",
                "geography": "domestic",
                "is_grouped": False,
                "group_size": None,
                "group_label": None,
                "evidence_refs": [
                    {
                        "block_id": "B001",
                        "evidence_id": None,
                        "anchor_text": "Party A signed an NDA",
                    }
                ],
                "notes": [],
            }
        ],
        "count_assertions": [],
        "unresolved_mentions": [],
    }

    events_payload = {
        "events": [
            {
                "event_id": "evt_001",
                "event_type": "target_sale",
                "date": {"raw_text": "June 2016", "normalized_hint": "2016-06"},
                "actor_ids": ["party_a"],
                "summary": "Target initiated sale process.",
                "evidence_refs": [
                    {
                        "block_id": "B001",
                        "evidence_id": None,
                        "anchor_text": "indication of interest",
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
                "nda_signed": None,
                "notes": [],
            },
            {
                "event_id": "evt_002",
                "event_type": "executed",
                "date": {"raw_text": "July 13, 2016", "normalized_hint": "2016-07-13"},
                "actor_ids": ["party_a"],
                "summary": "Deal executed.",
                "evidence_refs": [
                    {
                        "block_id": "B001",
                        "evidence_id": None,
                        "anchor_text": "submitted an indication of interest",
                    }
                ],
                "terms": None,
                "formality_signals": None,
                "whole_company_scope": True,
                "drop_reason_text": None,
                "round_scope": None,
                "invited_actor_ids": [],
                "deadline_date": None,
                "executed_with_actor_id": "party_a",
                "boundary_note": None,
                "nda_signed": None,
                "notes": [],
            },
        ],
        "exclusions": [],
        "coverage_notes": [],
    }

    (extract_dir / "actors_raw.json").write_text(json.dumps(actors_payload), encoding="utf-8")
    (extract_dir / "events_raw.json").write_text(json.dumps(events_payload), encoding="utf-8")


def test_verify_treats_fuzzy_match_as_unresolved(tmp_path: Path) -> None:
    _write_verify_fixture_for_fuzzy_only_match(tmp_path)
    exit_code = run_verify("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    findings = _read_findings_list(paths.verification_findings_path)

    assert exit_code == 1
    assert len(findings) >= 1
    assert findings[0]["check_type"] == "quote_verification"
    assert findings[0]["repairability"] == "repairable"


def test_verify_promotes_expanded_exact_match_over_initial_fuzzy_match() -> None:
    anchor_text = "Party A submitted a bid on July 5 (preliminary)"
    raw_lines = [
        "Party A submitted a bid on July 5.",
        "Party A submitted a bid on July 5 (preliminary).",
    ]

    match_type = _resolve_quote_match(
        raw_lines[0],
        anchor_text,
        raw_lines,
        1,
        1,
    )

    assert match_type == QuoteMatchType.EXACT


def test_verify_writes_compatible_pass_log_without_llm_repair(tmp_path: Path) -> None:
    _write_verify_fixture_for_clean_pass(tmp_path)
    exit_code = run_verify("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    log = json.loads(paths.verification_log_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert log["summary"]["status"] == "pass"
    assert log["summary"]["total_checks"] == 9
    assert "round_1" in log
    assert "round_2" in log


def test_verify_reports_missing_actor_reference(tmp_path: Path) -> None:
    _write_verify_fixture_for_clean_pass(tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    events_payload = json.loads(paths.events_raw_path.read_text(encoding="utf-8"))
    events_payload["events"][0]["actor_ids"] = ["missing_actor"]
    paths.events_raw_path.write_text(json.dumps(events_payload), encoding="utf-8")

    exit_code = run_verify("imprivata", project_root=tmp_path)
    findings = _read_findings_list(paths.verification_findings_path)

    assert exit_code == 1
    assert any(
        finding["check_type"] == "referential_integrity"
        and finding["event_ids"] == ["evt_001"]
        for finding in findings
    )


def test_verify_reports_missing_executed_with_actor_reference(tmp_path: Path) -> None:
    _write_verify_fixture_for_clean_pass(tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    events_payload = json.loads(paths.events_raw_path.read_text(encoding="utf-8"))
    events_payload["events"][1]["actor_ids"] = []
    events_payload["events"][1]["executed_with_actor_id"] = "missing_actor"
    paths.events_raw_path.write_text(json.dumps(events_payload), encoding="utf-8")

    exit_code = run_verify("imprivata", project_root=tmp_path)
    findings = _read_findings_list(paths.verification_findings_path)

    assert exit_code == 1
    assert any(
        finding["check_type"] == "referential_integrity"
        and finding["event_ids"] == ["evt_002"]
        and "executed_with_actor_id" in finding["description"]
        for finding in findings
    )


def test_verify_reports_structural_failure_for_empty_proposal_actor_ids(tmp_path: Path) -> None:
    _write_verify_fixture_for_clean_pass(tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    events_payload = json.loads(paths.events_raw_path.read_text(encoding="utf-8"))
    events_payload["events"] = [
        {
            "event_id": "evt_003",
            "event_type": "proposal",
            "date": {"raw_text": "July 5, 2016", "normalized_hint": "2016-07-05"},
            "actor_ids": [],
            "summary": "Proposal with no linked actor.",
            "evidence_refs": [
                {
                    "block_id": "B001",
                    "evidence_id": None,
                    "anchor_text": "submitted an indication of interest",
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
            "nda_signed": None,
            "notes": [],
        }
    ]
    paths.events_raw_path.write_text(json.dumps(events_payload), encoding="utf-8")

    exit_code = run_verify("imprivata", project_root=tmp_path)
    findings = _read_findings_list(paths.verification_findings_path)

    assert exit_code == 1
    assert any(
        finding["check_type"] == "structural_integrity"
        and finding["event_ids"] == ["evt_003"]
        and finding["description"] == "Proposal events must have non-empty actor_ids."
        for finding in findings
    )
