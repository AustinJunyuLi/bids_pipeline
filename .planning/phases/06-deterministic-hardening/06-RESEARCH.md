# Phase 6: Deterministic Hardening - Research

**Researched:** 2026-03-29
**Domain:** extract loader invariants, canonicalize quote renumbering, NDA false-positive suppression, DuckDB lock retry
**Confidence:** HIGH

## Summary

Phase 6 is a narrow deterministic-runtime hardening pass over five live modules:
`extract_artifacts.py`, `canonicalize.py`, `coverage.py`, `gates.py`, and
`db_schema.py`/`db_export.py`. The codebase already contains the correct stage
boundaries and most of the fixture infrastructure needed for this phase. The
work is not architectural expansion. It is targeted correctness hardening at
existing choke points.

The main planning conclusion is to keep the fixes local to the current stage
owners:

1. `load_extract_artifacts()` should become the single shared guard for mixed
   canonical vs quote-first artifacts and raise a dedicated `MixedSchemaError`
   before any stage-specific parsing or writes.
2. `run_canonicalize()` should renumber quote-first quote IDs deterministically
   before actor/event quote merge, preserving same-array duplicate failures while
   allowing cross-array collisions.
3. Coverage and gates should both suppress rollover-side and other non-sale
   process confidentiality agreements using an interim text-pattern classifier
   grounded in event/block text.
4. `open_pipeline_db()` should own bounded retry for DuckDB file-lock
   contention, because both `db-load` and `db-export` already route through that
   helper.

The repo already has strong regression scaffolding in
`tests/test_skill_canonicalize.py`, `tests/test_skill_coverage.py`,
`tests/test_skill_gates.py`, and `tests/test_skill_db_load.py`. Adding Phase 6
coverage to those files is lower-risk than introducing a new testing style.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Mixed-schema detection lives in `skill_pipeline/extract_artifacts.py`
  and protects all downstream deterministic consumers.
- **D-02:** The loader must check the actor/event schema mismatch before the
  current "if either artifact is canonical" routing path.
- **D-03:** Canonicalize deterministically renumbers quote IDs before merge
  using namespaced IDs (`qa_###` for actor-side quotes, `qe_###` for event-side
  quotes). Do not depend on parsing existing numeric suffixes.
- **D-04:** Same-array duplicate quote IDs still fail-fast.
- **D-05:** Quote ID renumber mappings belong in the existing
  `canonicalize_log.json` artifact. No new artifact files.
- **D-06:** All quote ID references must be rewritten consistently, including
  actor quote references, count assertions, and event quote references.
- **D-07:** Phase 6 uses an interim text-pattern exclusion for rollover,
  teaming, and diligence confidentiality agreements. Phase 8 owns the precise
  schema-level `nda_subtype` solution.
- **D-08:** Both coverage and gates must get the Phase 6 NDA tolerance fix.
- **D-09:** DuckDB retry logic lives in `open_pipeline_db()` with three bounded
  attempts and exponential backoff. Retry only true lock-contention failures.

### Claude's Discretion
- Exact mixed-schema exception class placement and message text
- Exact rollover/teaming/diligence exclusion phrases
- Exact backoff intervals for DuckDB retry
- Internal helper structure for renumbering and NDA qualification
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HARD-06 | Shared loader rejects mixed canonical/quote-first artifacts with dedicated error | Existing loader already computes `actors_canonical` and `events_canonical`; add mismatch guard before branch |
| HARD-01 | Canonicalize handles cross-array quote_id collisions by deterministic renumbering and reference rewrite | Current failure is concentrated in `_resolve_quotes_to_spans()` where actor+event quotes are merged into one list |
| HARD-04 | Coverage and gates tolerate rollover-side and non-sale-process confidentiality agreements | Coverage already has phrase-based exclusions; gates needs the same concept before treating NDA events as lifecycle/cycle signals |
| HARD-05 | db-export retries transient DuckDB lock errors after db-load with bounded exponential backoff | Live `db-load`, `db-export`, and `deal_agent` all already route through `open_pipeline_db()` |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- `skill_pipeline/` and `tests/` are the implementation authority.
- Favor fail-fast behavior over silent fallback or best-effort recovery.
- Keep artifact contracts in existing files and paths. Do not create alternate
  runtime outputs for this phase.
