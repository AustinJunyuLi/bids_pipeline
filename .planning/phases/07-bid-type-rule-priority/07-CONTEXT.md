# Phase 7: bid_type Rule Priority - Context

**Gathered:** 2026-03-29
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix highest-impact enrichment bug: final-round proposals misclassified as Informal across 5+ deals because Rule 1 (IOI-language signals) fires before Rule 2.5 (process-position signals). After this phase, `_classify_proposal()` evaluates process position before IOI language, so final-round responses are classified as Formal regardless of filing terminology.

Single requirement: ENRICH-01.

</domain>

<decisions>
## Implementation Decisions

### Rule priority restructuring
- **D-01:** Move Rule 2.5 (process position: `after_final_round_announcement` / `after_final_round_deadline`) above Rule 1 (informal signals: `contains_range`, `mentions_indication_of_interest`, `mentions_preliminary`, `mentions_non_binding`) in `_classify_proposal()`. This is the simplest correct fix and matches the success criteria wording: "evaluates process-position rules before IOI-language rules."
- **D-02:** Rule 2 (explicit formal signals: `includes_draft_merger_agreement`, `includes_marked_up_agreement`, `mentions_binding_offer`) stays above both. Explicit formal evidence is the strongest signal and should fire first.
- **D-03:** New rule evaluation order: Rule 2 (explicit formal) → Rule 2.5 (process position) → Rule 1 (informal signals) → Rule 3 (selective round) → Rule 4 (residual/Uncertain). Renumber rules in code comments to reflect the new priority.

### Override scope
- **D-04:** Process position overrides ALL informal signals, not just IOI-language ones. Reconciliation evidence: mac-gray Party B $17-19 has `contains_range=True` (range proposal) but is a final-round deadline response and should be Formal. Providence-worcester has `mentions_non_binding` (LOI language) with merger mark-ups and 24h expiry — should be Formal. M&A convention: final-round submissions are Formal regardless of filing terminology.
- **D-05:** The override is one-directional: process position promotes to Formal, but does NOT demote. A proposal with `includes_draft_merger_agreement=True` is already Formal via Rule 2 regardless of process position.

### Process-letter signal
- **D-06:** `requested_binding_offer_via_process_letter` remains unused in the current rule set. Adding new signal interpretation is scope creep — the process-position override already fixes the imprivata case ("solicited via process letter" is after final round). Phase 8 can decide whether to incorporate this signal.

### Regression test design
- **D-07:** The existing test `test_rule_1_overrides_rule_2_5_when_non_binding` must be flipped to expect Formal (was Informal). This is an intentional behavior change, not a test bug. The test name should be updated to reflect the new expected behavior.
- **D-08:** New regression tests must cover both directions: (a) proposals after final round with informal signals → Formal (mac-gray, imprivata, providence-worcester patterns), and (b) early-stage IOIs before any final round → still Informal (the fix must not over-promote).
- **D-09:** Regression fixtures should use the specific deal patterns from the reconciliation analysis as inspiration but do not need to replicate exact deal data. Synthetic fixtures with the relevant signal combinations are sufficient.

### Claude's Discretion
- Exact rule numbering in code comments (renumbering to sequential 1-5 vs keeping historical numbers with reordering)
- Whether to extract process-position evaluation into a separate helper or keep it inline
- Exact test fixture structure and naming
- Whether the `rule_applied` field values in `BidClassification` should be updated to match new numbering

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope
- `.planning/ROADMAP.md` — Phase 7 goal, success criteria, dependency on Phase 6
- `.planning/REQUIREMENTS.md` — ENRICH-01 requirement definition
- `.planning/PROJECT.md` — project constraints (correctness priority, fail-fast, filing-text-only truth)

### Evidence Sources
- `data/reconciliation_cross_deal_analysis.md` — Systematic Difference #3 (bid_type classification): root cause analysis, 5-deal affected examples, rule-ordering diagnosis

### Target Source Files
- `skill_pipeline/enrich_core.py` — `_classify_proposal()` at lines 209-272 (the function to fix), `_classify_proposals()` at lines 275-286, `ROUND_PAIRS` constant
- `skill_pipeline/models.py` — `FormalitySignals` model (lines 155-167), `BidClassification` model, `SkillEventRecord.formality_signals` field

### Existing Tests
- `tests/test_skill_enrich_core.py` — `test_rule_2_5_classifies_after_final_round_deadline_as_formal` (line 461), `test_rule_1_overrides_rule_2_5_when_non_binding` (line 493, must be updated)

### Prior Phase Context
- `.planning/phases/06-deterministic-hardening/06-CONTEXT.md` — Phase 6 decisions (D-07/D-08: rollover CA tolerance, NDA text-pattern approach); establishes that Phase 7 depends on hardened pipeline

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_classify_proposal()` in `enrich_core.py` — the exact function to modify. Well-structured with numbered rules and clear `BidClassification` return values.
- `BidClassification` model — already has `label`, `rule_applied`, and `basis` fields. Rule reordering just changes which rule fires; output schema is unchanged.
- `FormalitySignals` model — already has `after_final_round_announcement` and `after_final_round_deadline` booleans. No model changes needed.
- Existing test helpers in `test_skill_enrich_core.py` — `_make_canonical_fixtures()` pattern creates synthetic deal fixtures for enrich-core tests.

### Established Patterns
- Rule-based classification with numbered rules and explicit `BidClassification` return per branch
- `rule_applied` tracks which rule fired (float values: 1, 2, 2.5, 3, None)
- `basis` string documents the classification rationale
- Test fixtures use synthetic events with explicit `formality_signals` dicts

### Integration Points
- `_classify_proposal()` is called only by `_classify_proposals()` which iterates over all proposal events
- Output flows into `bid_classifications` dict in `deterministic_enrichment.json`
- `_compute_formal_boundary()` consumes bid classifications — reordering rules may change which proposals are first-Formal in a cycle
- `db-load` and `db-export` consume `deterministic_enrichment.json` — no schema change means no downstream changes needed

</code_context>

<specifics>
## Specific Ideas

- The reconciliation analysis (Systematic Difference #3) provides 5 concrete misclassification examples with filing reality checks — use these as regression test inspiration.
- mac-gray Party B $17-19 is the clearest test case: `contains_range=True` AND `after_final_round_deadline=True` — currently Informal, should be Formal.
- The existing test `test_rule_1_overrides_rule_2_5_when_non_binding` is the most important test to flip — it explicitly asserts the broken behavior.
- After fix, re-running `skill-pipeline enrich-core` on the 5 affected deals should show changed `bid_classifications` in `deterministic_enrichment.json` — this is the integration validation.

</specifics>

<deferred>
## Deferred Ideas

- `requested_binding_offer_via_process_letter` signal incorporation into formal rules — Phase 8 can evaluate
- More granular process-position detection (e.g., "after 2nd round but before final round" as a separate tier) — future enrichment improvement
- `nda_subtype` schema for precise NDA classification — already deferred to Phase 8 from Phase 6

</deferred>

---

*Phase: 07-bid-type-rule-priority*
*Context gathered: 2026-03-29*
