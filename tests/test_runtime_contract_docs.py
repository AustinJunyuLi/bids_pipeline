"""Regression tests for the runtime-contract boundary.

Ensures that:
- pyproject.toml and requirements.txt declare only deterministic runtime deps
- edgartools is capped below 6.0 in both manifests
- neither manifest declares anthropic or openai
- historical plan docs carry disclaimers marking them non-authoritative
- live docs describe the v2 default flow and legacy archive split
- prompt packet validator can run on a temporary fixture manifest
"""

from __future__ import annotations

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PYPROJECT = PROJECT_ROOT / "pyproject.toml"
REQUIREMENTS = PROJECT_ROOT / "requirements.txt"
GITIGNORE = PROJECT_ROOT / ".gitignore"
ENV_LOCAL_EXAMPLE = PROJECT_ROOT / ".env.local.example"

HISTORICAL_PLAN_DOCS = [
    PROJECT_ROOT / "docs/plans/2026-03-16-pipeline-design-v3.md",
    PROJECT_ROOT / "docs/plans/2026-03-16-prompt-engineering-spec.md",
]

CLAUDE_MD = PROJECT_ROOT / "CLAUDE.md"
DESIGN_MD = PROJECT_ROOT / "docs" / "design.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_pyproject_does_not_declare_anthropic() -> None:
    text = _read(PYPROJECT)
    assert "anthropic" not in text.lower()


def test_pyproject_does_not_declare_openai() -> None:
    text = _read(PYPROJECT)
    assert "openai" not in text.lower()


def test_requirements_does_not_declare_anthropic() -> None:
    text = _read(REQUIREMENTS)
    assert "anthropic" not in text.lower()


def test_requirements_does_not_declare_openai() -> None:
    text = _read(REQUIREMENTS)
    assert "openai" not in text.lower()


def test_pyproject_caps_edgartools_below_6() -> None:
    text = _read(PYPROJECT)
    assert re.search(r"edgartools.*<\s*6", text)


def test_requirements_caps_edgartools_below_6() -> None:
    text = _read(REQUIREMENTS)
    assert re.search(r"edgartools.*<\s*6", text)


def test_pyproject_declares_duckdb() -> None:
    text = _read(PYPROJECT)
    assert "duckdb" in text.lower()


def test_requirements_declares_duckdb() -> None:
    text = _read(REQUIREMENTS)
    assert "duckdb" in text.lower()


def test_historical_plan_docs_carry_historical_disclaimer() -> None:
    violations: list[str] = []
    for path in HISTORICAL_PLAN_DOCS:
        text = _read(path)
        lowered = text.lower()
        if "historical" not in lowered:
            violations.append(f"{path.name}: missing 'historical' disclaimer")
    assert not violations, "Historical plan docs missing disclaimers:\n" + "\n".join(violations)


def test_historical_plan_docs_reference_skill_pipeline() -> None:
    violations: list[str] = []
    for path in HISTORICAL_PLAN_DOCS:
        text = _read(path)
        if "skill_pipeline" not in text and ".claude/skills/" not in text:
            violations.append(f"{path.name}: must reference skill_pipeline or .claude/skills/")
    assert not violations, "Historical plan docs do not reference the live implementation:\n" + "\n".join(
        violations
    )


def test_claude_md_includes_compose_prompts_stage() -> None:
    text = _read(CLAUDE_MD)
    assert "compose-prompts" in text


def test_design_md_includes_compose_prompts_stage() -> None:
    text = _read(DESIGN_MD)
    assert "compose-prompts" in text


def test_claude_md_compose_prompts_before_extract_deal_v2() -> None:
    text = _read(CLAUDE_MD)
    compose_pos = text.find("compose-prompts")
    extract_pos = text.find("/extract-deal-v2")
    assert compose_pos != -1 and extract_pos != -1
    assert compose_pos < extract_pos


def test_design_md_live_sequence_is_v2_default() -> None:
    text = _read(DESIGN_MD)
    sequence_start = text.find("Operational sequence:")
    artifact_start = text.find("Artifact flow:", sequence_start)
    assert sequence_start != -1 and artifact_start != -1
    sequence_text = text[sequence_start:artifact_start]
    compose_pos = sequence_text.find("compose-prompts --deal <slug> --contract v2 --mode observations")
    extract_pos = sequence_text.find("/extract-deal-v2 <slug>")
    derive_pos = sequence_text.find("skill-pipeline derive --deal <slug>")
    db_load_pos = sequence_text.find("skill-pipeline db-load-v2 --deal <slug>")
    db_export_pos = sequence_text.find("skill-pipeline db-export-v2 --deal <slug>")
    assert -1 not in (compose_pos, extract_pos, derive_pos, db_load_pos, db_export_pos)
    assert compose_pos < extract_pos < derive_pos < db_load_pos < db_export_pos


def test_design_md_mentions_legacy_archive_split() -> None:
    text = _read(DESIGN_MD)
    assert "data/legacy/v1/" in text
    assert "legacy" in text.lower()


