---
name: enrich-deal
description: Use when enriching verified skill extraction artifacts with bid classification, cycle structure, initiation judgment, and advisory or count review.
---

# enrich-deal

## Design Principles

1. The filing is the single source of truth. Every judgment must cite verbatim
   filing text.
2. Classification rules have strict priority order. Do not skip or reorder.
3. Diagnostic outputs (count reconciliation) never alter data.
4. Facts come from extract-deal. Judgments come from this skill.

## Purpose

Analyze what the extracted facts mean. Classify bids, segment cycles, determine
initiation, verify advisory links. This is where reading comprehension matters
most.

## When To Use

- Called by deal-agent after verify-extraction, or independently via
  `/enrich-deal <slug>`.
- Prerequisite: verified `actors_raw.json` and `events_raw.json` exist in
  `data/skill/<slug>/extract/`.

**Deterministic core:** Run `skill-pipeline enrich-core --deal <slug>` first.
This writes `enrich/deterministic_enrichment.json` with `rounds`,
`bid_classifications`, `cycles`, and `formal_boundary`. Residual bid
classification is `Uncertain`, not forced `Informal`. The interpretive remainder
(initiation, advisory verification, count reconciliation) stays in this skill.

## Benchmark Boundary

Benchmark materials are forbidden during generation. Do not consult benchmark
files, benchmark notes, `example/`, `diagnosis/`,
`data/skill/<slug>/reconcile/*`, or `/reconcile-alex` before `/export-csv`
completes.

Use only filing-grounded extract and source artifacts during enrichment.
Benchmark comparison is post-export only and read-only.

## Reads

| File | What it provides |
|---|---|
| `data/skill/<slug>/extract/actors_raw.json` | Verified actor roster with roles, advisory links, count_assertions |
| `data/skill/<slug>/extract/events_raw.json` | Verified event timeline with evidence_refs, terms, formality_signals |
| `data/deals/<slug>/source/chronology_blocks.jsonl` | Narrative blocks for rereading filing context |
| `data/deals/<slug>/source/evidence_items.jsonl` | Pre-tagged evidence anchors |
| `raw/<slug>/filings/*.txt` | Frozen filing text for verbatim citation |

## Enrichment Tasks

All 8 tasks must be completed in this order. Do not skip any task. Do not
reorder. Tasks 1-2 depend on Task 3's output, so compute Task 3 first even
though it appears third in the output schema.

**Execution order: 3 -> 4 -> 5 -> 1 -> 2 -> 6 -> 7 -> 8.**

---

### Task 1: Dropout Classification

For each `drop` event in events_raw.json, read `drop_reason_text` and the full
event history for that actor. Classify into exactly one of 5 labels:

| Label | Condition |
|---|---|
| `Drop` | Bidder informed of withdrawal, or general exit. This is the default when no more specific label applies. |
| `DropBelowM` | Filing says the valuation was below market or trading price. Use filing language only. If the filing does not explicitly mention a market-price comparison, classify as `Drop` and add `dropout_needs_market_data:evt_XXX` to review_flags. |
| `DropBelowInf` | Filing says the valuation was below the bidder's earlier informal bid. Verify by comparing the drop event's value (if stated) against the actor's extracted proposal values from earlier events. If no prior proposal is extracted for this actor, classify as `Drop` and flag. |
| `DropAtInf` | Filing says the valuation was at the bidder's earlier informal bid (no improvement). Verify by comparing against the actor's extracted proposal values from earlier events. If no prior proposal is extracted for this actor, classify as `Drop` and flag. |
| `DropTarget` | Target excluded the bidder from continuing (did not invite to next round). The filing must indicate target-initiated exclusion, not bidder-initiated withdrawal. |

**DropTarget directionality:** DropTarget requires the TARGET to initiate
exclusion without the bidder first signaling withdrawal. If the sequence is:
(1) bidder says it cannot improve its bid, then (2) target confirms
disinterest — classify based on the bidder's stated position (DropAtInf or
DropBelowInf), not as DropTarget. DropTarget applies only when the target
proactively excludes a bidder who has not signaled withdrawal.

**DropBelowM rule:** Use filing language only. Do not infer market-price
comparisons from external data. If the filing says something like "below the
current trading price" or "less than the market value," that qualifies. If the
filing simply says the bid was too low without referencing market price,
classify as `Drop` and add `dropout_needs_market_data:evt_XXX` to
review_flags.

