---
name: reconcile-alex
description: Use when a deal has completed the skill-native pipeline and you need benchmark reconciliation against Alex's spreadsheet, especially for row mismatches, aggregate spreadsheet rows, or disagreements that require filing-text arbitration.
---

# reconcile-alex

## Design Principles

1. This is an agent skill. YOU read both data sources and the raw filing, then reason about matches, disagreements, and filing evidence. No Python comparison code exists.
2. This is a secondary benchmark-validation skill, not the primary truth gate. `check`, `verify`, and `/verify-extraction` own pipeline grounding first.
3. Neither source is authoritative. The raw filing text is the tiebreaker.
4. Stay inside the current skill-native pipeline. Do not assume a deleted canonical-model layer exists.
5. Fail closed on missing prerequisites. When a comparison is unsupported, skip it explicitly and record why instead of guessing.

## Purpose

Post-pipeline validation that compares the current skill-native pipeline outputs against Alex's hand-coded spreadsheet, then arbitrates disagreements and orphan events against the actual SEC filing text.

The point is not to make Alex authoritative. The point is to measure benchmark agreement, explain disagreements, and distinguish true filing-grounded pipeline problems from harmless granularity or formatting mismatches.

## When To Use

Invoke as `/reconcile-alex <slug>` only after the full pipeline has completed for a deal (through export).

Benchmark materials are forbidden during generation. This skill is post-export
only and must not be used to steer extraction, verification, enrichment, or
export while a deal is still being generated.

Use this skill when:
- the pipeline is already filing-grounded, but you want benchmark QA against Alex
- the benchmark and pipeline disagree on row counts, bid labels, or event timing
- Alex has aggregate rows such as "Several parties" or "24 parties"
- same-day auction clusters make naive matching unreliable

Do not use this skill as a substitute for `check`, `verify`, or `/verify-extraction`.

## Cross-Machine Handoff

- This is a read-only QA skill. It must not rewrite generation artifacts.
- If a prior session consulted benchmark materials before `/export-csv` and then
  generated `data/skill/<slug>/...` artifacts, treat those artifacts as tainted
  for blind evaluation.
- A fresh agent on another machine should not continue generation from those
  tainted artifacts. Regenerate from the filing-grounded workflow, complete
  `/export-csv`, and only then run `/reconcile-alex <slug>`.

## Prerequisites

Before starting, confirm ALL of these exist:

- `data/skill/<slug>/extract/actors_raw.json`
- `data/skill/<slug>/extract/events_raw.json`
- `data/skill/<slug>/extract/spans.json`
- `data/skill/<slug>/export/deal_events.csv`
- At least one of:
  - `data/skill/<slug>/enrich/enrichment.json`
  - `data/skill/<slug>/enrich/deterministic_enrichment.json`
- `data/deals/<slug>/source/chronology_blocks.jsonl`
- `raw/<slug>/document_registry.json`
- `raw/<slug>/filings/*.txt`
- `example/deal_details_Alex_2026.xlsx`

If any are missing, stop and tell the user what is missing.

## Procedure

### Step 1: Extract Alex's rows for this deal

The xlsx file is binary; use Python to extract. Run:

```bash
python3 -c "
import json, sys
from openpyxl import load_workbook
from datetime import datetime

slug = sys.argv[1]

import csv
with open('data/seeds.csv') as f:
    for row in csv.DictReader(f):
        if row['deal_slug'] == slug:
            target_name = row['target_name']
            break
    else:
        print(json.dumps({'error': f'slug {slug} not found in seeds.csv'}))
        sys.exit(1)

import re
def _normalize_company(name):
    n = re.sub(r'[^a-z0-9 ]', ' ', name.strip().lower())
    for suffix in ('inc', 'corp', 'corporation', 'llc', 'ltd', 'l p', 'co', 'company'):
        n = re.sub(r'\b' + suffix + r'\b', '', n)
    return ' '.join(n.split())

normalized_target = _normalize_company(target_name)

wb = load_workbook('example/deal_details_Alex_2026.xlsx', read_only=True, data_only=True)
ws = wb['deal_details']
headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
rows = []
for row in ws.iter_rows(min_row=2, values_only=True):
    d = dict(zip(headers, row))
    if d.get('TargetName') and _normalize_company(d['TargetName']) == normalized_target:
        for k, v in d.items():
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        rows.append(d)
wb.close()

if not rows:
    print(json.dumps({'error': f'No rows for target_name={target_name!r}'}))
    sys.exit(1)

outpath = f'data/skill/{slug}/reconcile/alex_rows.json'
import os; os.makedirs(os.path.dirname(outpath), exist_ok=True)
with open(outpath, 'w') as f:
    json.dump(rows, f, indent=2, default=str)
print(f'Extracted {len(rows)} rows to {outpath}')
" <slug>
```

