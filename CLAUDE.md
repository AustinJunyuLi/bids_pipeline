# CLAUDE.md

This file is the authoritative instruction source for agents working in this
repository. When repository facts, artifact contracts, or action protocols
change, update this file.

## What This Repo Is

This repository is a filing-grounded M&A extraction pipeline.

It has two distinct parts:

- `skill_pipeline/`: the only active Python package and the only installed CLI
  in this worktree
- local-agent workflow documents under `.claude/skills/`: the canonical
  instructions for extraction, repair, and interpretive enrichment

LLM-driven stages are orchestrated by a local agent working against repository artifacts
and skill instructions. Keep that orchestration agent-agnostic.

If docs disagree, trust live code and tests over planning notes or historical
design documents.

## Authority And Scope

Authoritative implementation truth lives here:

- `skill_pipeline/`
- `tests/`
- `.claude/skills/`
- artifact path contracts encoded in `skill_pipeline/paths.py`

Important non-authorities unless explicitly updated to match the code:

- historical references to a `pipeline/` package
- provider-specific LLM infrastructure notes from older design work
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

### Deterministic Python Runtime

The `skill-pipeline` CLI owns these stages:

- `source-discover`: discover source filing candidates without fetching
- `raw-fetch`: fetch and freeze the seed-selected SEC filing set
- `preprocess-source`: build source artifacts from frozen filings
- `compose-prompts`: build provider-neutral prompt packet artifacts from source
- `migrate-extract-v1-to-v2`: bootstrap quote-first v2 observation artifacts
  from canonical v1 extract artifacts during migration
- `canonicalize`: upgrade extract artifacts into canonical span-backed form
- `check`: structural blocker gate
- `verify`: strict deterministic verification
- `coverage`: deterministic source-coverage audit
- `gates`: semantic validation (temporal consistency, cross-event logic, actor lifecycle, attention decay)
- `enrich-core`: deterministic enrichment
- `db-load`: load canonical extract + enrichment artifacts into DuckDB
- `db-export`: generate `deal_events.csv` from DuckDB queries
- `db-load-v2`: load canonical v2 observations, derivations, and structured coverage into additive DuckDB tables
- `db-export-v2`: generate the v2 triple export surface from DuckDB queries
- `deal-agent`: preflight and artifact summary only

### Local-Agent Stages

These stages are not implemented as Python-side provider wrappers:

- `/extract-deal`
- `/extract-deal-v2`
- `/verify-extraction`
- `/verify-extraction-v2`
- `/enrich-deal`
- `/reconcile-alex` (optional, post-export only)

The local agent reads and writes repo artifacts directly, following the
canonical skill docs.

### Important Name Collision

`skill-pipeline deal-agent --deal <slug>` is not the end-to-end orchestrator.
It only verifies required inputs, ensures output directories exist, and prints a
status summary.

The full end-to-end orchestration flow lives in the local-agent skill
documentation for `/deal-agent`. It covers fetch, preprocess, extraction,
gates, enrichment, and DuckDB export with idempotent re-run support.

## Repository Layout

- `skill_pipeline/`: deterministic runtime package
- `raw/<slug>/`: frozen filing ingress and manifests
- `data/deals/<slug>/source/`: shared source artifacts derived from raw filings
- `data/skill/<slug>/`: extract, QA, enrichment, and export artifacts
- `data/skill/<slug>/{extract_v2,check_v2,coverage_v2,gates_v2,derive,export_v2,prompt_v2}/`: additive v2 artifact locations reserved in `SkillPathSet`; they do not replace the live v1 surfaces
- `tests/`: regression tests for runtime stages
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

### Prompt Packet Outputs

`skill-pipeline compose-prompts --deal <slug>` writes:

- `data/skill/<slug>/prompt/manifest.json`
- `data/skill/<slug>/prompt/packets/<packet-id>/prefix.md`
- `data/skill/<slug>/prompt/packets/<packet-id>/body.md`
- `data/skill/<slug>/prompt/packets/<packet-id>/rendered.md`

Use `--mode actors` before `/extract-deal` for actor extraction packets. After
actor extraction creates `actors_raw.json`, rerun with `--mode events` for the
event extraction pass. `--mode all` is only the actor-packet shortcut; event
packets still require the separate `--mode events` call.

`skill-pipeline compose-prompts --deal <slug> --contract v2 --mode observations`
writes:

- `data/skill/<slug>/prompt_v2/manifest.json`
- `data/skill/<slug>/prompt_v2/packets/<packet-id>/prefix.md`
- `data/skill/<slug>/prompt_v2/packets/<packet-id>/body.md`
- `data/skill/<slug>/prompt_v2/packets/<packet-id>/rendered.md`

