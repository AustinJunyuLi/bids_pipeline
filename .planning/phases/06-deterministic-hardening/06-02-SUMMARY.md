---
phase: 06-deterministic-hardening
plan: 02
subsystem: pipeline
tags: [coverage, gates, nda, chronology-blocks, pytest]
requires:
  - phase: 06-deterministic-hardening
    provides: quote-first and canonical artifact stability from 06-01 loader/canonicalize hardening
provides:
  - shared Phase 6 non-sale NDA exclusion in coverage and gates
  - quote-first and canonical regressions for nda_after_drop and nda_signer_no_downstream
  - conservative bidder-target NDA preservation pending Phase 8 nda_subtype work
affects: [coverage, gates, phase-08-nda-subtype]
tech-stack:
  added: []
  patterns:
    - normalized exact-substring NDA qualification markers
    - gate qualification from event summaries plus matched chronology block text
key-files:
  created: []
  modified:
    - skill_pipeline/coverage.py
    - skill_pipeline/gates.py
    - tests/test_skill_coverage.py
    - tests/test_skill_gates.py
key-decisions:
  - "Keep the Phase 6 NDA fix schema-neutral by using exact normalized substring markers instead of altering extract artifacts."
  - "Have gates qualify NDA events from event summaries plus matched chronology block text so quote-first and canonical fixtures share the same exclusion behavior."
patterns-established:
  - "Non-sale NDA tolerance: rollover, teaming, and diligence markers suppress NDA findings while bidder-to-target sale-process confidentiality still qualifies."
  - "Cross-stage alignment: gates reuses the coverage NDA marker helper so coverage and gate findings stay consistent until Phase 8 adds nda_subtype."
requirements-completed: [HARD-04]
duration: 12 min
completed: 2026-03-29
---

# Phase 06 Plan 02: Coverage and Gate NDA Tolerance Summary

**Normalized non-sale NDA markers now suppress rollover, teaming, and diligence false positives in both coverage and gates while preserving real bidder-target NDAs.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-29T21:19:06Z
- **Completed:** 2026-03-29T21:31:19Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Extended coverage NDA cue classification with explicit normalized exclusions for rollover, teaming, and non-sale diligence phrases.
- Added gate-side NDA qualification that reads event summaries plus matched chronology block text before `nda_after_drop` or `nda_signer_no_downstream` state changes.
- Added focused quote-first and canonical regressions that prove excluded NDA patterns are ignored while standard bidder-target confidentiality events still surface findings.

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend coverage cue classification with explicit non-sale NDA exclusions** - `13594ff` (test), `78d9a83` (fix)
2. **Task 2: Apply the same non-sale NDA filter to gates before lifecycle and cycle checks** - `74d6c47` (test), `c6c0354` (fix)

**Plan metadata:** recorded in the docs commit that contains this summary.

## Files Created/Modified
- `skill_pipeline/coverage.py` - adds normalized Phase 6 NDA exclusion markers and applies them alongside existing prior-executed NDA suppression.
- `skill_pipeline/gates.py` - qualifies NDA events from summaries and chronology-block text before cross-event and lifecycle rules consume them.
- `tests/test_skill_coverage.py` - covers rollover, teaming, diligence, and bidder-target negative-control confidentiality cues.
- `tests/test_skill_gates.py` - adds quote-first and canonical regressions for `nda_after_drop` and `nda_signer_no_downstream`.

## Decisions Made
- Reused the coverage-side phrase helper in gates so both stages stay aligned on the exact Phase 6 exclusion vocabulary.
- Kept the fix conservative and text-pattern-based, matching the plan's interim Phase 6 scope instead of introducing schema changes.
- Used chronology block text in gates so generic event summaries do not hide rollover or continuing-equity NDA language.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `tests/test_skill_coverage.py` already contained uncommitted Task 1 regression cases in the working tree. I preserved them and used them as the RED baseline rather than rewriting them.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- HARD-04 is covered in both deterministic stages and Phase 06 can proceed to 06-03 for the DuckDB lock retry work.
- I will leave `.planning/REQUIREMENTS.md` untouched because it is outside the explicit write scope for this execution.

## Known Stubs

None in runtime code. The only placeholder-like strings detected were test fixture text and an existing skipped-data reason in `tests/test_skill_gates.py`.

## Self-Check: PASSED

- Verified `.planning/phases/06-deterministic-hardening/06-02-SUMMARY.md` exists.
- Verified task commits `13594ff`, `78d9a83`, `74d6c47`, and `c6c0354` exist in git history.

---
*Phase: 06-deterministic-hardening*
*Completed: 2026-03-29*