Gate: `data/skill/<slug>/reconcile/alex_rows.json` exists and is non-empty.

### Step 2: Load the current pipeline artifacts

Read these files:
- `data/skill/<slug>/reconcile/alex_rows.json`
- `data/skill/<slug>/extract/events_raw.json`
- `data/skill/<slug>/extract/actors_raw.json`
- `data/skill/<slug>/export/deal_events.csv`
- `data/skill/<slug>/enrich/enrichment.json`
  - Fallback: `deterministic_enrichment.json` for `bid_classifications` only

Fallback rule:
- If `enrichment.json` is absent but `deterministic_enrichment.json` exists, use the deterministic artifact for `bid_classifications`.
- Do **not** invent `dropout_classifications` from the deterministic artifact. Skip dropout subtype comparison and note the skip in the report.

The export CSV is a required post-pipeline cross-check, but extract plus enrich remain the structured source of record for reconciliation.

### Step 3: Load the filing text through the live source contract

Do not guess the raw filing path from the slug alone.

1. Read `chronology_blocks.jsonl`.
2. Use the chronology blocks to identify the primary `document_id` that contains the merger-background chronology.
3. Read `raw/<slug>/document_registry.json`.
4. Resolve `document_id` to the corresponding `.txt` path from the registry.
5. Read that filing's full text from `raw/<slug>/filings/*.txt`.

This keeps the skill aligned with the current skill-native pipeline instead of stale path assumptions.

### Step 4: Normalize both sources into comparison records

Before matching:
- normalize Alex typos and whitespace
- normalize pipeline dropout labels: `DropBelowM` → `DropM` (pipeline uses `DropBelowM`, Alex uses `DropM` — they mean the same thing)
- map both sources into a shared event-family taxonomy
- detect aggregate Alex rows
- identify unmatched Alex note values
- derive a comparison natural key for pipeline events

Never use `event_id` as a cross-source key. `event_id` is pipeline-internal. Match on event family, date, actor, and price or range when available.

#### Pipeline event_type to Alex note mapping

| Pipeline `event_type` | Alex note / row shape | Match family |
|---|---|---|
| `proposal` | row where bid value or bid range is populated and `bid_note` is `NA`, blank, or null | `proposal` |
| `nda` | `NDA` | `nda` |
| `drop` | `Drop`, `DropM`, `DropTarget`, `DropBelowInf`, `DropAtInf` | `drop` |
| `ib_retention` | `IB` | `ib` |
| `target_sale` | `Target Sale` | `target_sale` |
| `target_sale_public` | `Target Sale Public` | `target_sale_public` |
| `bidder_sale` | `Bidder Sale` | `bidder_sale` |
| `bidder_interest` | `Bidder Interest` | `bidder_interest` |
| `activist_sale` | `Activist Sale` | `activist_sale` |
| `sale_press_release` | `Sale Press Release` | `sale_press_release` |
| `bid_press_release` | `Bid Press Release` | `bid_press_release` |
| `executed` | `Executed` | `executed` |
| `terminated` | `Terminated` | `terminated` |
| `restarted` | `Restarted` | `restarted` |
| `final_round_ann` | `Final Round Ann` | `final_round_ann` |
| `final_round` | `Final Round` | `final_round` |
| `final_round_inf_ann` | `Final Round Inf Ann` | `final_round_inf_ann` |
| `final_round_inf` | `Final Round Inf` | `final_round_inf` |
| `final_round_ext_ann` | `Final Round Ext Ann` | `final_round_ext_ann` |
| `final_round_ext` | `Final Round Ext` | `final_round_ext` |

Proposal identification on the Alex side:
- treat `"NA"` in `bid_note` as Alex's normal proposal row marker, not as missing data
- require at least one populated amount field:
  - `bid_value`
  - `bid_value_pershare`
  - `bid_value_lower`
  - `bid_value_upper`

#### Unmapped Alex note values

Treat these as Alex-only orphan families rather than forcing a bad match:
- `Exclusivity*`
- `IB Terminated`
- `Final Round Inf Ext*`
- `Target Interest`
- any other unrecognized note value

#### Aggregate Alex rows

Aggregate rows are **not** atomic event rows. Treat them as count-level coverage assertions, not as 1:1 matches.

Examples:
- `"24 parties"`
- `"16 financial bidders"`
- `"Several parties"`

Detection heuristics:
- bidder text contains a numeric plural aggregate
- bidder text starts with `Several`
- bidder text is clearly a grouped plural rather than a named actor

