# Phase 7: bid_type Rule Priority - Research

**Researched:** 2026-03-29
**Domain:** Deterministic bid classification rule ordering in enrich-core
**Confidence:** HIGH

## Summary

Phase 7 fixes the highest-impact enrichment bug: `_classify_proposal()` in `enrich_core.py` evaluates informal-signal detection (Rule 1) before both explicit-formal signals (Rule 2) and process-position signals (Rule 2.5). This causes final-round proposals to be misclassified as Informal across at least 5 deals when filing language uses "indication of interest" or "non-binding" terminology.

The fix is a mechanical reordering of the rule evaluation branches in a single function. No model changes, no schema changes, no new dependencies. The function is 63 lines (209-272), self-contained, and already well-structured with numbered rules. The existing test suite (16 tests, 0.15s runtime) provides a green baseline, and the specific test `test_rule_1_overrides_rule_2_5_when_non_binding` explicitly asserts the broken behavior and must be flipped.

**Primary recommendation:** Reorder rule evaluation in `_classify_proposal()` to: Rule 2 (explicit formal) -> Rule 2.5 (process position) -> Rule 1 (informal signals) -> Rule 3 (selective round) -> Rule 4 (residual). Update the one inverted test, add new regression tests for both promotion and non-promotion, then validate against 5 affected deals.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Move Rule 2.5 (process position: `after_final_round_announcement` / `after_final_round_deadline`) above Rule 1 (informal signals: `contains_range`, `mentions_indication_of_interest`, `mentions_preliminary`, `mentions_non_binding`) in `_classify_proposal()`. This is the simplest correct fix and matches the success criteria wording: "evaluates process-position rules before IOI-language rules."
- **D-02:** Rule 2 (explicit formal signals: `includes_draft_merger_agreement`, `includes_marked_up_agreement`, `mentions_binding_offer`) stays above both. Explicit formal evidence is the strongest signal and should fire first.
- **D-03:** New rule evaluation order: Rule 2 (explicit formal) -> Rule 2.5 (process position) -> Rule 1 (informal signals) -> Rule 3 (selective round) -> Rule 4 (residual/Uncertain). Renumber rules in code comments to reflect the new priority.
- **D-04:** Process position overrides ALL informal signals, not just IOI-language ones. Reconciliation evidence: mac-gray Party B $17-19 has `contains_range=True` (range proposal) but is a final-round deadline response and should be Formal. Providence-worcester has `mentions_non_binding` (LOI language) with merger mark-ups and 24h expiry -- should be Formal. M&A convention: final-round submissions are Formal regardless of filing terminology.
- **D-05:** The override is one-directional: process position promotes to Formal, but does NOT demote. A proposal with `includes_draft_merger_agreement=True` is already Formal via Rule 2 regardless of process position.
- **D-06:** `requested_binding_offer_via_process_letter` remains unused in the current rule set. Adding new signal interpretation is scope creep.
- **D-07:** The existing test `test_rule_1_overrides_rule_2_5_when_non_binding` must be flipped to expect Formal (was Informal). This is an intentional behavior change, not a test bug. The test name should be updated to reflect the new expected behavior.
- **D-08:** New regression tests must cover both directions: (a) proposals after final round with informal signals -> Formal, and (b) early-stage IOIs before any final round -> still Informal.
- **D-09:** Regression fixtures should use the specific deal patterns from the reconciliation analysis as inspiration but do not need to replicate exact deal data. Synthetic fixtures with the relevant signal combinations are sufficient.

### Claude's Discretion
- Exact rule numbering in code comments (renumbering to sequential 1-5 vs keeping historical numbers with reordering)
- Whether to extract process-position evaluation into a separate helper or keep it inline
- Exact test fixture structure and naming
- Whether the `rule_applied` field values in `BidClassification` should be updated to match new numbering

### Deferred Ideas (OUT OF SCOPE)
- `requested_binding_offer_via_process_letter` signal incorporation into formal rules -- Phase 8 can evaluate
- More granular process-position detection (e.g., "after 2nd round but before final round" as a separate tier) -- future enrichment improvement
- `nda_subtype` schema for precise NDA classification -- already deferred to Phase 8 from Phase 6
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ENRICH-01 | bid_type classification promotes final-round proposals to Formal when process position (after final round announcement) overrides IOI filing language | Full code audit of `_classify_proposal()` confirms mechanical reordering fixes the root cause. 6 conflict events identified across 3 deals (mac-gray, stec, imprivata) with both process-position and informal signals. Providence-worcester additionally benefits from Rule 2 now firing before Rule 1 for proposals with both `mentions_non_binding` and `includes_marked_up_agreement`. |
</phase_requirements>

