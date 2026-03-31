# CLAUDE.md

This file is the authoritative instruction source for agents working in this
repository. When repository facts, artifact contracts, or action protocols
change, update this file.

## What This Repo Is

This repository is a filing-grounded M&A extraction pipeline.

The live default is the v2 observation-graph workflow:

- deterministic runtime under `skill_pipeline/`
- canonical local-agent workflow docs under `.claude/skills/`
- live per-deal outputs under `data/skill/<slug>/`
- archived v1 outputs under `data/legacy/v1/`

If docs disagree, trust live code and tests over planning notes or historical
design documents.

## Branch Policy

`two-pass` is the live working branch and the default GitHub publication branch
for this repository. Push current repo updates there unless the user explicitly
requests another branch.

`main` is not the default publication branch for the live v2 workflow. Do not
repoint `main` to `two-pass` or push live v2 updates to `main` unless the user
explicitly asks for that branch.

## Authority And Scope

Authoritative implementation truth lives here:

- `skill_pipeline/`
- `tests/`
- `.claude/skills/`
- artifact path contracts encoded in `skill_pipeline/paths.py`

Important non-authorities unless explicitly updated to match the code:

- historical references to a `pipeline/` package
- migration-era notes that still describe v1 as the live default
- benchmark materials in `example/`, `diagnosis/`, or spreadsheet workflows

`.claude/skills/` is the canonical workflow tree. `.codex/skills/` and
`.cursor/skills/` are derived mirrors and should be synced from `.claude/skills/`.

## Local Machine Notes

If `.claude/LOCAL.md` exists, read it immediately after this file before taking
action. It is a git-ignored workstation note for machine-local setup details
such as virtualenv naming, shell activation, and editor or tool integration.

Do not promote `.claude/LOCAL.md` content into repository-wide facts unless the
user explicitly wants that policy documented for everyone.

`.agents/skills/` is retired in this repo and should not be recreated.

## Runtime Split

### Live Deterministic Runtime

The live v2 default uses these `skill-pipeline` stages:

- `source-discover`: discover source filing candidates without fetching
- `raw-fetch`: fetch and freeze the seed-selected SEC filing set
- `preprocess-source`: build source artifacts from frozen filings
- `compose-prompts --contract v2 --mode observations`: build v2 observation extraction packets
- `canonicalize-v2`: resolve quote-first v2 observations to canonical span-backed artifacts
- `check-v2`: structural validation for canonical v2 observations
- `coverage-v2`: deterministic source-coverage audit for canonical v2 observations
- `gates-v2`: semantic validation for canonical v2 observations
- `derive`: deterministic derivation from literal observations to analyst rows
- `db-load-v2`: load canonical v2 artifacts into DuckDB `v2_*` tables
- `db-export-v2`: generate the live v2 triple export surface
- `deal-agent`: preflight and artifact summary only

### Legacy Deterministic Runtime

These commands still exist for explicit legacy use only:

- `compose-prompts` with the default v1 contract
- `canonicalize`
- `check`
- `verify`
- `coverage`
- `gates`
- `enrich-core`
- `db-load`
- `db-export`
- `migrate-extract-v1-to-v2` as a historical backfill bridge only

### Local-Agent Stages

Live v2 default skills:

- `/deal-agent`
- `/extract-deal-v2`
- `/verify-extraction-v2`
- `/reconcile-alex`

Legacy-only skills:

- `/deal-agent-legacy`
- `/extract-deal`
- `/verify-extraction`
- `/enrich-deal`
- `/reconcile-alex-legacy`

### Important Name Collision

`skill-pipeline deal-agent --deal <slug>` is not the end-to-end orchestrator.
It only verifies required inputs, ensures output directories exist, and prints a
status summary.

The full rerun workflow lives in the local-agent skill documentation for
`/deal-agent`. That skill owns the clean v2 rerun procedure.

## Repository Layout

- `skill_pipeline/`: deterministic runtime package
- `raw/<slug>/`: frozen filing ingress and manifests
- `data/deals/<slug>/source/`: shared source artifacts derived from raw filings
- `data/skill/<slug>/`: live v2 prompts, observations, validation, derivations, and exports
- `data/legacy/v1/`: archived v1 skill artifacts plus the pre-cutover DuckDB file
- `tests/`: regression tests for runtime stages and doc contracts
- `.claude/skills/`: canonical local-agent workflow instructions
- `docs/`: design notes and specs; useful, but not automatically authoritative

## Artifact Contract

### Seed Input

- `data/seeds.csv`: authoritative deal roster and seed URLs

### Raw Fetch Outputs

`skill-pipeline raw-fetch --deal <slug>` writes:

- `raw/<slug>/discovery.json`
- `raw/<slug>/document_registry.json`
- `raw/<slug>/filings/*.txt`
- raw HTML and markdown mirrors when available

Raw filing text under `raw/` is immutable truth input. Never rewrite it.

### Source Preprocess Outputs

`skill-pipeline preprocess-source --deal <slug>` currently enforces a seed-only,
single-primary-document contract. It requires:

