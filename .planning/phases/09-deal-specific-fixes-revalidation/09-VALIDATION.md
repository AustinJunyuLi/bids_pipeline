---
phase: 9
slug: deal-specific-fixes-revalidation
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-03-30
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >= 8.0 |
| **Config file** | `pytest.ini` |
| **Quick run command** | `python -m pytest -q` |
| **Full suite command** | `python -m pytest -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest -q`
- **After every plan wave:** Run `python -m pytest -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | EXTRACT-04 | manual + smoke | Inspect `data/skill/zep/extract/events_raw.json` post-extraction for NMC in grouped events | N/A (artifact) | ⬜ pending |
| 09-01-02 | 01 | 1 | RERUN-01 | integration | `skill-pipeline check/verify/coverage/gates/enrich-core/db-load/db-export --deal zep` | N/A (CLI) | ⬜ pending |
| 09-02-01 | 02 | 2 | EXTRACT-05 | manual + smoke | Inspect `data/skill/medivation/extract/events_raw.json` for coverage_notes/events consistency | N/A (artifact) | ⬜ pending |
| 09-02-02 | 02 | 2 | RERUN-01 | integration | `skill-pipeline check/verify/coverage/gates/enrich-core/db-load/db-export --deal medivation` | N/A (CLI) | ⬜ pending |
| 09-03-01 | 03 | 3 | RERUN-02 | manual | Compare cross-deal analysis to 2026-03-29 baseline | N/A (report) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements. Phase 9 adds zero new code; validation is artifact-level (checking output JSON and CSV files) and pipeline-level (all deterministic stages return success).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Zep NMC not in grouped 2014-cycle events | EXTRACT-04 | Artifact-level check on LLM-generated output | After re-extraction, load `events_raw.json`, find grouped proposal/drop events in 2014 cycle, verify `bidder_new_mountain_capital` absent from `actor_ids` |
| Medivation coverage_notes/events consistency | EXTRACT-05 | Artifact-level check on LLM-generated output | After re-extraction, verify every `evt_NNN` in `coverage_notes` exists in `events` array |
| 9-deal reconciliation improvement | RERUN-02 | Cross-deal comparison requires LLM-generated analysis | After both deals pass db-export, run `/reconcile-alex` for both, regenerate cross-deal analysis, compare atomic match rate and filing-contradicted claims vs 2026-03-29 baseline |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