## Standard Stack

No new libraries needed. This phase modifies only existing Python code and tests.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | already installed | `BidClassification`, `FormalitySignals` models | Existing schema layer, no changes needed |
| pytest | 8.3.4 | regression test execution | Already configured, 16 enrich-core tests |

### Supporting
None -- no new dependencies.

### Alternatives Considered
None -- this is a code change to existing logic, not a technology decision.

## Architecture Patterns

### Target File Structure (unchanged)
```
skill_pipeline/
  enrich_core.py         # _classify_proposal() lines 209-272 -- THE fix
tests/
  test_skill_enrich_core.py  # 16 existing tests, 1 to update, 2+ to add
```

### Pattern 1: Rule-Priority Classification
**What:** `_classify_proposal()` applies numbered rules in priority order, returning the first `BidClassification` match. Each rule branch is self-contained with a return statement.
**When to use:** This is the existing pattern. The fix is reordering branches, not restructuring.
**Current order (broken):**
```python
# Rule 1: Informal  (fires on contains_range, mentions_ioi, etc.)
# Rule 2: Formal    (fires on draft_merger, marked_up, binding)
# Rule 2.5: Formal  (fires on after_final_round_*)
# Rule 3: Formal    (fires on selective round)
# Rule 4: Uncertain (residual)
```
**New order (fix):**
```python
# Rule 1: Explicit Formal  (draft_merger, marked_up, binding)
# Rule 2: Process Position  (after_final_round_announcement/deadline)
# Rule 3: Informal Signals  (contains_range, ioi, preliminary, non_binding)
# Rule 4: Selective Round   (proposal after selective final round)
# Rule 5: Residual          (Uncertain)
```

### Pattern 2: BidClassification Output Schema
**What:** Each rule returns `BidClassification(label, rule_applied, basis)`. The `rule_applied` field is a float (historically 1, 2, 2.5, 3, None).
**Schema (unchanged):**
```python
class BidClassification(SkillModel):
    label: Literal["Formal", "Informal", "Uncertain"]
    rule_applied: float | None = None
    basis: str
```
**Discretion note:** The `rule_applied` values can be renumbered to sequential integers (1, 2, 3, 4, None) to match the new comment numbering, or kept as historical values with updated comments. Sequential is cleaner -- no downstream consumers depend on specific float values. The `rule_applied` field is informational.

### Pattern 3: Integration Test Fixtures
**What:** Tests use `_write_enrich_core_fixture()` with `events_override` parameter to create synthetic deal fixtures. Each test writes fixture files to `tmp_path`, runs `run_enrich_core()`, then reads the JSON output artifact.
**Example (existing test at line 461):**
```python
def test_rule_2_5_classifies_after_final_round_deadline_as_formal(tmp_path):
    formality_signals = {
        "after_final_round_deadline": True,
        # ... all other signals False
    }
    events = [
        _base_event("evt_001", "target_sale"),
        _base_event("evt_002", "nda", actor_ids=["party_a"]),
        _base_event("evt_003", "proposal", actor_ids=["party_a"],
                    formality_signals=formality_signals),
        _base_event("evt_004", "executed", ...),
    ]
    _write_enrich_core_fixture(tmp_path, events_override=events)
    _write_gate_artifacts(tmp_path)
    run_enrich_core("imprivata", project_root=tmp_path)
    # ... read artifact and assert
```

### Anti-Patterns to Avoid
- **Restructuring the function:** Keep the same single-function, sequential-if-return pattern. Do not convert to a strategy pattern, rule engine, or scoring system. The existing structure is simple and correct.
- **Adding new signals:** D-06 explicitly defers `requested_binding_offer_via_process_letter`. Do not interpret additional signals.
- **Changing the model:** `FormalitySignals` and `BidClassification` schemas are correct as-is. No field additions or removals.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rule evaluation | Rule engine or scoring system | Sequential if-return branches | The existing pattern is 63 lines and trivially auditable. A rule engine adds complexity for 5 branches. |
| Test fixtures | Real deal data loading | Synthetic `_base_event()` + `_write_enrich_core_fixture()` | Tests must be deterministic, fast, and independent of on-disk deal data. Existing helpers are sufficient. |

## Common Pitfalls

### Pitfall 1: Over-Promotion of Early-Stage IOIs
**What goes wrong:** If process position is checked too broadly, proposals before any formal round could be promoted.
**Why it happens:** Both `after_final_round_announcement` and `after_final_round_deadline` are extraction-time signals set by the LLM. If the LLM sets them incorrectly, the rule would over-promote.
**How to avoid:** The rule only fires when these boolean signals are True. The fix does not change WHEN the signals are set -- only the priority order of evaluation. Regression tests must explicitly cover the case where these signals are False and informal signals are present (early IOI case).
**Warning signs:** A deal with no final round events showing Formal proposals.

