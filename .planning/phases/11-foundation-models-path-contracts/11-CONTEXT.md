# Phase 11: Foundation Models + Path Contracts - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

Define the additive v2 schema layer and additive v2 path contract that every
later observation-graph phase will depend on.

This phase should:

1. Add importable, tested v2 Pydantic models for parties, cohorts, typed
   observations, provenance-bearing derived records, and the v2 artifact
   wrappers.
2. Add v2 path fields to `SkillPathSet` and `build_skill_paths()` without
   changing any v1 path values.

This phase must not implement loaders, canonicalization, validation, derivation
execution, DuckDB loading, or extraction-skill changes.

</domain>

<decisions>
## Implementation Decisions

### Model Placement
- **D-01:** Use a new `skill_pipeline/models_v2.py` module instead of extending
  the existing v1 `models.py` with large new schema sections.
- **D-02:** Reuse shared v1 primitives (`SkillModel`, `ResolvedDate`,
  `MoneyTerms`, `CoverageCheckRecord`, `SkillExclusionRecord`) where the
  semantics already match, instead of re-declaring near-duplicates.

### Schema Discipline
- **D-03:** Keep the v2 schema additive. No v1 classes are renamed, removed, or
  behaviorally changed in Phase 11.
- **D-04:** Observation polymorphism must use Pydantic's discriminated union on
  `obs_type`, not ad hoc manual dispatch.
- **D-05:** Observation-to-observation reference fields must be present in the
  schema now (`revises`, `supersedes`, `requested_by`, `related`) even though
  no runtime consumes them yet.
- **D-06:** Derived records should exist as schemas with required provenance via
  `DerivationBasis`, but Phase 11 does not need any derivation logic.

### Path Contract
- **D-07:** `SkillPathSet` path additions must be strictly additive and v1 path
  values must stay byte-for-byte unchanged.
- **D-08:** `ensure_output_directories()` should create the new v2 directories
  once they exist in `SkillPathSet`.

### the agent's Discretion
- Exact subtype enums and optional field names, as long as they satisfy the
  roadmap success criteria and the research sketches.
- Whether the v2 path set includes only the required directories or also key v2
  file paths needed by later phases.

</decisions>

<specifics>
## Specific Ideas

- `Observation = Annotated[Union[...], Field(discriminator="obs_type")]` is the
  critical dispatch surface to test.
- `CohortRecord` should validate the arithmetic invariant
  `unknown_member_count == exact_count - len(known_member_party_ids)`.
- Path tests should assert both that `extract_v2_dir` / `export_v2_dir` exist
  and that legacy `extract_dir` / `export_dir` values are untouched.

</specifics>

<canonical_refs>
## Canonical References

### Phase Scope
- `.planning/ROADMAP.md` — Phase 11 goal and success criteria
- `.planning/REQUIREMENTS.md` — MODEL-01 through MODEL-06 and INFRA-03
- `.planning/PROJECT.md` — additive-migration constraint

### Existing Research
- `.planning/research/ARCHITECTURE.md` — model sketches and additive path
  guidance
- `.planning/research/FEATURES.md` — required observation/derived record shapes
- `.planning/research/STACK.md` — discriminated-union implementation guidance
- `.planning/research/PITFALLS.md` — additive-model safety constraints

### Runtime Surfaces
- `skill_pipeline/models.py` — shared v1 primitives and current `SkillPathSet`
- `skill_pipeline/paths.py` — current v1 path builder and output-directory
  creation
- `tests/test_skill_pipeline.py` — existing path contract tests

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SkillModel` already provides the desired `extra="forbid"` behavior.
- `ResolvedDate`, `MoneyTerms`, and the Phase 10 `CoverageCheckRecord` are
  already reusable shared schema primitives.
- Existing path tests in `tests/test_skill_pipeline.py` provide the right place
  to assert that v2 additions do not perturb v1 path values.

### Integration Points
- `skill_pipeline/models_v2.py` for the new additive schemas
- `skill_pipeline/models.py` + `skill_pipeline/paths.py` for additive path
  fields
- `tests/test_skill_observation_models.py` (new) and
  `tests/test_skill_pipeline.py` (existing) for regression coverage

</code_context>

<deferred>
## Deferred Ideas

- `extract_artifacts_v2.py`
- `canonicalize-v2`
- `check_v2`, `coverage_v2`, `gates_v2`
- `derive.py`, `db-load-v2`, and `db-export-v2`

</deferred>
