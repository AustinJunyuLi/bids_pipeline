# Plan 20-01 Summary

## Outcome

Landed chronology-safe proposal phase resolution, proposal-local bid-type
inference, and matching v2 semantic gates for malformed proposal-request links.

## What Changed

- Updated `skill_pipeline/derive.py` so proposal association:
  - trusts `requested_by_observation_id` only when it points to a solicitation
    on or before the proposal date
  - otherwise falls back to the latest same-day-or-earlier solicitation
- Added bounded proposal-local `bid_type` inference that:
  - treats draft-markup and merger-agreement signals as hard-formal
  - treats explicit non-binding / IOI language conservatively
  - falls back to phase kind only when local cues stay inconclusive
- Extended `skill_pipeline/gates_v2.py` with blockers for:
  - proposal links that point to a non-solicitation observation
  - proposal links that point forward in time
- Added focused regression coverage in:
  - `tests/test_skill_derive.py`
  - `tests/test_skill_gates_v2.py`

## Verification

- `pytest -q tests/test_skill_derive.py tests/test_skill_gates_v2.py -k 'proposal or link or bid_type or formality or future or solicitation'`
- `pytest -q tests/test_skill_derive.py tests/test_skill_gates_v2.py`
- `pytest -q tests/test_skill_observation_models.py tests/test_skill_extract_artifacts_v2.py tests/test_skill_canonicalize_v2.py tests/test_skill_check_v2.py tests/test_skill_coverage_v2.py tests/test_skill_gates_v2.py tests/test_skill_derive.py tests/test_skill_pipeline.py`

## Result

Phase 20 removes the most obvious proposal chronology failure mode from derive,
improves late-stage bid-type classification without benchmark-driven heuristics,
and makes malformed proposal links fail at the v2 gate layer before export.
