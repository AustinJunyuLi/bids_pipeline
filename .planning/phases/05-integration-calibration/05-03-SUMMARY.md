---
phase: 05-integration-calibration
plan: 03
subsystem: database
tags: [duckdb, deal-agent, orchestration, docs, validation]
requires:
  - phase: 05-01
    provides: DuckDB db-load/db-export stages, shared database path, and stage summary models
  - phase: 05-02
    provides: compose-prompts routing and expanded event examples used by the orchestration contract
affects: [deal-agent, runtime-docs, db-validation]
provides:
  - deal-agent summary fields for db_load and db_export stage status
  - authoritative CLAUDE and deal-agent workflow docs for db-load and db-export
  - stec deterministic db-load/db-export validation plus an active 9-deal batch report
tech-stack:
  added: []
  patterns:
    - deal-agent reports db stage health from shared artifacts instead of invoking stages directly
    - deal-agent skill docs stay synchronized across .claude, .codex, and .cursor mirrors
    - integration validation stays scoped to the active 9-deal calibration roster even when seeds.csv is larger
key-files:
  created: []
  modified:
    - skill_pipeline/deal_agent.py
    - skill_pipeline/models.py
    - CLAUDE.md
    - .claude/skills/deal-agent/SKILL.md
    - tests/test_skill_pipeline.py
    - tests/test_runtime_contract_docs.py
key-decisions:
  - "deal-agent summarizes db-load and db-export from on-disk DuckDB/CSV artifacts instead of trying to execute those stages itself."
  - "Benchmark-boundary docs now describe db-export as the deterministic export contract while preserving explicit pre-/export-csv wording for legacy/manual workflows and policy tests."
  - "Batch validation for this plan uses the active 9-deal calibration set from PROJECT.md because data/seeds.csv now contains 401 rows outside the phase scope."
patterns-established:
  - "Summary contract: db_load reports actor/event/span row counts; db_export reports exported event row count and output path."
  - "Documentation contract: update .claude/skills first, then sync .codex/.cursor mirrors and rerun runtime-policy tests."
requirements-completed: [DB-02]
duration: 19m
completed: 2026-03-28
---

# Phase 5 Plan 3: Orchestration Wiring Summary

**Deal-agent db_load/db_export stage summaries with synced orchestration docs and stec DuckDB export validation**

## Performance

- **Duration:** 19m
- **Started:** 2026-03-28T18:16:00Z
- **Completed:** 2026-03-28T18:35:04Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Added `db_load` and `db_export` to `DealAgentSummary` and taught `deal-agent` to summarize DuckDB row counts plus exported CSV row counts from shared artifacts.
- Updated `CLAUDE.md`, the canonical `deal-agent` skill doc, and the synced skill mirrors so the documented runtime flow now includes `db-load` and `db-export` after `enrich-core`.
- Validated the deterministic db pipeline on `stec` end-to-end and produced a pass/skip batch report for the active 9-deal calibration roster.

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire db-load and db-export into deal-agent summary and update DealAgentSummary model** - `f96776a` (feat)
2. **Task 2: Update orchestration docs and validate stec end-to-end** - `c391939` (chore)

## Files Created/Modified
- `skill_pipeline/deal_agent.py` - adds `db_load` and `db_export` summarizers and wires them into `run_deal_agent()`.
- `skill_pipeline/models.py` - extends `DealAgentSummary` with `DbLoadStageSummary` and `DbExportStageSummary` fields.
- `tests/test_skill_pipeline.py` - upgrades deal-agent fixtures to include DuckDB + CSV outputs and asserts the new summary fields.
- `CLAUDE.md` - documents `db-load`/`db-export` in the runtime split, artifact contract, end-to-end flow, benchmark boundary, and command list.
- `.claude/skills/deal-agent/SKILL.md` - updates the canonical local-agent procedure and skill table with deterministic db stages.
- `.codex/skills/deal-agent/SKILL.md` - synced mirror of the canonical deal-agent workflow.
- `.cursor/skills/deal-agent/SKILL.md` - synced mirror of the canonical deal-agent workflow.
- `tests/test_runtime_contract_docs.py` - adds runtime-contract assertions for the DuckDB export stages and their placement in `CLAUDE.md`.

