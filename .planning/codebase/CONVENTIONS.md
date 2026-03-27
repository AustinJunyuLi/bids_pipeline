# Coding Conventions

**Analysis Date:** 2026-03-27

## Naming Patterns

**Files:**
- Module files use `snake_case`: `canonicalize.py`, `enrich_core.py`, `verify.py`
- Package directories also use `snake_case`: `skill_pipeline/`, `pipeline_models/`, `normalize/`
- Test files follow pattern `test_<stage_or_component>.py`: `test_skill_check.py`, `test_skill_canonicalize.py`

**Functions:**
- Public and private functions use `snake_case`: `run_check()`, `run_canonicalize()`, `ensure_output_directories()`
- Internal helper functions prefixed with single underscore: `_read_json()`, `_write_json()`, `_check_proposal_terms()`, `_load_document_lines()`
- Descriptive names indicating purpose: `_upgrade_raw_actors()`, `_resolve_ref_to_span_id()`, `_build_coverage_cues()`

**Variables:**
- `snake_case` for all variables: `deal_slug`, `chronology_blocks`, `evidence_items`, `actor_ids`, `block_texts`
- Dictionary keys use `snake_case`: `"actor_id"`, `"event_type"`, `"evidence_refs"`, `"block_id"`
- Constants in `UPPER_SNAKE_CASE`: `ROUND_PAIRS`, `SPAN_EXPANSION_LINES`, `STRICT_QUOTE_MATCH_TYPES`, `CRITICAL_CUE_FAMILIES`
- Single underscore prefix for module-level constants meant to be private: `TRANSLATIONS`, `QUOTE_CHARS`

**Types:**
- Enum classes use `PascalCase`: `ActorRole`, `AdvisorKind`, `BidderKind`, `DatePrecision`, `EventType`
- Pydantic model classes use `PascalCase` with suffix patterns:
  - Artifact models: `SkillCheckReport`, `SkillVerificationLog`, `CoverageFindingsArtifact`
  - Data models: `RawSkillActorRecord`, `ChronologyBlock`, `EvidenceItem`
  - Enum StrEnum values use `snake_case`: `"bidder"`, `"advisor"`, `"financial"`, `"proposal"`

## Code Style

**Formatting:**
- 4-space indentation (enforced by project structure)
- Line length: No strict enforcer configured in `pyproject.toml`
- No black or ruff formatter configured; follow surrounding style

**Imports:**
- `from __future__ import annotations` appears at top of all modules (enables forward references)
- Standard library imports first (no grouping enforcer)
- Third-party imports: `json`, `pathlib.Path`, `pydantic` models
- Local imports: `from skill_pipeline.<module> import ...`
- Example from `cli.py`:
  ```python
  from __future__ import annotations

  import argparse
  import json
  from datetime import date
  from pathlib import Path
  from typing import Sequence
  from uuid import uuid4

  from skill_pipeline.canonicalize import run_canonicalize
  from skill_pipeline.check import run_check
  ```

**Linting:**
- No `.flake8`, `.pylintrc`, `ruff.toml`, or other linter config present
- No enforced formatting tool (no Black, Ruff, or similar)
- Style guide is implicit from existing code

## Function Design

**Type Hints:**
- Type hints required on all function signatures (Python 3.11+)
- Return type always specified: `-> int`, `-> dict`, `-> list[ChronologyBlock]`, `-> None`
- Parameter type hints: `path: Path`, `deal_slug: str`, `artifacts: LoadedExtractArtifacts`
- Union types use `|` syntax: `str | None`, `list[str] | None`, `dict[str, list[str]]`

**Keyword-only Arguments:**
- Functions use `*` to mark keyword-only args where appropriate
- Example: `def build_skill_paths(deal_slug: str, *, project_root: Path = PROJECT_ROOT)`
- Allows safe addition of new parameters without breaking positional calls

**Parameter Structure:**
- Lead with required positional parameters
- Use `*` to enforce keyword arguments for optional parameters
- Default values provided for configuration parameters: `project_root: Path = PROJECT_ROOT`

**Return Values:**
- Explicit return types always present
- Functions return structured data (Pydantic models or dicts): `-> SkillCheckReport`, `-> dict`
- Return `0` for success, non-zero for failure in CLI entry points (`main()`)
- Single return value per function (no multiple returns)

**Size:**
- Functions are kept focused and reasonably sized
- Large operations broken into private helper functions
- Examples: `_load_document_lines()`, `_check_proposal_terms()`, `_build_coverage_cues()`

## Module Design

**Exports:**
- Public functions begin without underscore: `run_check()`, `run_canonicalize()`, `build_skill_paths()`
- Private utilities begin with underscore: `_read_json()`, `_write_json()`, `_load_chronology_blocks()`
- Pydantic models are public and exported for validation

