# Home Computer Setup

This repository is intended to run locally with the checked-in Python tooling
and the `skill-pipeline` CLI.

## Local Workflow

Use the filing-grounded workflow through `/export-csv`.

Benchmark materials are post-export only. Do not consult `example/`,
`diagnosis/`, benchmark workbooks, or `/reconcile-alex` before `/export-csv`
completes.

## Minimum Setup

- Install the package in editable mode: `pip install -e .`
- Use an EDGAR identity variable when running live SEC fetches.
- Keep generated artifacts under `data/skill/<slug>/` separate from read-only
  source inputs under `data/deals/<slug>/source/` and `raw/<slug>/`.
