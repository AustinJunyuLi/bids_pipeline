from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


LIVE_GENERATION_DOCS = [
    PROJECT_ROOT / "CLAUDE.md",
    PROJECT_ROOT / ".claude/skills/deal-agent/SKILL.md",
    PROJECT_ROOT / ".codex/skills/deal-agent/SKILL.md",
    PROJECT_ROOT / ".cursor/skills/deal-agent/SKILL.md",
    PROJECT_ROOT / ".claude/skills/extract-deal-v2/SKILL.md",
    PROJECT_ROOT / ".codex/skills/extract-deal-v2/SKILL.md",
    PROJECT_ROOT / ".cursor/skills/extract-deal-v2/SKILL.md",
    PROJECT_ROOT / ".claude/skills/verify-extraction-v2/SKILL.md",
    PROJECT_ROOT / ".codex/skills/verify-extraction-v2/SKILL.md",
    PROJECT_ROOT / ".cursor/skills/verify-extraction-v2/SKILL.md",
]

LEGACY_GENERATION_DOCS = [
    PROJECT_ROOT / ".claude/skills/deal-agent-legacy/SKILL.md",
    PROJECT_ROOT / ".codex/skills/deal-agent-legacy/SKILL.md",
    PROJECT_ROOT / ".cursor/skills/deal-agent-legacy/SKILL.md",
    PROJECT_ROOT / ".claude/skills/extract-deal/SKILL.md",
    PROJECT_ROOT / ".codex/skills/extract-deal/SKILL.md",
    PROJECT_ROOT / ".cursor/skills/extract-deal/SKILL.md",
    PROJECT_ROOT / ".claude/skills/verify-extraction/SKILL.md",
    PROJECT_ROOT / ".codex/skills/verify-extraction/SKILL.md",
    PROJECT_ROOT / ".cursor/skills/verify-extraction/SKILL.md",
    PROJECT_ROOT / ".claude/skills/enrich-deal/SKILL.md",
    PROJECT_ROOT / ".codex/skills/enrich-deal/SKILL.md",
    PROJECT_ROOT / ".cursor/skills/enrich-deal/SKILL.md",
]

LIVE_RECONCILE_DOCS = [
    PROJECT_ROOT / ".claude/skills/reconcile-alex/SKILL.md",
    PROJECT_ROOT / ".codex/skills/reconcile-alex/SKILL.md",
    PROJECT_ROOT / ".cursor/skills/reconcile-alex/SKILL.md",
]

LEGACY_RECONCILE_DOCS = [
    PROJECT_ROOT / ".claude/skills/reconcile-alex-legacy/SKILL.md",
    PROJECT_ROOT / ".codex/skills/reconcile-alex-legacy/SKILL.md",
    PROJECT_ROOT / ".cursor/skills/reconcile-alex-legacy/SKILL.md",
]

SUPPORT_DOCS = [
    PROJECT_ROOT / ".codex/skills/README.md",
    PROJECT_ROOT / "docs/HOME_COMPUTER_SETUP.md",
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
    for path in LIVE_GENERATION_DOCS + LEGACY_GENERATION_DOCS:
        text = _read(path)
        for term in forbidden_terms:
            if term in text:
                violations.append(f"{path}: {term}")

    assert not violations, "Generation docs reference benchmark materials:\n" + "\n".join(
        violations
    )


def test_live_generation_docs_state_benchmark_boundary_explicitly() -> None:
    violations: list[str] = []
    for path in LIVE_GENERATION_DOCS:
        normalized = " ".join(_read(path).split()).lower()
        if "benchmark" not in normalized:
            violations.append(f"{path}: missing benchmark-separation language")
        if (
            "before `skill-pipeline db-export-v2 --deal <slug>` completes" not in normalized
            and "before skill-pipeline db-export-v2 --deal <slug> completes" not in normalized
        ):
            violations.append(f"{path}: missing pre-db-export-v2 boundary")

    assert not violations, "Live generation docs do not state the v2 benchmark boundary clearly:\n" + "\n".join(
        violations
    )


def test_legacy_generation_docs_state_benchmark_boundary_explicitly() -> None:
    violations: list[str] = []
    for path in LEGACY_GENERATION_DOCS:
        normalized = " ".join(_read(path).split()).lower()
        if "benchmark" not in normalized:
            violations.append(f"{path}: missing benchmark-separation language")
        if (
            "before `skill-pipeline db-export --deal <slug>` completes" not in normalized
            and "before skill-pipeline db-export --deal <slug> completes" not in normalized
        ):
            violations.append(f"{path}: missing pre-db-export boundary")

    assert not violations, "Legacy generation docs do not state the benchmark boundary clearly:\n" + "\n".join(
        violations
    )


def test_generation_docs_do_not_frame_export_as_benchmark_matching() -> None:
    violations: list[str] = []
    for path in LIVE_GENERATION_DOCS + LEGACY_GENERATION_DOCS:
        text = _read(path)
        if "Alex-compatible" in text:
            violations.append(f"{path}: contains 'Alex-compatible'")
        if "Match Alex Gorbenko's spreadsheet conventions exactly." in text:
            violations.append(f"{path}: contains direct Alex spreadsheet matching rule")

    assert not violations, "Generation docs still frame export as benchmark matching:\n" + "\n".join(
        violations
    )


def test_live_reconcile_docs_require_post_export_usage() -> None:
    violations: list[str] = []
    for path in LIVE_RECONCILE_DOCS:
        text = _read(path)
        if "skill-pipeline db-export-v2 --deal <slug>" not in text:
            violations.append(f"{path}: missing db-export-v2 prerequisite")
        if "data/skill/<slug>/export_v2/benchmark_rows_expanded.csv" not in text:
            violations.append(f"{path}: missing v2 benchmark export prerequisite")
        if "forbidden during generation" not in text.lower():
            violations.append(f"{path}: missing explicit generation boundary language")

    assert not violations, "Live reconcile docs do not enforce post-export v2 boundary:\n" + "\n".join(
        violations
    )


def test_legacy_reconcile_docs_require_post_export_usage() -> None:
    violations: list[str] = []
    for path in LEGACY_RECONCILE_DOCS:
        text = _read(path)
        if "skill-pipeline db-export --deal <slug>" not in text:
            violations.append(f"{path}: missing db-export prerequisite")
        if "data/skill/<slug>/export/deal_events.csv" not in text:
            violations.append(f"{path}: missing legacy export prerequisite")

    assert not violations, "Legacy reconcile docs do not enforce post-export boundary:\n" + "\n".join(
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
