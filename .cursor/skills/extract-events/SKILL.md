---
name: extract-events
description: Extracts the full 23-type event chronology, links actors, handles open-world actor minting, and writes deal-level provenance artifacts. Use when converting a filing chronology into structured events.
---

# extract-events

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

Event-by-event extraction from the chronology section using the full
23-type event taxonomy. This is the heaviest skill in the pipeline.
Uses a two-pass method: a forward narrative scan followed by a
gap-targeted re-read. Ends with lifecycle closure to ensure every
actor has a terminal status. Also writes `deal.json` with deal-level
metadata and provenance.

## Input

- `Data/deals/<slug>/source/filings/<accession>.txt` (primary filing)
- `Data/deals/<slug>/source/filings/<accession>.txt` (supplementary
  filings, if any -- from corpus_manifest.json)
- `Data/deals/<slug>/source/chronology_bookmark.json` (line range)
- `Data/deals/<slug>/source/corpus_manifest.json` (to identify all
  filings and their roles)
- `Data/deals/<slug>/extraction/actors.jsonl` (initial roster from
  Skill 4)

## Output

- `Data/deals/<slug>/extraction/events.jsonl`
- `Data/deals/<slug>/extraction/event_actor_links.jsonl`
- `Data/deals/<slug>/extraction/deal.json`
- `Data/deals/<slug>/extraction/actors_extended.jsonl` (only if new
  actors minted during extraction -- does NOT overwrite actors.jsonl)
- `Data/deals/<slug>/extraction/decisions.jsonl` (append to existing
  log -- MANDATORY for approximate_date, implicit_dropout,
  event_type_choice, scope_exclusion decisions)

## Tools

| Tool | Purpose |
|------|---------|
| File read | Read .txt in targeted chunks (offset + limit), read actors.jsonl, read chronology_bookmark.json, read corpus_manifest.json |
| File write | Write events.jsonl, event_actor_links.jsonl, deal.json, actors_extended.jsonl, append to decisions.jsonl |

## Procedure

### Pass 1: Forward Narrative Scan

1. **Load the actor roster** from `extraction/actors.jsonl`. These are
   the known parties from Skill 4. Keep them as a lookup for actor_id
   assignment.

2. **Read the chronology in chunks** using the bookmark line range
   (start_line to end_line). Use manageable chunks of 300-500 lines.
   Do NOT read the entire filing in one context dump.

3. **For each chunk, extract events** by scanning for all 23 event
   types from the taxonomy (see `references/event-taxonomy.md`):
   - Process initiation events (target_sale, bidder_sale, etc.)
   - Advisor retention events (ib_retention)
   - NDA events (one per signer)
   - Proposal events (raw -- NO formal/informal classification)
   - Dropout events (with dropout type)
   - Round structure events (announcement + deadline PAIRS)
   - Execution events
   - Lifecycle events (terminated, restarted)

4. **For each event found, record ALL required fields:**
   - `event_id`: unique within the deal
   - `event_type`: from the taxonomy
   - `date`: YYYY-MM-DD (always populated)
   - `date_precision`: exact / approximate / month_only
   - `source_text`: VERBATIM from the .txt file
   - `source_accession_number` and `source_line_start` / `end`
   - Value fields for proposals (value, value_lower, value_upper, etc.)
   - `evidence_attributes` for proposals

5. **Write event_actor_links** for every event-actor relationship with
   `participation_role` (bidder/advisor/counterparty/decision_maker/
   initiator).

6. **Open-world actor minting:** If an event references a party NOT in
   the actors.jsonl roster, mint a new actor with a stable ID and add
   to `actors_extended.jsonl`. Do NOT overwrite actors.jsonl.

7. **Build a running inventory:** Track which taxonomy categories have
   events extracted and which do not. This drives Pass 2.

8. **Supplementary filing scan:** After the primary chronology, read
   supplementary `.txt` files (identified from corpus_manifest.json)
   for events not captured in the primary: activist actions, completion
   dates, additional filings, etc.

### Pass 2: Gap-Targeted Re-Read (ALWAYS RUNS)

Pass 2 always executes, even if Pass 1 appears complete. It catches
systematic gaps that forward-only reading misses.

#### 2a. Taxonomy Completeness Sweep

Check every event type against the Pass 1 inventory. For each type,
produce one of:
- List of extracted event_ids
- Explicit "NOT FOUND" with justification

```
PROCESS INITIATION:
  target_sale:        [event_id or NOT FOUND -- reason]
  target_sale_public: [event_id or NOT FOUND -- reason]
  bidder_sale:        [event_id or NOT FOUND -- reason]
  bidder_interest:    [event_id(s) or NOT FOUND -- reason]
  activist_sale:      [event_id or NOT FOUND -- reason]
  sale_press_release: [event_id or NOT FOUND -- reason]
  bid_press_release:  [event_id or NOT FOUND -- reason]

ADVISOR RETENTION:
  ib_retention:       [event_id(s) -- one per financial advisor]

NDAs:
  nda:                [count extracted vs count expected from census]

PROPOSALS:
  proposal:           [count extracted per actor]

DROPOUTS:
  drop/drop_*:        [event_id(s) or NOT FOUND per actor]

ROUND STRUCTURE (check pairs):
  final_round_inf_ann + final_round_inf:     [pair or NOT FOUND]
  final_round_ann     + final_round:         [pair or NOT FOUND]
  final_round_ext_ann + final_round_ext:     [pair or NOT FOUND]

EXECUTION:
  executed:           [event_id or NOT FOUND]

LIFECYCLE:
  terminated:         [event_id or NOT FOUND -- reason]
  restarted:          [event_id or NOT FOUND -- reason]
```

