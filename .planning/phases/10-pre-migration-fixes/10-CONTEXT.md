# Phase 10: Pre-Migration Fixes - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Ship the v1-only pre-migration fixes that must land before any observation-graph
implementation begins:

1. Fix the `_infer_all_cash_overrides()` short-circuit so existing v1
   re-baselines are attributable.
2. Upgrade deterministic coverage outputs from ad hoc finding records to a
   structured `CoverageCheckRecord` contract with explicit status and reason
   codes.
3. Re-run the affected benchmark/export surface after the bug fix so the v2
   migration starts from a corrected baseline.

This phase does not add any v2 models, paths, loaders, or CLI commands. It
only touches the current v1 runtime and its generated artifacts.

</domain>

<decisions>
## Implementation Decisions

### v1 Isolation
- **D-01:** Treat Phase 10 as a standalone v1 patch. No `models_v2.py`,
  `extract_v2/`, `export_v2/`, or additive v2 schema work lands here.
- **D-02:** The all-cash change must stay narrowly scoped to
  `_infer_all_cash_overrides()` and its direct regression coverage. If a rerun
  changes unrelated deterministic fields, treat that as a bug.

### Structured Coverage Contract
- **D-03:** Add a typed `CoverageCheckRecord` to the live v1 model surface and
  have the coverage stage emit structured records with explicit
  `status`/`reason_code`/supporting-reference fields.
- **D-04:** Keep the current coverage stage gating behavior (`coverage_summary`
  and enrich-core pass/fail semantics) intact while changing the detail-record
  contract.
- **D-05:** Do not expand Phase 10 into a full extraction-contract rewrite.
  `coverage_notes` on extract artifacts can remain a separate upstream concern
  until the v2 extraction contract lands.

### Baseline Re-Measurement
- **D-06:** Respect the benchmark boundary: benchmark and reconciliation
  materials are post-export only. Run deterministic pipeline stages first,
  then benchmark comparison.
- **D-07:** Re-baselining is allowed to regenerate generated artifacts under
  `data/skill/<slug>/` and `data/pipeline.duckdb`, but raw filing text under
  `raw/<slug>/filings/` remains immutable.

### the agent's Discretion
- Exact structured field names beyond the required `CoverageCheckRecord`
  semantics, as long as downstream records are explicit and auditable.
- Whether the all-cash regression test is synthetic, fixture-backed, or both,
  as long as it reproduces the executed-without-type short-circuit and preserves
  the Providence guardrail.

</decisions>

<specifics>
## Specific Ideas

- The concrete all-cash failure is already visible in `saks`: proposals
  `evt_008`, `evt_009`, `evt_015`, `evt_016`, and `evt_019` have null
  `consideration_type`, earlier typed proposals are cash, and `evt_020`
  (`executed`) has no consideration type, which currently suppresses fallback
  inference.
- `providence-worcester` remains the negative guardrail: a single typed cash
  proposal among many untyped proposals must not imply an all-cash cycle.
- The current coverage stage already has good cue detection; the work is mostly
  replacing the output model and preserving the summary gate.

</specifics>

<canonical_refs>
## Canonical References

### Phase Scope
- `.planning/ROADMAP.md` — Phase 10 goal, FIX-01/FIX-02 mapping, and success
  criteria
- `.planning/REQUIREMENTS.md` — explicit requirement statements for FIX-01 and
  FIX-02
- `.planning/PROJECT.md` — isolation requirement for the pre-migration v1 patch

### Existing Research
- `.planning/research/PITFALLS.md` — exact description of the all-cash
  short-circuit bug and its isolation rationale
- `.planning/research/FEATURES.md` — structured `CoverageCheckRecord` contract
- `.planning/research/ARCHITECTURE.md` — confirms Phase 10 should remain a
  small v1 fix before v2 work

### Runtime Surfaces
- `skill_pipeline/enrich_core.py` — current all-cash inference logic
- `skill_pipeline/coverage.py` — current deterministic coverage cue audit
- `skill_pipeline/models.py` — live v1 models and coverage artifact types
- `skill_pipeline/db_load.py` / `skill_pipeline/db_export.py` — downstream
  consumers of `all_cash_overrides`
- `.claude/skills/reconcile-alex/SKILL.md` — post-export benchmark comparison

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_infer_all_cash_overrides()` already contains the intended fallback path; the
  concrete bug is the early `continue` when an executed event exists without
  cash terms.
- `coverage.py` already centralizes cue detection, overlap checks, and summary
  generation, so structured coverage can land without touching preprocess or
  extraction stages.
- `CoverageSummary` is the only runtime coverage artifact consumed outside the
  coverage stage gate, which keeps the contract change localized.

### Integration Points
- `tests/test_skill_enrich_core.py` for all-cash regression coverage
- `tests/test_skill_coverage.py` for structured coverage contract tests
- `data/skill/*/enrich/deterministic_enrichment.json` and
  `data/skill/*/export/deal_events.csv` for the post-fix baseline rerun

</code_context>

<deferred>
## Deferred Ideas

- Full v2 observation-graph models, path additions, and CLI commands
- Replacing extract-artifact `coverage_notes` with structured coverage on the
  extraction side
- Process-level all-cash derivation beyond the narrow Phase 10 short-circuit fix

</deferred>
