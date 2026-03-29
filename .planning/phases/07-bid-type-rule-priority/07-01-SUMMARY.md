---
phase: 07-bid-type-rule-priority
plan: 01
subsystem: enrichment
tags: [enrich-core, bid-type, classification, rule-priority]

requires:
  - phase: 06-deterministic-hardening
    provides: stable enrich-core with gate prerequisites and test infrastructure
provides:
  - "_classify_proposal() with correct rule evaluation order: explicit formal (1) -> process position (2) -> informal (3) -> selective round (4) -> residual (5)"
  - "Regression tests covering both promotion (final-round -> Formal) and non-promotion (early IOI -> Informal) directions"
affects: [enrich-core, db-load, db-export, reconciliation]

tech-stack:
  added: []
  patterns:
    - "Rule priority in _classify_proposal: strongest evidence first, process context second, signal language third"

key-files:
  created: []
  modified:
    - skill_pipeline/enrich_core.py
    - tests/test_skill_enrich_core.py

key-decisions:
  - "Process position (after_final_round_*) overrides informal language signals -- filing context trumps IOI wording"
  - "Eliminated fractional rule_applied=2.5; all rules now use integer numbering 1-5"

patterns-established:
  - "bid_type classification rule order: explicit formal > process position > informal signals > selective round > residual"

requirements-completed: [ENRICH-01]

duration: 2min
completed: 2026-03-29
---

# Phase 7 Plan 1: Bid-Type Rule Priority Summary

**Reordered _classify_proposal() so process position (final-round context) overrides informal language signals, fixing Informal misclassification across 5+ deals**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-29T22:47:27Z
- **Completed:** 2026-03-29T22:49:48Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Fixed highest-impact enrichment bug: final-round proposals no longer misclassified as Informal when IOI language present
- Reordered rule evaluation: explicit formal (Rule 1) -> process position (Rule 2) -> informal signals (Rule 3) -> selective round (Rule 4) -> residual (Rule 5)
- Added 4 new/updated regression tests covering both promotion and non-promotion directions
- Eliminated fractional rule_applied=2.5; all rules use clean integer numbering
- Full test suite green: 291 tests, 0 failures

## Task Commits

Each task was committed atomically:

1. **Task 1: Write and update regression tests for rule priority reordering** - `6ca48fc` (test -- TDD RED phase)
2. **Task 2: Reorder _classify_proposal() rules and pass all tests** - `2ea4997` (fix -- TDD GREEN phase)

_TDD workflow: RED phase wrote 5 failing tests (4 new + 1 updated assertion), GREEN phase reordered production code to pass all 19 enrich-core tests._

## Files Created/Modified
- `skill_pipeline/enrich_core.py` - Reordered _classify_proposal() rule branches: explicit formal (1) before process position (2) before informal (3) before selective round (4) before residual (5)
- `tests/test_skill_enrich_core.py` - Replaced broken test_rule_1_overrides_rule_2_5_when_non_binding with test_process_position_overrides_informal_signals; added test_process_position_overrides_range_proposal, test_early_ioi_without_final_round_stays_informal, test_explicit_formal_overrides_informal_signals; updated rule_applied assertion from 2.5 to 2

## Decisions Made
- Process position (after_final_round_deadline, after_final_round_announcement) overrides informal language signals (contains_range, mentions_ioi, mentions_non_binding, mentions_preliminary). This reflects the domain reality that when a target committee has announced a final round, any proposal submitted in that context is functionally formal regardless of hedging language.
- Eliminated the fractional rule_applied=2.5 value. All rules now use integer numbering (1-5) which is cleaner for downstream analysis and DuckDB queries.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all changes are fully wired production code with passing tests.

## Next Phase Readiness
- enrich-core bid_type classification is now correct for the process-position override pattern
- Downstream db-load and db-export will produce corrected bid_type labels on next deal rerun
- Ready for Phase 8 (or remaining Phase 7 plans if any)

## Self-Check: PASSED

All files exist. All commit hashes verified.

---
*Phase: 07-bid-type-rule-priority*
*Completed: 2026-03-29*
