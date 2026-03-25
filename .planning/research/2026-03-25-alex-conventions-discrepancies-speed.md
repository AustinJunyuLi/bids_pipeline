# Research: Alex Workbook Conventions, Discrepancy Fortification, and Extraction Speed

**Date:** 2026-03-25
**Scope:** Ad-hoc research across all three interconnected questions.
**Sources:**
- `example/deal_details_Alex_2026.xlsx` — 9,335 data rows across 395 real deals
- `data/skill/stec/reconcile/reconciliation_report.json` — full STEC reconciliation
- `.claude/skills/extract-deal/SKILL.md` — extraction architecture
- `.claude/skills/export-csv/SKILL.md` — export column specification
- `skill_pipeline/models.py` — canonical schemas
- `skill_pipeline/preprocess/source.py` — block construction
- `data/skill/stec/export/deal_events.csv` — live STEC export
- `data/deals/*/source/chronology_blocks.jsonl` — block counts for 8 deals

---

## 1. Alex Workbook Conventions (Undocumented)

All counts below are derived from 9,335 data rows across 395 real deals. Comments columns are sparse (73/40/1 non-empty entries for c1/c2/c3 respectively) — they contain operator annotations, not systematic data.

### 1.1 Value/Range Convention

**Convention (confidence: CERTAIN — 797/797 range-bid rows agree):**
For any bid with a range, `bid_value` always equals `bid_value_lower`. `bid_value_upper` carries the top of the range. This is 100% consistent across all 797 true range bids (where `lower != upper`) in the dataset.

Evidence:
- 3,180 of 3,194 range-annotated rows have `bid_value == bid_value_lower`.
- The 14 remaining cases are single-value bids where lower=upper=bid_value (point bids stored in all three columns).
- 0 cases where `bid_value == bid_value_upper` while `bid_value != bid_value_lower`.

**Implication for pipeline:** The pipeline's current behavior (omitting `val` for range bids, outputting only `range`) diverges from Alex's convention. Alex always populates `val` with the lower bound. See Section 2.2.

**Point bids:** When a bid is a single value, Alex sets `bid_value = bid_value_lower = bid_value_upper`. The export-csv SKILL already handles this with its `val-val` range format for point bids.

### 1.2 Date Precision Convention

**Convention (confidence: HIGH):**

Three tiers observed:

1. **Exact date known:** `bid_date_precise` = `bid_date_rough` = the exact date. Both fields identical. This is the most common case (6,591 of 6,628 "both dates set" rows match exactly).

2. **Only rough date known:** `bid_date_precise` is absent (NA). `bid_date_rough` holds the approximation. This applies to 2,004 rows, predominantly:
   - NDA rows (1,288 of 2,004) — NDA dates are often given as a month range in filings.
   - Drop rows (431) — drops recorded with approximate month.
   Day-15 is Alex's most common rough date (1,212 occurrences, far above any other day), consistent with "mid-month" approximations.

3. **Both dates differ (37 rows):** Alex records `bid_date_precise` as one event's exact date while `bid_date_rough` is a different approximation. The STEC reconciliation confirms this pattern — Alex sometimes copies a nearby event's precise date into `date_p` for an imprecise event, creating data entry errors. The rough date field is the reliable anchor.

**Key insight:** `bid_date_rough` is the primary sort key. `bid_date_precise` is only meaningful when the filing gives an exact date for the specific event, and even then Alex sometimes uses it incorrectly (e.g., STEC: Company B interest, Company D interest, IB retention all show `date_p=2013-04-04`, which is the NDA date for Company E — clearly copied from the spreadsheet row below).

**Rough date encoding for imprecise language:**
- "early [month]" → day 5 (inferred from export-csv SKILL.md, not directly confirmed in Alex data)
- "mid [month]" → day 15 (confirmed from Alex data: 1,212 day-15 occurrences dominate)
- "late [month]" → day 25 (export-csv SKILL.md states this; day-25 has 252 occurrences, plausible)

