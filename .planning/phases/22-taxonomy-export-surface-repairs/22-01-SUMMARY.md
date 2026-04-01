# Plan 22-01 Summary

## Outcome

Expanded the additive analyst/export surface for agreement families, advisor
termination, proxy-date handling, and enterprise-value-only proposals.

## What Changed

- Extended `skill_pipeline/models_v2.py` so:
  - process observations can carry `advisor_termination`
  - analyst rows support `ib_terminated`, `nda_amendment`, `standstill`,
    `exclusivity`, and `clean_team`
  - analyst rows can carry `enterprise_value`, `date_precision`, and
    `date_sort_proxy`
- Updated `skill_pipeline/derive.py` so:
  - agreement-family observations no longer collapse to `nda`
  - advisor termination maps to `ib_terminated`
  - proposal rows preserve enterprise value
  - non-exact dates stop populating `date_recorded` and instead flow through
    `date_precision` plus `date_sort_proxy`
- Updated `skill_pipeline/db_export_v2.py` so analyst/benchmark CSVs include the
  new value and date-surface columns
- Added regression coverage in:
  - `tests/test_skill_derive.py`
  - `tests/test_skill_db_export_v2.py`

## Verification

- `pytest -q tests/test_skill_derive.py tests/test_skill_db_export_v2.py -k 'agreement or exclusivity or amendment or enterprise or proxy or advisor_termination'`
- `pytest -q tests/test_skill_derive.py tests/test_skill_gates_v2.py tests/test_skill_db_export_v2.py tests/test_skill_pipeline.py`
- `pytest -q tests/test_skill_observation_models.py tests/test_skill_extract_artifacts_v2.py tests/test_skill_canonicalize_v2.py tests/test_skill_check_v2.py tests/test_skill_coverage_v2.py tests/test_skill_gates_v2.py tests/test_skill_derive.py tests/test_skill_db_export_v2.py tests/test_skill_pipeline.py`

## Result

Phase 22 turns several previously lossy analyst/export surfaces into additive,
filing-grounded fields instead of forcing them through collapsed NDA types or
exact-date placeholders.
