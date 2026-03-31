---
phase: 13-validation-stack
verified: 2026-03-31T10:24:01Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 13: Validation Stack Verification Report

**Phase Goal:** v2 observations pass through structural, coverage, and semantic
validation gates that catch schema errors, coverage gaps, and graph-level
inconsistencies before derivation.

**Verified:** 2026-03-31T10:24:01Z  
**Status:** passed  
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `check_v2` rejects canonical observations missing evidence spans, unresolved refs, and bidderless proposals | VERIFIED | `skill_pipeline/check_v2.py` loads only canonical v2 artifacts and emits blocker findings for missing `evidence_span_ids`, missing entity/observation refs, bad supersession typing, and bidderless proposals. `tests/test_skill_check_v2.py` exercises each failing path directly. |
| 2 | `coverage_v2` emits structured coverage records with status and reason codes on canonical observations | VERIFIED | `skill_pipeline/coverage_v2.py` reuses filing-grounded source cues and writes `CoverageCheckRecordV2` rows with statuses such as `observed`, `not_found`, and `ambiguous`, plus supporting observation/span provenance. `tests/test_skill_coverage_v2.py` covers observed, missing, and ambiguous outcomes. |
| 3 | `gates_v2` enforces graph-level invariants that structural checks cannot see | VERIFIED | `skill_pipeline/gates_v2.py` emits blocker findings for proposal/agreement cycles, child cohorts exceeding parent counts, and solicitation deadlines before solicitation dates. `tests/test_skill_gates_v2.py` pins each invariant with a direct failing fixture. |
| 4 | All three validation stages are live CLI commands writing JSON artifacts under `data/skill/<slug>/` | VERIFIED | `skill_pipeline/cli.py` now registers `check-v2`, `coverage-v2`, and `gates-v2`. Parser coverage in `tests/test_skill_pipeline.py` proves all three commands parse successfully, and `CLAUDE.md` now documents their live output paths. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `skill_pipeline/check_v2.py` | Canonical-v2 structural gate | VERIFIED | Writes `check_v2/check_report.json` and fails on structural blockers. |
| `skill_pipeline/coverage_v2.py` | Canonical-v2 structured coverage stage | VERIFIED | Writes `coverage_v2/coverage_findings.json` and `coverage_v2/coverage_summary.json`. |
| `skill_pipeline/gates_v2.py` | Canonical-v2 semantic gate | VERIFIED | Writes `gates_v2/gates_report.json` and fails on graph blockers. |
| `skill_pipeline/models_v2.py` | v2 validation report types | VERIFIED | Contains additive v2 check, coverage, and gate report models. |
| `skill_pipeline/cli.py` | CLI registration for all v2 validation commands | VERIFIED | Exposes `check-v2`, `coverage-v2`, and `gates-v2`. |
| `tests/test_skill_check_v2.py` | Structural regression tests | VERIFIED | Covers missing evidence, unresolved refs, bidderless proposals, and bad supersession typing. |
| `tests/test_skill_coverage_v2.py` | Coverage regression tests | VERIFIED | Covers observed, uncovered, and ambiguous cue matching. |
| `tests/test_skill_gates_v2.py` | Semantic gate regression tests | VERIFIED | Covers revision cycles, cohort count violations, and deadline ordering failures. |
| `CLAUDE.md` | Repo memory update for live v2 validation outputs | VERIFIED | Marks the Phase 13 v2 validation writers as live authoritative runtime outputs. |

### Behavioral Spot-Checks

| Behavior | Command / Check | Result | Status |
|----------|-----------------|--------|--------|
| Focused Phase 13 validation slice | `pytest -q tests/test_skill_check_v2.py tests/test_skill_coverage_v2.py tests/test_skill_gates_v2.py tests/test_skill_pipeline.py -k 'check_v2 or coverage_v2 or gates_v2 or check-v2 or coverage-v2 or gates-v2'` | `16 passed` | PASS |
| Wider v2 regression bundle | `pytest -q tests/test_skill_observation_models.py tests/test_skill_extract_artifacts_v2.py tests/test_skill_canonicalize_v2.py tests/test_skill_check_v2.py tests/test_skill_coverage_v2.py tests/test_skill_gates_v2.py tests/test_skill_pipeline.py` | `61 passed` | PASS |
| Syntax sanity | `python -m py_compile skill_pipeline/check_v2.py skill_pipeline/coverage_v2.py skill_pipeline/gates_v2.py tests/_v2_validation_fixtures.py tests/test_skill_check_v2.py tests/test_skill_coverage_v2.py tests/test_skill_gates_v2.py` | `success` | PASS |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| VALID-01 | Structural `check_v2` on evidence/ref integrity and bidder subjects | SATISFIED | `check_v2.py` plus `tests/test_skill_check_v2.py` cover all required blocker conditions. |
| VALID-02 | Structured `coverage_v2` generation with status and reason codes | SATISFIED | `coverage_v2.py` writes typed coverage records with provenance, and the coverage tests assert observed, missing, and ambiguous statuses. |
| VALID-03 | Graph semantic gates for cycles, cohort counts, and deadline ordering | SATISFIED | `gates_v2.py` and `tests/test_skill_gates_v2.py` enforce each required invariant. |

### Human Verification Required

None. Phase 13 is fully supported by deterministic synthetic fixture tests and
CLI parser coverage.

### Gaps Summary

No phase-blocking gaps remain.

Residual note: `verify.py` still only serves the v1 extraction contract. Later
phases that require gate-before-derive semantics must decide whether v2 derive
depends on a shared verify report or only on the new Phase 13 validation
artifacts.

---

_Verified: 2026-03-31T10:24:01Z_  
_Verifier: Codex_
