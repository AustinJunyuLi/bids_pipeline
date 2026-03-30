from __future__ import annotations

import json
from pathlib import Path

import pytest

from skill_pipeline import cli
from skill_pipeline.compose_prompts import run_compose_prompts
from skill_pipeline.db_schema import open_pipeline_db
from skill_pipeline.deal_agent import run_deal_agent
from skill_pipeline.paths import build_skill_paths, ensure_output_directories


def _write_shared_inputs(tmp_path: Path, *, slug: str = "imprivata") -> None:
    data_dir = tmp_path / "data"
    deals_source_dir = data_dir / "deals" / slug / "source"
    raw_dir = tmp_path / "raw" / slug
    deals_source_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    (data_dir / "seeds.csv").write_text(
        (
            "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
            f"{slug},IMPRIVATA INC,THOMA BRAVO LLC,2016-07-13,https://example.com,false\n"
        ),
        encoding="utf-8",
    )
    (deals_source_dir / "chronology_blocks.jsonl").write_text(
        json.dumps({
            "block_id": "B001", "document_id": "DOC001", "ordinal": 1,
            "start_line": 1, "end_line": 1, "raw_text": "x", "clean_text": "x",
            "is_heading": False, "page_break_before": False, "page_break_after": False,
            "date_mentions": [], "entity_mentions": [], "evidence_density": 0,
            "temporal_phase": "other",
        }) + "\n",
        encoding="utf-8",
    )
    (deals_source_dir / "evidence_items.jsonl").write_text("", encoding="utf-8")
    (raw_dir / "document_registry.json").write_text("{}", encoding="utf-8")


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
        "quotes": [
            {
                "quote_id": "Q001",
                "block_id": "B001",
                "text": "Party A",
            }
        ],
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
                "quote_ids": ["Q001"],
                "notes": [],
            }
        ],
        "count_assertions": [],
        "unresolved_mentions": [],
    }
    events_payload = {
        "quotes": [
            {
                "quote_id": "Q101",
                "block_id": "B001",
                "text": "signed a confidentiality agreement",
            },
            {
                "quote_id": "Q102",
                "block_id": "B002",
                "text": "indication of interest",
            },
        ],
        "events": [
            {
                "event_id": "evt_001",
                "event_type": "nda",
                "date": {"raw_text": "July 1, 2016", "normalized_hint": "2016-07-01"},
                "actor_ids": ["party_a"],
                "summary": "Party A signed a confidentiality agreement.",
                "quote_ids": ["Q101"],
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
                "quote_ids": ["Q102"],
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
    deterministic_enrichment_payload = {
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
        "dropout_classifications": {},
        "all_cash_overrides": {},
    }
    interpretive_enrichment_payload = {
        "dropout_classifications": {},
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
    (enrich_dir / "deterministic_enrichment.json").write_text(
        json.dumps(deterministic_enrichment_payload),
        encoding="utf-8",
    )
    (enrich_dir / "enrichment.json").write_text(
        json.dumps(interpretive_enrichment_payload),
        encoding="utf-8",
    )
    (export_dir / "deal_events.csv").write_text(
        (
            "TargetName,Events,Acquirer,DateAnnounced,URL\n"
            "IMPRIVATA INC,1,THOMA BRAVO LLC,2016-07-13,https://example.com\n"
            "Party A,Proposal,THOMA BRAVO LLC,2016-07-05,https://example.com\n"
        ),
        encoding="utf-8",
    )

    database_path = tmp_path / "data" / "pipeline.duckdb"
    con = open_pipeline_db(database_path)
    try:
        con.execute(
            """
            INSERT INTO actors (
                deal_slug,
                actor_id,
                display_name,
                canonical_name,
                aliases,
                role,
                advisor_kind,
                advised_actor_id,
                bidder_kind,
                listing_status,
                geography,
                is_grouped,
                group_size,
                group_label,
                evidence_span_ids
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                slug,
                "party_a",
                "Party A",
                "PARTY A",
                [],
                "bidder",
                None,
                None,
                "financial",
                "private",
                "domestic",
                False,
                None,
                None,
                ["span_001"],
            ],
        )
        con.executemany(
            """
            INSERT INTO events (
                deal_slug,
                event_id,
                event_type,
                date_raw_text,
                date_sort,
                date_precision,
                actor_ids,
                summary,
                evidence_span_ids,
                terms_per_share,
                terms_range_low,
                terms_range_high,
                terms_consideration_type,
                whole_company_scope,
                drop_reason_text,
                round_scope,
                invited_actor_ids,
                executed_with_actor_id,
                nda_signed
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                [
                    slug,
                    "evt_001",
                    "nda",
                    "July 1, 2016",
                    "2016-07-01",
                    "exact",
                    ["party_a"],
                    "Party A signed a confidentiality agreement.",
                    ["span_001"],
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    [],
                    None,
                    True,
                ],
                [
                    slug,
                    "evt_002",
                    "proposal",
                    "July 5, 2016",
                    "2016-07-05",
                    "exact",
                    ["party_a"],
                    "Party A submitted an indication of interest.",
                    ["span_002"],
                    25.0,
                    None,
                    None,
                    "cash",
                    True,
                    None,
                    None,
                    [],
                    None,
                    None,
                ],
            ],
        )
        con.executemany(
            """
            INSERT INTO spans (
                deal_slug,
                span_id,
                document_id,
                filing_type,
                start_line,
                end_line,
                block_ids,
                quote_text,
                match_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                [
                    slug,
                    "span_001",
                    "DOC001",
                    "DEFM14A",
                    1,
                    1,
                    ["B001"],
                    "signed a confidentiality agreement",
                    "exact",
                ],
                [
                    slug,
                    "span_002",
                    "DOC001",
                    "DEFM14A",
                    2,
                    2,
                    ["B002"],
                    "submitted an indication of interest",
                    "exact",
                ],
            ],
        )
    finally:
        con.close()
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
    assert summary.db_load.status == "missing"
    assert summary.db_export.status == "missing"
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
    assert summary.db_load.status == "pass"
    assert summary.db_load.actor_rows == 1
    assert summary.db_load.event_rows == 2
    assert summary.db_load.span_rows == 2
    assert summary.db_export.status == "pass"
    assert summary.db_export.event_rows == 1
    assert summary.db_export.output_path == skill_root / "export" / "deal_events.csv"
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
                "dropout_classifications": {},
                "all_cash_overrides": {},
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


def test_run_deal_agent_marks_enrich_fail_when_interpretive_artifact_is_malformed(
    tmp_path: Path,
) -> None:
    _write_shared_inputs(tmp_path)
    skill_root = _write_skill_outputs(tmp_path)
    enrich_dir = skill_root / "enrich"
    (enrich_dir / "enrichment.json").write_text(
        json.dumps({"dropout_classifications": {}}),
        encoding="utf-8",
    )

    summary = run_deal_agent("imprivata", project_root=tmp_path)

    assert summary.enrich.status == "fail"
    assert summary.enrich.cycle_count == 1
    assert summary.enrich.formal_bid_count == 1
    assert summary.enrich.informal_bid_count == 0
    assert summary.enrich.initiation_judgment_type is None
    assert summary.enrich.review_flags_count == 0


# --- Prompt path and compose-prompts tests ---


def test_prompt_paths_exposed_by_build_skill_paths(tmp_path: Path) -> None:
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    skill_root = tmp_path / "data" / "skill" / "imprivata"
    assert paths.prompt_dir == skill_root / "prompt"
    assert paths.prompt_packets_dir == skill_root / "prompt" / "packets"
    assert paths.prompt_manifest_path == skill_root / "prompt" / "manifest.json"


def test_ensure_output_directories_creates_prompt_dirs(tmp_path: Path) -> None:
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    ensure_output_directories(paths)
    assert paths.prompt_dir.is_dir()
    assert paths.prompt_packets_dir.is_dir()


def test_compose_prompts_cli_subcommand_parses() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(["compose-prompts", "--deal", "stec"])
    assert args.command == "compose-prompts"
    assert args.deal == "stec"
    assert args.mode == "all"
    assert args.chunk_budget == 6000


def test_compose_prompts_cli_custom_args() -> None:
    parser = cli.build_parser()
    args = parser.parse_args([
        "compose-prompts", "--deal", "imprivata",
        "--mode", "actors", "--chunk-budget", "4000",
    ])
    assert args.mode == "actors"
    assert args.chunk_budget == 4000


def test_compose_prompts_fails_when_chronology_blocks_missing(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    source_dir = data_dir / "deals" / "imprivata" / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    # Write evidence_items but NOT chronology_blocks
    (source_dir / "evidence_items.jsonl").write_text("", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="chronology_blocks"):
        run_compose_prompts("imprivata", project_root=tmp_path)


def test_compose_prompts_fails_when_evidence_items_missing(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    source_dir = data_dir / "deals" / "imprivata" / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    # Write chronology_blocks but NOT evidence_items
    (source_dir / "chronology_blocks.jsonl").write_text(
        json.dumps({
            "block_id": "B001", "document_id": "DOC001", "ordinal": 1,
            "start_line": 1, "end_line": 1, "raw_text": "x", "clean_text": "x",
            "is_heading": False, "page_break_before": False, "page_break_after": False,
            "date_mentions": [], "entity_mentions": [], "evidence_density": 0,
            "temporal_phase": "other",
        }) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError, match="evidence_items"):
        run_compose_prompts("imprivata", project_root=tmp_path)


def test_compose_prompts_writes_valid_manifest(tmp_path: Path) -> None:
    _write_shared_inputs(tmp_path)
    manifest = run_compose_prompts("imprivata", project_root=tmp_path)
    assert manifest.deal_slug == "imprivata"
    assert manifest.artifact_type == "prompt_packet_manifest"

    # Verify manifest file was written to disk
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    assert paths.prompt_manifest_path.exists()

    # Verify manifest can be re-loaded from disk
    from skill_pipeline.pipeline_models.prompt import PromptPacketManifest

    loaded = PromptPacketManifest.model_validate_json(
        paths.prompt_manifest_path.read_text(encoding="utf-8")
    )
    assert loaded.deal_slug == "imprivata"
    assert loaded.run_id == manifest.run_id


def test_compose_prompts_creates_prompt_directories(tmp_path: Path) -> None:
    _write_shared_inputs(tmp_path)
    run_compose_prompts("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    assert paths.prompt_dir.is_dir()
    assert paths.prompt_packets_dir.is_dir()


# --- Prompt-stage status in deal-agent ---


def test_deal_agent_prompt_stage_missing_when_no_manifest(tmp_path: Path) -> None:
    """deal-agent reports prompt stage as missing when manifest does not exist."""
    _write_shared_inputs(tmp_path)
    summary = run_deal_agent("imprivata", project_root=tmp_path)
    assert summary.prompt.status == "missing"
    assert summary.prompt.packet_count == 0


def test_deal_agent_prompt_stage_pass_after_compose(tmp_path: Path) -> None:
    """deal-agent reports prompt stage as pass with packet counts after compose."""
    _write_shared_inputs(tmp_path)
    run_compose_prompts("imprivata", project_root=tmp_path, mode="actors")
    summary = run_deal_agent("imprivata", project_root=tmp_path)
    assert summary.prompt.status == "pass"
    assert summary.prompt.packet_count > 0
    assert summary.prompt.actor_packet_count > 0
    assert summary.prompt.event_packet_count == 0


# --- Prompt packet validator tests ---


def test_validate_prompt_packets_passes_on_valid_manifest(tmp_path: Path) -> None:
    """Validator returns no errors on well-formed prompt packets."""
    from scripts.validate_prompt_packets import validate_manifest

    _write_shared_inputs(tmp_path)
    run_compose_prompts("imprivata", project_root=tmp_path, mode="actors")
    errors = validate_manifest("imprivata", project_root=tmp_path, expect_sections=True)
    assert errors == []


def test_validate_prompt_packets_fails_when_manifest_missing(tmp_path: Path) -> None:
    """Validator returns an error when manifest.json does not exist."""
    from scripts.validate_prompt_packets import validate_manifest

    errors = validate_manifest("imprivata", project_root=tmp_path)
    assert len(errors) == 1
    assert "Manifest not found" in errors[0]


def test_validate_prompt_packets_detects_missing_rendered_file(tmp_path: Path) -> None:
    """Validator detects a missing rendered.md file referenced by the manifest."""
    from scripts.validate_prompt_packets import validate_manifest

    _write_shared_inputs(tmp_path)
    manifest = run_compose_prompts("imprivata", project_root=tmp_path, mode="actors")
    # Remove the rendered file for the first packet
    first_rendered = Path(manifest.packets[0].rendered_path)
    first_rendered.unlink()
    errors = validate_manifest("imprivata", project_root=tmp_path, expect_sections=True)
    assert any("rendered file missing" in e for e in errors)


def test_validate_prompt_packets_cli_help_mentions_expect_sections() -> None:
    """CLI --help output includes the --expect-sections flag."""
    from scripts.validate_prompt_packets import parse_args

    import io
    import contextlib

    buf = io.StringIO()
    with pytest.raises(SystemExit):
        with contextlib.redirect_stdout(buf):
            parse_args(["--help"])
    assert "--expect-sections" in buf.getvalue()