### 1.3 BidderID Numbering Convention

**Convention (confidence: CERTAIN — derived from export-csv SKILL.md plus data confirmation):**

The BidderID encoding carries three distinct signals:

**Integer IDs (1, 2, 3, ...):** Events from the first NDA onward. Sequential, starting at 1. Gaps are intentional and rare (5 gaps found across 395 deals), typically from events that were removed without renumbering.

**Fractional X.5 IDs (0.5, 1.5, 5.5, ...):** Process-level events or events inserted between integer-numbered bidder events (47 X.5 rows). The X.5 convention encodes "inserted between X and X+1." Key X.5 uses:
- `0.5` = single pre-NDA event (IB retention or early bidder interest)
- Other X.5 = mid-process insertions (Final Round events, Executed, late NDA, etc.)

**Fractional 0.x IDs (0.3, 0.7, 0.8, 0.9, 0.95):** Pre-NDA events only, spaced to fit N events in (0,1). The fractional spacing formula (confirmed by export-csv SKILL.md):
- 1 event: 0.5
- 2 events: 0.3, 0.7
- 3 events: 0.3, 0.5, 0.7
- 4 events: 0.2, 0.4, 0.6, 0.8
- 5+ events: includes 0.8, 0.9, 0.95 — Alex uses finer spacing ad hoc

**Special 0.x BidderID semantics (22 confirmed cases):**
- `0.5`: IB retention (6 deals) OR early bidder interest (4 deals) — the single pre-NDA event
- `0.7`: Target-sale announcement (2), Bidder-sale (2), or secondary pre-NDA event
- `0.8`: IB event (3), Activist-sale (1)
- `0.9`: Target-sale public announcement (1)
- `0.95`: Sale press release (1)

**IB rows always get fractional IDs.** All 11 IB retention rows in Alex's workbook have decimal BidderIDs. This is because IB retention precedes the first NDA.

### 1.4 Event Label Taxonomy

Full taxonomy from workbook (9,335 rows):

| Label | Count | Semantics |
|---|---|---|
| `NA` | 3,317 | Bid/proposal events (bid rows have bid_value set; `NA` in the note column is NOT the same as missing) |
| `Drop` | 2,735 | Bidder dropped; no further specified reason |
| `NDA` | 2,619 | Confidentiality agreement signed |
| `Executed` | 399 | Merger agreement executed |
| `DropM` | 109 | Bidder dropped; explicitly not meeting (M = merger?) the price threshold; always `bid_value=NA` |
| `Final Round` | 82 | Formal final round deadline |
| `DropTarget` | 12 | Target-initiated exclusion (distinct from bidder-initiated `Drop`) |
| `IB` | 10 | Investment bank retained (all have fractional BidderIDs) |
| `Final Round Ann` | 8 | Formal final round announced |
| `Final Round Inf Ann` | 7 | Informal final round announced |
| `Final Round Inf` | 7 | Informal final round deadline |
| `Bidder Interest` | 6 | Unsolicited bidder interest before process |
| `Final Round Ext Ann` | 3 | Extension round announced |
| `Final Round Ext` | 3 | Extension round deadline |
| `Bidder Sale` | 3 | Acquirer-initiated process start |
| `Target Sale` | 2 | Target board authorizes process |
| `Bid Press Release` | 1 | Public announcement of a bid |
| `DropAtInf` | 1 | Drop at informal round stage |
| `DropBelowInf` | 1 | Drop below informal round threshold |
| `Terminated` | 1 | Process terminated |
| `Restarted` | 1 | Process restarted |
| `Exclusivity 30 days` | 1 | Exclusivity granted |
| `Activist Sale` | 1 | Activist-triggered process |
| `Target Sale Public` | 1 | Public announcement of strategic review |
| `Sale Press Release` | 1 | Press release announcing strategic alternatives |
| `Target Interest` | 1 | Target-side expression of intent |
| `IB Terminated` | 1 | IB engagement terminated |
| `Final Round Inf Ext Ann` | 1 | Informal extension round announced |
| `Final Round Inf Ext` | 1 | Informal extension round deadline |

