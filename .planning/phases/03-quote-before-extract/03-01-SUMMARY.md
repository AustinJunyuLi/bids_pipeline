---
phase: 03-quote-before-extract
plan: 01
subsystem: infra
tags: [pydantic, quote-first, canonicalize, verify, pytest]
requires:
  - phase: 02-prompt-architecture
    provides: prompt-era raw extract artifacts and the deterministic test harness this plan migrates
provides:
  - QuoteEntry-backed raw extraction schema with top-level quote collections
  - quote_first versus canonical extract loader detection with legacy rejection
  - quote-first raw fixture coverage across canonicalize, verify, check, enrich-core, pipeline, provenance, and compose-prompts tests
affects: [03-02, 03-03, 03-04, canonicalize, verify, compose-prompts]
tech-stack:
  added: []
  patterns: [quote-first raw artifacts, fail-fast legacy format rejection, fixture materialization via top-level quotes arrays]
key-files:
  created: []
  modified:
    - skill_pipeline/models.py
    - skill_pipeline/extract_artifacts.py
    - skill_pipeline/verify.py
    - tests/test_skill_canonicalize.py
    - tests/test_skill_verify.py
    - tests/test_skill_check.py
    - tests/test_skill_enrich_core.py
    - tests/test_skill_pipeline.py
    - tests/test_skill_provenance.py
    - tests/test_skill_compose_prompts.py
key-decisions:
  - "Removed EvidenceRef immediately instead of carrying a deprecated alias, matching the plan's no-dual-path rule."
  - "Treat top-level quotes as the only supported raw pre-canonical contract; loader rejection is explicit rather than heuristic fallback."
  - "Applied a minimal verify.py import compatibility fix so pytest collection survives until the full quote-first verify rewrite in Plan 03-03."
patterns-established:
  - "Raw actor and event fixtures now carry top-level quotes arrays plus per-record quote_ids."
  - "Fixture helpers can synthesize quote collections from per-record quote metadata before writing disk artifacts."
requirements-completed: []
duration: 12min
completed: 2026-03-28
---

# Phase 3 Plan 01: Schema Foundation Summary

**QuoteEntry raw schema, quote-first extract loading, and suite-wide quote-linked raw test fixtures**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-28T01:16:49Z
- **Completed:** 2026-03-28T01:29:05Z
- **Tasks:** 3
- **Files modified:** 10

## Accomplishments
- Added the quote-first raw schema foundation in `skill_pipeline.models` by introducing `QuoteEntry`, replacing raw `evidence_refs` with `quote_ids`, and adding top-level `quotes` arrays to raw actor and event artifacts.
- Rewrote `load_extract_artifacts()` to distinguish `quote_first` from canonical span-backed payloads and reject legacy `evidence_refs` artifacts with a fail-fast error.
- Converted every owned raw-artifact fixture to the new quote-first shape, including the compose-prompts actor-roster fixture that validates against `RawSkillActorsArtifact` during event-packet generation.

## Task Commits

Each task was committed atomically:

1. **Task 1: Define QuoteEntry model and update Raw* models to use quote_ids** - `c57d35b` (feat)
2. **Task 2: Update extract artifact loader for quote_first format detection** - `bcab470` (feat)
3. **Task 3: Convert all test fixtures from evidence_refs to quote-first format** - `a388c0f` (test)

**Plan metadata:** included in the docs completion commit for this plan

## Files Created/Modified
- `skill_pipeline/models.py` - Quote-first raw extraction models and QuoteEntry schema.
- `skill_pipeline/extract_artifacts.py` - Raw/canonical format detection with explicit legacy rejection.
- `skill_pipeline/verify.py` - Minimal import compatibility fix after removing `EvidenceRef`.
- `tests/test_skill_canonicalize.py` - Quote-first canonicalize fixtures plus helper materialization of event quotes.
- `tests/test_skill_verify.py` - Quote-first verify fixtures and raw payload overrides.
- `tests/test_skill_check.py` - Quote-first check fixtures for actors and proposal events.
- `tests/test_skill_enrich_core.py` - Quote-first enrich-core fixtures with helper-generated event quote payloads.
- `tests/test_skill_pipeline.py` - Quote-first deal-agent and pipeline summary fixtures.
- `tests/test_skill_provenance.py` - Quote-first canonicalize provenance fixture.
- `tests/test_skill_compose_prompts.py` - Quote-first raw actor roster fixture for event-packet validation.

## Decisions Made
- Used the plan's quote-first contract literally: raw artifacts now require top-level `quotes` and raw records reference only `quote_ids`.
- Left canonical post-canonicalize models untouched so the downstream rewrite plans can migrate one boundary at a time.
- Kept PROMPT-05 open at the requirement level because this plan only establishes the schema and fixture foundation; canonicalize, verify, and prompt-instruction rewrites still remain.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed the broken `EvidenceRef` import from verify module collection path**
- **Found during:** Task 3 (Convert all test fixtures from evidence_refs to quote-first format)
- **Issue:** `tests/test_skill_verify.py` imports `skill_pipeline.verify`, and that module still imported the deleted `EvidenceRef` symbol. Pytest collection would fail before the converted fixtures could be validated.
- **Fix:** Dropped the `EvidenceRef` import and loosened the private helper annotation so the module still imports while the full quote-first verify rewrite remains deferred to Plan 03-03.
- **Files modified:** `skill_pipeline/verify.py`
- **Verification:** `python -m pytest --co -q` completed successfully after the change.
- **Committed in:** `a388c0f` (part of Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The deviation was necessary to keep the test suite importable after the model contract change. No feature scope was added beyond compatibility for the planned migration.

## Issues Encountered
- The first Task 1 commit attempt hit a stale `.git/index.lock`. The lock had already disappeared when checked, so the task commit succeeded on immediate retry with no repo cleanup needed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plan 03-02 can now rewrite canonicalize against a stable quote-first raw artifact contract and matching fixtures.
- Plan 03-03 can replace the remaining legacy runtime logic in `verify.py`; this plan only preserved importability, not quote-first verification behavior.
- Prompt/instruction work in Plan 03-04 can rely on the new raw schema and converted actor-roster fixtures already being in place.

## Self-Check: PASSED
- Summary file exists on disk.
- Task commits `c57d35b`, `bcab470`, and `a388c0f` are present in git history.

---
*Phase: 03-quote-before-extract*
*Completed: 2026-03-28*