**DropBelowInf/DropAtInf comparison logic:**
1. Find all prior proposal events where this actor appears in `actor_ids`.
2. Extract `terms.per_share` from each prior proposal.
3. Compare the drop event's stated value (from `drop_reason_text` or context)
   against the most recent prior proposal value.
4. If the drop value < prior proposal value: `DropBelowInf`.
5. If the drop value == prior proposal value: `DropAtInf`.
6. If no prior proposal exists for this actor: classify as `Drop` and add
   `dropout_comparison_missing_prior:evt_XXX` to review_flags.

---

### Task 2: Bid Classification (Formal/Informal)

For each `proposal` event in events_raw.json, apply classification rules in
strict priority order. First matching rule wins. Do not skip to a later rule
if an earlier rule matches.

| Priority | Rule | Label | Basis |
|---|---|---|---|
| 1 | Range bid (`contains_range=true`) OR explicit informal language: `mentions_indication_of_interest=true`, `mentions_preliminary=true`, or `mentions_non_binding=true` | `Informal` | Observable text signal from formality_signals |
| 2 | Draft/marked-up agreement (`includes_draft_merger_agreement=true` or `includes_marked_up_agreement=true`) OR explicit binding offer (`mentions_binding_offer=true`) | `Formal` | Observable text signal from formality_signals |
| 3 | Proposal follows a selective final round: `invited_actor_ids` is a strict subset of active bidders at that point in time | `Formal` | Round context + selectivity test |
| 4 | Residual case: none of the above rules matched | `Uncertain` | Conflicting signals; do not force Informal |

**Rule 3 selectivity test:**
1. From the `rounds` output (Task 3), find the most recent round announcement
   that precedes this proposal chronologically.
2. Count active bidders at the time of that round announcement: actors who have
   an NDA event and no prior drop event as of that date.
3. Compare `active_bidders_at_time` to `len(invited_actor_ids)`.
4. If `len(invited_actor_ids) < active_bidders_at_time`, the round is
   selective, and this rule applies.

**Fallback when invited_actor_ids is missing or incomplete:** If the round
announcement event does not have `invited_actor_ids` populated, fall back to
the post-announcement heuristic: check whether only a subset of previously
active bidders submitted proposals after the announcement. This is weaker
evidence. Apply the Formal label but add
`bid_classification_uncertain:evt_XXX` to review_flags.

---

### Task 3: Round Structure

**This task must be computed BEFORE Tasks 1 and 2** because dropout
classification and bid classification depend on round context.

Pair each round announcement event with its corresponding deadline event.
Round announcement types and their paired deadline types:

| Announcement Type | Deadline Type |
|---|---|
| `final_round_inf_ann` | `final_round_inf` |
| `final_round_ann` | `final_round` |
| `final_round_ext_ann` | `final_round_ext` |

For each paired round, record:

- `announcement_event_id`: the event_id of the announcement event
- `deadline_event_id`: the event_id of the deadline event (null if no
  corresponding deadline was extracted)
- `round_scope`: `formal`, `informal`, or `extension`, taken from the announcement
  event's `round_scope` field (extension rounds use `final_round_ext_ann`/`final_round_ext`)
- `invited_actor_ids`: from the announcement event (empty list if not
  identifiable)
- `active_bidders_at_time`: count of actors who have an NDA event and no prior
  drop event as of the announcement date
- `is_selective`: true when `len(invited_actor_ids) < active_bidders_at_time`
  and `invited_actor_ids` is non-empty; false otherwise

---

### Task 4: Cycle Segmentation

Identify process cycles from `terminated` and `restarted` events:

- **Single cycle:** No `terminated` or `restarted` events exist. The entire
  event timeline is one cycle.
- **Multi-cycle:** Each `terminated` event followed by a `restarted` event
  defines a cycle boundary. The cycle before the termination is one cycle; the
  cycle starting at the restart is the next.

For each cycle, record:
- `cycle_id`: `cycle_1`, `cycle_2`, etc.
- `start_event_id`: first event in this cycle (first event overall for cycle_1,
  restarted event_id for subsequent cycles)
- `end_event_id`: last event in this cycle (terminated event_id, or final event
  overall for the last cycle)
