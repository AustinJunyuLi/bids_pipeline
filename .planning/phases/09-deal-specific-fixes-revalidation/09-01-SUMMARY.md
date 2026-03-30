---
phase: 09-deal-specific-fixes-revalidation
plan: 01
subsystem: extraction-pipeline
tags: [zep, extract-deal, canonicalize, db-export]
requires:
  - phase: 08-extraction-guidance-enrichment-extensions
    provides: updated extraction guidance for NDA exclusions, verbal proposals, and round milestones used during the Zep rerun
provides:
  - refreshed Zep actor and event extracts without New Mountain Capital in grouped 2014 proposal and drop events
  - regenerated canonical QA artifacts for Zep through check, verify, coverage, and gates
  - refreshed deterministic enrichment and DuckDB-exported Zep event CSV
affects: [medivation-rerun, reconciliation, phase-09 verification]
tech-stack:
  added: []
  patterns:
    - extraction-forward reruns delete downstream deal artifacts, preserve raw/source inputs, and rerun canonicalize through db-export from fresh extracts
key-files:
  created:
    - .planning/phases/09-deal-specific-fixes-revalidation/09-01-SUMMARY.md
  modified:
    - data/skill/zep/extract/actors_raw.json
    - data/skill/zep/extract/events_raw.json
    - data/skill/zep/extract/spans.json
    - data/skill/zep/gates/gates_report.json
    - data/skill/zep/export/deal_events.csv
    - data/pipeline.duckdb
key-decisions:
  - "Zep was repaired by a clean extraction-forward rerun instead of hand-editing canonical artifacts."
  - "Coverage and gate warnings were kept as warnings because check, verify, and gates all returned pass status with zero blockers."
patterns-established:
  - "Deal-specific reruns should stay benchmark-blind until db-export completes, then hand reconciliation to the post-export validation step."
requirements-completed: [EXTRACT-04, RERUN-01]
duration: 21m
completed: 2026-03-30
---

# Phase 09 Plan 01: Zep Rerun Summary

**Re-extracted Zep with corrected 2014 bidder groupings, then regenerated its canonical QA, enrichment, and DuckDB export artifacts from the refreshed extract.**

## Performance

- **Duration:** 21m
- **Started:** 2026-03-30T15:41:00+01:00
- **Completed:** 2026-03-30T16:02:16+01:00
- **Tasks:** 2
- **Files modified:** 17

## Accomplishments

- Regenerated Zep quote-first extracts with 8 actors and 18 events, and removed `bidder_new_mountain_capital` from grouped 2014 proposal and drop events.
- Canonicalized the refreshed extract and reran check, verify, coverage, gates, enrich-core, db-load, and db-export without blocker findings.
- Restored the full downstream artifact chain needed for Phase 09 reconciliation, including deterministic enrichment and the DuckDB-backed `deal_events.csv`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Clean Zep downstream artifacts and re-extract** - `147c9f9` (fix)
2. **Task 2: Run Zep full deterministic pipeline through db-export** - `95e1797` (fix)

## Files Created/Modified

- `data/skill/zep/extract/actors_raw.json` - Refreshed actor roster grounded in the Phase 08 extraction contract.
- `data/skill/zep/extract/events_raw.json` - Refreshed event list with corrected grouped 2014 proposal/drop actor sets.
- `data/skill/zep/extract/spans.json` - Canonical span registry produced during canonicalize.
- `data/skill/zep/gates/gates_report.json` - Regenerated gates output with warnings only and zero blockers.
- `data/skill/zep/enrich/deterministic_enrichment.json` - Refreshed deterministic classifications, rounds, and cycle metadata.
- `data/skill/zep/export/deal_events.csv` - Refreshed DuckDB-derived export for downstream reconciliation.
- `data/pipeline.duckdb` - Reloaded Zep deal rows used for the refreshed export.

## Decisions Made

- Used a clean extraction-forward rerun instead of patching existing Zep artifacts by hand.
- Accepted the regenerated coverage and gate warnings because the reports stayed in `pass` status with zero blockers and no verify findings.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The executor completed the artifact work and both task commits but never returned a completion signal or wrote the summary. The orchestrator confirmed success via artifact and git spot-checks, then wrote this summary and bookkeeping metadata.

## Verification

- `python - <<'PY' ...` check confirming no grouped 2014 `proposal` or `drop` event contains `bidder_new_mountain_capital`
- Verified `data/skill/zep/extract/spans.json`, `data/skill/zep/check/check_report.json`, `data/skill/zep/verify/verification_findings.json`, `data/skill/zep/coverage/coverage_summary.json`, `data/skill/zep/gates/gates_report.json`, `data/skill/zep/enrich/deterministic_enrichment.json`, and `data/skill/zep/export/deal_events.csv` all exist
- Confirmed `check_report.json` has `blocker_count: 0`, `verification_findings.json` has no findings, and `gates_report.json` has `blocker_count: 0`

## Self-Check: PASSED

- Verified the EXTRACT-04 acceptance gate: no grouped 2014 Zep `proposal` or `drop` event includes New Mountain Capital.
- Verified the full deterministic chain completed through `db-export` and produced the expected artifacts on disk.
- Verified Zep is ready for the Phase 09 reconciliation plan.

---
*Phase: 09-deal-specific-fixes-revalidation*
*Completed: 2026-03-30*