def test_claude_md_documents_live_db_load_v2_and_db_export_v2_contract() -> None:
    text = _read(CLAUDE_MD)
    normalized = " ".join(text.split())
    assert "db-load-v2" in text
    assert "db-export-v2" in text
    assert "skill-pipeline db-load-v2 --deal <slug>" in text
    assert "skill-pipeline db-export-v2 --deal <slug>" in text
    assert "data/legacy/v1/" in text
    assert "`db-load-v2` requires canonical v2 observations" in normalized


def test_claude_md_documents_live_and_legacy_skill_split() -> None:
    text = _read(CLAUDE_MD)
    assert "/deal-agent" in text
    assert "/deal-agent-legacy" in text
    assert "/reconcile-alex" in text
    assert "/reconcile-alex-legacy" in text


def test_claude_md_documents_split_cross_os_env_setup() -> None:
    text = _read(CLAUDE_MD)
    normalized = " ".join(text.split())
    assert ".claude/LOCAL.md" in text
    assert "read it immediately after this file before taking action" in normalized
    assert ".env.local" in text
    assert "PIPELINE_SEC_IDENTITY" in text
    assert ".venv-win" not in text and ".venv-wsl" not in text


def test_claude_md_end_to_end_flow_is_v2_default() -> None:
    text = _read(CLAUDE_MD)
    flow_start = text.find("## End-To-End Flow")
    flow_end = text.find("## Hard Invariants", flow_start)
    assert flow_start != -1 and flow_end != -1
    flow_text = text[flow_start:flow_end]
    extract_pos = flow_text.find("/extract-deal-v2")
    derive_pos = flow_text.find("skill-pipeline derive --deal <slug>")
    db_load_pos = flow_text.find("skill-pipeline db-load-v2 --deal <slug>")
    db_export_pos = flow_text.find("skill-pipeline db-export-v2 --deal <slug>")
    assert -1 not in (extract_pos, derive_pos, db_load_pos, db_export_pos)
    assert extract_pos < derive_pos < db_load_pos < db_export_pos
    assert "/export-csv" not in flow_text


def test_gitignore_supports_split_cross_os_envs_and_template() -> None:
    text = _read(GITIGNORE)
    assert ".venv-*/" in text
    assert "!.env.local.example" in text
    assert ".claude/LOCAL.md" in text


def test_env_local_example_guides_runtime_identity_to_shell_profile() -> None:
    text = _read(ENV_LOCAL_EXAMPLE)
    assert "PIPELINE_SEC_IDENTITY" in text
    assert "NEWAPI_API_KEY=" in text


def _build_fixture_manifest(tmp_path: Path) -> Path:
    prompt_dir = tmp_path / "data" / "skill" / "fixture" / "prompt"
    packets_dir = prompt_dir / "packets" / "actors-w0"
    packets_dir.mkdir(parents=True, exist_ok=True)

    rendered_text = (
        "# Prompt\n\n"
        "<chronology_blocks>\nBlock text\n</chronology_blocks>\n\n"
        "<evidence_checklist>\n- item\n</evidence_checklist>\n\n"
        "<task_instructions>\nExtract actors.\n</task_instructions>\n"
    )
    rendered_path = packets_dir / "rendered.md"
    rendered_path.write_text(rendered_text, encoding="utf-8")
    (packets_dir / "prefix.md").write_text("prefix\n", encoding="utf-8")
    (packets_dir / "body.md").write_text("body\n", encoding="utf-8")

    manifest = {
        "schema_version": "2.0.0",
        "artifact_type": "prompt_packet_manifest",
        "created_at": "2026-03-27T00:00:00Z",
        "pipeline_version": "0.1.0",
        "run_id": "test-fixture",
        "deal_slug": "fixture",
        "source_accession_number": None,
        "packets": [
            {
                "packet_id": "actors-w0",
                "packet_family": "actors",
                "chunk_mode": "single_pass",
                "window_id": "w0",
                "prefix_path": str(packets_dir / "prefix.md"),
                "body_path": str(packets_dir / "body.md"),
                "rendered_path": str(rendered_path),
                "evidence_ids": [],
                "actor_roster_source_path": None,
            }
        ],
        "asset_files": [],
        "notes": [],
    }
    manifest_path = prompt_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return tmp_path


def test_validator_passes_on_fixture_manifest(tmp_path: Path) -> None:
    from scripts.validate_prompt_packets import validate_manifest

    _build_fixture_manifest(tmp_path)
    errors = validate_manifest("fixture", project_root=tmp_path, expect_sections=True)
    assert errors == [], f"Fixture validation failed: {errors}"


def test_validator_detects_missing_tag_on_fixture(tmp_path: Path) -> None:
    from scripts.validate_prompt_packets import validate_manifest

    _build_fixture_manifest(tmp_path)
    rendered_path = (
        tmp_path / "data" / "skill" / "fixture" / "prompt" / "packets" / "actors-w0" / "rendered.md"
    )
    text = rendered_path.read_text(encoding="utf-8")
    rendered_path.write_text(text.replace("<task_instructions>", ""), encoding="utf-8")

    errors = validate_manifest("fixture", project_root=tmp_path, expect_sections=True)
    assert any("<task_instructions>" in error for error in errors)
