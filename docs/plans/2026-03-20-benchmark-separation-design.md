# Benchmark Separation Design

## Problem

The repo currently separates filing-grounded generation from benchmark
reconciliation in practice, but not sharply enough in the active instructions.
That leaves three risks:

1. An agent can consult Alex benchmark materials before generation because the
   prohibition is not explicit in the generation workflow.
2. `/reconcile-alex` currently allows a pre-export invocation path, which
   weakens the intended boundary.
3. Generation-stage docs still describe export in Alex-centric terms, which
   blurs the line between a fixed review-schema contract and benchmark-driven
   comparison.

## Goals

1. Keep generation filing-grounded through `/export-csv`.
2. Make benchmark comparison strictly post-export and read-only.
3. Preserve the current review CSV contract without requiring any benchmark
   lookup during generation.
4. Add an automated regression check so the boundary does not drift.

## Non-Goals

1. Rewriting historical design docs that are no longer active instructions.
2. Reworking the current review CSV schema.
3. Deleting previously generated artifacts in this patch.

## Chosen Approach

Adopt a strict instruction-layer separation:

1. Add an explicit benchmark-separation policy to `CLAUDE.md`.
2. Update all active generation skills to forbid consulting Alex materials
   before `/export-csv` completes.
3. Update all `reconcile-alex` skill mirrors so reconciliation is post-export
   only and explicitly not part of generation.
4. Reword export as a fixed repo review-CSV contract rather than a live lookup
   against Alex’s spreadsheet.
5. Add a policy test that checks the live docs/skills for regressions.

## Allowed vs Forbidden Inputs

### Allowed before `/export-csv`

- `raw/<slug>/filings/*.txt`
- `raw/<slug>/document_registry.json`
- `data/deals/<slug>/source/*`
- `data/skill/<slug>/extract/*`
- `data/skill/<slug>/verify/*`
- `data/skill/<slug>/enrich/*`
- `data/seeds.csv`

### Forbidden before `/export-csv`

- `example/deal_details_Alex_2026.xlsx`
- `docs/CollectionInstructions_Alex_2026.qmd`
- `docs/bidding_instructions_flowcharts.qmd`
- `docs/bidding_instructions_flowcharts.html`
- `data/skill/<slug>/reconcile/*`
- `/reconcile-alex`
- Any deal-specific benchmark notes derived from Alex’s workbook

## Enforcement Strategy

The repo does not currently have a Python runtime hook for agent skill inputs,
so the right enforcement layer is the active instruction surface:

- `CLAUDE.md`
- generation skill docs
- `reconcile-alex` skill docs
- a regression test that fails if those docs drift

## Rationale

This keeps the pipeline behavior clean without pretending the review CSV schema
does not exist. The schema remains a repo contract. What is prohibited is
benchmark consultation before generation, not the existence of a stable export
format.
