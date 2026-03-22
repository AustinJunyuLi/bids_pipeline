# CLAUDE.md

This file is the authoritative instruction source for agents working in this repository. If repository memories or action protocols change, update this file.

## What This Is

Research pipeline that extracts structured M&A deal data from SEC filings using LLM structured output. Reads DEFM14A/PREM14A/SC 14D-9 filings, sends chronology text to Claude Sonnet or GPT-5.4, gets back JSON with actors, events, and evidence references, then verifies every citation against the source text.

## Project Structure & Module Organization

Canonical deterministic pipeline code lives in [`pipeline/`](./pipeline): extraction, QA, enrichment, export, raw/source handling, and the `pipeline` CLI entrypoint. Isolated skill-workflow runtime code lives in [`skill_pipeline/`](./skill_pipeline): skill-specific models, path construction, seed loading, and the `skill-pipeline` CLI. Tests live in [`tests/`](./tests). Canonical pipeline artifacts live under [`data/deals/`](./data/deals); skill-workflow artifacts live under [`data/skill/`](./data/skill). Both workflows share read-only upstream inputs from [`raw/`](./raw) and `data/deals/<slug>/source/`. For the skill workflow, those upstream inputs are now a **single-filing seed-only bundle**: one filing frozen in `raw/<slug>/`, then one copied filing plus derived chronology/evidence artifacts in `data/deals/<slug>/source/`. Design docs and prompt specs are in [`docs/`](./docs). External review packages and debugging bundles live in [`diagnosis/`](./diagnosis).

## Build, Test, and Development Commands

``` bash
# Install package and both CLI entrypoints in editable mode
pip install -e .

# Run all tests
pytest -q

# Run isolated skill runtime tests
pytest -q tests/test_skill_pipeline.py

# Run a single test file
pytest -q tests/test_qa_stage.py

# Run a single test
pytest -q tests/test_qa_stage.py::test_name -v

# Focused extraction subset
pytest -q tests/test_extract_pipeline.py -k event

# Discover source filings for a deal
pipeline source discover --deal imprivata

# Fetch raw filings from EDGAR
pipeline raw fetch --deal imprivata

# Preprocess source from raw filings
pipeline preprocess source --deal imprivata

# Canonical pipeline extraction examples
pipeline extract actors --deal imprivata --provider anthropic --model claude-sonnet-4-6
pipeline extract events --deal imprivata --provider openai --model gpt-5.4 --reasoning-effort none

# Canonical pipeline post-extraction stages
pipeline qa --deal imprivata --resume
pipeline enrich --deal imprivata
pipeline export --deal imprivata

# Isolated skill workflow preflight / summary
skill-pipeline deal-agent --deal imprivata

# Seed-only skill workflow upstream stages
skill-pipeline raw-fetch --deal imprivata
skill-pipeline preprocess-source --deal imprivata

# Deterministic skill-runtime stages used by the hybrid workflow
skill-pipeline canonicalize --deal imprivata
skill-pipeline check --deal imprivata
skill-pipeline verify --deal imprivata
skill-pipeline coverage --deal imprivata
skill-pipeline enrich-core --deal imprivata
```

## Architecture

### Canonical Pipeline

7-stage pipeline. Each stage reads from the previous stage's output directory:

```         
raw/<slug>/filings/*.txt          (Stage 1: frozen SEC filing text — NEVER modified)
    ↓
data/deals/<slug>/source/         (Stage 2: chronology_blocks.jsonl, evidence_items.jsonl)
    ↓
data/deals/<slug>/extract/        (Stage 3: actors_raw.json, events_raw.json via LLM)
    ↓
data/deals/<slug>/qa/             (Stage 4: extraction_canonical.json, report.json, span_registry.jsonl)
    ↓
data/deals/<slug>/enrich/         (Stage 5: deal_enrichment.json)
    ↓
data/deals/<slug>/export/         (Stage 6: events_long.csv, alex_compat.csv)
    ↓
data/validate/                    (Stage 7: reference_summary.json)
```

