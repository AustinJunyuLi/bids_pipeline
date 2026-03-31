# Phase 15: DuckDB Integration + Export - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning
**Mode:** Auto-generated (deterministic storage and export phase)

<domain>
## Phase Boundary

Build the additive v2 persistence and export layer:

1. Load canonical v2 observations, derivations, and structured coverage checks
   into DuckDB without disturbing the v1 tables.
2. Export three v2 CSV surfaces from DuckDB:
   - `literal_observations.csv`
   - `analyst_rows.csv`
   - `benchmark_rows_expanded.csv`
3. Keep anonymous slot expansion export-only and out of the core observation
   graph and derive artifact.
4. Provide a separate legacy adapter that maps v2 analyst rows back to the
   existing 14-column v1 CSV shape for benchmark regression.
5. Expose live `db-load-v2` and `db-export-v2` CLI commands.

This phase should not change prompt composition, extraction skill docs, or real
deal migration policy.

</domain>

<decisions>
## Implementation Decisions

### Storage
- **D-01:** Extend `skill_pipeline/db_schema.py` additively with `v2_*` tables
  rather than creating a second database or replacing the v1 schema.
- **D-02:** Store polymorphic observation and derivation payload details in JSON
  columns (`type_fields`, `record_fields`) while keeping shared query fields in
  normal columns.
- **D-03:** Keep the shared `data/pipeline.duckdb` file; deal isolation remains
  keyed by `deal_slug`.

### Export
- **D-04:** `db_export_v2.py` reads only from DuckDB, not from JSON artifacts.
- **D-05:** Anonymous cohort expansion is allowed only in
  `benchmark_rows_expanded.csv`.
- **D-06:** `analyst_rows.csv` stays graph-linked and provenance-bearing;
  benchmark-parity formatting belongs either in the benchmark-expanded export or
  the legacy adapter.

### Compatibility
- **D-07:** Build the legacy adapter as a separate helper module and reuse the
  existing `db_export.py` formatting logic instead of re-implementing bidder ID,
  note, type, and date formatting rules.
- **D-08:** `db-export-v2` does not replace `db-export`; the v1 CSV path remains
  its own live surface.

</decisions>

<specifics>
## Specific Ideas

- Reuse `load_observation_artifacts(..., mode="canonical")` to consume canonical
  v2 observations plus derive outputs.
- Load `coverage_v2/coverage_findings.json` into `v2_coverage_checks` so later
  analysis can query structured gaps beside the graph.
- Query analyst rows from `v2_derivations` by `record_type = 'analyst_row'`
  rather than creating a sixth v2 table prematurely.
- Make the byte-stable legacy adapter test synthetic and deterministic before
  trusting it on migrated deals.

</specifics>

<canonical_refs>
## Canonical References

### Phase Scope
- `.planning/ROADMAP.md` — Phase 15 goal and success criteria
- `.planning/REQUIREMENTS.md` — EXPORT-01 through EXPORT-03
- `.planning/STATE.md` — Phase 14 complete; Phase 15 is next

### Existing Research
- `.planning/research/ARCHITECTURE.md` — additive DuckDB schema and triple
  export design
- `.planning/research/FEATURES.md` — benchmark-expanded anonymous expansion
  boundary
- `.planning/research/PITFALLS.md` — legacy-adapter correctness and additive
  schema warnings
- `.planning/research/STACK.md` — DuckDB JSON/array capability notes

### Runtime Surfaces
- `skill_pipeline/db_schema.py`
- `skill_pipeline/db_load.py`
- `skill_pipeline/db_export.py`
- `skill_pipeline/derive.py`
- `skill_pipeline/paths.py`
- `skill_pipeline/models_v2.py`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `db_load.py` already has the transaction and delete-and-reload pattern needed
  for additive deal loads.
- `db_export.py` already contains the live bidder ID, note, type, and date
  formatting semantics that the legacy adapter must reuse.
- `extract_artifacts_v2.py` already loads canonical observations plus optional
  derive artifacts.

### Integration Points
- `skill_pipeline/db_schema.py`
- `skill_pipeline/db_load_v2.py`
- `skill_pipeline/db_export_v2.py`
- `skill_pipeline/legacy_adapter.py`
- `skill_pipeline/cli.py`
- `tests/test_skill_db_load_v2.py`
- `tests/test_skill_db_export_v2.py`
- `tests/test_skill_pipeline.py`
- `CLAUDE.md`

</code_context>

<deferred>
## Deferred Ideas

- Prompt contract updates
- Real-deal migration and benchmark comparison
- Shared v2 verify contract
- v2-specific reconciliation workflows

</deferred>
