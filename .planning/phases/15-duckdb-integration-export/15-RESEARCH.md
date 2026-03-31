# Phase 15: DuckDB Integration + Export - Research

**Date:** 2026-03-31
**Status:** Complete

## Findings

### 1. The safest schema change is additive `v2_*` tables in the existing DuckDB file

- `db_schema.py` already uses idempotent `CREATE TABLE IF NOT EXISTS` and
  additive `ALTER TABLE` patterns.
- `STACK.md` confirms DuckDB JSON and array columns are sufficient for
  polymorphic observations and derivations.
- Replacing or mutating the v1 tables would create avoidable migration risk.

### 2. The export boundary is three CSVs, not one overloaded surface

- `FEATURES.md` makes the split explicit:
  - `literal_observations.csv` for filing audit
  - `analyst_rows.csv` for graph-linked analytical rows
  - `benchmark_rows_expanded.csv` for export-only anonymous expansion
- This phase should preserve that separation instead of collapsing back into one
  benchmark-shaped file.

### 3. The legacy adapter should reuse `db_export.py`, not clone its formatting rules

- `PITFALLS.md` calls out bidder ID assignment, note formatting, and date
  formatting as easy sources of subtle benchmark drift.
- The lowest-risk path is to map v2 analyst rows into the pseudo-event shape
  expected by `_build_event_rows()` and let the existing exporter format the
  14-column CSV.

### 4. The derive artifact is already sufficient for Phase 15 if row IDs stay globally unique

- `db_load_v2` needs stable identifiers for `v2_derivations`.
- The Phase 15 integration work surfaced the need to renumber analyst rows once
  after concatenating literal, phase, and transition row families.

## Recommended Plan Shape

### Plan 15-01
- Extend DuckDB schema additively and implement `db_load_v2`
- Load parties, cohorts, observations, derivations, and coverage checks

### Plan 15-02
- Implement `db_export_v2`
- Write the triple export surface
- Keep anonymous slot expansion benchmark-only

### Plan 15-03
- Implement the legacy adapter on top of the v1 export formatter
- Add CLI wiring, parser coverage, repo-memory updates, and regression tests

## Risks

- If `db_load_v2` mutates the v1 tables, the existing 9-deal regression corpus
  becomes harder to trust.
- If benchmark expansion leaks into `derive/derivations.json`, the graph model
  starts carrying synthetic identities as if they were filing facts.
- If the legacy adapter diverges from `db_export.py`, benchmark diffs stop being
  attributable to extraction versus formatting.
