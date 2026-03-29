# Phase 7: bid_type Rule Priority - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 07-bid-type-rule-priority
**Areas discussed:** Rule priority restructuring, Override scope, Process-letter signal, Regression test design
**Mode:** --auto (all decisions auto-selected from recommended defaults)

---

## Rule Priority Restructuring

| Option | Description | Selected |
|--------|-------------|----------|
| Move Rule 2.5 above Rule 1 | Simplest fix — reorder existing rules so process position evaluates before informal signals | ✓ |
| Create new Rule 0.5 | Add a new top-priority rule for process position, keep existing rules in place | |
| Two-pass evaluation | First pass checks process position, second pass checks signals — more complex | |

**User's choice:** [auto] Move Rule 2.5 above Rule 1 (recommended default)
**Notes:** Matches success criteria wording exactly: "evaluates process-position rules before IOI-language rules." Minimal code change.

---

## Override Scope

| Option | Description | Selected |
|--------|-------------|----------|
| All informal signals | Process position overrides contains_range, mentions_IOI, mentions_preliminary, mentions_non_binding | ✓ |
| Only IOI-language signals | Override mentions_indication_of_interest and mentions_preliminary only | |
| All except contains_range | Override IOI language but not range proposals | |

**User's choice:** [auto] All informal signals (recommended default)
**Notes:** Reconciliation evidence includes range proposals (mac-gray Party B $17-19) and non-binding language (prov-worcester LOI) — both should be Formal in final rounds per M&A convention.

---

## Process-Letter Signal

| Option | Description | Selected |
|--------|-------------|----------|
| Incorporate into Rule 2 | Add requested_binding_offer_via_process_letter as a formal signal | |
| Use as process-position evidence | Treat as additional evidence for process position | |
| Leave unused | Don't change signal usage — process-position override already covers affected cases | ✓ |

**User's choice:** [auto] Leave unused (recommended default)
**Notes:** Adding new signal interpretation is scope creep. Process-position override already fixes imprivata case.

---

## Regression Test Design

| Option | Description | Selected |
|--------|-------------|----------|
| Flip existing test + add new cases | Update test_rule_1_overrides_rule_2_5 to expect Formal; add reconciliation-inspired fixtures | ✓ |
| Replace all bid_type tests | Rewrite entire test suite for new rule order | |
| Only add new tests | Keep existing tests, add new ones for the fixed behavior | |

**User's choice:** [auto] Flip existing test + add new cases (recommended default)
**Notes:** Documents the intentional behavior change. Must test both directions: final-round → Formal AND early-stage IOI → still Informal.

---

## Claude's Discretion

- Exact rule numbering in code comments
- Whether to extract process-position into a helper
- Test fixture structure and naming
- BidClassification.rule_applied value updates

## Deferred Ideas

- requested_binding_offer_via_process_letter incorporation — Phase 8
- Granular process-position tiers — future enrichment
- nda_subtype schema — Phase 8 (from Phase 6 deferral)
