# Phase 5: Integration + Calibration - Research

**Researched:** 2026-03-28
**Domain:** DuckDB integration, pipeline orchestration, complexity routing, few-shot examples
**Confidence:** HIGH

## Summary

Phase 5 wires the existing pipeline stages into an end-to-end flow with DuckDB as the canonical structured store, adds complexity-based extraction routing, expands few-shot examples, and documents an orchestration contract. The core technical work is: (1) a new `db-load` stage that reads canonical extract + enrichment artifacts and loads them into a single multi-deal DuckDB file, (2) a new `db-export` stage that generates the review CSV from DuckDB queries rather than JSON artifacts, (3) a complexity routing wrapper around `compose-prompts` that decides single-pass vs chunked extraction, and (4) expanding `event_examples.md` from 2 examples to 4-5 covering the target patterns.

DuckDB 1.4.4 is already installed in the runtime environment. It is a zero-dependency embedded database with a Python API that supports `INSERT OR REPLACE`, compound primary keys, array columns, JSON columns, and `COPY TO` CSV export. All patterns needed for this phase were verified against the live runtime. The project has 9 deals with block counts ranging from 36 (petsmart-inc) to 235 (stec), and token estimates from 5,710 to 18,032. Three deals fall under the default 6,000-token chunk budget for single-pass; the rest require chunked extraction. The block-count threshold of 150 from the roadmap produces a 6-simple / 3-complex split, which aligns well with the token-based reality.

**Primary recommendation:** Implement `db-load` and `db-export` as new deterministic Python stages following the established pattern (dedicated module, CLI subcommand, Pydantic models, fail-fast gating). Keep the DuckDB schema flat and denormalized for simplicity. Complexity routing adds a thin decision layer around the existing `build_chunk_windows()` function. Few-shot examples expand in-place in the existing `event_examples.md` asset file.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Single multi-deal DuckDB database file (not per-deal). All deals load into the same database, enabling cross-deal queries. Database location is a project-level path (e.g., `data/pipeline.duckdb`).
- **D-02:** DuckDB loading happens after enrich-core as a new dedicated `db-load` stage with its own CLI command: `skill-pipeline db-load --deal <slug>`. It reads canonical extract artifacts (actors_raw.json, events_raw.json, spans.json) plus enrichment artifacts and inserts/upserts into DuckDB tables.
- **D-03:** CSV export migrates to a new deterministic Python stage: `skill-pipeline db-export --deal <slug>`. This generates deal_events.csv from DuckDB queries, replacing the local-agent `/export-csv` skill. Export becomes fully deterministic.
- **D-04:** Claude has discretion on the orchestration form. The approach should satisfy DB-02 ("without manual handoffs between core stages") while respecting the constraint that extraction stays in `.claude/skills/`.
- **D-05:** Orchestration must support both per-deal execution and batch execution. Testing: validate per-deal first, then batch.
- **D-06:** Claude has discretion on whether complexity routing is fully automatic or has a manual override flag.
- **D-07:** Claude has discretion on exact thresholds. Roadmap suggests `<=150 blocks, <=8 actors` but thresholds should be calibrated against actual deal data.
- **D-08:** Claude has discretion on few-shot example source (extracted from completed deals vs hand-crafted from filing text). Target patterns: NDA groups, ambiguous drops, cycle boundaries, range proposals, formal-round signals.
- **D-09:** Claude has discretion on whether to expand existing `prompt_assets/` files or build a structured example registry.

### Claude's Discretion
- DuckDB table schema (normalization level, column types, indexes)
- Whether db-load upserts or drops-and-reloads per deal
- Exact orchestration form (enhanced deal-agent, new CLI command, documented workflow, or combination)
- Whether to add a `--force-chunked`/`--force-single-pass` override flag to compose-prompts
- Whether to calibrate complexity thresholds from corpus data or use roadmap defaults
- Example format (flat markdown vs structured registry)
- How to handle the deferred chunk-budget overhead issue from Phase 2