- `boundary_basis`: verbatim filing text or description of what triggered the
  boundary. For single-cycle deals, use `Single cycle -- no termination events`.

---

### Task 5: Formal Boundary

For each cycle, identify the first formal proposal. This is the event where the
deal shifted from exploratory to serious.

A proposal is formal if its bid classification (Task 2) is `Formal`.

Record:
- Key: the cycle_id (e.g., `cycle_1`)
- `event_id`: the event_id of the first formal proposal in that cycle
- `basis`: one-sentence explanation of why this is the formal boundary, citing
  the classification rule that applied

If a cycle has no formal proposals, record `event_id: null` and
`basis: "No formal proposals in this cycle"`.

---

### Task 6: Initiation Judgment

Determine who started the sale process. Read the earliest events in the
timeline and the surrounding filing narrative.

Four possible types:

| Type | Meaning |
|---|---|
| `target_driven` | Board proactively decided to explore strategic alternatives. First process event is `target_sale` or equivalent board decision. |
| `bidder_driven` | An unsolicited approach triggered the process. First process event is `bidder_interest` or `bidder_sale` before any board decision to sell. |
| `activist_driven` | Activist pressure forced the board's hand. `activist_sale` precedes or triggers the board's decision. |
| `mixed` | Multiple factors contributed. E.g., bidder interest coincided with board discussions already underway. |

Required output fields:
- `type`: one of the four labels above
- `basis`: one-sentence explanation of the judgment
- `source_text`: verbatim quote from the filing that supports the judgment
- `confidence`: `high`, `medium`, or `low`

Use `high` when the filing clearly describes a single initiating cause. Use
`medium` when the filing is suggestive but not explicit. Use `low` when the
filing is ambiguous or contradictory and you are making an inference.

---

### Task 7: Advisory Attribution Verification

For each actor with `role: "advisor"` in actors_raw.json:
1. Read the `advised_actor_id` field.
2. Search the filing text for the passage that establishes the advisory
   relationship.
3. Confirm the link matches. For example, if the filing says "Goodwin Procter,
   counsel to the Company," verify that `advised_actor_id` points to the
   target-side actor.
4. Flag mismatches: if the filing text contradicts the extracted
   `advised_actor_id`, record `verified: false` and add
   `advisory_mismatch:advisor_XXX` to review_flags.
5. If `advised_actor_id` is null but the filing clearly states who the advisor
   represents, record `verified: false` and flag
   `advisory_missing_link:advisor_XXX`.

---

### Task 8: Count Reconciliation (Diagnostic Only)

**This output is diagnostic. It never alters data. It informs review_flags.**

Compare each `count_assertion` from actors_raw.json against the actual
extracted counts. For example, if the filing asserts "15 parties signed
confidentiality agreements" and you extracted 12 NDA events, that is a
mismatch of 3.

For each mismatch, classify into exactly one of this 7-label closed set:

| Label | Meaning |
|---|---|
| `advisor_exclusion` | The filing counts advisors among the parties, but extraction correctly excludes them from bidder counts. |
| `stale_process` | The filing references parties from a prior process or earlier timeframe not covered by the chronology. |
| `unnamed_aggregate` | The filing counts unnamed parties in aggregate that were not individually extracted. |
| `filing_approximation` | The filing uses approximate language ("approximately 15", "more than a dozen"). |
| `consortium_counted_once` | Extraction counted consortium members individually, but the filing counted the consortium as one party. |
| `partial_bidder_excluded` | The filing counts partial-company bidders that were correctly excluded from extraction. |
| `unresolved` | The mismatch cannot be explained by any of the above categories. |

When counts match exactly, still record the reconciliation with a note
confirming the match.

---

## Writes

- `data/skill/<slug>/enrich/deterministic_enrichment.json` — from
  `skill-pipeline enrich-core` (rounds, bid_classifications, cycles, formal_boundary)
- `data/skill/<slug>/enrich/enrichment.json` — full enrichment including
  initiation_judgment, advisory_verification, count_reconciliation, review_flags

## JSON Format

The output must contain all 8 sections. Use `event_id` keys (e.g., `evt_016`,
`evt_011`), NOT event_index or positional references.