Aggregate handling:
- numeric aggregates: compare against a set of compatible pipeline events and filing count language
- vague aggregates such as `"Several parties"`: allow only soft coverage, not exact count claims
- aggregate rows do **not** enter the strict atomic match-rate denominator

Pipeline events covered by an aggregate Alex row with verdict `exact_count_match` or `soft_match` should be set aside from the strict 1:1 denominator rather than counted as pipeline-only failures.

### Step 5: Match atomic events by family, not by one global greedy pool

Do **not** throw all unmatched rows into one greedy matcher. Match inside each family first.

#### Actor name normalization

Normalize actor names by:
- lowercasing
- stripping suffixes such as `inc`, `corp`, `corporation`, `llc`, `ltd`, `l.p.`, `co`, `company`
- stripping leading `the`
- collapsing whitespace and punctuation

Pipeline side:
- check `display_name` first
- then check `aliases`

#### Consortium / joint-bid matching

When a pipeline event has multiple `actor_ids` (joint bid), or the CSV
`bidder` column contains `/` (slash-separated names):

1. Build the pipeline actor set from `actor_ids`, resolving each to
   `display_name` from the actor roster.
2. If Alex's bidder field also contains `/`, split on `/` and normalize
   each component independently.
3. Match if the normalized actor sets are equal regardless of order.
4. For `type` comparison, split the CSV `type` column on `/` and compare
   each component against the corresponding Alex type field.

Individual member events (e.g., separate NDA rows per consortium member)
still match as single-actor rows. Only joint proposal/drop rows use
consortium matching.

#### Proposal matching

Match in this order:
1. exact date + normalized actor + exact point value or exact range
2. exact date + normalized actor
3. date within 3 days + normalized actor + exact point value or exact range
4. date within 3 days + normalized actor

Never use `bid_type` as the primary proposal match key.

#### Drop matching

Match in this order:
1. exact date + normalized actor + dropout subtype when available on both sides
2. exact date + normalized actor
3. date within 3 days + normalized actor

Use subtype to refine a likely match, not to force a wrong one.

#### Bidderless process rows

For rows such as `Final Round`, `Final Round Ext Ann`, `Target Sale`, `Sale Press Release`, and similar bidderless events:
1. exact family + exact date
2. exact family + date within 3 days

Do not use category-only matching across different bidderless families.

#### Dense same-day clusters

When there are multiple same-family events on the same day, prefer the strongest observable fields:
- actor
- price / range
- exact note family
- distinctive drop reason text

If two or more candidate matches remain plausible after using the strongest fields, stop and leave the row unmatched or ambiguous. Do not guess.

### Step 6: Compare fields for matched pairs

The exported CSV (`deal_events.csv`) is the primary comparison surface.
Compare the CSV row against the matched Alex row first. Fall back to
internal extraction/enrichment artifacts only for fields the CSV does not
carry (e.g., `evidence_span_ids` for filing arbitration in Step 7).

If a CSV column disagrees with the internal artifact it was derived from,
that is an export regression — flag it in the report as
`export_regression` rather than a benchmark mismatch.

For each matched pair, compare these fields when relevant:

| Field | Pipeline source (CSV column) | Alex source | Event types |
|---|---|---|---|
| `bid_value` | `val` column | `bid_value` or `bid_value_pershare` | proposals |
| `bid_range` | `range` column (format: `X-Y`) | `bid_value_lower` to `bid_value_upper` | proposals |
| `bid_type` | `bid_type` column | `bid_type` | proposals |
| `dropout_subtype` | `note` column (`Drop`, `DropBelowM`, etc.) | `bid_note` subtype | drops |
| `bidder_type` | `type` column | `bidder_type_note` | NDAs / first bidder appearance |
| `date_precise` | `date_p` column | `bid_date_precise` | all |
| `date_rough` | `date_r` column | `bid_date_rough` | all |
| `all_cash` | `cash` column | `all_cash` | proposals |
| `bidder_name` | `bidder` column | Alex bidder field | all actor rows |

Bidder type code mapping (for cross-check against internal artifacts when
the CSV `type` column is `NA` on non-first-appearance rows):
- strategic + private + domestic = `S`
- financial + private + domestic = `F`
- add `public` prefix if `listing_status=public`
- add `non-US` prefix if `geography=non_us`

Known Alex-side cleanup:
- `"Informsl"` -> `"Informal"`
- strip whitespace from all text fields