**Notable labels the pipeline currently does NOT track:** `DropM`, `DropTarget`, `DropAtInf`, `DropBelowInf`, `IB Terminated`, `Exclusivity 30 days`. The export-csv SKILL maps these from `enrich-deal` enrichment labels — but `IB Terminated`, `Exclusivity 30 days`, `Target Interest`, and `Bidder Interest` (as distinct from `bidder_interest` event type) have no counterparts in the pipeline's 20-type taxonomy.

### 1.5 Bidder Type Convention

**bidder_type_note encoding (confidence: HIGH):**

Alex uses a free-text `bidder_type_note` field with these primary values (3,649 = F, 3,129 = S, 223+ compound variants). The four binary columns are derived:

| Note value | financial | strategic | mixed | nonUS |
|---|---|---|---|---|
| `F` | 1 | 0 | 0 | 0 |
| `S` | 0 | 1 | 0 | 0 |
| `Non-US S` | 0 | 1 | 0 | 1 |
| `Non-US F` | 1 | 0 | 0 | 1 |
| `Non-US public S` | 0 | 1 | 0 | 1 |
| `Non-US public F` | 1 | 0 | 0 | 1 |
| `Private S` | 0 | 1 | 0 | 0 |
| `Public S` | 0 | 1 | 0 | 0 |
| `S and F` / `F and S` | 1 | 1 | 1 | 0 |
| `Non-US acquisition vehicle` | 0 | 0 | 0 | 1 |

**Key rule:** The binary columns are generated from the note, not the reverse. For consortium bidders (165 mixed=1 rows), Alex records both S and F in the note with member names (e.g., `F(KKR) and S(WBA)`).

**Export convention:** The `type` column is populated only on the FIRST row for each actor (the NDA row is the canonical first appearance). All subsequent rows for the same actor (proposals, drops, executed) have `type=NA`. This explains the reconciliation finding: 13 "missing bidder_type" mismatches in STEC all come from non-NDA rows where Alex already recorded the type on the NDA row and correctly blanks it on later rows.

**Pipeline gap:** The pipeline's export-csv SKILL correctly documents this first-row-only convention, but the current export does not carry `bidder_kind` through from `actors_raw.json` to the non-NDA event rows it does populate. Confirmed by STEC export: rows 2 (NDA Company D), 12 (NDA Company H) show `type=NA` instead of `S` — these are the first-row NDA appearances, so they SHOULD have type populated. This is a genuine export bug, not a convention difference.

### 1.6 All-Cash Convention

**Convention (confidence: HIGH):**

`all_cash=1` is set only when the filing explicitly states the consideration is all-cash. The field is NA otherwise — Alex does not infer cash from context. Evidence:

- 2,082 rows have `all_cash=1`; 277 have `all_cash=0`; 6,976 are NA.
- `all_cash` is primarily set on `bid_note=NA` rows (1,707) and `Executed` rows (372).
- Only 2 `Drop` rows and 1 `Final Round` row have `all_cash` set — likely for proposals that were near-executed.

**Contrast with pipeline:** The STEC reconciliation shows the pipeline sets `all_cash=true` for Company D's verbal IOI even though the filing does not state "cash." Alex correctly leaves it NA. The pipeline should require explicit filing language, not context inference.

### 1.7 Consortium/Group Convention

**Convention (confidence: HIGH):**

Three consortium patterns observed:

1. **Named consortium (165 rows, mixed=1):** Both parties named in `BidderName` (e.g., `"Parties E and F"`), note contains `S and F, respectively`. One row per consortium bid.

