# Phase 14: Derivation Engine - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning
**Mode:** Auto-generated (logic-heavy implementation phase)

<domain>
## Phase Boundary

Build the first live deterministic derivation engine for canonical v2
observations:

1. Derive process phases, lifecycle transitions, cash regimes, judgments, and
   analyst rows from the observation graph.
2. Keep the rule catalog explicit and provenance-bearing through
   `DerivationBasis`.
3. Refuse derivation when the new Phase 13 validation artifacts are not present
   or do not pass.
4. Keep core derivation outputs graph-linked and filing-grounded; defer
   benchmark-shaped anonymous expansion and export formatting to Phase 15.
5. Write additive v2 derivation artifacts under `data/skill/<slug>/derive/`.

This phase should not load DuckDB tables, export CSVs, change prompt
composition, or migrate real deals.

</domain>

<decisions>
## Implementation Decisions

### Rule Engine Shape
- **D-01:** Create a new `skill_pipeline/derive.py` module. Do not widen
  `enrich_core.py`.
- **D-02:** Use a simple ordered rule registry that mirrors the architecture
  dependency DAG:
  - round derivation
  - exit derivation
  - cash regime derivation
  - analyst row compilation

### Validation Gate
- **D-03:** `derive.py` will require passing `check_v2`, `coverage_v2`, and
  `gates_v2` artifacts before it writes outputs.
- **D-04:** Because no shared v2 `verify.py` path exists yet, Phase 14 will not
  block on `verification_log.json`; that unresolved verify contract is recorded
  explicitly rather than hidden behind a silent fallback.

### Output Scope
- **D-05:** Phase 14 may refine `skill_pipeline/models_v2.py` additively before
  derive logic lands if a deterministic rule would otherwise have to parse
  `summary` text instead of a structured literal field.
- **D-06:** Round rules produce `ProcessPhaseRecord`; row emission for round
  announcement/deadline pairs happens during analyst-row compilation.
- **D-07:** Agreement-chain handling stays lightweight in Phase 14:
  superseding NDA-family agreements surface through analyst rows and provenance,
  not through a new standalone agreement-derived record type.
- **D-08:** `AnalystRowRecord` outputs must stay graph-linked. Prefer
  `subject_ref`, `row_count`, date/terms fields, and provenance. Export-shaped
  bidder/date/value formatting belongs to Phase 15 and the legacy adapter.
- **D-09:** Synthetic anonymous slot expansion is export-only. Phase 14 must
  not emit anonymous slot rows in `derive/derivations.json` or invent named
  bidder identities for cohort-backed observations.

### Judgment Scope
- **D-10:** Only generate `JudgmentRecord` when the engine would otherwise have
  to guess:
  - ambiguous phase classification
  - ambiguous exit state
  - initiation ambiguity
  - missing advisory linkage

### the agent's Discretion
- The exact derive-log schema, as long as it is deterministic and summarizes
  rule execution plus output counts.
- Whether phase-level cash regimes are keyed directly to `phase_id` or to an
  explicit cycle-like synthetic scope, as long as the output remains stable and
  later DuckDB loading can consume it.

</decisions>

<specifics>
## Specific Ideas

- If a derivation rule depends on missing literal structure today, add the
  smallest additive field to `models_v2.py` first rather than encoding that
  logic in `summary` parsing by default.
- Reuse v1 bidder-type formatting semantics from `db_export.py` only where they
  help preserve later export compatibility; do not let those formatting concerns
  define the core `AnalystRowRecord` contract.
- Derive round deadline rows directly from `SolicitationObservation.due_date`
  instead of forcing a second observation type for deadline events.
- Treat `StatusObservation(status_kind=\"selected_to_advance\")` as the Phase 14
  signal for screening/elimination logic.

</specifics>

<canonical_refs>
## Canonical References

### Phase Scope
- `.planning/ROADMAP.md` — Phase 14 goal and success criteria
- `.planning/REQUIREMENTS.md` — DERIVE-01 through DERIVE-06
- `.planning/STATE.md` — Phase 13 complete; derive depends on the new v2
  validation stack

### Existing Research
- `.planning/research/ARCHITECTURE.md` — derive rule catalog and dependency DAG
- `.planning/research/FEATURES.md` — initial rule mapping table and analyst-row
  expectations
- `.planning/research/STACK.md` — new-module guidance and test naming
- `.planning/research/PITFALLS.md` — explicit warning against building derive
  before validation or without a declared rule DAG

### Runtime Surfaces
- `skill_pipeline/enrich_core.py` — v1 rule analogues only
- `skill_pipeline/models_v2.py` — derived record output schema
- `skill_pipeline/check_v2.py`
- `skill_pipeline/coverage_v2.py`
- `skill_pipeline/gates_v2.py`
- `skill_pipeline/db_export.py` — bidder type and row-shape semantics to reuse
  only where they do not leak export policy back into core derivation

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `models_v2.py` already defines all required derived output records.
- `extract_artifacts_v2.py` already exposes the canonical observation graph and
  indexes.
- `db_export.py` contains the live bidder-type formatting semantics that later
  legacy export has to preserve.

### Integration Points
- `skill_pipeline/derive.py`
- `skill_pipeline/cli.py`
- `tests/test_skill_derive.py`
- `tests/test_skill_pipeline.py`
- `CLAUDE.md`

</code_context>

<deferred>
## Deferred Ideas

- DuckDB loading of derived records
- v2 triple export and legacy adapter
- shared v2 verification contract
- real-deal migration and prompt/skill updates

</deferred>