This v2 contract instructs the LLM to emit quote-first `parties`, `cohorts`,
and the 6 observation subtypes. It must not emit analyst rows.

### Extract Outputs

`/extract-deal <slug>` writes:

- `data/skill/<slug>/extract/actors_raw.json`
- `data/skill/<slug>/extract/events_raw.json`

These start as legacy extraction artifacts using `evidence_refs`.

`/extract-deal-v2 <slug>` writes:

- `data/skill/<slug>/extract_v2/observations_raw.json`

During the Phase 16 migration window, `skill-pipeline migrate-extract-v1-to-v2
--deal <slug>` is the deterministic bridge that bootstraps this quote-first v2
artifact from canonical v1 extract outputs when a native v2 LLM pass is not yet
available.

### Canonical Extract Outputs

`skill-pipeline canonicalize --deal <slug>` upgrades extraction artifacts in
place. It:

- rewrites `actors_raw.json` and `events_raw.json` into canonical span-backed
  form
- writes `data/skill/<slug>/extract/spans.json`
- writes `data/skill/<slug>/canonicalize/canonicalize_log.json`

Do not document the canonical extract contract as `actors.json` or
`events.json`. The live filenames are still `actors_raw.json` and
`events_raw.json`.

### Additive v2 Path Surface

Phase 11 registers additive v2 artifact paths in `SkillPathSet` and
`ensure_output_directories()`. These locations are reserved beside the live v1
surfaces; Phase 11 does not imply that all corresponding runtime writers exist
yet.

- `data/skill/<slug>/extract_v2/observations_raw.json`
- `data/skill/<slug>/extract_v2/observations.json`
- `data/skill/<slug>/extract_v2/spans.json`
- `data/skill/<slug>/check_v2/check_report.json`
- `data/skill/<slug>/coverage_v2/coverage_findings.json`
- `data/skill/<slug>/coverage_v2/coverage_summary.json`
- `data/skill/<slug>/gates_v2/gates_report.json`
- `data/skill/<slug>/derive/derivations.json`
- `data/skill/<slug>/derive/derive_log.json`
- `data/skill/<slug>/export_v2/literal_observations.csv`
- `data/skill/<slug>/export_v2/analyst_rows.csv`
- `data/skill/<slug>/export_v2/benchmark_rows_expanded.csv`
- `data/skill/<slug>/prompt_v2/manifest.json`
- `data/skill/<slug>/prompt_v2/packets/*`

The existing `extract/`, `check/`, `coverage/`, `gates/`, `enrich/`, `export/`,
and `prompt/` contracts remain unchanged.

`skill-pipeline canonicalize-v2 --deal <slug>` is now the live writer for the
canonical v2 observation surface. It reads `extract_v2/observations_raw.json`
when present, writes `extract_v2/observations.json`, and writes
`extract_v2/spans.json`. The v1 `canonicalize` command and `extract/` contract
remain unchanged.

`skill-pipeline check-v2 --deal <slug>` is now the live structural gate for the
canonical v2 observation surface. It writes
`data/skill/<slug>/check_v2/check_report.json`.

`skill-pipeline coverage-v2 --deal <slug>` is now the live structured coverage
audit for the canonical v2 observation surface. It writes
`data/skill/<slug>/coverage_v2/coverage_findings.json` and
`data/skill/<slug>/coverage_v2/coverage_summary.json`.

`skill-pipeline gates-v2 --deal <slug>` is now the live semantic validation
gate for the canonical v2 observation surface. It writes
`data/skill/<slug>/gates_v2/gates_report.json`.

`skill-pipeline derive --deal <slug>` is now the live deterministic derivation
stage for the canonical v2 observation surface. It writes
`data/skill/<slug>/derive/derivations.json` and
`data/skill/<slug>/derive/derive_log.json`.

`skill-pipeline db-load-v2 --deal <slug>` is now the live additive DuckDB
loader for canonical v2 artifacts. It populates `data/pipeline.duckdb` tables
`v2_parties`, `v2_cohorts`, `v2_observations`, `v2_derivations`, and
`v2_coverage_checks`.

`skill-pipeline db-export-v2 --deal <slug>` is now the live additive v2 export
stage. It writes:

- `data/skill/<slug>/export_v2/literal_observations.csv`
- `data/skill/<slug>/export_v2/analyst_rows.csv`
- `data/skill/<slug>/export_v2/benchmark_rows_expanded.csv`

### Deterministic QA And Enrichment Outputs

- `data/skill/<slug>/check/check_report.json`
- `data/skill/<slug>/verify/verification_findings.json`
- `data/skill/<slug>/verify/verification_log.json`
- `data/skill/<slug>/coverage/coverage_findings.json`
- `data/skill/<slug>/coverage/coverage_summary.json`
- `data/skill/<slug>/enrich/deterministic_enrichment.json`

