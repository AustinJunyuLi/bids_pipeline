---
phase: 01-foundation-annotation
plan: 02
subsystem: infra
tags: [dependencies, edgartools, runtime-contract, historical-docs, regression-tests]

requires:
  - phase: none
    provides: existing pyproject.toml and requirements.txt manifests
provides:
  - tightened runtime dependency manifests without provider SDKs
  - edgartools capped below 6.0 in both manifests
  - historical-doc disclaimers on stale provider-wrapper design docs
  - regression tests enforcing runtime-contract and docs boundary
affects: [01-foundation-annotation, runtime-contract, dependency-management]

tech-stack:
  added: []
  patterns: [manifest-guards, historical-doc-disclaimers, contract-boundary-tests]

key-files:
  created:
    - tests/test_runtime_contract_docs.py
  modified:
    - pyproject.toml
    - requirements.txt
    - .planning/codebase/STACK.md
    - docs/design.md
    - docs/plans/2026-03-16-pipeline-design-v3.md
    - docs/plans/2026-03-16-prompt-engineering-spec.md

key-decisions:
  - "Removed anthropic>=0.49 from manifests -- no live import in skill_pipeline or tests"
  - "Capped edgartools below 6.0 to guard against breaking API changes"
  - "Kept openpyxl>=3.1 as plan specified -- live workflow audit not performed"

patterns-established:
  - "Runtime manifests declare only deterministic Python path dependencies"
  - "Historical design docs carry top-of-file disclaimers pointing to live authority"
  - "Regression tests enforce runtime-contract boundaries programmatically"

requirements-completed: [INFRA-06]

duration: 2min
completed: 2026-03-27
---

# Phase 01 Plan 02: Runtime Contract Hardening Summary

**Removed unused anthropic SDK, capped edgartools<6.0, added historical disclaimers to stale design docs, and regression tests for runtime-contract boundary**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-27T16:24:12Z
- **Completed:** 2026-03-27T16:27:02Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments
- Runtime manifests now reflect only the deterministic Python path (no provider SDKs)
- edgartools capped below 6.0 in both pyproject.toml and requirements.txt
- Historical design docs carry explicit disclaimers distinguishing them from live authority
- 8 regression tests enforce manifest and docs boundary rules

## Task Commits

Each task was committed atomically:

1. **Task 1: Tighten live runtime dependency manifests** - `eaae3ca` (fix)
2. **Task 2: Mark stale provider-wrapper design docs as historical** - `351eb54` (docs)
3. **Task 3: Add regression coverage for manifest and docs boundary** - `356a1cf` (test)

## Files Created/Modified
- `pyproject.toml` - Removed anthropic, capped edgartools<6.0
- `requirements.txt` - Removed anthropic, capped edgartools<6.0
- `.planning/codebase/STACK.md` - Removed anthropic entry, updated edgartools constraint
- `docs/design.md` - Added explicit historical-background disclaimer
- `docs/plans/2026-03-16-pipeline-design-v3.md` - Added top-of-file historical warning
- `docs/plans/2026-03-16-prompt-engineering-spec.md` - Added top-of-file historical warning
- `tests/test_runtime_contract_docs.py` - 8 regression tests for runtime-contract boundary

## Decisions Made
- Removed anthropic>=0.49 confirmed by `rg` scan showing zero imports in skill_pipeline/ and tests/
- Kept openpyxl>=3.1 in place per plan instruction -- no live-workflow audit performed
- Historical disclaimers use blockquote format for visibility without altering doc structure

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Runtime manifests are clean and deterministic-only
- Historical docs are clearly labeled as non-authoritative
- Regression tests provide guardrails against re-introduction of provider deps or stale doc claims

## Self-Check: PASSED

- [x] tests/test_runtime_contract_docs.py exists
- [x] 01-02-SUMMARY.md exists
- [x] Commit eaae3ca found
- [x] Commit 351eb54 found
- [x] Commit 356a1cf found

---
*Phase: 01-foundation-annotation*
*Completed: 2026-03-27*
