from __future__ import annotations

import json
from pathlib import Path

import pytest

from skill_pipeline import cli
from skill_pipeline.compose_prompts import run_compose_prompts
from skill_pipeline.db_export_v2 import run_db_export_v2
from skill_pipeline.db_load_v2 import run_db_load_v2
from skill_pipeline.deal_agent import run_deal_agent
from skill_pipeline.derive import run_derive
from skill_pipeline.paths import build_skill_paths, ensure_output_directories
from tests._v2_validation_fixtures import (
    canonical_observations_payload,
    spans_payload,
    write_v2_validation_reports,
)


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
            "block_id": "B001",
            "document_id": "DOC001",
            "ordinal": 1,
            "start_line": 1,
            "end_line": 1,
            "raw_text": "x",
            "clean_text": "x",
            "is_heading": False,
            "page_break_before": False,
            "page_break_after": False,
            "date_mentions": [],
            "entity_mentions": [],
            "evidence_density": 0,
            "temporal_phase": "other",
        }) + "\n",
        encoding="utf-8",
    )
    (deals_source_dir / "evidence_items.jsonl").write_text("", encoding="utf-8")
    (raw_dir / "document_registry.json").write_text("{}", encoding="utf-8")


def _write_skill_outputs(tmp_path: Path, *, slug: str = "imprivata") -> Path:
    skill_root = tmp_path / "data" / "skill" / slug
    paths = build_skill_paths(slug, project_root=tmp_path)
    paths.extract_v2_dir.mkdir(parents=True, exist_ok=True)
    paths.observations_path.write_text(
        json.dumps(canonical_observations_payload()),
        encoding="utf-8",
    )
    paths.spans_v2_path.write_text(
        json.dumps(spans_payload()),
        encoding="utf-8",
    )
    write_v2_validation_reports(
        tmp_path,
        slug=slug,
        coverage_findings=[
            {
                "cue_family": "sale_process",
                "status": "observed",
                "severity": "warning",
                "repairability": None,
                "description": "Sale process cue grounded by process observation.",
                "supporting_event_ids": [],
                "supporting_actor_ids": [],
                "supporting_span_ids": ["span_process"],
                "block_ids": [],
                "evidence_ids": [],
                "matched_terms": [],
                "confidence": "high",
                "suggested_event_types": [],
                "supporting_observation_ids": ["obs_process"],
                "supporting_party_ids": ["party_target"],
                "supporting_cohort_ids": [],
                "reason_code": None,
                "note": None,
            }
        ],
    )
    run_compose_prompts(slug, project_root=tmp_path)
    run_derive(slug, project_root=tmp_path)
    run_db_load_v2(slug, project_root=tmp_path)
    run_db_export_v2(slug, project_root=tmp_path)
    return skill_root


def test_skill_cli_supports_deal_agent_subcommand() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(["deal-agent", "--deal", "imprivata"])
    assert args.command == "deal-agent"
    assert args.deal == "imprivata"


def test_run_deal_agent_creates_live_v2_directories_and_reports_missing_stage_outputs(
    tmp_path: Path,
) -> None:
    _write_shared_inputs(tmp_path)

    summary = run_deal_agent("imprivata", project_root=tmp_path)

    skill_root = tmp_path / "data" / "skill" / "imprivata"
    assert skill_root.exists()
    assert (skill_root / "extract_v2").is_dir()
    assert (skill_root / "check_v2").is_dir()
    assert (skill_root / "coverage_v2").is_dir()
    assert (skill_root / "gates_v2").is_dir()
    assert (skill_root / "derive").is_dir()
    assert (skill_root / "export_v2").is_dir()
    assert (skill_root / "prompt_v2").is_dir()

    assert summary.seed.deal_slug == "imprivata"
    assert summary.seed.target_name == "IMPRIVATA INC"
    assert summary.paths.skill_root == skill_root
    assert summary.extract.status == "missing"
    assert summary.coverage.status == "missing"
    assert summary.derive.status == "missing"
    assert summary.db_load.status == "missing"
    assert summary.db_export.status == "missing"
    assert summary.export.status == "missing"


