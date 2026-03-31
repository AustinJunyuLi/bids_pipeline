---
phase: 14-derivation-engine
verified: 2026-03-31T11:15:34Z
status: passed
score: 6/6 must-haves verified
re_verification: false
---

# Phase 14: Derivation Engine Verification Report

**Phase Goal:** A deterministic rule engine transforms validated observation
graphs into derived analytical records with explicit provenance on every output,
while keeping benchmark-shaped anonymous expansion deferred to Phase 15 export.

**Verified:** 2026-03-31T11:15:34Z  
**Status:** passed  
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `derive` refuses to run unless the Phase 13 v2 validation artifacts exist and pass | VERIFIED | `skill_pipeline/derive.py` invalidates stale outputs, requires `check_v2`, `coverage_v2`, and `gates_v2` artifacts, and raises when any summary status is not `pass`. `tests/test_skill_derive.py` covers the failing gate path directly. |
| 2 | Round rules derive provenance-bearing `ProcessPhaseRecord` outputs and phase-aware round rows | VERIFIED | `derive.py` classifies `SolicitationObservation` records into informal or formal phases, records `DerivationBasis`, and compiles `final_round_*` rows from solicitation dates and due dates. `tests/test_skill_derive.py` covers both informal and formal paths. |
| 3 | Exit rules cover not-invited and lost-to-winner semantics without collapsing cohort-backed identities | VERIFIED | `derive.py` now tracks active, submitted, and terminally exited subjects, emits deterministic `LifecycleTransitionRecord` rows for `EXIT-01` through `EXIT-04`, and preserves `subject_ref` plus `subject_count` on transition outputs. The exit fixture test covers both `not_invited` and `lost_to_winner`. |
| 4 | Cash regimes, judgments, and agreement supersession are derived deterministically with explicit provenance | VERIFIED | `derive.py` emits phase-level `CashRegimeRecord` entries from proposal terms or merger-agreement evidence, raises `JudgmentRecord` outputs for ambiguous initiation/advisory/phase states, and compiles NDA-family supersession flags into analyst rows. `tests/test_skill_derive.py` covers all three behaviors. |
| 5 | `AnalystRowRecord` stays graph-linked and defers anonymous slot expansion | VERIFIED | `skill_pipeline/models_v2.py` now centers `subject_ref` and `row_count`, while `derive.py` emits cohort-backed rows as `synthetic_anonymous` with preserved counts instead of invented slot rows. `tests/test_skill_derive.py` asserts cohort-backed proposal rows remain unexpanded. |
| 6 | `derive` is a live CLI stage and repo memory reflects the new artifact writers | VERIFIED | `skill_pipeline/cli.py` registers `derive`, `tests/test_skill_pipeline.py` covers parser behavior, and `CLAUDE.md` marks `derive/derivations.json` plus `derive/derive_log.json` as live outputs. |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `skill_pipeline/derive.py` | Deterministic v2 derivation runtime | VERIFIED | Gates on passing Phase 13 validation, derives phases/transitions/cash/judgments, compiles analyst rows, and writes derive artifacts. |
| `skill_pipeline/models_v2.py` | Phase 14 schema alignment | VERIFIED | Adds agreement consideration typing plus graph-linked transition and analyst-row fields needed by derive. |
| `skill_pipeline/extract_artifacts_v2.py` | Raw-to-canonical field support for derive | VERIFIED | Preserves agreement `consideration_type` through the v2 artifact loader. |
| `skill_pipeline/cli.py` | Live `derive` CLI registration | VERIFIED | Exposes `derive` without disturbing v1 commands. |
| `tests/test_skill_derive.py` | Derive regression coverage | VERIFIED | Covers gating, rounds, cash, judgments, exits, cohort-backed rows, superseding NDA rows, and CLI runtime behavior. |
| `tests/test_skill_observation_models.py` | Schema regression coverage | VERIFIED | Pins the additive Phase 14 model fields and derived-record validation contract. |
| `tests/test_skill_pipeline.py` | CLI parser coverage | VERIFIED | Confirms `derive --deal <slug>` parses correctly. |
| `CLAUDE.md` | Repo memory for live derive outputs | VERIFIED | Documents the additive derive artifact contract under `data/skill/<slug>/derive/`. |

### Behavioral Spot-Checks

| Behavior | Command / Check | Result | Status |
|----------|-----------------|--------|--------|
| Focused derive slice | `pytest -q tests/test_skill_observation_models.py tests/test_skill_derive.py tests/test_skill_pipeline.py -k 'derive or row_count or subject_ref or consideration_type'` | `10 passed, 37 deselected` | PASS |
| Full v2 regression bundle | `pytest -q tests/test_skill_observation_models.py tests/test_skill_extract_artifacts_v2.py tests/test_skill_canonicalize_v2.py tests/test_skill_check_v2.py tests/test_skill_coverage_v2.py tests/test_skill_gates_v2.py tests/test_skill_derive.py tests/test_skill_pipeline.py` | `70 passed` | PASS |
| Syntax sanity | `python -m py_compile skill_pipeline/models_v2.py skill_pipeline/extract_artifacts_v2.py skill_pipeline/check_v2.py skill_pipeline/coverage_v2.py skill_pipeline/gates_v2.py skill_pipeline/derive.py tests/_v2_validation_fixtures.py tests/test_skill_observation_models.py tests/test_skill_derive.py tests/test_skill_pipeline.py` | `success` | PASS |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| DERIVE-01 | Round derivation from solicitations | SATISFIED | `derive.py` emits `ProcessPhaseRecord` plus round rows for informal and formal phases. |
| DERIVE-02 | Exit inference rules | SATISFIED | `derive.py` implements `EXIT-01` through `EXIT-04` and `tests/test_skill_derive.py` exercises the exit cases. |
| DERIVE-03 | Cash regime derivation | SATISFIED | `derive.py` emits phase-level `CashRegimeRecord` values from proposal and agreement evidence. |
| DERIVE-04 | Agreement-derived NDA-family row handling | SATISFIED | Agreement supersession is preserved through NDA-family analyst rows with review flags. |
| DERIVE-05 | Graph-linked analyst-row compilation | SATISFIED | `AnalystRowRecord` now preserves `subject_ref`, `row_count`, date/terms fields, and provenance without slot expansion. |
| DERIVE-06 | Explicit judgments for ambiguity | SATISFIED | `derive.py` emits `JudgmentRecord` outputs for ambiguous phase, initiation, advisory link, and exit state paths. |

### Human Verification Required

None for Phase 14 synthetic validation. Real-deal migration and benchmark
comparison remain Phase 16 work.

### Gaps Summary

No phase-blocking gaps remain.

Residual note: Phase 14 intentionally does not depend on `verify.py`; the
derive log records that policy explicitly until a shared v2 verify surface
exists.

---

_Verified: 2026-03-31T11:15:34Z_  
_Verifier: Codex_
