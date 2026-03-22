# Pipeline Consolidation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Consolidate all agent skills into Python modules in `skill_pipeline/`, producing a single `skill-pipeline run --deal <slug>` command.

**Architecture:** Rename canonicalize → materialize with separate output dir. Add LLM backend wrapping OpenAI SDK for NewAPI. Port extract, repair, enrich-interpret, export from skill files to Python modules. Wire into end-to-end runner.

**Tech Stack:** Python 3.11+, Pydantic 2, OpenAI SDK, pytest

**Design doc:** `docs/plans/2026-03-22-pipeline-consolidation-design.md`

---

## Phase 1: Foundation — Rename + Path Separation

### Task 1: Add materialize paths to SkillPathSet

**Files:**
- Modify: `skill_pipeline/paths.py`
- Modify: `skill_pipeline/models.py`
- Test: `tests/test_skill_pipeline.py` (existing, verify paths)

**Step 1: Add new path fields to SkillPathSet model**

In `skill_pipeline/models.py`, add to `SkillPathSet`:

```python
materialize_dir: Path
materialized_actors_path: Path
materialized_events_path: Path
materialized_spans_path: Path
materialize_log_path: Path
repair_dir: Path
repair_log_path: Path
omission_findings_path: Path
```

**Step 2: Wire paths in build_skill_paths**

In `skill_pipeline/paths.py`, add after `canonicalize_dir`:

```python
materialize_dir = skill_root / "materialize"
repair_dir = skill_root / "repair"
```

And in the return statement:

```python
materialize_dir=materialize_dir,
materialized_actors_path=materialize_dir / "actors.json",
materialized_events_path=materialize_dir / "events.json",
materialized_spans_path=materialize_dir / "spans.json",
materialize_log_path=materialize_dir / "materialize_log.json",
repair_dir=repair_dir,
repair_log_path=repair_dir / "repair_log.json",
omission_findings_path=coverage_dir / "omission_findings.json",
```

**Step 3: Add materialize_dir and repair_dir to ensure_output_directories**

```python
paths.materialize_dir.mkdir(parents=True, exist_ok=True)
paths.repair_dir.mkdir(parents=True, exist_ok=True)
```

**Step 4: Run tests**

