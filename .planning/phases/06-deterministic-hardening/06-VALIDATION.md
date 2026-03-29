---
phase: 6
slug: deterministic-hardening
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-03-29
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pytest.ini` |
| **Quick run command** | `pytest -q tests/test_skill_canonicalize.py tests/test_skill_coverage.py tests/test_skill_gates.py tests/test_skill_db_load.py tests/test_skill_db_export.py` |
| **Full suite command** | `pytest -q` |
| **Estimated runtime** | ~25 seconds |

---

## Sampling Rate

- **After every task commit:** Run the task-local pytest target for the touched subsystem.
- **After every plan wave:** Run `pytest -q tests/test_skill_canonicalize.py tests/test_skill_coverage.py tests/test_skill_gates.py tests/test_skill_db_load.py tests/test_skill_db_export.py`
- **Before `$gsd-verify-work`:** Full suite must be green.
- **Max feedback latency:** 25 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | HARD-06 | unit | `pytest -q tests/test_skill_canonicalize.py -k mixed_schema` | ✅ | ⬜ pending |
| 06-01-02 | 01 | 1 | HARD-01 | unit | `pytest -q tests/test_skill_canonicalize.py -k \"duplicate_quote_ids or renumber or idempotent\"` | ✅ | ⬜ pending |
| 06-02-01 | 02 | 2 | HARD-04 | unit | `pytest -q tests/test_skill_coverage.py tests/test_skill_gates.py -k nda` | ✅ | ⬜ pending |
| 06-03-01 | 03 | 3 | HARD-05 | unit/integration | `pytest -q tests/test_skill_db_load.py tests/test_skill_db_export.py -k \"lock or retry or open_pipeline_db\"` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing pytest infrastructure and fixture helpers already cover this phase's
subsystems.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Fresh rerun no longer trips the known deterministic walls | HARD-06, HARD-01, HARD-04, HARD-05 | Requires corpus artifacts and end-to-end operator review, not just synthetic fixtures | Re-run the documented Phase 6 deals through `canonicalize`, `coverage`, `gates`, `db-load`, and `db-export`; confirm the previously logged mixed-schema, quote-collision, rollover-CA, and lock errors do not recur |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or existing test-file coverage
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all missing references
- [ ] No watch-mode flags
- [ ] Feedback latency < 25s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
