# CLAUDE.md

This file is the authoritative instruction source for agents working in this repository. If repository memories or action protocols change, update this file.

## What This Is

Research pipeline that extracts structured M&A deal data from SEC filings using LLM structured output. Reads DEFM14A/PREM14A/SC 14D-9 filings, sends chronology text to Claude Sonnet or GPT-5.4, gets back JSON with actors, events, and evidence references, then verifies every citation against the source text.

## Project Structure & Module Organization

The only Python package and installed CLI in this worktree is [`skill_pipeline/`](./skill_pipeline) with the `skill-pipeline` entrypoint from [`pyproject.toml`](./pyproject.toml). There is no active [`pipeline/`](./pipeline) package here; any notes that refer to it are historical and should not be treated as implementation guidance.

Core modules:

- `skill_pipeline/cli.py` - command routing for the deterministic stages
- `skill_pipeline/raw/` - seed-only raw fetch, immutable filing freeze, discovery manifest
- `skill_pipeline/preprocess/` and `skill_pipeline/source/` - chronology selection, block building, evidence scanning
- `skill_pipeline/canonicalize.py` - raw-to-canonical upgrade, span resolution, dedup, NDA gating, unnamed-party recovery
- `skill_pipeline/check.py`, `skill_pipeline/verify.py`, `skill_pipeline/coverage.py` - deterministic gates
- `skill_pipeline/enrich_core.py` - deterministic rounds, bid classifications, cycles, formal boundary
- `skill_pipeline/deal_agent.py` - preflight and artifact summary only
- `skill_pipeline/models.py` and `skill_pipeline/paths.py` - artifact schemas and path conventions

Artifacts:

- `raw/<slug>/` - immutable filing text plus seed-only discovery metadata
- `data/deals/<slug>/source/` - chronology and evidence artifacts shared by the skill workflow
- `data/skill/<slug>/extract/` - raw or canonical actors/events plus `spans.json`
- `data/skill/<slug>/{check,verify,coverage,enrich,export}/` - downstream deterministic outputs
- `tests/` - focused regression tests for each stage
- `docs/` - design notes and implementation plans

## Build, Test, and Development Commands

``` bash
# Install the single CLI entrypoint in editable mode
pip install -e .

# Run all tests
pytest -q

# Run focused stage suites
pytest -q tests/test_skill_raw_stage.py tests/test_skill_preprocess_source.py
pytest -q tests/test_skill_verify.py tests/test_skill_coverage.py
pytest -q tests/test_skill_canonicalize.py
pytest -q tests/test_skill_enrich_core.py tests/test_skill_pipeline.py

# Run a single test file
pytest -q tests/test_skill_pipeline.py

# Run a single test
pytest -q tests/test_skill_pipeline.py::test_name -v

# Seed-only upstream stages
skill-pipeline raw-fetch --deal imprivata
skill-pipeline preprocess-source --deal imprivata

# Preflight / summary only
skill-pipeline deal-agent --deal imprivata

# Deterministic stages after extract artifacts exist
skill-pipeline canonicalize --deal imprivata
skill-pipeline check --deal imprivata
skill-pipeline verify --deal imprivata
skill-pipeline coverage --deal imprivata
skill-pipeline enrich-core --deal imprivata
```

## Architecture

The active runtime is the `skill_pipeline` hybrid workflow. The deterministic stages are intended to run after seed-only source preparation and agent-produced extract artifacts.

``` text
data/seeds.csv
  -> skill-pipeline raw-fetch --deal <slug>
  -> raw/<slug>/filings/*.txt + raw/<slug>/{discovery,document_registry}.json
  -> skill-pipeline preprocess-source --deal <slug>
  -> data/deals/<slug>/source/{chronology_blocks,evidence_items}.jsonl
  -> /extract-deal <slug>
  -> data/skill/<slug>/extract/{actors_raw,events_raw}.json
  -> skill-pipeline canonicalize --deal <slug>
  -> skill-pipeline check --deal <slug>
  -> skill-pipeline verify --deal <slug>
  -> skill-pipeline coverage --deal <slug>
  -> /verify-extraction <slug> (if deterministic findings are repairable)
  -> skill-pipeline enrich-core --deal <slug>
  -> /enrich-deal <slug>
  -> /export-csv <slug>
  -> /reconcile-alex <slug> (optional post-export diagnostic)
```

Important distinctions:

