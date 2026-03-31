---
phase: 11-foundation-models-path-contracts
verified: 2026-03-31T08:58:11Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 11: Foundation Models + Path Contracts Verification Report

**Phase Goal:** All v2 Pydantic models exist as importable, tested schema
definitions and v2 artifact paths are registered in `SkillPathSet`.

**Verified:** 2026-03-31T08:58:11Z  
**Status:** passed  
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `PartyRecord` round-trips role, bidder/advisor classification fields, advised-party linkage, and evidence spans | VERIFIED | `tests/test_skill_observation_models.py` now exercises both a bidder-style record and an advisor-linked record with `bidder_kind`, `advisor_kind`, `advised_party_id`, and `evidence_span_ids`, and both serialize/deserialize cleanly through `PartyRecord`. |
| 2 | `CohortRecord` supports exact-count arithmetic and parent lineage for nested unnamed groups | VERIFIED | `skill_pipeline/models_v2.py` enforces `unknown_member_count == exact_count - len(known_member_party_ids)`, and `tests/test_skill_observation_models.py` includes both the invariant failure case and a nested `parent_cohort_id` round-trip representing a PetSmart-style finalist subgroup. |
| 3 | All six observation subtypes deserialize through a discriminated union on `obs_type`, including observation-to-observation references | VERIFIED | `Observation = Annotated[..., Field(discriminator=\"obs_type\")]` lives in `skill_pipeline/models_v2.py`, and the observation tests cover `requested_by_observation_id`, `revises_observation_id`, `supersedes_observation_id`, and `related_observation_id` across the six subtype payloads. |
| 4 | `DerivationBasis` and all required derived record types exist with provenance-bearing `basis` fields | VERIFIED | `skill_pipeline/models_v2.py` defines `ProcessPhaseRecord`, `LifecycleTransitionRecord`, `CashRegimeRecord`, `JudgmentRecord`, and `AnalystRowRecord`, and the derived-record test proves each requires a populated `DerivationBasis`. |
| 5 | `SkillPathSet` exposes additive v2 artifact paths while legacy v1 paths remain unchanged | VERIFIED | `skill_pipeline/models.py` and `skill_pipeline/paths.py` now register v2 paths under `extract_v2/`, `check_v2/`, `coverage_v2/`, `gates_v2/`, `derive/`, `export_v2/`, and `prompt_v2/`; `tests/test_skill_pipeline.py` asserts those fields alongside the unchanged legacy `extract/`, `export/`, and `prompt/` values. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `skill_pipeline/models_v2.py` | Additive v2 schema module | VERIFIED | Contains the Phase 11 party, cohort, observation, derivation, and wrapper schemas. |
| `tests/test_skill_observation_models.py` | Focused model validation tests | VERIFIED | Covers round-trip serialization, union dispatch, cross-observation references, nested cohorts, and provenance-bearing derived records. |
| `skill_pipeline/models.py` | Additive v2 path fields on `SkillPathSet` | VERIFIED | New v2 path fields coexist with all existing v1 fields. |
| `skill_pipeline/paths.py` | Path builder and directory creation for v2 surfaces | VERIFIED | `build_skill_paths()` and `ensure_output_directories()` materialize the additive v2 directories and file paths. |
| `tests/test_skill_pipeline.py` | Path regression coverage | VERIFIED | Adds explicit assertions for the v2 path surface and directory creation while pinning legacy path values. |
| `CLAUDE.md` | Authoritative memory update | VERIFIED | Documents the structured coverage detail contract and the additive v2 path surface as reserved scaffolding beside the live v1 artifacts. |

### Behavioral Spot-Checks

| Behavior | Command / Check | Result | Status |
|----------|-----------------|--------|--------|
| v2 schema validation slice | `pytest -q tests/test_skill_observation_models.py` | `12 passed` | PASS |
| Path-contract regression slice | `pytest -q tests/test_skill_pipeline.py` | `22 passed` | PASS |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| MODEL-01 | PartyRecord schema with role/linkage/evidence fields | SATISFIED | `PartyRecord` exists in `models_v2.py`, and dedicated round-trip tests cover role, bidder/advisor metadata, advised-party links, and evidence spans. |
| MODEL-02 | CohortRecord schema for unnamed group lifecycles | SATISFIED | `CohortRecord` supports parent lineage, exact counts, known members, unknown-member counts, and evidence spans, with direct invariant and nesting tests. |
| MODEL-03 | Six observation subtypes with discriminated-union loading | SATISFIED | All six subtypes dispatch through `obs_type` in the model tests. |
| MODEL-04 | Observation-to-observation references | SATISFIED | `requested_by`, `revises`, `supersedes`, and `related` fields exist and round-trip in tests. |
| MODEL-05 | Derivation basis plus derived record schemas | SATISFIED | All required derived record types carry a required `basis: DerivationBasis`. |
| MODEL-06 | v2 artifact wrapper models | SATISFIED | `ObservationArtifactV2` and `DerivedArtifactV2` are defined and exercised by the observation artifact round-trip test. |
| INFRA-03 | Additive v2 path contract in `SkillPathSet` | SATISFIED | `SkillPathSet`, `build_skill_paths()`, `ensure_output_directories()`, the path tests, and `CLAUDE.md` all reflect the additive v2 surface. |

### Human Verification Required

None. Phase 11 is fully supported by deterministic unit tests and direct schema/path inspection.

### Gaps Summary

No phase-blocking gaps remain.

Residual note: Phase 11 intentionally registers future-facing v2 paths before
their runtime writers exist. Later phases must treat these as reserved contract
locations, not evidence that the corresponding CLI commands are already live.

---

_Verified: 2026-03-31T08:58:11Z_  
_Verifier: Codex_
