# Phase 11: Foundation Models + Path Contracts - Research

**Date:** 2026-03-31
**Status:** Complete

## Findings

### 1. The repo has no v2 schema module yet

- There is no `skill_pipeline/models_v2.py`.
- The current `skill_pipeline/models.py` contains only the live v1 contract plus
  shared primitives.
- The project research consistently recommends an additive `models_v2.py`
  module instead of mutating the existing v1 schema surface.

### 2. The observation model shape is well specified already

- Research defines six observation subtypes:
  `ProcessObservation`, `AgreementObservation`, `SolicitationObservation`,
  `ProposalObservation`, `StatusObservation`, and `OutcomeObservation`.
- The required discriminator is `obs_type`.
- Required cross-observation reference fields are:
  `revises_observation_id`, `supersedes_observation_id`,
  `requested_by_observation_id`, and `related_observation_id`.

### 3. Shared primitives can be reused

- `SkillModel`, `ResolvedDate`, and `MoneyTerms` already exist in v1 and fit
  the v2 sketches.
- Phase 10 already introduced `CoverageCheckRecord` into the live model
  surface, so `models_v2.py` can reuse that contract rather than re-declaring
  it.

### 4. Path-contract changes are localized

- `SkillPathSet` lives in `skill_pipeline/models.py`.
- `build_skill_paths()` and `ensure_output_directories()` live in
  `skill_pipeline/paths.py`.
- Existing tests in `tests/test_skill_pipeline.py` already assert prompt-path
  behavior and can be extended to cover additive v2 paths without touching
  runtime code.

## Recommended Plan Shape

### Plan 11-01
- Create `skill_pipeline/models_v2.py`
- Define `PartyRecord`, `CohortRecord`, six observation subtypes, the
  discriminated union, `DerivationBasis`, derived record types, and v2 artifact
  wrappers
- Add a focused model test file for validation and round-trip serialization

### Plan 11-02
- Add additive v2 path fields to `SkillPathSet`
- Wire them through `build_skill_paths()` and `ensure_output_directories()`
- Add path tests proving v1 paths are unchanged
- Update `CLAUDE.md` to reflect the new additive v2 path surface

## Risks

- If v2 schemas land in `models.py` instead of a dedicated module, later phases
  will couple v1 and v2 too tightly.
- If path additions silently change existing v1 values, downstream loaders and
  tests will break immediately.
