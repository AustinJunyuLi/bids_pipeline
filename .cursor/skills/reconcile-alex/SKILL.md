---
name: reconcile-alex
description: Use when a deal has completed the skill-native pipeline and you need benchmark reconciliation against Alex's spreadsheet, especially for row mismatches, aggregate spreadsheet rows, or disagreements that require filing-text arbitration.
---

# reconcile-alex

## Design Principles

1. This is an agent skill. You read both data sources and the raw filing, then reason about matches, disagreements, and filing evidence. No Python comparison code exists.
2. This is a secondary benchmark-validation skill, not the primary truth gate. `check`, `verify`, and `/verify-extraction` own pipeline grounding first.
3. Neither source is authoritative. The raw filing text is the tiebreaker.
4. Stay inside the current skill-native pipeline. Do not assume a deleted canonical-model layer exists.
5. Fail closed on missing prerequisites. When a comparison is unsupported, skip it explicitly and record why instead of guessing.

## Purpose

Post-pipeline validation that compares the current skill-native pipeline outputs
against Alex's hand-coded spreadsheet, then arbitrates disagreements and orphan
events against the actual SEC filing text.

The point is not to make Alex authoritative. The point is to measure benchmark
agreement, explain disagreements, and distinguish true filing-grounded pipeline
problems from harmless granularity or formatting mismatches.

## When To Use

Invoke as `/reconcile-alex <slug>` only after the full pipeline has completed
for a deal through `skill-pipeline db-export --deal <slug>`.

Benchmark materials are forbidden during generation. This skill is post-export
only and must not be used to steer extraction, verification, enrichment, or
export while a deal is still being generated.

Do not use this skill as a substitute for `check`, `verify`, or
`/verify-extraction`.

## Cross-Machine Handoff

- This is a read-only QA skill. It must not rewrite generation artifacts.
- If a prior session consulted benchmark materials before
  `skill-pipeline db-export --deal <slug>` and then generated
  `data/skill/<slug>/...` artifacts, treat those artifacts as tainted for blind
  evaluation.
- A fresh agent on another machine should not continue generation from those
  tainted artifacts. Regenerate from the filing-grounded workflow, complete
  `skill-pipeline db-export --deal <slug>`, and only then run
  `/reconcile-alex`.

## Prerequisites

Before starting, confirm all of these exist:

- `data/skill/<slug>/extract/actors_raw.json`
- `data/skill/<slug>/extract/events_raw.json`
- `data/skill/<slug>/extract/spans.json`
- `data/skill/<slug>/export/deal_events.csv`
- `data/skill/<slug>/enrich/enrichment.json`
- `data/skill/<slug>/enrich/deterministic_enrichment.json`
- `data/deals/<slug>/source/chronology_blocks.jsonl`
- `raw/<slug>/document_registry.json`
- `raw/<slug>/filings/*.txt`
- `example/deal_details_Alex_2026.xlsx`

If any are missing, stop and tell the user what is missing.

## Procedure

### Step 1: Extract Alex rows for this deal

The xlsx file is binary; use Python to extract:

```bash
python3 -c "
import csv, json, os, re, sys
from datetime import datetime
from openpyxl import load_workbook

slug = sys.argv[1]

with open('data/seeds.csv', encoding='utf-8') as f:
    for row in csv.DictReader(f):
        if row['deal_slug'] == slug:
            target_name = row['target_name']
            break
    else:
        raise SystemExit(json.dumps({'error': f'slug {slug} not found in seeds.csv'}))

def norm(name):
    value = re.sub(r'[^a-z0-9 ]', ' ', name.strip().lower())
    for suffix in ('inc', 'corp', 'corporation', 'llc', 'ltd', 'l p', 'co', 'company'):
        value = re.sub(r'\\b' + suffix + r'\\b', '', value)
    return ' '.join(value.split())

wb = load_workbook('example/deal_details_Alex_2026.xlsx', read_only=True, data_only=True)
ws = wb['deal_details']
headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
rows = []
for row in ws.iter_rows(min_row=2, values_only=True):
    data = dict(zip(headers, row))
    if data.get('TargetName') and norm(data['TargetName']) == norm(target_name):
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        rows.append(data)
wb.close()

if not rows:
    raise SystemExit(json.dumps({'error': f'No rows for target_name={target_name!r}'}))

outpath = f'data/skill/{slug}/reconcile/alex_rows.json'
os.makedirs(os.path.dirname(outpath), exist_ok=True)
with open(outpath, 'w', encoding='utf-8') as f:
    json.dump(rows, f, indent=2)
print(f'Extracted {len(rows)} rows to {outpath}')
" <slug>
```

Gate: `data/skill/<slug>/reconcile/alex_rows.json` exists and is non-empty.

### Step 2: Load the current pipeline artifacts

Read:

- `data/skill/<slug>/reconcile/alex_rows.json`
- `data/skill/<slug>/extract/events_raw.json`
- `data/skill/<slug>/extract/actors_raw.json`
- `data/skill/<slug>/extract/spans.json`
- `data/skill/<slug>/export/deal_events.csv`
- `data/skill/<slug>/enrich/deterministic_enrichment.json`
  - authoritative for `bid_classifications`, `rounds`, `cycles`,
    `formal_boundary`, sparse `DropTarget`, and `all_cash_overrides`
- `data/skill/<slug>/enrich/enrichment.json`
  - interpretive-only layer for `dropout_classifications`,
    `initiation_judgment`, `advisory_verification`,
    `count_reconciliation`, and `review_flags`

