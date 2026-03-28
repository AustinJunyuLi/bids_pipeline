---
phase: 05-integration-calibration
plan: 02
subsystem: infra
tags: [compose-prompts, routing, chunking, few-shot, cli]
requires:
  - phase: 02-prompt-architecture
    provides: compose-prompts chunk planning, packet rendering, and prompt asset loading
  - phase: 03-quote-before-extract
    provides: quote-first event prompt contract and prompt asset schema
affects: [05-03-PLAN, compose-prompts, extract-deal]
provides:
  - complexity-based prompt routing for simple vs complex deals
  - explicit single-pass chunk planner override without magic budgets
  - expanded filing-grounded quote-first event few-shot examples
tech-stack:
  added: []
  patterns:
    - explicit routing flag threaded from CLI to compose-prompts
    - block-count complexity classification at SIMPLE_DEAL_MAX_BLOCKS=150
    - quote-first prompt examples grounded in on-disk filing text
key-files:
  created:
    - skill_pipeline/complexity.py
  modified:
    - skill_pipeline/compose_prompts.py
    - skill_pipeline/prompts/chunks.py
    - skill_pipeline/cli.py
    - skill_pipeline/prompt_assets/event_examples.md
    - tests/test_skill_compose_prompts.py
key-decisions:
  - "Auto routing classifies on chronology block count only and drives an explicit single_pass switch instead of a magic oversized chunk budget."
  - "Legacy chunk-behavior integration tests now opt into routing='chunked' so the new auto default can remain single-pass for small deals."
patterns-established:
  - "Routing contract: CLI exposes auto, single-pass, and chunked; compose-prompts records routing and effective_budget in manifest notes."
  - "Chunk planner contract: single_pass=True always emits one whole-filing window while chunk_budget continues to govern chunked mode."
requirements-completed: [PROMPT-06, INFRA-07]
duration: 6m
completed: 2026-03-28
---

# Phase 5 Plan 2: Complexity Routing and Example Expansion Summary

**Block-count-based compose-prompts routing with explicit single-pass windows and five filing-grounded quote-first event examples**

## Performance

- **Duration:** 6m
- **Started:** 2026-03-28T18:01:34Z
- **Completed:** 2026-03-28T18:07:59Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Added `skill_pipeline.complexity` and wired `compose-prompts` auto routing so deals with `<=150` blocks force a single prompt window while larger deals keep chunk-budget planning.
- Added an explicit `single_pass` override to the chunk planner and exposed `--routing {auto,single-pass,chunked}` through the `skill-pipeline compose-prompts` CLI.
- Expanded `event_examples.md` from 2 to 5 quote-first examples covering range proposals, formal-round signals, NDA groups, ambiguous drops, and termination/restart cycle boundaries.

## Task Commits

Each task was committed atomically:

1. **Task 1: Complexity routing module and compose-prompts integration** - `c49d0ee` (test), `b4f27e0` (feat)
2. **Task 2: Expand few-shot event examples to 4-5 patterns** - `84aa38c` (feat)

## Files Created/Modified
- `skill_pipeline/complexity.py` - exports `SIMPLE_DEAL_MAX_BLOCKS` and `classify_deal_complexity()`.
- `skill_pipeline/compose_prompts.py` - adds routing selection, manifest notes, and explicit single-pass window selection.
- `skill_pipeline/prompts/chunks.py` - adds the `single_pass` planner override while preserving existing chunk-budget behavior.
- `skill_pipeline/cli.py` - adds minimal compose-prompts `--routing` parser and dispatch wiring.
- `skill_pipeline/prompt_assets/event_examples.md` - rewrites the event few-shot asset to five quote-first, filing-grounded examples.
- `tests/test_skill_compose_prompts.py` - adds routing/classification regressions, example-count coverage, and updates chunk-specific assertions to request `routing="chunked"` explicitly.

## Decisions Made
- Auto routing uses only chronology block count in this plan. The roadmap still mentions actors, but this implementation follows the plan contract and exports the threshold in one place for later extension.
- The chunk planner keeps normal under-budget single-pass behavior and adds an explicit override for routing, avoiding any hidden magic-number budget path.
- The new few-shot examples favor real filing excerpts already present under `data/deals/*/source/` even when the paired extraction artifact was available only for some examples.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Regression] Preserved old chunk-behavior coverage under the new auto default**
- **Found during:** Task 1
- **Issue:** Existing integration tests using small fixtures and low chunk budgets started routing to single-pass under the new `auto` default, invalidating assertions that were actually exercising chunk overlap behavior.
- **Fix:** Updated those specific tests to request `routing="chunked"` explicitly while adding new auto-routing tests for the default behavior.
- **Files modified:** `tests/test_skill_compose_prompts.py`
- **Verification:** `python -m pytest tests/test_skill_compose_prompts.py -x -q`
- **Committed in:** `b4f27e0`

### Plan Sequencing Adjustments

- Added `test_event_examples_count` in Task 2 instead of Task 1 so Task 1 verification did not depend on unexecuted few-shot content changes.

---

**Total deviations:** 1 auto-fix, 1 sequencing adjustment
**Impact on plan:** No scope creep. Both changes kept task boundaries workable while preserving the intended feature set.

## Issues Encountered
- A transient `.git/index.lock` from parallel executor activity blocked the first test commit. The lock cleared immediately and the commit succeeded on retry without manual cleanup.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `compose-prompts` now exposes stable routing semantics for the orchestration work in `05-03`.
- Quote-first event prompts now have the full five-pattern few-shot coverage expected by the extraction workflow.
- No blockers found for the next integration/orchestration plan.

---
*Phase: 05-integration-calibration*
*Completed: 2026-03-28*

## Self-Check: PASSED
- Found `.planning/phases/05-integration-calibration/05-02-SUMMARY.md`
- Verified task commits `c49d0ee`, `b4f27e0`, and `84aa38c` in `git log --oneline --all`
