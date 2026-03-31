# Plan 14-02 Summary

## Outcome

Finished the transition rules and graph-linked analyst-row compilation needed
for later DuckDB/export work.

## What Changed

- Extended `skill_pipeline/derive.py` with lifecycle transition rules for:
  - literal withdrawal and non-participation
  - cannot-improve exits
  - not-invited eliminations
  - lost-to-winner closeout transitions
- Made transition identifiers deterministic across repeated runs
- Compiled graph-linked analyst rows from:
  - literal process observations
  - NDA-family agreements, including supersession review flags
  - proposals with phase-aware bid typing and cash regime propagation
  - derived round announcement and deadline rows
  - derived drop rows from lifecycle transitions
- Preserved cohort-backed rows as `subject_ref` plus `row_count` without
  anonymous slot expansion
- Added focused transition and row regression coverage in
  `tests/test_skill_derive.py`

## Verification

- `pytest -q tests/test_skill_derive.py -k 'exit or analyst or agreement or row_count or subject_ref'`

## Result

The derive artifact now carries the analyst-row surface Phase 15 needs while
preserving the graph boundary and provenance.
