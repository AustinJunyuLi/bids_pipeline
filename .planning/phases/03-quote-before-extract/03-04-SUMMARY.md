---
phase: 03-quote-before-extract
plan: 04
subsystem: prompting
tags: [quote-first, compose-prompts, skill-docs, pytest]
requires:
  - phase: 02-prompt-architecture
    provides: prompt packet rendering plus the prompt asset structure consumed by compose-prompts and extract-deal
affects: [compose-prompts, extract-deal, 03-02, 03-03]
provides:
  - Quote-before-extract task instructions in actor and event prompt packets
  - Prompt asset and few-shot example text aligned to the top-level quotes plus quote_ids schema
  - extract-deal skill documentation aligned to QuoteEntry and raw quote-first artifacts
tech-stack:
  added: []
  patterns: [quote-first prompt guidance, rendered-packet assertions for prompt contracts]
key-files:
  created: []
  modified:
    - skill_pipeline/compose_prompts.py
    - skill_pipeline/prompt_assets/actors_prefix.md
    - skill_pipeline/prompt_assets/events_prefix.md
    - skill_pipeline/prompt_assets/event_examples.md
    - .claude/skills/extract-deal/SKILL.md
    - tests/test_skill_compose_prompts.py
key-decisions:
  - "Kept explicit 'do not use evidence_refs' wording in prompt guidance because the plan's replacement text required an unambiguous prohibition during the quote-first migration."
  - "Added compose-prompts regression coverage at the rendered packet level so task-instruction and few-shot contract drift is caught end-to-end."
patterns-established:
  - "Prompt assets now require a top-level quotes array before structured actors or events."
  - "The canonical extract-deal skill doc mirrors the QuoteEntry and quote_ids runtime schema rather than the retired evidence_ref contract."
requirements-completed: []
duration: 14min
completed: 2026-03-28
---

# Phase 3 Plan 04: Prompt Contract Summary

**Quote-first extraction guidance in compose-prompts, prompt assets, event examples, and the extract-deal skill contract**

## Performance

- **Duration:** 14 min
- **Started:** 2026-03-28T09:31:00Z
- **Completed:** 2026-03-28T09:45:29Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Replaced the actor and event task instructions in `compose_prompts.py` with the quote-before-extract protocol, including quotes-first ordering and `quote_ids` linkage.
- Updated both prompt prefix assets and the event few-shot examples so the rendered packets teach the quote-first response format instead of inline evidence refs.
- Rewrote `.claude/skills/extract-deal/SKILL.md` so the local-agent extraction contract now documents the top-level `quotes` array, `quote_id`, and `quote_ids` field usage.
- Added rendered-packet regression tests that fail if the compose-prompts output drops the quote-before-extract instructions or examples.

## Task Commits

Each task was committed atomically:

1. **Task 1: Update prompt assets and task instructions for quote-first protocol** - `f4569a5` (feat)
2. **Task 2: Update extract-deal SKILL.md for quote-first schema** - `5a5d5a7` (docs)

**Plan metadata:** included in the docs completion commit for this plan

## Files Created/Modified
- `skill_pipeline/compose_prompts.py` - Actor and event task instructions now require the quote-before-extract workflow and quotes-first JSON output.
- `skill_pipeline/prompt_assets/actors_prefix.md` - Actor prompt evidence/output requirements now describe top-level quotes plus `quote_ids`.
- `skill_pipeline/prompt_assets/events_prefix.md` - Event prompt evidence/output requirements now describe top-level quotes plus `quote_ids`.
- `skill_pipeline/prompt_assets/event_examples.md` - Few-shot event examples now show quote entries and `quote_ids` references.
- `.claude/skills/extract-deal/SKILL.md` - Canonical extraction skill doc now documents the quote-first schema, field tables, and top-level artifact structures.
- `tests/test_skill_compose_prompts.py` - Added rendered-packet coverage for quote-before-extract instructions and quote-first examples.

## Decisions Made
- Kept the explicit prohibition on `evidence_refs` in the prompt guidance because that wording is the clearest way to prevent legacy-format outputs during the schema transition.
- Validated the prompt contract through rendered packets rather than isolated string constants so the tests cover the real asset composition path.
- Deferred skill-mirror syncing exactly as the plan required; `.claude/skills/` remains the authoritative source until the verification phase runs the sync step.

## Deviations from Plan

The plan's task text and one acceptance bullet conflicted: the replacement text explicitly said to tell the model not to use `evidence_refs`, while another acceptance bullet said the prompt files should not contain the string `evidence_refs`. I followed the explicit replacement text, so `evidence_refs` still appears only as a prohibition against the legacy format.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plan 03-02 and Plan 03-03 can rely on prompt packets and the extraction skill doc describing the same quote-first artifact contract.
- Skill mirror syncing remains pending for the verification phase by plan design; it was intentionally not run here.

## Self-Check: PASSED
- Summary file exists on disk.
- Task commits `f4569a5` and `5a5d5a7` are present in git history.

---
*Phase: 03-quote-before-extract*
*Completed: 2026-03-28*
