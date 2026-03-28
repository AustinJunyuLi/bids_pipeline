---
phase: 05-integration-calibration
plan: 01
subsystem: database
tags: [duckdb, csv, cli, testing]
requires:
  - phase: 04-enhanced-gates
    provides: canonical extract artifacts and deterministic enrich-core outputs
provides:
  - Shared DuckDB schema for actors, events, spans, enrichment, cycles, and rounds
  - Per-deal db-load stage with transactional drop-and-reload semantics
  - Deterministic db-export CSV generation from DuckDB queries
affects: [05-03-plan, deal-agent, export-workflow]
tech-stack:
  added: [duckdb]
  patterns: [multi-deal DuckDB store, transactional deal reloads, SQL-backed CSV export]
key-files:
  created: [skill_pipeline/db_schema.py, skill_pipeline/db_load.py, skill_pipeline/db_export.py, tests/test_skill_db_load.py, tests/test_skill_db_export.py]
  modified: [pyproject.toml, skill_pipeline/models.py, skill_pipeline/paths.py, skill_pipeline/cli.py]
key-decisions:
  - "The canonical database lives at data/pipeline.duckdb and is exposed through SkillPathSet.database_path."
  - "db-load deletes and reloads all deal-scoped rows inside one DuckDB transaction instead of doing partial upserts."
  - "db-export writes the two-row deal header followed by 14-column event rows generated directly from DuckDB queries."
patterns-established:
  - "Stage modules own their own DuckDB access: open_pipeline_db() centralizes schema creation and read-only access."
  - "Interpretive enrichment overlays must be able to create event rows when deterministic enrichment has no matching record."
requirements-completed: [DB-01, DB-03]
duration: 8 min
completed: 2026-03-28
---

# Phase 5 Plan 01: DuckDB Canonical Store Summary

**DuckDB-backed canonical store with transactional db-load ingestion and deterministic db-export CSV generation**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-28T18:05:06Z
- **Completed:** 2026-03-28T18:13:05Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Added the shared DuckDB schema and canonical `db-load` stage for actors, events, spans, enrichment, cycles, and rounds.
- Added deterministic `db-export` CSV generation from DuckDB with the export skill’s header, bidder ID ordering, and date/null formatting rules.
- Added focused regression suites for both stages and kept the full pytest suite green.

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: db-load tests** - `9680f2c` (`test`)
2. **Task 1 GREEN: db-load implementation** - `74fa07d` (`feat`)
3. **Task 2 RED: db-export tests** - `5bf0abe` (`test`)
4. **Task 2 GREEN: db-export implementation** - `6daacd6` (`feat`)

## Files Created/Modified
- `skill_pipeline/db_schema.py` - DuckDB DDL and connection helper.
- `skill_pipeline/db_load.py` - Canonical artifact ingestion with transactional deal reloads.
- `skill_pipeline/db_export.py` - DuckDB query layer and CSV export formatter.
- `skill_pipeline/models.py` - `database_path`, `DbLoadStageSummary`, and `DbExportStageSummary`.
- `skill_pipeline/paths.py` - Shared `data/pipeline.duckdb` path exposure.
- `skill_pipeline/cli.py` - Minimal `db-load` and `db-export` parser/dispatch wiring.
- `tests/test_skill_db_load.py` - Schema, load, gating, reload, and CLI regression tests.
- `tests/test_skill_db_export.py` - Header, bidder ID, date formatting, null handling, and CLI regression tests.
- `pyproject.toml` - Declared `duckdb>=1.2` as a project dependency.

## Decisions Made
- Used a single multi-deal DuckDB file at `data/pipeline.duckdb`, matching the phase constraint and keeping per-deal state isolated by `deal_slug`.
- Kept `cli.py` changes narrowly scoped to the `db-load` and `db-export` subcommands to avoid conflict with parallel plan 05-02 work.
- Modeled export formatting in Python on top of DuckDB queries instead of trying to push the full review contract into one SQL statement.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Interpretive drop overlays create standalone enrichment rows**
- **Found during:** Task 1 (db-load implementation)
- **Issue:** The written overlay step only updated existing deterministic enrichment rows. Drop classifications target drop events, while deterministic bid classifications target proposal events, so required dropout labels would be lost.
- **Fix:** `db-load` now creates an enrichment row when an interpretive `dropout_classifications` entry has no deterministic match, preserving `dropout_label` and `dropout_basis` for export.
- **Files modified:** `skill_pipeline/db_load.py`
- **Verification:** `python -m pytest tests/test_skill_db_load.py -x -q`
- **Committed in:** `74fa07d`

---

**Total deviations:** 1 auto-fixed (1 Rule 1 bug)
**Impact on plan:** Required for correctness. Without it, drop-event enrichment could not be represented in DuckDB or exported downstream.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `skill-pipeline db-load --deal <slug>` and `skill-pipeline db-export --deal <slug>` are available for orchestration wiring in 05-03.
- The shared DuckDB path and regression coverage are in place for downstream end-to-end pipeline integration.

---
*Phase: 05-integration-calibration*
*Completed: 2026-03-28*

## Self-Check: PASSED
- FOUND: `.planning/phases/05-integration-calibration/05-01-SUMMARY.md`
- FOUND: `9680f2c`
- FOUND: `74fa07d`
- FOUND: `5bf0abe`
- FOUND: `6daacd6`