### Deferred Ideas (OUT OF SCOPE)
- Cross-deal queries (REC-01, SCALE-01) -- v2 requirement, not in v1 scope
- Parallelized extraction for >50 deals (SCALE-02) -- v2 requirement
- BM25 recovery for coverage gaps (REC-01) -- v2 requirement
- Embedding-based deduplication (REC-02) -- v2 requirement
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DB-01 | DuckDB canonical database stores structured deal data as single source driving queries and CSV export | DuckDB 1.4.4 verified available; schema design, INSERT OR REPLACE, compound keys all validated |
| DB-02 | End-to-end pipeline run orchestrated without manual handoffs between core stages | Existing deal-agent SKILL.md already documents the flow; enhanced deal-agent + documented run contract recommended |
| DB-03 | CSV export generated from DuckDB canonical representation, not from JSON artifacts | DuckDB COPY TO CSV verified; export-csv skill column spec analyzed for query design |
| PROMPT-06 | Complexity-based routing: simple deals single-pass, complex deals multi-chunk | Corpus data analyzed: 6 simple / 3 complex by block count; token estimates validate thresholds |
| INFRA-07 | Few-shot examples expanded to 4-5 covering NDA groups, ambiguous drops, cycle boundaries, range proposals, formal-round signals | Current event_examples.md has 2 examples (range proposal, formal-round); 3 more needed for target patterns |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

These directives from CLAUDE.md constrain implementation:

- **No Python LLM wrapper:** Extraction, repair, enrichment, and export remain local-agent stages. `skill_pipeline` stays deterministic.
- **Fail fast:** No silent fallbacks. Fail on missing files, schema drift, contradictory state.
- **Pydantic-first schemas:** All models use Pydantic BaseModel with `extra="forbid"` via SkillModel.
- **snake_case everywhere:** Python names and JSON keys.
- **Filing text is sole source of truth:** Benchmark materials forbidden until export completes.
- **Agent/provider agnostic:** No vendor-specific SDK dependencies in skill_pipeline.
- **Python 3.11+:** Explicit types on public functions.
- **Focused regression tests** for behavior changes (canonicalization, verification, coverage, enrich-core gating).
- **Artifact path contracts:** Encoded in `skill_pipeline/paths.py` via `SkillPathSet`.
- **CLI pattern:** Each stage has a CLI subcommand in `cli.py`.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| duckdb | 1.4.4 | Embedded analytical database | Already installed in runtime; zero-config embedded; supports SQL, arrays, JSON, CSV export |
| pydantic | >=2.0 | Schema models for db-load/db-export artifacts | Existing project convention; SkillModel base class |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | >=8.0 | Test framework | Existing; 230 tests pass; add db-load and db-export tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| DuckDB | SQLite | DuckDB is already installed, has native array/JSON types, and COPY TO CSV; SQLite would need more adapter code |
| DROP+INSERT per deal | INSERT OR REPLACE | DROP+INSERT is simpler and safer for full-deal reloads; upsert is better for incremental updates. Recommend DROP+INSERT since deals always reload fully from artifacts. |

**Installation:**
```bash
pip install duckdb>=1.2
```

**Version verification:** DuckDB 1.4.4 is confirmed installed and operational in the current Python 3.13 runtime. The `duckdb` package has zero required dependencies.

**Note:** DuckDB is NOT currently listed in `pyproject.toml` dependencies. It must be added:
```toml
dependencies = [
  "duckdb>=1.2",
  ...
]
```

## Architecture Patterns

### Recommended Project Structure
```
skill_pipeline/
  db_load.py          # new: DuckDB loading stage
  db_export.py        # new: DuckDB-to-CSV export stage
  db_schema.py        # new: DuckDB table DDL and connection helper
  complexity.py       # new: complexity routing decision logic
  cli.py              # modified: add db-load, db-export subcommands
  paths.py            # modified: add database_path property
  models.py           # modified: add DbLoadStageSummary, DbExportStageSummary
  deal_agent.py       # modified: add db_load, db_export stage summaries
  compose_prompts.py  # modified: integrate complexity routing
  prompt_assets/
    event_examples.md # modified: expand from 2 to 5 examples
data/
  pipeline.duckdb     # new: single multi-deal database file
```

