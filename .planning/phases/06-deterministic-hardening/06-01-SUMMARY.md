---
phase: 06-deterministic-hardening
plan: 01
subsystem: pipeline
tags: [extract-loader, canonicalize, quote-ids, spans, pytest]
requires: []
provides:
  - shared mixed-schema rejection in extract artifact loading
  - deterministic qa_/qe_ quote renumbering before canonical span resolution
  - canonicalize log audit trail for quote_id remaps
affects: [canonicalize, check, verify, coverage, gates, db-load]
tech-stack:
  added: []
  patterns:
    - centralized schema-mode validation in load_extract_artifacts()
    - namespaced quote-id remap before actor/event quote merge
key-files:
  created:
    - tests/test_skill_extract_artifacts.py
  modified:
    - skill_pipeline/extract_artifacts.py
    - skill_pipeline/canonicalize.py
    - tests/test_skill_canonicalize.py
key-decisions:
  - "Keep mixed-schema detection centralized in load_extract_artifacts() so every deterministic consumer fails before stage-specific parsing."
  - "Renumber quote-first actor and event quotes to qa_### / qe_### before span resolution and record the remap in canonicalize_log.json."
patterns-established:
  - "Shared loader guard: actor/event schema mismatches raise MixedSchemaError before any canonical-path sidecar checks."
  - "Quote-first upgrade path: validate same-array duplicates first, then rewrite every quote reference site before resolving spans."
requirements-completed: [HARD-06, HARD-01]
duration: 4 min
completed: 2026-03-29
---

# Phase 06 Plan 01: Loader and Canonicalize Hardening Summary

**Shared extract schema-mode guard plus deterministic qa_/qe_ quote renumbering for canonicalize.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-29T21:07:03Z
- **Completed:** 2026-03-29T21:11:06Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added `MixedSchemaError` to `load_extract_artifacts()` so mixed canonical vs quote-first payloads fail before `spans.json` checks or canonical parsing.
- Renumbered quote-first actor and event quote IDs to collision-free `qa_###` and `qe_###` namespaces before `_resolve_quotes_to_spans()` merges them.
- Extended regression coverage for mixed-schema boundaries, cross-array quote collisions, remap logging, orphaned quote logging, and idempotent canonical reruns.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add a dedicated mixed-schema guard to the shared extract loader** - `ffdf8c1` (test), `9611a71` (fix)
2. **Task 2: Renumber quote-first quote IDs deterministically before canonical merge** - `278fbd9` (test), `e736c16` (fix), `2b66ee4` (test)

**Plan metadata:** recorded in the docs commit that contains this summary.

## Files Created/Modified
- `skill_pipeline/extract_artifacts.py` - adds `MixedSchemaError` and rejects actor/event schema mismatches before canonical dispatch.
- `skill_pipeline/canonicalize.py` - validates same-array duplicates, rewrites quote-first IDs to `qa_###` / `qe_###`, and records `quote_id_renumber_log`.
- `tests/test_skill_extract_artifacts.py` - adds focused loader regressions for mixed-schema failures and canonical spans-sidecar boundaries.
- `tests/test_skill_canonicalize.py` - adds cross-array collision/remap assertions and aligns existing canonicalize regressions with the new renumbered contract.

## Decisions Made
- Mixed-schema protection stays in the shared loader instead of duplicating checks in downstream stages.
- Canonicalize renumbers every quote-first actor/event quote deterministically rather than trying to preserve incoming numeric suffixes.
- `canonicalize_log.json` remains the single audit surface; the remap is appended there instead of creating a new artifact.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Regression] Updated canonicalize regressions after full-slice verification**
- **Found during:** post-task verification
- **Issue:** Existing assertions expected pre-renumber orphaned quote IDs and relied on an empty-actors edge case for the spans-sidecar boundary.
- **Fix:** Aligned the orphaned-quote assertion with the new remapped IDs and tightened the spans-sidecar test to use a fully canonical actor payload.
- **Files modified:** tests/test_skill_canonicalize.py
- **Verification:** `pytest -q tests/test_skill_extract_artifacts.py tests/test_skill_canonicalize.py`
- **Committed in:** 2b66ee4

---

**Total deviations:** 1 auto-fixed (1 rule-1 regression)
**Impact on plan:** Verification-only follow-up. No scope creep or runtime contract expansion.

## Issues Encountered
- Full-slice verification exposed two old canonicalize expectations that no longer matched the renumbered quote contract; both were resolved in the regression suite.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- HARD-06 and HARD-01 are covered with focused regressions and ready for the remaining deterministic-hardening plans.
- I intentionally did not update `.planning/STATE.md`, `.planning/ROADMAP.md`, or `.planning/REQUIREMENTS.md` because those files already had unrelated local changes and the user asked that they be preserved.

## Known Stubs

None in runtime code. The only placeholder strings detected were fixture text inside `tests/test_skill_canonicalize.py`.

## Self-Check: PASSED

- Verified `.planning/phases/06-deterministic-hardening/06-01-SUMMARY.md` exists.
- Verified task commits `ffdf8c1`, `9611a71`, `278fbd9`, `e736c16`, and `2b66ee4` exist in git history.

---
*Phase: 06-deterministic-hardening*
*Completed: 2026-03-29*
