# Phase 7 Handoff: Fix Rule 2 Over-Promotion

**Created:** 2026-03-30
**From:** Claude (adversarial audit with GPT 5.4 xhigh)
**For:** Codex pickup

## Problem

Phase 7 reordered `_classify_proposal()` in `skill_pipeline/enrich_core.py` to fix final-round proposals being misclassified as Informal. The fix works for the intended cases but **creates new false positives** on at least 2 live events where the old classification was correct.

Rule 2 (process position) is too blunt: it promotes ANY proposal with `after_final_round_announcement=true` or `after_final_round_deadline=true` to Formal, even when the proposal is clearly an informal range bid that happens to occur after a round announcement in the timeline.

## Current Rule Order (lines 209-273 of enrich_core.py)

```
Rule 1: Explicit formal (draft_merger_agreement, marked_up_agreement, binding_offer) -> Formal
Rule 2: Process position (after_final_round_deadline OR after_final_round_announcement) -> Formal  <-- TOO BLUNT
Rule 3: Informal signals (contains_range, mentions_IOI, mentions_preliminary, mentions_non_binding) -> Informal
Rule 4: After selective round -> Formal
Rule 5: Residual -> Uncertain
```

## Confirmed False Positives

### stec evt_025 (STRONGEST EVIDENCE)
- **Summary:** "WDC returned with a revised written $6.60 to $7.10 per share indication of interest"
- **Signals:** `contains_range=true`, `mentions_indication_of_interest=true`, `after_final_round_announcement=true`, `after_final_round_deadline=true`
- **Reconciliation:** "Both agree: Informal, $6.60-$7.10, all_cash=1" (exact match — pipeline and Alex agreed pre-fix)
- **File:** `data/skill/stec/extract/events_raw.json` line 922
- **Reconciliation:** `data/skill/stec/reconcile/reconciliation_report.json` line 241
- **Impact:** Phase 7 Rule 2 flips this from Informal (correct) to Formal (wrong)

### saks evt_013 (STRONG EVIDENCE)
- **Summary:** "Sponsor E and Sponsor G submitted a $14.50 to $15.50 per share joint proposal that required more diligence and did not include a draft merger agreement or financing support"
- **Signals:** `contains_range=true`, `after_final_round_announcement=true`, `requested_binding_offer_via_process_letter=true`
- **File:** `data/skill/saks/extract/events_raw.json` line 475
- **Impact:** Phase 7 Rule 2 flips this from Informal to Formal, but the proposal explicitly lacks binding docs

### stec evt_026 (NEEDS VERIFICATION)
- Check `data/skill/stec/extract/events_raw.json` and reconciliation report

## Cases That Must Still Be Fixed (the original bug)

These 5 cases from the reconciliation analysis MUST still classify as Formal after the fix:

| Deal | Event | Old Classification | Required | Why |
|------|-------|--------------------|----------|-----|
| mac-gray | Party A $18 (Sep 18) | Informal | Formal | Final-round deadline response |
| mac-gray | Party B $17-19 (Sep 18) | Informal | Formal | Final-round deadline response |
| stec | WDC $9.15 (May 28) | Informal | Formal | Marked merger agreement attached |
| prov-worcester | G&W $25 revised LOI | Informal | Formal | 24-hour expiry, merger mark-ups |
| imprivata | $19.25 best-and-final | Informal | Formal | Solicited via process letter |

Note: stec WDC $9.15 already has `includes_marked_up_agreement=true` in its extraction, so it would be caught by Rule 1 (explicit formal) regardless of Rule 2. Verify this.

## Suggested Fix Direction

Narrow Rule 2 so process position does NOT override when strong informal counter-evidence is present. Possible approaches:

### Approach A: Conditional override
Rule 2 only fires when process-position flags are true AND no `contains_range` signal is present. Rationale: a range bid is inherently informal regardless of timing.

### Approach B: Combined signal check
Rule 2 only fires when process-position flags are true AND at least one compliance signal is also present (e.g., `requested_binding_offer_via_process_letter`, or explicit terms without a range).

### Approach C: Negative evidence gate
Rule 2 fires on process position UNLESS `contains_range=true` AND (`includes_draft_merger_agreement=false` AND `includes_marked_up_agreement=false`). This captures "range bid without binding docs = still informal."

**Recommendation:** Approach A is simplest and handles both confirmed false positives. But verify against all 9 deals before committing.

## Verification Protocol

After any fix, run this on all deals with proposal events that have `after_final_round_*=true`:

```bash
# For each affected deal, run enrich-core and check bid_classifications
for deal in stec saks mac-gray imprivata penford petsmart-inc providence-worcester medivation zep; do
  skill-pipeline enrich-core --deal $deal 2>/dev/null && \
  python3 -c "
import json
from pathlib import Path
p = Path('data/skill/$deal/enrich/deterministic_enrichment.json')
if p.exists():
    d = json.loads(p.read_text())
    for eid, cls in d.get('bid_classifications', {}).items():
        print(f'$deal {eid}: {cls[\"label\"]} (rule {cls[\"rule_applied\"]})')
" 2>/dev/null
done
```

Then diff against the reconciliation reports to confirm no new false positives.

## Key Files

| File | What | Lines |
|------|------|-------|
| `skill_pipeline/enrich_core.py` | `_classify_proposal()` | 209-273 |
| `skill_pipeline/models.py` | `FormalitySignals` model | ~155-167 |
| `tests/test_skill_enrich_core.py` | bid_type tests | 461-618 |
| `data/reconciliation_cross_deal_analysis.md` | Cross-deal analysis | Systematic Difference #3 |
| `data/skill/stec/reconcile/reconciliation_report.json` | stec reconciliation | evt_025 at line 241 |
| `data/skill/saks/reconcile/reconciliation_report.json` | saks reconciliation | evt_013 at line 329 |

## Constraints

- Python 3.11+, Pydantic-first, snake_case
- Fail-fast: no silent fallbacks
- Filing text is the only factual source of truth
- `deterministic_enrichment.json` output must be reproducible
- Benchmark/reconciliation data is POST-EXPORT only (diagnostic, not generation input)
- But reconciliation reports document agreed-upon correct classifications that regressions should not break
- Tests in `tests/test_skill_enrich_core.py` — run with `python -m pytest tests/test_skill_enrich_core.py -q`
- Full suite: `python -m pytest -q` (291 tests, ~2s)

## Test Requirements

After fixing, add these regression tests:
1. Range proposal with `after_final_round_announcement=true` but no binding docs -> should remain **Informal** (stec evt_025 pattern)
2. Range proposal with `after_final_round_announcement=true` AND `contains_range=true` -> should remain **Informal** (saks evt_013 pattern)
3. Non-range proposal with `after_final_round_deadline=true` AND `mentions_non_binding=true` but no `contains_range` -> should be **Formal** (the intended fix for mac-gray/imprivata)
4. Existing tests must still pass

## Out of Scope

- Penford oral proposals (Uncertain -> should be Informal) — Phase 8 EXTRACT-02
- `requested_binding_offer_via_process_letter` signal incorporation — deferred per D-06
- Extraction data quality fixes — Phase 9