`coverage_findings.json` is a structured detail artifact. Its emitted findings
use `CoverageCheckRecord` entries with `status`, `reason_code`, and supporting
IDs; free-text `coverage_notes` is not the live coverage-output contract for
that artifact.

### Semantic Gate Outputs

`skill-pipeline gates --deal <slug>` writes:

- `data/skill/<slug>/gates/gates_report.json`

The gate report contains semantic findings (temporal consistency, cross-event
logic, actor lifecycle coverage) and an optional attention decay diagnostic.
Gates run after coverage and before enrich-core. Enrich-core refuses to run if
gates have blocker findings.

### DuckDB Database

`skill-pipeline db-load --deal <slug>` writes deal data into:

- `data/pipeline.duckdb`

Tables: `actors`, `events`, `spans`, `enrichment`, `cycles`, `rounds`. The
database is a single multi-deal file keyed by `(deal_slug, <entity_id>)`.

`skill-pipeline db-load-v2 --deal <slug>` writes into the same
`data/pipeline.duckdb` file but only touches additive `v2_*` tables:
`v2_parties`, `v2_cohorts`, `v2_observations`, `v2_derivations`, and
`v2_coverage_checks`.

`db-load` uses two-tier enrichment loading:

- `deterministic_enrichment.json` (required) -- bid classifications, rounds, cycles, dropout_classifications (sparse DropTarget), all_cash_overrides
- `enrichment.json` (required) -- interpretive layer with exactly 5 top-level keys: dropout_classifications, initiation_judgment, advisory_verification, count_reconciliation, review_flags

`skill-pipeline db-export --deal <slug>` writes:

- `data/skill/<slug>/export/deal_events.csv`

The CSV is generated from DuckDB queries, not from JSON artifacts.

`skill-pipeline db-export-v2 --deal <slug>` writes:

- `data/skill/<slug>/export_v2/literal_observations.csv`
- `data/skill/<slug>/export_v2/analyst_rows.csv`
- `data/skill/<slug>/export_v2/benchmark_rows_expanded.csv`

The v2 exporter also reads from DuckDB, not from JSON artifacts. The
`skill_pipeline/legacy_adapter.py` module is the benchmark-compatibility helper
that maps v2 analyst rows back to the existing 14-column v1 CSV shape; it does
not replace `db-export`.

## End-To-End Flow

```text
data/seeds.csv
  -> skill-pipeline source-discover --deal <slug>     (optional)
  -> skill-pipeline raw-fetch --deal <slug>
  -> raw/<slug>/*
  -> skill-pipeline preprocess-source --deal <slug>
  -> data/deals/<slug>/source/*
  -> skill-pipeline compose-prompts --deal <slug>
  -> data/skill/<slug>/prompt/*
  -> /extract-deal <slug>
  -> data/skill/<slug>/extract/{actors_raw,events_raw}.json
  -> skill-pipeline canonicalize --deal <slug>
  -> skill-pipeline check --deal <slug>
  -> skill-pipeline verify --deal <slug>
  -> skill-pipeline coverage --deal <slug>
  -> skill-pipeline gates --deal <slug>
  -> /verify-extraction <slug>        (only if deterministic findings are repairable)
  -> skill-pipeline enrich-core --deal <slug>
  -> /enrich-deal <slug>              (mandatory interpretive enrichment)
  -> skill-pipeline db-load --deal <slug>
  -> skill-pipeline db-export --deal <slug>
  -> /reconcile-alex <slug>           (optional post-export diagnostic)
```

## Hard Invariants

- Filing text is the only factual source of truth.
- Benchmark materials are forbidden until `skill-pipeline db-export --deal <slug>`
  completes.
- `raw-fetch` and `preprocess-source` are seed-only in this worktree.
- `preprocess-source` is currently single-primary-document and fail-closed on
  supplementary candidates.
- `skill-pipeline deal-agent` is summary/preflight only.
- Canonical extract loading requires `spans.json`; missing sidecars are an
  error.
- `check`, `verify`, and `coverage` are blocker gates before `enrich-core`.
- `gates` is a blocker gate before `enrich-core`. Semantic findings with
  severity `blocker` prevent enrichment.
- `db-load` requires canonical extract artifacts with `spans.json`,
  `deterministic_enrichment.json`, and `enrichment.json`. It refuses
  quote-first or incomplete data.
- `enrichment.json` is interpretive-only and must contain all 5 required
  top-level keys. Deterministic bid classifications, rounds, cycles, formal
  boundary, sparse `DropTarget` labels, and all-cash overrides remain owned by
  `deterministic_enrichment.json`.
- `db-export` generates CSV from DuckDB, not JSON artifacts. It is the only
  filing-grounded export boundary in this worktree.
