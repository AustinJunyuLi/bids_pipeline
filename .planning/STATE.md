---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Observation Graph Architecture
status: Planning Phase 16
stopped_at: Phase 15 completed; Phase 16 planning and migration next
last_updated: "2026-03-31T11:33:16Z"
progress:
  total_phases: 7
  completed_phases: 6
  total_plans: 16
  completed_plans: 16
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-31)

**Core value:** Produce the most correct filing-grounded structured deal record possible from raw text, by separating filing-literal observations from analyst-derived rows.
**Current focus:** Phase 16 — Extraction Contract + Migration

## Current Position

Phase: 16 (Extraction Contract + Migration)
Plan: Planning next

## Performance Metrics

**Velocity:**

- Total plans completed: 16 (v2.0)
- Average duration: 6.3 minutes
- Total execution time: 101 minutes

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 10 | 3 | 26m | 8.7m |
| 11 | 2 | 17m | 8.5m |
| 12 | 2 | 18m | 9.0m |
| 13 | 3 | 15m | 5.0m |
| 14 | 3 | 12m | 4.0m |
| 15 | 3 | 13m | 4.3m |

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- v2 models are additive (new files beside v1, never modify v1 classes)
- All-cash bug fix must be isolated and re-baselined before any v2 work
- STEC is the reference deal for v2 validation before 9-deal migration
- Derivation rules have an explicit dependency DAG with topological execution order
- Legacy adapter must produce byte-identical v1 CSV shape for benchmark regression
- Phase 11 registers reserved v2 artifact paths in `SkillPathSet`; these are additive scaffolding beside v1, not proof that all v2 runtime writers already exist
- Phase 12 keeps v1 and v2 artifact loaders separate and requires explicit version selection when both surfaces exist
- `canonicalize-v2` is now the live writer for canonical v2 observation artifacts under `extract_v2/`
- Phase 13 makes `check-v2`, `coverage-v2`, and `gates-v2` live canonical-v2 validation writers with observation-aware JSON report surfaces
- Phase 14 core derivation outputs must stay graph-linked; benchmark/export-shaped row formatting belongs to Phase 15
- Synthetic anonymous slot expansion is export-only; Phase 14 cohort-backed rows should preserve `subject_ref` and `row_count` rather than emit slot rows
- Phase 14 may refine `models_v2.py` additively when a deterministic rule needs structured literal fields that are missing today
- `derive` is now the live canonical-v2 derivation stage and explicitly depends on passing `check-v2`, `coverage-v2`, and `gates-v2`, not on the unresolved shared v2 verify contract
- Phase 15 keeps DuckDB additive via `v2_*` tables and stores observation/derivation subtype details in JSON payload columns
- `db-export-v2` now owns the triple export surface and keeps anonymous slot expansion confined to `benchmark_rows_expanded.csv`
- The legacy adapter reuses v1 export formatting helpers rather than duplicating bidder-ID and note logic

### Pending Todos

None yet.

### Blockers/Concerns

- CohortRecord approximate-count limitations still need real-deal validation before migration closes, especially on PetSmart-style cohorts
- Shared `verify.py` semantics for v2 remain unresolved; later phases still need to decide whether a shared v2 verify stage is worth adding beyond the current derive gate policy
- v2 extraction prompt effectiveness is highest-uncertainty deliverable (Phase 16)
- Phase 16 still has to prove the new v2 storage/export surface on STEC and the remaining 8 migrated deals

## Session Continuity

Last session: 2026-03-31
Stopped at: Phase 15 complete; Phase 16 not yet planned
Resume file: None
Next action: `$gsd-plan-phase 16`
