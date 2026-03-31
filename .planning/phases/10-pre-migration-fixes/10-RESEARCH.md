# Phase 10: Pre-Migration Fixes - Research

**Date:** 2026-03-31
**Status:** Complete

## Findings

### 1. The all-cash bug is a real control-flow error, not a missing rule

- `skill_pipeline/enrich_core.py` currently enters the `executed_events` branch
  first.
- If the last executed event exists but its `terms.consideration_type` is
  `None`, the function hits `continue` and never evaluates the typed-proposal
  fallback.
- `saks` is the concrete repro:
  - proposals `evt_003`, `evt_004`, and `evt_018` are typed `cash`
  - proposals `evt_008`, `evt_009`, `evt_015`, `evt_016`, and `evt_019` are
    untyped
  - `evt_020` is `executed` with null consideration type
  - current `deterministic_enrichment.json` shows `"all_cash_overrides": {}`
- Existing unit tests cover cash executed events, typed-cash fallback, mixed
  guardrails, and the Providence guardrail, but they do not cover the
  executed-without-type short-circuit.

### 2. The fix must stay narrower than general process-level cash inference

- Project research explicitly frames this as a v1 bug fix that should change
  only `all_cash_overrides`.
- The broader "process-level all-cash propagation" concept belongs to the v2
  cash-regime derivation work.
- To preserve the Providence guardrail while fixing Saks, the fallback should
  require more than a single typed-cash proposal before untyped proposals
  inherit `all_cash`.

### 3. Structured coverage can land without rewriting extraction

- The current coverage stage is isolated in `skill_pipeline/coverage.py`.
- Runtime consumers gate on `CoverageSummary`, not on the detail artifact model.
- That makes Phase 10 a good place to introduce `CoverageCheckRecord` as the
  structured detail-record contract while keeping summary gating unchanged.
- Existing cue detection and overlap logic can be reused to populate structured
  statuses and supporting references.

### 4. Re-baselining should start from deterministic enrichment forward

- The all-cash fix changes `deterministic_enrichment.json`, then flows into
  `db-load` and `db-export`.
- No upstream extraction/canonicalization rerun is required for the bug fix.
- Benchmark materials are allowed only after refreshed exports exist.

## Recommended Plan Shape

### Plan 10-01
- Patch `_infer_all_cash_overrides()`
- Add regression coverage for the executed-without-type fallback bug
- Preserve the Providence negative guardrail

### Plan 10-02
- Add `CoverageCheckRecord` to `skill_pipeline/models.py`
- Make `coverage.py` emit structured records with status, reason codes, and
  supporting references
- Update coverage tests while preserving `coverage_summary` gate behavior

### Plan 10-03
- Re-run deterministic downstream stages from coverage/enrich forward as needed
  to materialize the new contracts
- Re-run affected deal exports after the all-cash fix
- Re-measure and document the benchmark baseline post-export

## Risks

- The repo worktree already contains many modified generated artifacts. Any
  regeneration must be intentional and path-aware.
- If the all-cash fix changes fields besides `all_cash_overrides`, stop and
  inspect before continuing.
- Structured coverage records may require test updates wherever the JSON detail
  shape is asserted directly.
