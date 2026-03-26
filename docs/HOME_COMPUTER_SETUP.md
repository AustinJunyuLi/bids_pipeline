# Home Computer Setup

This repository is intended to run locally with the checked-in Python tooling
and the `skill-pipeline` CLI. For the full stage inventory and artifact
contracts, see [`docs/workflow-contract.md`](workflow-contract.md).

## Local Workflow

The pipeline is a hybrid of deterministic CLI stages and LLM-driven skills.
Use `/deal-agent <slug>` for end-to-end orchestration after upstream source
preparation, or invoke individual stages as documented in the workflow contract.

Note: `skill-pipeline deal-agent --deal <slug>` is a **preflight/summary**
command only. It checks prerequisites and summarizes artifact status but does
not run extraction, repair, enrichment, or export.

Benchmark materials are post-export only. Do not consult `example/`,
`diagnosis/`, benchmark workbooks, or `/reconcile-alex` before `/export-csv`
completes.

## Minimum Setup

- Install the package in editable mode: `pip install -e .`
- Use an EDGAR identity environment variable when running live SEC fetches.
- Keep generated artifacts under `data/skill/<slug>/` separate from read-only
  source inputs under `data/deals/<slug>/source/` and `raw/<slug>/`.
