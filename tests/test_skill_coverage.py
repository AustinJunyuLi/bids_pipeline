"""Tests for the deterministic coverage stage."""

from __future__ import annotations

import json
from pathlib import Path

from skill_pipeline import cli
from skill_pipeline.coverage import run_coverage
from skill_pipeline.paths import build_skill_paths


def _write_coverage_fixture(
    tmp_path: Path,
    *,
    slug: str = "imprivata",
    evidence_items: list[dict],
    chronology_blocks: list[dict] | None = None,
    actors_payload: dict | None = None,
    events_payload: dict | None = None,
    spans_payload: dict | None = None,
) -> None:
    data_dir = tmp_path / "data"
    source_dir = data_dir / "deals" / slug / "source"
    extract_dir = data_dir / "skill" / slug / "extract"
    source_dir.mkdir(parents=True, exist_ok=True)
    extract_dir.mkdir(parents=True, exist_ok=True)

    if chronology_blocks is None:
        chronology_blocks = [
            {
                "block_id": "B001",
                "document_id": "DOC001",
                "ordinal": 1,
                "start_line": 1,
                "end_line": 1,
                "raw_text": evidence_items[0]["raw_text"],
                "clean_text": evidence_items[0]["raw_text"],
                "is_heading": False,
                "page_break_before": False,
                "page_break_after": False,
                "date_mentions": [],
                "entity_mentions": [],
                "evidence_density": 0,
                "temporal_phase": "other",
            }
        ]

    if actors_payload is None:
        actors_payload = {"actors": [], "count_assertions": [], "unresolved_mentions": []}
    if events_payload is None:
        events_payload = {"events": [], "exclusions": [], "coverage_notes": []}

    (data_dir / "seeds.csv").write_text(
        (
            "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
            f"{slug},IMPRIVATA INC,THOMA BRAVO LLC,2016-07-13,https://example.com,false\n"
        ),
        encoding="utf-8",
    )
    (source_dir / "chronology_blocks.jsonl").write_text(
        "\n".join(json.dumps(block) for block in chronology_blocks) + "\n",
        encoding="utf-8",
    )
    (source_dir / "evidence_items.jsonl").write_text(
        "\n".join(json.dumps(item) for item in evidence_items) + "\n",
        encoding="utf-8",
    )
    (extract_dir / "actors_raw.json").write_text(json.dumps(actors_payload), encoding="utf-8")
    (extract_dir / "events_raw.json").write_text(json.dumps(events_payload), encoding="utf-8")
    if spans_payload is not None:
        (extract_dir / "spans.json").write_text(json.dumps(spans_payload), encoding="utf-8")


