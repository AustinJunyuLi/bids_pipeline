# Home Computer Setup

This repository is intended to run locally with the checked-in Python tooling
and the `skill-pipeline` CLI.

## Local Workflow

Use the filing-grounded workflow through `skill-pipeline db-export --deal <slug>`.

Benchmark materials are post-export only. Do not consult `example/`,
`diagnosis/`, benchmark workbooks, or `/reconcile-alex` before
`skill-pipeline db-export --deal <slug>` completes.

## Minimum Setup

- Install a standalone CPython: `uv python install 3.13`
- Create the local virtual environment: `uv venv --python 3.13 --managed-python --seed .venv`
- Activate it in PowerShell: `.\.venv\Scripts\Activate.ps1`
- Install the package in editable mode from the active venv: `python -m pip install -e .`
- Use an EDGAR identity environment variable when running live SEC fetches.
- Keep generated artifacts under `data/skill/<slug>/` separate from read-only
  source inputs under `data/deals/<slug>/source/` and `raw/<slug>/`.