2. **Unnamed aggregates (many rows):** `is_grouped=true` equivalent — rows like `BidderName="31 unnamed parties"`, `bidder_type_note="both S and F"`. Single row representing the batch.

3. **Individual-but-linked (rare):** Separate rows for each consortium member when the filing breaks them out, with the same BidderID decimal spacing between them.

**Drop/DropM with grouped bidders:** When a batch of unnamed bidders all drop at the same stage, Alex uses one `DropM` row (109 DropM rows, all `bid_value=NA`). DropM appears to mean "dropped en masse" rather than a price-threshold distinction.

### 1.8 Comments Convention

**c1 (primary annotation — 73 non-empty entries):** Human-written operator notes. Uses asterisk (`*`) prefix to flag process-level observations that are not directly captured in the structured fields:
- `*Go-shop period` — indicates a go-shop clause applies
- `*Due to exclusivity with X` — explains a drop's cause
- `*Board decides to...` — explains who was excluded and why
- Non-asterisk entries: bid structure decomposition, advisor names, date ambiguity notes

**c2 (deal terms — 40 non-empty entries):** Structured free text for DD/exclusivity terms:
- Duration: `30 day DD`, `4 week DD`, `Confirmatory DD`
- Exclusivity: `30 day exclusive DD`
- Financing: `No firm financing commitment`
- Restrictions: `Restrict from soliciting competing bids`

**c3 (overflow — 1 non-empty entry):** Treated as an overflow from c1/c2. Alex rarely uses it.

---

## 2. Discrepancy Fortification

### 2.1 Export Regression: bidder_type Missing

**Root cause (confidence: CERTAIN — confirmed by reading export CSV and SKILL.md):**

The export-csv SKILL specifies that `type` is populated only on the first row for each actor. However, examining the STEC export CSV shows the bug operates on the NDA rows themselves — rows 2 (`NDA, Company D, type=NA`) and 12 (`NDA, Company H, type=NA`) should show `type=S` on their first appearance but do not. The `bidder_kind` field is present in `actors_raw.json` (reconciliation confirms `pipeline actor actors_raw.json has bidder_kind=strategic`) but the export agent failed to propagate it to the first NDA row.

The reconciliation report confirms: "The underlying pipeline actors_raw.json has the correct bidder_kind=strategic." The failure is in the LLM export step — it misapplied the "first-row-only" rule by treating _any_ non-process-level event as "not the first row" rather than correctly identifying the first row for each unique actor.

**Proposed fix (confidence: HIGH):**

Update the export-csv SKILL.md to be more explicit about what "first row" means:

> "For each bidder actor: identify the chronologically first event row that names this actor in the `bidder` column. Populate `type` on that row only. All other rows for that actor get `type=NA`. The first row is typically the NDA row, but may be a `Bidder Interest`, `IB`, or proposal row if no NDA was signed."

Additionally add a self-check note: "After building all rows, verify that every bidder actor that has a `bidder_kind` in actors_raw.json has at least one row where `type` is non-NA."

**Scope:** This is a SKILL.md instruction gap, not a Python code bug. The fix is a prompt/SKILL.md update. No Python changes needed.

### 2.2 Val Convention for Range Bids

**Finding (confidence: CERTAIN — 797/797 range bids agree):**

Alex always populates `val` with the lower bound of a range. The pipeline currently outputs `val=NA` for range bids and uses the `range` column only.

The STEC reconciliation explicitly notes: "Both approaches are defensible" for the three range proposals (WDC $6.60-$7.10 and Company H $5.00-$5.75). However, given that Alex's convention is 100% consistent across the dataset, adopting it eliminates a systematic discrepancy.

**Proposed fix (confidence: MEDIUM — "defensible both ways" but consistency has value):**

Update the export-csv SKILL.md to add:

> "For range bids: populate `val` with `range_low`. This matches Alex's convention of recording the lower bound as the point estimate. Do not leave `val=NA` when a `range_low` is known."