### Pattern 1: Stage Module Pattern (Established)
**What:** Each pipeline stage is a dedicated Python module with a `run_<stage>()` entry point, dedicated CLI subcommand, Pydantic output models, and fail-fast gating.
**When to use:** Always. This is the established pattern for all existing stages.
**Example:**
```python
# Source: skill_pipeline/enrich_core.py (established pattern)
def run_enrich_core(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    paths = build_skill_paths(deal_slug, project_root=project_root)
    _require_gate_artifacts(paths)  # fail-fast on missing prerequisites
    artifacts = load_extract_artifacts(paths)
    # ... processing ...
    _write_json(paths.deterministic_enrichment_path, result)
    return 0
```

### Pattern 2: Gating Pattern (Established)
**What:** Stages verify all prerequisite artifacts exist and pass before running. Uses `_require_gate_artifacts()` pattern from `enrich_core.py`.
**When to use:** `db-load` must gate on enrich-core completion. `db-export` must gate on `db-load` completion.
**Example:**
```python
# db-load should gate on:
# 1. canonical extract artifacts (actors_raw.json, events_raw.json, spans.json)
# 2. check, verify, coverage, gates all passing
# 3. deterministic_enrichment.json exists
# This is the same set as enrich-core plus the enrichment output itself.
```

### Pattern 3: Drop-and-Reload Per Deal
**What:** When loading a deal into DuckDB, delete all existing rows for that deal_slug and reinsert from artifacts. This is simpler and safer than upsert for full-deal reloads.
**When to use:** Always for `db-load`. Deals are always fully reprocessed from artifacts.
**Example:**
```python
con.execute("DELETE FROM actors WHERE deal_slug = ?", [deal_slug])
con.executemany(
    "INSERT INTO actors VALUES (?, ?, ?, ?, ?, ?, ?)",
    actor_rows,
)
```

### Pattern 4: Connection Helper with Context Manager
**What:** A thin connection helper that opens the DuckDB file, ensures tables exist, and provides a context manager.
**When to use:** Both `db-load` and `db-export` need database access.
**Example:**
```python
def open_pipeline_db(db_path: Path, *, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(db_path), read_only=read_only)
    if not read_only:
        _ensure_schema(con)
    return con
```

### Anti-Patterns to Avoid
- **Per-deal database files:** D-01 explicitly requires a single multi-deal database. Do not create `data/skill/<slug>/db/`.
- **ORM abstraction:** DuckDB's Python API is already simple SQL. Adding SQLAlchemy or similar would be overengineering.
- **Dynamic schema from Pydantic:** Do not generate DDL from Pydantic models at runtime. Define explicit CREATE TABLE statements that match the artifact contracts.
- **Storing raw JSON blobs:** Do not dump entire JSON artifacts into a single TEXT column. Flatten into typed columns for queryability.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSV generation from structured data | Custom string formatting | DuckDB `COPY TO` with SQL query | Handles quoting, escaping, NULL formatting correctly |
| Upsert/dedup | Custom merge logic | DuckDB `DELETE + INSERT` in transaction | Atomic, simple, no edge cases with partial updates |
| Token estimation | New heuristic | Existing `estimate_block_tokens()` | Already calibrated with `ceil(word_count * 1.35)` |
| Chunk planning | New chunker | Existing `build_chunk_windows()` | Already handles single-pass vs chunked with overlap |

**Key insight:** The DuckDB layer is a thin persistence + query layer on top of existing artifacts. It does not replace or duplicate any pipeline logic. Artifacts remain the authoritative intermediate format; DuckDB is the canonical structured output.

## Common Pitfalls

### Pitfall 1: DuckDB File Locking
**What goes wrong:** DuckDB uses file-level locking. Two processes opening the same database file for writing will conflict.
**Why it happens:** Attempting parallel `db-load` for multiple deals simultaneously.
**How to avoid:** Load deals sequentially into the shared database. The batch command should iterate deals, not parallelize. DuckDB is fast enough that 9 deals will load in under a second.
**Warning signs:** `IOException: Could not set lock on file` errors.