State is tracked in `data/runs/pipeline_state.sqlite`.

Use the canonical pipeline for deterministic runs, reproducible artifacts, and any work that should align with the repository's Python pipeline code.

### Skill-Driven Hybrid Workflow

The quick workflow is now a hybrid agent + deterministic flow after
`skill-pipeline raw-fetch --deal <slug>` and
`skill-pipeline preprocess-source --deal <slug>`
have already run.

`skill-pipeline raw-fetch` and `skill-pipeline preprocess-source` are
**seed-only** stages. They use the filing URL from `data/seeds.csv` as the only
upstream filing source. They do not discover or preserve supplementary filings.
If `raw/<slug>/discovery.json` or `raw/<slug>/document_registry.json` still come
from an older multi-filing run, rerun `skill-pipeline raw-fetch --deal <slug>`
before preprocess.

The skill workflow source contract is:

- `raw/<slug>/discovery.json` has exactly one primary candidate
- `raw/<slug>/discovery.json` has no supplementary candidates
- `raw/<slug>/document_registry.json` has exactly one document
- `data/deals/<slug>/source/filings/` contains only that one filing's copies
- `data/deals/<slug>/source/supplementary_snippets.jsonl` must not exist

If any of those conditions are violated, treat the source bundle as stale and
rerun `skill-pipeline raw-fetch --deal <slug>` followed by
`skill-pipeline preprocess-source --deal <slug>` before doing extraction work.

#### Critical distinction for agents

-   `/deal-agent <slug>` is the agent-facing end-to-end orchestrator.
-   `skill-pipeline deal-agent --deal <slug>` is **not** the end-to-end runner. It is
    only a preflight / directory-creation / artifact-summary CLI.
-   Do **not** tell the user that `skill-pipeline deal-agent` executes extraction,
    repair, enrichment, or export. It does not.

#### End-to-end hybrid sequence

``` text
/deal-agent <slug>
  |-- /extract-deal <slug>
  |-- skill-pipeline canonicalize --deal <slug>
  |-- skill-pipeline check --deal <slug>
  |-- skill-pipeline verify --deal <slug>
  |-- skill-pipeline coverage --deal <slug>
  |-- /verify-extraction <slug>
  |-- skill-pipeline enrich-core --deal <slug>
  |-- /enrich-deal <slug>
  |-- /export-csv <slug>
  |-- /reconcile-alex <slug>          (optional, post-export diagnostic)
```

#### What each layer owns

-   Agent skills own:
    -   `/extract-deal <slug>`: LLM extraction into
        `data/skill/<slug>/extract/actors_raw.json` and
        `data/skill/<slug>/extract/events_raw.json`
    -   `/verify-extraction <slug>`: repair loop and final verification gate
    -   `/enrich-deal <slug>`: interpretive enrichment remainder
    -   `/export-csv <slug>`: CSV formatting / export
    -   `/reconcile-alex <slug>`: post-export benchmark QA against Alex's
        spreadsheet. Diagnostic only — does not gate the pipeline or
        rewrite any generation artifacts. Invoke only after `/export-csv`
        completes.
-   `skill-pipeline` CLI owns:
    -   `skill-pipeline deal-agent --deal <slug>`: preflight and summary only
    -   `skill-pipeline canonicalize --deal <slug>`: upgrade legacy extract JSON into
        canonical span-backed artifacts, normalize dates, deduplicate events,
        gate drops by NDA, recover unnamed parties
    -   `skill-pipeline check --deal <slug>`: deterministic structural gate
    -   `skill-pipeline verify --deal <slug>`: strict deterministic verification
    -   `skill-pipeline coverage --deal <slug>`: deterministic source-coverage audit
        over evidence cues vs extracted actors/events
    -   `skill-pipeline enrich-core --deal <slug>`: deterministic rounds, bid
        classifications, cycles, and formal boundary

#### Agent-facing manual

If you are a fresh agent and need to run the skill workflow correctly, follow
this exact procedure:

