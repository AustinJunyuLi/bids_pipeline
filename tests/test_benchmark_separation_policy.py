from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


GENERATION_DOCS = [
    PROJECT_ROOT / "CLAUDE.md",
    PROJECT_ROOT / ".claude/skills/deal-agent/SKILL.md",
    PROJECT_ROOT / ".codex/skills/deal-agent/SKILL.md",
    PROJECT_ROOT / ".cursor/skills/deal-agent/SKILL.md",
    PROJECT_ROOT / ".claude/skills/extract-deal/SKILL.md",
    PROJECT_ROOT / ".codex/skills/extract-deal/SKILL.md",
    PROJECT_ROOT / ".cursor/skills/extract-deal/SKILL.md",
    PROJECT_ROOT / ".claude/skills/verify-extraction/SKILL.md",
    PROJECT_ROOT / ".codex/skills/verify-extraction/SKILL.md",
    PROJECT_ROOT / ".cursor/skills/verify-extraction/SKILL.md",
    PROJECT_ROOT / ".claude/skills/enrich-deal/SKILL.md",
    PROJECT_ROOT / ".codex/skills/enrich-deal/SKILL.md",
    PROJECT_ROOT / ".cursor/skills/enrich-deal/SKILL.md",
    PROJECT_ROOT / ".claude/skills/export-csv/SKILL.md",
    PROJECT_ROOT / ".codex/skills/export-csv/SKILL.md",
    PROJECT_ROOT / ".cursor/skills/export-csv/SKILL.md",
]

SUPPORT_DOCS = [
    PROJECT_ROOT / ".codex/skills/README.md",
    PROJECT_ROOT / "docs/HOME_COMPUTER_SETUP.md",
]

RECONCILE_DOCS = [
    PROJECT_ROOT / ".claude/skills/reconcile-alex/SKILL.md",
    PROJECT_ROOT / ".codex/skills/reconcile-alex/SKILL.md",
    PROJECT_ROOT / ".cursor/skills/reconcile-alex/SKILL.md",
]

WARNING_DOCS = [
    PROJECT_ROOT / "example/README.md",
    PROJECT_ROOT / "diagnosis/README.md",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_generation_docs_do_not_reference_benchmark_files() -> None:
    forbidden_terms = [
        "example/deal_details_Alex_2026.xlsx",
        "CollectionInstructions_Alex_2026.qmd",
        "bidding_instructions_flowcharts.qmd",
    ]

    violations: list[str] = []
    for path in GENERATION_DOCS:
        text = _read(path)
        for term in forbidden_terms:
            if term in text:
                violations.append(f"{path}: {term}")

    assert not violations, "Generation docs reference benchmark materials:\n" + "\n".join(
        violations
    )


def test_generation_docs_state_benchmark_boundary_explicitly() -> None:
    violations: list[str] = []
    for path in GENERATION_DOCS:
        text = _read(path).lower()
        if "benchmark" not in text:
            violations.append(f"{path}: missing benchmark-separation language")
        if "before `/export-csv`" not in _read(path) and "before /export-csv" not in text:
            violations.append(f"{path}: missing pre-export boundary")

    assert not violations, "Generation docs do not state the benchmark boundary clearly:\n" + "\n".join(
        violations
    )


def test_generation_docs_forbid_opening_reconcile_skill_pre_export() -> None:
    violations: list[str] = []
    for path in GENERATION_DOCS:
        text = _read(path).lower()
        if "reconcile-alex" not in text:
            violations.append(f"{path}: missing reconcile-alex reference")
            continue
        if "do not open" not in text and "do not read" not in text:
            violations.append(f"{path}: missing do-not-open/do-not-read rule for reconcile-alex")

    assert not violations, (
        "Generation docs do not explicitly forbid opening reconcile-alex pre-export:\n"
        + "\n".join(violations)
    )


def test_generation_docs_treat_export_as_repo_review_contract() -> None:
    violations: list[str] = []
    for path in GENERATION_DOCS:
        text = _read(path)
        if "Alex-compatible" in text:
            violations.append(f"{path}: contains 'Alex-compatible'")
        if "Match Alex Gorbenko's spreadsheet conventions exactly." in text:
            violations.append(f"{path}: contains direct Alex spreadsheet matching rule")

    assert not violations, "Generation docs still frame export as benchmark matching:\n" + "\n".join(
        violations
    )


def test_reconcile_docs_require_post_export_usage() -> None:
    violations: list[str] = []
    for path in RECONCILE_DOCS:
        text = _read(path)
        if "It can also be run after extraction plus enrichment" in text:
            violations.append(f"{path}: permits pre-export fallback")
        if "data/skill/<slug>/export/deal_events.csv" not in text:
            violations.append(f"{path}: missing export prerequisite")
        if "forbidden during generation" not in text.lower():
            violations.append(f"{path}: missing explicit generation boundary language")

    assert not violations, "Reconcile docs do not enforce post-export boundary:\n" + "\n".join(
        violations
    )


def test_support_docs_do_not_frame_generation_as_benchmark_matching() -> None:
    violations: list[str] = []
    for path in SUPPORT_DOCS:
        text = _read(path)
        lowered = text.lower()
        if "alex-compatible" in lowered:
            violations.append(f"{path}: contains 'Alex-compatible'")
        if "example/" in text and "post-export" not in lowered:
            violations.append(f"{path}: references example/ without post-export warning")
        if "diagnosis/" in text and "post-export" not in lowered:
            violations.append(f"{path}: references diagnosis/ without post-export warning")
        if "anthropic_api_key" in lowered or "openai_api_key" in lowered:
            violations.append(f"{path}: contains obsolete llm api key setup")

    assert not violations, "Support docs still leak benchmark-oriented or obsolete guidance:\n" + "\n".join(
        violations
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

    assert not violations, "Benchmark warning docs are missing or incomplete:\n" + "\n".join(
        violations
    )
