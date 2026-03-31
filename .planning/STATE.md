---
gsd_state_version: 1.0
milestone: v2.0
milestone_name: Observation Graph Architecture
status: Phase 16 complete
stopped_at: Phase 16 completed across all 9 deals; milestone follow-up audit/cleanup remains optional
last_updated: "2026-03-31T17:45:00Z"
progress:
  total_phases: 7
  completed_phases: 7
  total_plans: 19
  completed_plans: 19
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-31)

**Core value:** Produce the most correct filing-grounded structured deal record possible from raw text, by separating filing-literal observations from analyst-derived rows.
**Current focus:** Milestone wrap-up after Phase 16 completion

## Current Position

Phase: 16 (Extraction Contract + Migration)
Plan: Complete

## Performance Metrics

**Velocity:**

- Total plans completed: 19 (v2.0)
- Average duration: 6.5 minutes
- Total execution time: 124 minutes

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 10 | 3 | 26m | 8.7m |
| 11 | 2 | 17m | 8.5m |
| 12 | 2 | 18m | 9.0m |
| 13 | 3 | 15m | 5.0m |
| 14 | 3 | 12m | 4.0m |
| 15 | 3 | 13m | 4.3m |
| 16 | 3 | 23m | 7.7m |

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
- Phase 16 adds a separate `compose-prompts --contract v2 --mode observations` path that writes under `prompt_v2/`
- `migrate-extract-v1-to-v2` is the deterministic bridge used during migration to bootstrap `extract_v2/observations_raw.json` from canonical v1 extracts
- Literal `status.expressed_interest` now compiles to `bidder_interest` analyst rows, and solicitation observations with `other_detail` mentioning extension compile to `final_round_ext_*`
- v2 coverage now ignores unsupported cue severities and treats multi-match NDA cues as covered when they resolve to multiple canonical NDA observations rather than a missing or ambiguous literal fact

### Pending Todos

None yet.

### Blockers/Concerns

- Shared `verify.py` semantics for v2 remain unresolved; later work can decide whether a shared v2 verify stage is worth adding beyond the current derive gate policy
- Legacy-adapter benchmark output is intentionally not byte-identical on migrated deals; row-count deltas now expose literal bidder-interest recovery, selected-to-advance structure, and cohort-backed anonymous participation that v1 flattened away

## Session Continuity

Last session: 2026-03-31
Stopped at: Phase 16 complete across the 9-deal corpus
Resume file: None
Next action: optional milestone audit / cleanup
