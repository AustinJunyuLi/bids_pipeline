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
  instructions for extraction, repair, interpretive enrichment, and export

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

## Runtime Split

### Deterministic Python Runtime

The `skill-pipeline` CLI owns these stages:

- `source-discover`: discover source filing candidates without fetching
- `raw-fetch`: fetch and freeze the seed-selected SEC filing set
- `preprocess-source`: build source artifacts from frozen filings
- `compose-prompts`: build provider-neutral prompt packet artifacts from source
- `canonicalize`: upgrade extract artifacts into canonical span-backed form
- `check`: structural blocker gate
- `verify`: strict deterministic verification
- `coverage`: deterministic source-coverage audit
- `enrich-core`: deterministic enrichment
- `deal-agent`: preflight and artifact summary only

### Local-Agent Stages

These stages are not implemented as Python-side provider wrappers:

- `/extract-deal`
- `/verify-extraction`
- `/enrich-deal`
- `/export-csv`
- `/reconcile-alex` (optional, post-export only)

The local agent reads and writes repo artifacts directly, following the
canonical skill docs.

### Important Name Collision

`skill-pipeline deal-agent --deal <slug>` is not the end-to-end orchestrator.
It only verifies required inputs, ensures output directories exist, and prints a
status summary.

The thin end-to-end orchestration flow lives in the local-agent skill
documentation for `/deal-agent`.

## Repository Layout

- `skill_pipeline/`: deterministic runtime package
- `raw/<slug>/`: frozen filing ingress and manifests
- `data/deals/<slug>/source/`: shared source artifacts derived from raw filings
- `data/skill/<slug>/`: extract, QA, enrichment, and export artifacts
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

Use `--mode actors` for actor extraction packets, `--mode events` for event
extraction packets (requires `actors_raw.json`), or `--mode all` for actor
packets only (event packets require a separate call after actor extraction).

### Extract Outputs

`/extract-deal <slug>` writes:

- `data/skill/<slug>/extract/actors_raw.json`
- `data/skill/<slug>/extract/events_raw.json`

These start as legacy extraction artifacts using `evidence_refs`.

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

### Deterministic QA And Enrichment Outputs

- `data/skill/<slug>/check/check_report.json`
- `data/skill/<slug>/verify/verification_findings.json`
- `data/skill/<slug>/verify/verification_log.json`
- `data/skill/<slug>/coverage/coverage_findings.json`
- `data/skill/<slug>/coverage/coverage_summary.json`
- `data/skill/<slug>/enrich/deterministic_enrichment.json`

Optional later-stage artifacts written by local-agent workflows:

- `data/skill/<slug>/enrich/enrichment.json`
- `data/skill/<slug>/export/deal_events.csv`

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
  -> /verify-extraction <slug>        (only if deterministic findings are repairable)
  -> skill-pipeline enrich-core --deal <slug>
  -> /enrich-deal <slug>              (optional interpretive layer)
  -> /export-csv <slug>
  -> /reconcile-alex <slug>           (optional post-export diagnostic)
```

## Hard Invariants

- Filing text is the only factual source of truth.
- Benchmark materials are forbidden until `/export-csv` completes.
- `raw-fetch` and `preprocess-source` are seed-only in this worktree.
- `preprocess-source` is currently single-primary-document and fail-closed on
  supplementary candidates.
- `skill-pipeline deal-agent` is summary/preflight only.
- Canonical extract loading requires `spans.json`; missing sidecars are an
  error.
- `check`, `verify`, and `coverage` are blocker gates before `enrich-core`.
- `verify` only treats `EXACT` and `NORMALIZED` quote matches as passing.
  `FUZZY` does not pass.
- Fail fast on missing files, schema drift, contradictory state, and invalid
  assumptions. Do not add silent fallbacks.
- Do not infer runtime architecture from stale docs or unused dependency ideas.
  This repo's LLM-facing behavior is local-agent orchestration, not a Python
  provider layer.

## Benchmark Boundary

Benchmark material is post-export only.

Do not consult any of the following before `/export-csv` completes:

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

Do not document provider API keys or provider/model selector variables here as
repository runtime facts. Agent-specific credentials, editor integrations, and
external tool setup live outside the Python package contract.

## Build, Test, And Development Commands

```bash
uv python install 3.13
uv venv --python 3.13 --managed-python --seed .venv
.\.venv\Scripts\Activate.ps1

python -m pip install -e .
python -m pytest -q

skill-pipeline source-discover --deal imprivata
skill-pipeline raw-fetch --deal imprivata
skill-pipeline preprocess-source --deal imprivata

skill-pipeline compose-prompts --deal imprivata

skill-pipeline canonicalize --deal imprivata
skill-pipeline check --deal imprivata
skill-pipeline verify --deal imprivata
skill-pipeline coverage --deal imprivata
skill-pipeline enrich-core --deal imprivata

skill-pipeline deal-agent --deal imprivata

python scripts/sync_skill_mirrors.py
python scripts/sync_skill_mirrors.py --check
```

## Editing And Safety Rules For Repo Artifacts

- Treat `raw/`, `data/deals/<slug>/source/`, and `data/skill/<slug>/` as
  generated artifacts. Edit only intentionally and document why.
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