### Pitfall 2: Schema Drift Between Artifacts and DuckDB
**What goes wrong:** Pydantic models evolve but DDL is not updated, causing column mismatches at load time.
**Why it happens:** DDL and Pydantic models are separate definitions.
**How to avoid:** Test fixtures that load artifacts into DuckDB and verify round-trip. Add a test that validates DuckDB schema matches expected columns.
**Warning signs:** `BinderException` on INSERT statements.

### Pitfall 3: CSV Export Format Mismatch
**What goes wrong:** The DuckDB-based CSV export produces different column ordering, NULL handling, or date formatting than the existing `/export-csv` skill.
**Why it happens:** The export-csv skill has specific conventions (e.g., `NA` for NULLs, `YYYY-MM-DD 00:00:00` date format, fractional bidderIDs, deal header block).
**How to avoid:** The `db-export` stage must reproduce the exact column spec from the export-csv SKILL.md. Test against the existing stec `deal_events.csv` as baseline.
**Warning signs:** Diff between old and new CSV exports shows structural differences.

### Pitfall 4: Complexity Routing Threshold Edge Cases
**What goes wrong:** A deal near the threshold gets inconsistent routing between runs.
**Why it happens:** Block count is deterministic but actor count is not known before extraction. The threshold check before compose-prompts only has block count available.
**How to avoid:** Route based on block count alone at compose-prompts time (before actors are extracted). The `<=150 blocks` criterion is sufficient since all deals with >150 blocks also have >8 actors based on the two completed deals (stec: 235 blocks, 22 actors; medivation: 165 blocks, 16 actors).
**Warning signs:** Deals flip between single-pass and chunked between runs.

### Pitfall 5: Missing DuckDB Dependency in pyproject.toml
**What goes wrong:** `pip install -e .` does not install duckdb, causing ImportError in production.
**Why it happens:** DuckDB is installed system-wide but not declared as a project dependency.
**How to avoid:** Add `"duckdb>=1.2"` to `pyproject.toml` dependencies immediately.
**Warning signs:** `ModuleNotFoundError: No module named 'duckdb'` in fresh environments.

### Pitfall 6: Enrichment Artifact Fragmentation
**What goes wrong:** DuckDB loading expects a single enrichment artifact, but the pipeline produces both `deterministic_enrichment.json` (from enrich-core) and optionally `enrichment.json` (from /enrich-deal).
**Why it happens:** The pipeline has a deterministic layer (enrich-core) and an optional interpretive layer (/enrich-deal). DuckDB must handle both cases.
**How to avoid:** Load from `deterministic_enrichment.json` as the baseline (always present after enrich-core). If `enrichment.json` exists, overlay its additional fields. The db-load stage should work with enrich-core output alone, since /enrich-deal is an optional interpretive step.
**Warning signs:** Missing enrichment columns in DuckDB when /enrich-deal has not run.

## Code Examples

