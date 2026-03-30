---
phase: 08-extraction-guidance-enrichment-extensions
plan: 02
subsystem: enrich-core
tags: [enrich-core, dropout, all-cash, regression-tests]
requires:
  - phase: 07-bid-type-rule-priority
    provides: stable proposal-classification baseline that must remain untouched
provides:
  - deterministic `DropTarget` classification from round-exclusion context
  - cycle-local deterministic `all_cash_overrides`
  - regression coverage for positive and fail-closed enrichment cases
affects: [enrich-core, db-load, db-export, phase-08 verification]
tech-stack:
  added: []
  patterns:
    - additive enrich-core helpers without mutating `_classify_proposal()`
    - cycle-local inference with fail-closed guardrails
key-files:
  created:
    - .planning/phases/08-extraction-guidance-enrichment-extensions/08-02-SUMMARY.md
  modified:
    - skill_pipeline/enrich_core.py
    - tests/test_skill_enrich_core.py
key-decisions:
  - "Bidder-withdrawal language is checked before any target-exclusion inference so mixed-signal drops do not become `DropTarget`."
  - "all_cash inference propagates only from explicit executed-cash context or no-executed unanimous typed-cash proposal context."
  - "If an executed event exists with null or non-cash consideration, inference fails closed."
patterns-established:
  - "Deterministic enrichment emits sparse additive overlays (`dropout_classifications`, `all_cash_overrides`) instead of mutating canonical extract data."
requirements-completed: [ENRICH-02]
duration: session
completed: 2026-03-30
---

# Phase 08 Plan 02: Deterministic Enrichment Summary

**Added deterministic dropout and all-cash enrichment helpers to `enrich_core.py` and proved the new behavior with focused regression coverage while preserving existing bid-type logic.**

## Performance

- **Completed:** 2026-03-30
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Added `_classify_dropouts()` with bidder-withdrawal-first directionality, cycle-aware active-bidder checks, and sparse `DropTarget` emission grounded in round invitation deltas.
- Added `_infer_all_cash_overrides()` to infer `all_cash` only when the same-cycle evidence is unambiguous, including the Providence & Worcester fail-closed guardrail.
- Extended `run_enrich_core()` to write both `dropout_classifications` and `all_cash_overrides` into `deterministic_enrichment.json`.
- Added 12 new regressions to `tests/test_skill_enrich_core.py` covering positive dropout classification, mixed-signal exclusions, no-round-context cases, sparse outputs, executed-cash propagation, unanimous typed-cash propagation, mixed-consideration blocking, restart boundaries, and null-executed guardrails.
- Kept `_classify_proposal()` unchanged so the Phase 7 bid-type priority fix remains intact.

## Verification

- `.\.venv\Scripts\python.exe -m pytest tests/test_skill_enrich_core.py -q`

Result: `33 passed`.

## Issues Encountered

- The first red test run failed at import time because the repo virtualenv did not include `duckdb`. Installing the package into `.venv` resolved the environment issue and exposed the expected logic failures afterward.

## Self-Check: PASSED

- Verified the new deterministic artifact keys are written by `run_enrich_core()`.
- Verified all new dropout and `all_cash` tests pass.
- Verified no existing enrich-core tests regressed.

---
*Phase: 08-extraction-guidance-enrichment-extensions*
*Completed: 2026-03-30*