This is a one-line SKILL.md addition. Affects proposals with `range_low != range_high` only.

### 2.3 Ambiguous Withdrawal Detection (Company H May 23)

**Finding:**

The reconciliation identifies one filing-grounded drop the pipeline missed: Company H on May 23, 2013 (line 1502). The filing text states Company H "indicated that Company H was not able to increase its indicated value range." This is a soft withdrawal — Company H did not formally drop, but communicated inability to raise its offer, leading the target to stop engaging with it.

**Why it's missed:**

The extract-deal SKILL specifies: "Collapse every withdrawal or exclusion into `drop`." However, the filing language for Company H is ambiguous — it's not a clean "Company H declined" statement. It's an indication of inability to raise value, which requires interpretation of whether this constitutes a drop event. The chunk covering this block likely treated it as a note on a prior event rather than a new drop event.

**Proposed fix (confidence: MEDIUM):**

Strengthen the extract-deal SKILL.md drop detection rules:

> "Extract a `drop` event when any of these filing signals appear:
> - Explicit declination or withdrawal
> - Party states it cannot increase its offer/bid and no further contact follows
> - Target board decides not to continue discussions (DropTarget)
> - Party indicates inability to meet price threshold without explicit value stated
>
> For ambiguous soft withdrawals ('indicated it was not able to increase'): include as a `drop` event with `drop_reason_text` quoting the filing language. Set `whole_company_scope=null` and add a note indicating the withdrawal was soft/implicit. The drop type (DropBelowM, DropBelowInf, etc.) will be determined by enrich-core."

**Also check during consolidation pass:** The consolidation step's targeted re-reads should include a pass over the `drop` event type looking for soft withdrawal language, not just explicit declinations.

### 2.4 Informal Round Taxonomy

**Finding:**

Alex uses `Final Round Inf Ann` (7 occurrences across workbook) and `Final Round Inf` (7 occurrences) to mark an informal round structure where the target invites verbal/written IOIs before the formal final round. The pipeline's 20-type taxonomy already includes `final_round_inf_ann` and `final_round_inf` — this is not a missing type.

**STEC-specific issue:** The reconciliation shows the pipeline does not extract these for STEC because the filing describes individual IOI solicitations rather than explicitly announcing "we are now entering an informal round." Alex's categorization is an interpretation. The pipeline correctly documents this as a `categorization_difference`.

**Recommendation (confidence: HIGH — no change needed to taxonomy):**

The 20-type taxonomy is correct. The gap is in the consolidation pass logic. The consolidation should look for the pattern: "target solicited IOIs/verbal indications from multiple parties before formal final round announcement" and emit `final_round_inf_ann` when this pattern is present.

Update the extract-deal SKILL.md consolidation pass instructions to add:

> "Informal round detection: If the timeline shows multiple bidders submitting verbal/written IOIs in a tight window before the formal final round announcement, and no explicit informal round announcement appears in the filing, emit `final_round_inf_ann` dated to the start of the IOI solicitation window and `final_round_inf` dated to when written bids were due (typically just before the formal final round announcement). Add a note that this is an inferred informal round."

**Do NOT add this as a new event type.** The taxonomy already has it.

### 2.5 Systematic Date Error Detection

**Finding:**

From the STEC workbook data: `bid_date_precise=2013-04-04` appears on 4 rows for different bidders — Company B (interest Feb 13), Company D (interest mid-March), BofA Merrill Lynch (retention Mar 28), and Company E (NDA Apr 4). Three of the four are wrong. This pattern is consistent with a copy-paste error: Alex recorded the NDA date (April 4, the most salient date at that stage) in the precise date column for events that occurred earlier.

**The pattern:**
- Multiple rows in the same deal share the same `date_p` value
- The shared value matches a more prominent event's date
- The rough date (`date_r`) correctly reflects different dates