### DuckDB Schema DDL
```python
# Based on artifact analysis of stec data
SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS actors (
    deal_slug TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    canonical_name TEXT NOT NULL,
    aliases TEXT[],
    role TEXT NOT NULL,
    advisor_kind TEXT,
    advised_actor_id TEXT,
    bidder_kind TEXT,
    listing_status TEXT,
    geography TEXT,
    is_grouped BOOLEAN NOT NULL,
    group_size INTEGER,
    group_label TEXT,
    evidence_span_ids TEXT[],
    PRIMARY KEY (deal_slug, actor_id)
);

CREATE TABLE IF NOT EXISTS events (
    deal_slug TEXT NOT NULL,
    event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    date_raw_text TEXT,
    date_sort DATE,
    date_precision TEXT,
    actor_ids TEXT[],
    summary TEXT NOT NULL,
    evidence_span_ids TEXT[],
    terms_per_share DOUBLE,
    terms_range_low DOUBLE,
    terms_range_high DOUBLE,
    terms_consideration_type TEXT,
    whole_company_scope BOOLEAN,
    drop_reason_text TEXT,
    round_scope TEXT,
    invited_actor_ids TEXT[],
    executed_with_actor_id TEXT,
    nda_signed BOOLEAN,
    PRIMARY KEY (deal_slug, event_id)
);

CREATE TABLE IF NOT EXISTS spans (
    deal_slug TEXT NOT NULL,
    span_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    filing_type TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    block_ids TEXT[],
    quote_text TEXT NOT NULL,
    match_type TEXT NOT NULL,
    PRIMARY KEY (deal_slug, span_id)
);

CREATE TABLE IF NOT EXISTS enrichment (
    deal_slug TEXT NOT NULL,
    event_id TEXT NOT NULL,
    dropout_label TEXT,
    dropout_basis TEXT,
    bid_label TEXT,
    bid_rule_applied DOUBLE,
    bid_basis TEXT,
    PRIMARY KEY (deal_slug, event_id)
);

CREATE TABLE IF NOT EXISTS cycles (
    deal_slug TEXT NOT NULL,
    cycle_id TEXT NOT NULL,
    start_event_id TEXT NOT NULL,
    end_event_id TEXT NOT NULL,
    boundary_basis TEXT NOT NULL,
    PRIMARY KEY (deal_slug, cycle_id)
);

CREATE TABLE IF NOT EXISTS rounds (
    deal_slug TEXT NOT NULL,
    announcement_event_id TEXT NOT NULL,
    deadline_event_id TEXT,
    round_scope TEXT NOT NULL,
    invited_actor_ids TEXT[],
    active_bidders_at_time INTEGER NOT NULL,
    is_selective BOOLEAN NOT NULL,
    PRIMARY KEY (deal_slug, announcement_event_id)
);
"""
```

### db-load Stage Pattern
```python
def run_db_load(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    paths = build_skill_paths(deal_slug, project_root=project_root)
    db_path = project_root / "data" / "pipeline.duckdb"

    # Gate: require canonical extract + enrichment
    if not paths.actors_raw_path.exists():
        raise FileNotFoundError(f"Missing: {paths.actors_raw_path}")
    if not paths.events_raw_path.exists():
        raise FileNotFoundError(f"Missing: {paths.events_raw_path}")
    if not paths.spans_path.exists():
        raise FileNotFoundError(f"Missing: {paths.spans_path}")
    if not paths.deterministic_enrichment_path.exists():
        raise FileNotFoundError(f"Missing: {paths.deterministic_enrichment_path}")

    artifacts = load_extract_artifacts(paths)
    if artifacts.mode != "canonical":
        raise ValueError("db-load requires canonical extract artifacts")

    con = open_pipeline_db(db_path)
    try:
        con.execute("BEGIN TRANSACTION")
        _delete_deal(con, deal_slug)
        _load_actors(con, deal_slug, artifacts.actors)
        _load_events(con, deal_slug, artifacts.events)
        _load_spans(con, deal_slug, artifacts.spans)
        _load_enrichment(con, deal_slug, paths)
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    finally:
        con.close()
    return 0
```

### db-export Stage Pattern
```python
def run_db_export(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    paths = build_skill_paths(deal_slug, project_root=project_root)
    db_path = project_root / "data" / "pipeline.duckdb"

    if not db_path.exists():
        raise FileNotFoundError(f"Pipeline database not found: {db_path}")

    con = open_pipeline_db(db_path, read_only=True)
    try:
        # Verify deal exists in database
        count = con.execute(
            "SELECT COUNT(*) FROM events WHERE deal_slug = ?", [deal_slug]
        ).fetchone()[0]
        if count == 0:
            raise ValueError(f"No events found for deal '{deal_slug}' in database")

        # Build CSV using SQL query that matches export-csv column spec
        ensure_output_directories(paths)
        _write_deal_csv(con, deal_slug, paths)
    finally:
        con.close()
    return 0
```