Run: `pytest tests/test_skill_pipeline.py -q`
Expected: PASS (existing tests don't reference new paths, just verify no breakage)

**Step 5: Commit**

```bash
git add skill_pipeline/models.py skill_pipeline/paths.py
git commit -m "feat: add materialize and repair paths to SkillPathSet"
```

---

### Task 2: Rename canonicalize.py → materialize.py

**Files:**
- Rename: `skill_pipeline/canonicalize.py` → `skill_pipeline/materialize.py`
- Modify: `skill_pipeline/materialize.py` (change output paths)
- Rename: `tests/test_skill_canonicalize.py` → `tests/test_skill_materialize.py`
- Modify: `skill_pipeline/cli.py`

**Step 1: Rename file and update function name**

```bash
git mv skill_pipeline/canonicalize.py skill_pipeline/materialize.py
```

In `materialize.py`:
- Rename `run_canonicalize` → `run_materialize`
- Change docstring to reference "materialize"

**Step 2: Change output writes to materialize/ directory**

In `run_materialize()`, change the four write calls (lines 540-555):

```python
# OLD: paths.actors_raw_path, paths.events_raw_path, paths.spans_path, paths.canonicalize_log_path
# NEW:
paths.materialized_actors_path.parent.mkdir(parents=True, exist_ok=True)
paths.materialized_actors_path.write_text(
    canonical_actors.model_dump_json(indent=2), encoding="utf-8",
)
paths.materialized_events_path.write_text(
    canonical_events.model_dump_json(indent=2), encoding="utf-8",
)
paths.materialized_spans_path.write_text(
    span_registry.model_dump_json(indent=2), encoding="utf-8",
)
paths.materialize_log_path.write_text(
    json.dumps(log, indent=2), encoding="utf-8",
)
```

**Step 3: Rename test file and update imports**

```bash
git mv tests/test_skill_canonicalize.py tests/test_skill_materialize.py
```

In `test_skill_materialize.py`:
- Replace `from skill_pipeline.canonicalize import run_canonicalize` with
  `from skill_pipeline.materialize import run_materialize`
- Replace all `run_canonicalize` calls with `run_materialize`
- Update assertions to check `materialize/` paths instead of `extract/` paths:
  - Check `data/skill/<slug>/materialize/actors.json` exists (not `extract/actors_raw.json` being overwritten)
  - Check `data/skill/<slug>/materialize/spans.json` exists
  - Verify `extract/actors_raw.json` is UNCHANGED after materialize runs

**Step 4: Update CLI import and command**

In `skill_pipeline/cli.py`:
- Replace `from skill_pipeline.canonicalize import run_canonicalize` with
  `from skill_pipeline.materialize import run_materialize`
- Change `if args.command == "canonicalize":` to `if args.command == "materialize":`
- Change `return run_canonicalize(...)` to `return run_materialize(...)`
- Update the subparser: rename `"canonicalize"` to `"materialize"` in `subparsers.add_parser`
- Keep `"canonicalize"` as an alias subparser pointing to same function (backward compat during migration)

**Step 5: Run tests**

Run: `pytest tests/test_skill_materialize.py -q -v`
Expected: PASS (tests verify materialize writes to new paths, raw artifacts preserved)

Run: `pytest -q` (full suite)
Expected: PASS

**Step 6: Commit**

```bash
git add -A
git commit -m "refactor: rename canonicalize to materialize, separate output directory"
```

---

### Task 3: Update downstream stages to read from materialize/

**Files:**
- Modify: `skill_pipeline/extract_artifacts.py`
- Modify: `skill_pipeline/check.py`
- Modify: `skill_pipeline/verify.py`
- Modify: `skill_pipeline/coverage.py`
- Modify: `skill_pipeline/enrich_core.py`
- Test: existing test files for each module

**Step 1: Add load_materialized_artifacts() to extract_artifacts.py**

Add a new function that reads from `materialize/` paths:

```python
def load_materialized_artifacts(paths: SkillPathSet) -> LoadedExtractArtifacts:
    """Load canonical artifacts from materialize/ directory."""
    if not paths.materialized_actors_path.exists():
        raise FileNotFoundError(
            f"Missing materialized artifacts: {paths.materialized_actors_path}. "
            "Run 'skill-pipeline materialize --deal <slug>' first."
        )
    actors_payload = _read_json(paths.materialized_actors_path)
    events_payload = _read_json(paths.materialized_events_path)
    spans_payload = (
        _read_json(paths.materialized_spans_path)
        if paths.materialized_spans_path.exists()
        else {"spans": []}
    )
    return LoadedExtractArtifacts(
        mode="canonical",
        raw_actors=None,
        raw_events=None,
        actors=SkillActorsArtifact.model_validate(actors_payload),
        events=SkillEventsArtifact.model_validate(events_payload),
        spans=SpanRegistryArtifact.model_validate(spans_payload),
    )
```

**Step 2: Update check.py, verify.py, coverage.py, enrich_core.py**

In each file, change:
```python
# OLD
from skill_pipeline.extract_artifacts import load_extract_artifacts
artifacts = load_extract_artifacts(paths)

# NEW
from skill_pipeline.extract_artifacts import load_materialized_artifacts
artifacts = load_materialized_artifacts(paths)
```

**Step 3: Update test fixtures**

In `tests/test_skill_check.py`, `test_skill_verify.py`, `test_skill_coverage.py`,
`test_skill_enrich_core.py`: update fixture writers to write canonical artifacts
to `materialize/` directory instead of `extract/`. Keep raw artifacts in
`extract/` for any tests that need them.

**Step 4: Run all tests**

Run: `pytest -q`
Expected: PASS

**Step 5: Commit**

```bash
git add -A
git commit -m "refactor: downstream stages read from materialize/ not extract/"
```

---

## Phase 2: LLM Backend

### Task 4: Add openai dependency and create llm.py

**Files:**
- Modify: `pyproject.toml`
- Create: `skill_pipeline/llm.py`
- Create: `tests/test_skill_llm.py`

**Step 1: Write the failing test**

Create `tests/test_skill_llm.py`:

```python
"""Tests for LLM backend wrapper."""
from __future__ import annotations

from unittest.mock import MagicMock, patch
from pydantic import BaseModel

from skill_pipeline.llm import invoke_structured


class SampleOutput(BaseModel):
    name: str
    value: int


def _mock_chat_response(content: str):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def test_invoke_structured_returns_validated_model():
    with patch("skill_pipeline.llm._get_client") as mock_client_fn:
        client = MagicMock()
        mock_client_fn.return_value = client
        client.chat.completions.create.return_value = _mock_chat_response(
            '{"name": "test", "value": 42}'
        )
        result = invoke_structured(
            system_prompt="You are a test.",
            user_message="Return a sample.",
            output_model=SampleOutput,
        )
        assert isinstance(result, SampleOutput)
        assert result.name == "test"
        assert result.value == 42


def test_invoke_structured_retries_on_validation_error():
    with patch("skill_pipeline.llm._get_client") as mock_client_fn:
        client = MagicMock()
        mock_client_fn.return_value = client
        # First call returns invalid JSON, second returns valid
        client.chat.completions.create.side_effect = [
            _mock_chat_response('{"name": "test"}'),  # missing 'value'
            _mock_chat_response('{"name": "test", "value": 42}'),
        ]
        result = invoke_structured(
            system_prompt="You are a test.",
            user_message="Return a sample.",
            output_model=SampleOutput,
        )
        assert result.value == 42
        assert client.chat.completions.create.call_count == 2


def test_invoke_structured_raises_after_second_failure():
    with patch("skill_pipeline.llm._get_client") as mock_client_fn:
        client = MagicMock()
        mock_client_fn.return_value = client
        client.chat.completions.create.return_value = _mock_chat_response(
            '{"name": "test"}'  # always missing 'value'
        )
        try:
            invoke_structured(
                system_prompt="You are a test.",
                user_message="Return a sample.",
                output_model=SampleOutput,
            )
            assert False, "Should have raised"
        except ValueError as e:
            assert "validation" in str(e).lower() or "retry" in str(e).lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_skill_llm.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'skill_pipeline.llm'`

**Step 3: Write implementation**

Add `openai` to `pyproject.toml` dependencies:

```toml
dependencies = [
  "anthropic>=0.49",
  "edgartools>=5.23",
  "openai>=1.60",
  "openpyxl>=3.1",
  "pydantic>=2.0",
  "pytest>=8.0",
]
```

Create `skill_pipeline/llm.py`:

```python
"""Thin LLM wrapper for structured output via OpenAI-compatible API."""
from __future__ import annotations

import json
import os
from typing import TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

_DEFAULT_MODEL = "gpt-5.4"
_DEFAULT_BASE_URL = "https://api.newapi.pro/v1"


def _get_client():
    from openai import OpenAI

    return OpenAI(
        api_key=os.environ.get("NEWAPI_API_KEY", ""),
        base_url=os.environ.get("NEWAPI_BASE_URL", _DEFAULT_BASE_URL),
    )


def _schema_outline(model: type[BaseModel]) -> str:
    """Render a JSON schema outline for the system prompt."""
    schema = model.model_json_schema()
    return json.dumps(schema, indent=2)


def invoke_structured(
    system_prompt: str,
    user_message: str,
    output_model: type[T],
    *,
    model: str | None = None,
    max_output_tokens: int = 16_000,
    temperature: float = 0.0,
    reasoning_effort: str = "none",
) -> T:
    """Send prompt, parse JSON response, validate against Pydantic model.

    Prompted JSON mode: schema outline appended to system prompt.
    Retries once on validation failure with error feedback.
    Raises ValueError on second failure.
    """
    client = _get_client()
    effective_model = model or os.environ.get("NEWAPI_MODEL", _DEFAULT_MODEL)

    schema_text = _schema_outline(output_model)
    full_system = (
        f"{system_prompt}\n\n"
        f"You MUST respond with exactly one JSON object matching this schema:\n"
        f"```json\n{schema_text}\n```\n"
        f"Return ONLY the JSON object, no other text."
    )

    messages = [
        {"role": "system", "content": full_system},
        {"role": "user", "content": user_message},
    ]

    extra_kwargs: dict = {}
    if reasoning_effort != "none":
        extra_kwargs["reasoning_effort"] = reasoning_effort

    response = client.chat.completions.create(
        model=effective_model,
        messages=messages,
        max_completion_tokens=max_output_tokens,
        temperature=temperature,
        **extra_kwargs,
    )

    raw_text = response.choices[0].message.content.strip()
    # Strip markdown code fences if present
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        raw_text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    try:
        data = json.loads(raw_text)
        return output_model.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as first_error:
        pass

    # Retry with error feedback
    messages.append({"role": "assistant", "content": raw_text})
    messages.append({
        "role": "user",
        "content": (
            f"Your response failed validation:\n{first_error}\n\n"
            f"Fix the JSON and return only the corrected JSON object."
        ),
    })

    response = client.chat.completions.create(
        model=effective_model,
        messages=messages,
        max_completion_tokens=max_output_tokens,
        temperature=temperature,
        **extra_kwargs,
    )

    raw_text = response.choices[0].message.content.strip()
    if raw_text.startswith("```"):
        lines = raw_text.split("\n")
        raw_text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    try:
        data = json.loads(raw_text)
        return output_model.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as second_error:
        raise ValueError(
            f"LLM output failed validation after retry: {second_error}"
        ) from second_error
```

**Step 4: Install openai and run tests**

Run: `pip install openai>=1.60`
Run: `pytest tests/test_skill_llm.py -q -v`
Expected: PASS

**Step 5: Commit**

```bash
git add pyproject.toml skill_pipeline/llm.py tests/test_skill_llm.py
git commit -m "feat: add LLM backend wrapper for NewAPI/OpenAI"
```

---

## Phase 3: Export Module (deterministic)

### Task 5: Write export.py

**Files:**
- Create: `skill_pipeline/export.py`
- Create: `tests/test_skill_export.py`
- Modify: `skill_pipeline/cli.py`

**Step 1: Write failing tests for core export logic**

Create `tests/test_skill_export.py` with tests for:

```python
def test_bidder_type_mapping():
    """Test 11-priority type composition from actor fields."""

def test_bidderid_assignment_pre_nda_fractional():
    """Pre-NDA events get fractional IDs spaced in (0, 1)."""

def test_same_date_sort_round_ann_before_drop():
    """Final Round Ann precedes DropTarget on same date."""

def test_note_mapping_proposal_is_na():
    """Proposal events map to note='NA'."""

def test_dropout_label_from_enrichment():
    """Drop events use enrichment label as note value."""

def test_type_only_on_first_row_per_actor():
    """Bidder type populated only on first row for each actor."""

def test_date_format_mm_dd_yyyy():
    """Dates formatted as MM/DD/YYYY per Alex instructions."""

def test_enterprise_value_flagged_in_review():
    """Enterprise-value-only bids get review flag."""

def test_range_for_point_bid():
    """Point bids output range as val-val (e.g., 15-15)."""

def test_cash_column_mapping():
    """consideration_type=cash -> cash=1, else NA."""
```

Each test constructs minimal synthetic actors/events/enrichment artifacts,
calls the export function, and asserts on the CSV output.

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_skill_export.py -q`
Expected: FAIL with import error

**Step 3: Implement export.py**

Create `skill_pipeline/export.py` with:

```python
"""Deterministic CSV export from materialized artifacts + enrichment."""
from __future__ import annotations

import csv
import io
from decimal import Decimal
from pathlib import Path

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.extract_artifacts import load_materialized_artifacts
from skill_pipeline.models import (
    SkillActorRecord,
    SkillEnrichmentArtifact,
    SkillEventRecord,
    SkillPathSet,
)
from skill_pipeline.paths import build_skill_paths, ensure_output_directories
from skill_pipeline.seeds import load_seed_entry


# Event-type sort priority for same-date ordering
_TYPE_PRIORITY = {
    "target_sale": 0, "target_sale_public": 1, "bidder_sale": 2,
    "bidder_interest": 3, "activist_sale": 4, "sale_press_release": 5,
    "bid_press_release": 6, "ib_retention": 7, "nda": 8,
    "final_round_inf_ann": 9, "final_round_ann": 10,
    "drop": 11,
    "final_round_inf": 12, "final_round": 13,
    "final_round_ext_ann": 14, "final_round_ext": 15,
    "proposal": 16, "executed": 17, "terminated": 18, "restarted": 19,
}

NOTE_MAP = {
    "target_sale": "Target Sale", "target_sale_public": "Target Sale Public",
    "bidder_sale": "Bidder Sale", "bidder_interest": "Bidder Interest",
    "activist_sale": "Activist Sale", "sale_press_release": "Sale Press Release",
    "bid_press_release": "Bid Press Release", "ib_retention": "IB",
    "nda": "NDA", "proposal": "NA",
    "final_round_inf_ann": "Final Round Inf Ann",
    "final_round_inf": "Final Round Inf",
    "final_round_ann": "Final Round Ann", "final_round": "Final Round",
    "final_round_ext_ann": "Final Round Ext Ann",
    "final_round_ext": "Final Round Ext",
    "executed": "Executed", "terminated": "Terminated", "restarted": "Restarted",
}


def compose_bidder_type(actor: SkillActorRecord) -> str:
    """11-priority bidder type composition."""
    # ... implementation per priority table in design doc


def assign_bidder_ids(sorted_events: list[SkillEventRecord]) -> list[float]:
    """5-step bidderID algorithm."""
    # ... implementation per design doc


def format_date(date_obj, precision) -> tuple[str, str]:
    """Return (date_r, date_p) in MM/DD/YYYY format."""
    # ... implementation


def run_export(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    """Export materialized artifacts + enrichment to CSV."""
    # ... load artifacts, build rows, write CSV
```

Key implementation details:
- `compose_bidder_type()`: check geography → listing_status → bidder_kind in
  priority order, return combined string
- `assign_bidder_ids()`: find first NDA index, assign fractional pre-NDA,
  integer post-NDA
- `format_date()`: convert ResolvedDate to MM/DD/YYYY string pair
- `run_export()`: load materialized artifacts + enrichment, sort events,
  assign IDs, build CSV rows, write header + data

**Step 4: Run tests**

Run: `pytest tests/test_skill_export.py -q -v`
Expected: PASS

**Step 5: Wire into CLI**

In `skill_pipeline/cli.py`: add `export` subparser and handler.

**Step 6: Commit**

```bash
git add skill_pipeline/export.py tests/test_skill_export.py skill_pipeline/cli.py
git commit -m "feat: add deterministic CSV export module"
```

---

## Phase 4: Extract Module (LLM)

### Task 6: Write extract.py

**Files:**
- Create: `skill_pipeline/extract.py`
- Create: `skill_pipeline/prompts.py` (system prompts for extraction)
- Create: `tests/test_skill_extract.py`
- Modify: `skill_pipeline/cli.py`

**Step 1: Write failing tests**

```python
def test_extract_actors_writes_raw_artifact(tmp_path):
    """Extract creates actors_raw.json with RawSkillActorsArtifact schema."""

def test_extract_events_writes_raw_artifact(tmp_path):
    """Extract creates events_raw.json with RawSkillEventsArtifact schema."""

def test_extract_events_receives_actor_roster(tmp_path):
    """Event extraction prompt includes actor roster from actor extraction."""

def test_extract_gap_reread_populates_coverage_notes(tmp_path):
    """Gap re-read sweep populates coverage_notes on events artifact."""

def test_extract_excludes_partial_company_bids(tmp_path):
    """Bids for segments/percentages are excluded."""

def test_extract_excludes_unsigned_ndas(tmp_path):
    """NDAs sent but not signed are excluded."""
```

Each test mocks `invoke_structured` to return synthetic actor/event data
and verifies the output artifacts.

**Step 2: Implement extract.py**

```python
"""LLM-driven extraction of actors and events from SEC filing."""
from __future__ import annotations

import json
from pathlib import Path

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.llm import invoke_structured
from skill_pipeline.models import RawSkillActorsArtifact, RawSkillEventsArtifact
from skill_pipeline.paths import build_skill_paths, ensure_output_directories
from skill_pipeline.seeds import load_seed_entry
from skill_pipeline.prompts import build_actor_prompt, build_event_prompt


def run_extract(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    """Two-pass extraction: actors then events with gap re-read."""
    paths = build_skill_paths(deal_slug, project_root=project_root)
    ensure_output_directories(paths)
    seed = load_seed_entry(deal_slug, seeds_path=paths.seeds_path)

    # Load source
    blocks_text = paths.chronology_blocks_path.read_text(encoding="utf-8")
    evidence_text = paths.evidence_items_path.read_text(encoding="utf-8")

    # Pass 1a: Extract actors
    actor_system, actor_user = build_actor_prompt(seed, blocks_text, evidence_text)
    actors = invoke_structured(actor_system, actor_user, RawSkillActorsArtifact)

    # Pass 1b: Extract events (with actor roster as context)
    event_system, event_user = build_event_prompt(
        seed, blocks_text, evidence_text, actors
    )
    events = invoke_structured(event_system, event_user, RawSkillEventsArtifact)

    # Write raw artifacts (never overwritten by materialize)
    paths.actors_raw_path.write_text(
        actors.model_dump_json(indent=2), encoding="utf-8"
    )
    paths.events_raw_path.write_text(
        events.model_dump_json(indent=2), encoding="utf-8"
    )
    return 0
```

**Step 3: Create prompts.py**

```python
"""System and user prompts for LLM extraction stages."""
from __future__ import annotations

from skill_pipeline.models import SeedEntry, RawSkillActorsArtifact


def build_actor_prompt(seed, blocks_text: str, evidence_text: str) -> tuple[str, str]:
    """Build system + user prompts for actor extraction."""
    system = _ACTOR_SYSTEM_PROMPT  # encodes actor roles, schema, instructions
    user = (
        f"Deal: {seed.target_name} / {seed.acquirer or 'unknown acquirer'}\n"
        f"Date announced: {seed.date_announced or 'unknown'}\n\n"
        f"## Chronology Blocks\n{blocks_text}\n\n"
        f"## Evidence Items\n{evidence_text}"
    )
    return system, user


def build_event_prompt(
    seed, blocks_text: str, evidence_text: str, actors: RawSkillActorsArtifact
) -> tuple[str, str]:
    """Build system + user prompts for event extraction."""
    # ... includes actor roster in user message for cross-reference


def build_repair_prompt(findings: list, filing_context: str) -> tuple[str, str]:
    """Build prompt for repair stage."""


def build_omission_audit_prompt(
    uncovered_blocks: str, coverage_findings: str
) -> tuple[str, str]:
    """Build prompt for omission audit."""


def build_enrich_interpret_prompt(task_name: str, context: str) -> tuple[str, str]:
    """Build prompt for interpretive enrichment tasks."""
```

The actual prompt text is ported from the SKILL.md files. The 20-event
taxonomy, actor roles, formality signals, MoneyTerms schema, and exclusion
rules are encoded in the system prompts.

**Step 4: Run tests, wire CLI, commit**

Run: `pytest tests/test_skill_extract.py -q -v`
Expected: PASS

```bash
git add skill_pipeline/extract.py skill_pipeline/prompts.py tests/test_skill_extract.py skill_pipeline/cli.py
git commit -m "feat: add LLM extraction module"
```

---

## Phase 5: Omission Audit

### Task 7: Write omission_audit.py

**Files:**
- Create: `skill_pipeline/omission_audit.py`
- Create: `tests/test_skill_omission_audit.py`
- Modify: `skill_pipeline/cli.py`

Reads coverage findings + uncovered source regions. Sends to LLM for semantic
gap detection. Outputs `coverage/omission_findings.json`.

**Implementation:** ~80 lines. Load coverage_findings, identify uncovered
blocks, construct prompt, call `invoke_structured` with output model for
structured omission findings, write result.

**Tests:** Mock LLM, verify output schema and file creation.

```bash
git commit -m "feat: add LLM omission audit module"
```

---

## Phase 6: Repair Module

### Task 8: Write repair.py

**Files:**
- Create: `skill_pipeline/repair.py`
- Create: `tests/test_skill_repair.py`
- Modify: `skill_pipeline/cli.py`

**Key tests:**

```python
def test_repair_fails_closed_on_non_repairable():
    """Pipeline stops if any error-level finding is non_repairable."""

def test_repair_patches_raw_artifacts():
    """Repair writes to extract/ (raw schema), not materialize/."""

def test_repair_reruns_deterministic_stages():
    """After patching, re-runs materialize+check+verify+coverage."""

def test_repair_stops_after_two_rounds():
    """Max 2 repair rounds. Fails if errors remain."""

def test_repair_passes_when_no_errors():
    """No-op when all findings are warnings only."""
```

**Implementation:** ~150 lines.

```python
def run_repair(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    """LLM-driven repair loop. Max 2 rounds."""
    paths = build_skill_paths(deal_slug, project_root=project_root)

    for round_num in range(1, 3):
        findings = _load_all_findings(paths)
        errors = [f for f in findings if f.severity == "error"]

        if not errors:
            break  # all clear

        non_repairable = [f for f in errors if f.repairability == "non_repairable"]
        if non_repairable:
            raise RuntimeError(
                f"Round {round_num}: {len(non_repairable)} non-repairable errors. "
                "Pipeline cannot continue."
            )

        # LLM repair call
        patches = _call_repair_llm(paths, errors)
        _apply_patches(paths, patches)

        # Re-run deterministic stages
        run_materialize(deal_slug, project_root=project_root)
        run_check(deal_slug, project_root=project_root)
        run_verify(deal_slug, project_root=project_root)
        run_coverage(deal_slug, project_root=project_root)

    # Final gate check
    final_findings = _load_all_findings(paths)
    final_errors = [f for f in final_findings if f.severity == "error"]
    if final_errors:
        raise RuntimeError(
            f"Repair failed: {len(final_errors)} errors remain after 2 rounds."
        )

    return 0
```

```bash
git commit -m "feat: add LLM repair module with 2-round loop"
```

---

## Phase 7: Enrich Interpret

### Task 9: Write enrich_interpret.py

**Files:**
- Create: `skill_pipeline/enrich_interpret.py`
- Create: `tests/test_skill_enrich_interpret.py`
- Modify: `skill_pipeline/cli.py`

**Four LLM tasks, each a separate call:**

1. Dropout classification — output: `dict[str, DropoutClassification]`
2. Initiation judgment — output: `InitiationJudgment`
3. Advisory verification — output: `dict[str, AdvisoryVerificationRecord]`
4. Count reconciliation — output: `list[CountReconciliationRecord]`

**Tests:** Mock LLM for each task, verify output merges with
`deterministic_enrichment.json` into final `enrichment.json`.

```bash
git commit -m "feat: add LLM interpretive enrichment module"
```

---

## Phase 8: End-to-End Orchestrator

### Task 10: Write run.py

**Files:**
- Create: `skill_pipeline/run.py`
- Create: `tests/test_skill_run.py`
- Modify: `skill_pipeline/cli.py`

**Implementation:**

```python
"""End-to-end pipeline orchestrator."""
from __future__ import annotations

from pathlib import Path

from skill_pipeline.config import PROJECT_ROOT


def run_deal(
    deal_slug: str,
    *,
    project_root: Path = PROJECT_ROOT,
    skip_reconcile: bool = False,
) -> int:
    """Run all pipeline stages for a deal."""
    from skill_pipeline.check import run_check
    from skill_pipeline.coverage import run_coverage
    from skill_pipeline.enrich_core import run_enrich_core
    from skill_pipeline.enrich_interpret import run_enrich_interpret
    from skill_pipeline.export import run_export
    from skill_pipeline.extract import run_extract
    from skill_pipeline.materialize import run_materialize
    from skill_pipeline.omission_audit import run_omission_audit
    from skill_pipeline.repair import run_repair
    from skill_pipeline.verify import run_verify

    print(f"[1/11] Extracting actors and events...")
    run_extract(deal_slug, project_root=project_root)

    print(f"[2/11] Materializing canonical artifacts...")
    run_materialize(deal_slug, project_root=project_root)

    print(f"[3/11] Running structural checks...")
    run_check(deal_slug, project_root=project_root)

    print(f"[4/11] Running quote verification...")
    run_verify(deal_slug, project_root=project_root)

    print(f"[5/11] Running coverage audit...")
    run_coverage(deal_slug, project_root=project_root)

    print(f"[6/11] Running omission audit...")
    run_omission_audit(deal_slug, project_root=project_root)

    print(f"[7/11] Running repair loop...")
    run_repair(deal_slug, project_root=project_root)

    print(f"[8/11] Running deterministic enrichment...")
    run_enrich_core(deal_slug, project_root=project_root)

    print(f"[9/11] Running interpretive enrichment...")
    run_enrich_interpret(deal_slug, project_root=project_root)

    print(f"[10/11] Exporting CSV...")
    run_export(deal_slug, project_root=project_root)

    if not skip_reconcile:
        print(f"[11/11] Running reconciliation...")
        from skill_pipeline.reconcile import run_reconcile
        run_reconcile(deal_slug, project_root=project_root)

    print(f"Pipeline complete for {deal_slug}.")
    return 0
```

**Test:** Mock all LLM calls, run on synthetic fixtures, verify all output
artifacts exist.

**CLI:** Add `run` subparser with `--deal` and `--skip-reconcile` flags.

```bash
git commit -m "feat: add end-to-end pipeline orchestrator"
```

---

## Phase 9: Reconcile

### Task 11: Write reconcile.py

**Files:**
- Create: `skill_pipeline/reconcile.py`
- Create: `tests/test_skill_reconcile.py`
- Modify: `skill_pipeline/cli.py`

Port the reconciliation logic from the `/reconcile-alex` skill file. This is
the only stage that reads from `example/deal_details_Alex_2026.xlsx`.

**Implementation:** ~200 lines. Load Alex's rows, load pipeline output, match
events by family, compare fields, arbitrate via filing text, write report.

```bash
git commit -m "feat: add post-export reconciliation module"
```

---

## Phase 10: Cleanup

### Task 12: Move skill files, delete mirrors, update docs

**Files:**
- Move: `.claude/skills/*/SKILL.md` → `docs/skills/*.md`
- Delete: `.codex/skills/` (entire directory)
- Delete: `.cursor/skills/` (entire directory)
- Delete: `.claude/skills/` agent skill directories
- Modify: `CLAUDE.md`

**Step 1: Move skill files to docs**

```bash
mkdir -p docs/skills
cp .claude/skills/extract-deal/SKILL.md docs/skills/extract-deal.md
cp .claude/skills/verify-extraction/SKILL.md docs/skills/verify-extraction.md
cp .claude/skills/enrich-deal/SKILL.md docs/skills/enrich-deal.md
cp .claude/skills/export-csv/SKILL.md docs/skills/export-csv.md
cp .claude/skills/deal-agent/SKILL.md docs/skills/deal-agent.md
cp .claude/skills/reconcile-alex/SKILL.md docs/skills/reconcile-alex.md
```

**Step 2: Delete skill directories and mirrors**

```bash
rm -rf .claude/skills/extract-deal
rm -rf .claude/skills/verify-extraction
rm -rf .claude/skills/enrich-deal
rm -rf .claude/skills/export-csv
rm -rf .claude/skills/reconcile-alex
rm -rf .codex/skills/
rm -rf .cursor/skills/
```

Keep `.claude/skills/deal-agent/` as it's used for preflight (or move to docs
if preflight is handled by `skill-pipeline deal-agent`).