- Python runtime stays deterministic and provider-agnostic.
- Add focused regression tests instead of broad refactors.
- Preserve idempotence for already-canonical artifacts.

## Relevant Existing Code

### `skill_pipeline/extract_artifacts.py`
- `load_extract_artifacts()` already reads both raw JSON payloads and derives
  `actors_canonical` / `events_canonical` from `evidence_span_ids`.
- Current bug: `if actors_canonical or events_canonical:` treats any partial
  canonicalization as fully canonical, then validates models as if both sides
  were canonical.
- This is the correct single choke point for HARD-06 because `check`, `verify`,
  `coverage`, `gates`, `canonicalize`, and `db-load` all call it.

### `skill_pipeline/canonicalize.py`
- `run_canonicalize()` currently concatenates actor and event quote arrays into
  `all_quotes` and passes them to `_resolve_quotes_to_spans()`.
- `_resolve_quotes_to_spans()` currently enforces quote ID uniqueness across the
  combined list, which means valid cross-array collisions fail before span
  resolution.
- Canonicalize already writes a structured `canonicalize_log.json` with keys
  `dedup_log`, `nda_gate_log`, `recovery_log`, and `orphaned_quotes`. Extending
  that log is the right audit surface for renumber mappings.

### `skill_pipeline/coverage.py`
- `_classify_cue_family()` already contains phrase-based exclusions for
  contextual references to prior NDAs and one target-diligence pattern.
- HARD-04 should extend this pattern rather than inventing a second
  classification system.

### `skill_pipeline/gates.py`
- `_gate_cross_event_logic()` currently treats every `nda` event as a cycle
  signal for `nda_after_drop`.
- `_gate_actor_lifecycle()` currently treats every `nda` event as evidence that
  a bidder entered the sale process.
- Gates has access to event summaries and to evidence block text through
  `_event_block_ids()` plus the loaded chronology blocks. That is enough for the
  interim Phase 6 text-pattern fix.

### `skill_pipeline/db_schema.py` and `skill_pipeline/db_export.py`
- `open_pipeline_db()` is the only database entry helper.
- `run_db_export()` opens the shared database in `read_only=True` mode.
- Local reproduction with a separate process holding a write transaction shows
  DuckDB raises `duckdb.IOException` with message prefix
  `IO Error: Could not set lock on file ... Conflicting lock is held ...`.
- In the same process, opening the same DB with a different configuration while
  another connection is still open raises `duckdb.ConnectionException` instead.
  That is not the transient file-lock case targeted by HARD-05 and should not be
  retried.

## Requirement Guidance

### HARD-06: Mixed-Schema Guard

**Recommended implementation**
- Add `class MixedSchemaError(ValueError): ...` in
  `skill_pipeline/extract_artifacts.py`.
- In `load_extract_artifacts()`:
  - compute `actors_canonical` and `events_canonical` as today
  - if `actors_canonical != events_canonical`, raise `MixedSchemaError`
    immediately
  - only after the mismatch check continue into canonical or quote-first parsing
- Keep the current missing-`spans.json` check for the fully canonical path.

**Test shape**
- Add a fixture that writes canonical actors + quote-first events and asserts
  `load_extract_artifacts()` raises `MixedSchemaError`.
- Add the inverse case: quote-first actors + canonical events.
- Add at least one consumer-level test (for example canonicalize or db-load)
  proving the dedicated error surfaces before downstream model validation.

**Why this shape**
- It is the smallest change with the broadest blast-radius protection.
- It preserves the repo’s current loader-dispatch contract and avoids duplicating
  schema checks inside each stage.

