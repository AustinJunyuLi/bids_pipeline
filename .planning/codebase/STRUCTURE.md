# Codebase Structure

**Analysis Date:** 2026-03-27

## Directory Layout

```
bids_data/
├── skill_pipeline/              # Single installed Python package with CLI
│   ├── __init__.py              # Exports run_deal_agent
│   ├── cli.py                   # Command routing and argument parsing
│   ├── config.py                # Path constants and filing type preferences
│   ├── models.py                # Pydantic schemas for all artifacts (raw, canonical, reports)
│   ├── paths.py                 # SkillPathSet builder and directory creation
│   ├── seeds.py                 # Seed CSV loader
│   ├── deal_agent.py            # Preflight status summarizer
│   ├── extract_artifacts.py     # Unified loader for legacy/canonical extract artifacts
│   ├── canonicalize.py          # Schema upgrade, dedup, NDA-gate, unnamed-party recovery
│   ├── check.py                 # Structural verification gate
│   ├── verify.py                # Quote resolution and referential integrity gate
│   ├── coverage.py              # Source evidence coverage audit
│   ├── enrich_core.py           # Deterministic enrichment (rounds, bids, cycles)
│   ├── provenance.py            # Span resolution and quote matching helpers
│   │
│   ├── raw/                     # Immutable filing freeze layer
│   │   ├── __init__.py
│   │   ├── fetch.py             # Filing download and SHA256 freezing
│   │   ├── discover.py          # Candidate ranking and selection
│   │   └── stage.py             # Orchestration: fetch_raw_deal()
│   │
│   ├── preprocess/              # Source preprocessing orchestrator
│   │   ├── __init__.py
│   │   └── source.py            # Orchestration: preprocess_source_deal()
│   │
│   ├── source/                  # Chronology and evidence extraction
│   │   ├── __init__.py
│   │   ├── locate.py            # Chronology candidate detection via regex
│   │   ├── blocks.py            # Chronology block building from candidate
│   │   ├── evidence.py          # Evidence item scanning and classification
│   │   ├── fetch.py             # (Unused; legacy artifact)
│   │   ├── discovery.py         # Chronology candidate ranking
│   │   ├── ranking.py           # Filing candidate ranking (CIK extraction)
│   │   └── supplementary.py     # Supplementary filing logic (not used in seed-only mode)
│   │
│   ├── normalize/               # Quote and date normalization
│   │   ├── __init__.py
│   │   ├── quotes.py            # find_anchor_in_segment(), quote matching logic
│   │   └── dates.py             # Date parsing and precision inference
│   │
│   ├── pipeline_models/         # Pydantic schema definitions for artifacts
│   │   ├── __init__.py
│   │   ├── common.py            # Enums (ActorRole, EventType, DatePrecision, etc.)
│   │   ├── raw.py               # Raw discovery and document registry schemas
│   │   └── source.py            # Filing candidates, chronology, evidence, seed deal
│   │
│   ├── schemas/                 # (Legacy; schema defs now in models.py and pipeline_models/)
│   │   └── __pycache__/
│   │
│   ├── stages/                  # (Organized stage modules; some duplicated from root)
│   │   ├── enrich/
│   │   │   └── __pycache__/
│   │   ├── preprocess/
│   │   │   └── __pycache__/
│   │   └── __pycache__/
│   │
│   └── core/                    # (Legacy/unused)
│       └── __pycache__/
│
├── data/                        # Data artifacts (generated and committed selectively)
│   ├── seeds.csv                # Deal seed list (deal_slug, target_name, acquirer, etc.)
│   ├── deals/                   # Per-deal source artifacts shared across skills
│   │   ├── imprivata/source/
│   │   │   ├── chronology_blocks.jsonl    # Parsed chronology section
│   │   │   └── evidence_items.jsonl       # Scanned evidence cues
│   │   ├── mac-gray/source/
│   │   ├── medivation/source/
│   │   └── ...other deals.../source/
│   │
│   ├── skill/                   # Per-deal skill workflow outputs
│   │   ├── imprivata/
│   │   │   ├── extract/
│   │   │   │   ├── actors_raw.json (or actors.json if canonical)
│   │   │   │   ├── events_raw.json (or events.json if canonical)
│   │   │   │   └── spans.json (required if canonical)
│   │   │   ├── check/
│   │   │   │   └── check_report.json
│   │   │   ├── verify/
│   │   │   │   ├── verification_log.json
│   │   │   │   └── verification_findings.json
│   │   │   ├── coverage/
│   │   │   │   ├── coverage_findings.json
│   │   │   │   └── coverage_summary.json
│   │   │   ├── enrich/
│   │   │   │   ├── deterministic_enrichment.json
│   │   │   │   └── enrichment.json (optional later layer)
│   │   │   ├── export/
│   │   │   │   └── deal_events.csv
│   │   │   └── canonicalize/
│   │   │       └── canonicalize_log.json
│   │   └── ...other deals.../
│   │
│   └── runs/                    # (Legacy run tracking; minimal usage)
│
├── raw/                         # Immutable frozen filings per deal
│   ├── imprivata/
│   │   ├── filings/
│   │   │   └── {document_id}.txt        # Raw filing text
│   │   ├── discovery.json               # Candidate ranking results
│   │   └── document_registry.json       # Frozen document metadata
│   ├── mac-gray/
│   └── ...other deals.../
│
├── tests/                       # Pytest suite organized by stage
│   ├── conftest.py              # (Shared fixtures if any)
│   ├── test_skill_raw_stage.py
│   ├── test_skill_preprocess_source.py
│   ├── test_skill_canonicalize.py
│   ├── test_skill_check.py
│   ├── test_skill_verify.py
│   ├── test_skill_coverage.py
│   ├── test_skill_enrich_core.py
│   ├── test_skill_pipeline.py
│   ├── test_skill_provenance.py
│   ├── test_benchmark_separation_policy.py
│   └── test_skill_mirror_sync.py
│
├── .planning/                   # GSD codebase mapping output
│   ├── codebase/
│   │   ├── ARCHITECTURE.md      # (This project's architecture)
│   │   ├── STRUCTURE.md         # (This file)
│   │   ├── STACK.md             # (Technology dependencies)
│   │   ├── INTEGRATIONS.md      # (External services)
│   │   ├── CONVENTIONS.md       # (Code style and patterns)
│   │   └── TESTING.md           # (Test patterns and coverage)
│   │
│   └── phases/                  # GSD phase plans
│
├── .claude/                     # Canonical skill tree
│   └── skills/
│
├── .codex/                      # Derived from .claude/ (synced via scripts/sync_skill_mirrors.py)
│   └── skills/
│
├── .cursor/                     # Derived from .claude/ (synced via scripts/sync_skill_mirrors.py)
│   └── skills/
│
├── scripts/
│   └── sync_skill_mirrors.py    # Sync .codex/ and .cursor/ from .claude/
│
├── docs/                        # Design notes and implementation guides
│   └── (Various .md files with architecture and design decisions)
│
├── diagnosis/                   # Post-export benchmark diagnostics
│   ├── deepthink/               # Reasoning traces and comparisons
│   │   └── 2026-03-{date}/
│   │       ├── round_1/
│   │       │   └── 00_PROJECT_OVERVIEW.md
│   │       └── round_2/, round_3/, ...
│   │
│   └── (Other diagnostic outputs)
│
├── example/                     # Reference example deals (post-export only)
│   └── (Exemplary extraction outputs for benchmarking)
│
├── quality_reports/             # Post-processing QA reports
│   └── (Coverage, completeness, and quality metrics)
│
├── pyproject.toml               # Package config with skill-pipeline CLI entrypoint
├── pytest.ini                   # Test runner config
├── requirements.txt             # Top-level dependencies (mainly anthropic, openai, edgartools, pydantic)
├── CLAUDE.md                    # Authoritative project instructions
├── AGENTS.md                    # Agent notes
└── pipeline_overhaul.txt        # Development notes on pipeline refactoring
```