1.  Confirm prerequisites exist:
    -   `data/deals/<slug>/source/chronology_blocks.jsonl`
    -   `data/deals/<slug>/source/evidence_items.jsonl`
    -   `raw/<slug>/document_registry.json`
    -   `raw/<slug>/discovery.json`
2.  Confirm the upstream source bundle is seed-only:
    -   `raw/<slug>/discovery.json` has exactly one primary candidate
    -   `raw/<slug>/discovery.json` has no supplementary candidates
    -   `raw/<slug>/document_registry.json` has exactly one document
    -   `data/deals/<slug>/source/supplementary_snippets.jsonl` does not exist
    -   If not, rerun `skill-pipeline raw-fetch --deal <slug>` and
        `skill-pipeline preprocess-source --deal <slug>` before continuing
3.  If `data/skill/<slug>/extract/actors_raw.json` and
    `data/skill/<slug>/extract/events_raw.json` do not exist, run
    `/extract-deal <slug>` first. Do **not** run `skill-pipeline canonicalize`,
    `skill-pipeline check`, `skill-pipeline verify`, or
    `skill-pipeline enrich-core` before extract artifacts exist.
4.  Run `skill-pipeline canonicalize --deal <slug>`.
    -   Output: `data/skill/<slug>/canonicalize/canonicalize_log.json`
        plus `data/skill/<slug>/extract/spans.json`
    -   Overwrites `actors_raw.json` and `events_raw.json` in place with the
        canonical schema
    -   Canonical schema uses `evidence_span_ids` and `ResolvedDate` objects;
        legacy `evidence_refs` and `DateHint` input are accepted only before
        canonicalize runs
    -   Deduplicates events, removes drops without NDAs, recovers unnamed parties
5.  Run `skill-pipeline check --deal <slug>`.
    -   Output: `data/skill/<slug>/check/check_report.json`
    -   Gate: stop on blocker findings
6.  Run `skill-pipeline verify --deal <slug>`.
    -   Outputs:
        -   `data/skill/<slug>/verify/verification_findings.json`
        -   `data/skill/<slug>/verify/verification_log.json`
    -   Strict quote policy: EXACT and NORMALIZED resolve; FUZZY does not
7.  Run `skill-pipeline coverage --deal <slug>`.
    -   Outputs:
        -   `data/skill/<slug>/coverage/coverage_findings.json`
        -   `data/skill/<slug>/coverage/coverage_summary.json`
    -   Coverage fails on uncovered high-confidence critical cues such as
        proposal, NDA, withdrawal/drop, and process-initiation evidence
8.  Run `/verify-extraction <slug>`.
    -   Use `verification_findings.json` as the deterministic input
    -   Use `coverage_findings.json` as an additional deterministic repair input
    -   Run the LLM repair loop only if **all** error-level findings are `repairable`
    -   If any error-level finding is `non_repairable`, fail closed and do not
        run repair
9.  Run `skill-pipeline enrich-core --deal <slug>`.
    -   Output: `data/skill/<slug>/enrich/deterministic_enrichment.json`
10. Run `/enrich-deal <slug>`.
    -   This adds the interpretive remainder and writes
        `data/skill/<slug>/enrich/enrichment.json`
11. Run `/export-csv <slug>`.
    -   Output: `data/skill/<slug>/export/deal_events.csv`
12. (Optional) Run `/reconcile-alex <slug>`.
    -   Output: `data/skill/<slug>/reconcile/reconciliation_report.json`
    -   Post-export only. Diagnostic, not a pipeline gate.
    -   Status is `clean`, `attention`, or `high_attention` — informational only.

#### Common failure mode

If `skill-pipeline canonicalize`, `skill-pipeline check`, `skill-pipeline verify`,
`skill-pipeline coverage`, or `skill-pipeline enrich-core` fails with:

`FileNotFoundError: Missing required input: data/skill/<slug>/extract/actors_raw.json`

