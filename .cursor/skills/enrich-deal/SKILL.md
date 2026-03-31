---
name: enrich-deal
description: Legacy-only v1 skill for adding interpretive enrichment to verified event-first extraction artifacts.
---

# enrich-deal

## Status

This is the retired v1 interpretive enrichment step. The live v2 default has no
analogous mandatory enrichment stage.

## Design Principles

1. The filing is the single source of truth. Every judgment must cite verbatim
   filing text.
2. Deterministic enrichment is authoritative for bid_classifications, rounds,
   cycles, formal_boundary, sparse DropTarget labels, and all_cash_overrides.
   This skill fills interpretive gaps that require filing reading comprehension.
3. Diagnostic outputs (count reconciliation) never alter data.
4. Facts come from extract-deal. Deterministic classifications come from
   enrich-core. Interpretive judgments come from this skill.

## Purpose

Provide the interpretive enrichment layer that deterministic rules cannot.
Classify dropout reasons that require reading the filing narrative, judge who
initiated the sale process, verify advisory attribution links, and reconcile
filing count assertions against extracted totals.

## When To Use

- This skill is a **mandatory pipeline gate**. It runs after
  `skill-pipeline enrich-core` and before `skill-pipeline db-load` /
  `skill-pipeline db-export`. Do not skip.
- Called by `/deal-agent-legacy` as a required step, or independently via
  `/enrich-deal <slug>`.
- Prerequisite: verified `actors_raw.json` and `events_raw.json` exist in
  `data/skill/<slug>/extract/`, and `deterministic_enrichment.json` exists in
  `data/skill/<slug>/enrich/`.

**Deterministic baseline:** Run `skill-pipeline enrich-core --deal <slug>`
first. It writes `enrich/deterministic_enrichment.json` with six sections:
`rounds`, `bid_classifications`, `cycles`, `formal_boundary`,
`dropout_classifications` (sparse DropTarget labels only), and
`all_cash_overrides`. This skill reads that baseline and adds what deterministic
rules cannot produce.

## Benchmark Boundary

Benchmark materials are forbidden during generation. Do not consult benchmark
files, benchmark notes, `example/`, `diagnosis/`,
`data/skill/<slug>/reconcile/*`, or `/reconcile-alex` before
`skill-pipeline db-export --deal <slug>` completes.

Use only filing-grounded extract and source artifacts during enrichment.
Benchmark comparison is post-export only and read-only.

## Reads

| File | What it provides |
|---|---|
| `data/skill/<slug>/extract/actors_raw.json` | Verified actor roster with roles, advisory links, count_assertions |
| `data/skill/<slug>/extract/events_raw.json` | Verified event timeline with quote_ids, terms, formality_signals |
| `data/skill/<slug>/enrich/deterministic_enrichment.json` | Deterministic baseline: rounds, bid_classifications, cycles, formal_boundary, dropout_classifications (sparse DropTarget), all_cash_overrides |
| `data/deals/<slug>/source/chronology_blocks.jsonl` | Narrative blocks for rereading filing context |
| `data/deals/<slug>/source/evidence_items.jsonl` | Pre-tagged evidence anchors |
| `raw/<slug>/filings/*.txt` | Frozen filing text for verbatim citation |

## Enrichment Tasks

All 4 tasks must be completed. No internal ordering dependency.

---

### Task 1: Interpretive Dropout Classification

**Scope:** Classify drop events that `enrich-core` did NOT already label as
DropTarget. Read `deterministic_enrichment.json` first. For each `drop` event
in events_raw.json:

- If the event_id already appears in `deterministic_enrichment.json`'s
  `dropout_classifications` with label `DropTarget`, **do not override it**.
  Skip this event.
- If the event_id is NOT in the deterministic dropout_classifications, read
  `drop_reason_text` and the full event history for that actor. Classify into
  exactly one of 4 labels:

| Label | Condition |
|---|---|
| `Drop` | Bidder informed of withdrawal, or general exit. This is the default when no more specific label applies. |
| `DropBelowM` | Filing says the valuation was below market or trading price. Use filing language only. If the filing does not explicitly mention a market-price comparison, classify as `Drop` and add `dropout_needs_market_data:evt_XXX` to review_flags. |
| `DropBelowInf` | Filing says the valuation was below the bidder's earlier informal bid. Verify by comparing the drop event's value (if stated) against the actor's extracted proposal values from earlier events. If no prior proposal is extracted for this actor, classify as `Drop` and flag. |
| `DropAtInf` | Filing says the valuation was at the bidder's earlier informal bid (no improvement). Verify by comparing against the actor's extracted proposal values from earlier events. If no prior proposal is extracted for this actor, classify as `Drop` and flag. |

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

### Task 2: Initiation Judgment

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

### Task 3: Advisory Attribution Verification

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

### Task 4: Count Reconciliation (Diagnostic Only)

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

- `data/skill/<slug>/enrich/enrichment.json` -- interpretive enrichment with
  5 top-level keys: `dropout_classifications`, `initiation_judgment`,
  `advisory_verification`, `count_reconciliation`, `review_flags`

This skill does NOT write `deterministic_enrichment.json`. That file is
produced by `skill-pipeline enrich-core` and is read-only input to this skill.

## JSON Format

The output must contain all 5 sections. Use `event_id` keys (e.g., `evt_016`,
`evt_011`), NOT event_index or positional references.

```json
{
  "dropout_classifications": {
    "evt_016": {
      "label": "DropBelowInf",
      "basis": "Party C's revised indication of $18.50 was below their earlier informal bid of $19.25",
      "source_text": "Party C submitted a revised indication..."
    },
    "evt_025": {
      "label": "Drop",
      "basis": "Party E informed the Company it was no longer interested",
      "source_text": "On October 3, Party E informed representatives of the Company..."
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
    "advisory_mismatch:advisor_wachtell"
  ]
}
```

Note: `dropout_classifications` here contains ONLY events not already
classified as DropTarget by `deterministic_enrichment.json`. Events with
deterministic DropTarget labels are omitted from this output; db-load merges
both sources.

### Field Reference

- **dropout_classifications**: keyed by drop event_id. Only events NOT already
  classified as DropTarget by deterministic enrichment. Events with
  deterministic DropTarget labels must not appear here.
- **initiation_judgment**: single object. Always present.
- **advisory_verification**: keyed by advisor actor_id. Every advisor actor
  must have an entry.
- **count_reconciliation**: list of reconciliation entries. One per
  count_assertion. May be empty if no count_assertions exist.
- **review_flags**: flat list of strings. Format: `flag_name:entity_id`.
  Collect flags from all tasks. May be empty.

## Gate

`enrichment.json` exists and contains all 5 top-level keys:
`dropout_classifications`, `initiation_judgment`, `advisory_verification`,
`count_reconciliation`, `review_flags`. Fail closed if any key is missing.
