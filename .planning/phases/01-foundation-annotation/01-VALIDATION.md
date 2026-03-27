---
phase: 1
slug: foundation-annotation
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-27
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pytest.ini` |
| **Quick run command** | `python -m pytest -q tests/test_skill_source_annotations.py tests/test_skill_preprocess_source.py` |
| **Full suite command** | `python -m pytest -q` |
| **Estimated runtime** | ~60 seconds |

---

## Sampling Rate

- **After every task commit:** Run the task-local targeted pytest command from the plan
- **After every plan wave:** Run `python -m pytest -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | INFRA-04 | unit/schema | `python -m pytest -q tests/test_skill_source_annotations.py` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | INFRA-04 | integration | `python -m pytest -q tests/test_skill_preprocess_source.py` | ✅ | ⬜ pending |
| 01-01-03 | 01 | 1 | INFRA-04 | regression | `python -m pytest -q tests/test_skill_canonicalize.py tests/test_skill_verify.py tests/test_skill_coverage.py tests/test_skill_enrich_core.py tests/test_skill_pipeline.py tests/test_skill_provenance.py` | ✅ | ⬜ pending |
| 01-02-01 | 02 | 1 | INFRA-06 | manifest audit | `python -m pytest -q tests/test_runtime_contract_docs.py` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 1 | INFRA-06 | doc policy | `python -m pytest -q tests/test_runtime_contract_docs.py tests/test_benchmark_separation_policy.py` | ✅ | ⬜ pending |
| 01-02-03 | 02 | 1 | INFRA-06 | full regression | `python -m pytest -q tests/test_runtime_contract_docs.py tests/test_benchmark_separation_policy.py tests/test_skill_mirror_sync.py` | ✅ | ⬜ pending |
| 01-03-01 | 03 | 2 | INFRA-04 | artifact validation | `python scripts/validate_annotated_blocks.py --deals imprivata mac-gray medivation penford petsmart-inc providence-worcester saks stec zep --spot-check stec` | ❌ W0 | ⬜ pending |
| 01-03-02 | 03 | 2 | INFRA-04 | corpus regeneration | `python scripts/validate_annotated_blocks.py --deals imprivata mac-gray medivation penford petsmart-inc providence-worcester saks stec zep` | ❌ W0 | ⬜ pending |
| 01-03-03 | 03 | 2 | INFRA-04, INFRA-06 | full-suite regression | `python -m pytest -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- Existing infrastructure covers all phase requirements.
- No new test framework or harness installation is required before execution.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `stec` block metadata looks semantically plausible | INFRA-04 | The roadmap requires a human spot-check, not just schema validity | Open `data/deals/stec/source/chronology_blocks.jsonl` after regeneration and inspect one early, one middle, and one late block. Confirm the phase hint tracks the narrative, `date_mentions` include real filing dates, entity mentions correspond to filing names or aliases, and `evidence_density` is not uniformly zero. |

---

## Validation Sign-Off

- [ ] All tasks have automated verify commands or existing infrastructure
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all missing references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