**Proposed reconcile-alex enhancement (confidence: HIGH):**

The `/reconcile-alex` skill should flag this as a systematic pattern when it detects:

1. More than 2 rows in the same deal with the same `date_p` value
2. Those rows span different bidders (not just process-level rows)
3. The `date_r` values differ across those rows

Flag as: `"systematic_date_p_reuse: X rows share date_p=YYYY-MM-DD across different bidders; date_r values differ — possible copy-paste error in Alex spreadsheet"`

This is a post-export diagnostic, not a generation fix. The reconcile skill should report it; the human researcher decides if Alex's data needs correction.

---

## 3. Extraction Speed

### 3.1 Current Architecture

The extract-deal SKILL defines a strictly sequential LLM-based workflow:

1. **Chunking:** `chronology_blocks.jsonl` is split into chunks of 10-12 blocks each (~3-4K tokens per chunk). Each block appears in exactly one primary chunk, with 1-2 blocks of overlap at boundaries.

2. **Sequential chunk extraction:** Chunks processed in order — chunk_1, chunk_2, ..., chunk_N. Each chunk receives: its block window, scoped evidence items, and the running actor roster from prior chunks.

3. **Roster carry-forward:** After each chunk, newly minted actors merge into the running roster before the next chunk is prompted.

4. **Consolidation pass:** One final pass receives all chunk drafts, performs actor dedup, event dedup in overlap zones, taxonomy sweep, targeted re-reads for missing event types, temporal signal assignment, and global event ID assignment.

**Total LLM calls for a typical deal:**

| Deal | Blocks | Estimated chunks | Plus consolidation | Total calls |
|---|---|---|---|---|
| petsmart-inc | 35 | ~3-4 | 1 | 4-5 |
| saks | 64 | ~6 | 1 | 7 |
| imprivata | 100 | ~10 | 1 | 11 |
| stec | 235 | ~20-24 | 1 | 21-25 |
| mac-gray | 179 | ~15-18 | 1 | 16-19 |
| medivation | 164 | ~14-16 | 1 | 15-17 |
| zep | 113 | ~10-11 | 1 | 11-12 |

**Rough latency estimate:** Each LLM call ~15-30 seconds for a 3-4K token chunk on Sonnet (including network). A 20-chunk deal takes 300-600 seconds (5-10 minutes) end-to-end at full sequential speed.

### 3.2 Bottleneck Analysis

**Primary bottleneck: Sequential chunk dependency via roster carry-forward.**

Each chunk requires the running actor roster from all prior chunks. This is a hard serial dependency — chunk N cannot start until chunk N-1 completes, because chunk N may reference actors first seen in chunk N-2 or N-3.

**Secondary bottleneck: Consolidation pass scope.**

The consolidation pass does up to 5 targeted re-reads for event types marked `NOT FOUND`. Each re-read is one additional LLM call. For a 20-chunk deal with 5 missing event types, that's 5 additional calls — 25% overhead.

**Evidence items per deal:** 1,000-3,200 items per deal. Scoping evidence to a chunk window limits prompt size, but the evidence JSONL is only read for anchoring — it is not the bottleneck.

### 3.3 Parallelization Opportunities

**What can be parallelized (confidence: HIGH):**

1. **Cross-deal parallelism (already possible):** Multiple deals can run extraction simultaneously since they are fully independent. This is the highest-leverage option for batch processing.

2. **Actor extraction vs. event extraction cannot be split within a chunk.** The SKILL explicitly extracts both together per chunk. Separating them would double calls while requiring a merge step, yielding no net speedup.

3. **Chunk parallelism is blocked by roster dependency.** However, a partial relaxation is possible:
   - Chunk a deal into two halves (early and late chronology)
   - Run early chunks sequentially, run late chunks sequentially
   - Both sequences start at "empty roster" with a reconciliation step at the midpoint

   This requires a roster reconciliation pass between the two sequences. For a 20-chunk deal, this could yield ~2x speedup on wall time at the cost of one additional reconciliation call.

