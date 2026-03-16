# Column Specification for master_rows.csv

47 columns across 8 groups. One row per event-actor link. Actorless events
(round announcements, process events) get one row with blank actor columns.

## Group A: Deal Header (cols 1-10)

Repeats on every row. Identifies which deal.

| # | Column | Type | Source |
|---|--------|------|--------|
| 1 | `deal_slug` | string | deal.json |
| 2 | `target_name` | string | deal.json |
| 3 | `cik` | string | deal.json |
| 4 | `winning_acquirer` | string | deal.json (actor alias of winner) |
| 5 | `deal_outcome` | string | deal.json (`completed` / `terminated` / `withdrawn`) |
| 6 | `consideration_type` | string | deal.json (`all_cash` / `stock` / `mixed`) |
| 7 | `DateAnnounced` | date | deal.json `date_announced` |
| 8 | `DateEffective` | date | deal.json `date_effective` (null for terminated) |
| 9 | `filing_type` | string | deal.json |
| 10 | `URL` | string | deal.json `filing_url` |

## Group B: Row Identity (cols 11-15)

| # | Column | Type | Source |
|---|--------|------|--------|
| 11 | `row_seq` | int | Generated (1, 2, 3... per deal, chronological after sorting) |
| 12 | `event_id` | string | events.jsonl |
| 13 | `event_type` | string | events.jsonl (machine-readable taxonomy name) |
| 14 | `bid_note` | string | Derived from event_type (see mapping table below). Blank for proposal rows. |
| 15 | `cycle_id` | string | process_cycles.jsonl (which cycle this event belongs to) |

## Group C: Actor (cols 16-22)

| # | Column | Type | Source |
|---|--------|------|--------|
| 16 | `actor_id` | string | event_actor_links.jsonl |
| 17 | `BidderName` | string | actors.jsonl `actor_alias` |
| 18 | `actor_type` | string | actors.jsonl (`bidder` / `advisor` / `activist` / `target_board`) |
| 19 | `bidder_subtype` | string | actors.jsonl (`financial` / `strategic` / `non_us` / `mixed`) |
| 20 | `lifecycle_status` | string | actors.jsonl (`bid` / `dropped` / `dropped_by_target` / `winner` / `stale` / `advisor` / `unresolved`) |
| 21 | `participation_role` | string | event_actor_links.jsonl (`bidder` / `advisor` / `counterparty` / `decision_maker` / `initiator`) |
| 22 | `actor_notes` | string | actors.jsonl |

## Group D: Dates (cols 23-25)

| # | Column | Type | Source |
|---|--------|------|--------|
| 23 | `event_date` | date | events.jsonl `date` (YYYY-MM-DD, always populated) |
| 24 | `date_precision` | string | events.jsonl (`exact` / `approximate` / `month_only`) |
| 25 | `round_id` | string | process_cycles.jsonl (which round this event belongs to, if any) |

## Group E: Bid Values (cols 26-31)

Only populated on proposal rows.

| # | Column | Type | Source |
|---|--------|------|--------|
| 26 | `bid_value_pershare` | float | events.jsonl `value` (midpoint for ranges) |
| 27 | `bid_value_lower` | float | events.jsonl `value_lower` |
| 28 | `bid_value_upper` | float | events.jsonl `value_upper` |
| 29 | `all_cash` | int | Derived: 1 if event consideration is `cash`, blank otherwise |
| 30 | `event_consideration_type` | string | events.jsonl (`cash` / `stock` / `mixed` / `cash_plus_cvr`) |
| 31 | `cshoc` | float | `Data/reference/compustat_linkage.csv` (nullable, external) |

## Group F: Classification & Judgments (cols 32-36)

| # | Column | Type | Source |
|---|--------|------|--------|
| 32 | `bid_type` | string | judgments.jsonl (`Informal` / `Formal` / blank for non-proposals) |
| 33 | `bid_classification_rule` | string | judgments.jsonl (e.g., `post_final_round_announcement`) |
| 34 | `bid_classification_confidence` | string | judgments.jsonl (`high` / `medium` / `low`) |
| 35 | `initiation` | string | judgments.jsonl (`target_driven` / `bidder_driven` / `activist_driven` / `mixed`). Repeats per deal. |
| 36 | `formal_boundary_event` | string | judgments.jsonl (event_id of informal-to-formal transition). Repeats per deal. |

## Group G: Evidence & Notes (cols 37-40)

| # | Column | Type | Source |
|---|--------|------|--------|
| 37 | `source_text_short` | string | events.jsonl `source_text` truncated to ~120 chars + `"..."` |
| 38 | `raw_note` | string | events.jsonl |
| 39 | `deal_notes` | string | deal.json (repeats per deal) |
| 40 | `reviewer_note` | string | Generated: per-row explanation of review flags (blank if no flags) |

## Group H: Review Machinery (cols 41-47)

| # | Column | Type | Source |
|---|--------|------|--------|
| 41 | `needs_review` | bool | review_status.json (true if any flag is set for the deal) |
| 42 | `flag_approximate_date` | bool | Derived: true if `date_precision != "exact"` |
| 43 | `flag_missing_nda` | bool | Derived: true if actor is bidder with no NDA event |
| 44 | `flag_unresolved_lifecycle` | bool | Derived: true if `lifecycle_status == "unresolved"` |
| 45 | `flag_anonymous_mapping` | bool | Derived: true if actor cannot be mapped to named entity |
| 46 | `comments_1` | string | Empty (reviewer workspace) |
| 47 | `comments_2` | string | Empty (reviewer workspace) |

