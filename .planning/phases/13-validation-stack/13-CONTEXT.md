# Phase 13: Validation Stack - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Make the canonical v2 observation graph fail-closed before derivation:

1. Add a structural `check_v2` stage for evidence presence and reference
   integrity on `extract_v2/observations.json`.
2. Add a structured `coverage_v2` stage that emits `CoverageCheckRecord`
   entries from source cues and canonical v2 observations.
3. Add a semantic `gates_v2` stage for graph invariants that can only be
   checked after canonicalization.
4. Expose all three stages as additive CLI commands with JSON report writers
   under `data/skill/<slug>/`.

This phase should not implement derivation logic, DuckDB loading, export
surfaces, prompt changes, or deal migration.

</domain>

<decisions>
## Implementation Decisions

### Validation Separation
- **D-01:** Keep v1 validation modules unchanged. Add separate `check_v2.py`,
  `coverage_v2.py`, and `gates_v2.py` modules rather than widening the v1
  loaders and report logic.
- **D-02:** Consume canonical v2 observations through
  `load_observation_artifacts(..., mode="canonical")` so validation runs only
  on span-backed artifacts and fails fast if canonicalization was skipped.

### Structural Scope
- **D-03:** `check_v2` will enforce observation evidence presence, party/cohort
  and observation-reference integrity, proposal bidder-subject presence, and
  agreement supersession typing.
- **D-04:** Cohort math remains fail-closed via the existing Pydantic model
  invariants, but `check_v2` should still surface downstream reference failures
  in a stable JSON report when loading succeeds.

### Coverage Scope
- **D-05:** Reuse the existing source cue detector from `coverage.py` so v2
  coverage remains benchmark-blind and grounded only in filing-derived evidence
  items and chronology blocks.
- **D-06:** `coverage_v2` should emit structured records for covered and
  uncovered cues, using observation IDs rather than free-text notes as the
  primary provenance surface.

### Semantic Scope
- **D-07:** `gates_v2` will only enforce graph-level invariants that need the
  observation graph: revision/supersession acyclicity, cohort parent-child
  count consistency, and solicitation deadline ordering.

### the agent's Discretion
- The exact report model split between shared `models.py` and additive
  `models_v2.py`, as long as v1 contracts remain backward compatible and the v2
  JSON reports are typed and stable.
- The exact coverage cue-family naming, as long as it is deterministic and
  preserves reason codes plus supporting observation/span references.

</decisions>

<specifics>
## Specific Ideas

- Extend `CoverageCheckRecord` additively with v2 observation/party/cohort
  provenance fields rather than inventing a parallel coverage record type.
- Use a compact synthetic canonical-v2 fixture writer shared across the new
  validation tests so the three modules exercise the same observation graph.
- Treat proposal subjects that resolve to cohorts as valid bidder subjects,
  because anonymous bidder groups are a first-class v2 concept.

</specifics>

<canonical_refs>
## Canonical References

### Phase Scope
- `.planning/ROADMAP.md` — Phase 13 goal and success criteria
- `.planning/REQUIREMENTS.md` — VALID-01, VALID-02, VALID-03
- `.planning/PROJECT.md` — additive v1/v2 migration principles

### Existing Research
- `.planning/research/ARCHITECTURE.md` — v2 validation stack design and layer
  separation
- `.planning/research/STACK.md` — implementation surfaces and test strategy
- `.planning/research/PITFALLS.md` — keep validation ahead of derivation and
  preserve parallel v1/v2 safety

### Runtime Surfaces
- `skill_pipeline/check.py` — v1 structural gate pattern
- `skill_pipeline/coverage.py` — source-cue detection and structured coverage
  record precedent
- `skill_pipeline/gates.py` — v1 semantic gate/report pattern
- `skill_pipeline/extract_artifacts_v2.py` — canonical v2 loader
- `skill_pipeline/models_v2.py` — observation graph schema
- `skill_pipeline/cli.py` — additive command registration surface

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CoverageCheckRecord` already captures structured status, reason codes, and
  supporting IDs.
- `coverage.py` already has deterministic cue-family extraction from source
  evidence items; v2 can reuse that filing-grounded signal.
- `extract_artifacts_v2.py` already exposes canonical indices for parties,
  cohorts, observations, and spans.

### Integration Points
- `skill_pipeline/check_v2.py`
- `skill_pipeline/coverage_v2.py`
- `skill_pipeline/gates_v2.py`
- `skill_pipeline/cli.py`
- `tests/test_skill_check_v2.py`
- `tests/test_skill_coverage_v2.py`
- `tests/test_skill_gates_v2.py`
- `tests/test_skill_pipeline.py`

</code_context>

<deferred>
## Deferred Ideas

- Shared `verify.py` support for v2 observation artifacts
- `derive.py` gate-before-derive enforcement
- v2 DuckDB loaders and export surfaces
- v2 extraction prompt packets and skill docs

</deferred>
