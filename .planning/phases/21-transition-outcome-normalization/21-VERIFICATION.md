---
phase: 21-transition-outcome-normalization
verified: 2026-04-01T12:30:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 21: Transition + Outcome Normalization Verification Report

**Phase Goal:** Rework dropout and outcome derivation so elimination dates and
winning actors reflect the strongest filing-grounded support.

**Verified:** 2026-04-01T12:30:00Z
**Status:** passed
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | synthetic transition rows now carry an explicit deterministic event date | VERIFIED | `LifecycleTransitionRecord` now has `event_date`, and `derive.py` compiles transition rows from that field before falling back to the source observation timestamp. |
| 2 | `EXIT-03` and `EXIT-04` use stronger round evidence than the raw status/execution timestamps when available | VERIFIED | `derive.py` now prefers related solicitation deadlines and last known round exit dates, bounded by each subject's last active evidence. |
| 3 | literal outcome rows choose bidder actors first and can inherit an exact related merger-agreement date | VERIFIED | `_preferred_outcome_subject_ref` and `_outcome_row_date` normalize literal executed rows toward bidder refs and exact related agreement dates. |
| 4 | derive regression tests pin the new transition/outcome timing and actor behavior | VERIFIED | `tests/test_skill_derive.py` now covers deadline-driven not-invited exits, residual-loser execution exits, and bidder-first executed rows with related merger-agreement dates. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `skill_pipeline/models_v2.py` | Additive transition-date support | VERIFIED | `LifecycleTransitionRecord.event_date` preserves deterministic timing without widening the rest of the graph contract. |
| `skill_pipeline/derive.py` | Transition-date precedence and normalized outcome rows | VERIFIED | Deadline- and round-aware synthetic exits plus bidder-first literal outcomes are implemented in the derive runtime. |
| `tests/test_skill_derive.py` | Transition/outcome regression coverage | VERIFIED | New fixture tests assert exact `date_recorded` behavior and executed-row normalization. |

### Behavioral Spot-Checks

| Behavior | Command / Check | Result | Status |
|----------|-----------------|--------|--------|
| Focused transition/outcome slice | `pytest -q tests/test_skill_derive.py -k 'drop or outcome or executed or transition or date_recorded'` | `3 passed, 10 deselected` | PASS |
| Derive/gate/export subset | `pytest -q tests/test_skill_derive.py tests/test_skill_gates_v2.py tests/test_skill_db_export_v2.py tests/test_skill_pipeline.py` | `52 passed` | PASS |
| Broader v2 regression bundle | `pytest -q tests/test_skill_observation_models.py tests/test_skill_extract_artifacts_v2.py tests/test_skill_canonicalize_v2.py tests/test_skill_check_v2.py tests/test_skill_coverage_v2.py tests/test_skill_gates_v2.py tests/test_skill_derive.py tests/test_skill_db_export_v2.py tests/test_skill_pipeline.py` | `84 passed` | PASS |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| TRANS-01 | Use stronger elimination dates for `EXIT-03` and `EXIT-04` | SATISFIED | Transition rows now carry explicit dates derived from deadlines, prior round evidence, and last active support. |
| TRANS-02 | Prefer bidder actors and anchored dates on substantive outcomes | SATISFIED | Literal outcome rows now choose bidder refs first and can recover exact related merger-agreement dates. |
| TRANS-03 | Keep round and transition scope recoverable enough for deterministic derivation | SATISFIED | Transition timing now uses related solicitation evidence and avoids duplicate post-exit rows, improving the recovered lifecycle surface even before later contract work. |

### Human Verification Required

None for this synthetic derive slice.

### Gaps Summary

No phase-blocking gaps remain inside the Phase 21 scope. Agreement/process
taxonomy, export precision, and prompt/gate contract work remain Phase 22-23
items.

---

_Verified: 2026-04-01T12:30:00Z_
_Verifier: Codex_
