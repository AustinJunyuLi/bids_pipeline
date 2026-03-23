# Home Computer Setup

This repository is intended to run locally with the checked-in Python tooling and the `skill-pipeline` CLI.

## Local Workflow

Use `skill-pipeline run --deal <slug>` for production generation through export.

The supported production sequence is:

1. `skill-pipeline raw-fetch --deal <slug>`
2. `skill-pipeline preprocess-source --deal <slug>`
3. `skill-pipeline run --deal <slug>`
4. `python scripts/reconcile_alex.py --deal <slug>` only after export, if benchmark QA is needed

Benchmark materials are post-export only. Before `/export-csv` completes, do not
consult `example/`, `diagnosis/`, benchmark workbooks, or reconciliation artifacts.

## Minimum Setup

- Install the package in editable mode: `pip install -e .`
- Set an EDGAR identity variable before running live SEC fetches.
- Keep generated artifacts under `data/skill/<slug>/` separate from read-only source inputs under `data/deals/<slug>/source/` and `raw/<slug>/`.
- Treat `skill_pipeline` as the active pipeline and `python scripts/reconcile_alex.py --deal <slug>` as a standalone diagnostic.
