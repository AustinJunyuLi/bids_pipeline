---
name: deal-agent
description: Use when orchestrating the live v2 deal workflow from raw filing fetch through v2 DuckDB export, with a clean rerun that overwrites current v2 results.
---

# deal-agent

## Design Principles

1. This is the live default orchestrator.
2. It performs a clean v2 rerun: delete current live v2 outputs for the deal, then rebuild from filing-grounded inputs.
3. It never reads benchmark material during generation.
4. It never revives archived v1 artifacts into the live surface.

## Purpose

Run the repository's live v2 observation-graph workflow end to end for one
deal, from frozen filing text through `db-export-v2`.

The goal is a clean, filing-grounded rerun that overwrites the current live v2
outputs for `<slug>` while leaving `raw/<slug>/` untouched.

## When To Use

Invoke as `/deal-agent <slug>` when you want the current deal rebuilt on the
live v2 contract.

## Benchmark Boundary

Benchmark materials are forbidden during generation. Do not consult benchmark
files, benchmark notes, `example/`, `diagnosis/`,
`data/skill/<slug>/reconcile/*`, or `/reconcile-alex` before
`skill-pipeline db-export-v2 --deal <slug>` completes.

## Live Outputs

This workflow owns these live paths:

- `data/skill/<slug>/prompt_v2/`
- `data/skill/<slug>/extract_v2/`
- `data/skill/<slug>/check_v2/`
- `data/skill/<slug>/coverage_v2/`
- `data/skill/<slug>/gates_v2/`
- `data/skill/<slug>/derive/`
- `data/skill/<slug>/export_v2/`
- `data/pipeline.duckdb` via `v2_*` tables
- historical v1 recovery through Git tag `v1-working-tree-2026-04-01`

## Procedure

```text
0. Clean the live v2 surface for <slug>.
   Delete:
   - data/skill/<slug>/prompt_v2/
   - data/skill/<slug>/extract_v2/
   - data/skill/<slug>/check_v2/
   - data/skill/<slug>/coverage_v2/
   - data/skill/<slug>/gates_v2/
   - data/skill/<slug>/derive/
   - data/skill/<slug>/export_v2/
   Delete data/deals/<slug>/source/ so preprocess-source rebuilds cleanly.
   Do not touch raw/<slug>/.
1. Confirm data/seeds.csv contains <slug>.

2. Run `skill-pipeline raw-fetch --deal <slug>`.
   Gate: raw/<slug>/document_registry.json exists.

3. Run `skill-pipeline preprocess-source --deal <slug>`.
   Gate: data/deals/<slug>/source/chronology_blocks.jsonl exists.

4. Run `skill-pipeline compose-prompts --deal <slug> --mode observations`.
   Gate: data/skill/<slug>/prompt_v2/manifest.json exists and packet_count > 0.

5. Run `/extract-deal-v2 <slug>`.
   Gate: data/skill/<slug>/extract_v2/observations_raw.json exists and is non-empty.

6. Run `skill-pipeline canonicalize-v2 --deal <slug>`.
   Gate: observations.json and spans.json exist.

7. Run `skill-pipeline check-v2 --deal <slug>`.
   Gate: check_report.json exists and summary.status == "pass".

8. Run `skill-pipeline coverage-v2 --deal <slug>`.
   Gate: coverage_summary.json exists and summary.status == "pass".

9. Run `skill-pipeline gates-v2 --deal <slug>`.
   Gate: gates_report.json exists and blocker_count == 0.

10. Run `/verify-extraction-v2 <slug>` only if deterministic findings are repairable.
    If the raw observation artifact changes, rerun steps 6-9.

11. Run `skill-pipeline derive --deal <slug>`.
    Gate: derivations.json exists and is non-empty.

12. Run `skill-pipeline db-load-v2 --deal <slug>`.
    Gate: data/pipeline.duckdb exists and contains v2 rows for <slug>.

13. Run `skill-pipeline db-export-v2 --deal <slug>`.
    Gate:
    - export_v2/literal_observations.csv exists
    - export_v2/analyst_rows.csv exists
    - export_v2/benchmark_rows_expanded.csv exists

14. Optionally run `/reconcile-alex <slug>` after db-export-v2 completes.
```

## Notes

- `skill-pipeline deal-agent --deal <slug>` is only a summary/preflight CLI. It
  does not execute the workflow above.
- The retired v1 runtime is recoverable through tag `v1-working-tree-2026-04-01`,
  not through working-tree files.
