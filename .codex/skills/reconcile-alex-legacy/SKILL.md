---
name: reconcile-alex-legacy
description: Use when you explicitly need benchmark reconciliation on the archived v1 event-first export surface.
---

# reconcile-alex-legacy

## Status

This skill is the preserved v1 reconciliation workflow. The live default is
`/reconcile-alex`.

## Purpose

Compare the archived v1 event-first export surface against Alex's spreadsheet
after `skill-pipeline db-export --deal <slug>` completes.

## Deterministic / Interpretive Split

- Deterministic enrichment baseline:
  `data/skill/<slug>/enrich/deterministic_enrichment.json`
- Interpretive enrichment layer:
  `data/skill/<slug>/enrich/enrichment.json`

The legacy reconciliation workflow may inspect both, but generation remains
post-export only.

## Benchmark Boundary

Benchmark materials are forbidden during generation. Do not consult benchmark
files, benchmark notes, `example/`, `diagnosis/`,
`data/skill/<slug>/reconcile/*`, or `/reconcile-alex-legacy` before
`skill-pipeline db-export --deal <slug>` completes.

## Prerequisites

- `data/skill/<slug>/export/deal_events.csv`
- `data/skill/<slug>/extract/actors_raw.json`
- `data/skill/<slug>/extract/events_raw.json`
- `data/skill/<slug>/extract/spans.json`
- `data/skill/<slug>/enrich/deterministic_enrichment.json`
- `data/skill/<slug>/enrich/enrichment.json`
- `example/deal_details_Alex_2026.xlsx`

## Writes

- `data/skill/<slug>/reconcile/alex_rows.json`
- `data/skill/<slug>/reconcile/reconciliation_report.json`
