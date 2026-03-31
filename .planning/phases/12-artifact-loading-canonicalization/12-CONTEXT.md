# Phase 12: Artifact Loading + Canonicalization - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Enable the first live v2 runtime path after the Phase 11 schema scaffolding:

1. Load v2 observation artifacts from `extract_v2/` without contaminating the
   existing v1 loader path.
2. Add a `canonicalize-v2` command that upgrades quote-first v2 observation
   artifacts into canonical span-backed artifacts using the existing span
   resolution machinery.

This phase should not implement v2 validation gates, derivation logic, DuckDB
loading, export, or extraction-skill changes.

</domain>

<decisions>
## Implementation Decisions

### Loader Boundary
- **D-01:** Keep the v1 loader (`extract_artifacts.py`) intact. Add a separate
  v2 loader module rather than extending the existing three-way v1
  quote-first/canonical logic.
- **D-02:** Provide a small version-router helper for `v1` / `v2` / `both` /
  `none` detection at the file-system level, but require an explicit version
  choice when both artifact families exist on disk.

### Raw vs Canonical v2 Shape
- **D-03:** Treat canonical v2 artifacts as `ObservationArtifactV2` plus
  `spans_v2_path`.
- **D-04:** Introduce quote-first v2 wrapper models for canonicalization input
  (`observations_raw.json`) because the Phase 11 canonical schemas are
  span-backed only.

### Canonicalization Scope
- **D-05:** `canonicalize-v2` reuses `_resolve_quotes_to_spans()` and the shared
  chronology/document helpers, but it does not inherit v1-specific event
  heuristics such as dedup, NDA gating, or unnamed-party recovery.
- **D-06:** `canonicalize-v2` preserves the raw artifact and writes canonical
  outputs to `observations.json` plus `extract_v2/spans.json`.

### the agent's Discretion
- Whether the version router lives in `extract_artifacts_v2.py` or a nearby
  module, as long as the v1 loader stays untouched and callers can distinguish
  v1-only, v2-only, both, and empty states.
- Whether derivations are optionally loaded in the v2 loader now or deferred
  behind an optional file-presence branch.

</decisions>

<specifics>
## Specific Ideas

- Mirror the ergonomic shape of `LoadedExtractArtifacts` with a
  `LoadedObservationArtifacts` dataclass exposing `party_index`,
  `cohort_index`, `observation_index`, and `span_index`.
- Reuse `QuoteEntry`, `ResolvedDate`, `MoneyTerms`, and `SkillExclusionRecord`
  instead of inventing new raw-v2 primitives.
- Use `tests/test_skill_extract_artifacts.py` as the model for v1/v2 detection
  regression patterns, and add a dedicated v2 canonicalize fixture test file
  instead of mutating the large v1 canonicalize test file.

</specifics>

<canonical_refs>
## Canonical References

### Phase Scope
- `.planning/ROADMAP.md` — Phase 12 goal and success criteria
- `.planning/REQUIREMENTS.md` — INFRA-01 and INFRA-02
- `.planning/PROJECT.md` — additive migration and parallel v1/v2 execution

### Existing Research
- `.planning/research/ARCHITECTURE.md` — v2 loader/canonicalize recommendations
- `.planning/research/STACK.md` — integration-point guidance
- `.planning/research/PITFALLS.md` — avoid cross-version contamination and
  shared-span regressions

### Runtime Surfaces
- `skill_pipeline/extract_artifacts.py` — current v1 loader
- `skill_pipeline/canonicalize.py` — reusable span-resolution helpers and the
  current v1 canonicalize flow
- `skill_pipeline/cli.py` — additive CLI registration surface
- `tests/test_skill_extract_artifacts.py` — v1 loader mode-detection tests
- `tests/test_skill_canonicalize.py` — existing synthetic canonicalize fixtures

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_resolve_quotes_to_spans()` in `skill_pipeline/canonicalize.py` already maps
  `QuoteEntry` arrays to span sidecars and can be reused for v2.
- `QuoteEntry` and `SpanRegistryArtifact` are already version-independent.
- `tests/test_skill_canonicalize.py` includes a compact fixture writer pattern
  for chronology blocks, document registry, and filings.

### Integration Points
- `skill_pipeline/extract_artifacts_v2.py` (new) for v2 loading and version
  routing
- `skill_pipeline/canonicalize.py` (or adjacent v2-specific helper) for
  `run_canonicalize_v2`
- `skill_pipeline/cli.py` for `canonicalize-v2`
- `tests/test_skill_extract_artifacts_v2.py`, `tests/test_skill_canonicalize_v2.py`,
  and `tests/test_skill_pipeline.py` for regression coverage

</code_context>

<deferred>
## Deferred Ideas

- `check_v2`, `coverage_v2`, `gates_v2`
- `derive.py`
- `db-load-v2` / `db-export-v2`
- v2 prompt composition and skill-doc changes

</deferred>
