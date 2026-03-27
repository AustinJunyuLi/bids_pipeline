---
phase: 01-foundation-annotation
plan: 01
subsystem: preprocessing
tags: [pydantic, chronology-blocks, annotation, deterministic-metadata]

# Dependency graph
requires: []
provides:
  - "Required annotated ChronologyBlock schema with date_mentions, entity_mentions, evidence_density, temporal_phase"
  - "Deterministic annotation helper module at skill_pipeline/source/annotate.py"
  - "Annotation integrated into preprocess-source stage"
  - "All downstream test fixtures refreshed for new block schema"
affects: [prompt-architecture, extract-deal, verify, coverage]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Block annotation as post-build step in preprocess-source"
    - "Evidence-type primary signal with ordinal fallback for temporal phase"
    - "Seed-based entity matching with filing alias patterns"

key-files:
  created:
    - "skill_pipeline/source/annotate.py"
    - "tests/test_skill_source_annotations.py"
  modified:
    - "skill_pipeline/pipeline_models/source.py"
    - "skill_pipeline/source/blocks.py"
    - "skill_pipeline/preprocess/source.py"
    - "tests/test_skill_preprocess_source.py"
    - "tests/test_skill_canonicalize.py"
    - "tests/test_skill_verify.py"
    - "tests/test_skill_coverage.py"
    - "tests/test_skill_enrich_core.py"
    - "tests/test_skill_pipeline.py"
    - "tests/test_skill_provenance.py"

key-decisions:
  - "New annotation fields are required on ChronologyBlock (no defaults, no optionals)"
  - "Block builder creates placeholder annotation values that annotate_chronology_blocks replaces"
  - "Entity matching uses case-insensitive substring for seed names plus regex for Party/Company/Board/Committee aliases"
  - "Temporal phase uses evidence-type primary signal (outcome > bidding > initiation) with ordinal fallback"

patterns-established:
  - "Annotation as post-build enrichment: build_chronology_blocks creates base blocks, annotate_chronology_blocks adds metadata"
  - "BlockDateMention and BlockEntityMention as lightweight Pydantic models for structured block metadata"

requirements-completed: [INFRA-04]

# Metrics
duration: 6min
completed: 2026-03-27
---

# Phase 1 Plan 01: Annotated Block Schema Summary

**Required date/entity/density/phase metadata on ChronologyBlock with deterministic annotation helpers and preprocess-source integration**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-27T16:24:10Z
- **Completed:** 2026-03-27T16:30:21Z
- **Tasks:** 3
- **Files modified:** 12

## Accomplishments
- Added BlockDateMention and BlockEntityMention Pydantic models and four required annotation fields to ChronologyBlock
- Created annotate_chronology_blocks() with date extraction, entity matching, evidence density counting, and temporal phase assignment
- Integrated annotation into preprocess-source without adding CLI subcommands or new artifact files
- Refreshed all 7 downstream test files with valid annotated block fixtures (77 tests pass)

## Task Commits

Each task was committed atomically:

1. **Task 1: Define the required annotated block schema and helper surface** - `3afa2a6` (feat)
2. **Task 2: Integrate annotation into preprocess-source** - `6a25a53` (feat)
3. **Task 3: Add focused annotation tests and refresh every stale block fixture** - `adebb26` (test)

## Files Created/Modified
- `skill_pipeline/pipeline_models/source.py` - Added BlockDateMention, BlockEntityMention models and required annotation fields on ChronologyBlock
- `skill_pipeline/source/annotate.py` - New module with annotate_chronology_blocks() and helpers for date, entity, density, phase
- `skill_pipeline/source/blocks.py` - Updated block builder to include placeholder annotation fields
- `skill_pipeline/preprocess/source.py` - Imported and wired annotation step after evidence dedup
- `tests/test_skill_source_annotations.py` - 23 unit tests for annotation helpers
- `tests/test_skill_preprocess_source.py` - Added seeds.csv fixture and annotation assertion test
- `tests/test_skill_canonicalize.py` - Refreshed block fixtures with annotation metadata
- `tests/test_skill_verify.py` - Refreshed block fixtures with annotation metadata
- `tests/test_skill_coverage.py` - Refreshed block fixtures with annotation metadata
- `tests/test_skill_enrich_core.py` - Replaced bare {} block stubs with valid annotated blocks
- `tests/test_skill_pipeline.py` - Replaced bare {} block stubs with valid annotated blocks
- `tests/test_skill_provenance.py` - Refreshed block fixtures with annotation metadata

## Decisions Made
- Annotation fields are required (no defaults) so stale unannotated blocks fail on load -- forces re-running preprocess-source
- Block builder creates blocks with placeholder annotation values (empty lists, 0 density, "other" phase) that annotate_chronology_blocks replaces with computed values
- Entity matching: case-insensitive substring for seed target/acquirer names plus regex for Party [A-Z], the Company, the Board, Special Committee, Transaction Committee
- Temporal phase priority: outcome > bidding > initiation from evidence types; ordinal fallback for blocks without overlapping evidence

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated blocks.py to include required annotation placeholders**
- **Found during:** Task 2 (preprocess integration)
- **Issue:** build_chronology_blocks creates ChronologyBlock instances without the new required fields, causing ValidationError
- **Fix:** Added placeholder annotation values (empty lists, 0 density, "other" phase) to block construction in blocks.py
- **Files modified:** skill_pipeline/source/blocks.py
- **Verification:** All preprocess tests pass
- **Committed in:** 6a25a53 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary structural fix -- the block builder must emit valid ChronologyBlock instances under the new schema. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Annotated block schema is required and serialized through chronology_blocks.jsonl
- The preprocess stage remains deterministic and fail-fast
- Downstream deterministic tests accept the new source artifact contract
- Ready for Plans 02 and 03 (enhanced gates and deterministic enrichment extensions)

## Self-Check: PASSED

All 12 created/modified files verified present. All 3 task commits verified in git log.

---
*Phase: 01-foundation-annotation*
*Completed: 2026-03-27*
