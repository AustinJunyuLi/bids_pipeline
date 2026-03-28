# Phase 5: Integration + Calibration - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire the complete pipeline into an end-to-end flow with DuckDB as the canonical structured store, complexity-based routing for extraction, expanded few-shot examples, and a documented orchestration contract. This phase produces a single multi-deal database, a deterministic CSV export from DuckDB, and a documented local-agent orchestration entry point that processes any deal end-to-end.

</domain>

<decisions>
## Implementation Decisions

### DuckDB Schema + Loading
- **D-01:** Single multi-deal DuckDB database file (not per-deal). All deals load into the same database, enabling cross-deal queries. Database location is a project-level path (e.g., `data/pipeline.duckdb`).
- **D-02:** DuckDB loading happens after enrich-core as a new dedicated `db-load` stage with its own CLI command: `skill-pipeline db-load --deal <slug>`. It reads canonical extract artifacts (actors_raw.json, events_raw.json, spans.json) plus enrichment artifacts and inserts/upserts into DuckDB tables.
- **D-03:** CSV export migrates to a new deterministic Python stage: `skill-pipeline db-export --deal <slug>`. This generates deal_events.csv from DuckDB queries, replacing the local-agent `/export-csv` skill. Export becomes fully deterministic.

### Orchestration Contract
- **D-04:** Claude has discretion on the orchestration form. The approach should satisfy DB-02 ("without manual handoffs between core stages") while respecting the constraint that extraction stays in `.claude/skills/`. The most natural approach is a combination of enhanced deal-agent and documented workflow.
- **D-05:** Orchestration must support both per-deal execution (test one deal works) and batch execution (process all 9 deals). Testing strategy: validate per-deal first, then batch.

### Complexity Routing
- **D-06:** Claude has discretion on whether routing is fully automatic or has a manual override flag. The compose-prompts chunk planner already supports both single-pass and chunked modes; complexity routing adds the decision logic.
- **D-07:** Claude has discretion on exact thresholds. The roadmap suggests `<=150 blocks, <=8 actors` but thresholds should be calibrated against actual deal data from the 9-deal corpus if the research warrants it.

### Few-Shot Expansion
- **D-08:** Claude has discretion on example source (extracted from completed deals vs hand-crafted from filing text). The 5 target patterns from INFRA-07 are: NDA groups, ambiguous drops, cycle boundaries, range proposals, and formal-round signals.
- **D-09:** Claude has discretion on whether to expand existing `prompt_assets/` files or build a structured example registry. The approach should be compatible with the existing prompt composition engine from Phase 2.

### Claude's Discretion
- DuckDB table schema (normalization level, column types, indexes)
- Whether db-load upserts or drops-and-reloads per deal
- Exact orchestration form (enhanced deal-agent, new CLI command, documented workflow, or combination)
- Whether to add a `--force-chunked`/`--force-single-pass` override flag to compose-prompts
- Whether to calibrate complexity thresholds from corpus data or use roadmap defaults
- Example format (flat markdown vs structured registry)
- How to handle the deferred chunk-budget overhead issue from Phase 2

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope
- `.planning/ROADMAP.md` — Phase 5 goal, scope, exit criteria, and requirements (DB-01, DB-02, DB-03, PROMPT-06, INFRA-07)
- `.planning/REQUIREMENTS.md` — DB-01 (DuckDB store), DB-02 (orchestration), DB-03 (DuckDB export), PROMPT-06 (complexity routing), INFRA-07 (few-shot examples)
- `.planning/PROJECT.md` — project constraints (correctness priority, no Python LLM wrapper, benchmark separation)

