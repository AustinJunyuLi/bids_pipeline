from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


ACTIVE_DOCS = [
    PROJECT_ROOT / "CLAUDE.md",
    PROJECT_ROOT / "docs/HOME_COMPUTER_SETUP.md",
]

WARNING_DOCS = [
    PROJECT_ROOT / "example/README.md",
    PROJECT_ROOT / "diagnosis/README.md",
]

LEGACY_DOCS = [
    PROJECT_ROOT / "docs/skills/README.md",
    PROJECT_ROOT / "docs/skills/deal-agent.md",
    PROJECT_ROOT / "docs/skills/extract-deal.md",
    PROJECT_ROOT / "docs/skills/verify-extraction.md",
    PROJECT_ROOT / "docs/skills/enrich-deal.md",
    PROJECT_ROOT / "docs/skills/export-csv.md",
    PROJECT_ROOT / "docs/skills/reconcile-alex.md",
    PROJECT_ROOT / ".agents/skills/deal-agent/SKILL.md",
    PROJECT_ROOT / ".agents/skills/extract-deal/SKILL.md",
    PROJECT_ROOT / ".agents/skills/verify-extraction/SKILL.md",
    PROJECT_ROOT / ".agents/skills/enrich-deal/SKILL.md",
    PROJECT_ROOT / ".agents/skills/export-csv/SKILL.md",
    PROJECT_ROOT / ".agents/skills/reconcile-alex/SKILL.md",
    PROJECT_ROOT / ".claude/skills/deal-agent/SKILL.md",
    PROJECT_ROOT / ".claude/skills/extract-deal/SKILL.md",
    PROJECT_ROOT / ".claude/skills/verify-extraction/SKILL.md",
    PROJECT_ROOT / ".claude/skills/enrich-deal/SKILL.md",
    PROJECT_ROOT / ".claude/skills/export-csv/SKILL.md",
    PROJECT_ROOT / ".claude/skills/reconcile-alex/SKILL.md",
    PROJECT_ROOT / ".codex/skills/README.md",
    PROJECT_ROOT / ".codex/skills/deal-agent/SKILL.md",
    PROJECT_ROOT / ".codex/skills/extract-deal/SKILL.md",
    PROJECT_ROOT / ".codex/skills/verify-extraction/SKILL.md",
    PROJECT_ROOT / ".codex/skills/enrich-deal/SKILL.md",
    PROJECT_ROOT / ".codex/skills/export-csv/SKILL.md",
    PROJECT_ROOT / ".codex/skills/reconcile-alex/SKILL.md",
    PROJECT_ROOT / ".cursor/skills/deal-agent/SKILL.md",
    PROJECT_ROOT / ".cursor/skills/extract-deal/SKILL.md",
    PROJECT_ROOT / ".cursor/skills/verify-extraction/SKILL.md",
    PROJECT_ROOT / ".cursor/skills/enrich-deal/SKILL.md",
    PROJECT_ROOT / ".cursor/skills/export-csv/SKILL.md",
    PROJECT_ROOT / ".cursor/skills/reconcile-alex/SKILL.md",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_active_docs_do_not_reference_benchmark_files() -> None:
    forbidden_terms = [
        "example/deal_details_Alex_2026.xlsx",
        "CollectionInstructions_Alex_2026.qmd",
        "bidding_instructions_flowcharts.qmd",
    ]

    violations: list[str] = []
    for path in ACTIVE_DOCS:
        text = _read(path)
        for term in forbidden_terms:
            if term in text:
                violations.append(f"{path}: {term}")

    assert not violations, "Active docs reference benchmark materials:\n" + "\n".join(
        violations
    )


def test_active_docs_state_benchmark_boundary_explicitly() -> None:
    violations: list[str] = []
    for path in ACTIVE_DOCS:
        raw_text = _read(path)
        text = raw_text.lower()
        if "benchmark" not in text:
            violations.append(f"{path}: missing benchmark-separation language")
        if "before `/export-csv`" not in text and "before /export-csv" not in text:
            violations.append(f"{path}: missing pre-export boundary")

    assert not violations, (
        "Active docs do not state the benchmark boundary clearly:\n"
        + "\n".join(violations)
    )


def test_active_docs_treat_export_as_repo_review_contract() -> None:
    violations: list[str] = []
    for path in ACTIVE_DOCS:
        text = _read(path)
        if "Alex-compatible" in text:
            violations.append(f"{path}: contains 'Alex-compatible'")
        if "Match Alex Gorbenko's spreadsheet conventions exactly." in text:
            violations.append(f"{path}: contains direct Alex spreadsheet matching rule")

    assert not violations, (
        "Active docs still frame export as benchmark matching:\n"
        + "\n".join(violations)
    )


def test_active_docs_do_not_frame_generation_as_benchmark_matching() -> None:
    violations: list[str] = []
    for path in ACTIVE_DOCS:
        text = _read(path)
        lowered = text.lower()
        if "alex-compatible" in lowered:
            violations.append(f"{path}: contains 'Alex-compatible'")
        if "anthropic_api_key" in lowered or "openai_api_key" in lowered:
            violations.append(f"{path}: contains obsolete llm api key setup")

    assert not violations, (
        "Active docs still leak benchmark-oriented or obsolete guidance:\n"
        + "\n".join(violations)
    )


def test_benchmark_warning_docs_exist_and_warn_cleanly() -> None:
    violations: list[str] = []
    for path in WARNING_DOCS:
        if not path.exists():
            violations.append(f"{path}: missing warning doc")
            continue
        text = _read(path).lower()
        if "benchmark" not in text:
            violations.append(f"{path}: missing benchmark warning")
        if "post-export" not in text:
            violations.append(f"{path}: missing post-export boundary")
        if "do not consult" not in text:
            violations.append(f"{path}: missing explicit do-not-consult language")

    assert not violations, (
        "Benchmark warning docs are missing or incomplete:\n" + "\n".join(violations)
    )


def test_legacy_instruction_surfaces_are_removed() -> None:
    violations: list[str] = []
    for path in LEGACY_DOCS:
        if path.exists():
            violations.append(f"{path}: still exists")

    assert not violations, "Legacy instruction surfaces still exist:\n" + "\n".join(
        violations
    )
