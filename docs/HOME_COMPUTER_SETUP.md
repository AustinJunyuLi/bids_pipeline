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
- Create a local virtual environment with a host-appropriate directory name: `uv venv --python 3.13 --managed-python --seed <local-venv-dir>`
- Activate it according to your host shell.
- Install the package in editable mode from the active venv: `python -m pip install -e .`
- Set `PIPELINE_SEC_IDENTITY` in your shell profile for live SEC fetches.
- Keep `.env.local` for machine-local tooling or editor settings only.
- If this checkout has `.claude/LOCAL.md`, treat it as the machine-local override for venv naming and shell-specific workflow details.
- Keep generated artifacts under `data/skill/<slug>/` separate from read-only
  source inputs under `data/deals/<slug>/source/` and `raw/<slug>/`.
