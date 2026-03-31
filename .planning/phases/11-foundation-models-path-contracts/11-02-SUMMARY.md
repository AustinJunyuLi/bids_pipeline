---
phase: 11-foundation-models-path-contracts
plan: 02
subsystem: additive-path-contracts
tags: [paths, infrastructure, additive-migration, repo-memory]
requires:
  - phase: 11-foundation-models-path-contracts
    provides: importable v2 schema surface for downstream path consumers
provides:
  - additive v2 directories and file paths in `SkillPathSet`
  - directory creation support for reserved v2 artifact surfaces
  - authoritative repo memory for the structured coverage and v2 path contracts
affects: [phase-11 verification, future phase-12/13/14/15/16 implementation, CLAUDE.md]
tech-stack:
  added: []
  patterns:
    - low-risk additive path registration with tests that explicitly pin legacy v1 values
key-files:
  created:
    - .planning/phases/11-foundation-models-path-contracts/11-02-SUMMARY.md
  modified:
    - skill_pipeline/models.py
    - skill_pipeline/paths.py
    - tests/test_skill_pipeline.py
    - CLAUDE.md
key-decisions:
  - "Phase 11 registers the full low-risk v2 artifact surface now, including future-facing file paths, but documents them as reserved paths rather than claiming live writers already exist."
  - "The v2 path contract remains strictly additive: `extract/`, `export/`, and `prompt/` values are preserved byte-for-byte."
  - "Repository memory now records the Phase 10 structured coverage detail contract in `CLAUDE.md` because it is part of the live artifact surface."
patterns-established:
  - "When migration scaffolding lands ahead of runtime writers, `CLAUDE.md` must distinguish reserved path contracts from active emitting stages."
requirements-completed: [INFRA-03]
duration: 8m
completed: 2026-03-31
---

# Phase 11 Plan 02: Additive Path Contract Summary

**Registered the v2 artifact path surface in `SkillPathSet`, created the new directories in `ensure_output_directories()`, and documented the contract in `CLAUDE.md`.**

## Performance

- **Duration:** 8m
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Added additive v2 path fields for `extract_v2/`, `check_v2/`,
  `coverage_v2/`, `gates_v2/`, `derive/`, `export_v2/`, and `prompt_v2/`,
  along with the key file paths those later phases will consume.
- Updated `ensure_output_directories()` so the reserved v2 surfaces are
  materialized alongside the existing v1 directories.
- Added regression tests proving the new v2 paths exist while legacy
  `extract/`, `export/`, and `prompt/` values remain unchanged.
- Updated `CLAUDE.md` so the repo memory now reflects both the structured
  coverage detail artifact and the additive v2 path surface.

## Task Commits

None. The work stayed uncommitted because the worktree already contained many
unrelated generated and user-created changes.

## Verification

- `pytest -q tests/test_skill_pipeline.py`

## Self-Check: PASSED

- `build_skill_paths()` exposes both v1 and v2 surfaces without collisions.
- `ensure_output_directories()` creates the new v2 directories.
- Repo memory describes the v2 paths as reserved additive scaffolding, not as
  already-live writer outputs.

---
*Phase: 11-foundation-models-path-contracts*
*Completed: 2026-03-31*