### Prior Phase Carry-Forward
- `.planning/phases/01-foundation-annotation/01-CONTEXT.md` — D-01: no Python LLM wrapper constraint; D-09: annotation runs inside preprocess-source
- `.planning/phases/02-prompt-architecture/02-CONTEXT.md` — D-06: single-pass and chunked from same contract, thresholds deferred to Phase 5; D-10: few-shot examples are file-backed
- `.planning/phases/03-quote-before-extract/03-CONTEXT.md` — D-04: new format only, no dual-path support
- `.planning/phases/04-enhanced-gates/04-CONTEXT.md` — D-02: gates run after coverage before enrich-core; D-03: own CLI command and output directory

### Existing Pipeline Implementation
- `skill_pipeline/cli.py` — CLI entry points; new `db-load` and `db-export` subcommands needed
- `skill_pipeline/paths.py` — `SkillPathSet`, `build_skill_paths()` — new db paths needed
- `skill_pipeline/deal_agent.py` — deal status summarizer; orchestration enhancement point
- `skill_pipeline/compose_prompts.py` — prompt composition engine; complexity routing integration point
- `skill_pipeline/prompts/chunks.py` — chunk planner with `build_chunk_windows()` and `estimate_block_tokens()`
- `skill_pipeline/enrich_core.py` — last deterministic stage before db-load
- `skill_pipeline/models.py` — Pydantic models for all artifacts
- `skill_pipeline/extract_artifacts.py` — `LoadedExtractArtifacts`, format dispatch

### Prompt Assets
- `skill_pipeline/prompt_assets/event_examples.md` — current few-shot examples (23 lines, needs expansion)
- `skill_pipeline/prompt_assets/actors_prefix.md` — actor extraction prompt prefix
- `skill_pipeline/prompt_assets/events_prefix.md` — event extraction prompt prefix

### Pipeline Flow
- `CLAUDE.md` — end-to-end flow documentation (needs db-load and db-export inserted)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `build_chunk_windows()` in `prompts/chunks.py` — already handles single-pass vs chunked based on token budget. Complexity routing adds a decision wrapper.
- `estimate_block_tokens()` in `prompts/chunks.py` — token estimation for complexity threshold evaluation.
- `LoadedExtractArtifacts` in `extract_artifacts.py` — loads canonical extract data; DuckDB loading can consume the same artifacts.
- `SkillPathSet` in `paths.py` — path generation pattern for new db-related paths.
- `deal_agent.py` — existing summarizer that can be extended for orchestration status.

### Established Patterns
- Each pipeline stage has: CLI subcommand in `cli.py`, dedicated module, output directory under `data/skill/<slug>/`, Pydantic models for output, and exit code convention (0=pass, 1=fail).
- Stage prerequisite checking via `_require_gate_artifacts()` in `enrich_core.py` — db-load should follow the same gating pattern.
- Prompt assets are plain markdown files loaded at composition time.

### Integration Points
- `cli.py` — new `db-load` and `db-export` subcommands
- `paths.py` — new database path and export path properties
- `compose_prompts.py` — complexity routing decision before chunk planning
- `deal_agent.py` — orchestration status and run-plan generation
- `CLAUDE.md` — pipeline flow documentation update

</code_context>

<specifics>
## Specific Ideas

- The chunk-budget overhead issue from Phase 2 should be addressed as part of complexity routing — the token estimation heuristic (`ceil(word_count * 1.35)`) needs validation against actual stec packet sizes.
- DuckDB is file-based and embedded — no server infrastructure needed. The database file can live alongside artifacts.
- Testing orchestration: validate stec end-to-end first (per-deal), then run all 9 deals (batch).
- DB-03 requires CSV export from DuckDB queries, not from JSON artifacts — this means the db-export stage replaces the /export-csv skill for standard exports.

</specifics>

<deferred>
## Deferred Ideas

- Cross-deal queries (REC-01, SCALE-01) — v2 requirement, not in v1 scope
- Parallelized extraction for >50 deals (SCALE-02) — v2 requirement
- BM25 recovery for coverage gaps (REC-01) — v2 requirement
- Embedding-based deduplication (REC-02) — v2 requirement

</deferred>

---

*Phase: 05-integration-calibration*
*Context gathered: 2026-03-28*
