# Roadmap: Filing-Grounded Pipeline Redesign

## Milestones

- **v1.0 Filing-Grounded Pipeline Redesign** -- Phases 1-5 (shipped 2026-03-28) -- [archive](milestones/v1.0-ROADMAP.md)
- **v1.1 Reconciliation + Execution-Log Quality Fixes** -- Phases 6-9 (complete 2026-03-30)
- **v2.0 Observation Graph Architecture** -- Phases 10-16 (shipped 2026-03-31) -- [archive](milestones/v2.0-ROADMAP.md)
- **v2.1 V2 Default Cutover + Legacy Archive** -- Phases 17-19 (complete 2026-03-31)

## Current Milestone

### v2.1 V2 Default Cutover + Legacy Archive

- [x] **Phase 17: Default Surface Cutover** - make `/deal-agent`, `/reconcile-alex`, `CLAUDE.md`, and live docs point at the v2 workflow; preserve v1 only under explicit legacy names
- [x] **Phase 18: Legacy Archive + Live Data Reset** - archive v1 skill outputs to `data/legacy/v1/`, preserve the pre-cutover DuckDB file, and rebuild the live database from v2 artifacts only
- [x] **Phase 19: Clean Rerun Orchestration + Release Hygiene** - document the clean v2 rerun contract, sync skill mirrors, and tighten repo tests around the live/legacy split

## Phase Details

### Phase 17: Default Surface Cutover
**Goal**: The repo's live documentation and skill surface unambiguously describe v2 as the default workflow.
**Depends on**: Phase 16 complete
**Success Criteria**:
  1. `/deal-agent` documents the live v2 rerun flow through `db-export-v2`
  2. `/deal-agent-legacy` and `/reconcile-alex-legacy` preserve the retired v1 paths
  3. `CLAUDE.md`, `docs/design.md`, and planning docs stop presenting v1 as the live default

### Phase 18: Legacy Archive + Live Data Reset
**Goal**: v1 results are stored away from the live working surface so future reruns and reconciliations are not confused by mixed contracts.
**Depends on**: Phase 17
**Success Criteria**:
  1. v1 skill outputs move to `data/legacy/v1/skill/<slug>/...`
  2. `data/legacy/v1/pipeline_precutover.duckdb` preserves the pre-cutover database
  3. the live `data/pipeline.duckdb` file is rebuilt from v2 artifacts only

### Phase 19: Clean Rerun Orchestration + Release Hygiene
**Goal**: the live repo is tidy enough that another agent can rerun or reconcile v2 without ambiguous guidance.
**Depends on**: Phase 18
**Success Criteria**:
  1. `/deal-agent` explicitly describes the clean-rerun overwrite behavior for live v2 results
  2. `.codex/skills/` and `.cursor/skills/` are synced mirrors of `.claude/skills/`
  3. tests enforce the live v2 benchmark boundary and legacy archive split

## Progress

| Phase | Milestone | Status | Completed |
|-------|-----------|--------|-----------|
| 17. Default Surface Cutover | v2.1 | Complete | 2026-03-31 |
| 18. Legacy Archive + Live Data Reset | v2.1 | Complete | 2026-03-31 |
| 19. Clean Rerun Orchestration + Release Hygiene | v2.1 | Complete | 2026-03-31 |

---
*Roadmap refreshed: 2026-03-31 after v2 default cutover*
