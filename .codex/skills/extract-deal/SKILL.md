---
name: extract-deal
description: Use when extracting skill-workflow actor and event artifacts from preprocessed SEC filing source for a specific deal.
---

# extract-deal

## Design Principles

1. The filing is the single source of truth. Every fact traces to
   `source_accession_number` + verbatim `source_text`.
2. Fail closed on source ambiguity. Fail open on extraction incompleteness.
3. Facts before judgments. Extract observable text features only.
4. Evidence items are anchors, not constraints. Use them to guide rereads, not
   to replace reading the chronology.

## Purpose

Chunked sequential LLM extraction of actors and events from preprocessed SEC
filing source, followed by a consolidation pass that preserves the existing
output schema. The skill defines its own JSON format as specified below.

## When To Use

- Called by the deal-agent orchestrator, or independently via
  `/extract-deal <slug>`.
- Prerequisite: `skill-pipeline raw-fetch` +
  `skill-pipeline preprocess-source` already ran.

## Benchmark Boundary

Benchmark materials are forbidden during generation. Do not consult benchmark
files, benchmark notes, `example/`, `diagnosis/`,
`data/skill/<slug>/reconcile/*`, or `/reconcile-alex` before `/export-csv`
completes.

Use only filing-grounded source artifacts during extraction. Benchmark
comparison is post-export only and read-only.

## Reads

| File | What it provides |
|---|---|
| `data/deals/<slug>/source/chronology_selection.json` | Selected filing and section |
| `data/deals/<slug>/source/chronology_blocks.jsonl` | Chronology narrative blocks |
| `data/deals/<slug>/source/evidence_items.jsonl` | Pre-tagged anchors for dates, actors, values, and process signals |
| `raw/<slug>/document_registry.json` | Filing metadata and paths |
| `raw/<slug>/filings/*.txt` | Frozen text for verbatim anchors |

## Extraction Method

### Chunk Construction

Split `chronology_blocks.jsonl` into sequential chunks of roughly 10-12 blocks
per chunk, targeting about 3-4K tokens each. Follow these chunking rules:

- Every block appears in exactly one primary chunk.
- Adjacent chunks share 1-2 blocks of overlap to catch boundary-spanning
  events.
- Heading blocks (`is_heading=true`) are never chunk boundaries. Keep the
  heading with the following narrative block.
- Number chunks sequentially as `chunk_1`, `chunk_2`, ..., `chunk_N`.

For each chunk, scope evidence from `evidence_items.jsonl` to only the items
whose `start_line`..`end_line` range intersects that chunk's block range.

### Chunk Extraction (Sequential)

Process chunks in order: `chunk_1` first, then `chunk_2`, and so on. Each chunk
receives:

1. Its block window rendered as numbered text
2. Scoped evidence items for that window only
3. The running actor roster from prior chunks (empty for `chunk_1`)

Each chunk extracts actors and events together. For every chunk:

- Extract every actor visible in the chunk's blocks, including named bidders,
  advisors, activists, target-side entities, filing aliases such as `Party A`,
  and unnamed aggregates when the filing counts them but does not individualize
  them.
- If a chunk identifies a party that is not already present on the running
  roster, mint a new actor with a new `actor_id` plus `evidence_refs` grounded
  in this chunk.
- For advisors, set `advised_actor_id` when the filing identifies the client.
  Example: if the text says "Wachtell, Lipton, Rosen & Katz, counsel to the
  Company", set `advised_actor_id` to the target-side actor. If unclear, set
  `null`.
- Extract `count_assertions` for explicit numeric statements such as "15
  parties signed confidentiality agreements" or "7 bidders were invited to the
  final round."
- Extract all events visible in the chunk's blocks across the 20-type taxonomy
  below.

Chunk-level event rules:

For each event, include:
- Assign temporary per-chunk `event_id` values such as `c1_evt_001` or
  `c2_evt_003`. Consolidation replaces them with global IDs later.
- `event_type`
- `date`
- `actor_ids`
- `summary`
- `evidence_refs` with verbatim `anchor_text`
- Proposal events must include `terms`, `consideration_type`, and
  `formality_signals`.
- Add `formality_signals.is_subject_to_financing`:
  - `true` when the proposal is explicitly subject to financing
  - `false` when the text explicitly says financing is committed, available, or
    not a condition
  - `null` when financing is not discussed
- Round events must include `round_scope`. For announcement events, also fill
  `invited_actor_ids` when the filing names or clearly identifies the invitees.
- Collapse every withdrawal or exclusion into `drop`. Do not emit
  `drop_below_m`, `drop_below_inf`, `drop_at_inf`, or `drop_target`.
  Preserve the narrative basis in `drop_reason_text`, including whether the
  withdrawal was bidder-initiated or target-initiated when the text makes that
  clear.
- For `executed`, fill `executed_with_actor_id` when the counterparty is known.
- For `terminated` and `restarted`, fill `boundary_note`.
- Do not set the final-round temporal flags during chunk extraction. Those
  signals require cross-chunk history and are set only during consolidation.

