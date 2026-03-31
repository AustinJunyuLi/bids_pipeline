# Plan 14-01 Summary

## Outcome

Landed the gated derivation core and aligned the v2 schema for deterministic
round, cash, and judgment rules.

## What Changed

- Added `skill_pipeline/derive.py` as a new additive v2 derivation runtime
- Extended additive v2 models in `skill_pipeline/models_v2.py` for Phase 14:
  - `AgreementObservation.consideration_type`
  - `LifecycleTransitionRecord.subject_count`
  - `AnalystRowRecord.subject_ref`
  - `AnalystRowRecord.row_count`
- Extended `skill_pipeline/extract_artifacts_v2.py` so raw agreement artifacts
  can carry `consideration_type` into canonical v2 observations
- Implemented derive gating on passing `check-v2`, `coverage-v2`, and
  `gates-v2` artifacts before any output is written
- Implemented deterministic derivation for:
  - informal and formal process phases
  - phase-scoped cash regimes
  - ambiguity judgments for initiation, advisory linkage, and phase
    classification
- Added schema and derive regression coverage in:
  - `tests/test_skill_observation_models.py`
  - `tests/test_skill_derive.py`

## Verification

- `pytest -q tests/test_skill_observation_models.py tests/test_skill_derive.py -k 'phase or cash or judgment or validation or row_count or subject_ref'`
- `python -m py_compile skill_pipeline/derive.py tests/test_skill_derive.py`

## Result

Phase 14 now starts from a validation-gated, provenance-bearing derive core
instead of forcing export-shaped rules into the observation graph.