The export CSV is the primary comparison surface. Extract and enrich provide
canonical IDs, provenance, and fallback details when the CSV intentionally
compresses information.

### Step 3: Load the filing text through the live source contract

Do not guess the raw filing path from the slug alone.

1. Read `chronology_blocks.jsonl`.
2. Use the chronology blocks to identify the primary `document_id`.
3. Read `raw/<slug>/document_registry.json`.
4. Resolve `document_id` to the correct `.txt` path.
5. Read that filing's full text from `raw/<slug>/filings/*.txt`.

### Step 4: Normalize both sides into comparison records

Before matching:

- normalize Alex typos and whitespace
- normalize pipeline dropout labels so `DropBelowM` and `DropM` are treated as equivalent
- map both sources into a shared event-family taxonomy
- detect aggregate Alex rows such as `24 parties` or `Several parties`
- derive comparison keys from family, date, actor, and price or range when available

Never use pipeline `event_id` as a cross-source key.

### Step 5: Match atomic events by family

Do not throw all rows into one global greedy matcher. Match inside each family
first.

Guidelines:

- proposals: prefer exact date + normalized actor + exact price/range, then relax to date-within-3-days
- drops: prefer exact date + actor + subtype when both sides have subtype, then relax
- bidderless process rows: match on family + date, not category-only
- consortium rows: compare normalized actor sets, not string order
- dense same-day clusters: if multiple candidates remain plausible after actor, amount, and note family checks, leave the row ambiguous rather than guessing

### Step 6: Compare fields for matched pairs

The CSV is the primary comparison surface. Fall back to internal extract or
enrich artifacts only for fields the CSV does not carry or intentionally
compresses.

Compare, when relevant:

- bidder name
- bidder type
- date
- price or range
- bid type
- dropout subtype
- all-cash flag

If the CSV disagrees with the internal artifact it was derived from, record that
under `export_regressions` rather than as a benchmark mismatch.

### Step 7: Arbitrate disagreements against the filing

For each mismatch:

1. Resolve the pipeline event's `evidence_span_ids` through `extract/spans.json`.
2. Use the span's `document_id`, `start_line`, and `end_line` plus the registry
   to find the correct filing text.
3. Read the passage with about +/- 5 lines of context.
4. Search for both the pipeline claim and Alex claim.
5. Record:
   - `filing_supports: "pipeline" | "alex" | "both" | "neither" | "inconclusive" | "no_evidence"`
   - a filing snippet

Use explicit wording first. Use contextual rules only when the filing text is
not enough by itself.

### Step 8: Handle orphans and aggregate rows separately

Pipeline-only atomic orphans:

- verify they are grounded through `evidence_span_ids`
- verdict: `grounded` or `ungrounded`

Alex-only atomic orphans:

- search chronology and filing for date, actor, and amount signals
- verdict: `likely_grounded` or `ungrounded`

Aggregate Alex rows are not 1:1 atomic events. Use count-level verdicts:

- `exact_count_match`
- `soft_match`
- `count_conflict`
- `ambiguous`
- `ungrounded`

Aggregate rows do not enter the strict atomic match-rate denominator.

### Step 9: Write the reconciliation report

Write `data/skill/<slug>/reconcile/reconciliation_report.json` with:

- counts for pipeline, Alex, matches, pipeline-only, Alex-only, and aggregate rows
- `field_mismatches`
- `pipeline_only`
- `alex_only`
- `aggregate_rows`
- `export_regressions`
- `summary`

`summary.status` must be one of:

- `clean`
- `attention`
- `high_attention`

Status is informational only. It does not gate the pipeline.

### Step 10: Report the result to the user

Print a concise summary covering:

- pipeline vs Alex event counts
- atomic match rate
- aggregate-row coverage summary
- top field mismatches with arbitration results
- pipeline-only and Alex-only orphan verdicts
- overall status

## Reads

| File | Content |
|---|---|
| `data/skill/<slug>/extract/actors_raw.json` | pipeline actors with names, types, and evidence span IDs |
| `data/skill/<slug>/extract/events_raw.json` | pipeline events with dates, amounts, and evidence span IDs |
| `data/skill/<slug>/extract/spans.json` | resolved span registry |
| `data/skill/<slug>/enrich/deterministic_enrichment.json` | Deterministic enrichment baseline: bid classifications, rounds, cycles, formal boundary, sparse DropTarget labels, all-cash overrides |
| `data/skill/<slug>/enrich/enrichment.json` | Interpretive enrichment layer: dropout classifications, initiation judgment, advisory verification, count reconciliation, review flags |
| `data/deals/<slug>/source/chronology_blocks.jsonl` | block to filing mapping |
| `raw/<slug>/document_registry.json` | document ID to filing path mapping |
| `raw/<slug>/filings/*.txt` | raw SEC filing text |
| `example/deal_details_Alex_2026.xlsx` | Alex's hand-coded spreadsheet |
| `data/seeds.csv` | slug to target-name mapping |

## Writes

| File | Content |
|---|---|
| `data/skill/<slug>/reconcile/alex_rows.json` | extracted Alex rows |
| `data/skill/<slug>/reconcile/reconciliation_report.json` | final reconciliation report |

## Gate

`reconciliation_report.json` exists. The `summary.status` field is
informational (`clean`, `attention`, or `high_attention`) and does not gate the
pipeline. This is a diagnostic report for the researcher, not a pipeline stop
condition.