## Directory Purposes

**skill_pipeline/:**
- Purpose: Single installed CLI package with all stages and helpers
- Contains: All Python modules for fetching, preprocessing, validation, enrichment
- Key files: `cli.py` (entry point), `models.py` (schemas), `paths.py` (artifact routing)

**skill_pipeline/raw/:**
- Purpose: Immutable filing freeze and discovery
- Contains: SEC fetch logic, candidate ranking, document registry
- Key files: `fetch.py` (download & freeze), `discover.py` (ranking), `stage.py` (orchestration)

**skill_pipeline/source/:**
- Purpose: Chronology and evidence extraction from frozen text
- Contains: Regex-based localization, block parsing, evidence scanning
- Key files: `locate.py` (chronology detection), `blocks.py` (block building), `evidence.py` (evidence classification)

**skill_pipeline/normalize/:**
- Purpose: Quote and date normalization for span resolution and canonical form
- Contains: Anchor text matching, date parsing
- Key files: `quotes.py` (find_anchor_in_segment), `dates.py` (parse_resolved_date)

**skill_pipeline/pipeline_models/:**
- Purpose: Pydantic schema definitions for all artifacts
- Contains: SeedDeal, FilingCandidate, ChronologyBlock, EvidenceItem, etc.
- Key files: `common.py` (enums), `source.py` (source artifacts), `raw.py` (discovery/registry)

**data/seeds.csv:**
- Purpose: Deal seed list with target name, acquirer, filing URL, announcement date
- Contents: One row per deal with deal_slug, is_reference flag
- Committed: Yes; canonical source for deal roster

