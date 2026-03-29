# Cross-Deal Reconciliation Analysis: Pipeline vs. Alex

Generated: 2026-03-29
Deals: imprivata, mac-gray, medivation, penford, petsmart-inc, providence-worcester, saks, stec, zep

## Headline Numbers (9 deals)

| Metric | Count |
|---|---|
| Pipeline events | 207 |
| Alex rows (total) | 269 |
| Alex atomic rows | 222 |
| Alex aggregate rows | 47 |
| Matched pairs | 156 |
| Pipeline-only (grounded) | 47 |
| Alex-only (atomic) | 65 |
| Arbitrations: pipeline wins | 45 |
| Arbitrations: Alex wins | 16 |
| Both defensible / inconclusive | 24 |

When the filing is consulted as tiebreaker, the pipeline is right ~3x more often than Alex.

## Per-Deal Scorecard

| Deal | Pipeline | Alex | Matched | Pipe-only | Alex-only | Agg | Status |
|---|---|---|---|---|---|---|---|
| imprivata | 28 | 29 | 23 | 5 | 6 | 0 | attention |
| mac-gray | 27 | 34 | 23 | 4 | 7 | 3 | attention |
| medivation | 33 | 16 | 12 | 19 | 2 | 2 | attention |
| penford | 23 | 25 | 17 | 3 | 8 | 4 | attention |
| petsmart-inc | 14 | 53 | 12 | 2 | 10 | 31 | attention |
| prov-worcester | 18 | 36 | 15 | 3 | 10 | 4 | attention |
| saks | 19 | 25 | 17 | 4 | 8 | 0 | attention |
| stec | 29 | 28 | 23 | 6 | 5 | 0 | attention |
| zep | 16 | 23 | 14 | 1 | 9 | 3 | attention |

## Systematic Difference #1: Granularity Philosophy

Pipeline = filing-literal atomic events. Every distinct action the filing describes gets its own event row.

Alex = research-coded summary rows. Alex often bundles:
- Aggregate rows (PetSmart: "15 parties NDA", "6 parties IOI", Providence-Worcester: "25 parties NDA", "9 IOIs")
- Round milestone rows (Final Round Inf Ann, Final Round Inf, Final Round Ext Ann, Final Round Ext)

This explains why Alex has 269 rows vs pipeline's 207. Alex's aggregate rows inflate the count, but his atomic event count (222) is close to pipeline's 207.

Illustration: PetSmart -- Alex has 53 rows but 31 are aggregate per-party rows. Pipeline has 14 events capturing the deal skeleton.

## Systematic Difference #2: Date Accuracy

Pipeline is consistently more accurate on dates. Filing-arbitrated date disagreements:

| Deal | Event | Pipeline date | Alex date | Filing says |
|---|---|---|---|---|
| imprivata | IB retention | 2016-04-19 | 2016-03-09 | Apr 19 |
| imprivata | Executed | 2016-07-13 | 2016-07-09 | Jul 13 |
| mac-gray | Party C NDA | 2013-06-30 | 2013-06-20 | Jun 30 |
| mac-gray | Executed | 2013-10-14 | 2013-09-21 | Oct 14 |
| medivation | IB retention | 2016-03-24 | 2016-06-29 | Mar 24 |
| penford | Executed | 2014-10-14 | 2014-10-08 | Oct 14 |
| petsmart-inc | Final Round Ann | 2014-11-03 | 2014-11-15 | Nov 3 |
| prov-worcester | Late-July LOIs | ~Jul 25 | Jul 20 | "late July" |
| zep | Target Sale | 2014-01-28 | 2014-01-31 | Jan 28 |
| zep | Executed | 2015-04-07 | 2015-04-08 | Apr 7 |

Pattern: Alex's date errors cluster around (a) confusing merger-agreement date with press-release date, (b) using deadline dates instead of filing-stated dates, (c) simple transcription errors. Pipeline's span-backed extraction anchors dates to specific filing passages.

## Systematic Difference #3: bid_type Classification (Pipeline's Biggest Bug)

The pipeline's deterministic enrichment systematically misclassifies final-round proposals as Informal when the filing uses "indication of interest" language, even though these are clearly formal-round responses.

| Deal | Event | Pipeline | Alex | Filing reality |
|---|---|---|---|---|
| mac-gray | Party A $18 (Sep 18) | Informal | Formal | Final-round deadline response |
| mac-gray | Party B $17-19 (Sep 18) | Informal | Formal | Final-round deadline response |
| stec | WDC $9.15 (May 28) | Informal | Formal | Marked merger agreement attached |
| prov-worcester | G&W $25 revised LOI | Informal | Formal | 24-hour expiry, merger mark-ups |
| imprivata | $19.25 best-and-final | Informal | Formal | Solicited via process letter |
| penford | $17 oral (Aug 6) | Uncertain | Informal | Oral proposal, no binding docs |
| penford | $18.50 oral (Oct 2) | Uncertain | Informal | Oral proposal, no binding docs |

