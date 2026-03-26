# Coding Conventions

**Analysis Date:** 2026-03-26

## Naming Patterns

**Files:**
- Use `snake_case.py` for Python modules under `skill_pipeline/`, for example `skill_pipeline/canonicalize.py`, `skill_pipeline/enrich_core.py`, and `skill_pipeline/source_validation.py`.
- Use `test_<scope>.py` for pytest files in `tests/`, for example `tests/test_skill_check.py`, `tests/test_skill_verify.py`, and `tests/test_workflow_contract_surface.py`.
- Use uppercase `SKILL.md` for skill instructions under `.claude/skills/`; the mirrors under `.codex/skills/` and `.cursor/skills/` follow the same filename convention and are checked by `tests/test_skill_mirror_sync.py`.

**Functions:**
- Use `snake_case` for public functions and stage entrypoints, for example `run_check()`, `run_verify()`, `preprocess_source_deal()`, `fetch_raw_deal()`, and `load_seed_entry()` in `skill_pipeline/check.py`, `skill_pipeline/verify.py`, `skill_pipeline/preprocess/source.py`, `skill_pipeline/raw/stage.py`, and `skill_pipeline/seeds.py`.
- Prefix internal helpers with `_`, for example `_read_json()`, `_write_check_fixture()`, `_write_verify_fixture_for_clean_pass()`, `_invalidate_source_artifacts()`, and `_seed_entry_to_seed_deal()` in `skill_pipeline/check.py`, `tests/test_skill_check.py`, `tests/test_skill_verify.py`, `skill_pipeline/preprocess/source.py`, and `skill_pipeline/cli.py`.

**Variables:**
- Use `snake_case` for locals, parameters, and JSON keys across runtime code and tests, for example `deal_slug`, `project_root`, `evidence_items`, `coverage_notes`, and `invited_actor_ids`.
- Use `UPPER_SNAKE_CASE` for module constants, for example `PROJECT_ROOT` in `skill_pipeline/config.py`, `SCHEMA_VERSION` and `PIPELINE_VERSION` in `skill_pipeline/pipeline_models/common.py`, and `EXPECTED_STAGE_ORDER` in `tests/test_workflow_contract_surface.py`.

**Types:**
- Use `PascalCase` for Pydantic models, dataclasses, and enums, for example `SkillCheckReport` in `skill_pipeline/models.py`, `LoadedExtractArtifacts` in `skill_pipeline/extract_artifacts.py`, `ResolvedFrozenDocumentPaths` in `skill_pipeline/source_validation.py`, and `QuoteMatchType` in `skill_pipeline/pipeline_models/common.py`.

## Code Style

**Formatting:**
- Follow 4-space indentation and UTF-8 text encoding throughout `skill_pipeline/` and `tests/`.
- Default to `LF` line endings for tracked text. The line-ending policy is reinforced in `CLAUDE.md`, and `tests/test_skill_mirror_sync.py` explicitly checks that mirrored skill files are normalized away from `CRLF`.
- Default to `from __future__ import annotations` at the top of new Python modules. This is the dominant pattern in stage modules such as `skill_pipeline/cli.py`, `skill_pipeline/check.py`, `skill_pipeline/canonicalize.py`, `skill_pipeline/verify.py`, and in most test files such as `tests/test_skill_raw_stage.py` and `tests/test_skill_verify.py`.
- Keep public function signatures type-annotated. The stage entrypoints and helper functions in `skill_pipeline/check.py`, `skill_pipeline/preprocess/source.py`, `skill_pipeline/raw/fetch.py`, and `tests/test_skill_check.py` all use explicit return annotations.

**Linting:**
- No repo-level formatter or linter configuration is tracked in the repository root. No `ruff.toml`, `.ruff.toml`, `pyproject.toml` tool sections, `mypy.ini`, `tox.ini`, `noxfile.py`, or `.pre-commit-config.yaml` are present.
- Keep imports tidy and style decisions local to the file. There is no automated tool enforcing rearrangement.
- Use targeted inline suppressions only when the file already does so. Current examples are `# pragma: no cover` in `skill_pipeline/raw/fetch.py` and `skill_pipeline/raw/stage.py`, and `# noqa: S310` in `skill_pipeline/source/fetch.py`.

