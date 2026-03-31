---
gsd_state_version: 1.0
milestone: v2.1
milestone_name: V2 Default Cutover + Legacy Archive
status: Phase 19 complete
stopped_at: v2 is the live default; v1 artifacts are archived under data/legacy/v1; live DuckDB rebuilt from v2 only
last_updated: "2026-03-31T22:00:00Z"
progress:
  total_phases: 3
  completed_phases: 3
  total_plans: 3
  completed_plans: 3
---

# Project State

## Project Reference

See: `.planning/PROJECT.md` and `.planning/ROADMAP.md`

**Core value:** Produce the most correct filing-grounded structured deal record
possible from raw text, with the observation-graph v2 contract as the live
default.

## Current Position

Milestone: `v2.1 V2 Default Cutover + Legacy Archive`
Phase: `19`
Plan: Complete

## Decisions In Force

- v2 is the live default workflow and benchmark boundary
- `/deal-agent` and `/reconcile-alex` now refer to the v2 path
- v1 survives only under explicit legacy skill names
- archived v1 skill outputs live under `data/legacy/v1/`
- `data/pipeline.duckdb` is the rebuilt live v2 database; the pre-cutover file is preserved separately
- `migrate-extract-v1-to-v2` remains historical backfill support only

## Pending Todos

None recorded.

## Blockers / Concerns

- Legacy runtime commands still exist in `skill_pipeline/`; they are preserved for explicit legacy use and should not be mistaken for the live default.
- Future milestone planning should decide whether any legacy code can be removed or whether long-term dual support is required.

## Session Continuity

Last session: 2026-03-31
Stopped at: v2 default cutover complete
Next action: define the next milestone after cutover
