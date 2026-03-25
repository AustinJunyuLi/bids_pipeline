from __future__ import annotations

import json
from pathlib import Path

import pytest

from skill_pipeline import cli
from skill_pipeline.deal_agent import run_deal_agent
from skill_pipeline.raw.fetch import text_sha256


def _write_shared_inputs(tmp_path: Path, *, slug: str = "imprivata") -> None:
    data_dir = tmp_path / "data"
    deals_source_dir = data_dir / "deals" / slug / "source"
    raw_dir = tmp_path / "raw" / slug
    filings_dir = raw_dir / "filings"
    deals_source_dir.mkdir(parents=True, exist_ok=True)
    filings_dir.mkdir(parents=True, exist_ok=True)

    (data_dir / "seeds.csv").write_text(
        (
            "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
            f"{slug},IMPRIVATA INC,THOMA BRAVO LLC,2016-07-13,https://example.com,false\n"
        ),
        encoding="utf-8",
    )
    filing_text = "\n".join(
        [
            "Background of the Merger",
            "Party A signed a confidentiality agreement.",
            "Party A submitted an indication of interest.",
        ]
    )
    (filings_dir / "DOC001.txt").write_text(filing_text, encoding="utf-8")
    (deals_source_dir / "chronology_blocks.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "block_id": "B001",
                        "document_id": "DOC001",
                        "ordinal": 1,
                        "start_line": 1,
                        "end_line": 2,
                        "raw_text": "Background of the Merger\nParty A signed a confidentiality agreement.",
                        "clean_text": "Background of the Merger Party A signed a confidentiality agreement.",
                        "is_heading": False,
                        "page_break_before": False,
                        "page_break_after": False,
                    }
                ),
                json.dumps(
                    {
                        "block_id": "B002",
                        "document_id": "DOC001",
                        "ordinal": 2,
                        "start_line": 3,
                        "end_line": 3,
                        "raw_text": "Party A submitted an indication of interest.",
                        "clean_text": "Party A submitted an indication of interest.",
                        "is_heading": False,
                        "page_break_before": False,
                        "page_break_after": False,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (deals_source_dir / "evidence_items.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "evidence_id": "DOC001:E0001",
                        "document_id": "DOC001",
                        "accession_number": "DOC001",
                        "filing_type": "DEFM14A",
                        "start_line": 2,
                        "end_line": 2,
                        "raw_text": "Party A signed a confidentiality agreement.",
                        "evidence_type": "dated_action",
                        "confidence": "high",
                        "matched_terms": ["confidentiality agreement"],
                        "date_text": None,
                        "actor_hint": "Party A",
                        "value_hint": None,
                        "note": None,
                    }
                ),
                json.dumps(
                    {
                        "evidence_id": "DOC001:E0002",
                        "document_id": "DOC001",
                        "accession_number": "DOC001",
                        "filing_type": "DEFM14A",
                        "start_line": 3,
                        "end_line": 3,
                        "raw_text": "Party A submitted an indication of interest.",
                        "evidence_type": "dated_action",
                        "confidence": "high",
                        "matched_terms": ["submitted", "indication of interest"],
                        "date_text": None,
                        "actor_hint": "Party A",
                        "value_hint": None,
                        "note": None,
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (raw_dir / "document_registry.json").write_text(
        json.dumps(
            {
                "artifact_type": "raw_document_registry",
                "run_id": "run-1",
                "deal_slug": slug,
                "documents": [
                    {
                        "document_id": "DOC001",
                        "accession_number": "DOC001",
                        "filing_type": "DEFM14A",
                        "txt_path": f"raw/{slug}/filings/DOC001.txt",
                        "sha256_txt": text_sha256(filing_text),
                        "byte_count_txt": len(filing_text.encode("utf-8")),
                        "fetched_at": "2026-03-20T00:00:00Z",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _write_skill_outputs(tmp_path: Path, *, slug: str = "imprivata") -> Path:
    skill_root = tmp_path / "data" / "skill" / slug
    extract_dir = skill_root / "extract"
    coverage_dir = skill_root / "coverage"
    verify_dir = skill_root / "verify"
    enrich_dir = skill_root / "enrich"
    export_dir = skill_root / "export"
    extract_dir.mkdir(parents=True, exist_ok=True)
    coverage_dir.mkdir(parents=True, exist_ok=True)
    verify_dir.mkdir(parents=True, exist_ok=True)
    enrich_dir.mkdir(parents=True, exist_ok=True)
    export_dir.mkdir(parents=True, exist_ok=True)

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
                        "anchor_text": "Party A",
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
                "event_type": "nda",
                "date": {"raw_text": "July 1, 2016", "normalized_hint": "2016-07-01"},
                "actor_ids": ["party_a"],
                "summary": "Party A signed a confidentiality agreement.",
                "evidence_refs": [
                    {
                        "block_id": "B001",
                        "evidence_id": None,
                        "anchor_text": "signed a confidentiality agreement",
                    }
                ],
                "terms": None,
                "formality_signals": None,
                "whole_company_scope": None,
                "drop_reason_text": None,
                "round_scope": None,
                "invited_actor_ids": [],
                "deadline_date": None,
                "executed_with_actor_id": None,
                "boundary_note": None,
                "nda_signed": True,
                "notes": [],
            },
            {
                "event_id": "evt_002",
                "event_type": "proposal",
                "date": {"raw_text": "July 5, 2016", "normalized_hint": "2016-07-05"},
                "actor_ids": ["party_a"],
                "summary": "Party A submitted an indication of interest.",
                "evidence_refs": [
                    {
                        "block_id": "B002",
                        "evidence_id": None,
                        "anchor_text": "indication of interest",
                    }
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
            },
        ],
        "exclusions": [],
        "coverage_notes": [
            "nda: extracted (evt_001)",
            "proposal: extracted (evt_002)",
        ],
    }
    verification_payload = {
        "round_1": {
            "findings": [
                {
                    "check_type": "quote_verification",
                    "severity": "error",
                    "description": "anchor_text not found within +/-3 lines of block B002",
                    "event_id": "evt_002",
                    "anchor_text": "indication of interest",
                }
            ],
            "fixes_applied": [
                {
                    "finding_index": 0,
                    "action": "Updated anchor_text to exact substring from source filing",
                    "old_value": "indication of interest",
                    "new_value": "submitted an indication of interest",
                }
            ],
        },
        "round_2": {
            "findings": [],
            "status": "pass",
        },
        "summary": {
            "total_checks": 7,
            "round_1_errors": 1,
            "round_1_warnings": 0,
            "fixes_applied": 1,
            "round_2_errors": 0,
            "round_2_warnings": 0,
            "status": "pass",
        },
    }
    coverage_summary_payload = {
        "status": "pass",
        "finding_count": 1,
        "error_count": 0,
        "warning_count": 1,
        "counts_by_cue_family": {"advisor": 1},
    }
    enrichment_payload = {
        "dropout_classifications": {},
        "bid_classifications": {
            "evt_002": {
                "label": "Formal",
                "rule_applied": 2,
                "basis": "Proposal included formality signals.",
            }
        },
        "rounds": [],
        "cycles": [
            {
                "cycle_id": "cycle_1",
                "start_event_id": "evt_001",
                "end_event_id": "evt_002",
                "boundary_basis": "Single cycle -- no termination events",
            }
        ],
        "formal_boundary": {
            "cycle_1": {
                "event_id": "evt_002",
                "basis": "First formal proposal in cycle_1",
            }
        },
        "initiation_judgment": {
            "type": "bidder_driven",
            "basis": "Party A initiated the process.",
            "source_text": "Party A contacted the Company.",
            "confidence": "high",
        },
        "advisory_verification": {},
        "count_reconciliation": [],
        "review_flags": ["bid_classification_uncertain:evt_002"],
    }

    (extract_dir / "actors_raw.json").write_text(json.dumps(actors_payload), encoding="utf-8")
    (extract_dir / "events_raw.json").write_text(json.dumps(events_payload), encoding="utf-8")
    (coverage_dir / "coverage_summary.json").write_text(
        json.dumps(coverage_summary_payload),
        encoding="utf-8",
    )
    (verify_dir / "verification_log.json").write_text(
        json.dumps(verification_payload),
        encoding="utf-8",
    )
    (enrich_dir / "enrichment.json").write_text(json.dumps(enrichment_payload), encoding="utf-8")
    (export_dir / "deal_events.csv").write_text("header\nrow\n", encoding="utf-8")
    return skill_root


def test_skill_cli_supports_deal_agent_subcommand():
    parser = cli.build_parser()
    args = parser.parse_args(["deal-agent", "--deal", "imprivata"])

    assert args.command == "deal-agent"
    assert args.deal == "imprivata"


def test_run_deal_agent_creates_isolated_skill_directories_and_reports_missing_stage_outputs(
    tmp_path: Path,
):
    _write_shared_inputs(tmp_path)

    summary = run_deal_agent("imprivata", project_root=tmp_path)

    skill_root = tmp_path / "data" / "skill" / "imprivata"
    assert skill_root.exists()
    assert (skill_root / "extract").is_dir()
    assert (skill_root / "verify").is_dir()
    assert (skill_root / "enrich").is_dir()
    assert (skill_root / "export").is_dir()

    assert summary.seed.deal_slug == "imprivata"
    assert summary.seed.target_name == "IMPRIVATA INC"
    assert summary.paths.skill_root == skill_root
    assert summary.paths.source_dir == tmp_path / "data" / "deals" / "imprivata" / "source"
    assert summary.extract.status == "missing"
    assert summary.coverage.status == "missing"
    assert summary.verify.status == "missing"
    assert summary.enrich.status == "missing"
    assert summary.export.status == "missing"


def test_run_deal_agent_raises_when_prerequisites_are_missing(tmp_path: Path):
    data_dir = tmp_path / "data"
    (data_dir / "seeds.csv").parent.mkdir(parents=True, exist_ok=True)
    (data_dir / "seeds.csv").write_text(
        (
            "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
            "imprivata,IMPRIVATA INC,THOMA BRAVO LLC,2016-07-13,https://example.com,false\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError, match="Missing required skill inputs"):
        run_deal_agent("imprivata", project_root=tmp_path)


def test_run_deal_agent_summarizes_existing_skill_artifacts(tmp_path: Path):
    _write_shared_inputs(tmp_path)
    skill_root = _write_skill_outputs(tmp_path)

    summary = run_deal_agent("imprivata", project_root=tmp_path)

    assert summary.paths.skill_root == skill_root
    assert summary.extract.status == "pass"
    assert summary.extract.actor_count == 1
    assert summary.extract.event_count == 2
    assert summary.extract.proposal_count == 1
    assert summary.coverage.status == "pass"
    assert summary.coverage.error_count == 0
    assert summary.coverage.warning_count == 1
    assert summary.verify.status == "pass"
    assert summary.verify.round_1_errors == 1
    assert summary.verify.fixes_applied == 1
    assert summary.verify.round_2_status == "pass"
    assert summary.enrich.status == "pass"
    assert summary.enrich.cycle_count == 1
    assert summary.enrich.formal_bid_count == 1
    assert summary.enrich.informal_bid_count == 0
    assert summary.enrich.initiation_judgment_type == "bidder_driven"
    assert summary.enrich.review_flags_count == 1
    assert summary.export.status == "pass"
    assert summary.export.output_path == skill_root / "export" / "deal_events.csv"


def test_run_deal_agent_reports_deterministic_enrichment_when_interpretive_artifact_is_missing(
    tmp_path: Path,
):
    _write_shared_inputs(tmp_path)
    skill_root = _write_skill_outputs(tmp_path)
    enrich_dir = skill_root / "enrich"
    (enrich_dir / "enrichment.json").unlink()
    (enrich_dir / "deterministic_enrichment.json").write_text(
        json.dumps(
            {
                "rounds": [],
                "bid_classifications": {
                    "evt_002": {
                        "label": "Formal",
                        "rule_applied": 2,
                        "basis": "Proposal included formality signals.",
                    }
                },
                "cycles": [
                    {
                        "cycle_id": "cycle_1",
                        "start_event_id": "evt_001",
                        "end_event_id": "evt_002",
                        "boundary_basis": "Single cycle -- no termination events",
                    }
                ],
                "formal_boundary": {
                    "cycle_1": {
                        "event_id": "evt_002",
                        "basis": "First formal proposal in cycle: evt_002.",
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    summary = run_deal_agent("imprivata", project_root=tmp_path)

    assert summary.enrich.status == "pass"
    assert summary.enrich.cycle_count == 1
    assert summary.enrich.formal_bid_count == 1
    assert summary.enrich.informal_bid_count == 0
    assert summary.enrich.initiation_judgment_type is None
    assert summary.enrich.review_flags_count == 0


def test_run_deal_agent_fails_on_invalid_deterministic_enrichment_artifact(tmp_path: Path) -> None:
    _write_shared_inputs(tmp_path)
    skill_root = _write_skill_outputs(tmp_path)
    enrich_dir = skill_root / "enrich"
    (enrich_dir / "enrichment.json").unlink()
    (enrich_dir / "deterministic_enrichment.json").write_text("{}", encoding="utf-8")

    summary = run_deal_agent("imprivata", project_root=tmp_path)

    assert summary.enrich.status == "fail"


def test_run_deal_agent_fails_on_header_only_export(tmp_path: Path) -> None:
    _write_shared_inputs(tmp_path)
    skill_root = _write_skill_outputs(tmp_path)
    (skill_root / "export" / "deal_events.csv").write_text("header\n", encoding="utf-8")

    summary = run_deal_agent("imprivata", project_root=tmp_path)

    assert summary.export.status == "fail"
