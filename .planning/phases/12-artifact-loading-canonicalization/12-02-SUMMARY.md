---
phase: 12-artifact-loading-canonicalization
plan: 02
subsystem: canonicalize-v2-runtime
tags: [canonicalize-v2, spans, cli, v2-runtime]
requires:
  - phase: 12-artifact-loading-canonicalization
    provides: v2 loader surface and raw-v2 wrapper models
provides:
  - live `canonicalize-v2` runtime path for canonical v2 observations
  - CLI registration and synthetic fixture coverage for the new command
  - authoritative repo memory update for live canonical v2 outputs
affects: [phase-12 verification, CLAUDE.md, future phase-13 validation]
tech-stack:
  added: []
  patterns:
    - reuse shared span-resolution helpers while keeping v1 event heuristics out of the v2 path
key-files:
  created:
    - .planning/phases/12-artifact-loading-canonicalization/12-02-SUMMARY.md
    - tests/test_skill_canonicalize_v2.py
  modified:
    - skill_pipeline/canonicalize.py
    - skill_pipeline/cli.py
    - tests/test_skill_pipeline.py
    - CLAUDE.md
key-decisions:
  - "canonicalize-v2 prefers `observations_raw.json` when present so reruns can rebuild canonical outputs from fresh raw extraction artifacts."
  - "The v2 canonicalization path reuses quote-to-span resolution only; it does not inherit v1 dedup, NDA gating, or unnamed-party recovery heuristics."
  - "CLAUDE.md now promotes `canonicalize-v2` from a reserved path contract to a live writer for canonical v2 observation outputs."
patterns-established:
  - "New v2 runtime stages can piggyback on shared provenance helpers without sharing v1 post-processing semantics."
requirements-completed: [INFRA-02]
duration: 8m
completed: 2026-03-31
---

# Phase 12 Plan 02: canonicalize-v2 Summary

**Implemented `canonicalize-v2`, wired it into the CLI, and proved it on synthetic v2 fixtures including an actual `cli.main([...])` execution path.**

## Performance

- **Duration:** 8m
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Added `run_canonicalize_v2()` to upgrade quote-first v2 observation artifacts
  into canonical `observations.json` plus `extract_v2/spans.json`.
- Reused the shared `_resolve_quotes_to_spans()` helper and shared
  chronology/document loaders instead of duplicating provenance logic.
- Added the `canonicalize-v2` CLI command and parser coverage.
- Added a dedicated v2 canonicalize test file covering raw-to-canonical
  upgrades, canonical idempotence, and direct CLI execution on a synthetic
  fixture.
- Updated `CLAUDE.md` so the repo memory now records `canonicalize-v2` as a
  live writer, not just a reserved path surface.

## Task Commits

None. The work remained uncommitted because the worktree still contains many
unrelated generated and user-originated modifications.

## Verification

- `pytest -q tests/test_skill_canonicalize_v2.py`
- `pytest -q tests/test_skill_extract_artifacts_v2.py tests/test_skill_canonicalize_v2.py tests/test_skill_pipeline.py -k 'v2 or canonicalize_v2'`

## Self-Check: PASSED

- `canonicalize-v2` upgrades raw v2 artifacts into span-backed canonical files.
- The command is idempotent on existing canonical v2 fixtures.
- Existing v1 canonicalize and v1 loader tests stay green.

---
*Phase: 12-artifact-loading-canonicalization*
*Completed: 2026-03-31*
