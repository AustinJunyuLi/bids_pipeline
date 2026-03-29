# Feature Landscape: v1.1 Reconciliation + Execution-Log Quality Fixes

**Domain:** M&A deal extraction pipeline -- enrichment correctness, event taxonomy expansion, and runtime hardening
**Researched:** 2026-03-29
**Overall Confidence:** HIGH (evidence-driven from 9-deal reconciliation + 7-deal execution logs)

---

## Table Stakes

Features that close demonstrated bugs or plug gaps exposed by real data. Missing = the pipeline produces known-incorrect output across multiple deals.

---

### TS-1: Fix bid_type Enrichment Rule Priority

| Attribute | Detail |
|-----------|--------|
| Why Expected | 5+ deals produce incorrect Formal/Informal classifications. This is the pipeline's single biggest systematic bug per the cross-deal reconciliation. |
| Complexity | Low |
| Dependencies | `enrich_core.py` `_classify_proposal()` only |
| Confidence | HIGH -- directly observable in reconciliation data |

**The Problem:** The current `_classify_proposal()` function in `enrich_core.py` (lines 209-272) applies Rule 1 (informal signals) before Rule 2.5 (after final round). When a final-round deadline response uses "indication of interest" language in the filing, Rule 1 fires first and labels it Informal. But M&A convention universally classifies final-round submissions as Formal regardless of filing terminology -- these are solicited responses to a process letter, submitted with merger agreement markups and financing commitments.

**Filing Reality (from reconciliation):**
- Mac-Gray: Party A $18 and Party B $17-19 (Sep 18) -- final-round deadline responses classified Informal
- STEC: WDC $9.15 (May 28) -- marked "merger agreement attached" but caught by IOI language first
- Providence-Worcester: G&W $25 revised LOI -- 24-hour expiry, merger mark-ups, still classified Informal
- Imprivata: $19.25 best-and-final -- solicited via process letter, still classified Informal

**The Fix:** Reorder rules so Rule 2.5 (after_final_round_announcement or after_final_round_deadline) takes priority over Rule 1's informal language signals. Specifically:

1. Rule 0 (new): If `after_final_round_deadline=true` or `after_final_round_announcement=true`, classify Formal. Rationale: a final-round response is definitionally formal in M&A, even if the filing uses "indication of interest" phrasing.
2. Rule 1 (demoted): Informal signals only apply to pre-final-round proposals.
3. Rules 2-4: Unchanged.

Additionally, insert a `requested_binding_offer_via_process_letter` check: if this flag is true, the proposal is Formal regardless of other signals -- a process letter requesting binding offers makes informality impossible.

**M&A Domain Basis:** In structured M&A auctions, the progression from IOI to LOI to definitive agreement is well-established. An "indication of interest" submitted in response to a final-round process letter is functionally a formal bid -- the terminology is an artifact of the filing drafter's prose style, not a substantive signal of informality. The seller's financial advisor has structured the round, set a deadline, and specified deliverables (markup of merger agreement, financing commitment letters). That context overrides any surface-level "indication of interest" language.

