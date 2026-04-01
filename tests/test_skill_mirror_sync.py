from __future__ import annotations

from pathlib import Path

from scripts.sync_skill_mirrors import check_target, sync_target

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _write_skill(source_dir: Path, skill_name: str, description: str, body: str) -> None:
    skill_dir = source_dir / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        (
            "---\n"
            f"name: {skill_name}\n"
            f"description: {description}\n"
            "---\n\n"
            f"# {skill_name}\n\n"
            f"{body}\n"
        ),
        encoding="utf-8",
    )


def test_sync_target_copies_skills_and_generates_codex_readme(tmp_path: Path) -> None:
    source_dir = tmp_path / ".claude" / "skills"
    codex_dir = tmp_path / ".codex" / "skills"

    _write_skill(source_dir, "alpha", "Alpha description.", "Alpha body.")
    _write_skill(source_dir, "beta", "Beta description.", "Beta body.")

    sync_target(source_dir, codex_dir)

    assert (codex_dir / "alpha" / "SKILL.md").read_text(encoding="utf-8").endswith("Alpha body.\n")
    assert (codex_dir / "beta" / "SKILL.md").read_text(encoding="utf-8").endswith("Beta body.\n")

    readme = (codex_dir / "README.md").read_text(encoding="utf-8")
    assert "Derived mirror of `.claude/skills/` for Codex." in readme
    assert "| `alpha` | Alpha description. |" in readme
    assert "| `beta` | Beta description. |" in readme

    assert check_target(source_dir, codex_dir) == []


def test_check_target_reports_missing_and_drifted_files(tmp_path: Path) -> None:
    source_dir = tmp_path / ".claude" / "skills"
    cursor_dir = tmp_path / ".cursor" / "skills"

    _write_skill(source_dir, "alpha", "Alpha description.", "Alpha body.")
    sync_target(source_dir, cursor_dir)

    (cursor_dir / "alpha" / "SKILL.md").write_text("drifted\n", encoding="utf-8")
    (cursor_dir / "extra.txt").write_text("unexpected\n", encoding="utf-8")

    issues = check_target(source_dir, cursor_dir)

    assert any("content drift in alpha/SKILL.md" in issue for issue in issues)
    assert any("unexpected file extra.txt" in issue for issue in issues)


def _assert_mirror_matches(skill_name: str) -> None:
    canonical = PROJECT_ROOT / ".claude" / "skills" / skill_name / "SKILL.md"
    codex = PROJECT_ROOT / ".codex" / "skills" / skill_name / "SKILL.md"
    cursor = PROJECT_ROOT / ".cursor" / "skills" / skill_name / "SKILL.md"
    assert codex.exists(), f".codex {skill_name} mirror must exist"
    assert cursor.exists(), f".cursor {skill_name} mirror must exist"
    assert canonical.read_bytes() == codex.read_bytes(), f".codex {skill_name} mirror drifted"
    assert canonical.read_bytes() == cursor.read_bytes(), f".cursor {skill_name} mirror drifted"


def test_live_extract_skill_references_prompt_v2_manifest() -> None:
    skill_path = PROJECT_ROOT / ".claude" / "skills" / "extract-deal-v2" / "SKILL.md"
    text = skill_path.read_text(encoding="utf-8")
    assert "data/skill/<slug>/prompt_v2/manifest.json" in text
    assert "compose-prompts --deal <slug> --mode observations" in text


def test_live_reconcile_skill_documents_v2_exports() -> None:
    skill_path = PROJECT_ROOT / ".claude" / "skills" / "reconcile-alex" / "SKILL.md"
    text = skill_path.read_text(encoding="utf-8")
    assert "export_v2/benchmark_rows_expanded.csv" in text
    assert "skill-pipeline db-export-v2 --deal <slug>" in text


def test_live_deal_agent_skill_documents_clean_rerun() -> None:
    skill_path = PROJECT_ROOT / ".claude" / "skills" / "deal-agent" / "SKILL.md"
    text = skill_path.read_text(encoding="utf-8")
    assert "clean v2 rerun" in text.lower()
    assert "db-export-v2" in text
    assert "overwrite" in text.lower()
    assert "v1-working-tree-2026-04-01" in text


def test_only_live_skill_tree_remains() -> None:
    skill_names = sorted(path.name for path in (PROJECT_ROOT / ".claude" / "skills").iterdir() if path.is_dir())
    assert skill_names == [
        "deal-agent",
        "extract-deal-v2",
        "reconcile-alex",
        "verify-extraction-v2",
    ]


def test_live_skill_mirrors_match_canonical() -> None:
    for skill_name in (
        "deal-agent",
        "extract-deal-v2",
        "reconcile-alex",
        "verify-extraction-v2",
    ):
        _assert_mirror_matches(skill_name)