## Decisions Made
- Deal-agent remains a thin status surface: it reports db-stage health from persisted artifacts rather than invoking `db-load`/`db-export` itself.
- The runtime docs now treat `db-export` as the deterministic export contract, but they preserve the explicit `/export-csv` benchmark boundary language required by the repo’s policy tests and legacy/manual workflow docs.
- Plan validation stays scoped to the active 9-deal calibration roster from `PROJECT.md`; the larger 401-row `data/seeds.csv` file is no longer the right corpus for this phase.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Kept db-stage summary checks fail-fast instead of swallowing DuckDB errors**
- **Found during:** Task 1
- **Issue:** The plan’s example implementation used a broad exception fallback for db summary status, which would have hidden corrupted or schema-drifted DuckDB state and violated the repo’s fail-fast rules.
- **Fix:** Implemented explicit missing/partial-row checks for `db_load` and let unexpected database/query failures surface normally.
- **Files modified:** `skill_pipeline/deal_agent.py`
- **Verification:** `python -m pytest tests/test_skill_pipeline.py -x -q && python -m pytest -q --tb=short`
- **Committed in:** `f96776a`

**2. [Rule 1 - Regression] Restored explicit `/export-csv` benchmark-boundary wording after policy tests failed**
- **Found during:** Task 2
- **Issue:** The first docs pass moved the benchmark boundary entirely to `db-export`, which broke the repository’s benchmark-separation regression test expecting explicit pre-`/export-csv` language in generation docs.
- **Fix:** Added compatibility wording to `CLAUDE.md` and the deal-agent skill docs while keeping `db-export` documented as the deterministic export contract, then resynced the `.codex` and `.cursor` mirrors.
- **Files modified:** `CLAUDE.md`, `.claude/skills/deal-agent/SKILL.md`, `.codex/skills/deal-agent/SKILL.md`, `.cursor/skills/deal-agent/SKILL.md`
- **Verification:** `python -m pytest tests/test_runtime_contract_docs.py -x -q && python -m pytest -q --tb=short`
- **Committed in:** `c391939`

### Plan Scope Adjustment

- The plan’s inline batch-validation sketch assumed `data/seeds.csv` represented the 9-deal corpus. In the current repo it contains 401 rows, so validation was run against the active 9-deal calibration set from `PROJECT.md`: `imprivata`, `mac-gray`, `medivation`, `penford`, `petsmart-inc`, `providence-worcester`, `saks`, `stec`, and `zep`.
- Result: `stec` passed `db-load` and `db-export`; the other eight active deals were reported as `SKIP` because they lack the canonical extract and/or deterministic enrichment prerequisites needed for deterministic DB loading.
- Generated `deal_events.csv` files and `data/pipeline.duckdb` were backed up and restored around validation so the task commit stayed docs-only.

---

**Total deviations:** 2 auto-fixes, 1 scope adjustment
**Impact on plan:** All adjustments were necessary to keep the implementation aligned with repo rules and live corpus scope. No product-scope expansion was introduced.

## Issues Encountered
- The new runtime-contract assertions initially failed on newline-sensitive and whole-file position checks; the tests were tightened to look at normalized text and the `End-To-End Flow` section specifically.
- The full suite then surfaced the repo-wide benchmark-boundary policy requirement, which required explicitly preserving the legacy `/export-csv` wording alongside the new `db-export` contract.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `skill-pipeline deal-agent --deal stec` now reports `db_load.status=pass` and `db_export.status=pass` with row counts from the shared deterministic artifacts.
- The authoritative docs and synced skill mirrors now document the intended `enrich-core -> db-load -> db-export` sequence.
- A full 9/9 deterministic db batch still requires canonical extract artifacts plus `deterministic_enrichment.json` for the other eight active deals; this plan added the validation/reporting path but did not regenerate those prerequisites.

---
*Phase: 05-integration-calibration*
*Completed: 2026-03-28*

## Self-Check: PASSED
- Found `.planning/phases/05-integration-calibration/05-03-SUMMARY.md`
- Verified task commits `f96776a` and `c391939` in `git log --oneline --all`