that usually means the agent skipped `/extract-deal <slug>` or is running the
deterministic stage before skill extract artifacts exist. This is expected
fail-fast behavior, not a reason to add fallback logic.

Repository support for this workflow is split across two layers:

-   The skill files define the stage semantics and gate conditions for
    `/extract-deal`, `/verify-extraction`, `/enrich-deal`, and `/export-csv`.
-   The isolated [`skill_pipeline/`](./skill_pipeline) package provides
    deterministic runtime support plus preflight / summary CLI commands.
-   Skill artifacts live under `data/skill/<slug>/`
    (`extract/`, `check/`, `verify/`, `enrich/`, `export/`), and the final review
    CSV is `data/skill/<slug>/export/deal_events.csv`.
-   Shared read-only inputs for the skill workflow are
    `data/deals/<slug>/source/`, `raw/<slug>/document_registry.json`, and
    `data/seeds.csv`.
-   Canonical pipeline artifacts under `data/deals/<slug>/...` remain separate
    and must not be used as skill outputs.

#### Benchmark separation

-   The generation workflow is filing-grounded from `/extract-deal <slug>`
    through `/export-csv <slug>`.
-   Before `/export-csv` completes, do **not** consult benchmark materials,
    benchmark notes, or reconciliation artifacts.
-   Before `/export-csv` completes, do not open, read, or consult the
    `reconcile-alex` skill file itself in any mirror
    (`.claude/`, `.codex/`, or `.cursor/`). Treat the skill text as
    post-export-only benchmark material.
-   Treat `example/` as post-export-only material.
-   `/reconcile-alex <slug>` is a read-only, post-export diagnostic. It must
    not rewrite `extract/`, `verify/`, `enrich/`, or `export/` artifacts.
-   If any prior session consulted benchmark materials before `/export-csv` and
    then generated `data/skill/<slug>/...` artifacts, treat those artifacts as
    tainted for blind evaluation. Regenerate from the filing-grounded workflow
    first.

#### Artifact directories

Skill workflow artifacts under `data/skill/<slug>/`:

| Directory | Stage | Contents |
|-----------|-------|----------|
| `extract/` | `/extract-deal` + `canonicalize` | `actors_raw.json`, `events_raw.json`, `spans.json` |
| `canonicalize/` | `canonicalize` | `canonicalize_log.json` |
| `check/` | `check` | `check_report.json` |
| `verify/` | `verify` | `verification_findings.json`, `verification_log.json` |
| `coverage/` | `coverage` | `coverage_findings.json`, `coverage_summary.json` |
| `enrich/` | `enrich-core` + `/enrich-deal` | `deterministic_enrichment.json`, `enrichment.json` |
| `export/` | `/export-csv` | `deal_events.csv` |
| `reconcile/` | `/reconcile-alex` | `alex_rows.json`, `reconciliation_report.json` |

Historical notes may still describe the skill workflow as purely agent-driven or
may imply that `skill-pipeline deal-agent` is the end-to-end runner. Those notes
are stale. Follow this file and the current skill docs instead.

### LLM Call Path

The critical extraction path flows through these files in order:

1.  `pipeline/extract/actors.py` / `events.py` — orchestrate extraction, set token budgets
2.  `pipeline/llm/prompts.py` — render the user message from chronology blocks + evidence items
3.  `pipeline/llm/backend.py` — `ainvoke_structured()` sends the prompt, parses JSON, runs repair loop on validation failure
4.  `pipeline/llm/anthropic_backend.py` / `openai_backend.py` — provider-specific request construction
5.  `pipeline/llm/token_budget.py` — complexity classification and output budget estimation

### QA Span Resolution

After extraction, QA verifies every evidence citation:

1.  `pipeline/qa/rules.py` — `SpanRegistry` resolves each `block_id`/`evidence_id` + `anchor_text` to a `SourceSpan`
2.  `pipeline/normalize/spans.py` — maps anchor text to line/char positions in the source filing
3.  `pipeline/normalize/quotes.py` — matching cascade: exact substring → normalized (smart quotes/whitespace) → unresolved
4.  Any unresolved span is a **blocker** — the deal cannot be exported

