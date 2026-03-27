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


# --- Prompt stage visibility in extract-deal skill mirrors ---


def test_canonical_extract_skill_references_prompt_manifest() -> None:
    """The canonical .claude extract skill references the prompt manifest path."""
    skill_path = PROJECT_ROOT / ".claude" / "skills" / "extract-deal" / "SKILL.md"
    text = skill_path.read_text(encoding="utf-8")
    assert "data/skill/<slug>/prompt/manifest.json" in text, (
        "extract-deal SKILL.md must reference the prompt manifest path"
    )


def test_codex_mirror_matches_canonical_extract_skill() -> None:
    """The .codex extract skill mirror matches the canonical .claude version."""
    canonical = PROJECT_ROOT / ".claude" / "skills" / "extract-deal" / "SKILL.md"
    mirror = PROJECT_ROOT / ".codex" / "skills" / "extract-deal" / "SKILL.md"
    assert mirror.exists(), ".codex extract-deal mirror must exist"
    assert canonical.read_bytes() == mirror.read_bytes(), (
        ".codex extract-deal SKILL.md has drifted from .claude canonical"
    )


def test_cursor_mirror_matches_canonical_extract_skill() -> None:
    """The .cursor extract skill mirror matches the canonical .claude version."""
    canonical = PROJECT_ROOT / ".claude" / "skills" / "extract-deal" / "SKILL.md"
    mirror = PROJECT_ROOT / ".cursor" / "skills" / "extract-deal" / "SKILL.md"
    assert mirror.exists(), ".cursor extract-deal mirror must exist"
    assert canonical.read_bytes() == mirror.read_bytes(), (
        ".cursor extract-deal SKILL.md has drifted from .claude canonical"
    )