### HARD-01: Quote ID Renumbering

**Recommended implementation**
- Split quote validation into three steps:
  1. Validate actor quote array has no internal duplicate IDs.
  2. Validate event quote array has no internal duplicate IDs.
  3. Deterministically rewrite quote IDs before merging:
     - actor quotes -> `qa_001`, `qa_002`, ...
     - event quotes -> `qe_001`, `qe_002`, ...
- Rewrite all quote references using the mapping:
  - `actors[].quote_ids`
  - `count_assertions[].quote_ids`
  - `events[].quote_ids`
- Only then concatenate the renumbered quote arrays and resolve spans.
- Record the mapping in `canonicalize_log.json`, for example:
  - `quote_id_renumber_log.actor_quotes`
  - `quote_id_renumber_log.event_quotes`

**Important edge behavior**
- Same-array duplicates must still fail before renumbering. Otherwise Phase 6
  would silently bless corrupt artifacts.
- Idempotence requirement applies to rerunning canonicalize on already-canonical
  artifacts. That path should remain unchanged.
- Do not try to preserve original numeric suffixes. The schema only guarantees
  quote IDs are strings.

**Test shape**
- Preserve the existing same-array duplicate test.
- Add a cross-array collision test where actors and events both use `Q001` and
  canonicalize succeeds.
- Assert output references point to the renumbered quote IDs and the final
  canonical artifacts have consistent `evidence_span_ids`.
- Assert the renumber mapping is written to `canonicalize_log.json`.

### HARD-04: Rollover / Non-Sale NDA Tolerance

**Recommended implementation**
- Create a small shared predicate within the Phase 6 scope, such as
  `_looks_like_non_sale_process_nda(text: str) -> bool`, and use the same phrase
  families in coverage and gates.
- Feed the predicate normalized text from:
  - `EvidenceItem.raw_text` in coverage
  - event summary plus matched chronology block text in gates
- Suggested exclusion families, based on the phase context and current code:
  - rollover / management equity participation
  - bidder-bidder teaming / joint bid / consortium exploration
  - target-on-target diligence or strategic diligence unrelated to joining the
    sale process

**Precision rule**
- The exclusion logic must remain asymmetric:
  - false positives to suppress: rollover CA, teaming CA, diligence CA
  - false positives to avoid creating: legitimate bidder NDA with the target for
    sale-process access
- Because Phase 8 owns `nda_subtype`, Phase 6 should stay conservative and
  pattern-based rather than widening the meaning of all confidentiality
  references.

**Where to apply it**
- In coverage: suppress `cue_family="nda"` classification for excluded text.
- In gates:
  - exclude non-sale-process NDA events from `nda_after_drop`
  - exclude them from `nda_signer_no_downstream`
- Do not change unrelated gate rules or event-type taxonomies.

**Test shape**
- Coverage:
  - one positive exclusion test for rollover/teaming/diligence language
  - one negative control showing a true bidder NDA still yields `cue_family=nda`
- Gates:
  - one test where a rollover-style NDA after drop does not trigger
    `nda_after_drop`
  - one test where a rollover-only signer does not trigger
    `nda_signer_no_downstream`
  - one negative control where a normal bidder NDA still triggers the existing
    warning/blocker behavior

### HARD-05: DuckDB Lock Retry

**Observed runtime behavior**
- Separate-process contention against the same DuckDB file raises
  `duckdb.IOException` with the lock-specific message
  `Could not set lock on file`.
- Same-process configuration mismatch raises `duckdb.ConnectionException` and is
  not the transient lock case.

**Recommended implementation**
- Add retry to `open_pipeline_db()` itself so all callers benefit.
- Keep retry policy small and explicit:
  - attempts: 3
  - backoff: exponential, for example `0.25s`, `0.5s`, `1.0s`
- Retry only when both are true:
  - exception is `duckdb.IOException` (or future-compatible subclass check)
  - message contains `Could not set lock on file`