### Pitfall 2: Breaking Providence-Worcester's Implicit Fix
**What goes wrong:** Providence-worcester proposals (evt_006/007/008/009/018) have both `mentions_non_binding=True` AND `includes_marked_up_agreement=True`. The current code incorrectly classifies these as Informal because Rule 1 fires before Rule 2. After the fix, Rule 1 (now Rule 2, explicit formal) fires first, catching these as Formal.
**Why it happens:** The reordering fixes TWO problems simultaneously -- process-position priority AND explicit-formal priority over informal signals.
**How to avoid:** Verify providence-worcester results after re-enrichment. These events should go from Informal to Formal via the explicit-formal rule (Rule 1 in new numbering), not the process-position rule (Rule 2 in new numbering).
**Warning signs:** If prov-worcester still shows Informal on evt_006/007/008/009/018 after the fix.

### Pitfall 3: `rule_applied` Value Regression
**What goes wrong:** If `rule_applied` float values are changed, downstream consumers that log or display them could show confusing values.
**Why it happens:** Historical values were 1, 2, 2.5, 3, None. Renumbering to 1, 2, 3, 4, None changes what existing enrichment artifacts contain.
**How to avoid:** The `rule_applied` field is informational (not consumed by `_compute_formal_boundary()` or `db-load`). Renumbering is safe but should be documented. Update all test assertions that reference specific `rule_applied` values.
**Warning signs:** Test assertions failing on `rule_applied` values after renumbering.

### Pitfall 4: Formal Boundary Shift
**What goes wrong:** `_compute_formal_boundary()` finds the first Formal proposal per cycle. If the rule change promotes an earlier proposal to Formal, the boundary shifts earlier in the timeline.
**Why it happens:** This is correct and expected behavior. The boundary was wrong before because the classification was wrong.
**How to avoid:** This is not a bug -- it is the intended effect of the fix. No prevention needed. Just verify that `formal_boundary` in the enrichment output makes sense for affected deals.
**Warning signs:** None -- a boundary shift is expected.

## Code Examples

### Current `_classify_proposal()` (broken order, lines 209-272)
```python
def _classify_proposal(
    evt: SkillEventRecord,
    rounds: list[dict],
    event_order: list[str],
) -> BidClassification:
    sig = evt.formality_signals
    if not sig:
        return BidClassification(label="Uncertain", rule_applied=None,
                                  basis="No formality_signals; residual case.")

    # Rule 1: Informal  <-- fires first, catches final-round IOIs
    if (sig.contains_range or sig.mentions_indication_of_interest
        or sig.mentions_preliminary or sig.mentions_non_binding):
        return BidClassification(label="Informal", rule_applied=1, ...)

    # Rule 2: Formal  <-- never reached when Rule 1 matches
    if (sig.includes_draft_merger_agreement or sig.includes_marked_up_agreement
        or sig.mentions_binding_offer):
        return BidClassification(label="Formal", rule_applied=2, ...)

    # Rule 2.5: After final round  <-- never reached when Rule 1 matches
    if sig.after_final_round_deadline or sig.after_final_round_announcement:
        return BidClassification(label="Formal", rule_applied=2.5, ...)
    # ...
```

### Fixed `_classify_proposal()` (correct order per D-01/D-02/D-03)
```python
def _classify_proposal(
    evt: SkillEventRecord,
    rounds: list[dict],
    event_order: list[str],
) -> BidClassification:
    sig = evt.formality_signals
    if not sig:
        return BidClassification(label="Uncertain", rule_applied=None,
                                  basis="No formality_signals; residual case.")

    # Rule 1: Explicit formal signals (strongest evidence)
    if (sig.includes_draft_merger_agreement or sig.includes_marked_up_agreement
        or sig.mentions_binding_offer):
        return BidClassification(label="Formal", rule_applied=1,
            basis="Observable formal signal from formality_signals.")

    # Rule 2: Process position (final-round context overrides language)
    if sig.after_final_round_deadline or sig.after_final_round_announcement:
        return BidClassification(label="Formal", rule_applied=2,
            basis="Proposal after final round announcement/deadline; "
                  "process position overrides informal language.")

    # Rule 3: Informal signals
    if (sig.contains_range or sig.mentions_indication_of_interest
        or sig.mentions_preliminary or sig.mentions_non_binding):
        return BidClassification(label="Informal", rule_applied=3,
            basis="Observable informal signal from formality_signals.")

    # Rule 4: Formal after selective round
    evt_idx = event_order.index(evt.event_id) if evt.event_id in event_order else -1
    for r in reversed(rounds):
        ann_idx = (event_order.index(r["announcement_event_id"])
                   if r["announcement_event_id"] in event_order else -1)
        if ann_idx >= 0 and evt_idx > ann_idx and r.get("is_selective"):
            return BidClassification(label="Formal", rule_applied=4,
                basis="Proposal after selective final round.")

    # Rule 5: Residual -> Uncertain
    return BidClassification(label="Uncertain", rule_applied=None,
        basis="No deterministic rule matched; residual case.")
```

