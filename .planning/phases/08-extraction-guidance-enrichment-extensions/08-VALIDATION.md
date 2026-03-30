---
phase: 8
slug: extraction-guidance-enrichment-extensions
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/test_skill_enrich_core.py tests/test_skill_mirror_sync.py tests/test_skill_compose_prompts.py tests/test_skill_db_load.py tests/test_skill_db_export.py -q` |
| **Full suite command** | `python -m pytest -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick command for touched test files
- **After every plan wave:** Run full suite
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | EXTRACT-01/02/03 | content | `python -m pytest tests/test_skill_mirror_sync.py tests/test_skill_compose_prompts.py -q` | YES | pending |
| 08-02-01 | 02 | 1 | ENRICH-02/03 | unit | `python -m pytest tests/test_skill_enrich_core.py -q` | YES | pending |
| 08-03-01 | 03 | 2 | ENRICH-02/03 | unit | `python -m pytest tests/test_skill_db_load.py tests/test_skill_db_export.py -q` | YES | pending |

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Extraction guidance produces correct events on re-run | EXTRACT-01/02/03 | Requires LLM extraction agent | Phase 9 re-extraction will validate |
| DropTarget on live corpus | ENRICH-02 | Requires complete deal artifacts | Run `skill-pipeline enrich-core --deal saks` and check deterministic_enrichment.json |

---

## Validation Sign-Off

- [ ] All tasks have automated verify
- [ ] Sampling continuity maintained
- [ ] Wave 0 not needed
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
