---
phase: 06-chunked-extraction-architecture
plan: 02
subsystem: infra
tags: [canonicalize, check, actors, extraction, regression-tests]

# Dependency graph
requires:
  - phase: 02-deterministic-stage-interfaces
    provides: Stable raw actor and event artifact contracts consumed by deterministic stages
provides:
  - Canonical actor deduplication with actor ID rewrites and dedup logging
  - Warning-level actor audit checks for duplicate names, missing NDAs, count gaps, and missing advisor links
  - Regression coverage for residual chunk-boundary actor issues in canonicalize and check
affects:
  - 06-03 enrich-deal targeted rereads
  - 06-04 end-to-end validation
  - deterministic stage QA

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Canonical actor dedup runs after event dedup and before NDA gating so downstream checks see stable actor IDs
    - Actor audit findings stay warning-only so structural blockers remain reserved for fail-fast contract violations

key-files:
  created:
    - .planning/phases/06-chunked-extraction-architecture/06-02-SUMMARY.md
  modified:
    - skill_pipeline/canonicalize.py
    - skill_pipeline/check.py
    - tests/test_skill_canonicalize.py
    - tests/test_skill_check.py
    - .planning/STATE.md
    - .planning/ROADMAP.md
    - .planning/REQUIREMENTS.md

key-decisions:
  - Deduplicate actors by normalized canonical name, role, and bidder kind before NDA gating so later stages operate on survivor actor IDs
  - Surface actor audit residuals as warnings instead of blockers because they are important QA signals but not structural contract failures

patterns-established:
  - "Actor dedup merges evidence_span_ids, aliases, and notes while rewriting actor references in events before canonical artifacts are written."
  - "Check-stage actor audits derive roster warnings from the loaded extract mode (legacy or canonical) without changing gate pass/fail semantics."

requirements-completed: [WFLO-03, QUAL-01]

# Metrics
duration: 7 min
completed: 2026-03-25
---

# Phase 6 Plan 02: Add actor dedup and actor audit Summary

**Canonical actor deduplication now rewrites residual chunk-boundary actor IDs before NDA gating, and `check` now audits the resulting roster for non-blocking actor warnings.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-25T15:54:45Z
- **Completed:** 2026-03-25T16:01:50Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- Added `_dedup_actors()` to `canonicalize.py` so duplicate actors merge by normalized canonical name, role, and bidder kind, with survivor evidence and reference rewrites preserved in the canonical output.
- Added `_check_actor_audit()` to `check.py` so duplicate canonical names, bidders without NDA coverage, count assertion gaps, and advisors missing `advised_actor_id` surface as warning findings.
- Added focused regression coverage for both behaviors and kept the touched deterministic stage suites green.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add `_dedup_actors` to canonicalize.py with regression tests** - `b50facb` (`feat`)
2. **Task 2: Add `_check_actor_audit` to check.py with regression tests** - `4daf064` (`feat`)

**Plan metadata:** Recorded in the final docs commit that captures this summary plus planning-state updates.

## Files Created/Modified

- `skill_pipeline/canonicalize.py` - Added actor deduplication, list-remap helpers, canonicalize logging, and the new call site between event dedup and NDA gating.
- `skill_pipeline/check.py` - Added actor audit warnings and wired them into the existing check dispatch.
- `tests/test_skill_canonicalize.py` - Added four actor dedup regression tests plus a small actor fixture helper.
- `tests/test_skill_check.py` - Added five actor audit regression tests and generalized the check fixture for custom actor and event scenarios.
- `.planning/phases/06-chunked-extraction-architecture/06-02-SUMMARY.md` - Execution summary for this plan.
- `.planning/STATE.md` - GSD execution state updated after plan completion.
- `.planning/ROADMAP.md` - Phase 06 plan progress updated after plan completion.
- `.planning/REQUIREMENTS.md` - Requirement tracking updated for this plan's completed requirements.

## Decisions Made

- Chose survivor actors by largest `evidence_span_ids` set, keeping first-occurrence tie behavior inherited from Python's stable `max()` evaluation.
- Kept actor audit checks warning-only so the gate still fails only on structural blockers like missing proposal terms or empty anchor text.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Adjusted the shared check fixture to keep older warning-count tests scoped**
- **Found during:** Task 2 (Add `_check_actor_audit` to check.py with regression tests)
- **Issue:** The new `bidder_no_nda` warning correctly fired against the old default proposal-only fixture, which made an unrelated existing warning-count test fail for the wrong reason.
- **Fix:** Added a default NDA event to the shared check fixture so existing tests still isolate proposal and bidder-kind behavior while the new actor-audit tests cover missing-NDA scenarios explicitly.
- **Files modified:** `tests/test_skill_check.py`
- **Verification:** `pytest -q tests/test_skill_check.py tests/test_skill_pipeline.py`
- **Committed in:** `4daf064`

---

**Total deviations:** 1 auto-fixed (1 blocking issue)
**Impact on plan:** The fixture adjustment preserved the intended scope of the existing check regressions. No scope creep.

## Issues Encountered

- The new actor-audit warning changed the baseline warning count in one legacy check test until the shared fixture included an NDA event for its default bidder actor.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase `06-04` can now validate chunked extraction on real deals with deterministic actor cleanup and actor-audit warnings already in place.
- Phase `06-03` remains independent, but any enrichment work will now consume cleaner canonical actor IDs and more explicit check reports.

## Self-Check: PASSED

- Found summary file at `.planning/phases/06-chunked-extraction-architecture/06-02-SUMMARY.md`.
- Verified task commit `b50facb`.
- Verified task commit `4daf064`.

---
*Phase: 06-chunked-extraction-architecture*
*Completed: 2026-03-25*
