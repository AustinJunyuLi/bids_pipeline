---
phase: 05
slug: integration-calibration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest -q tests/` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest -q tests/`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | DB-01 | unit | `python -m pytest tests/test_db_load.py` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | DB-01 | integration | `python -m pytest tests/test_db_load.py -k integration` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 1 | DB-03 | unit | `python -m pytest tests/test_db_export.py` | ❌ W0 | ⬜ pending |
| 05-02-02 | 02 | 1 | DB-03 | integration | `python -m pytest tests/test_db_export.py -k csv_parity` | ❌ W0 | ⬜ pending |
| 05-03-01 | 03 | 1 | PROMPT-06 | unit | `python -m pytest tests/test_complexity_routing.py` | ❌ W0 | ⬜ pending |
| 05-04-01 | 04 | 2 | INFRA-07 | unit | `python -m pytest tests/test_prompt_assets.py` | ❌ W0 | ⬜ pending |
| 05-05-01 | 05 | 2 | DB-02 | integration | `skill-pipeline deal-agent --deal stec` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_db_load.py` — stubs for DB-01 (DuckDB schema, loading, upsert)
- [ ] `tests/test_db_export.py` — stubs for DB-03 (CSV export from DuckDB, format parity)
- [ ] `tests/test_complexity_routing.py` — stubs for PROMPT-06 (threshold logic, routing decisions)
- [ ] `tests/test_prompt_assets.py` — stubs for INFRA-07 (few-shot example loading)
- [ ] `duckdb` added to pyproject.toml dependencies

*Existing test infrastructure (pytest, conftest.py) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end orchestration processes stec | DB-02 | Requires local-agent extraction step | Run `skill-pipeline deal-agent --deal stec`, then execute each stage manually |
| CSV export matches JSON-based baseline | DB-03 | Requires existing stec export for comparison | Diff `db-export` output against existing `deal_events.csv` |
| All 9 deals process through full pipeline | DB-02 | Requires corpus-wide batch run | Run orchestration for all 9 deals, check for failures |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