def test_run_deal_agent_raises_when_prerequisites_are_missing(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "seeds.csv").write_text(
        (
            "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
            "imprivata,IMPRIVATA INC,THOMA BRAVO LLC,2016-07-13,https://example.com,false\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError, match="Missing required skill inputs"):
        run_deal_agent("imprivata", project_root=tmp_path)


def test_run_deal_agent_summarizes_existing_skill_artifacts(tmp_path: Path) -> None:
    _write_shared_inputs(tmp_path)
    skill_root = _write_skill_outputs(tmp_path)

    summary = run_deal_agent("imprivata", project_root=tmp_path)

    assert summary.paths.skill_root == skill_root
    assert summary.extract.status == "pass"
    assert summary.coverage.status == "pass"
    assert summary.gates.status == "pass"
    assert summary.derive.status == "pass"
    assert summary.db_load.status == "pass"
    assert summary.db_export.status == "pass"
    assert summary.export.status == "pass"
    assert summary.db_export.output_path == skill_root / "export_v2" / "analyst_rows.csv"


def test_build_skill_paths_is_v2_only(tmp_path: Path) -> None:
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    skill_root = tmp_path / "data" / "skill" / "imprivata"

    assert paths.extract_v2_dir == skill_root / "extract_v2"
    assert paths.observations_raw_path == skill_root / "extract_v2" / "observations_raw.json"
    assert paths.observations_path == skill_root / "extract_v2" / "observations.json"
    assert paths.spans_v2_path == skill_root / "extract_v2" / "spans.json"
    assert paths.check_v2_dir == skill_root / "check_v2"
    assert paths.coverage_v2_dir == skill_root / "coverage_v2"
    assert paths.gates_v2_dir == skill_root / "gates_v2"
    assert paths.derive_dir == skill_root / "derive"
    assert paths.export_v2_dir == skill_root / "export_v2"
    assert paths.prompt_v2_dir == skill_root / "prompt_v2"
    assert paths.prompt_v2_packets_dir == skill_root / "prompt_v2" / "packets"
    assert paths.prompt_v2_manifest_path == skill_root / "prompt_v2" / "manifest.json"
    assert not hasattr(paths, "prompt_manifest_path")


def test_ensure_output_directories_creates_v2_dirs(tmp_path: Path) -> None:
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    ensure_output_directories(paths)

    assert paths.extract_v2_dir.is_dir()
    assert paths.check_v2_dir.is_dir()
    assert paths.coverage_v2_dir.is_dir()
    assert paths.gates_v2_dir.is_dir()
    assert paths.derive_dir.is_dir()
    assert paths.export_v2_dir.is_dir()
    assert paths.prompt_v2_dir.is_dir()
    assert paths.prompt_v2_packets_dir.is_dir()


def test_v2_cli_subcommands_parse() -> None:
    parser = cli.build_parser()
    for command in (
        "canonicalize-v2",
        "check-v2",
        "coverage-v2",
        "gates-v2",
        "derive",
        "db-load-v2",
        "db-export-v2",
    ):
        args = parser.parse_args([command, "--deal", "stec"])
        assert args.command == command
        assert args.deal == "stec"


def test_compose_prompts_cli_subcommand_parses() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(["compose-prompts", "--deal", "stec"])
    assert args.command == "compose-prompts"
    assert args.deal == "stec"
    assert args.mode == "observations"
    assert args.chunk_budget == 6000


def test_compose_prompts_fails_when_chronology_blocks_missing(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    source_dir = data_dir / "deals" / "imprivata" / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "evidence_items.jsonl").write_text("", encoding="utf-8")

    with pytest.raises(FileNotFoundError, match="chronology_blocks"):
        run_compose_prompts("imprivata", project_root=tmp_path)


def test_compose_prompts_fails_when_evidence_items_missing(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    source_dir = data_dir / "deals" / "imprivata" / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "chronology_blocks.jsonl").write_text(
        json.dumps({
            "block_id": "B001",
            "document_id": "DOC001",
            "ordinal": 1,
            "start_line": 1,
            "end_line": 1,
            "raw_text": "x",
            "clean_text": "x",
            "is_heading": False,
            "page_break_before": False,
            "page_break_after": False,
            "date_mentions": [],
            "entity_mentions": [],
            "evidence_density": 0,
            "temporal_phase": "other",
        }) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError, match="evidence_items"):
        run_compose_prompts("imprivata", project_root=tmp_path)


def test_compose_prompts_writes_valid_manifest(tmp_path: Path) -> None:
    _write_shared_inputs(tmp_path)
    manifest = run_compose_prompts("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)

    assert manifest.deal_slug == "imprivata"
    assert manifest.artifact_type == "prompt_packet_manifest"
    assert paths.prompt_v2_manifest_path.exists()

    from skill_pipeline.pipeline_models.prompt import PromptPacketManifest

    loaded = PromptPacketManifest.model_validate_json(
        paths.prompt_v2_manifest_path.read_text(encoding="utf-8")
    )
    assert loaded.deal_slug == "imprivata"
    assert loaded.run_id == manifest.run_id


def test_compose_prompts_creates_prompt_directories(tmp_path: Path) -> None:
    _write_shared_inputs(tmp_path)
    run_compose_prompts("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    assert paths.prompt_v2_dir.is_dir()
    assert paths.prompt_v2_packets_dir.is_dir()


def test_deal_agent_prompt_stage_missing_when_no_manifest(tmp_path: Path) -> None:
    _write_shared_inputs(tmp_path)
    summary = run_deal_agent("imprivata", project_root=tmp_path)
    assert summary.prompt.status == "missing"
    assert summary.prompt.packet_count == 0


def test_deal_agent_prompt_stage_pass_after_compose(tmp_path: Path) -> None:
    _write_shared_inputs(tmp_path)
    run_compose_prompts("imprivata", project_root=tmp_path)
    summary = run_deal_agent("imprivata", project_root=tmp_path)
    assert summary.prompt.status == "pass"
    assert summary.prompt.packet_count > 0
    assert summary.prompt.observation_packet_count > 0


def test_validate_prompt_packets_passes_on_valid_manifest(tmp_path: Path) -> None:
    from scripts.validate_prompt_packets import validate_manifest

    _write_shared_inputs(tmp_path)
    run_compose_prompts("imprivata", project_root=tmp_path)
    errors = validate_manifest("imprivata", project_root=tmp_path, expect_sections=True)
    assert errors == []


def test_validate_prompt_packets_fails_when_manifest_missing(tmp_path: Path) -> None:
    from scripts.validate_prompt_packets import validate_manifest

    errors = validate_manifest("imprivata", project_root=tmp_path)
    assert len(errors) == 1
    assert "Manifest not found" in errors[0]


def test_validate_prompt_packets_detects_missing_rendered_file(tmp_path: Path) -> None:
    from scripts.validate_prompt_packets import validate_manifest

    _write_shared_inputs(tmp_path)
    manifest = run_compose_prompts("imprivata", project_root=tmp_path)
    first_rendered = Path(manifest.packets[0].rendered_path)
    first_rendered.unlink()
    errors = validate_manifest("imprivata", project_root=tmp_path, expect_sections=True)
    assert any("rendered file missing" in error for error in errors)


def test_validate_prompt_packets_cli_help_mentions_expect_sections() -> None:
    from scripts.validate_prompt_packets import parse_args

    import contextlib
    import io

    buf = io.StringIO()
    with pytest.raises(SystemExit):
        with contextlib.redirect_stdout(buf):
            parse_args(["--help"])
    assert "--expect-sections" in buf.getvalue()