Root cause: Enrichment rule 1.0 (IOI/indication-of-interest language -> Informal) takes priority over rule 2.5 (after final round announcement -> Formal). This is a mechanical rule-ordering bug. Alex is right: M&A convention classifies final-round submissions as Formal regardless of filing terminology.

## Systematic Difference #4: Event Type Coverage

### Things the pipeline captures that Alex doesn't

| Event type | Deals affected | Examples |
|---|---|---|
| bidder_interest (early-stage) | imprivata, stec, saks, medivation | Pre-NDA expressions of interest |
| target_sale (board decision) | imprivata, mac-gray, saks, petsmart | Board authorizing the sale process |
| activist_sale | stec, petsmart | 13D amendments, activist pressure |
| bid_press_release | imprivata, stec, petsmart | Public announcement of signed deal |
| sale_press_release | mac-gray | Public sale announcement |
| Per-bidder dropouts | medivation, prov-worcester | Individual Company 1-4 drops |

### Things Alex captures that the pipeline doesn't

| Event type | Deals affected | Examples |
|---|---|---|
| Round milestones | all 9 deals | Final Round Inf Ann, Final Round Inf, deadlines |
| DropTarget (committee exclusion) | mac-gray, stec, prov-worcester, saks | Committee narrows field |
| Aggregate cohort drops | petsmart, prov-worcester, zep | "16 parties dropped" |
| Exclusivity grants | zep | 30-day exclusivity period |
| IB termination | mac-gray | Prior engagement terminated |
| Verbal indications | stec, petsmart | Oral price signals without written IOI |

Pattern: Pipeline is deeper on pre-process and post-signing tails (early interest, board decisions, activist pressure, press releases). Alex is deeper on process structure (round milestones, cohort movements, committee-driven narrowing). Complementary blind spots.

## Systematic Difference #5: all_cash Inference

Pipeline is conservative -- only marks all_cash=1 when the filing sentence explicitly says "cash." Alex infers all_cash from deal context.

| Deal | Pipeline approach | Alex approach | Who's more useful |
|---|---|---|---|
| penford | Explicit only | Contextual inference | Alex (all Ingredion bids were cash) |
| petsmart | Omits on Executed | Marks 1 | Alex (deal was clearly all-cash) |
| prov-worcester | null on $21.15 | Marks 1 | Neither (was cash + CVR mix) |

Design choice, not a bug. Pipeline prioritizes precision; Alex prioritizes coverage.

## Systematic Difference #6: Actor Identity

Pipeline is more precise on actor identification:

| Deal | Event | Pipeline | Alex | Filing |
|---|---|---|---|---|
| saks | Jul 11 joint proposal | Sponsor E + G | Sponsor A + E | Filing says E + G |
| saks | Apr 26 phantom drop | No drop (correct) | Sponsor A Drop | A signed NDA that day |
| zep | Apr 14 IOIs | 5 other parties | Includes NMC | NMC explicitly declined |
| prov-worcester | Party F type | Strategic | Financial | Filing says strategic |

Pattern: Alex's actor errors tend to be (a) confusing consortium membership, (b) including parties who explicitly declined, (c) miscoding bidder type. Pipeline's span-backed extraction prevents these.

## Systematic Difference #7: Structural Framing

1. Sale initiation: Pipeline codes the board's decision to explore (target_sale). Alex codes the first unsolicited approach (Bidder Sale). Both defensible -- different research questions.

2. Round taxonomy: Alex has a richer round vocabulary (Inf/Ext/Formal rounds with Ann/deadline pairs). Pipeline uses a simpler model (round announcements + proposals).

## Actionable Pipeline Bugs

### HIGH -- Must fix

1. bid_type enrichment rule priority: final-round responses must be Formal regardless of IOI language (affects mac-gray, stec, prov-worcester, imprivata, penford)
2. Zep NMC actor error: remove NMC from evt_005 and evt_008 (NMC explicitly declined to bid)
3. Medivation missing drops: evt_013, evt_017 referenced in coverage notes but absent from events array

### MODERATE -- Pipeline gaps to consider

4. Round milestone events (Final Round Inf Ann, deadlines) -- Alex captures; pipeline doesn't
5. DropTarget events (committee narrowing) -- filing-grounded but pipeline omits
6. all_cash contextual inference -- trade precision for coverage
7. Verbal/oral price indications -- stec Company D, petsmart Bidder 3

### Alex coding errors found (for benchmark cleanup)

- 10+ date transcription errors across deals
- Actor misidentifications (saks consortium, zep NMC)
- Bidder type errors (prov-worcester Party F)
- Phantom events (saks Sponsor A "drop" on NDA signing day)
