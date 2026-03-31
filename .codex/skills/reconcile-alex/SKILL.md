---
name: reconcile-alex
description: Use when a deal has completed the live v2 pipeline and you need post-export benchmark reconciliation against Alex's spreadsheet.
---

# reconcile-alex

## Design Principles

1. This is a read-only QA skill.
2. The filing text is the tiebreaker when pipeline and benchmark disagree.
3. Reconciliation is post-export only. It must never steer generation.
4. Compare the v2 benchmark-facing export while keeping literal observation
   provenance available for arbitration.

## Purpose

Compare the live v2 export surface for one deal against Alex's spreadsheet, then
arbitrate disagreements against the filing text.

## When To Use

Invoke as `/reconcile-alex <slug>` only after the full v2 pipeline has
completed through `skill-pipeline db-export-v2 --deal <slug>`.

This skill is forbidden during generation.

## Prerequisites

Confirm all of these exist before starting:

- `data/skill/<slug>/export_v2/analyst_rows.csv`
- `data/skill/<slug>/export_v2/benchmark_rows_expanded.csv`
- `data/skill/<slug>/export_v2/literal_observations.csv`
- `data/skill/<slug>/extract_v2/observations.json`
- `data/skill/<slug>/extract_v2/spans.json`
- `data/deals/<slug>/source/chronology_blocks.jsonl`
- `raw/<slug>/document_registry.json`
- `raw/<slug>/filings/*.txt`
- `example/deal_details_Alex_2026.xlsx`

If any are missing, stop and report the missing prerequisite.

## Procedure

```text
1. Extract Alex rows for <slug> into data/skill/<slug>/reconcile/alex_rows.json.
2. Load:
   - export_v2/benchmark_rows_expanded.csv as the benchmark-facing comparison surface
   - export_v2/analyst_rows.csv for the unexpanded analyst-row surface
   - export_v2/literal_observations.csv for literal provenance context
   - extract_v2/observations.json and extract_v2/spans.json for filing-grounded arbitration
3. Normalize actor names, dates, ranges, and dropout labels before matching.
4. Match rows within family first; do not use a single global greedy match.
5. For mismatches, resolve the relevant span IDs and inspect the filing text.
6. Classify each disagreement as:
   - pipeline
   - alex
   - both
   - neither
   - inconclusive
7. Write data/skill/<slug>/reconcile/reconciliation_report.json.
```

## Writes

- `data/skill/<slug>/reconcile/alex_rows.json`
- `data/skill/<slug>/reconcile/reconciliation_report.json`

## Gate

`reconciliation_report.json` exists. Its status is informational only and does
not gate the pipeline.