4. **Consolidation re-reads are parallelizable.** The 5 targeted re-reads for missing event types are independent of each other and could be issued as a single parallel call (one multi-part prompt or parallel API calls).

**What cannot be parallelized:**
- Actor dedup (requires all chunk outputs)
- Global event ID assignment (requires the full sorted timeline)
- Temporal signal assignment (requires the full event sequence)

### 3.4 Token Reduction

**Opportunities (confidence: MEDIUM):**

1. **Evidence scoping (already implemented).** The SKILL already scopes evidence items to the chunk's block range. No change needed.

2. **Running roster compression.** After chunk extraction, the actor roster carries all previously seen actors as full objects. For a 20-chunk deal, by chunk 20 the roster may have 15-20 actors, each with full evidence_refs. Compressing the roster to `{actor_id, display_name, bidder_kind}` tuples in the carry-forward prompt (stripping evidence_refs from the roster in subsequent prompts) could reduce prompt tokens by 30-50%.

3. **Chunk overlap reduction.** The SKILL specifies 1-2 blocks of overlap. Going to 0-1 block overlap reduces total processed tokens by ~10% with minor risk to boundary event coverage. The consolidation's event dedup step handles the boundary issue.

4. **Consolidation prompt batching.** Currently the consolidation receives all chunk drafts as input. For a 20-chunk deal this is a large context. A two-pass consolidation (first pass: dedup and actor merge; second pass: taxonomy sweep and re-reads) would reduce per-pass token count at the cost of one extra call.

**Estimated token savings from roster compression:** ~15-25% reduction in total tokens across the sequential run for large deals.

### 3.5 Model Tiering

**Current setup:** Single model (Claude Sonnet by default, configurable via `BIDS_LLM_MODEL`).

**Tiering opportunity (confidence: MEDIUM):**

The chunk extraction passes are relatively mechanical: read blocks, identify actors and events, fill structured fields. These do not require high reasoning capability. A faster/cheaper model could handle chunk extraction while reserving the quality model for:
- Consolidation (requires cross-chunk reasoning)
- Targeted re-reads (requires understanding why an event type is absent)
- Temporal signal assignment (requires understanding the full event sequence)

**Practical issue:** The extract-deal skill uses structured JSON output. Model tiering requires verifying that the cheaper model reliably produces schema-valid output. claude-haiku-3 or gpt-4o-mini are candidates but would need per-deal validation.

**Estimate:** A faster model at 3x throughput on chunk passes with a quality model on consolidation could reduce wall time by 40-50% for large deals. Accuracy risk is moderate — chunk extraction errors propagate to consolidation.

### 3.6 Recommended Speedups

**Priority order:**

1. **Cross-deal parallelism** (confidence: CERTAIN, no code changes needed). Run multiple deals simultaneously. For 9 deals, 3x parallel extraction reduces total wall time by ~3x. Already possible today by running `/extract-deal` in separate terminal sessions.

2. **Roster compression in carry-forward** (confidence: HIGH, SKILL.md change only). Strip `evidence_refs` from actors when passing the roster to subsequent chunks. Keep only `{actor_id, display_name, canonical_name, aliases, role, bidder_kind, geography, listing_status}`. Reduces prompt size for large deals. Expected 15-25% token reduction, no accuracy loss.

3. **Parallel consolidation re-reads** (confidence: HIGH, SKILL.md change only). When the taxonomy sweep identifies multiple `NOT FOUND` event types, issue all targeted re-reads as a single multi-event-type prompt rather than one call per type. This collapses N re-read calls into 1. For deals with 3-5 missing event types, this saves 2-4 LLM calls.

4. **Reduced overlap** (confidence: MEDIUM). Reduce chunk overlap from "1-2 blocks" to "1 block" consistently. The consolidation event dedup already handles the boundary case. Saves ~5-10% of chunk processing tokens.

