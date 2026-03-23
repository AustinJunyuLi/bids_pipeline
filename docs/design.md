# Skill Pipeline Design Index

## Current

The active production architecture is the consolidated `skill_pipeline` runtime.

- **Operator docs:** [`CLAUDE.md`](../CLAUDE.md)
- **Production CLI:** [`skill_pipeline/cli.py`](../skill_pipeline/cli.py)
- **Production orchestrator:** [`skill_pipeline/stages/run.py`](../skill_pipeline/stages/run.py)
- **Core runtime helpers:** [`skill_pipeline/core/`](../skill_pipeline/core)
- **Pipeline stages:** [`skill_pipeline/stages/`](../skill_pipeline/stages)
- **Schemas:** [`skill_pipeline/schemas/`](../skill_pipeline/schemas)
- **Standalone reconciliation:** [`scripts/reconcile_alex.py`](../scripts/reconcile_alex.py)
- **Backend probe:** [`scripts/stress_linkflow_backend.py`](../scripts/stress_linkflow_backend.py)

Current pipeline shape:

- `skill-pipeline raw-fetch --deal <slug>`
- `skill-pipeline preprocess-source --deal <slug>`
- `skill-pipeline run --deal <slug>`
- `python scripts/reconcile_alex.py --deal <slug>` only after export

Benchmark materials remain post-export only. Before `/export-csv` completes, do
not consult `example/`, `diagnosis/`, benchmark workbooks, or reconciliation
artifacts.

## Archived

These are historical references, not active instructions:

- The deleted hybrid agent workflow that used `/extract-deal`, `/verify-extraction`, `/enrich-deal`, and `/export-csv`
- The empty legacy `pipeline/` package
- Old v1/v2/v3 planning docs that predate the consolidated `skill_pipeline` runtime

## Notes

If a design document conflicts with [`CLAUDE.md`](../CLAUDE.md), treat
[`CLAUDE.md`](../CLAUDE.md) as authoritative for operator behavior. Files under
`docs/plans/` and `docs/superpowers/` are archival design records, not live
operator instructions.