Tolerances:
- bid values: plus or minus $0.01
- dates: precision-aware comparison using the pipeline's `date.precision`
  field from the internal extraction artifact:
  - `EXACT_DAY`: exact match only
  - `MONTH_EARLY`, `MONTH_MID`, `MONTH_LATE`: Alex's date must fall
    within the pipeline's `normalized_start` to `normalized_end` range
  - `MONTH`: Alex's date must fall within the calendar month
  - `QUARTER`: Alex's date must fall within the calendar quarter
  - `RANGE`: Alex's date must fall within `normalized_start` to
    `normalized_end`
  - `RELATIVE`, `YEAR`, `UNKNOWN`: widen tolerance to +/- 30 days and
    note the imprecision in the report
  - When the CSV `date_p` is `NA` (imprecise date), use `date_r` for
    matching and note the rough-date comparison in the report

#### `Uncertain` handling

`Uncertain` is a valid pipeline output, not a missing value.

If the pipeline labels a proposal `Uncertain` and Alex labels it `Formal` or `Informal`:
- record the mismatch
- arbitrate it against the filing
- do **not** treat Alex's forced label as automatically more correct

An `Uncertain` mismatch alone should never force `fail`.

### Step 7: Arbitrate disagreements against the filing

For each field mismatch:

1. Resolve the pipeline event's `evidence_span_ids` by looking up each span_id
   in `data/skill/<slug>/extract/spans.json`. Each `SpanRecord` has
   `document_id`, `start_line`, `end_line`, `block_ids`, and `anchor_text`.
2. Use `document_registry.json` to resolve `document_id` to the correct
   filing `.txt` path.
3. Read the filing passage with plus or minus 5 lines of context.
4. Search for both the pipeline claim and Alex claim.
6. Record:
   - `filing_supports: "pipeline" | "alex" | "both" | "neither" | "inconclusive" | "no_evidence"`
   - a filing snippet

Use both explicit wording and contextual rule basis.

#### What to search for

- Amounts:
  - `$X`
  - `$X.XX`
  - `X per share`
  - `X.XX per share`
- Dates:
  - `Month Day`
  - `Month Day, Year`
- Informal bid language:
  - `indication of interest`
  - `preliminary`
  - `non-binding`
- Formal bid language:
  - `binding`
  - `definitive`
  - `draft merger agreement`
  - `marked-up merger agreement`
  - `process letter`
- Dropout language:
  - `withdrew`
  - `no longer interested`
  - `declined to increase`
  - `not invited`
  - `below market`

#### Contextual arbitration rules

Use the current pipeline logic when explicit keywords are not enough.

- For `Uncertain` versus `Formal` or `Informal`:
  - consult the filing language **and** the pipeline's deterministic basis such as selective-round context or absence of explicit formality signals
  - if the filing provides only mixed or contextual support, prefer `pipeline` or `inconclusive` over a forced Alex win

- For `DropBelowInf` and `DropAtInf`:
  - compare the filing's drop language against earlier proposal values for that actor
  - do not rely on keywords alone

If the event has no usable `evidence_span_ids`, verdict is `no_evidence`.

### Step 8: Verify orphans and aggregate rows separately

#### Pipeline-only atomic orphans

These have `evidence_span_ids`.

- look up each span_id in `spans.json` to get `document_id`, `start_line`,
  `end_line`, and `anchor_text`
- read the referenced filing passage
- check whether `anchor_text` appears at EXACT or NORMALIZED match level
- verdict: `grounded` or `ungrounded`

#### Alex-only atomic orphans

These do not have evidence refs.

Search the chronology for:
1. the claimed date
2. the actor name
3. the amount, if present

If at least two of those signals appear near each other in the chronology section, verdict `likely_grounded`. Otherwise `ungrounded`.

#### Aggregate Alex rows

Do not treat aggregate rows as normal Alex-only orphans.

Use one of these verdicts instead:
- `exact_count_match`
- `soft_match`
- `count_conflict`
- `ambiguous`
- `ungrounded`

Guidance:
- numeric aggregate row + filing-supported exact count + compatible pipeline set -> `exact_count_match`
- vague aggregate row + compatible grounded pipeline set -> `soft_match`
- filing count clearly contradicts pipeline count -> `count_conflict`
- multiple plausible interpretations -> `ambiguous`
- filing does not support the aggregate claim -> `ungrounded`

### Step 9: Write the reconciliation report

Write to `data/skill/<slug>/reconcile/reconciliation_report.json`:

