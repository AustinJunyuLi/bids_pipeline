---
phase: 4
slug: enhanced-gates
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/test_gates.py -q` |
| **Full suite command** | `python -m pytest -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_gates.py -q`
- **After every plan wave:** Run `python -m pytest -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | GATE-01 | unit | `python -m pytest tests/test_gates.py::test_temporal_consistency -q` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | GATE-02 | unit | `python -m pytest tests/test_gates.py::test_cross_event_logic -q` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | GATE-03 | unit | `python -m pytest tests/test_gates.py::test_actor_lifecycle -q` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 1 | GATE-04 | unit | `python -m pytest tests/test_gates.py::test_attention_decay -q` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 2 | GATE-01..04 | integration | `skill-pipeline gates --deal stec` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_gates.py` — stubs for GATE-01, GATE-02, GATE-03, GATE-04
- [ ] Test fixtures with synthetic events covering temporal violations, cross-event invariant violations, orphaned NDA signers, and attention decay patterns

*Existing pytest infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| medivation gates catch new error class | GATE-01..04 | Requires full deal data + visual review of findings | Run `skill-pipeline gates --deal medivation`, inspect gates_report.json for non-trivial findings |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