- `skill-pipeline raw-fetch` and `skill-pipeline preprocess-source` are **seed-only**. They use the filing URL from `data/seeds.csv` and do not preserve supplementary filings.
- `skill-pipeline deal-agent --deal <slug>` is **summary/preflight only**. It does not run extraction, repair, enrichment, or export.
- `skill-pipeline canonicalize`, `check`, `verify`, `coverage`, and `enrich-core` are fail-fast deterministic gates. Do not add fallback logic to keep them running on missing or contradictory inputs.
- `skill-pipeline enrich-core` now requires passing `check`, `verify`, and `coverage` artifacts before it will write `data/skill/<slug>/enrich/deterministic_enrichment.json`.
- `data/skill/<slug>/extract/spans.json` is required once extract artifacts are canonicalized. Missing sidecars are an error, not a cue to fabricate an empty registry.

### Benchmark Separation

Benchmark materials are post-export only. Do not consult `example/`,
`diagnosis/`, benchmark workbooks, or `/reconcile-alex` before `/export-csv`
completes.

Generation stops at the repository's filing-grounded export contract.
Extraction, canonicalization, check, verify, coverage, enrichment, and export
must not use benchmark conventions as hidden requirements. `/reconcile-alex` is
an optional diagnostic comparison skill that runs only after export and never
rewrites generation artifacts.

### Stage Responsibilities

- `/extract-deal <slug>` writes legacy extract artifacts with `evidence_refs` into `data/skill/<slug>/extract/`.
- `skill-pipeline canonicalize --deal <slug>` upgrades those artifacts into canonical span-backed form, normalizes dates, deduplicates only semantically equivalent events, removes drops without prior NDA support, and recovers unnamed parties when the deterministic rules allow it.
- `skill-pipeline check --deal <slug>` is the structural blocker gate.
- `skill-pipeline verify --deal <slug>` enforces referential integrity and strict quote resolution. `EXACT` and `NORMALIZED` pass; `FUZZY` does not.
- `skill-pipeline coverage --deal <slug>` audits source cues against extracted actors/events and fails on uncovered high-confidence critical evidence.
- `/verify-extraction <slug>` consumes deterministic findings and may run a repair loop only when every error-level finding is repairable.
- `skill-pipeline enrich-core --deal <slug>` writes deterministic rounds, bid classifications, cycles, and formal-boundary outputs.
- `/enrich-deal <slug>` writes the later interpretive `enrichment.json` layer if used.
- `/export-csv <slug>` writes the repository review CSV from filing-grounded extract and enrich artifacts only.
- `/reconcile-alex <slug>` is optional post-export benchmark QA. It must not modify generation artifacts or become a prerequisite for export.

### Key Files

- `skill_pipeline/raw/fetch.py` and `skill_pipeline/raw/stage.py` - immutable filing freeze and seed-only ingress
- `skill_pipeline/preprocess/source.py` and `skill_pipeline/source/locate.py` - chronology discovery and fail-closed preprocessing
- `skill_pipeline/provenance.py` and `skill_pipeline/canonicalize.py` - span resolution and canonical schema upgrade
- `skill_pipeline/check.py`, `skill_pipeline/verify.py`, `skill_pipeline/coverage.py` - deterministic gates
- `skill_pipeline/enrich_core.py` - downstream deterministic enrichment
- `skill_pipeline/deal_agent.py` - artifact summary that recognizes both `deterministic_enrichment.json` and `enrichment.json`
- `skill_pipeline/models.py` - raw/canonical artifact models, `ResolvedDate`, `SpanRecord`, verification and coverage schemas

## Key Invariants

-   Filing `.txt` files under `raw/` are immutable truth sources. Never rewrite them.
-   Filing text is the only factual source. Do not use spreadsheets or notes as evidence.
-   `raw-fetch` and `preprocess-source` are single-seed, single-primary-document stages in this worktree.
-   Evidence items use per-filing IDs, so provenance resolution must validate document/line consistency instead of assuming global uniqueness.
-   Canonical extract artifacts must carry `evidence_span_ids`, and canonical loading must fail if `spans.json` is missing.
-   `check`, `verify`, and `coverage` are prerequisites for `enrich-core`; enrichment must not create success artifacts on unchecked extracts.
-   `skill-pipeline deal-agent` is only a preflight / summary command. It may summarize deterministic enrichment from `deterministic_enrichment.json` even when the later interpretive `enrichment.json` does not exist yet.
-   Benchmark materials are forbidden until `/export-csv` completes. `example/`, `diagnosis/`, and `/reconcile-alex` are post-export only.
-   `edgartools>=5.23` is currently allowed in `pyproject.toml`, but the live fetch path emits v6 deprecation warnings. Treat pinning or capping before a breaking v6 release as a follow-up dependency risk.