**data/deals/<slug>/source/:**
- Purpose: Source artifacts shared across skill stages
- Contents: Chronology blocks and evidence items in JSONL format
- Generated by: `preprocess-source` stage
- Committed: Yes; upstream for all downstream analysis

**data/skill/<slug>/extract/:**
- Purpose: LLM-extracted actors and events (legacy or canonical form)
- Contents: actors_raw.json, events_raw.json (legacy) OR actors.json, events.json + spans.json (canonical)
- Generated by: External `/extract-deal` command
- Committed: Yes; input to all gates

**data/skill/<slug>/{check,verify,coverage,enrich,export,canonicalize}/:**
- Purpose: Per-stage output artifacts and reports
- Contents: JSON reports with findings, summaries, and derived data
- Generated by: Each stage (check → verify → coverage → enrich-core → export)
- Committed: Yes; audit trail and state preservation

**raw/<slug>/filings/:**
- Purpose: Immutable frozen SEC filing text
- Contents: {document_id}.txt with content hash (SHA256) in registry
- Generated by: `raw-fetch` stage
- Committed: Yes; immutable truth source
- Notes: Never modified after creation; document_registry.json tracks metadata

**tests/:**
- Purpose: Pytest suite organized by stage with focused regression tests
- Pattern: test_skill_<stage>.py files with fixtures and parametrized tests
- Coverage: Each major stage (raw, preprocess, canonicalize, check, verify, coverage, enrich) has dedicated test file

## Key File Locations

**Entry Points:**
- `skill_pipeline/cli.py`: Main CLI dispatcher (build_parser, main())
- `skill_pipeline/deal_agent.py`: Preflight status summarizer (run_deal_agent)
- `pyproject.toml`: Defines `skill-pipeline` console script entry point

**Configuration:**
- `skill_pipeline/config.py`: Path constants (PROJECT_ROOT, RAW_DIR, DEALS_DIR, SKILL_DIR, SEEDS_PATH)
- `pytest.ini`: Test runner config with testpaths = tests/
- `.env.local`: Local environment variables (not committed; contains secrets)

**Core Logic:**
- `skill_pipeline/models.py`: All Pydantic schemas (400+ lines) including SkillPathSet, artifact models, gate findings
- `skill_pipeline/paths.py`: SkillPathSet builder with consistent path computation for all stages
- `skill_pipeline/pipeline_models/common.py`: Enums (ActorRole, EventType, DatePrecision, ConsiderationType, etc.)
- `skill_pipeline/extract_artifacts.py`: Unified loader for legacy/canonical extract artifacts

**Stage Orchestrators:**
- `skill_pipeline/raw/stage.py`: fetch_raw_deal()
- `skill_pipeline/preprocess/source.py`: preprocess_source_deal()
- `skill_pipeline/canonicalize.py`: run_canonicalize()
- `skill_pipeline/check.py`: run_check()
- `skill_pipeline/verify.py`: run_verify()
- `skill_pipeline/coverage.py`: run_coverage()
- `skill_pipeline/enrich_core.py`: run_enrich_core()

**Support Modules:**
- `skill_pipeline/raw/fetch.py`: fetch_filing_contents(), freeze_raw_filing(), atomic_write_json()
- `skill_pipeline/raw/discover.py`: build_raw_discovery_manifest()
- `skill_pipeline/source/locate.py`: select_chronology() with regex-based candidate evaluation
- `skill_pipeline/source/blocks.py`: build_chronology_blocks() line-aware block builder
- `skill_pipeline/source/evidence.py`: scan_document_evidence() evidence classification
- `skill_pipeline/normalize/quotes.py`: find_anchor_in_segment() quote matching with normalization
- `skill_pipeline/normalize/dates.py`: parse_resolved_date() date parsing with precision
- `skill_pipeline/provenance.py`: resolve_text_span() bridge evidence refs to file locations
- `skill_pipeline/seeds.py`: load_seed_entry() CSV loader

**Testing:**
- `tests/test_skill_pipeline.py`: Integration tests for full pipeline
- `tests/test_skill_raw_stage.py`: raw-fetch stage tests
- `tests/test_skill_preprocess_source.py`: preprocess-source stage tests
- `tests/test_skill_canonicalize.py`: canonicalize stage tests with dedup/NDA-gating
- `tests/test_skill_check.py`: check gate tests
- `tests/test_skill_verify.py`: verify gate tests with quote matching
- `tests/test_skill_coverage.py`: coverage audit tests
- `tests/test_skill_enrich_core.py`: enrich-core stage tests with round pairing
- `tests/test_skill_provenance.py`: provenance and span resolution tests
- `tests/test_benchmark_separation_policy.py`: Verify benchmark materials not consulted before export