Any "NOT FOUND" that cannot be justified produces a `needs_review`
flag on the deal.

#### 2b. Targeted Re-Reads (max 5)

For each gap or count mismatch found in 2a, re-read the specific
chronology section most likely to contain it:

| Gap type | Where to re-read |
|----------|------------------|
| Missing process initiation | First 15% of chronology |
| NDA count mismatch | Sections near board meeting summaries |
| Missing dropouts | Between actor's last event and execution |
| Missing round events | Near "process letter" / "final round" language |
| Missing advisors | First appearances of known parties |
| Lifecycle gaps | Forward from each unresolved actor's last event |

**Limit: Max 5 targeted re-reads in 2b.**

#### 2c. Lifecycle Reconciliation

For each actor without a terminal status after 2b:
- Trace forward from their last event in the chronology.
- Look for implicit dropout signals: standstill agreement, not
  invited to next round, no further mention.
- **Found:** Record an inferred `drop` event with `raw_note`
  explaining the inference. Log an `implicit_dropout` decision to
  `decisions.jsonl`.
- **Not found:** Flag `needs_review` on the actor.

**Pass 2 effort limit:** Pass 2 should consume <= 30% of Pass 1
effort. Do not re-read the entire chronology.

### After Both Passes

9. **Assign terminal lifecycle status** to every actor:
   - `winner`: executed merger agreement
   - `dropped`: informed company of withdrawal
   - `dropped_by_target`: not invited to continue
   - `bid`: submitted proposal, still active at deal close
   - `stale`: from a terminated prior cycle
   - `advisor`: financial/legal advisor
   - `unresolved`: no terminal event -- deal flagged `needs_review`

10. **Verify lifecycle-event consistency:** Every actor with status
    `dropped`, `dropped_by_target`, or `winner` MUST have a
    corresponding event (`drop*` or `executed`). Missing event =
    record inferred event with `raw_note`, or flag `needs_review`.

11. **Write `extraction/deal.json`** with deal-level metadata and
    provenance. See `references/extraction-schemas.md` for the schema
    and provenance model.

12. **Write all output files:**
    - `extraction/events.jsonl`
    - `extraction/event_actor_links.jsonl`
    - `extraction/deal.json`
    - `extraction/actors_extended.jsonl` (if any new actors minted)
    - Append to `extraction/decisions.jsonl`

## Gate

At least 1 event in `extraction/events.jsonl`.

## Failure Mode

**Fail open.** Missing events, unresolved lifecycles, and count
mismatches produce `needs_review` flags but do not stop the pipeline.
Downstream skills (audit, enrichment, assembly) will propagate the
flags.

## Common Mistakes

1. **Classifying bids as formal/informal at extraction time.** Proposals
   are raw events. The `bid_type` field is assigned by Skill 8
   (classify-bids-and-boundary) AFTER round structure is identified.
   Do not add any formality classification during extraction.

2. **Fabricating or summarizing filing text.** Every `source_text`
   field must be a verbatim quote that can be found in the .txt file.
   Never paraphrase, combine sentences, or invent text. If you cannot
   find the exact words, read the .txt again.

3. **Using Alex's Excel / collection spreadsheet during extraction.**
   Alex's instructions define the methodology and taxonomy. The
   spreadsheet data is for post-hoc validation only (Skill 6). Never
   use it as a source of facts during extraction.

4. **Reading the entire filing in one context dump.** Read the
   chronology in 300-500 line chunks. The full filing is too large for
   a single context window and causes quality degradation.

5. **Counting partial-asset bidders as whole-company bidders.** Only
   collect bids to acquire the entire company. Bidders wanting a
   segment, division, or percentage stake are not recorded as proposal
   events. Log a `scope_exclusion` decision to `decisions.jsonl`.

6. **Skipping the taxonomy completeness sweep.** Pass 2a is MANDATORY
   and ALWAYS runs, even if Pass 1 appears to have found everything.
   Every taxonomy category must be checked.

7. **Recording round announcements without deadlines.** Round events
   come in mandatory announcement + deadline pairs. Every `*_ann`
   event MUST have a corresponding deadline event. Missing pair = go
   back to the filing and find it.

8. **Ignoring pre-existing advisors.** If the filing describes an
   advisor as "already retained" or "retained for routine
   preparedness", still record an `ib_retention` event using their
   first appearance date. The model needs every advisor.

9. **Missing implicit dropouts.** If an NDA signer has no subsequent
   events (no bid, no explicit dropout), they need either an inferred
   `drop` event with `raw_note`, or a `needs_review` flag. They
   cannot silently disappear.

10. **Assuming every Interested Party has an NDA event.** Not every
    party that expressed interest necessarily signed an NDA. Only
    record NDA events where the filing explicitly states a
    confidentiality agreement was signed.

11. **Converting total value to per-share without explicit share
    count.** If the filing states a bid in total value (e.g., "$8.7
    billion"), record it as `value_unit: "total"`. Only convert to
    per-share if the filing provides an explicit share count or
    per-share figure. Never compute per-share from an assumed share
    count.

## Decision Log (MANDATORY)

Every approximate_date, implicit_dropout, event_type_choice, and
scope_exclusion decision MUST be logged to `extraction/decisions.jsonl`.

See `references/extraction-schemas.md` for decision type definitions
and examples.

## Required Reading

1. `references/event-taxonomy.md` -- full 23-type taxonomy with filing
   signals, field requirements, and lifecycle closure rules
2. `references/extraction-schemas.md` -- events.jsonl, event_actor_links.jsonl,
   deal.json, provenance model, actors_extended.jsonl, decisions.jsonl