### Test Update: Flip the Inverted Test (D-07)
```python
def test_process_position_overrides_informal_signals(tmp_path: Path) -> None:
    """Proposal with mentions_non_binding=True AND after_final_round_deadline=True -> Formal via Rule 2."""
    formality_signals = {
        "contains_range": False,
        "mentions_indication_of_interest": False,
        "mentions_preliminary": False,
        "mentions_non_binding": True,        # informal signal present
        "mentions_binding_offer": False,
        "includes_draft_merger_agreement": False,
        "includes_marked_up_agreement": False,
        "requested_binding_offer_via_process_letter": False,
        "after_final_round_announcement": False,
        "after_final_round_deadline": True,   # process position overrides
        "is_subject_to_financing": None,
    }
    # ... same fixture setup ...
    classification = artifact["bid_classifications"]["evt_003"]
    assert classification["label"] == "Formal"   # was "Informal"
    assert classification["rule_applied"] == 2    # was 1
```

### New Test: Early IOI Without Final Round Stays Informal (D-08)
```python
def test_early_ioi_without_final_round_stays_informal(tmp_path: Path) -> None:
    """Proposal with mentions_indication_of_interest=True but NO process position -> Informal."""
    formality_signals = {
        "contains_range": False,
        "mentions_indication_of_interest": True,  # informal signal
        "mentions_preliminary": False,
        "mentions_non_binding": False,
        "mentions_binding_offer": False,
        "includes_draft_merger_agreement": False,
        "includes_marked_up_agreement": False,
        "requested_binding_offer_via_process_letter": False,
        "after_final_round_announcement": False,  # no process position
        "after_final_round_deadline": False,       # no process position
        "is_subject_to_financing": None,
    }
    # ... fixture setup ...
    classification = artifact["bid_classifications"]["evt_003"]
    assert classification["label"] == "Informal"
    assert classification["rule_applied"] == 3  # new Rule 3 (was Rule 1)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Rule 1 (informal) fires before Rule 2 (formal) | Rule 1 (formal) fires before Rule 3 (informal) | This phase | Fixes 6+ misclassified events across 3 deals via process-position; fixes 5+ misclassified events in prov-worcester via explicit-formal priority |

## Open Questions

None. All implementation decisions are locked. The code change is well-scoped and all affected events have been inventoried.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3.4 |
| Config file | pyproject.toml (implicit) |
| Quick run command | `python -m pytest tests/test_skill_enrich_core.py -q` |
| Full suite command | `python -m pytest -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ENRICH-01a | Process position overrides informal signals -> Formal | unit | `python -m pytest tests/test_skill_enrich_core.py::test_process_position_overrides_informal_signals -x` | Wave 0 (update existing test_rule_1_overrides_rule_2_5_when_non_binding) |
| ENRICH-01b | Process position with range -> Formal (mac-gray pattern) | unit | `python -m pytest tests/test_skill_enrich_core.py::test_process_position_overrides_range_proposal -x` | Wave 0 |
| ENRICH-01c | Early IOI without final round -> Informal | unit | `python -m pytest tests/test_skill_enrich_core.py::test_early_ioi_without_final_round_stays_informal -x` | Wave 0 |
| ENRICH-01d | Explicit formal beats informal even without process position | unit | `python -m pytest tests/test_skill_enrich_core.py::test_explicit_formal_overrides_informal_signals -x` | Wave 0 |
| ENRICH-01e | Existing Rule 2.5 test (no-conflict case) still passes | unit | `python -m pytest tests/test_skill_enrich_core.py::test_rule_2_5_classifies_after_final_round_deadline_as_formal -x` | Existing -- must update rule_applied assertion |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_skill_enrich_core.py -q`
- **Per wave merge:** `python -m pytest -q`
- **Phase gate:** Full suite green + 5-deal re-enrichment validation

### Wave 0 Gaps
- [ ] Rename `test_rule_1_overrides_rule_2_5_when_non_binding` and flip assertions (ENRICH-01a)
- [ ] Add `test_process_position_overrides_range_proposal` (ENRICH-01b)
- [ ] Add `test_early_ioi_without_final_round_stays_informal` (ENRICH-01c)
- [ ] Add `test_explicit_formal_overrides_informal_signals` (ENRICH-01d)
- [ ] Update `rule_applied` assertion in existing `test_rule_2_5_classifies_after_final_round_deadline_as_formal` if renumbered

## Affected Events Inventory

Verified from on-disk artifacts. These events will change classification after the fix.

### Process-Position Conflicts (Rule 2.5 -> now Rule 2 will fire instead of old Rule 1)
| Deal | Event | Current | Expected | Informal Signal | Process Signal |
|------|-------|---------|----------|-----------------|----------------|
| mac-gray | evt_022 | Informal (rule 1) | Formal (rule 2) | contains_range, mentions_ioi | after_final_round_announcement |
| mac-gray | evt_023 | Informal (rule 1) | Formal (rule 2) | mentions_ioi | after_final_round_announcement |
| stec | evt_020 | Informal (rule 1) | Formal (rule 2) | mentions_ioi | after_final_round_announcement |
| stec | evt_025 | Informal (rule 1) | Formal (rule 2) | contains_range, mentions_ioi | after_final_round_announcement, after_final_round_deadline |
| stec | evt_026 | Informal (rule 1) | Formal (rule 2) | mentions_ioi | after_final_round_announcement, after_final_round_deadline |
| imprivata | evt_026 | Informal (rule 1) | Formal (rule 2) | mentions_non_binding | after_final_round_announcement, after_final_round_deadline |

### Explicit-Formal vs Informal Conflicts (Rule 2 -> now Rule 1 will fire instead of old Rule 1)
| Deal | Event | Current | Expected | Informal Signal | Formal Signal |
|------|-------|---------|----------|-----------------|---------------|
| prov-worcester | evt_006 | Informal (rule 1) | Formal (rule 1) | mentions_non_binding | includes_marked_up_agreement |
| prov-worcester | evt_007 | Informal (rule 1) | Formal (rule 1) | mentions_non_binding | includes_marked_up_agreement |
| prov-worcester | evt_008 | Informal (rule 1) | Formal (rule 1) | mentions_non_binding | includes_marked_up_agreement |
| prov-worcester | evt_009 | Informal (rule 1) | Formal (rule 1) | mentions_non_binding | includes_marked_up_agreement |
| prov-worcester | evt_018 | Informal (rule 1) | Formal (rule 1) | mentions_non_binding | includes_marked_up_agreement |

### Penford Note
Penford proposals (evt_005, evt_019) are Uncertain with no formality signals at all. They are not affected by rule reordering. The reconciliation table listed penford as affected, but the process-position signals are not set on penford proposals.

## Project Constraints (from CLAUDE.md)

- **Fail fast:** Do not add silent fallbacks or broad try/except. The existing `_classify_proposal()` already follows this.
- **No overengineering:** Simplest correct path. Sequential if-return is the correct pattern.
- **No scope expansion:** Only fix ENRICH-01. Do not incorporate `requested_binding_offer_via_process_letter`.
- **Regression tests:** Add focused regression tests for behavior changes (especially around enrichment).
- **Coding style:** Python 3.11+, explicit types on public functions, Pydantic-first schema, snake_case.
- **Commit guidance:** Concise imperative subjects, conventional prefixes (fix:, test:).

## Sources

### Primary (HIGH confidence)
- `skill_pipeline/enrich_core.py` -- full audit of `_classify_proposal()` (lines 209-272), `_classify_proposals()` (lines 275-286), `_compute_formal_boundary()` (lines 323-361)
- `skill_pipeline/models.py` -- `FormalitySignals` (lines 157-168), `BidClassification` (lines 369-372)
- `tests/test_skill_enrich_core.py` -- all 16 tests read, green baseline verified (16 passed, 0.15s)
- On-disk enrichment artifacts for 5 affected deals -- all `bid_classifications` entries inventoried
- On-disk extraction artifacts for 5 deals -- all `formality_signals` inspected for conflict patterns
- `data/reconciliation_cross_deal_analysis.md` -- Systematic Difference #3 root cause analysis

### Secondary (MEDIUM confidence)
- `.claude/skills/enrich-deal/SKILL.md` -- confirmed deterministic core runs before interpretive layer

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, existing code only
- Architecture: HIGH -- full audit of target function and all consumers
- Pitfalls: HIGH -- all affected events inventoried from live artifacts, conflict patterns verified

**Research date:** 2026-03-29
**Valid until:** Indefinite (code-only change to existing function)
