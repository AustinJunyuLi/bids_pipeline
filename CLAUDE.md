# CLAUDE.md

This file is the authoritative instruction source for agents working in this repository. If repository memories or action protocols change, update this file rather than older notes.

## What This Is

This repository now has one active production pipeline: `skill_pipeline/`. It is the Python-native runtime for filing-grounded SEC deal extraction, verification, enrichment, CSV export, and post-export benchmark QA. The old hybrid agent workflow and the deleted `pipeline/` package are archival history only.

The only production runner is `skill-pipeline run --deal <slug>`. Reconciliation is deliberately outside the pipeline and stays as `python scripts/reconcile_alex.py --deal <slug>` after export.

## Repository Map

- `skill_pipeline/cli.py` is the stable production CLI entrypoint.
- `skill_pipeline/core/` contains path helpers, config, prompts, provenance, seeds, artifact loading, and the LLM wrapper.
- `skill_pipeline/stages/` contains executable pipeline stages, grouped into `raw/`, `preprocess/`, `qa/`, and `enrich/`.
- `skill_pipeline/schemas/` contains runtime and filing/source schemas.
- `skill_pipeline/source/` contains source-text processing helpers.
- `skill_pipeline/normalize/` contains deterministic normalization helpers.
- `scripts/` contains standalone operational scripts, including post-production reconciliation and backend load testing.
- `tests/` contains regression coverage for the runtime, CLI, docs boundaries, and the standalone scripts.
- `data/skill/<slug>/` holds skill-pipeline artifacts.
- `data/deals/<slug>/source/` and `raw/<slug>/` hold read-only upstream inputs.
- `docs/` holds active operator docs, reference docs, and archival design material.
- `diagnosis/` holds review bundles and generated probes.

If a document or note still describes `/extract-deal`, `/verify-extraction`, `/enrich-deal`, `/export-csv`, or `/reconcile-alex` as active production entrypoints, treat that as archival unless it explicitly says it is a standalone post-production diagnostic.

## Documentation Precedence

- `CLAUDE.md` is the operator contract for this repository.
- `docs/HOME_COMPUTER_SETUP.md` is the short local-setup companion.
- `docs/design.md` is a lightweight index to the live runtime, not a runbook.
- `docs/plans/`, `docs/superpowers/`, `quality_reports/`, `diagnosis/`, and `example/` are historical, diagnostic, or benchmark-reference material. They may describe prior designs or audits and must not override the production contract in this file.

## Build, Test, and Development Commands

```bash
# Install package and CLI entrypoints in editable mode
pip install -e .

# Run the full test suite
pytest -q

# Focused skill runtime tests
pytest -q tests/test_skill_pipeline.py
pytest -q tests/test_skill_run.py

# Standalone production pipeline for a deal
skill-pipeline raw-fetch --deal imprivata
skill-pipeline preprocess-source --deal imprivata
skill-pipeline run --deal imprivata

# Individual production stages
skill-pipeline extract --deal imprivata
skill-pipeline materialize --deal imprivata
skill-pipeline check --deal imprivata
skill-pipeline verify --deal imprivata
skill-pipeline coverage --deal imprivata
skill-pipeline omission-audit --deal imprivata
skill-pipeline repair --deal imprivata
skill-pipeline enrich-core --deal imprivata
skill-pipeline enrich-interpret --deal imprivata
skill-pipeline export --deal imprivata

# Standalone post-production benchmark QA
python scripts/reconcile_alex.py --deal imprivata

# Standalone backend load test against the configured NewAPI/OpenAI endpoint
python scripts/stress_linkflow_backend.py --requests-per-scenario 4 --concurrency 3
```

## Backend Configuration

`skill_pipeline.core.llm` reads these variables:

- `NEWAPI_API_KEY`
- `NEWAPI_BASE_URL`
- `NEWAPI_MODEL`
- `NEWAPI_REASONING_EFFORT`
- `NEWAPI_SERVICE_TIER`

For local development, the wrapper auto-loads `.env.local` first, then `.env`, from the repository root if those files exist. Existing shell environment variables take precedence.

Current local defaults are:

- model: `gpt-5.4`
- base URL: `https://www.linkflow.run/v1`
- reasoning effort: `xhigh`
- service tier: `priority`

`invoke_structured()` does not impose a default completion-token cap. Only set `max_output_tokens` when a caller explicitly needs one. The wrapper checks `finish_reason` before parsing: if the API truncates the response (`finish_reason='length'`), it raises immediately with a clear message instead of retrying.

`EDGAR_IDENTITY` is required for live SEC fetches. `skill-pipeline raw-fetch` also accepts `PIPELINE_SEC_IDENTITY` and `SEC_IDENTITY` for compatibility, but `EDGAR_IDENTITY` is the documented variable.

Do not commit real API keys. Keep local credentials in `.env.local`, which is gitignored.

## Active Production Pipeline

`skill-pipeline run --deal <slug>` is the production entrypoint. The stage order is fixed:

1. `extract`
2. `materialize`
3. `check`
4. `verify`
5. `coverage`
6. `omission-audit`
7. `repair`
8. `enrich-core`
9. `enrich-interpret`
10. `export`

The production runner stops at export. Reconciliation is not part of the pipeline and must not be added to `skill_pipeline.stages.run`, the CLI, or any production stage.

All QA stages (3–6) run unconditionally so repair gets the fullest picture. The pipeline gates at repair: if repair raises `RuntimeError` (non-repairable errors or errors remaining after 2 rounds), enrichment and export do not run. The repair loop re-runs only deterministic stages (materialize, check, verify, coverage) after each round — omission-audit runs once at stage 6 and is not re-run inside the loop.

### Seed-Only Upstream Contract

The production pipeline depends on a single-filing source bundle:

- `raw/<slug>/discovery.json` has exactly one primary candidate.
- `raw/<slug>/discovery.json` has no supplementary candidates.
- `raw/<slug>/document_registry.json` has exactly one document.
- `data/deals/<slug>/source/filings/` contains only that one filing's copies.
- `data/deals/<slug>/source/supplementary_snippets.jsonl` must not exist.

If those conditions are violated, rerun `skill-pipeline raw-fetch --deal <slug>` followed by `skill-pipeline preprocess-source --deal <slug>` before doing extraction work.

### Stage Ownership

- `skill-pipeline raw-fetch --deal <slug>` and `skill-pipeline preprocess-source --deal <slug>` are seed-only upstream stages.
- `skill-pipeline extract --deal <slug>` writes raw LLM artifacts.
- `skill-pipeline materialize --deal <slug>` writes canonical deterministic artifacts.
- `skill-pipeline check`, `verify`, `coverage`, `omission-audit`, `repair`, `enrich-core`, `enrich-interpret`, and `export` are production stages.
- `python scripts/reconcile_alex.py --deal <slug>` is a standalone post-production diagnostic and never a pipeline gate.

### Artifact Layout

Production artifacts live under `data/skill/<slug>/`:

| Directory | Stage | Contents |
|-----------|-------|----------|
| `extract/` | `extract` | `actors_raw.json`, `events_raw.json` |
| `materialize/` | `materialize` | `actors.json`, `events.json`, `spans.json`, `materialize_log.json` |
| `check/` | `check` | `check_report.json` |
| `verify/` | `verify` | `verification_findings.json`, `verification_log.json` |
| `coverage/` | `coverage` + `omission-audit` | `coverage_findings.json`, `coverage_summary.json`, `omission_findings.json` |
| `repair/` | `repair` | `repair_log.json` |
| `enrich/` | `enrich-core` + `enrich-interpret` | `deterministic_enrichment.json`, `enrichment.json` |
| `export/` | `export` | `deal_events.csv` |
| `reconcile/` | standalone post-production QA | `alex_rows.json`, `reconciliation_report.json` |

### Key Code Map

- `skill_pipeline/cli.py` defines the production CLI surface.
- `skill_pipeline/stages/run.py` defines the end-to-end production orchestrator.
- `skill_pipeline/core/artifacts.py` is the single materialized-artifact loader used by downstream gates.
- `skill_pipeline/core/llm.py` is the single structured-output LLM backend wrapper.
- `skill_pipeline/core/prompts.py` contains prompt builders for LLM-backed stages.
- `scripts/reconcile_alex.py` is the standalone post-production benchmark QA path.
- `scripts/stress_linkflow_backend.py` is the standalone backend load probe.

### Production Runbook

If you are running a deal end to end, follow this order:

1. Confirm `data/deals/<slug>/source/chronology_blocks.jsonl`, `data/deals/<slug>/source/evidence_items.jsonl`, `raw/<slug>/document_registry.json`, and `raw/<slug>/discovery.json` exist.
2. Confirm the source bundle is seed-only.
3. Run `skill-pipeline run --deal <slug>`.
4. If benchmark QA is needed, run `python scripts/reconcile_alex.py --deal <slug>` after export only.

### Failure Modes

- If `skill-pipeline run`, `extract`, or `materialize` fails with a missing source artifact such as `data/deals/<slug>/source/chronology_blocks.jsonl`, the source bundle is not ready.
- If `skill-pipeline raw-fetch` fails, check `EDGAR_IDENTITY` and the live SEC access prerequisites.
- If QA stages (check, verify, coverage, omission-audit) report errors, the orchestrator prints PASS/FAIL per stage and proceeds to repair. Repair reads all findings from disk and attempts to fix repairable errors.
- If `repair` encounters any non-repairable error, it raises `RuntimeError` and the orchestrator returns 1 — enrichment and export do not run.
- If `repair` exhausts 2 rounds with errors remaining, it raises `RuntimeError`.
- If `invoke_structured` receives a truncated response (`finish_reason='length'`), it raises `ValueError` immediately without retrying.

## Benchmark Separation

- The generation workflow is filing-grounded from `extract` through `export`.
- Before `/export-csv` completes, do not consult benchmark materials, benchmark notes, `example/`, `diagnosis/`, or reconciliation artifacts.
- `python scripts/reconcile_alex.py --deal <slug>` is read-only, post-export only, and must not rewrite `extract/`, `materialize/`, `check/`, `verify/`, `coverage/`, `repair/`, `enrich/`, or `export/` artifacts.
- Historical slash-skill references are archival only. They do not define current production behavior.

## Architecture

The old `pipeline/` package is no longer active. The current production code lives in `skill_pipeline/`, and the authoritative operational contract lives in this file.

## Key Invariants

- Filing `.txt` files under `raw/` are immutable truth sources. Never rewrite them.
- Filing text is the only factual source. Do not use spreadsheets or notes as evidence during generation.
- LLM `anchor_text` output must survive deterministic substring matching in verification.
- `skill_pipeline` stages should fail fast on violated assumptions, missing files, or malformed artifacts.
- `materialize` is the canonical deterministic transform from raw extraction artifacts to canonical skill artifacts.

## Testing Guidelines

- Use `pytest` for all validation.
- Add targeted regression tests for extraction, verification, export, stage orchestration, and docs boundaries when behavior changes.
- Run the full suite before claiming the branch is complete.

## Commit Guidelines

- Keep commit subjects short and imperative.
- Include the affected stages or docs in the commit message.
- If docs or runtime outputs change, mention the relevant commands in the final summary.

## Historical Notes

Any remaining references to the deleted hybrid workflow, the empty `pipeline/`
package, or old slash-skill entrypoints are archival. They should not be
treated as active instructions.