---

## bid_note Mapping Table

The `bid_note` column maps machine-readable `event_type` values to
human-readable labels matching Alex's collection format. Proposal rows
have blank `bid_note` (their value is in the bid columns instead).

| event_type | bid_note |
|------------|----------|
| `proposal` | *(blank)* |
| `nda` | NDA |
| `drop` | Drop |
| `drop_below_m` | DropBelowM |
| `drop_below_inf` | DropBelowInf |
| `drop_at_inf` | DropAtInf |
| `drop_target` | DropTarget |
| `ib_retention` | IB |
| `executed` | Executed |
| `terminated` | Terminated |
| `restarted` | Restarted |
| `final_round_inf_ann` | Final Round Inf Ann |
| `final_round_inf` | Final Round Inf |
| `final_round_ann` | Final Round Ann |
| `final_round` | Final Round |
| `final_round_ext_ann` | Final Round Ext Ann |
| `final_round_ext` | Final Round Ext |
| `activist_sale` | Activist Sale |
| `bidder_sale` | Bidder Sale |
| `bidder_interest` | Bidder Interest |
| `target_sale` | Target Sale |
| `target_sale_public` | Target Sale Public |
| `sale_press_release` | Sale Press Release |
| `bid_press_release` | Bid Press Release |

23 event types total.

---

## Sorting Rules

Rows are sorted in the following priority order:

1. **`deal_slug`** -- alphabetical (only matters for global master.csv)
2. **`event_date`** -- chronological (earliest first)
3. **`event_type` priority** -- process events before actor events on the
   same date. Priority order:
   - Process initiation (`target_sale`, `target_sale_public`, `bidder_sale`,
     `bidder_interest`, `activist_sale`, `sale_press_release`,
     `bid_press_release`)
   - Advisor retention (`ib_retention`)
   - Round structure (`final_round_*_ann`, `final_round_*`)
   - NDAs (`nda`)
   - Proposals (`proposal`)
   - Dropouts (`drop`, `drop_*`)
   - Execution (`executed`, `terminated`, `restarted`)
4. **`actor_alias`** -- alphabetical within same event

After sorting, assign `row_seq` as 1, 2, 3... per deal.

---

## Review Flag Derivation Rules

Each flag is independently computed per row:

| Flag | Condition | reviewer_note text |
|------|-----------|-------------------|
| `flag_approximate_date` | `date_precision` is `approximate` or `month_only` | `"Date is {date_precision}"` |
| `flag_missing_nda` | Actor has `actor_type == "bidder"` AND no `nda` event exists for this `actor_id` anywhere in `event_actor_links.jsonl` | `"Bidder has no NDA event"` |
| `flag_unresolved_lifecycle` | Actor has `lifecycle_status == "unresolved"` | `"Actor lifecycle unresolved"` |
| `flag_anonymous_mapping` | Actor `actor_alias` starts with `"Unnamed"` or `"unnamed"` or actor_id contains `/unnamed_` | `"Anonymous actor, cannot map to named entity"` |

**Deal-level `needs_review`:** Set to `true` on EVERY row of the deal if
ANY row in the deal has ANY flag set to `true`, or if `audit_flags.json`
contains any unresolved issues.

**`reviewer_note`:** Concatenate all applicable flag descriptions with
`"; "` separator. Blank if no flags are set on this row.

---

## review_status.json Schema

Written to `review/review_status.json` for each deal.

```json
{
  "status": "needs_review",
  "flags": ["approximate_date", "unresolved_lifecycle"],
  "last_extraction_date": "2026-03-15",
  "reviewer": null,
  "review_date": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `"needs_review"` if any flags exist, `"pending_review"` otherwise |
| `flags` | array | List of flag names that are set for this deal |
| `last_extraction_date` | string | YYYY-MM-DD of when assembly ran |
| `reviewer` | string | null (filled by reviewer) |
| `review_date` | string | null (filled by reviewer) |

---

## overrides.csv Schema

Written to `review/overrides.csv` as header-only (no data rows). Reviewers
add corrections here during review.

| Column | Description |
|--------|-------------|
| `override_id` | Unique ID |
| `target_type` | `actor` / `event` / `judgment` |
| `target_id` | ID of the corrected object |
| `field` | Which field is corrected |
| `original_value` | What the extraction produced |
| `corrected_value` | What the reviewer determined |
| `reviewer` | Who made the correction |
| `date` | When corrected (YYYY-MM-DD) |
| `basis` | Why corrected |

---

## Global master.csv Rebuild

After writing the per-deal `master_rows.csv`, rebuild the shared
`Data/views/master.csv` by concatenating all deal-local slices.

### Procedure

1. Find all `Data/deals/*/master_rows.csv` to find all deal slices.
2. Read the header row from the first file.
3. For each subsequent file, verify its header matches. If headers are
   inconsistent, raise an error and stop (do not produce a corrupt master).
4. Concatenate all data rows (excluding duplicate headers).
5. Sort by `deal_slug` (alphabetical), preserving intra-deal row order.
6. Write to `Data/views/master.csv`.

The global master.csv uses the same 47-column schema as each per-deal
`master_rows.csv`. It is the single review surface across all deals.