## Coding Style & Naming Conventions

Target Python 3.11+ with 4-space indentation and type hints on public functions. Follow existing Pydantic-first patterns for schemas and use `snake_case` for functions, modules, and JSON keys. Keep pipeline stages deterministic where possible: prefer stable IDs, explicit budgets, and structured artifacts over ad hoc strings. No formatter is configured in `pyproject.toml`; match the surrounding style and keep imports tidy.

## Testing Guidelines

Pytest is configured via [`pytest.ini`](./pytest.ini) with `tests/` as the test root. Name new tests `test_<behavior>()` and keep fixtures local unless broadly reused. Add targeted regression tests for every extraction, QA, or budgeting bug you fix, especially around span resolution, chunk planning, and provider-specific LLM behavior.

## Commit & Pull Request Guidelines

Recent history uses conventional prefixes such as `feat:`, `fix:`, and `test:`. Keep commit subjects short and imperative, for example `fix: reject mismatched span references in canonicalize`. PRs should include: the affected deal slugs or stages, a brief rationale, commands run (`pytest -q ...`, `skill-pipeline ...`), and before/after artifact notes when outputs change.

## Environment Variables

```         
ANTHROPIC_API_KEY      — required for Anthropic provider
OPENAI_API_KEY         — required for OpenAI provider
BIDS_LLM_PROVIDER      — default: anthropic (anthropic|openai)
BIDS_LLM_MODEL         — override model ID
BIDS_LLM_REASONING_EFFORT — provider-specific reasoning effort
BIDS_LLM_STRUCTURED_MODE  — prompted_json|provider_native|auto
PIPELINE_SEC_IDENTITY  — preferred EDGAR identity for raw-fetch
SEC_IDENTITY / EDGAR_IDENTITY — fallback EDGAR identity env vars
```

## Active Deals

9 deals in scope: imprivata, mac-gray, medivation, penford, petsmart-inc, providence-worcester, saks, stec, zep. All have preprocessed source. Seeds are in `data/seeds.csv`.

## Security & Configuration Tips

Do not commit API keys or provider secrets. Use environment variables such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `BIDS_LLM_PROVIDER`, and `BIDS_LLM_MODEL`. Treat canonical pipeline artifacts under `data/deals/` and skill workflow artifacts under `data/skill/` as generated outputs; only edit them intentionally and document why.

You are my local Python agent.

## Core operating rules:

1.  Think from first principles. Do not assume I have perfectly specified the true objective. Start from the underlying need and the actual problem. If the objective, constraints, interfaces, or success criteria are materially unclear, stop and ask focused clarification questions.

2.  Solve the real problem, not the symptom. Do not give patch-style, workaround-style, or compatibility-first solutions when the correct fix is structural.

3.  Do not overengineer. Use the shortest correct path. Do not add speculative abstractions, future-proofing, fallback systems, downgrade paths, optional modes, or extra branches unless I explicitly ask for them.

4.  Do not expand scope. Only solve the requirement I gave you. Do not invent adjacent features or “helpful” extras.

5.  Fail fast. Fail fast on violated assumptions, invalid states, unexpected inputs, schema mismatches, missing required data, and logic inconsistencies. Do not silence errors. Do not swallow exceptions. Do not use broad try/except blocks that hide failures. Do not substitute defaults, empty outputs, partial success, fallback behavior, retries, or log-and-continue behavior unless I explicitly request them. Prefer loud failure over silent corruption. A precise crash is better than an untrustworthy result.

6.  Protect logical correctness. Before proposing or writing code, validate the full end-to-end logic: inputs -\> transformations -\> outputs -\> edge cases -\> failure paths -\> side effects.

7.  Python coding rules. Write complete Python code. No pseudocode. No TODOs. No omitted core sections. Prefer explicitness, clear naming, input validation, deterministic behavior, and strong error handling. Use specific exceptions. Preserve original tracebacks when possible. Avoid hidden state and silent failures.

8.  Research and pipeline safety. Do not silently alter semantics, schemas, event definitions, sample construction, or output meaning. Do not silently drop malformed data. Do not add fallback logic that can contaminate inference. If a step could change results, surface it explicitly. Default policy: abort on the first materially relevant error.

9.  Design Approch (Very Important) Think step by step about whether there exists a less over-engineered and yet simpler, more elegant, and more robust solution to the problem that accords with KISS and DRY principles. Present it to me with your degree of confidence from 1 to 10 and its rationale, but do not modify code yet. Target minimum viable functionality in all designs of yours.
