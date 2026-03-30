---
phase: 09-deal-specific-fixes-revalidation
verified: 2026-03-30T15:47:08Z
status: passed
score: 4/4 must-haves verified
re_verification: false
---

# Phase 9: Deal-Specific Fixes + Revalidation Verification Report

**Phase Goal:** Known extraction errors in Zep and Medivation are corrected, affected deals are re-extracted with updated skill docs, and cross-deal reconciliation shows measurable improvement.

**Verified:** 2026-03-30T15:47:08Z  
**Status:** passed  
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Zep no longer includes New Mountain Capital in grouped 2014 proposal/drop actor sets | VERIFIED | A direct artifact check over `data/skill/zep/extract/events_raw.json` found zero grouped `proposal` / `drop` events containing `bidder_new_mountain_capital` in the refreshed 2014-cycle surface. The regenerated Zep summary and reconciliation report both describe the actor-set fix explicitly. |
| 2 | Medivation no longer has dangling `coverage_notes` event references and preserves the bidder-round chronology | VERIFIED | A direct scan over `data/skill/medivation/extract/events_raw.json` found no missing `evt_NNN` references in `coverage_notes`, and the refreshed extract contains `evt_013`, `evt_017`, `evt_027`, and `evt_029` as filing-grounded proposal/drop events. |
| 3 | Both affected deals were rerun through the full deterministic pipeline and produced refreshed export + reconciliation artifacts | VERIFIED | All required artifacts exist for both `zep` and `medivation`: extract, spans, canonicalize log, check, verify, coverage, gates, deterministic enrichment, `deal_events.csv`, and refreshed `reconcile/reconciliation_report.json`. |
| 4 | The refreshed 9-deal benchmark shows measurable improvement versus the 2026-03-29 baseline | VERIFIED | `data/reconciliation_cross_deal_analysis.md` reports `70.7% (157/222)` atomic match rate versus the `70.3% (156/222)` baseline and reduces Alex-favored contradictions from `16` to `13`. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `data/skill/zep/extract/events_raw.json` | Refreshed Zep extract with grouped 2014 actor-set fix | VERIFIED | No grouped 2014 proposal/drop row includes `bidder_new_mountain_capital`. |
| `data/skill/medivation/extract/events_raw.json` | Refreshed Medivation extract with internally consistent `coverage_notes` | VERIFIED | `evt_013`, `evt_017`, `evt_027`, and `evt_029` exist; no dangling `coverage_notes` refs remain. |
| `data/skill/zep/export/deal_events.csv` / `data/skill/medivation/export/deal_events.csv` | Post-rerun deterministic exports | VERIFIED | Both CSVs exist and were regenerated during Phase 9. |
| `data/skill/zep/reconcile/reconciliation_report.json` / `data/skill/medivation/reconcile/reconciliation_report.json` | Refreshed benchmark reconciliation reports | VERIFIED | Both reports are valid JSON and contain counts, arbitration summaries, and refreshed Phase 9 verdicts. |
| `data/reconciliation_cross_deal_analysis.md` | Refreshed 9-deal corpus memo with baseline comparison | VERIFIED | Includes `Baseline Comparison`, references `2026-03-29`, and states the refreshed `atomic match rate`. |

### Behavioral Spot-Checks

| Behavior | Command / Check | Result | Status |
|----------|-----------------|--------|--------|
| Phase 6-8 regression slice remains green after Phase 9 artifact refreshes | `python3 -m pytest -q tests/test_skill_mirror_sync.py tests/test_skill_enrich_core.py tests/test_skill_db_load.py tests/test_skill_db_export.py` | `79 passed in 5.36s` | PASS |
| Zep grouped 2014 actor-set fix | Direct JSON scan for grouped 2014 `proposal` / `drop` rows containing NMC | No violations found | PASS |
| Medivation `coverage_notes` integrity | Direct JSON scan for unresolved `evt_NNN` refs | No missing refs found | PASS |
| Cross-deal improvement surfaced | Direct markdown scan of `data/reconciliation_cross_deal_analysis.md` | Improvement metrics and baseline section present | PASS |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| EXTRACT-04 | Zep NMC actor error corrected | SATISFIED | Refreshed Zep extract passes the grouped-actor scan; `09-01-SUMMARY.md` and the refreshed Zep reconciliation report both reflect the fix. |
| EXTRACT-05 | Medivation missing drops / reference integrity corrected | SATISFIED | Refreshed Medivation extract now contains `evt_013`, `evt_017`, `evt_027`, and `evt_029`, and `coverage_notes` references resolve cleanly. |
| RERUN-01 | Affected deals rerun through full deterministic pipeline | SATISFIED | Both deals have regenerated canonicalize/check/verify/coverage/gates/enrich/export artifacts on disk. |
| RERUN-02 | 9-deal reconciliation rerun shows improvement vs baseline | SATISFIED | Refreshed cross-deal memo records `70.7%` atomic match rate and `13` Alex wins vs the `70.3%` / `16` baseline. |

### Human Verification Required

None. Phase 9 outcomes are verifiable from the regenerated artifacts and the benchmark memo already on disk.

### Gaps Summary

No phase-blocking gaps found. Phase 9 achieved the requested rerun-and-measure goal.

Residual attention item: the refreshed Zep reconciliation report still surfaces a coverage-note integrity concern around unmaterialized drop ids. That issue is now explicitly documented in the benchmark artifacts rather than hidden, but it should remain visible if a future follow-up phase revisits Zep extraction quality.

---

_Verified: 2026-03-30T15:47:08Z_  
_Verifier: Codex_