**Sources:**
- [Kimberly Advisors: IOI vs LOI](https://kimberlyadvisors.com/articles/indication-of-interest-ioi) -- IOI is non-binding early-stage; LOI is partially-binding final stage
- [Redmount: Two-Step M&A Bidding Process](https://redmountpartners.com/twostepsofmanda/) -- IOI is first round, LOI is second/final round
- `data/reconciliation_cross_deal_analysis.md` lines 69-82 -- 5-deal pattern of misclassification

---

### TS-2: Harden Canonicalize Against Duplicate quote_id Collisions

| Attribute | Detail |
|-----------|--------|
| Why Expected | Penford canonicalization failed on duplicate quote_ids. Multi-pass extraction (actors then events) can independently assign Q001, Q002, etc. |
| Complexity | Low |
| Dependencies | `canonicalize.py` `_resolve_quotes_to_spans()` only |
| Confidence | HIGH -- observed in 7-deal rerun (penford) |

**The Problem:** The `_resolve_quotes_to_spans()` function (line 88-142 of `canonicalize.py`) combines `raw_actors.quotes` and `raw_events.quotes` into one list (line 408), then checks for duplicate `quote_id` values and raises `ValueError` if found. But actors and events are extracted in separate LLM passes, each starting their quote IDs at Q001. Collision is guaranteed for any deal with both actor and event quotes.

**Current Workaround:** The 7-deal rerun manually renumbered event-side quote IDs above the actor-side max. This should be automated.

**The Fix:** Before merging quotes, renumber event-side quote_ids with an offset (e.g., event Q001 becomes Q{actor_max + 1}). Update all event `quote_ids` references correspondingly. This is a purely mechanical transformation -- no semantic change.

---

### TS-3: Harden Coverage Against False Positive NDA Cues

| Attribute | Detail |
|-----------|--------|
| Why Expected | Saks coverage reported spurious NDA findings from contextual confidentiality-agreement mentions that were not NDA-signing events. |
| Complexity | Low |
| Dependencies | `coverage.py` `_classify_cue_family()` |
| Confidence | HIGH -- observed in 7-deal rerun (saks) |

**The Problem:** The coverage module's NDA cue detection (lines 89-120 of `coverage.py`) catches phrases like "entered into a confidentiality agreement" but does not filter out backward-looking references like "which had executed a confidentiality agreement" in all sentence contexts. The existing `references_prior_executed_nda` filter covers some patterns but misses contextual mentions like "pursuant to their confidentiality agreement" or "under the terms of the confidentiality agreement" that reference a previously-signed NDA rather than a new signing event.

**The Fix:** Expand the exclusion phrases in `references_prior_executed_nda` and add a new filter for contextual NDA references that appear in non-signing contexts (e.g., "pursuant to", "under the terms of", "in accordance with"). The saks fix from the 7-deal rerun partially addresses this but may need additional patterns from other deals.

---

### TS-4: Harden check.py Grouped NDA Count Assertions

| Attribute | Detail |
|-----------|--------|
| Why Expected | Providence-Worcester check stage failed because grouped bidder actors' `group_size` was not counted toward NDA count assertions. |
| Complexity | Low |
| Dependencies | `check.py` `_check_nda_count_gaps()` |
| Confidence | HIGH -- observed in 7-deal rerun (providence-worcester) |

**The Problem:** The `_check_nda_count_gaps()` function (lines 174-219 of `check.py`) already uses `_counted_bidder_weight()` to count grouped actors by their `group_size`. However, the providence-worcester rerun log indicates this did not work correctly -- suggesting the grouped bidder either lacked a NDA event linkage or the `group_size` was not being used in the assertion comparison path. The fix applied during the rerun needs to be verified and regression-tested.

**The Fix:** Verify the existing `_counted_bidder_weight()` logic covers grouped actors with NDA evidence. Add regression tests for the providence-worcester pattern (grouped NDA-signing bidder cohorts with `group_size` > 1).

---

### TS-5: Fix Gates Rejecting Rollover-Side Confidentiality Agreements

| Attribute | Detail |
|-----------|--------|
| Why Expected | PetSmart gates rejected a Longview confidentiality agreement modeled as a sale-process NDA. Rollover-side agreements are not sale-process NDAs. |
| Complexity | Low |
| Dependencies | `gates.py` NDA-after-drop logic, extraction guidance |
| Confidence | HIGH -- observed in 7-deal rerun (petsmart-inc) |

**The Problem:** In leveraged buyouts, the existing management team or rollover investor signs confidentiality agreements related to their participation in the buyer's equity structure, not as sale-process bidders. When these get extracted as NDA events, the gates module's `nda_after_drop` rule fires because the rollover party was never an active sale-process bidder. The root fix is either (a) not extracting rollover-side confidentiality agreements as NDA events, or (b) teaching gates to distinguish rollover NDAs from sale-process NDAs.

**The Fix:** The cleaner approach is (a): update extraction guidance to exclude rollover-side confidentiality agreements from the NDA event type. These are operational agreements, not sale-process milestones. If extraction cannot reliably distinguish them, add a `nda_context` field (values: `sale_process`, `rollover`, `other`) to allow gates to filter appropriately.

---

### TS-6: Fix Zep NMC Actor Error

| Attribute | Detail |
|-----------|--------|
| Why Expected | NMC explicitly declined to bid per the Zep filing but is incorrectly included in evt_005/evt_008. This is a data correction, not a code fix. |
| Complexity | Low (extraction repair) |
| Dependencies | Extraction re-run or manual artifact correction for Zep |
| Confidence | HIGH -- filing text directly contradicts current extraction |

**The Problem:** The Zep filing states NMC explicitly declined to bid, yet the pipeline includes NMC in two events (evt_005 and evt_008). This is an extraction error -- the LLM included a party that the filing text explicitly excludes.

**The Fix:** Re-extract Zep with corrected guidance, or surgically repair the two affected events in the Zep extract artifacts. Add a regression note in the reconciliation report.

---

### TS-7: Fix Medivation Missing Drop Events

| Attribute | Detail |
|-----------|--------|
| Why Expected | evt_013 and evt_017 are referenced in coverage notes but absent from the events array. These are filing-grounded drops. |
| Complexity | Low (extraction repair) |
| Dependencies | Extraction re-run or manual artifact correction for Medivation |
| Confidence | HIGH -- coverage notes reference events that do not exist |

**The Fix:** Re-extract Medivation to include the missing drop events, or surgically add them to the events artifact with proper span evidence.

---

### TS-8: Fix DuckDB Transient Lock on db-export After db-load

| Attribute | Detail |
|-----------|--------|
| Why Expected | Zep db-export hit a transient DuckDB lock immediately after db-load; retry succeeded. |
| Complexity | Low |
| Dependencies | `db_load.py`, `db_export.py` |
| Confidence | HIGH -- observed in 7-deal rerun |

**The Problem:** DuckDB's WAL (write-ahead log) can hold a brief lock after a write transaction commits. When `db-export` runs immediately after `db-load` in the same orchestration, it can encounter this lock.

**The Fix:** Either (a) ensure `db-load` explicitly closes the connection and flushes the WAL before returning, or (b) add a brief retry loop (1-2 attempts, 500ms delay) in `db-export`'s `open_pipeline_db(read_only=True)` call. Option (a) is cleaner. DuckDB's `CHECKPOINT` command forces WAL flush.

---

## Differentiators

Features that improve the pipeline's analytical depth beyond what's minimally correct. Valuable but not required for correctness.

---

### D-1: DropTarget Event Classification in Enrichment

| Attribute | Detail |
|-----------|--------|
| Value Proposition | Distinguishes target-initiated exclusions from bidder-initiated withdrawals, capturing a critical M&A process dynamic. |
| Complexity | Medium |
| Dependencies | Existing `drop` events + `drop_reason_text` field; existing `DropoutClassification` model already has the label |
| Confidence | MEDIUM-HIGH -- domain logic is clear, but extraction quality of `drop_reason_text` determines effectiveness |

**What It Is:** When a target's special committee or board decides not to invite a bidder to the next round, that is a DropTarget -- fundamentally different from a bidder voluntarily withdrawing. The reconciliation shows Alex captures these (mac-gray, stec, prov-worcester, saks) while the pipeline does not.

**Current State:** The extraction skill (SKILL.md line 125-128) explicitly collapses all drops into the single `drop` type and instructs the LLM to preserve the narrative basis in `drop_reason_text`. The `DropoutClassification` model (`models.py` line 364) already includes `DropTarget` as a valid label. The `enrich-deal` skill (SKILL.md) already defines the DropTarget classification logic.

**What's Missing:** The deterministic `enrich_core.py` does not perform dropout classification at all -- it only handles rounds, bid classification, cycles, and formal boundary. Dropout classification currently lives only in the interpretive `enrich-deal` local-agent skill. To make DropTarget deterministic, the pipeline needs to:

1. Parse `drop_reason_text` for target-initiated exclusion signals (e.g., "the committee determined not to invite", "was not selected for the final round", "the board decided to narrow the field")
2. Check directionality: was the bidder excluded before signaling withdrawal?
3. Cross-reference round structure: if a bidder had an NDA but was not in `invited_actor_ids` for the next round announcement, that is likely a DropTarget

**M&A Domain Signals for DropTarget:**
- "The committee determined not to invite [Party X] to the final round"
- "The board narrowed the field to [N] bidders"
- "[Party X] was not selected to participate in the next phase"
- Absence from `invited_actor_ids` when the bidder was previously active (implicit DropTarget)

**Complexity Note:** The implicit DropTarget case (active bidder not invited to next round, no explicit drop event extracted) may require synthesizing new drop events from round invitation data. This is a higher-complexity variant.

---

### D-2: Round Milestone Event Types

| Attribute | Detail |
|-----------|--------|
| Value Proposition | Captures auction process structure that Alex records but the pipeline omits. |
| Complexity | Low-Medium |
| Dependencies | Already in the 20-type event taxonomy; round pairing already works in `enrich_core.py` |
| Confidence | HIGH -- the taxonomy and pairing logic already exist |

**What It Is:** The pipeline's event taxonomy already includes 6 round event types:
- `final_round_inf_ann` / `final_round_inf` (informal round announcement / deadline)
- `final_round_ann` / `final_round` (formal round announcement / deadline)
- `final_round_ext_ann` / `final_round_ext` (extension round announcement / deadline)

The reconciliation shows Alex captures round milestones across all 9 deals, but the pipeline's extraction often misses them. This is not a taxonomy gap -- it is an extraction coverage gap. The LLM does not reliably extract round events because the filing language for round announcements is more subtle than for proposals or NDAs.

**Root Cause Analysis:**
1. Round announcements in filings rarely say "we announced a final round." Instead they say things like "the committee requested that the remaining parties submit revised proposals by [date]" or "process letters were sent to [N] bidders."
2. The extraction prompt's event taxonomy lists round types but provides no examples of what filing language maps to them.
3. The coverage module (`coverage.py`) does not have cue families for round events -- it checks proposals, NDAs, drops, and process initiation, but not round milestones.

**The Fix:**
1. Add few-shot examples in the extraction prompt showing round announcement language patterns.
2. Add a `round_milestone` cue family to coverage with patterns like "process letter", "requested that parties submit", "invited to submit revised", "narrowed the field."
3. Optionally, add round milestone detection in the extraction gap re-read (Pass 2) with explicit prompting for round events.

---

### D-3: Contextual all_cash Inference

| Attribute | Detail |
|-----------|--------|
| Value Proposition | Increases `all_cash` coverage from explicit-mention-only to contextually inferrable cases. |
| Complexity | Medium |
| Dependencies | `db_export.py` cash_value logic, `enrich_core.py` |
| Confidence | MEDIUM -- the inference rules are domain-clear but require careful scoping to avoid false positives |

**What It Is:** The current pipeline only marks `all_cash=1` when the event's `terms.consideration_type == "cash"` (line 303 of `db_export.py`). The reconciliation shows this misses cases where cash consideration is contextually obvious:
- Penford: All Ingredion bids were cash (deal context makes this clear), but not every proposal sentence says "cash"
- PetSmart: The executed deal was clearly all-cash, but the executed event lacks explicit cash mention

**Inference Rules (domain-grounded, conservative):**

1. **Same-actor consistency:** If an actor's earlier proposal explicitly states "cash" and a later proposal from the same actor does not specify consideration_type, infer cash (unless the later proposal introduces stock/mixed language). Rationale: bidders rarely switch from cash to mixed consideration without stating it.

2. **Executed event inference:** If the executed merger agreement specifies cash consideration (checkable from the `executed` event or the signing event's terms), propagate `all_cash` to the executed row. This is nearly always disclosed.

3. **Process-level inference:** If ALL proposals from ALL bidders throughout the process specify cash, and the filing does not mention stock or mixed consideration, the process is all-cash. Mark all proposals accordingly.

**Anti-pattern to avoid:** Do NOT infer cash from the absence of stock mention. Some filings simply do not specify consideration type for early-stage indications. The inference must be positive (evidence of cash), not negative (absence of stock).

**Where It Lives:** This belongs in `enrich_core.py` as a new enrichment pass after bid classification. The inference result should be stored in `deterministic_enrichment.json` as a `consideration_inference` dict keyed by event_id, with fields: `inferred_type`, `basis`, `confidence`.

---

### D-4: Verbal/Oral Price Indication Support

| Attribute | Detail |
|-----------|--------|
| Value Proposition | Captures price signals that precede formal written bids, filling a gap Alex records. |
| Complexity | Medium |
| Dependencies | Extraction prompt guidance, possibly a new `formality_signals` flag |
| Confidence | MEDIUM -- filing language is clear but these are inherently informal |

**What It Is:** Some deals include verbal price indications before written IOIs: STEC Company D oral price signal, PetSmart Bidder 3 verbal indication. The filing says something like "representatives of Company D verbally indicated a willingness to pay approximately $X per share."

**Current Gap:** The extraction prompt does not specifically guide the LLM to extract verbal/oral indications. The `FormalitySignals` model does not have a flag for verbal-only proposals.

**The Fix:**
1. Add extraction prompt guidance: "Verbal or oral price indications are extractable as proposal events. Set `formality_signals.mentions_preliminary=true` and add `verbal_indication` to event notes."
2. Optionally add `is_verbal_indication: bool` to `FormalitySignals` (default false). This allows deterministic classification to handle verbal proposals correctly (they are always Informal).
3. Add coverage cue patterns for "verbally indicated", "oral indication", "verbal expression of interest."

---

### D-5: Harden Extraction Orchestration Against Concurrent Artifact Writes

| Attribute | Detail |
|-----------|--------|
| Value Proposition | Prevents corruption when multiple workers write deal artifacts simultaneously. |
| Complexity | Medium |
| Dependencies | Orchestration workflow, filesystem locking |
| Confidence | HIGH -- observed in 7-deal rerun |

**What It Is:** The 7-deal rerun initially launched parallel workers that could collide on shared filesystem paths. The workaround was serialized per-deal launches with strict path ownership. A more robust solution would be file-level locking or per-deal workspace isolation.

**The Fix:** Add per-deal lock files (e.g., `data/skill/<slug>/.lock`) that deterministic stages check before writing. The lock should be advisory (not mandatory) with clear error messages. Alternatively, document the concurrency contract: each deal slug is owned by exactly one worker at a time.

---

## Anti-Features

Features to explicitly NOT build for this milestone.

---

### AF-1: Do Not Add New Event Types to the Taxonomy

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Adding `exclusivity_grant`, `ib_termination`, `aggregate_cohort_drop`, or other new event types | The 20-type taxonomy is sufficient. Alex's extra event types (exclusivity, IB termination) are either rare or can be captured as notes on existing events. Adding types increases schema complexity, extraction prompt length, and downstream handling for minimal coverage gain. | Capture exclusivity grants as notes on NDA or proposal events. IB termination is rare (1 deal) -- not worth a taxonomy slot. Aggregate cohort drops are a presentation choice, not an event type. |

### AF-2: Do Not Build Benchmark-Informed Generation

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Using reconciliation findings or Alex's spreadsheet to influence extraction generation | This violates the benchmark boundary constraint. The pipeline must generate from filing text alone. Reconciliation findings inform pipeline code fixes, not extraction prompts. | Use reconciliation to identify code bugs (bid_type rule order) and coverage gaps (missing round events), then fix the pipeline code. Never feed Alex's answers into the extraction prompt. |

### AF-3: Do Not Add Aggregate Per-Party Rows

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Adding aggregate rows like "15 parties NDA" or "6 parties IOI" as pseudo-events | These are presentation artifacts, not events. Alex uses them for spreadsheet readability. The pipeline's `count_assertions` mechanism already captures these filing statements as metadata without polluting the event timeline. | Continue using `count_assertions` for filing-stated aggregate counts. The count reconciliation task in enrich-deal already compares them to extracted events. |

### AF-4: Do Not Build Automatic Extraction Re-Run for Data Fixes

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Building an automated re-extraction pipeline that detects and fixes data errors like Zep NMC or Medivation missing drops | Re-extraction is expensive and non-deterministic. The fixes for Zep and Medivation are surgical artifact repairs, not systematic pipeline changes. Automating artifact repair risks masking extraction quality issues. | Fix the specific data errors via manual artifact repair (Zep NMC, Medivation drops). Improve extraction prompts to prevent similar errors in future runs. |

---

## Feature Dependencies

```
TS-1 (bid_type rule fix) -> D-1 (DropTarget depends on correct round structure from enrichment)
TS-2 (canonicalize dedup) -> TS-3, TS-4, TS-5 (all downstream stages depend on clean canonicalization)
TS-3 (coverage false positives) -> no downstream dependency
TS-4 (check grouped NDA) -> no downstream dependency (but blocks canonicalize -> check -> verify flow)
TS-5 (gates rollover NDA) -> D-1 (DropTarget enrichment needs clean gate results)
TS-6 (Zep NMC) -> independent (data fix)
TS-7 (Medivation drops) -> independent (data fix)
TS-8 (DuckDB lock) -> independent (runtime fix)

D-1 (DropTarget) -> depends on D-2 (round milestones) for implicit DropTarget detection
D-2 (round milestones) -> independent extraction improvement
D-3 (all_cash inference) -> depends on TS-1 (correct bid classification needed for inference context)
D-4 (verbal indications) -> independent extraction improvement
D-5 (concurrent writes) -> independent runtime improvement
```

---

## MVP Recommendation

### Must-Fix (blocks correctness):
1. **TS-1: bid_type rule priority** -- highest-impact single fix, affects 5+ deals
2. **TS-2: canonicalize dedup** -- prevents runtime crashes
3. **TS-3: coverage false positives** -- prevents spurious repair work
4. **TS-4: check grouped NDA** -- prevents false blocker assertions
5. **TS-5: gates rollover NDA** -- prevents false gate rejections
6. **TS-8: DuckDB lock** -- prevents transient runtime failures

### Should-Fix (closes known data gaps):
7. **TS-6: Zep NMC** -- data repair
8. **TS-7: Medivation drops** -- data repair

### High-Value Additions:
9. **D-1: DropTarget classification** -- moves a key interpretive judgment into deterministic code
10. **D-2: Round milestone coverage** -- closes the biggest extraction gap vs Alex

### Defer to v1.2:
- **D-3: all_cash inference** -- design choice (precision vs coverage), not a bug
- **D-4: Verbal indications** -- rare (2 deals affected), extraction prompt guidance is sufficient
- **D-5: Concurrent write hardening** -- documentation of the concurrency contract is sufficient for now

---

## Complexity Summary

| Feature | Complexity | Lines of Code (est.) | Test Effort |
|---------|------------|---------------------|-------------|
| TS-1: bid_type rule fix | Low | ~20 lines changed in `enrich_core.py` | Medium (regression tests across 5+ deals) |
| TS-2: canonicalize dedup | Low | ~30 lines in `canonicalize.py` | Low (unit test with overlapping quote_ids) |
| TS-3: coverage false positives | Low | ~10-20 lines in `coverage.py` | Low (add exclusion patterns, unit tests) |
| TS-4: check grouped NDA | Low | ~10 lines verification + tests | Low (regression test for providence-worcester pattern) |
| TS-5: gates rollover NDA | Low | ~20 lines in gates or extraction guidance | Medium (needs extraction guidance update + gate logic) |
| TS-6: Zep NMC | Low | Artifact edit | Low (data verification) |
| TS-7: Medivation drops | Low | Artifact edit | Low (data verification) |
| TS-8: DuckDB lock | Low | ~10 lines in `db_load.py` or `db_export.py` | Low (integration test) |
| D-1: DropTarget enrichment | Medium | ~80-120 lines in `enrich_core.py` | Medium (need filing-grounded test cases) |
| D-2: Round milestone coverage | Medium | ~40-60 lines in `coverage.py` + prompt updates | Medium (new cue family + extraction prompt changes) |
| D-3: all_cash inference | Medium | ~60-80 lines in `enrich_core.py` | Medium (inference rules + edge cases) |
| D-4: Verbal indications | Medium | ~20 lines prompt guidance + optional model field | Low |
| D-5: Concurrent writes | Medium | ~40 lines lock mechanism | Low |

---

## Sources

### Primary Evidence (Pipeline-Internal)
- `data/reconciliation_cross_deal_analysis.md` -- 9-deal cross-deal reconciliation (pipeline vs Alex)
- `quality_reports/session_logs/2026-03-29_7-deal-rerun_master.md` -- 7-deal execution log with runtime walls
- `skill_pipeline/enrich_core.py` -- current bid classification rules
- `skill_pipeline/canonicalize.py` -- current quote-to-span resolution
- `skill_pipeline/coverage.py` -- current coverage cue families
- `skill_pipeline/check.py` -- current structural assertions
- `skill_pipeline/gates.py` -- current semantic gates
- `skill_pipeline/db_export.py` -- current CSV export with all_cash logic
- `.claude/skills/extract-deal/SKILL.md` -- extraction taxonomy and instructions
- `.claude/skills/enrich-deal/SKILL.md` -- enrichment classification rules

### M&A Domain (External)
- [Kimberly Advisors: Indication of Interest (IOI)](https://kimberlyadvisors.com/articles/indication-of-interest-ioi) -- IOI is non-binding, LOI is partially binding
- [Redmount: The Two-Step M&A Bidding Process](https://redmountpartners.com/twostepsofmanda/) -- IOI (first round) vs LOI (final round) formality progression
- [Carpenter Wellington: All Cash Consideration in Public Company Mergers](https://carpenterwellington.com/post/public-company-merger-transactions-involving-all-cash-consideration/) -- explicit disclosure in merger agreements and SEC filings
- [Exit Strategies: M&A Auction Process](https://www.exitstrategiesgroup.com/how-auction-process-works/) -- two-round bid process with field narrowing
- [Wall Street Prep: Sell Side M&A Process](https://www.wallstreetprep.com/knowledge/sell-side-process/) -- round milestones and process timeline
