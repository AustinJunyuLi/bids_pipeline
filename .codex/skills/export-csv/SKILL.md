# export-csv

## Design Principles

1. No analysis, no judgment. Pure formatting.
2. Match Alex Gorbenko's spreadsheet conventions exactly.
3. One event per row. One deal per file.

## Purpose

Flatten extraction + enrichment into Alex-compatible CSV for human review.

## When To Use

- Called by deal-agent after enrich-deal, or independently via
  `/export-csv <slug>`.
- Prerequisite: extract-deal and enrich-deal have already run for this deal.

## Reads

| File | What it provides |
|---|---|
| `data/skill/<slug>/extract/actors_raw.json` | Actor roster with roles, types, geography |
| `data/skill/<slug>/extract/events_raw.json` | Extracted events with dates, terms, evidence |
| `data/skill/<slug>/enrich/enrichment.json` | Dropout labels, bid classifications, round structure, review flags |
| `data/seeds.csv` | Deal metadata (target name, acquirer, date announced, URL) |

Note: export-csv does NOT read `verify/verification_log.json`. Verification
findings that need human attention are already captured in enrichment.json's
`review_flags` array.

## Output Columns

| Column | Source | Format |
|---|---|---|
| `bidderID` | Sequential assignment with fractional IDs for inserted events | Numeric (1, 1.5, 2, etc.) |
| `note` | Event type mapped to Alex's labels | See mapping table below |
| `bidder` | Actor `display_name` from actor roster | Text or `NA` |
| `type` | Bidder type code from actor fields | `S`, `F`, `non-US S`, `public F`, etc. or `NA` |
| `bid_type` | From enrichment `bid_classifications` | `Formal`, `Informal`, or `NA` |
| `val` | Proposal `per_share` value | Numeric or `NA` |
| `range` | Proposal `range_low` - `range_high` | `X-Y` or `NA` |
| `date_r` | Rough date | `YYYY-MM-DD 00:00:00` or `NA` |
| `date_p` | Precise date (same as rough when exact) | `YYYY-MM-DD 00:00:00` or `NA` |
| `cash` | All-cash indicator from `consideration_type` | `1` or `NA` |
| `c1` | Primary annotation | Free text or empty |
| `c2` | Deal terms / conditions | Free text or empty |
| `c3` | Always empty (matching Alex's practice) | Always empty |
| `review_flags` | Machine-readable uncertainty markers | Pipe-separated tags or empty |

Flags are per-event: each row gets only the flags whose tag contains that
event's `event_id`. A row for `evt_016` gets `dropout_needs_market_data:evt_016`
but not `bid_classification_uncertain:evt_022`.

## Event Type to Note Mapping

| event_type | note value | bidder populated? |
|---|---|---|
| `target_sale` | `Target Sale` | NA |
| `target_sale_public` | `Target Sale Public` | NA |
| `bidder_sale` | `Bidder Sale` | Bidder name |
| `bidder_interest` | `Bidder Interest` | Bidder name |
| `activist_sale` | `Activist Sale` | Activist name |
| `sale_press_release` | `Sale Press Release` | NA |
| `bid_press_release` | `Bid Press Release` | Bidder name |
| `ib_retention` | `IB` | IB name |
| `nda` | `NDA` | Bidder name |
| `proposal` | `NA` | Bidder name |
| `drop` (+ enrichment label) | `Drop` / `DropBelowM` / `DropBelowInf` / `DropAtInf` / `DropTarget` | Bidder name |
| `final_round_inf_ann` | `Final Round Inf Ann` | NA |
| `final_round_inf` | `Final Round Inf` | NA |
| `final_round_ann` | `Final Round Ann` | NA |
| `final_round` | `Final Round` | NA |
| `final_round_ext_ann` | `Final Round Ext Ann` | NA |
| `final_round_ext` | `Final Round Ext` | NA |
| `executed` | `Executed` | Bidder name |
| `terminated` | `Terminated` | NA |
| `restarted` | `Restarted` | Bidder name (if applicable) |

`proposal` maps to note value `NA`. This is Alex's convention for bid rows.
Bids are identified by having a value in `val` or `range`, not by the note
column. This `NA` is not the same as `NA` meaning "missing" in other columns.

For `drop` events: look up the event_id in enrichment.json
`dropout_classifications`. Use the enrichment label (`Drop`, `DropBelowM`,
`DropBelowInf`, `DropAtInf`, `DropTarget`) as the note value. If the event_id
has no enrichment classification, default to `Drop`.

## Bidder Type Mapping

Apply most-specific-first. Check in this priority order. First match wins.

| Priority | Actor fields | type value |
|---|---|---|
| 1 | `geography=non_us` + `listing_status=public` + `bidder_kind=strategic` | `non-US public S` |
| 2 | `geography=non_us` + `listing_status=public` + `bidder_kind=financial` | `non-US public F` |
| 3 | `geography=non_us` + `bidder_kind=strategic` | `non-US S` |
| 4 | `geography=non_us` + `bidder_kind=financial` | `non-US F` |
| 5 | `listing_status=public` + `bidder_kind=strategic` | `public S` |
| 6 | `listing_status=public` + `bidder_kind=financial` | `public F` |
| 7 | `bidder_kind=strategic` | `S` |
| 8 | `bidder_kind=financial` | `F` |
| 9 | `is_grouped=true` (unnamed aggregates) | `11S, 14F` style (from `group_size` + `group_label`) |
| 10 | Consortium (slash-separated, see below) | `S/F` style |
| 11 | Advisors, target board, non-bid events | `NA` |

## Consortium / Joint Bids

When two or more named parties submit a joint bid (common in PE consortiums):

- `bidder` column: slash-separated display names (e.g., `Party E/F`)
- `type` column: slash-separated types (e.g., `S/F`)
- One row per joint bid, not one row per consortium member
- Individual NDA rows still get separate rows per member

## Date Formatting

Three rules:

1. **Exact dates:** both `date_r` and `date_p` set to `YYYY-MM-DD 00:00:00`.
2. **Imprecise dates:** `date_r` set to approximation using these conventions:
   `early` = 5th, `mid` = 15th, `late` = 25th of the month. `date_p` set to
   `NA`.
3. **Unknown dates:** both `date_r` and `date_p` set to `NA`.

## Comment Column Conventions

**c1 (primary annotation):**

- IB rows: note the corresponding legal advisor if known, e.g.,
  `Legal advisor: Wachtell Lipton`. The IB itself is already in the bidder
  column; c1 captures the associated legal counsel, not the IB.
- Proposals: bid structure decomposition (e.g., `20.02 cash + 1.13 CVR`)
- Drops: reason text from filing
- Date ambiguity: rough date explanation
- Bidder characterization: industry, reengagement notes

**c2 (deal terms):**

- DD duration (`30 day DD`, `Confirmatory DD <=30 days`)
- Financing conditions (`No firm financing commitment`)
- Exclusivity terms (`Exclusivity 2 weeks`)
- Go-shop / covenants

**c3:** always empty.

## BidderID Assignment

5-step algorithm:

1. Sort all events chronologically by date (rough date as tiebreaker).
2. Within same-date events, sort by type priority: process markers first, then
   NDA, then proposal, then drop, then round events, then outcomes.
3. Events from the first NDA onward get integer IDs starting at 1.
4. Events that precede the first NDA (process initiation, IB retention, early
   bidder interest) get fractional IDs spaced evenly in (0, 1). For N pre-NDA
   events, assign IDs at increments of `1/(N+1)`, rounded to one decimal.

   Examples:
   - 1 pre-NDA event: 0.5
   - 2 pre-NDA events: 0.3, 0.7
   - 3 pre-NDA events: 0.3, 0.5, 0.7
   - 4 pre-NDA events: 0.2, 0.4, 0.6, 0.8

5. If enrichment inserts classification-derived events (e.g., a DropTarget that
   was not in the original extraction), assign a fractional ID at the midpoint
   between the surrounding events.

   Example: if the surrounding events have bidderIDs 5 and 6, the inserted
   event gets 5.5.

## Deal-Level Header

The CSV starts with a header block for the deal. Column names match Alex's
spreadsheet. Source field mapping from seeds.csv:

| seeds.csv field | CSV header column |
|---|---|
| `target_name` | `TargetName` |
| (computed event count) | `Events` |
| `acquirer` | `Acquirer` |
| `date_announced` | `DateAnnounced` |
| `primary_url` | `URL` |

Header row format:

```
TargetName | Events | Acquirer | DateAnnounced | URL
IMPRIVATA INC | 29 | THOMA BRAVO LLC | 2016-07-13 00:00:00 | https://...
```

Followed by the event rows with the 14-column schema defined above.

## Writes

- `data/skill/<slug>/export/deal_events.csv`

## Gate

Output file exists and is non-empty. At minimum: deal-level header + one event
row.