## Import Organization

**Order:**
1. `from __future__ import annotations`
2. Standard-library imports
3. Third-party imports such as `pydantic` or `pytest`
4. Absolute package-local imports from `skill_pipeline...`

**Path Aliases:**
- Not used. Import internal code with package-qualified imports such as `from skill_pipeline.models import SkillCheckReport` and `from skill_pipeline.paths import build_skill_paths`.

**Observed import pattern:**
```python
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Literal

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.extract_artifacts import LoadedExtractArtifacts, load_extract_artifacts
from skill_pipeline.models import CheckFinding, CheckReportSummary, SkillCheckReport
from skill_pipeline.paths import build_skill_paths, ensure_output_directories
```
Pattern shown in `skill_pipeline/check.py`.

## Error Handling

**Patterns:**
- Fail fast on missing inputs, schema mismatches, ambiguous discovery state, and invalid provenance. `skill_pipeline/check.py`, `skill_pipeline/verify.py`, `skill_pipeline/canonicalize.py`, `skill_pipeline/preprocess/source.py`, and `skill_pipeline/source_validation.py` all raise immediately instead of inventing defaults.
- Raise specific built-in exceptions matched to the contract:
  - `FileNotFoundError` for missing required artifacts in `skill_pipeline/check.py`, `skill_pipeline/verify.py`, `skill_pipeline/canonicalize.py`, and `skill_pipeline/enrich_core.py`
  - `ValueError` for contradictory or malformed artifact content in `skill_pipeline/preprocess/source.py`, `skill_pipeline/raw/discover.py`, and `skill_pipeline/canonicalize.py`
  - `RuntimeError` for failed upstream fetches in `skill_pipeline/raw/fetch.py` and `skill_pipeline/source/fetch.py`
  - `FileExistsError` for immutable-file violations in `skill_pipeline/raw/fetch.py`
- If cleanup is necessary, invalidate stale outputs and re-raise the original exception. `skill_pipeline/preprocess/source.py` is the concrete example: the stage wraps output publication in `try/except Exception`, calls `_invalidate_source_artifacts()`, then re-raises.

**Current fail-fast stage pattern:**
```python
def run_verify(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    paths = build_skill_paths(deal_slug, project_root=project_root)

    if not paths.actors_raw_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.actors_raw_path}")
    if not paths.events_raw_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.events_raw_path}")
```
Pattern shown in `skill_pipeline/verify.py`.

## Logging

**Framework:** None detected.

**Patterns:**
- Do not introduce a general logging framework. No `logging` or structured logger usage is present in `skill_pipeline/`.
- Emit machine-readable JSON to stdout for CLI-facing commands in `skill_pipeline/cli.py`, for example `summary.model_dump_json(indent=2)` and `json.dumps(result, indent=2)`.
- Persist stage outputs as JSON or JSONL artifacts on disk rather than relying on console logs. Current examples include:
  - `data/skill/<slug>/check/check_report.json`
  - `data/skill/<slug>/verify/verification_log.json`
  - `data/skill/<slug>/verify/verification_findings.json`
  - `data/skill/<slug>/coverage/coverage_summary.json`
  - `data/skill/<slug>/coverage/coverage_findings.json`

## Comments

**When to Comment:**
- Use short module docstrings for stage purpose when the file defines a major deterministic stage. Current examples are `skill_pipeline/check.py`, `skill_pipeline/canonicalize.py`, `skill_pipeline/coverage.py`, `skill_pipeline/enrich_core.py`, and `skill_pipeline/verify.py`.
- Use inline comments for invariants, classification rules, or platform-sensitive behavior. Current examples include:
  - the CRLF hash explanation in `skill_pipeline/source_validation.py`
  - rule labels in `skill_pipeline/enrich_core.py`
  - chronology-overlap coverage comments in `skill_pipeline/coverage.py`

