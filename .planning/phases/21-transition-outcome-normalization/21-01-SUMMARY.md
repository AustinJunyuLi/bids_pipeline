# Plan 21-01 Summary

## Outcome

Added explicit transition dates, normalized synthetic exit timing, and made
literal outcome rows bidder-first with bounded related-date recovery.

## What Changed

- Extended `skill_pipeline/models_v2.py` so `LifecycleTransitionRecord` can
  carry an additive explicit `event_date`
- Updated `skill_pipeline/derive.py` so:
  - `EXIT-03` can prefer a related solicitation deadline, bounded by each
    subject's last active evidence
  - `EXIT-04` can prefer the last known round exit date instead of defaulting
    residual losers to the execution timestamp
  - duplicate execution drops are avoided once a bidder has already exited in an
    earlier transition
  - literal outcome rows prefer bidder or bidder-cohort refs over target-side
    refs
  - undated literal executed rows can inherit an exact-day related merger
    agreement date when the graph link is explicit
- Added focused derive regression coverage for:
  - deadline-driven `not_invited` exits
  - residual-loser `lost_to_winner` exits
  - bidder-first executed-row normalization with related merger-agreement dates

## Verification

- `pytest -q tests/test_skill_derive.py -k 'drop or outcome or executed or transition or date_recorded'`
- `pytest -q tests/test_skill_derive.py tests/test_skill_gates_v2.py tests/test_skill_db_export_v2.py tests/test_skill_pipeline.py`
- `pytest -q tests/test_skill_observation_models.py tests/test_skill_extract_artifacts_v2.py tests/test_skill_canonicalize_v2.py tests/test_skill_check_v2.py tests/test_skill_coverage_v2.py tests/test_skill_gates_v2.py tests/test_skill_derive.py tests/test_skill_db_export_v2.py tests/test_skill_pipeline.py`

## Result

Phase 21 removes the coarsest synthetic timing artifacts from derive, stops
literal executed rows from keying to target-side refs when a bidder is present,
and keeps the new behavior pinned by direct fixture tests.
