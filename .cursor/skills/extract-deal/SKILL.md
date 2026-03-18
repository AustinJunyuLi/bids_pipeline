# extract-deal

## Design Principles

1. The filing is the single source of truth. Every fact traces to
   `source_accession_number` + verbatim `source_text`.
2. Fail closed on source ambiguity. Fail open on extraction incompleteness.
3. Facts before judgments. Extract observable text features only.
4. Evidence items are anchors, not constraints. Use them to guide rereads, not
   to replace reading the chronology.

## Purpose

Two-pass LLM extraction of actors and events from preprocessed SEC filing
source. The skill defines its own JSON format as specified below.

## When To Use

- Called by the deal-agent orchestrator, or independently via
  `/extract-deal <slug>`.
- Prerequisite: `pipeline raw fetch` + `pipeline preprocess source` already ran.

## Reads

| File | What it provides |
|---|---|
| `data/deals/<slug>/source/chronology_selection.json` | Selected filing and section |
| `data/deals/<slug>/source/chronology_blocks.jsonl` | Chronology narrative blocks |
| `data/deals/<slug>/source/evidence_items.jsonl` | Pre-tagged anchors for dates, actors, values, and process signals |
| `data/deals/<slug>/source/supplementary_snippets.jsonl` | Cross-filing hints from non-primary filings |
| `raw/<slug>/document_registry.json` | Filing metadata and paths |
| `raw/<slug>/filings/*.txt` | Frozen text for verbatim anchors |

## Extraction Method

### Pass 1 — Forward Scan

#### Step 1a: Actor Extraction

Extract every party mentioned in the chronology:

- Named bidders, advisors, activists, and target-side entities
- Filing aliases such as `Party A`
- Unnamed aggregates when the filing counts them but does not individualize them

For each actor, produce a `RawActorRecord` with the standard roster fields plus:

- `advised_actor_id`: for advisors only, link the advisor to the actor it
  represents when the filing says so. Example: if the text says "Wachtell,
  Lipton, Rosen & Katz, counsel to the Company", set `advised_actor_id` to the
  target-side actor. If unclear, set `null`.

Also extract `count_assertions` for explicit numeric statements such as:

- "15 parties signed confidentiality agreements"
- "7 bidders were invited to the final round"

#### Step 1b: Event Extraction

Every event must have a stable `event_id` (e.g., `evt_001`, `evt_002`)
assigned at extraction time. IDs must not change once assigned. Downstream
skills reference events by event_id.

Extract all events across the 20-type taxonomy below. Every event needs:

- `event_id`
- `event_type`
- `date`
- `actor_ids`
- `summary`
- `evidence_refs` with verbatim `anchor_text`

Events with genuinely unknown dates: set `date.raw_text` and
`date.normalized_hint` both to null. The event is still extracted.

Additional event rules:

- Proposal events must include `terms`, `consideration_type`, and
  `formality_signals`.
- Add `formality_signals.is_subject_to_financing`:
  - `true` when the proposal is explicitly subject to financing
  - `false` when the text explicitly says financing is committed, available, or
    not a condition
  - `null` when financing is not discussed
- Only set `after_final_round_announcement=true` if you have already extracted
  a chronologically earlier `final_round_ann` or `final_round_ext_ann`.
- Round events must include `round_scope`. For announcement events, also fill
  `invited_actor_ids` when the filing names or clearly identifies the invitees.
- Collapse every withdrawal or exclusion into `drop`. Do not emit
  `drop_below_m`, `drop_below_inf`, `drop_at_inf`, or `drop_target`.
  Preserve the narrative basis in `drop_reason_text`, including whether the
  withdrawal was bidder-initiated or target-initiated when the text makes that
  clear.
- For `executed`, fill `executed_with_actor_id` when the counterparty is known.
- For `terminated` and `restarted`, fill `boundary_note`.

Open-world actor minting is allowed. If an event clearly references a party not
yet on the roster, add that actor with evidence. When minting new actors during
event extraction, add a corresponding actor record to actors_raw.json with
evidence_refs.

### Pass 2 — Gap Re-Read (Always Runs)

1. For each of the 20 event types, list extracted events or write
   `NOT FOUND — [specific filing-based reason]`.
2. Re-read the most relevant sections for missing NDA, dropout, adviser, and
   process-initiation events.
3. Re-check actor lifecycle coverage. If an actor disappears from the process,
   record that in `coverage_notes` even if the terminal event remains unresolved.

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
