---
phase: 02-prompt-architecture
plan: 01
subsystem: infra
tags: [pydantic, prompt-packets, cli, artifact-contracts]

# Dependency graph
requires:
  - phase: 01-foundation-annotation
    provides: annotated ChronologyBlock and EvidenceItem source artifacts
provides:
  - PromptPacketManifest, PromptPacketArtifact, PromptChunkWindow schema models
  - prompt_dir, prompt_packets_dir, prompt_manifest_path in SkillPathSet
  - compose-prompts CLI subcommand with --deal, --mode, --chunk-budget
  - run_compose_prompts deterministic stage entrypoint
affects: [02-02-PLAN (packet rendering), 02-03-PLAN (skill integration), extract-deal]

# Tech tracking
tech-stack:
  added: []
  patterns: [prompt-artifact-directory-under-skill-root, manifest-stub-pattern]

key-files:
  created:
    - skill_pipeline/pipeline_models/prompt.py
    - skill_pipeline/compose_prompts.py
    - tests/test_skill_prompt_models.py
  modified:
    - skill_pipeline/pipeline_models/__init__.py
    - skill_pipeline/models.py
    - skill_pipeline/paths.py
    - skill_pipeline/cli.py
    - tests/test_skill_pipeline.py

key-decisions:
  - "Prompt packet models inherit ArtifactEnvelope for manifest-level metadata consistency"
  - "Prompt artifacts live under data/skill/<slug>/prompt/ separate from extract/"
  - "compose-prompts writes a manifest stub; packet rendering deferred to plan 02"

patterns-established:
  - "Prompt artifact directory: data/skill/<slug>/prompt/ with packets/ subdirectory"
  - "Manifest-first stage pattern: compose-prompts creates manifest.json before packet files"

requirements-completed: [INFRA-01, INFRA-02, INFRA-05]

# Metrics
duration: 4min
completed: 2026-03-27
---

# Phase 2 Plan 01: Prompt Packet Contract Summary

**Provider-neutral prompt packet schemas, deterministic artifact paths under data/skill/<slug>/prompt/, and compose-prompts CLI stage shell with contract tests**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-27T23:17:38Z
- **Completed:** 2026-03-27T23:22:08Z
- **Tasks:** 3/3
- **Files modified:** 7

## Accomplishments
- Schema-validated prompt packet models (PromptChunkWindow, PromptPacketArtifact, PromptPacketManifest) with Literal-typed packet_family and chunk_mode
- Extended SkillPathSet with prompt_dir, prompt_packets_dir, prompt_manifest_path; ensure_output_directories creates them
- compose-prompts CLI subcommand with --deal, --mode, --chunk-budget that validates source artifacts and writes a manifest stub
- 20 new tests covering schema validation, path contracts, CLI parsing, missing-input failures, and manifest round-trips

## Task Commits

Each task was committed atomically:

1. **Task 1: Define schema-validated prompt packet models** - `5aefdbf` (feat)
2. **Task 2: Extend path contracts and expose compose-prompts stage** - `68a1ec2` (feat)
3. **Task 3: Add contract-level tests for prompt models, paths, and CLI failures** - `e4e4c14` (test)

## Files Created/Modified
- `skill_pipeline/pipeline_models/prompt.py` - PromptChunkWindow, PromptPacketArtifact, PromptPacketManifest schemas
- `skill_pipeline/pipeline_models/__init__.py` - Exports new prompt models
- `skill_pipeline/models.py` - Added prompt_dir, prompt_packets_dir, prompt_manifest_path to SkillPathSet
- `skill_pipeline/paths.py` - Build and ensure prompt directories
- `skill_pipeline/cli.py` - compose-prompts subcommand
- `skill_pipeline/compose_prompts.py` - run_compose_prompts deterministic stage entrypoint
- `tests/test_skill_prompt_models.py` - Schema validation tests
- `tests/test_skill_pipeline.py` - Path contract, CLI, and integration tests

## Decisions Made
- Prompt packet models inherit ArtifactEnvelope (via PromptPacketManifest) for manifest-level metadata consistency with other pipeline artifacts
- Prompt artifacts live under data/skill/<slug>/prompt/ to stay separate from extract/ (which holds LLM-produced outputs)
- compose-prompts writes a manifest stub with source stats in notes; actual packet rendering is deferred to plan 02

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
- `skill_pipeline/compose_prompts.py`: The manifest `packets` list is empty (intentional stub). Packet rendering logic will be implemented in plan 02 of this phase. The stage validates inputs and creates directory structure but does not yet produce rendered prompt files.

## Next Phase Readiness
- Prompt artifact contract is locked: schemas, paths, and CLI entrypoint are testable
- Plan 02 can implement chunk planning, checklist construction, and packet rendering against this contract
- Plan 03 can update extract-deal skill to consume the composed packets
- Full test suite passes (141 tests, 0 failures)

---
*Phase: 02-prompt-architecture*
*Completed: 2026-03-27*