### Complexity Routing Pattern
```python
# Source: compose_prompts.py integration point
SIMPLE_DEAL_MAX_BLOCKS = 150

def classify_deal_complexity(
    blocks: list[ChronologyBlock],
    *,
    max_blocks: int = SIMPLE_DEAL_MAX_BLOCKS,
) -> Literal["simple", "complex"]:
    """Classify a deal as simple or complex based on block count.

    Simple deals use single-pass extraction (entire filing in one prompt).
    Complex deals use chunked extraction with overlap windows.
    """
    if len(blocks) <= max_blocks:
        return "simple"
    return "complex"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| JSON artifacts only | DuckDB + JSON artifacts | Phase 5 | CSV export moves from agent skill to deterministic stage |
| Manual single-pass/chunked choice | Automatic complexity routing | Phase 5 | Compose-prompts auto-selects based on block count |
| 2 few-shot examples | 4-5 few-shot examples | Phase 5 | Better extraction coverage for edge patterns |
| Thin deal-agent summary | Enhanced orchestration contract | Phase 5 | End-to-end flow documented with db-load and db-export stages |

**Deprecated/outdated:**
- `/export-csv` local-agent skill: replaced by `skill-pipeline db-export` for standard exports. The skill document remains for reference but the deterministic stage is the primary export path.

## Open Questions

1. **Enrichment overlay strategy**
   - What we know: `deterministic_enrichment.json` always exists after enrich-core. `enrichment.json` may exist after optional /enrich-deal.
   - What's unclear: Whether db-load should require `enrichment.json` or work with `deterministic_enrichment.json` alone.
   - Recommendation: Load from `deterministic_enrichment.json` as baseline. The db-export CSV uses enrichment fields (dropout labels, bid classifications) that come from deterministic enrichment. If `enrichment.json` exists and has additional fields (initiation_judgment, advisory_verification), load those as supplementary columns. This keeps db-load functional without the optional interpretive layer.

2. **CSV export exact parity**
   - What we know: The export-csv skill has specific conventions (fractional bidderIDs, deal header block, type-on-first-row-only, NA for NULLs).
   - What's unclear: Whether 100% byte-identical output is required or just semantically equivalent.
   - Recommendation: Target semantic equivalence with the same column spec and formatting rules. Test against stec baseline CSV to validate. Small differences in whitespace or quoting are acceptable as long as the data is identical.

3. **Chunk-budget overhead (deferred from Phase 2)**
   - What we know: Token estimation uses `ceil(word_count * 1.35)`. Actual stec packet sizes may diverge for legal text.
   - What's unclear: How much the heuristic over/under-estimates for SEC filing prose.
   - Recommendation: Address during complexity routing calibration. Compare estimated tokens vs actual chunk window count for stec. If the heuristic is significantly off, adjust the multiplier. This is a calibration step, not a redesign.

## Corpus Complexity Analysis

Based on actual corpus data (all 9 deals):

| Deal | Blocks | Est. Tokens | Single-Pass (<= 6000) | Simple (<= 150 blocks) |
|------|--------|-------------|------------------------|------------------------|
| petsmart-inc | 36 | 5,769 | YES | YES |
| providence-worcester | 41 | 5,710 | YES | YES |
| saks | 65 | 5,713 | YES | YES |
| penford | 95 | 9,619 | NO | YES |
| imprivata | 101 | 10,817 | NO | YES |
| zep | 114 | 7,679 | NO | YES |
| medivation | 165 | 11,311 | NO | NO |
| mac-gray | 180 | 12,769 | NO | NO |
| stec | 235 | 18,032 | NO | NO |

**Threshold recommendation:** Use `<=150 blocks` as the complexity routing threshold (from roadmap D-07). This produces a 6-simple / 3-complex split. The token budget of 6,000 already handles the single-pass vs chunked decision within `build_chunk_windows()`. Complexity routing at the block-count level is a higher-level decision about extraction strategy, not just chunk sizing.

**Important distinction:** "Simple" in complexity routing means the deal can be reasonably processed with a large context window in single-pass mode (one actor prompt + one event prompt). Even "simple" deals like penford (95 blocks, ~9,600 tokens) exceed the current 6,000-token chunk budget and will be chunked. Complexity routing should set a higher token budget for simple deals (e.g., no limit, forcing single-pass) rather than relying solely on the 6,000-token default.

**Recommended approach:** Add a `--routing` flag to `compose-prompts` with values `auto`, `single-pass`, `chunked`. In `auto` mode, deals with `<=150` blocks use a very large chunk budget (effectively single-pass). Deals with `>150` blocks use the default 6,000-token budget. This integrates naturally with the existing `build_chunk_windows()` function.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All stages | Yes | 3.13.5 | -- |
| duckdb | DB-01, DB-03 | Yes (system) | 1.4.4 | -- |
| pydantic | Schema models | Yes | >=2.0 | -- |
| pytest | Testing | Yes | >=8.0 | -- |
| skill-pipeline CLI | All stages | Yes | 0.1.0 | -- |

**Missing dependencies with no fallback:**
- `duckdb` must be added to `pyproject.toml` (currently system-installed only)

**Missing dependencies with fallback:**
- None

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 8.0 |
| Config file | pyproject.toml (implicit) |
| Quick run command | `python -m pytest -q --tb=short` |
| Full suite command | `python -m pytest -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DB-01 | DuckDB schema creation and multi-deal loading | unit | `python -m pytest tests/test_skill_db_load.py -x` | No -- Wave 0 |
| DB-01 | Round-trip: load artifacts, query back, verify match | unit | `python -m pytest tests/test_skill_db_load.py::test_round_trip -x` | No -- Wave 0 |
| DB-02 | Orchestration flow documents all stages including db-load and db-export | unit | `python -m pytest tests/test_runtime_contract_docs.py -x` | Yes (existing, needs update) |
| DB-03 | CSV export from DuckDB matches expected column spec | unit | `python -m pytest tests/test_skill_db_export.py -x` | No -- Wave 0 |
| DB-03 | CSV export produces valid output for stec baseline | integration | `python -m pytest tests/test_skill_db_export.py::test_stec_baseline -x` | No -- Wave 0 |
| PROMPT-06 | Complexity routing classifies deals correctly | unit | `python -m pytest tests/test_skill_compose_prompts.py::test_complexity_routing -x` | No -- Wave 0 |
| PROMPT-06 | compose-prompts respects routing mode flag | unit | `python -m pytest tests/test_skill_compose_prompts.py::test_routing_flag -x` | No -- Wave 0 |
| INFRA-07 | Event examples file has >= 4 examples | unit | `python -m pytest tests/test_skill_compose_prompts.py::test_event_examples_count -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest -q --tb=short`
- **Per wave merge:** `python -m pytest -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_skill_db_load.py` -- covers DB-01 (schema, loading, round-trip)
- [ ] `tests/test_skill_db_export.py` -- covers DB-03 (CSV format, stec baseline)
- [ ] `tests/test_skill_compose_prompts.py` -- needs new tests for PROMPT-06 complexity routing
- [ ] `duckdb>=1.2` added to `pyproject.toml` dependencies