- `verify` only treats `EXACT` and `NORMALIZED` quote matches as passing.
  `FUZZY` does not pass.
- Fail fast on missing files, schema drift, contradictory state, and invalid
  assumptions. Do not add silent fallbacks.
- Do not infer runtime architecture from stale docs or unused dependency ideas.
  This repo's LLM-facing behavior is local-agent orchestration, not a Python
  provider layer.

## Benchmark Boundary

Benchmark material is post-export only.

Do not consult any of the following before
`skill-pipeline db-export --deal <slug>` completes:

- `example/`
- `diagnosis/`
- benchmark workbooks or benchmark notes
- `data/skill/<slug>/reconcile/*`
- `/reconcile-alex`

Generation stops at the filing-grounded export contract. Benchmark comparison is
diagnostic only and must never become a hidden generation requirement.

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

skill-pipeline source-discover --deal imprivata
skill-pipeline raw-fetch --deal imprivata
skill-pipeline preprocess-source --deal imprivata

skill-pipeline compose-prompts --deal imprivata --mode actors
# after actor extraction creates actors_raw.json:
skill-pipeline compose-prompts --deal imprivata --mode events

skill-pipeline canonicalize --deal imprivata
skill-pipeline check --deal imprivata
skill-pipeline verify --deal imprivata
skill-pipeline coverage --deal imprivata
skill-pipeline gates --deal imprivata
skill-pipeline enrich-core --deal imprivata
skill-pipeline db-load --deal imprivata
skill-pipeline db-export --deal imprivata

skill-pipeline deal-agent --deal imprivata

python scripts/sync_skill_mirrors.py
python scripts/sync_skill_mirrors.py --check
```

## Editing And Safety Rules For Repo Artifacts

- Treat `raw/`, `data/deals/<slug>/source/`, and `data/skill/<slug>/` as
  generated artifacts. Edit only intentionally and document why.
- Re-running `/deal-agent <slug>` deletes `data/skill/<slug>/` and
  `data/deals/<slug>/source/` then rebuilds from scratch. `raw/<slug>/` is
  preserved (immutable content from EDGAR).
- Never rewrite raw filing text under `raw/<slug>/filings/`.
- When skill docs change, update `.claude/skills/` first, then sync mirrors.
- Keep repo documentation factual. Do not write future architecture into this
  file as if it already exists.

## Coding Style And Testing

Target Python 3.11+ with explicit types on public functions. Follow the
existing Pydantic-first schema style and use `snake_case` for Python names and
JSON keys. No formatter is configured in `pyproject.toml`; match surrounding
style.

Add focused regression tests for behavior changes, especially around:

- source selection and preprocessing
- canonicalization and span resolution
- deterministic verification and coverage
- enrich-core gating

## Commit Guidance

Use concise imperative commit subjects. Conventional prefixes such as `feat:`,
`fix:`, and `test:` match recent history.

When behavior changes, document:

- affected deal slug or stage
- commands run
- artifact contract changes
- whether outputs were regenerated

## Agent Working Rules

1. Think from first principles. Do not assume the user has perfectly specified
   the true objective. Start from the underlying need and the actual problem.
   If the objective, constraints, interfaces, or success criteria are
   materially unclear, ask focused clarification questions.

2. Solve the real problem, not the symptom. Do not give patch-style,
   workaround-style, or compatibility-first solutions when the correct fix is
   structural.

3. Do not overengineer. Use the shortest correct path. Do not add speculative
   abstractions, future-proofing, fallback systems, downgrade paths, optional
   modes, or extra branches unless explicitly requested.

4. Do not expand scope. Only solve the requirement that was asked for. Do not
   invent adjacent features or extras.

5. Fail fast. Fail fast on violated assumptions, invalid states, unexpected
   inputs, schema mismatches, missing required data, and logic inconsistencies.
   Do not silence errors. Do not swallow exceptions. Do not use broad
   `try/except` blocks that hide failures. Do not substitute defaults, empty
   outputs, partial success, fallback behavior, retries, or log-and-continue
   behavior unless explicitly requested.

6. Protect logical correctness. Before proposing or writing code, validate the
   full end-to-end logic: inputs, transformations, outputs, edge cases, failure
   paths, and side effects.

7. Write complete Python code. No pseudocode. No TODO placeholders for core
   behavior. Prefer explicitness, clear naming, input validation, deterministic
   behavior, and strong error handling.

8. Research and pipeline safety. Do not silently alter semantics, schemas,
   event definitions, sample construction, or output meaning. Do not silently
   drop malformed data. If a step could change results, surface it explicitly.
   Default policy: abort on the first materially relevant error.

9. Prefer the simplest robust design that satisfies the requirement. Follow
   KISS and DRY. If proposing alternatives, state the preferred option, degree
   of confidence, and rationale before changing code.
