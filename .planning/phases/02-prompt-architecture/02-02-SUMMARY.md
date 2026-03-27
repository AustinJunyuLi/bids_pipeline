---
phase: 02-prompt-architecture
plan: 02
subsystem: prompts
tags: [chunk-planner, evidence-checklist, packet-renderer, xml-sections, overlap-context]

# Dependency graph
requires:
  - phase: 02-prompt-architecture plan 01
    provides: PromptChunkWindow/PromptPacketArtifact/PromptPacketManifest models, compose-prompts CLI, prompt directory paths
provides:
  - deterministic whole-block chunk planner with 2-block overlap windows
  - evidence checklist builder grouped by evidence type
  - provider-neutral actor and event packet renderer with XML sections
  - file-backed stable prompt assets (actors_prefix.md, events_prefix.md, event_examples.md)
  - fully wired compose-prompts stage producing real packet artifacts and manifest
affects: [02-prompt-architecture plan 03, extract-deal skill consumption, phase 05 complexity routing]

# Tech tracking
tech-stack:
  added: []
  patterns: [chronology-first XML packet layout, active evidence checklist, 2-block overlap windows]

key-files:
  created:
    - skill_pipeline/prompts/__init__.py
    - skill_pipeline/prompts/chunks.py
    - skill_pipeline/prompts/checklist.py
    - skill_pipeline/prompts/render.py
    - skill_pipeline/prompt_assets/actors_prefix.md
    - skill_pipeline/prompt_assets/events_prefix.md
    - skill_pipeline/prompt_assets/event_examples.md
    - tests/test_skill_compose_prompts.py
  modified:
    - skill_pipeline/compose_prompts.py

key-decisions:
  - "Token estimation uses ceil(word_count * 1.35) heuristic -- validate against stec in Plan 03"
  - "Greedy whole-block chunking with at-least-one-block-per-window guarantee"
  - "Checklist groups evidence by type with imperative headers, not passive appendix"
  - "Packet body order: deal_context, chronology_blocks, overlap_context, evidence_checklist, actor_roster, task_instructions"
  - "--mode all generates actors only; event packets require separate --mode events after actors_raw.json exists"

patterns-established:
  - "XML section tags for deterministic packet structure: <chronology_blocks>, <overlap_context>, <evidence_checklist>, <actor_roster>, <task_instructions>"
  - "File-backed prompt assets under skill_pipeline/prompt_assets/ for provider-neutral stability"
  - "Packet files written as prefix.md + body.md + rendered.md per packet_id directory"

requirements-completed: [INFRA-03, INFRA-05, PROMPT-01, PROMPT-02, PROMPT-03, PROMPT-04]

# Metrics
duration: 7min
completed: 2026-03-27
---

# Phase 2 Plan 02: Chunk Planner, Evidence Checklist, and Packet Renderer Summary

**Deterministic chunk planner with 2-block overlap, active evidence checklist, and chronology-first XML packet renderer producing real file-backed prompt artifacts**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-27T23:25:58Z
- **Completed:** 2026-03-27T23:33:07Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments
- Whole-block chunk planner that emits single_pass or chunked windows with exact 2-block overlap
- Evidence checklist builder that groups items by type with imperative headers and evidence IDs
- Provider-neutral packet renderer enforcing chronology-first section ordering with explicit XML tags
- Stable prompt assets (actors_prefix.md, events_prefix.md, event_examples.md) versioned in repo
- compose-prompts wired end-to-end: loads blocks, builds windows, renders packets, writes manifest
- Fail-fast on --mode events without actors_raw.json
- 34 regression tests covering chunks, checklist, render, and integration

## Task Commits

Each task was committed atomically:

1. **Task 1: Build whole-block chunk planner with 2-block overlap** - `9b43963` (feat)
2. **Task 2: Render chronology-first packets, evidence checklists, stable assets** - `ba1ebd3` (feat)
3. **Task 3: Wire renderer into compose-prompts with regression tests** - `a4076c0` (feat)

## Files Created/Modified
- `skill_pipeline/prompts/__init__.py` - Package init for prompt composition helpers
- `skill_pipeline/prompts/chunks.py` - Token estimator and deterministic chunk planner
- `skill_pipeline/prompts/checklist.py` - Evidence checklist builder grouped by type
- `skill_pipeline/prompts/render.py` - Actor and event packet renderer with XML sections
- `skill_pipeline/prompt_assets/actors_prefix.md` - Stable actor extraction prefix
- `skill_pipeline/prompt_assets/events_prefix.md` - Stable event extraction prefix
- `skill_pipeline/prompt_assets/event_examples.md` - Few-shot event examples
- `skill_pipeline/compose_prompts.py` - Full render + file-write wiring
- `tests/test_skill_compose_prompts.py` - 34 regression tests

## Decisions Made
- Token estimation uses `ceil(word_count * 1.35)` -- needs validation against real stec packet sizes in Plan 03
- Greedy whole-block chunking always includes at least one block per window even if it exceeds budget
- Evidence checklist uses imperative headers grouped by EvidenceType enum order for stable output
- Packet body order is fixed: deal_context, chronology_blocks, overlap_context, evidence_checklist, actor_roster, task_instructions
- `--mode all` generates actor packets only; event packets need `--mode events` after actor extraction produces actors_raw.json

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Known Stubs

None - all functionality is fully wired.

## Next Phase Readiness
- Prompt composition engine is fully operational for actor and event packet families
- Plan 03 (skill doc update + stec validation) can consume the generated packets
- Phase 5 complexity routing can use the same chunk planner with different thresholds

## Self-Check: PASSED

All 9 created files verified present. All 3 task commits verified in git log. 175/175 tests pass.

---
*Phase: 02-prompt-architecture*
*Completed: 2026-03-27*