```json
{
  "dropout_classifications": {
    "evt_016": {
      "label": "DropBelowInf",
      "basis": "Party C's revised indication of $18.50 was below their earlier informal bid of $19.25",
      "source_text": "Party C submitted a revised indication..."
    },
    "evt_023": {
      "label": "DropTarget",
      "basis": "Target did not invite Party D to the final round",
      "source_text": "the Special Committee determined not to invite Party D..."
    },
    "evt_025": {
      "label": "Drop",
      "basis": "Party E informed the Company it was no longer interested",
      "source_text": "On October 3, Party E informed representatives of the Company..."
    }
  },
  "bid_classifications": {
    "evt_011": {
      "label": "Formal",
      "rule_applied": 2,
      "basis": "Proposal included marked-up merger agreement"
    },
    "evt_008": {
      "label": "Informal",
      "rule_applied": 1,
      "basis": "Proposal described as preliminary indication of interest"
    },
    "evt_019": {
      "label": "Formal",
      "rule_applied": 3,
      "basis": "Proposal submitted after selective final round (3 of 7 active bidders invited)"
    },
    "evt_022": {
      "label": "Uncertain",
      "rule_applied": null,
      "basis": "Residual case; conflicting signals"
    }
  },
  "rounds": [
    {
      "announcement_event_id": "evt_009",
      "deadline_event_id": "evt_012",
      "round_scope": "informal",
      "invited_actor_ids": [],
      "active_bidders_at_time": 8,
      "is_selective": false
    },
    {
      "announcement_event_id": "evt_014",
      "deadline_event_id": "evt_018",
      "round_scope": "formal",
      "invited_actor_ids": ["bidder_sponsor_a", "bidder_sponsor_b", "bidder_thoma_bravo"],
      "active_bidders_at_time": 5,
      "is_selective": true
    }
  ],
  "cycles": [
    {
      "cycle_id": "cycle_1",
      "start_event_id": "evt_001",
      "end_event_id": "evt_029",
      "boundary_basis": "Single cycle -- no termination events"
    }
  ],
  "formal_boundary": {
    "cycle_1": {
      "event_id": "evt_020",
      "basis": "First formal proposal per Rule 2 (includes_draft_merger_agreement=true)"
    }
  },
  "initiation_judgment": {
    "type": "bidder_driven",
    "basis": "Thoma Bravo approached Imprivata before any board decision to explore alternatives",
    "source_text": "In early 2015, and again in June 2015, representatives of Thoma Bravo informally approached representatives of Imprivata",
    "confidence": "high"
  },
  "advisory_verification": {
    "advisor_goodwin": {
      "advised_actor_id": "target_board",
      "verified": true,
      "source_text": "Goodwin Procter, counsel to the Company"
    },
    "advisor_morgan_stanley": {
      "advised_actor_id": "target_board",
      "verified": true,
      "source_text": "Morgan Stanley & Co. LLC, financial advisor to the Company"
    }
  },
  "count_reconciliation": [
    {
      "assertion": "15 parties signed confidentiality agreements",
      "extracted_count": 12,
      "classification": "unnamed_aggregate",
      "note": "Filing counts unnamed parties in aggregate; 3 parties were never individually named in the chronology"
    },
    {
      "assertion": "7 bidders were invited to the final round",
      "extracted_count": 7,
      "classification": null,
      "note": "Counts match exactly"
    }
  ],
  "review_flags": [
    "dropout_needs_market_data:evt_016",
    "bid_classification_uncertain:evt_022",
    "advisory_mismatch:advisor_wachtell"
  ]
}
```

### Field Reference

- **dropout_classifications**: keyed by drop event_id. Every drop event must
  have an entry.
- **bid_classifications**: keyed by proposal event_id. Every proposal event
  must have an entry.
- **rounds**: ordered list of round pairs. May be empty if no round events
  exist.
- **cycles**: ordered list of cycles. Always at least one entry.
- **formal_boundary**: keyed by cycle_id. Every cycle must have an entry (use
  `event_id: null` if no formal proposals in that cycle).
- **initiation_judgment**: single object. Always present.
- **advisory_verification**: keyed by advisor actor_id. Every advisor actor
  must have an entry.
- **count_reconciliation**: list of reconciliation entries. One per
  count_assertion. May be empty if no count_assertions exist.
- **review_flags**: flat list of strings. Format: `flag_name:entity_id`.
  Collect flags from all tasks. May be empty.

## Gate

`enrichment.json` exists and contains all 8 top-level keys. Fail closed if
any key is missing.