**Barrel Files:**
- Some `__init__.py` files are empty
- No re-export pattern; imports are explicit
- Modules export what they define; no aggregation pattern

**File Organization:**
- One primary public function per module (or closely related functions)
- Helper functions private with leading underscore
- Models and schemas in dedicated modules: `skill_pipeline/models.py`, `skill_pipeline/pipeline_models/`
- Stage runners at module level: `run_check()`, `run_verify()`, `run_canonicalize()`

## Error Handling

**Patterns:**
- Fail-fast philosophy: raise exceptions on invalid inputs or missing prerequisites
- Specific exception types: `FileNotFoundError`, `ValueError`
- Descriptive error messages with context

**Examples from codebase:**
```python
# From check.py - explicit file existence check
def _read_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))

# From canonicalize.py - descriptive validation error
if evidence_id not in evidence_items_by_id:
    raise ValueError(f"Unknown evidence_id in evidence reference: {evidence_id!r}")

# From verify.py - informative error for missing prerequisites
if not filings_dir.exists():
    raise FileNotFoundError(
        f"Raw filings directory not found: {filings_dir}. "
        "Run 'skill-pipeline raw-fetch --deal <slug>' first."
    )
```

**No Silent Failures:**
- No broad try/except blocks that hide errors
- Missing required files raise `FileNotFoundError` immediately
- Invalid data raises `ValueError` with specifics
- Preconditions checked before operations

**Error Recovery:**
- No fallback behavior: gates fail hard on violated invariants
- Exception handling used only for parsing (e.g., `date.fromisoformat()`)
- Pipeline design is fail-fast: check before compute, verify before enrich

## Logging

**Framework:** No logging framework imported; uses only exception raising

**Patterns:**
- Errors surfaced via exceptions with descriptive messages
- No debug logging or warning logs
- Console output only through sys.exit() and exception messages
- Each stage reports its status through artifact files or return codes

## Comments and Documentation

**When to Comment:**
- Docstrings on all public functions
- Docstrings brief but descriptive
- Inline comments rare; code is self-documenting via naming

**JSDoc/Docstring Style:**
- Triple-quote docstrings on public functions
- Format: brief description of what the function does
- Example: `"""Deterministic structural gate for extracted skill artifacts."""`
- Longer docstrings for complex operations include explanation of behavior

**Examples:**
```python
# From verify.py - brief docstring
def _load_document_lines(filings_dir: Path) -> dict[str, list[str]]:
    """Load raw filing text keyed by document_id (path.stem).

    Raises FileNotFoundError if filings directory is missing — this means
    ``pipeline raw fetch`` was not run.
    """

# From enrich_core.py - functional docstring
def _pair_rounds(events: list[SkillEventRecord], actors) -> list[dict]:
    """Pair round announcements with deadlines. Preserve extension rounds as round_scope='extension'."""
```

## Pydantic Model Conventions

**Base Class:**
- All models inherit from `BaseModel` (via `SkillModel` or `PipelineModel` base class)
- `model_config = ConfigDict(extra="forbid")` prevents unknown fields

**Validation:**
- Use `model_validator` for cross-field validation: `@model_validator(mode="after")`
- Use `Field()` for constraints: `Field(default_factory=list)`
- Example from `models.py`:
  ```python
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

**JSON Serialization:**
- Models use `model_dump()` for Python dict conversion
- Models use `model_validate()` for JSON parsing (JSONL lines)
- Example from `canonicalize.py`:
  ```python
  blocks.append(ChronologyBlock.model_validate_json(line))
  ```

## JSONL Format Conventions

**Pattern:**
- One JSON object per line
- Pydantic models parse via `model_validate_json(line)`
- Empty lines are skipped: `if not line.strip(): continue`
- Files read as single string then split: `path.read_text().splitlines()`

**Examples:**
```python
# Reading JSONL
for line in path.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    blocks.append(ChronologyBlock.model_validate_json(line))
```

## Constants and Configuration

**Module Constants:**
- Defined at module level before functions
- `UPPER_SNAKE_CASE` for module-level constants
- Example from `enrich_core.py`:
  ```python
  ROUND_PAIRS = [
      ("final_round_inf_ann", "final_round_inf", "informal"),
      ("final_round_ann", "final_round", "formal"),
      ("final_round_ext_ann", "final_round_ext", "extension"),
  ]
  ```

**Configuration Module:**
- `skill_pipeline/config.py` holds project paths and primary filing types
- `PROJECT_ROOT` derived from module location: `Path(__file__).resolve().parent.parent`

---

*Convention analysis: 2026-03-27*
