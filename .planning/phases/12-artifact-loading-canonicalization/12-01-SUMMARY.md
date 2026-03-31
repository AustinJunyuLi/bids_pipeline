---
phase: 12-artifact-loading-canonicalization
plan: 01
subsystem: v2-loader-surface
tags: [extract-artifacts-v2, mode-detection, raw-v2, canonical-v2]
requires:
  - phase: 11-foundation-models-path-contracts
    provides: additive v2 schema and path contracts
provides:
  - separate v2 artifact loader module with raw/canonical load modes
  - explicit v1/v2/both/none extract-surface detection
affects: [phase-12 verification, future phase-13 validation, future phase-14 derivation]
tech-stack:
  added: []
  patterns:
    - separate v2 loader plus explicit version router, leaving the v1 loader untouched
key-files:
  created:
    - .planning/phases/12-artifact-loading-canonicalization/12-01-SUMMARY.md
    - skill_pipeline/extract_artifacts_v2.py
    - tests/test_skill_extract_artifacts_v2.py
  modified: []
key-decisions:
  - "Phase 12 adds quote-first v2 wrapper models in the v2 loader module because the Phase 11 models are canonical span-backed schemas only."
  - "When both v1 and v2 artifacts exist on disk, auto-routing refuses ambiguity instead of silently picking one contract."
patterns-established:
  - "Cross-version migration surfaces should separate version-specific loaders and put ambiguity handling in a narrow router rather than in the legacy loader."
requirements-completed: [INFRA-01]
duration: 10m
completed: 2026-03-31
---

# Phase 12 Plan 01: v2 Loader Summary

**Added a separate v2 artifact loader with explicit version detection and quote-first/canonical v2 loading modes.**

## Performance

- **Duration:** 10m
- **Tasks:** 2
- **Files modified:** 2 created

## Accomplishments

- Created `extract_artifacts_v2.py` with raw v2 quote-first models,
  `LoadedObservationArtifacts`, and typed canonical loading.
- Added `detect_extract_artifact_version()` and
  `load_versioned_extract_artifacts()` so the repo can distinguish `v1`, `v2`,
  `both`, and `none` states without modifying `extract_artifacts.py`.
- Added dedicated tests covering raw v2 loads, canonical v2 loads, missing
  spans failures, and explicit ambiguity handling when both artifact families
  are present.

## Task Commits

None. The repository remained in a heavily dirty state with unrelated generated
artifacts, so this work stayed uncommitted.

## Verification

- `pytest -q tests/test_skill_extract_artifacts_v2.py`

## Self-Check: PASSED

- The v1 loader behavior is unchanged.
- The v2 loader can load either raw or canonical observation artifacts.
- Ambiguous mixed-version presence now fails closed unless the caller chooses a
  version explicitly.

---
*Phase: 12-artifact-loading-canonicalization*
*Completed: 2026-03-31*
