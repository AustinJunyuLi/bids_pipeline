---
phase: 03
slug: quote-before-extract
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (standard library, no version pinned in pyproject.toml) |
| **Config file** | none (uses defaults) |
| **Quick run command** | `python -m pytest -q` |
| **Full suite command** | `python -m pytest -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest -q`
- **After every plan wave:** Run `python -m pytest -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | PROMPT-05a | unit | `python -m pytest tests/test_skill_canonicalize.py -x` | Needs update (W0) | ⬜ pending |
| 03-01-02 | 01 | 1 | PROMPT-05b | unit | `python -m pytest tests/test_skill_canonicalize.py -x` | Needs update (W0) | ⬜ pending |
| 03-01-03 | 01 | 1 | PROMPT-05c | unit | `python -m pytest tests/test_skill_canonicalize.py -x` | Needs new test (W0) | ⬜ pending |
| 03-02-01 | 02 | 1 | PROMPT-05d | unit | `python -m pytest tests/test_skill_canonicalize.py -x` | Needs rewrite (W0) | ⬜ pending |
| 03-02-02 | 02 | 1 | PROMPT-05e | unit | `python -m pytest tests/test_skill_verify.py -x` | Needs rewrite (W0) | ⬜ pending |
| 03-02-03 | 02 | 1 | PROMPT-05f | unit | `python -m pytest tests/test_skill_verify.py -x` | Needs new test (W0) | ⬜ pending |
| 03-03-01 | 03 | 2 | PROMPT-05g | unit | `python -m pytest tests/test_skill_compose_prompts.py -x` | Needs update | ⬜ pending |
| 03-04-01 | 04 | 3 | PROMPT-05h | integration/manual | `skill-pipeline canonicalize --deal stec && skill-pipeline verify --deal stec` | Manual | ⬜ pending |
| 03-04-02 | 04 | 3 | PROMPT-05i | integration/manual | `skill-pipeline canonicalize --deal medivation && skill-pipeline verify --deal medivation` | Manual | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Rewrite `tests/test_skill_canonicalize.py` fixtures from evidence_refs to quote-first format
- [ ] Rewrite `tests/test_skill_verify.py` fixtures from evidence_refs to quote-first format
- [ ] Add tests for quote-first format detection in extract_artifacts.py
- [ ] Add tests for legacy format rejection in extract_artifacts.py
- [ ] Update `tests/test_skill_check.py` fixtures if check.py references evidence_refs

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| stec end-to-end re-extraction | PROMPT-05h | Requires LLM extraction call | Re-extract stec, run canonicalize + verify, check EXACT match rate |
| medivation end-to-end re-extraction | PROMPT-05i | Requires LLM extraction call | Re-extract medivation, run canonicalize + verify, check EXACT match rate |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
