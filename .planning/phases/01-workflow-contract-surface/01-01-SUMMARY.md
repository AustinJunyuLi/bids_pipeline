---
phase: 01-workflow-contract-surface
plan: 01
subsystem: docs
tags: [workflow-contract, stage-inventory, deterministic-vs-llm, regression-tests]

# Dependency graph
requires: []
provides:
  - "Single canonical workflow contract doc at docs/workflow-contract.md"
  - "Stage classification table (deterministic, LLM, hybrid, formatting-only)"
  - "deal-agent disambiguation (CLI summary vs skill orchestrator)"
  - "Regression test suite for contract surface drift"
affects: [01-workflow-contract-surface, docs, testing]

# Tech tracking
tech-stack:
  added: []
  patterns: [document-level regression assertions over committed contract docs]

key-files:
  created:
    - docs/workflow-contract.md
    - tests/test_workflow_contract_surface.py
  modified:
    - docs/design.md

key-decisions:
  - "Workflow contract doc is the single detailed inventory; design.md stays a concise index that points to it"
  - "Stage count: 7 deterministic, 3 LLM skill, 1 hybrid repair, 1 optional post-export diagnostic"

patterns-established:
  - "Contract surface regression: document-level pytest assertions that fail if stage order, classification, or boundary language drifts"

requirements-completed: [WFLO-01]

# Metrics
duration: 2min
completed: 2026-03-25
---

# Phase 01 Plan 01: Workflow Contract Surface Summary

**Single canonical workflow contract documenting all 11 stages from raw-fetch through /export-csv with deterministic/LLM classification, deal-agent disambiguation, and 9 regression assertions**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-25T23:13:28Z
- **Completed:** 2026-03-25T23:16:18Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Created `docs/workflow-contract.md` with the full stage inventory, stage table, artifact roots, gate boundaries, and benchmark boundary
- Reduced `docs/design.md` to a concise index that explicitly points to the contract doc for detailed stage classification
- Added `tests/test_workflow_contract_surface.py` with 9 assertions covering stage order, deterministic/LLM heading, deal-agent disambiguation, verify-extraction placement, reconcile-alex post-export boundary, and design-index cross-reference

## Task Commits

Each task was committed atomically:

1. **Task 1: Author the canonical workflow contract document** - `3235343` (feat)
2. **Task 2: Reduce docs/design.md to an accurate current-runtime index** - `7ec1557` (feat)
3. **Task 3: Add regression coverage for the workflow contract surface** - `2fb3878` (test)

## Files Created/Modified

- `docs/workflow-contract.md` - Single canonical inventory of all live pipeline stages with classification, artifacts, and gates
- `docs/design.md` - Updated to point to workflow-contract.md as the detailed source
- `tests/test_workflow_contract_surface.py` - 9 regression assertions protecting the contract surface from drift

## Decisions Made

- Workflow contract doc is the single detailed inventory; design.md stays a concise index that points to it
- Stage count breakdown: 7 deterministic, 3 LLM skill, 1 hybrid repair, 1 optional post-export diagnostic
- `/export-csv` classified as LLM skill (formatting only) rather than deterministic because it uses an LLM for CSV formatting

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None - all contract content is complete and wired to regression tests.

## Next Phase Readiness

- The workflow contract surface is committed and regression-tested
- Subsequent plans in Phase 01 can reference `docs/workflow-contract.md` for stage inventory
- The design index already points to the contract doc

## Self-Check: PASSED

- All 3 created/modified files exist on disk
- All 3 task commits verified in git log

---
*Phase: 01-workflow-contract-surface*
*Completed: 2026-03-25*
