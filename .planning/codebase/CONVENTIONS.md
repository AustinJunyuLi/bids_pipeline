# Coding Conventions

**Analysis Date:** 2026-03-25

## Naming Patterns

**Files:**
- `snake_case.py` for tracked Python modules in `skill_pipeline/`
- `test_<scope>.py` for pytest files in `tests/`
- `SKILL.md` for skill instructions under `.claude/skills/` and the derived mirrors

**Functions:**
- `snake_case` for functions and helpers such as `fetch_raw_deal()`, `preprocess_source_deal()`, and `run_enrich_core()`
- Private helpers usually use a leading underscore, for example `_set_identity()` and `_load_document_lines()`

**Variables and constants:**
- `snake_case` for locals and parameters
- `UPPER_SNAKE_CASE` for module constants such as `PRIMARY_FILING_TYPES`, `ROUND_PAIRS`, and `STRICT_QUOTE_MATCH_TYPES`

**Types and models:**
- `PascalCase` for Pydantic models and typed records such as `SkillVerificationLog`, `FrozenDocument`, and `ChronologySelection`

## Code Style

**Formatting:**
- 4-space indentation
- UTF-8 text with `LF` line endings for tracked files
- Type hints on public functions are common and expected
- `from __future__ import annotations` appears at the top of most tracked modules

**Tooling:**
- No tracked formatter or linter configuration exists
- The repo expectation is "match surrounding style" rather than apply an external formatter

## Import Organization

**Order observed in tracked modules:**
1. Future import (`from __future__ import annotations`)
2. Standard library imports
3. Third-party imports such as Pydantic or `edgar`
4. Local `skill_pipeline` imports

**Grouping:**
- Imports are grouped with blank lines between standard library, third-party, and local modules
- Relative imports are rare; package-qualified imports such as `from skill_pipeline...` are preferred

## Error Handling

**Patterns:**
- Fail fast on missing inputs, invalid manifests, ambiguous source URLs, and schema mismatches
- Raise specific built-in exceptions such as `FileNotFoundError`, `ValueError`, `RuntimeError`, and `FileExistsError`
- Avoid silent fallbacks; for example, `skill_pipeline/raw/fetch.py` explicitly removes the old HTTP fallback path

**Boundary behavior:**
- Stages either return JSON-friendly summaries or exit codes
- Some stages invalidate partial outputs on failure, for example `preprocess_source_deal()` and `run_enrich_core()`

## Logging

**Framework:**
- No structured logging framework is tracked
- CLI commands primarily print JSON payloads or rely on written artifact files

**Pattern:**
- Persist machine-readable results under `data/skill/<slug>/` rather than emit verbose logs
- Use explicit report files such as `check_report.json`, `verification_log.json`, and `coverage_summary.json`

## Comments and Docstrings

**When comments appear:**
- Short module docstrings for stage purpose, for example in `skill_pipeline/canonicalize.py` and `skill_pipeline/enrich_core.py`
- Narrow inline comments where stage logic would otherwise be hard to parse

**Style:**
- Comments usually explain intent or invariants rather than restate the line of code
- Long explanatory guidance belongs in `CLAUDE.md` or `docs/`, not inline comments

## Function Design

**Patterns:**
- Stage entrypoints are thin functions with explicit keyword-only parameters, for example `project_root`, `raw_dir`, or injected test doubles
- Helpers are extracted aggressively for path lookup, span resolution, and classification logic
- Early guard clauses are common before main processing begins

**I/O style:**
- `pathlib.Path` is the standard path abstraction
- File writes are often atomic via temp-file replace patterns
- Generated JSON is typically written with explicit indentation

## Module Design

**Stage-oriented modules:**
- One primary concern per file, such as `coverage.py`, `verify.py`, or `raw/stage.py`
- Shared models and path helpers live in central modules instead of being redefined in each stage

**Hybrid repo conventions:**
- `CLAUDE.md` is the authoritative instruction file for repo behavior
- `.claude/skills/` is the canonical skill tree; `.codex/skills/` and `.cursor/skills/` are generated mirrors

---

*Convention analysis: 2026-03-25*
*Update when patterns change*