- exactly one primary candidate
- zero supplementary candidates
- exactly one frozen document in `document_registry.json`

It writes:

- `data/deals/<slug>/source/chronology_selection.json`
- `data/deals/<slug>/source/chronology_blocks.jsonl`
- `data/deals/<slug>/source/evidence_items.jsonl`
- `data/deals/<slug>/source/chronology.json`
- `data/deals/<slug>/source/filings/*`

It also removes stale `source/supplementary_snippets.jsonl`. That file is not a
current preprocess output in this worktree.

### Live Prompt Packet Outputs

`skill-pipeline compose-prompts --deal <slug> --contract v2 --mode observations`
writes:

- `data/skill/<slug>/prompt_v2/manifest.json`
- `data/skill/<slug>/prompt_v2/packets/<packet-id>/prefix.md`
- `data/skill/<slug>/prompt_v2/packets/<packet-id>/body.md`
- `data/skill/<slug>/prompt_v2/packets/<packet-id>/rendered.md`

This contract instructs the LLM to emit quote-first `quotes`, `parties`,
`cohorts`, and the 6 literal observation subtypes. It must not emit analyst
rows.

### Legacy Prompt Packet Outputs

The legacy v1 prompt surface remains available under `data/skill/<slug>/prompt/`
for `/deal-agent-legacy`, `/extract-deal`, `/verify-extraction`, and
`/enrich-deal`. Those outputs are no longer the live default.

### Live Extract Outputs

`/extract-deal-v2 <slug>` writes:

- `data/skill/<slug>/extract_v2/observations_raw.json`

`skill-pipeline canonicalize-v2 --deal <slug>` writes:

- `data/skill/<slug>/extract_v2/observations.json`
- `data/skill/<slug>/extract_v2/spans.json`

### Live Validation Outputs

- `data/skill/<slug>/check_v2/check_report.json`
- `data/skill/<slug>/coverage_v2/coverage_findings.json`
- `data/skill/<slug>/coverage_v2/coverage_summary.json`
- `data/skill/<slug>/gates_v2/gates_report.json`

### Live Derivation Outputs

`skill-pipeline derive --deal <slug>` writes:

- `data/skill/<slug>/derive/derivations.json`
- `data/skill/<slug>/derive/derive_log.json`

### Live DuckDB And Export Outputs

`skill-pipeline db-load-v2 --deal <slug>` writes into:

- `data/pipeline.duckdb`

The live database is the v2 cutover database. It is rebuilt from v2 artifacts
and populated with:

- `v2_parties`
- `v2_cohorts`
- `v2_observations`
- `v2_derivations`
- `v2_coverage_checks`

`skill-pipeline db-export-v2 --deal <slug>` writes:

- `data/skill/<slug>/export_v2/literal_observations.csv`
- `data/skill/<slug>/export_v2/analyst_rows.csv`
- `data/skill/<slug>/export_v2/benchmark_rows_expanded.csv`

### Legacy Archive Outputs

The v1 cutover archive lives here:

- `data/legacy/v1/README.md`
- `data/legacy/v1/archive_manifest.json`
- `data/legacy/v1/pipeline_precutover.duckdb`
- `data/legacy/v1/skill/<slug>/{canonicalize,check,coverage,enrich,export,extract,gates,prompt,verify}/...`
- `data/legacy/v1/skill/<slug>/reconcile/alex_rows_codex_blind_round2.json`
- `data/legacy/v1/skill/<slug>/reconcile/reconciliation_report_codex_blind_round2.json`

Legacy v1 artifacts should not be written back into the live `data/skill/<slug>/`
surface.

## End-To-End Flow

```text
data/seeds.csv
  -> skill-pipeline raw-fetch --deal <slug>
  -> raw/<slug>/*
  -> skill-pipeline preprocess-source --deal <slug>
  -> data/deals/<slug>/source/*
  -> skill-pipeline compose-prompts --deal <slug> --contract v2 --mode observations
  -> data/skill/<slug>/prompt_v2/*
  -> /extract-deal-v2 <slug>
  -> data/skill/<slug>/extract_v2/observations_raw.json
  -> skill-pipeline canonicalize-v2 --deal <slug>
  -> skill-pipeline check-v2 --deal <slug>
  -> skill-pipeline coverage-v2 --deal <slug>
  -> skill-pipeline gates-v2 --deal <slug>
  -> /verify-extraction-v2 <slug>   (only if deterministic findings are repairable)
  -> skill-pipeline derive --deal <slug>
  -> skill-pipeline db-load-v2 --deal <slug>
  -> skill-pipeline db-export-v2 --deal <slug>
  -> /reconcile-alex <slug>         (optional post-export diagnostic)
```

The v1 enrich/repair/export flow is preserved only under `/deal-agent-legacy`.

## Hard Invariants

