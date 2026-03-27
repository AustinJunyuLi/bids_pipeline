"""Regression tests for the runtime-contract boundary.

Ensures that:
- pyproject.toml and requirements.txt declare only deterministic runtime deps
- edgartools is capped below 6.0 in both manifests
- neither manifest declares anthropic or openai
- historical plan docs carry disclaimers marking them non-authoritative
- compose-prompts appears in runtime docs before /extract-deal
- prompt packet validator can run on a temporary fixture manifest
"""
from __future__ import annotations

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PYPROJECT = PROJECT_ROOT / "pyproject.toml"
REQUIREMENTS = PROJECT_ROOT / "requirements.txt"

HISTORICAL_PLAN_DOCS = [
    PROJECT_ROOT / "docs/plans/2026-03-16-pipeline-design-v3.md",
    PROJECT_ROOT / "docs/plans/2026-03-16-prompt-engineering-spec.md",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Manifest: no provider SDK dependencies
# ---------------------------------------------------------------------------

def test_pyproject_does_not_declare_anthropic() -> None:
    text = _read(PYPROJECT)
    assert "anthropic" not in text.lower(), (
        "pyproject.toml must not declare anthropic as a dependency"
    )


def test_pyproject_does_not_declare_openai() -> None:
    text = _read(PYPROJECT)
    assert "openai" not in text.lower(), (
        "pyproject.toml must not declare openai as a dependency"
    )


def test_requirements_does_not_declare_anthropic() -> None:
    text = _read(REQUIREMENTS)
    assert "anthropic" not in text.lower(), (
        "requirements.txt must not declare anthropic as a dependency"
    )


def test_requirements_does_not_declare_openai() -> None:
    text = _read(REQUIREMENTS)
    assert "openai" not in text.lower(), (
        "requirements.txt must not declare openai as a dependency"
    )


# ---------------------------------------------------------------------------
# Manifest: edgartools capped below 6.0
# ---------------------------------------------------------------------------

def test_pyproject_caps_edgartools_below_6() -> None:
    text = _read(PYPROJECT)
    assert re.search(r"edgartools.*<\s*6", text), (
        "pyproject.toml must cap edgartools below 6.0"
    )


def test_requirements_caps_edgartools_below_6() -> None:
    text = _read(REQUIREMENTS)
    assert re.search(r"edgartools.*<\s*6", text), (
        "requirements.txt must cap edgartools below 6.0"
    )


# ---------------------------------------------------------------------------
# Historical plan docs carry disclaimers
# ---------------------------------------------------------------------------

def test_historical_plan_docs_carry_historical_disclaimer() -> None:
    violations: list[str] = []
    for path in HISTORICAL_PLAN_DOCS:
        text = _read(path)
        lowered = text.lower()
        if "historical" not in lowered:
            violations.append(f"{path.name}: missing 'historical' disclaimer")
    assert not violations, (
        "Historical plan docs missing disclaimers:\n" + "\n".join(violations)
    )


def test_historical_plan_docs_reference_skill_pipeline() -> None:
    violations: list[str] = []
    for path in HISTORICAL_PLAN_DOCS:
        text = _read(path)
        if "skill_pipeline" not in text and ".claude/skills/" not in text:
            violations.append(
                f"{path.name}: must reference skill_pipeline or .claude/skills/"
            )
    assert not violations, (
        "Historical plan docs do not reference the live implementation:\n"
        + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# Runtime docs include compose-prompts stage
# ---------------------------------------------------------------------------

CLAUDE_MD = PROJECT_ROOT / "CLAUDE.md"
DESIGN_MD = PROJECT_ROOT / "docs" / "design.md"


def test_claude_md_includes_compose_prompts_stage() -> None:
    text = _read(CLAUDE_MD)
    assert "compose-prompts" in text, (
        "CLAUDE.md must document the compose-prompts stage in the runtime sequence"
    )


def test_design_md_includes_compose_prompts_stage() -> None:
    text = _read(DESIGN_MD)
    assert "compose-prompts" in text, (
        "docs/design.md must include compose-prompts in the operational sequence"
    )


def test_claude_md_compose_prompts_before_extract_deal() -> None:
    """compose-prompts must appear before /extract-deal in CLAUDE.md flow."""
    text = _read(CLAUDE_MD)
    compose_pos = text.find("compose-prompts")
    extract_pos = text.find("/extract-deal")
    assert compose_pos != -1 and extract_pos != -1, (
        "Both compose-prompts and /extract-deal must appear in CLAUDE.md"
    )
    assert compose_pos < extract_pos, (
        "compose-prompts must appear before /extract-deal in CLAUDE.md"
    )


# ---------------------------------------------------------------------------
# Prompt packet validator on fixture manifest
# ---------------------------------------------------------------------------


def _build_fixture_manifest(tmp_path: Path) -> Path:
    """Build a minimal valid prompt packet manifest with rendered files."""
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
    """The prompt packet validator runs successfully on a temp fixture manifest."""
    from scripts.validate_prompt_packets import validate_manifest

    _build_fixture_manifest(tmp_path)
    errors = validate_manifest("fixture", project_root=tmp_path, expect_sections=True)
    assert errors == [], f"Fixture validation failed: {errors}"


def test_validator_detects_missing_tag_on_fixture(tmp_path: Path) -> None:
    """The validator catches a missing tag in a fixture rendered packet."""
    from scripts.validate_prompt_packets import validate_manifest

    _build_fixture_manifest(tmp_path)
    # Remove <task_instructions> tag from rendered file
    rendered_path = tmp_path / "data" / "skill" / "fixture" / "prompt" / "packets" / "actors-w0" / "rendered.md"
    text = rendered_path.read_text(encoding="utf-8")
    rendered_path.write_text(text.replace("<task_instructions>", ""), encoding="utf-8")

    errors = validate_manifest("fixture", project_root=tmp_path, expect_sections=True)
    assert any("<task_instructions>" in e for e in errors)