**JSDoc/TSDoc:**
- Not applicable. The active codebase is Python-only.

## Function Design

**Size:** Keep stage entrypoints thin and push detail into focused helpers. `run_check()` in `skill_pipeline/check.py`, `run_verify()` in `skill_pipeline/verify.py`, and `preprocess_source_deal()` in `skill_pipeline/preprocess/source.py` mainly coordinate helper calls and write outputs.

**Parameters:**
- Prefer explicit keyword-only infrastructure parameters on stage entrypoints and helpers, especially `project_root`, `raw_dir`, `deals_dir`, `identity`, `get_filing_fn`, and `fetch_contents_fn`. This pattern appears in `skill_pipeline/check.py`, `skill_pipeline/verify.py`, `skill_pipeline/preprocess/source.py`, and `skill_pipeline/raw/fetch.py`.
- Use `pathlib.Path` rather than raw strings for filesystem parameters and computed paths. This is consistent across `skill_pipeline/` and `tests/`.

**Return Values:**
- Return integer exit codes from deterministic gate stages that map naturally to CLI behavior, for example `run_check()`, `run_verify()`, and `run_coverage()`.
- Return JSON-serializable dictionaries from fetch and preprocess stages that summarize work done, for example `skill_pipeline/raw/stage.py` and `skill_pipeline/preprocess/source.py`.
- Serialize Pydantic artifacts with `.model_dump_json(indent=2)` for JSON files and `.model_dump(mode="json")` when intermediate dicts are needed. This is used throughout `skill_pipeline/check.py`, `skill_pipeline/canonicalize.py`, `skill_pipeline/coverage.py`, `skill_pipeline/cli.py`, and `skill_pipeline/deal_agent.py`.

**Current artifact-writing pattern:**
```python
def _write_json(path: Path, report: SkillCheckReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
```
Pattern shown in `skill_pipeline/check.py`.

**Filesystem mutation pattern:**
- Prefer atomic temp-file replacement for generated outputs. Current implementations are `write_immutable_text()` and `atomic_write_text()` in `skill_pipeline/raw/fetch.py`, `_atomic_write_text()` in `skill_pipeline/preprocess/source.py`, and `_copy_if_present()` in `skill_pipeline/preprocess/source.py`.

## Module Design

**Exports:**
- Keep runtime modules single-purpose. The main stage files are `skill_pipeline/raw/stage.py`, `skill_pipeline/preprocess/source.py`, `skill_pipeline/canonicalize.py`, `skill_pipeline/check.py`, `skill_pipeline/verify.py`, `skill_pipeline/coverage.py`, and `skill_pipeline/enrich_core.py`.
- Centralize schema and artifact definitions in `skill_pipeline/models.py` and `skill_pipeline/pipeline_models/` rather than redefining ad hoc dict contracts in stage files.
- Keep `__init__.py` files thin and re-export only a small public surface. Current examples are `skill_pipeline/__init__.py`, `skill_pipeline/raw/__init__.py`, `skill_pipeline/source/__init__.py`, `skill_pipeline/normalize/__init__.py`, and `skill_pipeline/pipeline_models/__init__.py`.

**Barrel Files:**
- Limited and intentional. Re-export packages only where a small convenience surface already exists.

**Schema-first pattern:**
```python
class SkillModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceRef(SkillModel):
    block_id: str | None = None
    evidence_id: str | None = None
    anchor_text: str

    @model_validator(mode="after")
    def validate_reference_target(self) -> "EvidenceRef":
        if self.block_id is None and self.evidence_id is None:
            raise ValueError("At least one of block_id or evidence_id must be present.")
        return self
```
Pattern shown in `skill_pipeline/models.py`.

---

*Convention analysis: 2026-03-26*
