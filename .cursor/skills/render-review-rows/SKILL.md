---
name: render-review-rows
description: Denormalizes extraction artifacts into Alex-style 47-column review rows and rebuilds global master views. Use after extraction and enrichment or when reviewer CSV outputs need to be regenerated.
---

# render-review-rows

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

Denormalize all extraction and enrichment artifacts into a 47-column review
CSV. Pure mechanical assembly -- no judgment, no classification, no
interpretation. If the input artifacts exist, this skill always succeeds.

## When To Use

- After Skills 1-8 have completed (orchestrated or independent).
- To rebuild `master_rows.csv` after manual overrides or re-extraction.
- To rebuild the global `Data/views/master.csv` after any deal changes.

## Input Artifacts

All paths relative to `Data/deals/<slug>/`:

| Artifact | Source Skill |
|----------|-------------|
| `extraction/deal.json` | 5. extract-events |
| `extraction/actors.jsonl` | 4. build-party-register |
| `extraction/actors_extended.jsonl` | 5. extract-events (if new actors minted) |
| `extraction/events.jsonl` | 5. extract-events |
| `extraction/event_actor_links.jsonl` | 5. extract-events |
| `enrichment/process_cycles.jsonl` | 7. segment-processes |
| `enrichment/judgments.jsonl` | 8. classify-bids-and-boundary |
| `extraction/audit_flags.json` | 6. audit-and-reconcile (optional) |

## Output Artifacts

| Artifact | Description |
|----------|-------------|
| `master_rows.csv` | 47-column review CSV (one row per event-actor link) |
| `review/review_status.json` | Review status and flags for this deal |
| `review/overrides.csv` | Header-only CSV for reviewer corrections |
| `Data/views/master.csv` | Global rebuild: all `Data/deals/*/master_rows.csv` concatenated |

## Tools

| Tool | Purpose |
|------|---------|
| File read | Read all input artifacts from disk |
| File write | Write master_rows.csv, review_status.json, overrides.csv |
| File search | Find all `Data/deals/*/master_rows.csv` for global rebuild |

## Procedure

```
1. Read deal.json -> extract Group A (deal header) fields.
2. Read actors.jsonl + actors_extended.jsonl (if exists) -> build actor lookup.
3. Read events.jsonl -> build event list.
4. Read event_actor_links.jsonl -> build link list.
5. Read process_cycles.jsonl -> build cycle/round lookup.
6. Read judgments.jsonl -> build classification lookup.
7. Read audit_flags.json (if exists) -> build review flag inputs.

8. For each event:
   a. Look up event-actor links for this event.
   b. If links exist: emit one row per link (event + actor columns).
   c. If no links: emit one row with blank actor columns.
   d. Populate all 47 columns per the column spec.
   e. Derive bid_note from event_type using the mapping table.
   f. Derive review flags (approximate_date, missing_nda, etc.).

9. Sort rows: deal_slug -> event_date -> event_type priority -> actor_alias.
10. Write master_rows.csv with header + sorted rows.
11. Write review/review_status.json with status, flags, extraction date.
12. Write review/overrides.csv (header only).
13. Rebuild global Data/views/master.csv:
    - Find all Data/deals/*/master_rows.csv files.
    - Validate headers are consistent across all deals.
    - Concatenate all rows sorted by deal_slug.
    - Write to Data/views/master.csv.
```

## Gate

`master_rows.csv` exists in `Data/deals/<slug>/`.

## Failure Policy

**Always succeeds** if input artifacts exist. This is pure denormalization --
no judgment calls, no ambiguity. If an input artifact is missing, skip its
columns (leave blank) and note in review_status.json.

## Required Reading

1. `references/column-spec.md` -- 47-column specification, sorting rules,
   bid_note mapping, review flag derivation, global master.csv rebuild
