---
phase: 01-workflow-contract-surface
plan: 02
subsystem: docs
tags: [workflow-contract, skill-docs, mirror-sync, deal-agent-disambiguation]

# Dependency graph
requires:
  - "01-01: Canonical workflow contract doc at docs/workflow-contract.md"
provides:
  - "CLAUDE.md aligned with live workflow contract and deal-agent disambiguation"
  - "Canonical skill docs corrected for stale artifact references"
  - "Mirror skill trees synchronized and tested after corrections"
affects: [01-workflow-contract-surface, docs, skills]

# Tech tracking
tech-stack:
  added: []
  patterns: [deal-agent CLI-vs-skill disambiguation in top-level docs]

key-files:
  created: []
  modified:
    - CLAUDE.md
    - docs/HOME_COMPUTER_SETUP.md
    - .claude/skills/README.md
    - .claude/skills/enrich-deal/SKILL.md
    - .codex/skills/README.md
    - .codex/skills/enrich-deal/SKILL.md
    - .cursor/skills/README.md
    - .cursor/skills/enrich-deal/SKILL.md

key-decisions:
  - "Add deal-agent disambiguation section to CLAUDE.md rather than duplicating the full workflow-contract.md content"
  - "Remove stale supplementary_snippets.jsonl from enrich-deal Reads rather than marking it optional, since preprocess-source actively deletes it"

patterns-established:
  - "Top-level docs cross-reference workflow-contract.md for detailed stage inventory"

requirements-completed: [WFLO-01]

# Metrics
duration: 3min
completed: 2026-03-25
---

# Phase 01 Plan 02: Reconcile Authoritative Docs and Canonical Skill Contracts Summary

**CLAUDE.md and skill docs aligned with live workflow contract: deal-agent disambiguation, stale artifact removal, mirror sync with 9 passing policy tests**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-25T23:18:16Z
- **Completed:** 2026-03-25T23:21:13Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments

- Added deal-agent disambiguation section to CLAUDE.md distinguishing CLI summary from skill orchestrator
- Added stage classification annotations and workflow-contract.md cross-reference to CLAUDE.md Architecture
- Removed stale `supplementary_snippets.jsonl` dependency from enrich-deal SKILL.md Reads table
- Updated skills README.md with accurate stage descriptions
- Synchronized .codex/skills and .cursor/skills mirrors, all 9 doc-policy tests passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Align top-level instructions and contributor docs with the contract surface** - `2fc73f6` (feat)
2. **Task 2: Correct canonical skill docs for live artifact paths and stage roles** - `6bde239` (feat)
3. **Task 3: Sync mirror skill trees and re-run doc-policy checks** - `b5a4dee` (chore)

## Files Created/Modified

- `CLAUDE.md` - Added deal-agent disambiguation section, stage classification annotations, workflow-contract.md cross-reference, corrected extract-deal description
- `docs/HOME_COMPUTER_SETUP.md` - Added workflow-contract reference and deal-agent entrypoint guidance
- `.claude/skills/README.md` - Updated skill descriptions with accurate stage roles and deal-agent disambiguation
- `.claude/skills/enrich-deal/SKILL.md` - Removed stale supplementary_snippets.jsonl from Reads table
- `.codex/skills/README.md` - Mirror sync
- `.codex/skills/enrich-deal/SKILL.md` - Mirror sync
- `.cursor/skills/README.md` - Mirror sync
- `.cursor/skills/enrich-deal/SKILL.md` - Mirror sync

## Decisions Made

- Added a deal-agent disambiguation section directly in CLAUDE.md rather than duplicating the full workflow-contract.md content -- keeps CLAUDE.md as a concise instruction file while pointing to the contract for details
- Removed stale supplementary_snippets.jsonl from enrich-deal Reads entirely rather than marking it optional -- the current preprocess-source stage actively deletes it as stale output

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None - all doc content is complete and wired to regression tests.

## Next Phase Readiness

- Authoritative docs and canonical skill docs now match the live runtime contract
- Mirror skill trees are synchronized and protected by 9 passing doc-policy tests
- Phase 01 Plan 03 can proceed with any remaining workflow-contract-surface work

## Self-Check: PASSED

- All 8 modified files exist on disk
- All 3 task commits verified in git log

---
*Phase: 01-workflow-contract-surface*
*Completed: 2026-03-25*