- Filing text is the only factual source of truth.
- Benchmark materials are forbidden until `skill-pipeline db-export-v2 --deal <slug>` completes.
- `raw-fetch` and `preprocess-source` are seed-only in this worktree.
- `preprocess-source` is currently single-primary-document and fail-closed on supplementary candidates.
- `skill-pipeline deal-agent` is summary/preflight only.
- Canonical v2 loading requires `extract_v2/spans.json`; missing sidecars are an error.
- `check-v2`, `coverage-v2`, and `gates-v2` are blocker gates before `derive`.
- `db-load-v2` requires canonical v2 observations, derivations, and structured coverage findings.
- `db-export-v2` generates CSVs from DuckDB, not from JSON artifacts.
- `migrate-extract-v1-to-v2` is historical migration support only; it is not the live extraction path.
- Fail fast on missing files, schema drift, contradictory state, and invalid assumptions.

## Benchmark Boundary

Benchmark material is post-export only.

Do not consult any of the following before
`skill-pipeline db-export-v2 --deal <slug>` completes:

- `example/`
- `diagnosis/`
- benchmark workbooks or benchmark notes
- `data/skill/<slug>/reconcile/*`
- `/reconcile-alex`

Generation stops at the filing-grounded v2 export contract. Benchmark
comparison is diagnostic only and must never become a hidden generation
requirement.

Legacy benchmark work under `/reconcile-alex-legacy` follows the same principle
but uses the legacy `db-export` boundary.

## Environment Variables

The live Python runtime currently reads only EDGAR identity variables for SEC
access:

- `PIPELINE_SEC_IDENTITY`
- `SEC_IDENTITY`
- `EDGAR_IDENTITY`

Use `PIPELINE_SEC_IDENTITY` as the preferred setting when present.

Keep `.env.local` for machine-local tooling, editor, or agent config only. Do
not treat `.env.local` as the Python runtime contract.

Do not document provider API keys or provider/model selector variables here as
repository runtime facts. Agent-specific credentials, editor integrations, and
external tool setup live outside the Python package contract.

## Build, Test, And Development Commands

```bash
uv python install 3.13
uv venv --python 3.13 --managed-python --seed <local-venv-dir>
# activate according to your host shell or local workstation note

python -m pip install -e .
python -m pytest -q

skill-pipeline raw-fetch --deal imprivata
skill-pipeline preprocess-source --deal imprivata
skill-pipeline compose-prompts --deal imprivata --contract v2 --mode observations
skill-pipeline canonicalize-v2 --deal imprivata
skill-pipeline check-v2 --deal imprivata
skill-pipeline coverage-v2 --deal imprivata
skill-pipeline gates-v2 --deal imprivata
skill-pipeline derive --deal imprivata
skill-pipeline db-load-v2 --deal imprivata
skill-pipeline db-export-v2 --deal imprivata

skill-pipeline deal-agent --deal imprivata

python scripts/archive_v1_cutover.py
python scripts/sync_skill_mirrors.py
python scripts/sync_skill_mirrors.py --check
```

## Editing And Safety Rules For Repo Artifacts

- Treat `raw/`, `data/deals/<slug>/source/`, `data/skill/<slug>/`, and `data/legacy/v1/` as generated or archived artifacts. Edit only intentionally and document why.
- Re-running `/deal-agent <slug>` deletes live per-deal v2 outputs under `data/skill/<slug>/` and rebuilds them from scratch. `raw/<slug>/` is preserved.
- `/deal-agent <slug>` must not delete or rewrite `data/legacy/v1/`.
- Never rewrite raw filing text under `raw/<slug>/filings/`.
- When skill docs change, update `.claude/skills/` first, then sync mirrors.
- Keep repo documentation factual. Do not write future architecture into this file as if it already exists.

## Coding Style And Testing

Target Python 3.11+ with explicit types on public functions. Follow the
existing Pydantic-first schema style and use `snake_case` for Python names and
JSON keys. No formatter is configured in `pyproject.toml`; match surrounding
style.

Add focused regression tests for behavior changes, especially around:

- source selection and preprocessing
- canonicalization and span resolution
- deterministic validation and derivation
- DuckDB load/export cutover behavior
- skill mirror sync and doc boundary policy

## Commit Guidance

Use concise imperative commit subjects. Conventional prefixes such as `feat:`,
`fix:`, `docs:`, and `test:` match recent history.

When behavior changes, document:

- affected deal slug or stage
- commands run
- artifact contract changes
- whether outputs were regenerated or archived

## Agent Working Rules

1. Think from first principles. Do not assume the user has perfectly specified the true objective.
2. Solve the real problem, not the symptom.
3. Do not overengineer. Use the shortest correct path.
4. Do not expand scope.
5. Fail fast on violated assumptions, invalid states, unexpected inputs, schema mismatches, missing required data, and logic inconsistencies.
6. Protect logical correctness. Validate the full end-to-end logic before changing code.
7. Write complete Python code. No pseudocode. No TODO placeholders for core behavior.
8. Research and pipeline safety. Do not silently alter semantics, schemas, event definitions, sample construction, or output meaning.
9. Prefer the simplest robust design that satisfies the requirement.
