---
phase: 10-pre-migration-fixes
plan: 03
subsystem: rerun-and-baseline
tags: [rerun, db-load, db-export, baseline]
requires:
  - phase: 10-pre-migration-fixes
    provides: all-cash inference fix and structured coverage contract
provides:
  - refreshed deterministic enrichment and exports for every deal matching the Phase 10 short-circuit pattern
  - documented corrected v1 baseline for the start of v2 work
affects: [phase-10 verification, .planning/STATE.md, .planning/ROADMAP.md]
tech-stack:
  added: []
  patterns:
    - rerun only deals proven to match the affected control-flow pattern, then verify diffs are constrained to the intended downstream field
key-files:
  created:
    - .planning/phases/10-pre-migration-fixes/10-03-SUMMARY.md
  modified:
    - data/skill/imprivata/enrich/deterministic_enrichment.json
    - data/skill/imprivata/export/deal_events.csv
    - data/skill/penford/enrich/deterministic_enrichment.json
    - data/skill/penford/export/deal_events.csv
    - data/skill/petsmart-inc/enrich/deterministic_enrichment.json
    - data/skill/petsmart-inc/export/deal_events.csv
    - data/skill/saks/enrich/deterministic_enrichment.json
    - data/skill/saks/export/deal_events.csv
    - data/skill/stec/enrich/deterministic_enrichment.json
    - data/skill/stec/export/deal_events.csv
    - data/pipeline.duckdb
key-decisions:
  - "The affected rerun set was determined from live cycle data, not guessed up front: imprivata, penford, petsmart-inc, saks, and stec all matched the short-circuit pattern."
  - "Phase-10 export verification uses pre/post file diffs to prove that only the Cash column changed downstream."
patterns-established:
  - "For deterministic baseline repairs, save pre-rerun generated artifacts to /tmp, rerun only the affected deals, and diff before closing the phase."
requirements-completed: [FIX-01]
duration: 11m
completed: 2026-03-31
---

# Phase 10 Plan 03: Rerun And Baseline Summary

**Re-ran every deal that actually hit the Phase 10 short-circuit pattern and verified the downstream deltas stayed strictly on the all-cash path.**

## Performance

- **Duration:** 11m
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments

- Identified the affected rerun set from live cycle data:
  `imprivata`, `penford`, `petsmart-inc`, `saks`, and `stec`.
- Re-ran `skill-pipeline enrich-core`, `skill-pipeline db-load`, and
  `skill-pipeline db-export` for those five deals.
- Verified each refreshed `deterministic_enrichment.json` changed only in the
  `all_cash_overrides` key.
- Verified each refreshed `deal_events.csv` changed only by flipping the Cash
  column from `NA` to `1` on the affected rows.
- Established the corrected Phase 10 baseline: the existing 9-deal atomic match
  rate remains `70.7% (157/222)` by inference from unchanged row counts and
  line-level export diffs that touch only the Cash column.

## Task Commits

None. The rerun updated generated artifacts inside a worktree that already had
many unrelated generated-file modifications, so no isolated commit was created.

## Verification

- `python` diff check comparing pre/post deterministic artifacts for the five
  affected deals
- `python` line diff check comparing pre/post exports for the five affected
  deals
- `pytest -q tests/test_skill_db_load.py -k all_cash`
- `pytest -q tests/test_skill_db_export.py -k all_cash`
- `pytest -q tests/test_skill_enrich_core.py tests/test_skill_coverage.py tests/test_skill_db_load.py -k 'all_cash or coverage'`

## Notes

- The benchmark-match-rate statement is an explicit inference from the export
  diffs and the current `data/reconciliation_cross_deal_analysis.md` method,
  not a fresh full `/reconcile-alex` rerun across all nine deals.
- Field-level benchmark agreement improves on the rerun deals because the Cash
  column now matches filing-grounded all-cash context more often, but the atomic
  denominator/numerator do not change when only the Cash field flips on existing
  rows.

## Self-Check: PASSED

- The affected rerun set was discovered and rerun successfully.
- Deterministic diffs are isolated to `all_cash_overrides`.
- Export diffs are isolated to Cash-column flips.

---
*Phase: 10-pre-migration-fixes*
*Completed: 2026-03-31*