### Key Models

-   `pipeline/models/source.py` — ChronologyBlock, EvidenceItem, ChronologySelection
-   `pipeline/models/extraction.py` — ActorRecord, SourceSpan, DealExtraction, event types
-   `pipeline/models/common.py` — enums (EventType, ActorRole, QuoteMatchType, etc.)
-   `pipeline/llm/schemas.py` — Pydantic schemas for LLM output (ActorExtractionOutput, EventExtractionOutput)
-   `skill_pipeline/models.py` — skill-workflow raw and canonical artifact models,
    including `ResolvedDate`, `SpanRecord`, and coverage artifacts; keep these
    separate from `pipeline/models/*`

## Key Invariants

-   Filing `.txt` files under `raw/` are immutable truth sources. Never rewrite them.
-   Filing text is the only factual source. Do not use spreadsheets or notes as evidence.
-   Evidence items use per-filing sequential IDs (E0001, E0002...) that collide across filings. QA must handle duplicates.
-   The LLM's `anchor_text` is free-form output that must survive deterministic substring matching in QA. The model is told "do not paraphrase" but compliance varies by provider.
-   `prompted_json` is the default structured output mode. The system prompt includes a JSON schema outline and tells the model to return exactly one JSON object.
-   GPT-5.4 shares `max_completion_tokens` between hidden reasoning and visible output. Use `reasoning_effort=none` for extraction.

## Coding Style & Naming Conventions

Target Python 3.11+ with 4-space indentation and type hints on public functions. Follow existing Pydantic-first patterns for schemas and use `snake_case` for functions, modules, and JSON keys. Keep pipeline stages deterministic where possible: prefer stable IDs, explicit budgets, and structured artifacts over ad hoc strings. No formatter is configured in `pyproject.toml`; match the surrounding style and keep imports tidy.

## Testing Guidelines

Pytest is configured via [`pytest.ini`](./pytest.ini) with `tests/` as the test root. Name new tests `test_<behavior>()` and keep fixtures local unless broadly reused. Add targeted regression tests for every extraction, QA, or budgeting bug you fix, especially around span resolution, chunk planning, and provider-specific LLM behavior.

## Commit & Pull Request Guidelines

Recent history uses conventional prefixes such as `feat:`, `fix:`, and `test:`. Keep commit subjects short and imperative, for example `fix: resolve duplicate evidence ids in QA`. PRs should include: the affected deal slugs or stages, a brief rationale, commands run (`pytest -q ...`, pipeline CLI invocations), and before/after artifact notes when outputs change.

## Environment Variables

```         
ANTHROPIC_API_KEY      — required for Anthropic provider
OPENAI_API_KEY         — required for OpenAI provider
BIDS_LLM_PROVIDER      — default: anthropic (anthropic|openai)
BIDS_LLM_MODEL         — override model ID
BIDS_LLM_REASONING_EFFORT — provider-specific reasoning effort
BIDS_LLM_STRUCTURED_MODE  — prompted_json|provider_native|auto
EDGAR_IDENTITY         — required for live SEC access during `skill-pipeline raw-fetch`; local value: Austin Li, University College London, junyu.li.24@ucl.ac.uk
```

## Active Deals

9 deals in scope: imprivata, mac-gray, medivation, penford, petsmart-inc, providence-worcester, saks, stec, zep. All have preprocessed source. Seeds are in `data/seeds.csv`.

## Security & Configuration Tips

Do not commit API keys or provider secrets. Use environment variables such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `BIDS_LLM_PROVIDER`, `BIDS_LLM_MODEL`, and `EDGAR_IDENTITY`. For live SEC fetches on this machine, `EDGAR_IDENTITY` should be set to `Austin Li, University College London, junyu.li.24@ucl.ac.uk`. Treat canonical pipeline artifacts under `data/deals/` and skill workflow artifacts under `data/skill/` as generated outputs; only edit them intentionally and document why.

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