## Naming Conventions

**Files:**
- Module files: `snake_case.py` (e.g., `canonicalize.py`, `check.py`, `deal_agent.py`)
- Package subdirectories: `snake_case/` (e.g., `raw/`, `source/`, `normalize/`)
- Test files: `test_<behavior>.py` (e.g., `test_skill_verify.py`)
- Artifact files: `<name>.json` or `<name>.jsonl` (e.g., `actors_raw.json`, `chronology_blocks.jsonl`)

**Directories:**
- Deal slug directories: `kebab-case` (e.g., `imprivata`, `mac-gray`, `saks`)
- Stage output directories: `<stage_name>/` matching CLI command (e.g., `extract/`, `check/`, `verify/`)

**Functions:**
- Public stage entrypoints: `run_<stage_name>()` (e.g., run_check, run_verify, run_canonicalize)
- Helpers: `_<descriptor>()` (leading underscore for private; e.g., _load_document_lines, _write_json)
- Loaders: `load_<artifact>()` or `<artifact>_from_<source>()`

**Variables:**
- Snake case throughout: `actor_id`, `document_registry`, `evidence_items`, `chronology_blocks`
- Line numbers: `start_line`, `end_line` (1-indexed matching filing text convention)
- IDs: `block_id`, `actor_id`, `event_id`, `evidence_id`, `span_id` (not abbreviated)

**Types:**
- Pydantic models: `PascalCase` (e.g., SkillPathSet, ChronologyBlock, VerificationFinding)
- Enums: `PascalCase` with CONSTANT_CASE values (e.g., `EventType.PROPOSAL`, `ActorRole.BIDDER`)
- Dataclasses: `PascalCase` (e.g., LoadedExtractArtifacts, CoverageCue)

## Where to Add New Code

**New Feature (Stage or Module):**
- Primary code: Create module in `skill_pipeline/<stage_name>.py` or subpackage `skill_pipeline/<stage_name>/`
- Tests: Create `tests/test_skill_<stage_name>.py`
- CLI integration: Add subparser in `skill_pipeline/cli.py` build_parser()
- Configuration: Add path constants to `skill_pipeline/config.py` if needed
- Models: Add Pydantic schemas to `skill_pipeline/models.py` or `skill_pipeline/pipeline_models/`

**New Component/Module (Helper):**
- Implementation: Place in relevant subpackage (`source/`, `normalize/`, `raw/`)
- Tests: Add test function to relevant stage test file or create focused test file
- Pattern: Use type hints, document preconditions/postconditions, fail loudly on invalid inputs

**Utilities (Shared Helpers):**
- Shared quote/date helpers: `skill_pipeline/normalize/`
- Shared provenance logic: `skill_pipeline/provenance.py`
- Path/artifact loading: `skill_pipeline/paths.py`, `skill_pipeline/extract_artifacts.py`
- Seed/config data: `skill_pipeline/seeds.py`, `skill_pipeline/config.py`

**New Artifact Type:**
- Schema: Define Pydantic model in `skill_pipeline/models.py` or `skill_pipeline/pipeline_models/`
- Path: Add property to `SkillPathSet` in `skill_pipeline/models.py` and update `build_skill_paths()`
- Loader: Add function to appropriate module or extend `extract_artifacts.py`
- Writer: Use `atomic_write_json()` from `skill_pipeline/raw/fetch.py` for safe writes

## Special Directories

**`.claude/skills/`:**
- Purpose: Canonical skill tree for LLM-guided task decomposition
- Generated: Manually maintained or generated by agent tasks
- Committed: Yes; canonical source for skill definitions
- Notes: Synced to `.codex/skills/` and `.cursor/skills/` via `scripts/sync_skill_mirrors.py`

**`.codex/` and `.cursor/`:**
- Purpose: IDE-specific skill mirrors derived from `.claude/`
- Generated: Yes, via `python scripts/sync_skill_mirrors.py`
- Committed: Yes; for IDE compatibility
- Pattern: Run sync after editing `.claude/skills/`

**`diagnosis/`:**
- Purpose: Post-export benchmark diagnostics and reasoning traces
- Generated: Yes, by `/reconcile-alex` and other post-export tools
- Committed: Yes; only after export completes
- Notes: Forbidden until `/export-csv` finishes; no generation artifacts modified here

**`example/`:**
- Purpose: Reference example extraction outputs for benchmarking
- Generated: External tools
- Committed: Yes; post-export only
- Notes: Forbidden during generation; consulted only after export

**`quality_reports/`:**
- Purpose: QA metrics and coverage analysis
- Generated: Yes, post-processing
- Committed: Yes
- Notes: Diagnostic only; never affects generation artifacts

---

*Structure analysis: 2026-03-27*