**Step 3: Update CLAUDE.md**

Major updates:
- Remove "End-to-end hybrid sequence" section, replace with
  `skill-pipeline run --deal <slug>`
- Remove "Agent-facing manual" section
- Remove all `/extract-deal`, `/verify-extraction`, `/enrich-deal`,
  `/export-csv`, `/reconcile-alex` references
- Update "Build, Test, and Development Commands" with new CLI commands
- Update artifact directory table (add `materialize/`, `repair/`)
- Update environment variables (add NEWAPI_*, deprecate old vars)
- Remove "Benchmark separation" rules about not reading skill files
  pre-export (no longer relevant — no agent skills to contaminate)

**Step 4: Update pyproject.toml**

Remove stale `pipeline` package from find includes if present.

**Step 5: Run full test suite**

Run: `pytest -q`
Expected: PASS

**Step 6: Commit**

```bash
git add -A
git commit -m "chore: delete agent skills, update CLAUDE.md for consolidated pipeline"
```

---

## Validation

### Task 13: Run on stec (active deal)

After all modules are implemented:

```bash
skill-pipeline run --deal stec
```

Verify:
- All output artifacts exist in `data/skill/stec/`
- `extract/actors_raw.json` preserved (raw schema)
- `materialize/actors.json` exists (canonical schema)
- `export/deal_events.csv` exists and is non-empty
- Run `skill-pipeline reconcile --deal stec` and check status

### Task 14: Run on saks (second validation)

```bash
skill-pipeline run --deal saks
```

Compare output against existing saks artifacts from prior runs.

---

## Task Dependency Graph

```
Task 1 (paths) ─→ Task 2 (rename) ─→ Task 3 (downstream reads)
                                            │
Task 4 (llm.py) ──────────────────────────→ │
                                            ↓
                                   Task 5 (export.py)
                                   Task 6 (extract.py)
                                   Task 7 (omission_audit.py)
                                   Task 8 (repair.py)
                                   Task 9 (enrich_interpret.py)
                                            │
                                            ↓
                                   Task 10 (run.py)
                                   Task 11 (reconcile.py)
                                            │
                                            ↓
                                   Task 12 (cleanup)
                                            │
                                            ↓
                                   Task 13-14 (validation)
```

Tasks 5-9 are independent of each other (all depend on Tasks 1-4).
Tasks 5-9 can be parallelized across agents.
