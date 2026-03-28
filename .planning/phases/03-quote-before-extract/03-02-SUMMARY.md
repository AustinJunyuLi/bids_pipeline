---
phase: 03-quote-before-extract
plan: 02
subsystem: infra
tags: [canonicalize, enrich-core, provenance, quote-first, pytest]
requires:
  - phase: 03-quote-before-extract
    provides: quote-first raw extract schema, loader detection, and converted fixtures from 03-01
provides:
  - quote-to-span canonicalization for quote-first extract artifacts
  - orphaned-quote logging plus duplicate and unknown-quote fail-fast handling
  - canonical-only enrich-core span positioning and quote-first test fixture canonicalization
affects: [03-03, 03-04, canonicalize, enrich-core, verify, check]
tech-stack:
  added: []
  patterns: [quote-to-span span reuse by block/text, canonical-only enrich-core inputs, fixture canonicalization before enrichment]
key-files:
  created: []
  modified:
    - skill_pipeline/canonicalize.py
    - skill_pipeline/enrich_core.py
    - tests/test_skill_canonicalize.py
    - tests/test_skill_enrich_core.py
key-decisions:
  - "Quote-first canonicalization reuses a single span for repeated identical quote text in the same block so downstream event dedup semantics stay stable."
  - "enrich-core now fails fast unless extract artifacts are already canonical and span-backed; quote-first fixtures are canonicalized in tests rather than relying on removed raw fallbacks."
patterns-established:
  - "Canonicalize resolves every quote through resolve_text_span and maps quote_ids to canonical evidence_span_ids before downstream normalization."
  - "Enrich-core tests should materialize quote-first raw extracts and run canonicalize before invoking the enrichment stage."
requirements-completed: []
duration: 11min
completed: 2026-03-28
---

# Phase 3 Plan 02: Canonicalize Rewrite Summary

**Quote-first canonicalization now resolves quote text directly to spans, logs orphaned quotes, and hands enrich-core canonical span-backed artifacts only**

## Performance

- **Duration:** 11 min
- **Started:** 2026-03-28T09:37:30Z
- **Completed:** 2026-03-28T09:48:25Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Rewrote `skill_pipeline/canonicalize.py` around top-level quote resolution, removed the old `evidence_refs` path, and preserved idempotence on already-canonical extracts.
- Added quote-specific protections in canonicalize: duplicate `quote_id` rejection, unknown `block_id` rejection, orphaned quote logging, and shared span reuse for identical quote text in the same block.
- Removed enrich-core legacy fallback logic so span positioning and count-assertion anchors are derived only from canonical `evidence_span_ids`, then updated the owned tests to canonicalize quote-first fixtures before enrichment.

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite canonicalize.py for quote-to-span resolution** - `edd6369` (feat)
2. **Task 2: Clean up enrich_core legacy code paths and run all tests** - `69f285f` (test)

**Plan metadata:** included in the docs completion commit for this plan

## Files Created/Modified
- `skill_pipeline/canonicalize.py` - Replaced `evidence_refs` resolution with quote-to-span mapping and orphaned-quote logging.
- `skill_pipeline/enrich_core.py` - Removed dead legacy fallback paths and requires canonical span-backed artifacts explicitly.
- `tests/test_skill_canonicalize.py` - Removed the temporary `xfail` and added quote-first canonicalize regressions for duplicate IDs and orphaned quotes.
- `tests/test_skill_enrich_core.py` - Materializes quote-first fixtures into synthetic filings, runs canonicalize, then exercises enrich-core on canonical inputs.

## Decisions Made
- Preserved the existing dedup behavior by reusing one span per repeated `(block_id, text)` quote instead of generating a fresh span for every `quote_id`.
- Tightened enrich-core to the live pipeline contract: it consumes canonical artifacts only, not raw quote-first artifacts.
- Left `PROMPT-05` open at the requirement level because verify/check and prompt-contract work still remain in Plans 03-03 and 03-04.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reused spans for identical quote text in the same block**
- **Found during:** Task 1 (Rewrite canonicalize.py for quote-to-span resolution)
- **Issue:** The initial quote-to-span rewrite generated distinct span IDs for identical quotes in the same block, which broke existing event dedup clustering because duplicate events no longer shared evidence spans.
- **Fix:** Added span reuse keyed by `(block_id, text)` inside `_resolve_quotes_to_spans` while still rejecting duplicate `quote_id` values.
- **Files modified:** `skill_pipeline/canonicalize.py`
- **Verification:** `python -m pytest tests/test_skill_canonicalize.py -x -v`
- **Committed in:** `edd6369` (part of Task 1 commit)

**2. [Rule 2 - Missing Critical] Fail fast on non-canonical enrich-core inputs**
- **Found during:** Task 2 (Clean up enrich_core legacy code paths and run all tests)
- **Issue:** After removing the legacy fallback branches, `enrich-core` no longer had a correct behavior for raw quote-first artifacts; owned tests were still invoking it before canonicalize.
- **Fix:** `run_enrich_core()` now rejects non-canonical extract artifacts explicitly, and the owned enrich-core tests canonicalize their quote-first fixtures before invoking the stage.
- **Files modified:** `skill_pipeline/enrich_core.py`, `tests/test_skill_enrich_core.py`
- **Verification:** `python -m pytest tests/test_skill_canonicalize.py tests/test_skill_enrich_core.py -x -v`
- **Committed in:** `69f285f` (part of Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical)
**Impact on plan:** Both fixes were required to preserve deterministic downstream behavior and make the quote-first rewrite correct. No extra feature scope was added.

## Issues Encountered
- Concurrent worktree changes were present in `quality_reports/session_logs/2026-03-18_skill-pipeline-design.md`, `.claude/projects/`, `.claude/worktrees/`, `data/skill/stec/prompt/`, and an in-progress `skill_pipeline/check.py` modification from another executor. They were left untouched and excluded from all staging.

## Known Stubs
- Test helper fallback strings such as `"placeholder source text"` remain in `tests/test_skill_canonicalize.py` and `tests/test_skill_enrich_core.py` only to materialize minimal synthetic filings when a fixture omits explicit quote text. No runtime stubs remain in the owned production code.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plan 03-03 can now rewrite `verify.py` and `check.py` against a stable quote-first canonicalization contract with explicit duplicate/orphan protections already in place.
- Plan 03-04 can update prompt instructions and skill docs knowing canonicalize and enrich-core now align on canonical span-backed evidence.
- `PROMPT-05` remains open until the remaining Phase 3 plans land.

## Self-Check: PASSED
- Summary file exists: `.planning/phases/03-quote-before-extract/03-02-SUMMARY.md`
- Task commits present in git history: `edd6369`, `69f285f`

---
*Phase: 03-quote-before-extract*
*Completed: 2026-03-28*
