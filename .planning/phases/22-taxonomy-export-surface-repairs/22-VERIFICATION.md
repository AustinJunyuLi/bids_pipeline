---
phase: 22-taxonomy-export-surface-repairs
verified: 2026-04-01T12:50:00Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 22: Taxonomy + Export Surface Repairs Verification Report

**Phase Goal:** Expand the analyst surface so agreement/process rows, proxy
dates, and enterprise-value proposals are represented without misleading
precision.

**Verified:** 2026-04-01T12:50:00Z
**Status:** passed
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | agreement-family rows now preserve additive analyst event types | VERIFIED | `derive.py` now maps amendment, standstill, exclusivity, and clean-team observations to distinct analyst event types rather than collapsing them all to `nda`. |
| 2 | advisor termination is representable on the analyst surface | VERIFIED | `models_v2.py` now accepts `advisor_termination`, and `derive.py` emits `ib_terminated` rows. |
| 3 | proxy sort dates no longer masquerade as exact `date_recorded` values | VERIFIED | `derive.py` now reserves `date_recorded`/`date_public` for exact-day dates and carries non-exact dates through `date_precision` plus `date_sort_proxy`; `db_export_v2.py` exports those fields directly. |
| 4 | enterprise-value-only proposals survive derive and export cleanly | VERIFIED | Proposal rows now preserve `enterprise_value` end-to-end through derive and the analyst CSV surface. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `skill_pipeline/models_v2.py` | Expanded additive analyst row contract | VERIFIED | Adds new process/event taxonomy values plus `enterprise_value`, `date_precision`, and `date_sort_proxy` on analyst rows. |
| `skill_pipeline/derive.py` | Distinct event mapping and safer date/value surfaces | VERIFIED | Agreement families, advisor termination, proxy dates, and enterprise-value proposals are compiled into analyst rows without lossy collapse. |
| `skill_pipeline/db_export_v2.py` | Updated analyst/benchmark CSV surface | VERIFIED | Exports the new enterprise-value and date-metadata columns. |
| `tests/test_skill_derive.py` | Taxonomy regression coverage | VERIFIED | Covers `nda_amendment` and `ib_terminated` row emission. |
| `tests/test_skill_db_export_v2.py` | Export regression coverage | VERIFIED | Covers enterprise-value-only proposals and proxy-date export behavior. |

### Behavioral Spot-Checks

| Behavior | Command / Check | Result | Status |
|----------|-----------------|--------|--------|
| Focused taxonomy/export slice | `pytest -q tests/test_skill_derive.py tests/test_skill_db_export_v2.py -k 'agreement or exclusivity or amendment or enterprise or proxy or advisor_termination'` | `4 passed, 15 deselected` | PASS |
| Derive/gate/export subset | `pytest -q tests/test_skill_derive.py tests/test_skill_gates_v2.py tests/test_skill_db_export_v2.py tests/test_skill_pipeline.py` | `54 passed` | PASS |
| Broader v2 regression bundle | `pytest -q tests/test_skill_observation_models.py tests/test_skill_extract_artifacts_v2.py tests/test_skill_canonicalize_v2.py tests/test_skill_check_v2.py tests/test_skill_coverage_v2.py tests/test_skill_gates_v2.py tests/test_skill_derive.py tests/test_skill_db_export_v2.py tests/test_skill_pipeline.py` | `86 passed` | PASS |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| SURFACE-01 | Preserve distinct analyst event types for agreement families | SATISFIED | Agreement-family observations now emit `nda_amendment`, `standstill`, `exclusivity`, and `clean_team`. |
| SURFACE-02 | Cover bidder-originated sale / advisor termination boundaries | SATISFIED | Bidder-originated sale already existed; Phase 22 adds explicit `advisor_termination` → `ib_terminated`. |
| SURFACE-03 | Stop leaking proxy dates as exact `date_recorded` | SATISFIED | Non-exact dates now export through `date_precision` and `date_sort_proxy`, with `date_recorded` reserved for exact-day values. |
| SURFACE-04 | Export enterprise-value-only proposals | SATISFIED | Proposal rows now preserve `enterprise_value` through derive and CSV export. |

### Human Verification Required

None for this additive surface slice.

### Gaps Summary

No phase-blocking gaps remain inside the Phase 22 scope. Prompt/skill contract
updates and the remaining v2 gate warnings are still owned by Phase 23.

---

_Verified: 2026-04-01T12:50:00Z_
_Verifier: Codex_