## Sources

### Primary (HIGH confidence)
- [DuckDB Python API Overview](https://duckdb.org/docs/stable/clients/python/overview) -- connection management, query API, CSV export
- [DuckDB Insert Statement](https://duckdb.org/docs/stable/sql/statements/insert) -- INSERT OR REPLACE, ON CONFLICT DO UPDATE
- [DuckDB CSV Export](https://duckdb.org/docs/stable/guides/file_formats/csv_export) -- COPY TO syntax and options
- Live corpus analysis -- all 9 deals' block counts and token estimates computed directly
- Live DuckDB 1.4.4 verification -- compound keys, arrays, JSON, upsert, COPY TO all tested

### Secondary (MEDIUM confidence)
- `skill_pipeline/` codebase analysis -- existing stage patterns, models, CLI structure, paths
- `.claude/skills/export-csv/SKILL.md` -- CSV column spec, bidderID algorithm, formatting rules
- `.claude/skills/deal-agent/SKILL.md` -- orchestration procedure and gating

### Tertiary (LOW confidence)
- None -- all findings verified against live code or live DuckDB runtime

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- DuckDB verified installed and operational, all API patterns tested
- Architecture: HIGH -- follows established stage module pattern from existing codebase
- Pitfalls: HIGH -- based on direct analysis of artifact shapes, DuckDB behavior, and CSV format
- Complexity routing: HIGH -- based on actual corpus token analysis of all 9 deals
- Few-shot examples: MEDIUM -- target patterns identified but example content not yet drafted

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable -- DuckDB API and project patterns are well-established)