```json
{
  "deal_slug": "<slug>",
  "target_name": "<name>",
  "pipeline_event_count": 38,
  "alex_event_count": 16,
  "aggregate_alex_count": 2,
  "matched_count": 12,
  "pipeline_only_count": 1,
  "alex_only_count": 1,
  "aggregate_rows": [
    {
      "alex_bidder_id": 9.0,
      "event_family": "nda",
      "actor_name": "Several parties",
      "date_rough": "2016-07-05",
      "expected_count": null,
      "pipeline_event_ids": ["evt_010", "evt_011", "evt_012", "evt_013"],
      "filing_verdict": "soft_match",
      "filing_snippet": "Several parties executed confidentiality agreements..."
    }
  ],
  "field_mismatches": [
    {
      "pipeline_event_id": "evt_008",
      "alex_bidder_id": 3.0,
      "field": "bid_type",
      "pipeline_value": "Uncertain",
      "alex_value": "Formal",
      "filing_supports": "inconclusive",
      "filing_snippet": "...mixed signals from non-binding language and later-round context..."
    }
  ],
  "pipeline_only": [
    {
      "source": "pipeline",
      "event_id": "evt_015",
      "alex_bidder_id": null,
      "event_family": "nda",
      "actor_name": "Party G",
      "date_rough": "2016-03-15",
      "value": null,
      "filing_verdict": "grounded",
      "filing_snippet": "Party G executed a confidentiality agreement on March 15"
    }
  ],
  "alex_only": [
    {
      "source": "alex",
      "event_id": null,
      "alex_bidder_id": 14.0,
      "event_family": "drop",
      "actor_name": "Party H",
      "date_rough": "2016-05-20",
      "value": null,
      "filing_verdict": "likely_grounded",
      "filing_snippet": "Party H informed the Company it was no longer interested"
    }
  ],
  "summary": {
    "status": "warn",
    "match_rate": 0.92,
    "field_mismatch_count": 1,
    "aggregate_warning_count": 1,
    "arbitration_pipeline_wins": 0,
    "arbitration_alex_wins": 0,
    "arbitration_inconclusive": 1,
    "orphan_grounded_count": 0,
    "orphan_ungrounded_count": 0
  }
}
```

Define:
- `match_rate = matched_count / max(matched_count + pipeline_only_count, matched_count + alex_only_count)`
- This denominator uses only the remaining atomic comparison pools after aggregate handling

### Step 10: Status logic

Evaluate in order:

1. `fail` if:
   - `match_rate < 0.7`, or
   - ungrounded atomic orphans outnumber grounded atomic orphans, or
   - a numeric aggregate row has `count_conflict` and the filing clearly supports Alex's count against the pipeline

2. `warn` if:
   - `match_rate < 0.9`, or
   - any field mismatch has `filing_supports` in `alex`, `inconclusive`, or `no_evidence`, or
   - any atomic orphan is `ungrounded`, or
   - any aggregate row has verdict `count_conflict`, `ambiguous`, or `ungrounded`

3. `pass` otherwise

Aggregate rows alone should not trigger `fail` unless the filing clearly contradicts the pipeline's count-level story.

### Step 11: Report summary to the user

Print a concise summary:
- pipeline vs Alex event counts
- atomic match rate
- aggregate-row coverage summary
- top field mismatches with arbitration results
- pipeline-only and Alex-only orphan verdicts
- overall status

## Reads

| File | Content |
|---|---|
| `data/skill/<slug>/extract/actors_raw.json` | Pipeline actors with names, types, and evidence_span_ids |
| `data/skill/<slug>/extract/events_raw.json` | Pipeline events with dates, amounts, and evidence_span_ids |
| `data/skill/<slug>/extract/spans.json` | Resolved span registry (span_id → document_id, lines, anchor_text) |
| `data/skill/<slug>/enrich/enrichment.json` | Full enrichment including bid and dropout classifications |
| `data/skill/<slug>/enrich/deterministic_enrichment.json` | Fallback for bid classifications only |
| `data/deals/<slug>/source/chronology_blocks.jsonl` | block_id to document_id and filing-line mapping |
| `raw/<slug>/document_registry.json` | document_id to filing path mapping |
| `raw/<slug>/filings/*.txt` | Raw SEC filing text |
| `example/deal_details_Alex_2026.xlsx` | Alex's hand-coded spreadsheet |
| `data/seeds.csv` | slug to target_name mapping |

## Writes

| File | Content |
|---|---|
| `data/skill/<slug>/reconcile/alex_rows.json` | Extracted Alex rows (intermediate) |
| `data/skill/<slug>/reconcile/reconciliation_report.json` | Final reconciliation report |

## Gate

`reconciliation_report.json` exists. The `summary.status` field is
informational (`pass`, `warn`, or `fail`) and does NOT gate the pipeline.
This is a diagnostic report for the researcher, not a pipeline stop
condition. A `fail` status means the disagreement with Alex is large
enough to warrant investigation, not that the pipeline output is wrong.
