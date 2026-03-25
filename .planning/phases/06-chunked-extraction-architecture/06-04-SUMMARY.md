---
phase: 06-chunked-extraction-architecture
plan: 04
subsystem: validation
tags: [validation, extraction, chunking, human-verification, deterministic-stages]

# Dependency graph
requires:
  - plan: 06-01
    provides: Canonical chunked extract-deal skill contract and synced mirrors
  - plan: 06-02
    provides: Deterministic actor deduplication and actor-audit warnings
  - plan: 06-03
    provides: Event-targeted enrich-deal reread contract and synced mirrors
provides:
  - Human-approved validation record for chunked extraction on `petsmart-inc`
  - Human-approved validation record for a fresh post-change `stec` rerun through `coverage`
  - Phase closeout evidence tying code changes to real-deal validation outcomes
affects:
  - Phase 06 verification and closeout
  - Future chunked extraction regressions and deal validation expectations

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Chunk debug artifacts under `data/skill/<slug>/extract/chunks/` are the primary runtime proof that a specific extraction run used the chunked workflow
    - Deterministic stage passes may require filing-grounded repair loops before final validation artifacts stabilize

key-files:
  created:
    - .planning/phases/06-chunked-extraction-architecture/06-04-SUMMARY.md
  modified: []

key-decisions:
  - Record `petsmart-inc` validation from current local artifacts and human review
  - Record `stec` validation from the user-approved fresh rerun report, with an explicit caveat that matching chunk and coverage artifacts are not present in this worktree snapshot
  - Treat `verify` and `coverage` repair loops on `stec` as acceptable because the fixes were filing-grounded and the final deterministic chain passed

patterns-established:
  - "Phase validation for chunked extraction requires direct chunk-path evidence, not just final `actors_raw.json` and `events_raw.json` outputs."
  - "Human verification summaries may preserve externally reported rerun results when the user explicitly approves phase closeout on that basis."

requirements-completed: [WFLO-03, QUAL-01]

# Metrics
duration: human verification session
completed: 2026-03-25
---

# Phase 6 Plan 04: End-to-end validation on stec and petsmart Summary

**Phase 06 validation is approved: `petsmart-inc` is locally confirmed through chunked extraction and deterministic follow-on stages, and `stec` is approved from a reported fresh post-change rerun that demonstrated chunked extraction and a final passing deterministic chain through `coverage`.**

## Performance

- **Duration:** Human verification session plus follow-up review
- **Completed:** 2026-03-25
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Recorded a locally grounded `petsmart-inc` validation with chunked extraction artifacts, captured NDA signer count assertions, unnamed-party recovery in `canonicalize`, and a passing `check` run with no blockers.
- Recorded a user-approved `stec` validation from a reported fresh rerun that produced 7 chunk artifacts with overlap metadata and roster carry-forward, then reached passing `canonicalize`, `check`, `verify`, and `coverage` artifacts after filing-grounded repairs.
- Confirmed the full repository test suite passed for the phase (`pytest -q` -> `89 passed`) before accepting the human verification checkpoint.

## Validation Evidence

### petsmart-inc

- Chunked path confirmed directly from local artifacts under `data/skill/petsmart-inc/extract/chunks/` with 3 chunks.
- `actors_raw.json` and `events_raw.json` were present with the expected top-level shape.
- `count_assertions` captured the silent NDA signer signal with `subject: nda_signed_financial_buyers` and `count: 15`.
- `canonicalize` triggered unnamed-party recovery, synthesizing placeholder NDA actors and events.
- `check` passed with no blockers; the only reported warning was duplicate canonical names across synthesized placeholder actors.

### stec

- Human approval was granted based on a reported fresh post-change rerun rather than matching local rerun artifacts in this worktree snapshot.
- The reported rerun used the chunked extraction path directly, preserving `data/skill/stec/extract/chunks/` with 7 chunk files, overlap metadata, and roster carry-forward.
- The reported rerun regenerated `actors_raw.json` and `events_raw.json`, then reached:
  - `canonicalize`: pass
  - `check`: pass with warnings only
  - `verify`: pass after one filing-grounded exact-anchor repair
  - `coverage`: pass after adding five filing-grounded proposal-support spans
- Final reported blocker-level failures at the end of the rerun: 0.

## Deterministic Stage Notes

- `petsmart-inc` satisfied the intended Phase 06 quality signal directly: chunked extraction, preserved output contract, count assertions for silent NDA signers, unnamed-party recovery, and a passing deterministic follow-up stage.
- `stec` satisfied the intended stress-test signal for chunked extraction and deterministic compatibility, but not as a clean first-pass run. The final approval depends on the reported repaired rerun, not on a pristine first-pass chain.

## Files Created/Modified

- `.planning/phases/06-chunked-extraction-architecture/06-04-SUMMARY.md` - Human-approved validation summary for the Phase 06 deal-level checkpoint.

## Decisions Made

- Accepted the `stec` checkpoint for phase closeout because the reported rerun preserved direct chunk evidence and finished with passing deterministic artifacts after filing-grounded repairs.
- Kept enrich/export outside the approval surface because `06-04` only requires validation through `coverage`.

## Deviations from Plan

### User-approved deviation

**1. Closeout uses a reported `stec` rerun instead of matching local rerun artifacts**
- **Found during:** Task 2 (Human verification of chunked extraction on stec and petsmart)
- **Issue:** The current worktree does not contain the reported `stec` chunk artifacts or `coverage/` outputs that were used during the fresh rerun review.
- **Resolution:** The user explicitly approved phase closeout using the reported rerun results anyway, and this summary records that caveat instead of presenting the local worktree as if it contained those artifacts.
- **Impact:** Phase validation remains honest about the evidence source. Future readers should not infer that the current `data/skill/stec/` tree alone proves the chunked rerun.

**2. `stec` validation required filing-grounded repair loops before the deterministic chain fully passed**
- **Found during:** Task 2 (Human verification of chunked extraction on stec and petsmart)
- **Issue:** The fresh `stec` rerun reportedly failed `verify` once on an exact-anchor mismatch and failed `coverage` once on proposal-support gaps.
- **Resolution:** The reported rerun applied filing-grounded fixes, then re-ran the deterministic stages to a clean final pass.
- **Impact:** The plan validates final correctness and repairability, but it does not establish a no-touch first-pass success for `stec`.

---

**Total deviations:** 2 user-approved deviations
**Impact on plan:** Both deviations are fully documented. Phase closeout relies on approved reported runtime evidence for `stec`, while `petsmart-inc` remains backed by local artifacts in this worktree.

## Issues Encountered

- The current worktree snapshot does not contain the reported fresh `stec` chunk rerun outputs, so closeout required an explicit user decision to rely on the reported results.

## User Setup Required

None - the human verification checkpoint is complete and approved.

## Next Phase Readiness

- Phase-level verification can proceed using the committed code changes, the passing test suite, and this validation record.
- Any future `stec` debugging should start by deciding whether to preserve fresh rerun chunk artifacts in the worktree for easier auditability.

## Self-Check: PASSED

- Created `.planning/phases/06-chunked-extraction-architecture/06-04-SUMMARY.md`.
- Recorded the approval caveat for the reported `stec` rerun instead of overstating what the current worktree proves.

---

*Phase: 06-chunked-extraction-architecture*
*Completed: 2026-03-25*
