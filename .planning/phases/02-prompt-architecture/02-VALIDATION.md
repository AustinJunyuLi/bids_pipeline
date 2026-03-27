---
phase: 2
slug: prompt-architecture
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-27
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pytest.ini` |
| **Quick run command** | `python -m pytest -q tests/test_skill_prompt_models.py tests/test_skill_compose_prompts.py` |
| **Full suite command** | `python -m pytest -q` |
| **Estimated runtime** | ~90 seconds |

---

## Sampling Rate

- **After every task commit:** Run the task-local targeted pytest command from the plan
- **After every plan wave:** Run `python -m pytest -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | INFRA-05 | schema | `python -m pytest -q tests/test_skill_prompt_models.py` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | INFRA-01, INFRA-02 | cli/path | `python -m pytest -q tests/test_skill_pipeline.py -k "compose_prompts or prompt"` | ✅ | ⬜ pending |
| 02-01-03 | 01 | 1 | INFRA-01, INFRA-02, INFRA-05 | regression | `python -m pytest -q tests/test_skill_prompt_models.py tests/test_skill_pipeline.py` | ✅ | ⬜ pending |
| 02-02-01 | 02 | 2 | PROMPT-02 | unit | `python -m pytest -q tests/test_skill_compose_prompts.py -k chunk` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 2 | PROMPT-01, PROMPT-03, PROMPT-04 | renderer | `python -m pytest -q tests/test_skill_compose_prompts.py -k "render or overlap or checklist"` | ❌ W0 | ⬜ pending |
| 02-02-03 | 02 | 2 | INFRA-03, INFRA-05 | integration | `python -m pytest -q tests/test_skill_compose_prompts.py` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 3 | INFRA-01, INFRA-02 | skill-doc contract | `python -m pytest -q tests/test_skill_mirror_sync.py tests/test_runtime_contract_docs.py` | ✅ | ⬜ pending |
| 02-03-02 | 03 | 3 | INFRA-05 | artifact validation | `python scripts/validate_prompt_packets.py --deal stec --expect-sections` | ❌ W0 | ⬜ pending |
| 02-03-03 | 03 | 3 | PROMPT-01, PROMPT-02, PROMPT-03, PROMPT-04 | full integration | `python -m pytest -q && python scripts/validate_prompt_packets.py --deal stec --expect-sections` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- Existing pytest infrastructure covers the phase requirements.
- New prompt-specific tests and validator script must be added during execution:
  - `tests/test_skill_prompt_models.py`
  - `tests/test_skill_compose_prompts.py`
  - `scripts/validate_prompt_packets.py`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `stec` prompt packets are visibly chronology-first and human-auditable | PROMPT-01, PROMPT-03, PROMPT-04 | Ordering and readability matter beyond schema validity | Generate `stec` packets, open one actor packet and one event packet, confirm chronology text appears before instructions, checklist is concise, and `<overlap_context>` is clearly separated from primary extraction blocks. |
| `stec` extraction through composed packets passes deterministic gates | INFRA-01, INFRA-05 | Roadmap exit criterion requires real extraction quality, not only render correctness | Run `skill-pipeline compose-prompts --deal stec --mode actors`, extract actors, then `--mode events`, extract events, then run check/verify/coverage gates and confirm passing. |

---

## Validation Sign-Off

- [ ] All tasks have automated verify commands or existing infrastructure
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all missing references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
