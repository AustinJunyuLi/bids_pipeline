---
phase: 11-foundation-models-path-contracts
plan: 01
subsystem: v2-schema-foundation
tags: [models-v2, pydantic, observations, derivations]
requires:
  - phase: 10-pre-migration-fixes
    provides: clean v1 baseline and structured coverage contract for v2 reuse
provides:
  - additive `skill_pipeline.models_v2` module with the full Phase 11 schema surface
  - direct validation tests for parties, cohorts, observation unions, and derived records
affects: [phase-11 verification, future phase-12 loading, phase-13 validation, phase-14 derivation]
tech-stack:
  added: []
  patterns:
    - additive v2 schema module beside v1 models with shared primitive reuse
key-files:
  created:
    - .planning/phases/11-foundation-models-path-contracts/11-01-SUMMARY.md
    - skill_pipeline/models_v2.py
    - tests/test_skill_observation_models.py
  modified: []
key-decisions:
  - "Phase 11 keeps v2 schemas in `models_v2.py` instead of expanding the live v1 `models.py` surface with a second contract family."
  - "Observation polymorphism uses a discriminated union on `obs_type`, with revision/request/related reference fields present now even though no runtime consumes them yet."
  - "Shared v1 primitives (`SkillModel`, `ResolvedDate`, `MoneyTerms`, `CoverageCheckRecord`, `SkillExclusionRecord`) are reused directly instead of forked."
patterns-established:
  - "Later observation-graph phases can depend on typed importable schemas before any loader or canonicalization runtime exists."
requirements-completed: [MODEL-01, MODEL-02, MODEL-03, MODEL-04, MODEL-05, MODEL-06]
duration: 9m
completed: 2026-03-31
---

# Phase 11 Plan 01: v2 Schema Foundation Summary

**Added the additive `models_v2.py` schema layer and locked its core behaviors with focused Pydantic tests.**

## Performance

- **Duration:** 9m
- **Tasks:** 2
- **Files modified:** 2 created

## Accomplishments

- Defined `PartyRecord`, `CohortRecord`, six observation subtypes, the
  `Observation` discriminated union, `DerivationBasis`, and all Phase 11
  derived record schemas.
- Added v2 artifact wrapper models for observation and derivation surfaces.
- Proved round-trip serialization for parties, nested cohorts, and
  cross-observation references.
- Proved that all six observation subtypes dispatch through the `obs_type`
  discriminator and that derived record schemas require provenance via
  `DerivationBasis`.

## Task Commits

None. The work remained uncommitted because the repository already contained a
large set of unrelated generated-artifact changes.

## Verification

- `pytest -q tests/test_skill_observation_models.py`

## Self-Check: PASSED

- The v2 schema module imports cleanly through the test suite.
- Optional PartyRecord linkage fields and nested CohortRecord lineage are both
  exercised directly.
- Observation references (`requested_by`, `revises`, `supersedes`, `related`)
  survive JSON round-trips.

---
*Phase: 11-foundation-models-path-contracts*
*Completed: 2026-03-31*