def test_coverage_reports_uncovered_high_confidence_proposal_cue(tmp_path: Path) -> None:
    evidence_items = [
        {
            "evidence_id": "DOC001:E0001",
            "document_id": "DOC001",
            "accession_number": "DOC001",
            "filing_type": "DEFM14A",
            "start_line": 1,
            "end_line": 1,
            "raw_text": "Party A submitted an indication of interest.",
            "evidence_type": "dated_action",
            "confidence": "high",
            "matched_terms": ["submitted", "indication of interest"],
            "date_text": "July 5, 2016",
            "actor_hint": "Party A",
            "value_hint": None,
            "note": None,
        }
    ]
    events_payload = {
        "events": [],
        "exclusions": [],
        "coverage_notes": [],
    }
    _write_coverage_fixture(tmp_path, evidence_items=evidence_items, events_payload=events_payload)

    exit_code = run_coverage("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    findings = json.loads(paths.coverage_findings_path.read_text(encoding="utf-8"))
    summary = json.loads(paths.coverage_summary_path.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert summary["status"] == "fail"
    assert summary["error_count"] == 1
    assert findings["findings"][0]["cue_family"] == "proposal"
    assert findings["findings"][0]["severity"] == "error"
    assert findings["findings"][0]["block_ids"] == ["B001"]
    assert findings["findings"][0]["suggested_event_types"] == ["proposal"]


def test_coverage_passes_when_canonical_proposal_span_covers_cue(tmp_path: Path) -> None:
    evidence_items = [
        {
            "evidence_id": "DOC001:E0001",
            "document_id": "DOC001",
            "accession_number": "DOC001",
            "filing_type": "DEFM14A",
            "start_line": 1,
            "end_line": 1,
            "raw_text": "Party A submitted an indication of interest.",
            "evidence_type": "dated_action",
            "confidence": "high",
            "matched_terms": ["submitted", "indication of interest"],
            "date_text": "July 5, 2016",
            "actor_hint": "Party A",
            "value_hint": None,
            "note": None,
        }
    ]
    events_payload = {
        "events": [
            {
                "event_id": "evt_001",
                "event_type": "proposal",
                "date": {
                    "raw_text": "July 5, 2016",
                    "normalized_start": "2016-07-05",
                    "normalized_end": "2016-07-05",
                    "sort_date": "2016-07-05",
                    "precision": "exact_day",
                    "anchor_event_id": None,
                    "anchor_span_id": None,
                    "resolution_note": None,
                    "is_inferred": False,
                },
                "actor_ids": ["party_a"],
                "summary": "Party A submitted an indication of interest.",
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
                "evidence_span_ids": [],
                "notes": [],
            }
        ],
        "count_assertions": [],
        "unresolved_mentions": [],
    }
    spans_payload = {
        "spans": [
            {
                "span_id": "span_0001",
                "document_id": "DOC001",
                "accession_number": "DOC001",
                "filing_type": "DEFM14A",
                "start_line": 1,
                "end_line": 1,
                "start_char": 8,
                "end_char": 43,
                "block_ids": ["B001"],
                "evidence_ids": ["DOC001:E0001"],
                "anchor_text": "submitted an indication of interest",
                "quote_text": "Party A submitted an indication of interest.",
                "quote_text_normalized": "party a submitted an indication of interest.",
                "match_type": "exact",
                "resolution_note": None,
            }
        ]
    }
    _write_coverage_fixture(
        tmp_path,
        evidence_items=evidence_items,
        actors_payload=actors_payload,
        events_payload=events_payload,
        spans_payload=spans_payload,
    )

    exit_code = run_coverage("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    findings = json.loads(paths.coverage_findings_path.read_text(encoding="utf-8"))
    summary = json.loads(paths.coverage_summary_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert findings["findings"] == []
    assert summary["status"] == "pass"
    assert summary["error_count"] == 0


def test_coverage_warns_on_uncovered_medium_confidence_advisor_cue(tmp_path: Path) -> None:
    evidence_items = [
        {
            "evidence_id": "DOC001:E0001",
            "document_id": "DOC001",
            "accession_number": "DOC001",
            "filing_type": "DEFM14A",
            "start_line": 1,
            "end_line": 1,
            "raw_text": "The Company retained Goldman Sachs as financial advisor.",
            "evidence_type": "actor_identification",
            "confidence": "medium",
            "matched_terms": ["retained", "financial advisor"],
            "date_text": None,
            "actor_hint": "Goldman Sachs",
            "value_hint": None,
            "note": None,
        }
    ]
    _write_coverage_fixture(tmp_path, evidence_items=evidence_items)

    exit_code = run_coverage("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    findings = json.loads(paths.coverage_findings_path.read_text(encoding="utf-8"))
    summary = json.loads(paths.coverage_summary_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert summary["status"] == "pass"
    assert summary["warning_count"] == 1
    assert findings["findings"][0]["cue_family"] == "advisor"
    assert findings["findings"][0]["severity"] == "warning"


def test_coverage_ignores_evidence_outside_chronology_blocks(tmp_path: Path) -> None:
    evidence_items = [
        {
            "evidence_id": "DOC001:E0001",
            "document_id": "DOC001",
            "accession_number": "DOC001",
            "filing_type": "DEFM14A",
            "start_line": 50,
            "end_line": 50,
            "raw_text": "The merger agreement is subject to shareholder approval.",
            "evidence_type": "outcome_fact",
            "confidence": "high",
            "matched_terms": ["merger agreement", "vote"],
            "date_text": None,
            "actor_hint": None,
            "value_hint": None,
            "note": None,
        }
    ]
    chronology_blocks = [
        {
            "block_id": "B001",
            "document_id": "DOC001",
            "ordinal": 1,
            "start_line": 1,
            "end_line": 5,
            "raw_text": "Background of the merger.",
            "clean_text": "Background of the merger.",
            "is_heading": False,
            "page_break_before": False,
            "page_break_after": False,
            "date_mentions": [],
            "entity_mentions": [],
            "evidence_density": 0,
            "temporal_phase": "other",
        }
    ]
    _write_coverage_fixture(
        tmp_path,
        evidence_items=evidence_items,
        chronology_blocks=chronology_blocks,
    )

    exit_code = run_coverage("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    findings = json.loads(paths.coverage_findings_path.read_text(encoding="utf-8"))
    summary = json.loads(paths.coverage_summary_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert findings["findings"] == []
    assert summary["status"] == "pass"


def test_coverage_does_not_treat_draft_nda_as_signed_nda_cue(tmp_path: Path) -> None:
    evidence_items = [
        {
            "evidence_id": "DOC001:E0001",
            "document_id": "DOC001",
            "accession_number": "DOC001",
            "filing_type": "DEFM14A",
            "start_line": 1,
            "end_line": 1,
            "raw_text": "Company A sent a draft non-disclosure agreement for a possible transaction.",
            "evidence_type": "dated_action",
            "confidence": "high",
            "matched_terms": ["sent", "proposed"],
            "date_text": "July 5, 2016",
            "actor_hint": "Company A",
            "value_hint": None,
            "note": None,
        }
    ]
    _write_coverage_fixture(tmp_path, evidence_items=evidence_items)

    exit_code = run_coverage("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    findings = json.loads(paths.coverage_findings_path.read_text(encoding="utf-8"))
    summary = json.loads(paths.coverage_summary_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert findings["findings"] == []
    assert summary["status"] == "pass"


def test_coverage_does_not_treat_outcome_fact_as_proposal_cue(tmp_path: Path) -> None:
    evidence_items = [
        {
            "evidence_id": "DOC001:E0001",
            "document_id": "DOC001",
            "accession_number": "DOC001",
            "filing_type": "DEFM14A",
            "start_line": 1,
            "end_line": 1,
            "raw_text": "The merger agreement requires shareholder approval at the special meeting.",
            "evidence_type": "outcome_fact",
            "confidence": "high",
            "matched_terms": ["merger agreement", "vote"],
            "date_text": None,
            "actor_hint": None,
            "value_hint": None,
            "note": None,
        }
    ]
    _write_coverage_fixture(tmp_path, evidence_items=evidence_items)

    exit_code = run_coverage("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    findings = json.loads(paths.coverage_findings_path.read_text(encoding="utf-8"))
    summary = json.loads(paths.coverage_summary_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert findings["findings"] == []
    assert summary["status"] == "pass"


def test_coverage_reports_uncovered_second_proposal_cue_in_same_block(
    tmp_path: Path,
) -> None:
    chronology_blocks = [
        {
            "block_id": "B001",
            "document_id": "DOC001",
            "ordinal": 1,
            "start_line": 1,
            "end_line": 2,
            "raw_text": "Party A submitted an indication of interest.\nParty B submitted an indication of interest.",
            "clean_text": "Party A submitted an indication of interest. Party B submitted an indication of interest.",
            "is_heading": False,
            "page_break_before": False,
            "page_break_after": False,
            "date_mentions": [],
            "entity_mentions": [],
            "evidence_density": 0,
            "temporal_phase": "other",
        }
    ]
    evidence_items = [
        {
            "evidence_id": "DOC001:E0001",
            "document_id": "DOC001",
            "accession_number": "DOC001",
            "filing_type": "DEFM14A",
            "start_line": 1,
            "end_line": 1,
            "raw_text": "Party A submitted an indication of interest.",
            "evidence_type": "dated_action",
            "confidence": "high",
            "matched_terms": ["submitted", "indication of interest"],
            "date_text": "July 5, 2016",
            "actor_hint": "Party A",
            "value_hint": None,
            "note": None,
        },
        {
            "evidence_id": "DOC001:E0002",
            "document_id": "DOC001",
            "accession_number": "DOC001",
            "filing_type": "DEFM14A",
            "start_line": 2,
            "end_line": 2,
            "raw_text": "Party B submitted an indication of interest.",
            "evidence_type": "dated_action",
            "confidence": "high",
            "matched_terms": ["submitted", "indication of interest"],
            "date_text": "July 5, 2016",
            "actor_hint": "Party B",
            "value_hint": None,
            "note": None,
        },
    ]
    events_payload = {
        "events": [
            {
                "event_id": "evt_001",
                "event_type": "proposal",
                "date": {
                    "raw_text": "July 5, 2016",
                    "normalized_start": "2016-07-05",
                    "normalized_end": "2016-07-05",
                    "sort_date": "2016-07-05",
                    "precision": "exact_day",
                    "anchor_event_id": None,
                    "anchor_span_id": None,
                    "resolution_note": None,
                    "is_inferred": False,
                },
                "actor_ids": ["party_a"],
                "summary": "Party A submitted an indication of interest.",
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
                "evidence_span_ids": [],
                "notes": [],
            }
        ],
        "count_assertions": [],
        "unresolved_mentions": [],
    }
    spans_payload = {
        "spans": [
            {
                "span_id": "span_0001",
                "document_id": "DOC001",
                "accession_number": "DOC001",
                "filing_type": "DEFM14A",
                "start_line": 1,
                "end_line": 1,
                "start_char": 8,
                "end_char": 43,
                "block_ids": ["B001"],
                "evidence_ids": ["DOC001:E0001"],
                "anchor_text": "submitted an indication of interest",
                "quote_text": "Party A submitted an indication of interest.",
                "quote_text_normalized": "party a submitted an indication of interest.",
                "match_type": "exact",
                "resolution_note": None,
            }
        ]
    }
    _write_coverage_fixture(
        tmp_path,
        evidence_items=evidence_items,
        chronology_blocks=chronology_blocks,
        actors_payload=actors_payload,
        events_payload=events_payload,
        spans_payload=spans_payload,
    )

    exit_code = run_coverage("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    findings = json.loads(paths.coverage_findings_path.read_text(encoding="utf-8"))
    summary = json.loads(paths.coverage_summary_path.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert summary["status"] == "fail"
    assert summary["error_count"] == 1
    assert findings["findings"][0]["evidence_ids"] == ["DOC001:E0002"]


def test_skill_cli_supports_coverage_subcommand() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(["coverage", "--deal", "imprivata"])

    assert args.command == "coverage"
    assert args.deal == "imprivata"
