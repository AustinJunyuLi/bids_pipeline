# CLAUDE.md

This file is the authoritative agent contract for the live repository state.
Keep it short, current, and operational. When repo facts change, update this
file instead of layering on historical notes.

## What This Repo Is

This repository is a filing-grounded M&A extraction pipeline.

The live default is the v2 observation workflow:

- deterministic runtime in `skill_pipeline/`
- canonical agent workflow docs in `.claude/skills/`
- live per-deal artifacts in `data/skill/<slug>/`

If docs disagree, trust live code and tests over planning notes or historical
design docs.

## Source Of Truth

Authoritative implementation truth lives here:

- `skill_pipeline/`
- `tests/`
- `.claude/skills/`
- artifact path contracts encoded in `skill_pipeline/paths.py`

Non-authorities (post-export reference only):

- benchmark materials under `example/`
- diagnostic reviews under `diagnosis/`

`.claude/skills/` is canonical. `.codex/skills/` and `.cursor/skills/` are
mirrors and should be synced from `.claude/skills/`.

## Branch Policy

`two-pass` is the live working branch and default publication branch.

Do not push live repo updates to `main` unless the user explicitly asks for
that branch.

## Read Next

- Read `.claude/LOCAL.md` immediately after this file if it exists.
- Use `.claude/skills/deal-agent/SKILL.md` for the full clean-rerun procedure.
- Use `docs/design.md` for the compact design index.

## Live Workflow

Deterministic runtime stages:

1. `skill-pipeline source-discover --deal <slug>`
2. `skill-pipeline raw-fetch --deal <slug>`
3. `skill-pipeline preprocess-source --deal <slug>`
4. `skill-pipeline compose-prompts --deal <slug> --mode observations`
5. `/extract-deal-v2 <slug>`
6. `skill-pipeline canonicalize-v2 --deal <slug>`
7. `skill-pipeline check-v2 --deal <slug>`
8. `skill-pipeline coverage-v2 --deal <slug>`
9. `skill-pipeline gates-v2 --deal <slug>`
10. `/verify-extraction-v2 <slug>` only if deterministic findings are repairable
11. `skill-pipeline derive --deal <slug>`
12. `skill-pipeline db-load-v2 --deal <slug>`
13. `skill-pipeline db-export-v2 --deal <slug>`
14. `/reconcile-alex <slug>` only after export, as an optional diagnostic

Live local-agent skills:

- `/deal-agent`
- `/extract-deal-v2`
- `/verify-extraction-v2`
- `/reconcile-alex`

Important distinction:

- `skill-pipeline deal-agent --deal <slug>` is preflight and stage summary only.
- `/deal-agent` is the end-to-end rerun orchestration skill.

## Hard Rules

- Filing text is the only factual source of truth.
- Benchmark material is forbidden before `skill-pipeline db-export-v2 --deal <slug>` completes.
- Generation stops at the filing-grounded v2 export contract.
- `raw-fetch` and `preprocess-source` are seed-only in this worktree.
- `preprocess-source` is single-primary-document and fail-closed on supplementary candidates.
- `compose-prompts` only supports `--mode observations`.
- Canonical v2 loading requires `data/skill/<slug>/extract_v2/spans.json`.
- `check-v2`, `coverage-v2`, and `gates-v2` are blocker gates before `derive`.
- `db-load-v2` requires canonical v2 observations, derivations, and structured coverage findings.
- `db-export-v2` generates CSVs from DuckDB, not from JSON artifacts.
- `/reconcile-alex`, `example/`, `diagnosis/`, and benchmark workbooks are post-export only.
- Fail fast on missing files, schema drift, contradictory state, and invalid assumptions.

## Runtime Environment

The live Python runtime reads SEC identity from:

- `PIPELINE_SEC_IDENTITY` (preferred)
- `SEC_IDENTITY`
- `EDGAR_IDENTITY`

Use `.env.local` for machine-local tooling or editor settings only. Do not
treat `.env.local` as the Python runtime contract.

## Minimal Commands

```bash
python -m pip install -e .
python -m pytest -q

skill-pipeline raw-fetch --deal imprivata
skill-pipeline preprocess-source --deal imprivata
skill-pipeline compose-prompts --deal imprivata --mode observations
skill-pipeline canonicalize-v2 --deal imprivata
skill-pipeline check-v2 --deal imprivata
skill-pipeline coverage-v2 --deal imprivata
skill-pipeline gates-v2 --deal imprivata
skill-pipeline derive --deal imprivata
skill-pipeline db-load-v2 --deal imprivata
skill-pipeline db-export-v2 --deal imprivata

skill-pipeline deal-agent --deal imprivata

python scripts/sync_skill_mirrors.py --check
```

## Editing Safety

- Treat `data/deals/<slug>/source/` and `data/skill/<slug>/` as generated artifacts.
- Never rewrite raw filing text under `raw/<slug>/filings/`.
- Re-running `/deal-agent <slug>` rebuilds live per-deal v2 outputs under `data/skill/<slug>/`.
- Update `.claude/skills/` first when skill docs change, then sync mirrors.
- Keep this file factual and present-tense. Do not turn it back into an archive.
