---
phase: 02-prompt-architecture
plan: 03
subsystem: infra
tags: [prompt-packets, validation, deal-agent, skill-mirrors, runtime-contract]

# Dependency graph
requires:
  - phase: 02-prompt-architecture plan 01
    provides: prompt packet models, paths, CLI subcommand
  - phase: 02-prompt-architecture plan 02
    provides: chunk planner, evidence checklist, packet renderer
provides:
  - deterministic prompt packet validator script
  - prompt-stage status reporting in deal-agent summary
  - compose-prompts integrated into CLAUDE.md, docs/design.md, and extract-deal SKILL.md
  - skill mirror sync with prompt-stage content
  - stec prompt packet validation baseline
affects: [extract-deal, deal-agent, runtime-contract, phase-03]

# Tech tracking
tech-stack:
  added: []
  patterns: [validator-script-pattern, stage-summary-extension]

key-files:
  created:
    - scripts/validate_prompt_packets.py
  modified:
    - skill_pipeline/deal_agent.py
    - skill_pipeline/models.py
    - CLAUDE.md
    - docs/design.md
    - .claude/skills/extract-deal/SKILL.md
    - .codex/skills/extract-deal/SKILL.md
    - .cursor/skills/extract-deal/SKILL.md
    - tests/test_skill_pipeline.py
    - tests/test_skill_mirror_sync.py
    - tests/test_runtime_contract_docs.py

key-decisions:
  - "Validator checks both schema validity and rendered content tags"
  - "PromptStageSummary reports packet_count, actor_packet_count, event_packet_count"
  - "compose-prompts inserted between preprocess-source and /extract-deal in all runtime docs"

patterns-established:
  - "Validator script pattern: scripts/*.py with --deal, --project-root, and feature flags"
  - "Stage summary extension: new *StageSummary model + _summarize_* helper in deal_agent"

requirements-completed: [INFRA-01, INFRA-02, INFRA-03, INFRA-05, PROMPT-01, PROMPT-02, PROMPT-03, PROMPT-04]

# Metrics
duration: 8min
completed: 2026-03-27
---

# Phase 2 Plan 3: Integration and stec Validation Summary

**Prompt packet validator, deal-agent prompt-stage status, runtime doc integration, skill mirror sync, and stec validation baseline**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-27T23:36:40Z
- **Completed:** 2026-03-27T23:45:03Z
- **Tasks:** 3
- **Files modified:** 10

## Accomplishments
- Created deterministic prompt packet validator with schema and tag assertions
- Extended deal-agent summary to report prompt-stage status (packet counts)
- Integrated compose-prompts into all runtime docs (CLAUDE.md, docs/design.md)
- Updated extract-deal skill contract to consume prompt packets with preflight instructions
- Synced all skill mirrors (.codex, .cursor) and added sync regression tests
- Validated stec prompt packets (actors mode, chunk-budget 6000) end-to-end
- Added 12 new tests across 3 test files

## Task Commits

Each task was committed atomically:

1. **Task 1: Add prompt packet validation and surface prompt-stage status in deal-agent** - `a166485` (feat)
2. **Task 2: Update the canonical extract skill and sync all skill mirrors** - `b754e6d` (feat)
3. **Task 3: Validate stec prompt packets and record the extraction-quality check path** - `01747cf` (feat)

## Files Created/Modified
- `scripts/validate_prompt_packets.py` - Deterministic validator for prompt packet artifacts with --deal, --project-root, --expect-sections
- `skill_pipeline/models.py` - Added PromptStageSummary model and wired into DealAgentSummary
- `skill_pipeline/deal_agent.py` - Added _summarize_prompt helper, imported PromptStageSummary
- `CLAUDE.md` - Added compose-prompts to runtime split, end-to-end flow, artifact contract, dev commands
- `docs/design.md` - Inserted compose-prompts in operational sequence, added prompt artifact flow entry
- `.claude/skills/extract-deal/SKILL.md` - Added prompt manifest/packets to Reads table, preflight section, packet-based extraction instructions
- `.codex/skills/extract-deal/SKILL.md` - Mirror synced from canonical
- `.cursor/skills/extract-deal/SKILL.md` - Mirror synced from canonical
- `tests/test_skill_pipeline.py` - 6 new tests: prompt-stage status and packet validator
- `tests/test_skill_mirror_sync.py` - 3 new tests: prompt manifest reference and mirror byte equality
- `tests/test_runtime_contract_docs.py` - 5 new tests: compose-prompts in runtime docs, fixture-based validator

## Decisions Made
- Validator checks both Pydantic schema validation (via PromptPacketManifest) and rendered content tag assertions (chronology_blocks, evidence_checklist, task_instructions, overlap_context for chunked)
- PromptStageSummary uses three count fields (packet_count, actor_packet_count, event_packet_count) plus StageStatus
- compose-prompts is documented between preprocess-source and /extract-deal in all three runtime documents

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## stec Validation Path

The following commands validate the prompt-to-extraction pipeline for stec:

```bash
# 1. Generate actor prompt packets
skill-pipeline compose-prompts --deal stec --mode actors --chunk-budget 6000

# 2. Validate prompt packets
python scripts/validate_prompt_packets.py --deal stec --project-root /home/austinli/Projects/bids_pipeline --expect-sections

# 3. Extract actors using composed packets
/extract-deal stec  # (local agent, uses prompt packets)

# 4. Generate event prompt packets (requires actors_raw.json)
skill-pipeline compose-prompts --deal stec --mode events --chunk-budget 6000

# 5. Extract events using composed packets
/extract-deal stec  # (local agent, uses event prompt packets)

# 6. Run deterministic gates
skill-pipeline canonicalize --deal stec
skill-pipeline check --deal stec
skill-pipeline verify --deal stec
skill-pipeline coverage --deal stec
```

Exit criterion: deterministic gates pass on filing-grounded extraction through composed prompt packets.

## Next Phase Readiness
- Phase 2 prompt architecture is complete: models, composition engine, rendering, validation, and integration
- stec prompt packets validated and the extraction-quality path is documented
- Ready for Phase 3 (quote-before-extract response format)

---
*Phase: 02-prompt-architecture*
*Completed: 2026-03-27*
