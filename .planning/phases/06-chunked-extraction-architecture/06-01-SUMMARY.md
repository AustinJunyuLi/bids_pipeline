---
phase: 06-chunked-extraction-architecture
plan: 01
subsystem: infra
tags: [skills, extraction, chunking, mirrors, docs]

# Dependency graph
requires:
  - phase: 02-deterministic-stage-interfaces
    provides: Stable deterministic artifact contracts for skill outputs
provides:
  - Canonical extract-deal skill contract for sequential chunk extraction with consolidation
  - Synced Codex and Cursor skill mirrors for the rewritten extraction contract
affects:
  - 06-02 actor dedup and audit follow-up
  - 06-03 enrich-deal targeted rereads
  - 06-04 end-to-end validation

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Canonical skill edits flow from `.claude/skills/` into derived mirrors via `python scripts/sync_skill_mirrors.py`
    - Chunk extraction docs can add transient debug artifacts without changing deterministic stage inputs

key-files:
  created:
    - .planning/phases/06-chunked-extraction-architecture/06-01-SUMMARY.md
  modified:
    - .claude/skills/extract-deal/SKILL.md
    - .codex/skills/extract-deal/SKILL.md
    - .cursor/skills/extract-deal/SKILL.md
    - .planning/STATE.md
    - .planning/ROADMAP.md
    - .planning/REQUIREMENTS.md

key-decisions:
  - Document chunking as the only extract-deal path and keep consolidation responsible for global event IDs and temporal flags
  - Correct the extraction skill reads contract to match the repo's seed-only single-document source artifacts

patterns-established:
  - "Canonical skill edits flow from `.claude/skills/` into derived mirrors via `python scripts/sync_skill_mirrors.py`."
  - "Chunk extraction documentation may write transient debug artifacts under `data/skill/<slug>/extract/chunks/` without changing `actors_raw.json` or `events_raw.json`."

requirements-completed: [WFLO-03]

# Metrics
duration: 1 min
completed: 2026-03-25
---

# Phase 6 Plan 01: Rewrite extract-deal SKILL.md for all-chunked sequential extraction Summary

**Sequential chunk extraction with roster carry-forward and consolidation now defines the canonical `extract-deal` contract, with both mirrored skill trees synced to match.**

## Performance

- **Duration:** 1 min
- **Started:** 2026-03-25T15:51:24Z
- **Completed:** 2026-03-25T15:52:42Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Replaced the old forward-scan and follow-up reread instructions with chunk construction, sequential chunk extraction, and consolidation guidance in the canonical skill.
- Kept the downstream extraction contract fixed at `actors_raw.json` plus `events_raw.json` while documenting transient chunk debug artifacts under `data/skill/<slug>/extract/chunks/`.
- Synced `.codex` and `.cursor` mirrors and verified both drift detection and the mirror sync regression test.

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite extract-deal SKILL.md for chunked extraction** - `56afa8f` (`feat`)
2. **Task 2: Sync skill mirrors after SKILL.md update** - `8a39f49` (`chore`)

**Plan metadata:** Recorded in the final docs commit that captures this summary plus planning-state updates.

## Files Created/Modified

- `.claude/skills/extract-deal/SKILL.md` - Canonical extraction skill rewritten around chunk construction, sequential extraction, and consolidation.
- `.codex/skills/extract-deal/SKILL.md` - Derived mirror synced from the canonical extract-deal skill.
- `.cursor/skills/extract-deal/SKILL.md` - Derived mirror synced from the canonical extract-deal skill.
- `.planning/phases/06-chunked-extraction-architecture/06-01-SUMMARY.md` - Execution summary for this plan.
- `.planning/STATE.md` - GSD execution state updated after plan completion.
- `.planning/ROADMAP.md` - Phase 06 plan progress updated after plan completion.
- `.planning/REQUIREMENTS.md` - Requirement tracking updated for `WFLO-03` per plan workflow.

## Decisions Made

- Used consolidation as the only post-chunk reconciliation step and kept final-round temporal flags out of chunk-local extraction instructions.
- Followed the verification criteria instead of the contradictory plan prose that suggested retaining the literal `Pass 2` phrase.
- Corrected the skill's input contract to match the repository's seed-only, single-document workflow rather than preserving stale supplementary-snippet guidance.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected the Purpose section to match the rewritten extraction contract**
- **Found during:** Task 1 (Rewrite extract-deal SKILL.md for chunked extraction)
- **Issue:** Preserving the old Purpose text would have left the skill claiming a two-pass extraction flow after the method section was rewritten.
- **Fix:** Rewrote the Purpose section to describe chunked sequential extraction followed by consolidation.
- **Files modified:** `.claude/skills/extract-deal/SKILL.md`
- **Verification:** Task 1 contract verification passed after the rewrite.
- **Committed in:** `56afa8f`

**2. [Rule 1 - Bug] Removed stale supplementary-snippet input from the extraction skill contract**
- **Found during:** Task 1 (Rewrite extract-deal SKILL.md for chunked extraction)
- **Issue:** The skill still advertised `supplementary_snippets.jsonl`, which conflicts with the repo's authoritative seed-only single-document workflow.
- **Fix:** Removed the stale read entry from the canonical skill and propagated the correction through both mirrors.
- **Files modified:** `.claude/skills/extract-deal/SKILL.md`, `.codex/skills/extract-deal/SKILL.md`, `.cursor/skills/extract-deal/SKILL.md`
- **Verification:** Task 1 contract verification passed; `python scripts/sync_skill_mirrors.py --check` and `pytest -q tests/test_skill_mirror_sync.py` both passed after mirror sync.
- **Committed in:** `56afa8f` and `8a39f49`

---

**Total deviations:** 2 auto-fixed (2 bug corrections)
**Impact on plan:** Both corrections were necessary to keep the skill contract internally consistent with the repository's authoritative workflow. No scope creep.

## Issues Encountered

- The task body suggested a consolidation heading that referenced `Pass 2`, but the acceptance criteria and verification checks explicitly forbade that phrase. The final skill follows the acceptance criteria while still documenting consolidation as the replacement step.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase `06-02` can now implement deterministic actor dedup and actor audit against a committed chunked-extraction contract.
- The mirror sync workflow is still green, so follow-on skill edits can continue to treat `.claude/skills/` as canonical and `.codex/.cursor` as derived outputs.

## Self-Check: PASSED

- Found summary file at `.planning/phases/06-chunked-extraction-architecture/06-01-SUMMARY.md`.
- Verified task commit `56afa8f`.
- Verified task commit `8a39f49`.

---
*Phase: 06-chunked-extraction-architecture*
*Completed: 2026-03-25*