- Re-raise immediately on any other exception.
- If retries exhaust, raise the last lock exception with clear context; do not
  swallow it into a generic `RuntimeError`.

**Test shape**
- Use a subprocess or multiprocessing worker that opens the DB, begins a write
  transaction, and holds the lock briefly.
- Assert `open_pipeline_db(..., read_only=True)` retries and eventually succeeds
  once the lock is released.
- Assert a persistent lock eventually fails after the bounded retry budget.
- Assert non-lock exceptions are not retried by monkeypatching
  `duckdb.connect` to raise a different error and checking the call count.

## Recommended Plan Shape

The cleanest execution split is three serial plans:

1. **Plan 01: Loader + canonicalize hardening**
   - HARD-06 and HARD-01
   - Files: `skill_pipeline/extract_artifacts.py`,
     `skill_pipeline/canonicalize.py`,
     `tests/test_skill_canonicalize.py`
   - Optional new test file only if the planner wants loader tests isolated

2. **Plan 02: NDA tolerance across coverage and gates**
   - HARD-04
   - Files: `skill_pipeline/coverage.py`, `skill_pipeline/gates.py`,
     `tests/test_skill_coverage.py`, `tests/test_skill_gates.py`

3. **Plan 03: DuckDB lock retry**
   - HARD-05
   - Files: `skill_pipeline/db_schema.py`, possibly `skill_pipeline/db_export.py`
     only if tests require helper exposure, and `tests/test_skill_db_load.py`

This matches the roadmap order while keeping write ownership disjoint enough for
execution.

## Validation Architecture

### Test Infrastructure
- Framework: `pytest`
- Config: `pytest.ini`
- Existing relevant suites:
  - `tests/test_skill_canonicalize.py`
  - `tests/test_skill_coverage.py`
  - `tests/test_skill_gates.py`
  - `tests/test_skill_db_load.py`
  - `tests/test_skill_db_export.py`

### Fast Feedback
- **Quick command:** `pytest -q tests/test_skill_canonicalize.py tests/test_skill_coverage.py tests/test_skill_gates.py tests/test_skill_db_load.py tests/test_skill_db_export.py`
- **Targeted per-task commands:**
  - Loader/canonicalize: `pytest -q tests/test_skill_canonicalize.py`
  - Coverage/gates: `pytest -q tests/test_skill_coverage.py tests/test_skill_gates.py`
  - DuckDB retry: `pytest -q tests/test_skill_db_load.py tests/test_skill_db_export.py`
- **Full suite:** `pytest -q`

### Validation Expectations
- Every Phase 6 task should land with regression tests in the same change.
- Mixed-schema and quote-renumber tests should verify failure mode and boundary
  behavior, not only happy-path success.
- NDA tolerance tests must include both exclusion and negative-control cases.
- DuckDB retry tests should be deterministic and avoid long sleeps by using
  short backoff intervals or monkeypatching sleep in tests.

### Wave 0 Need
- None. The repo already has pytest, helpers, and fixture-writing patterns for
  every affected subsystem.

## Risks To Preserve In Planning

- Over-broad NDA suppression will hide legitimate sale-process NDAs and weaken
  downstream signals. Preserve negative controls in the plan text.
- If quote renumbering happens after reference collection or only rewrites one
  side, canonicalize will silently produce missing span coverage.
- Retrying the wrong DuckDB exceptions will mask real connection/configuration
  bugs.
- Adding mixed-schema checks outside the shared loader would leave some stages
  unprotected and break the phase goal.

## Planner Notes

- Prefer concrete file ownership over abstract “runtime hardening.”
- Every task should include exact test commands in `<acceptance_criteria>`.
- Every plan that touches tests should list the specific fixture helpers it
  reuses from existing files rather than instructing the executor to invent new
  scaffolding.

---
*Phase: 06-deterministic-hardening*
*Research completed: 2026-03-29*
