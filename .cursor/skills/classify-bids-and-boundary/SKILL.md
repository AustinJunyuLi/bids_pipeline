---
name: classify-bids-and-boundary
description: Classifies proposal events as formal or informal, determines the formal boundary, and records initiation judgments. Use after cycle segmentation or when deal interpretation judgments need to be rebuilt.
---

# classify-bids-and-boundary

## Design Principles

1. The filing is the single source of truth. Every fact traces to
   `source_accession_number` + verbatim `source_text`.
2. Fail closed on source ambiguity. Fail open on extraction incompleteness.
3. Facts before judgments. Proposals are raw events. Classification is
   Skill 8, not Skill 5.
4. Alex's collection instructions are the extraction spec. Used for
   methodology and taxonomy. Never as a factual source.
5. master.csv is the review artifact, not the estimation artifact.

## Overview

Apply formal/informal classification to each proposal event using a
priority-ordered rule set. Determine the informal-to-formal boundary
event. Record the initiation judgment (who started the deal process).
This is the final enrichment skill -- it produces the interpretive
layer that sits on top of the factual extraction.

## Input

- `Data/deals/<slug>/extraction/events.jsonl` (from Skill 5)
- `Data/deals/<slug>/enrichment/process_cycles.jsonl` (from Skill 7)

## Output

- `Data/deals/<slug>/enrichment/judgments.jsonl` (bid classifications +
  interpretive judgments: initiation and formal_boundary)
- `Data/deals/<slug>/extraction/decisions.jsonl` (append to existing
  log -- MANDATORY for ambiguous classification decisions)

## Tools

| Tool | Purpose |
|------|---------|
| File read | Read events.jsonl, process_cycles.jsonl |
| File write | Write judgments.jsonl, append to decisions.jsonl |

## Procedure

### Step 1: Load Inputs

1. **Read `extraction/events.jsonl`** and filter to `event_type:
   "proposal"` events. Also load all events for round timing context.
2. **Read `enrichment/process_cycles.jsonl`** to get round structure
   and cycle boundaries.

### Step 2: Classify Each Proposal

For each proposal event, apply the classification rules **in priority
order**. The first matching rule wins.

**Classification Rules (priority order):**

1. **Post-final-round proposals = formal.** If the proposal date is
   after the announcement of the final round (`final_round_ann` or
   `final_round_ext_ann`), classify as `formal`. Rule:
   `post_final_round_announcement`.

2. **Proposals with merger agreement draft = formal.** If the event's
   `evidence_attributes.accompanied_by_merger_agreement` is true,
   classify as `formal`. Rule: `merger_agreement_draft`.

3. **"Indication of interest" or range bids = informal.** If the
   event's `evidence_attributes.filing_language` contains "indication
   of interest", or if the event has `value_lower` and `value_upper`
   (a range bid), classify as `informal`. Rule:
   `indication_or_range`.

4. **All other proposals = informal (default).** If no other rule
   matches, classify as `informal`. Rule: `default_informal`.

Write one `bid_classification` judgment per proposal event to
`judgments.jsonl`.

**Ambiguous cases:** When a proposal has conflicting signals (e.g.,
post-final-round but described as an "indication"), apply the
highest-priority matching rule. Set `confidence: "medium"` or
`confidence: "low"` and log a decision to `decisions.jsonl`.

See `references/classification-rules.md` for detailed rule
definitions with examples and filing signal language.

### Step 3: Determine Formal Boundary

1. **Identify the transition point** where informal bidding becomes
   formal bidding. This is typically the event (or narrow range of
   events) where the process shifts from indications of interest to
   binding offers.
2. **Record as a `formal_boundary` judgment** in judgments.jsonl with:
   - The boundary event_id (or event_ids if a range)
   - Confidence (high / medium / low)
   - Source text supporting the determination
   - Alternative interpretation (if any)
3. **Uncertain boundary:** If the filing does not clearly mark a
   transition, set `confidence: "low"` and `needs_review: true`.
   Record the best available interpretation with alternatives.

### Step 4: Record Initiation Judgment

1. **Determine who initiated the deal process:**
   - `target_driven`: Board authorized the sale exploration.
   - `bidder_driven`: An unsolicited offer triggered the process.
   - `activist_driven`: Activist pressure drove the decision.
   - `mixed`: Multiple initiating forces contributed.
2. **Record as an `initiation` judgment** in judgments.jsonl with
   basis, source_text, confidence, and alternative interpretation.

### Step 5: Write Output

1. **Write `enrichment/judgments.jsonl`** -- one JSON line per
   judgment. File contains all three judgment types: bid_classification
   (one per proposal), formal_boundary (one per deal), and initiation
   (one per deal).
2. **Append to `extraction/decisions.jsonl`** for any ambiguous
   classification decisions.

## Gate

`enrichment/judgments.jsonl` exists with at least 1 judgment.

## Failure Mode

**Fail open.** Ambiguous classifications produce `needs_review` flags
and low-confidence judgments. The pipeline continues. Skill 9 will
propagate flags to master_rows.csv.

## Common Mistakes

- **Forcing a formal boundary where the filing only supports a
  transition zone.** If the filing describes a gradual shift from
  informal to formal bidding without a clear demarcation event, record
  the boundary with `confidence: "low"` and describe the transition
  zone in `alternative_basis`. Do not invent a sharp boundary that
  the filing does not support.

## Decision Log (MANDATORY)

Every ambiguous classification decision MUST be logged to
`extraction/decisions.jsonl`. Examples:

- Classifying a post-final-round "indication of interest" (conflicting
  signals -- Rule 1 vs Rule 3).
- Setting a formal boundary when the transition is gradual.
- Choosing between target_driven and mixed initiation.

## Required Reading

1. `references/classification-rules.md` -- the 4 classification rules
   with examples and filing signals, boundary determination procedure,
   initiation judgment types, judgments.jsonl full schema with examples