Events with genuinely unknown dates: set `date.raw_text` and
`date.normalized_hint` both to null. The event is still extracted.

roster carry-forward is mandatory. After each chunk completes, merge its newly
minted actors into the running roster before prompting the next chunk.

Write each chunk's structured draft to
`data/skill/<slug>/extract/chunks/` as a transient debug artifact. These files
support operator review only and are not consumed by deterministic stages.

### Date and Event Precision Rules

**Date precision:** When the filing gives a specific date for an individual
party's action (e.g., "including Thoma Bravo on May 10, 2016"), use that exact
date. Do not substitute the date range of a broader period (e.g., "May 6
through June 9") when an individual date is explicitly stated. When the filing
says a letter was "received on date X" but "dated date Y," use date Y (the
authoring/sending date).

**Event granularity:** One action = one event. A board committee discussing a
received bid is not a separate proposal event. A board confirming a prior
decision is not a separate event. Only create an event when there is a new
external action (bid submitted, NDA signed, party drops out) or a new board
decision (launch sale process, advance to final round).

**Terminated semantics:** Use `terminated` only when the deal process itself
ends (sale process abandoned, no transaction). A party terminating a hostile
tactic (consent solicitation, proxy fight) as a condition of joining the
friendly process is NOT a `terminated` event. Note it in the NDA event's
`notes` field instead.

### Consolidation Pass

After all chunks finish, run one consolidation pass. It receives:

1. The final accumulated actor roster
2. All chunk event drafts from every chunk
3. All merged `count_assertions`
4. Evidence gap signals for block ranges that still have no extracted events, if
   any

The consolidation pass performs these actions:

1. Actor dedup by canonical name. Group actors by
   `(canonical_name.strip().upper(), role, bidder_kind)`. Keep the survivor
   with the richest evidence, merge duplicate `evidence_refs` into the
   survivor, and log the merge decisions in the transient working notes.
2. Event dedup for overlap zones. When adjacent chunks both extract the same
   overlap event, dedup by `(event_type, date, actor_ids)`, keep the richer
   summary, and merge `evidence_refs`.
3. 20-type taxonomy sweep. For every event type, either confirm the extracted
   events or write `NOT FOUND -- [specific filing-based reason]` in
   `coverage_notes`.
4. Count reconciliation. Compare `count_assertions` against the extracted
   actor/event roster and flag mismatches for downstream review.
5. Targeted re-reads. For event types still marked `NOT FOUND`, re-read the
   3-5 most relevant blocks for that type and extract any missing events.
6. Temporal signal assignment. Set
   `after_final_round_announcement` and `after_final_round_deadline` on
   proposal events only after scanning the consolidated event timeline for the
   relevant prior round events.
7. Global event ID assignment. Replace temporary chunk event IDs with stable
   global IDs (`evt_001`, `evt_002`, ...) in chronological order and update any
   dependent references such as `invited_actor_ids`.

### Output

Consolidation writes the final `actors_raw.json` and `events_raw.json` to
`data/skill/<slug>/extract/`. These use the same schema and artifact paths as
today. Do not change downstream contracts, Pydantic models, or deterministic
stage expectations.

## Writes

### `data/skill/<slug>/extract/actors_raw.json`

### `data/skill/<slug>/extract/events_raw.json`

The skill defines its own JSON format as specified below.

`coverage_notes` must be a list of strings. It must explicitly record the
taxonomy sweep, for example:

```json
"coverage_notes": [
  "target_sale: extracted (evt_001)",
  "activist_sale: NOT FOUND -- no activist involvement in this deal"
]
```

### Evidence Ref Schema

Every evidence_ref in both actors and events uses this shape:

```json
{
  "block_id": "B042",
  "evidence_id": "0001193125-16-677939:E0012",
  "anchor_text": "representatives of Thoma Bravo informally approached"
}
```

- `block_id`: references a block in chronology_blocks.jsonl. Required for
  chronology evidence.
- `evidence_id`: references an item in evidence_items.jsonl. Required for
  appendix/cross-filing evidence.
- At least one of `block_id` or `evidence_id` must be present.
- `anchor_text`: verbatim substring from the filing. Always required.

### Actor Record Fields

Each actor in the `actors` array:

| Field | Type | Required | Notes |
|---|---|---|---|
| `actor_id` | string | yes | Stable ID (e.g., `bidder_thoma_bravo`) |
| `display_name` | string | yes | Human-readable name |
| `canonical_name` | string | yes | Uppercase legal name |
| `aliases` | list[string] | no | Filing aliases (Party A, etc.) |
| `role` | string | yes | `bidder`, `advisor`, `activist`, `target_board` |
| `advisor_kind` | string or null | no | `financial`, `legal`, `other` (advisors only) |
| `advised_actor_id` | string or null | no | Actor ID of client (advisors only) |
| `bidder_kind` | string or null | no | `strategic`, `financial` (bidders only) |
| `listing_status` | string or null | no | `public`, `private` |
| `geography` | string or null | no | `domestic`, `non_us` |
| `is_grouped` | boolean | yes | True for unnamed aggregates |
| `group_size` | integer or null | no | Required when is_grouped=true |
| `group_label` | string or null | no | Required when is_grouped=true |
| `evidence_refs` | list[evidence_ref] | yes | At least one |
| `notes` | list[string] | no | |

### Event Record Fields

Each event in the `events` array:

| Field | Type | Required | Notes |
|---|---|---|---|
| `event_id` | string | yes | Stable ID (e.g., `evt_001`) assigned at extraction time |
| `event_type` | string | yes | One of 20 taxonomy types |
| `date` | object | yes | `{raw_text, normalized_hint}`. Both may be null for genuinely undated events. |
| `actor_ids` | list[string] | yes | May be empty for process-level events (round announcements, etc.) |
| `summary` | string | yes | One-sentence description |
| `evidence_refs` | list[evidence_ref] | yes | At least one |
| `terms` | object or null | proposal only | `{per_share, range_low, range_high, enterprise_value, consideration_type}` |
| `formality_signals` | object or null | proposal only | 11 boolean flags (see Reference: Formality Signals below) |
| `whole_company_scope` | boolean or null | proposal only | See note below |
| `drop_reason_text` | string or null | drop only | Verbatim filing language |
| `round_scope` | string or null | round only | `formal` or `informal` |
| `invited_actor_ids` | list[string] | round only | When identifiable from filing |
| `deadline_date` | object or null | round only | Same shape as `date` |
| `executed_with_actor_id` | string or null | executed only | Counterparty |
| `boundary_note` | string or null | terminated/restarted only | Filing context |
| `nda_signed` | boolean or null | nda only | |
| `notes` | list[string] | no | |

`whole_company_scope`: set to true for whole-company bids, false for partial-
company bids. When ambiguous, set to null and include the event (do not exclude
on ambiguity). Partial-company bids with `whole_company_scope=false` go into
`exclusions`, not `events`.

### Top-Level Structures

```json
// actors_raw.json
{
  "actors": [ <actor records> ],
  "count_assertions": [
    {
      "subject": "confidentiality agreements",
      "count": 15,
      "evidence_refs": [ <evidence refs> ]
    }
  ],
  "unresolved_mentions": [ <strings> ]
}

// events_raw.json
{
  "events": [ <event records> ],
  "exclusions": [
    {
      "category": "partial_company_bid",
      "block_ids": ["B015"],
      "explanation": "Party X only interested in acquiring the software division"
    }
  ],
  "coverage_notes": [
    "target_sale: extracted (evt_001)",
    "activist_sale: NOT FOUND -- no activist involvement in this deal"
  ]
}
```

## Gate

Both files exist. `actors` has at least one entry. `events` has at least one
entry. Fail closed if the gate fails.

---

## Reference: Event Taxonomy (20 types)

### Process Markers (8 types)

| Type | Filing Signal |
|---|---|
| `target_sale` | Board authorizes strategic alternatives exploration |
| `target_sale_public` | Public announcement of strategic review |
| `bidder_sale` | Acquirer-initiated process |
| `bidder_interest` | Unsolicited expression of interest without a bid |
| `activist_sale` | Activist pressure triggers a sale review |
| `sale_press_release` | Press release announcing strategic alternatives |
| `bid_press_release` | Press release announcing a deal or public bid |
| `ib_retention` | Investment bank or other adviser retained |

### Deal Mechanics (3 types)

| Type | Filing Signal |
|---|---|
| `nda` | Confidentiality agreement signed |
| `proposal` | Whole-company priced bid or indication of interest |
| `drop` | Bidder withdraws or target excludes bidder from continuing |

### Auction Stages (6 types)

| Type | Filing Signal |
|---|---|
| `final_round_inf_ann` | Informal final round announced |
| `final_round_inf` | Informal final round deadline |
| `final_round_ann` | Formal final round announced |
| `final_round` | Formal final round deadline |
| `final_round_ext_ann` | Extension round announced |
| `final_round_ext` | Extension round deadline |

### Outcomes (3 types)

| Type | Filing Signal |
|---|---|
| `executed` | Merger agreement signed |
| `terminated` | Sale process terminated |
| `restarted` | Sale process restarted |

## Reference: Formality Signals

Every proposal must include:

```json
{
  "contains_range": false,
  "mentions_indication_of_interest": false,
  "mentions_preliminary": false,
  "mentions_non_binding": false,
  "mentions_binding_offer": true,
  "includes_draft_merger_agreement": true,
  "includes_marked_up_agreement": false,
  "requested_binding_offer_via_process_letter": false,
  "after_final_round_announcement": true,
  "after_final_round_deadline": false,
  "is_subject_to_financing": null
}
```

These are observable text features, not classifications.

## Reference: Exclusions

Record deliberate exclusions with category and explanation:

- `partial_company_bid`
- `unsigned_nda`
- `stale_process_reference`
- `duplicate_mention`
- `non_event_context`
- `other`

## Supersedes

This skill replaces the old `audit-and-enrich` skill's extraction
responsibilities. Its QA and enrichment responsibilities are now handled by
verify-extraction (Skill 2) and enrich-deal (Skill 3).