5. **Half-deal parallelism** (confidence: LOW, requires new orchestration). Split chronology at the midpoint, run two sequences in parallel, reconcile rosters at the merge point. Adds one reconciliation call but could halve wall time for large deals (20+ chunks). Not recommended until cross-deal parallelism and roster compression are confirmed insufficient.

6. **Model tiering** (confidence: LOW, requires validation). Use a faster model for chunk extraction, quality model for consolidation. Requires per-deal accuracy validation before relying on it. Defer until a dedicated model evaluation run confirms acceptable accuracy.

---

## 4. Summary: Priority Actions

### Priority 1: Fix export bidder_type (Section 2.1)
**What:** Update export-csv SKILL.md to clarify "first row for each actor" means the chronologically first event row naming that actor in the `bidder` column, and add a post-build self-check.
**Why:** 13 of 28 STEC field mismatches are this single bug. It's 100% systematic and filing-grounded.
**Effort:** SKILL.md update, 15 minutes.
**Confidence:** CERTAIN.

### Priority 2: Adopt lower-bound-as-val convention (Section 2.2)
**What:** Update export-csv SKILL.md: for range bids, populate `val` with `range_low`.
**Why:** 100% consistent across 797 range-bid rows in Alex's workbook. Eliminates 3 systematic mismatches in STEC (WDC twice, Company H once) with zero ambiguity.
**Effort:** One-line SKILL.md addition, 5 minutes.
**Confidence:** CERTAIN.

### Priority 3: Strengthen soft-withdrawal drop detection (Section 2.3)
**What:** Add to extract-deal SKILL.md: extract `drop` for "indicated unable to raise offer" language, not just explicit declinations.
**Why:** Company H May 23 is filing-grounded (line 1502, reconciliation confirms) and the pipeline missed it. Pattern likely affects other deals too.
**Effort:** SKILL.md update, 30 minutes.
**Confidence:** HIGH.

### Priority 4: Roster compression in chunk carry-forward (Section 3.4)
**What:** Add instruction to extract-deal SKILL.md: strip `evidence_refs` from actor objects before passing them as the running roster to subsequent chunks.
**Why:** Reduces prompt size by 15-25% for large deals with zero accuracy loss. No structural change.
**Effort:** SKILL.md update, 10 minutes.
**Confidence:** HIGH.

### Priority 5: Add informal round consolidation rule (Section 2.4)
**What:** Add to extract-deal SKILL.md consolidation pass: infer `final_round_inf_ann` / `final_round_inf` from IOI solicitation pattern when no explicit announcement exists in filing.
**Why:** Alex uses this in 7 deals; it's already in the 20-type taxonomy. STEC shows it's a consistent categorization Alex applies.
**Effort:** SKILL.md update, 20 minutes.
**Confidence:** MEDIUM (STEC shows the pattern; not yet verified across all 7 workbook occurrences).

### Priority 6: Reconcile-alex systematic date error flag (Section 2.5)
**What:** Add to reconcile-alex SKILL: flag deals where multiple bidders share the same `date_p` while having different `date_r` values.
**Why:** STEC shows this is a detectable data quality signal in Alex's workbook. Post-export diagnostic only.
**Effort:** reconcile-alex SKILL.md update, 30 minutes.
**Confidence:** HIGH.

### Not recommended now

- **Model tiering** (Section 3.5): Requires per-deal accuracy validation, medium risk.
- **Half-deal parallelism** (Section 3.6): Complex orchestration, defer until simpler speedups confirmed insufficient.
- **Adding DropM/IB Terminated/Exclusivity to pipeline taxonomy** (Section 1.4): These are Alex-specific labels for rare events (109, 1, 1 occurrences). The pipeline's `drop` type with `drop_reason_text` covers DropM semantics. Adding taxonomy types for rare edge cases increases complexity without proportional value.
