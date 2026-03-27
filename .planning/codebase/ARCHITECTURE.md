# Architecture

**Analysis Date:** 2026-03-27

## Pattern Overview

**Overall:** Deterministic multi-stage extraction and verification pipeline with hybrid workflow architecture.

**Key Characteristics:**
- Seed-only upstream stages (`raw-fetch`, `preprocess-source`) freeze immutable filing text and build source artifacts
- Deterministic gate stages (`check`, `verify`, `coverage`) validate extract artifacts before downstream processing
- Canonical schema upgrade with span-backed evidence references replaces legacy evidence models
- Fail-fast gates prevent corrupted state from flowing downstream; missing or contradictory inputs cause immediate rejection
- Modular stage separation via CLI entry points (`skill-pipeline` in `pyproject.toml`) with isolated output directories per stage

## Layers

**Raw Fetch Layer (Immutable Filing Freeze):**
- Purpose: Discover SEC filings from seed data and fetch filing text atomically
- Location: `skill_pipeline/raw/`
- Contains: `fetch.py` (filing fetch/freeze), `discover.py` (candidate ranking), `stage.py` (orchestration)
- Depends on: edgartools for SEC access, `pipeline_models/source.py` for schema, seed CSV
- Used by: `preprocess-source` stage, external tools (archive, reference checks)
- Output: `raw/<slug>/filings/*.txt` (immutable), `raw/<slug>/discovery.json`, `raw/<slug>/document_registry.json`

**Source Preprocessing Layer (Chronology & Evidence Extraction):**
- Purpose: Parse frozen filings into chronology blocks and evidence items for later-stage analysis
- Location: `skill_pipeline/preprocess/`, `skill_pipeline/source/`
- Contains: `preprocess/source.py` (orchestration), `source/locate.py` (chronology detection), `source/blocks.py` (block building), `source/evidence.py` (evidence scanning)
- Depends on: raw frozen documents, regex-based chronology candidate scoring, line-level parsing
- Used by: deterministic gates (check, verify, coverage), canonicalization,
  local-agent extraction
- Output: `data/deals/<slug>/source/chronology_selection.json`,
  `chronology_blocks.jsonl`, `evidence_items.jsonl`, `chronology.json`, and
  `source/filings/*`
- Contract note: current preprocess is seed-only and single-primary-document;
  stale `supplementary_snippets.jsonl` is explicitly removed rather than
  produced

**Extract Artifacts Layer (Local-Agent Structured Output):**
- Purpose: Store actor/event structures produced by local-agent extraction,
  first in legacy evidence-ref form and then in canonical span-backed form
- Location: Loaded by `skill_pipeline/extract_artifacts.py`
- Contains: `actors_raw.json` and `events_raw.json` in both modes; canonicalization upgrades the schema in place and adds `spans.json`
- Depends on: `/extract-deal` command (external)
- Used by: all deterministic gates, canonicalize, enrich-core
- Input: `data/skill/<slug>/extract/actors_raw.json`, `data/skill/<slug>/extract/events_raw.json`
- Sidecar: `data/skill/<slug>/extract/spans.json` (required once canonical, bridges evidence refs to source text)

**Deterministic Verification & Enrichment Layers:**
- Purpose: Sequential gates that validate extracted data, enforce referential integrity, audit source coverage, then enrich with derived attributes
- Location: `skill_pipeline/check.py`, `verify.py`, `coverage.py`, `enrich_core.py`
- Contains: Structural checks, quote matching, evidence auditing, round pairing, bid classification
- Depends on: extract artifacts, source evidence/chronology, frozen filings text
- Used by: downstream tools (export)
- Output: Check reports, verification logs, coverage findings, enrichment artifacts in `data/skill/<slug>/{check,verify,coverage,enrich}/`

**Canonicalization Layer (Schema Upgrade):**
- Purpose: Convert legacy evidence-ref models to span-backed canonical form; deduplicate semantically equivalent events; gate drops by NDA support; recover unnamed parties
- Location: `skill_pipeline/canonicalize.py`, `skill_pipeline/provenance.py`, `skill_pipeline/normalize/`
- Contains: Span resolution, date normalization, quote matching, NDA gating logic
- Depends on: raw extract artifacts, frozen filing text, chronology blocks, evidence items
- Used by: Runs before check/verify/coverage if canonical form is needed
- Output: Canonical span-backed payloads written back to `actors_raw.json` and `events_raw.json`, plus `spans.json`

**Deal Agent Summarizer (Preflight & Status Only):**
- Purpose: Verify shared inputs exist, summarize artifact counts and stage status without running extraction or repair
- Location: `skill_pipeline/deal_agent.py`
- Contains: Status checks for all stages, actor/event counts, error summaries
- Depends on: artifact paths, loaded extract artifacts
- Used by: diagnostics and pre-flight checks
- Output: JSON summary with stage statuses and counts

## Data Flow

**Seed-Only Upstream Path:**

1. `data/seeds.csv` + `--deal <slug>`
2. → `skill-pipeline raw-fetch` discovers filing candidates and fetches primary filing
3. → `raw/<slug>/filings/{doc_id}.txt` (immutable), `discovery.json`, `document_registry.json`
4. → `skill-pipeline preprocess-source` parses frozen text into chronology and evidence
5. → `data/deals/<slug>/source/chronology_selection.json`,
   `chronology_blocks.jsonl`, `evidence_items.jsonl`, `chronology.json`
6. → (**External:** `/extract-deal <slug>` produces extract artifacts)

**Deterministic Verification Path (After Extract):**

1. Extract artifacts at `data/skill/<slug>/extract/{actors_raw,events_raw}.json`
2. → `skill-pipeline check` (structural blocker gate) → `check_report.json`
3. → `skill-pipeline verify` (strict quote resolution, EXACT/NORMALIZED only) → `verification_log.json`
4. → `skill-pipeline coverage` (source cue audit) → `coverage_findings.json`, `coverage_summary.json`
5. → (**External:** `/verify-extraction` may repair if all errors repairable)
6. → `skill-pipeline enrich-core` (deterministic rounds, bids, cycles) → `deterministic_enrichment.json`
7. → (**External:** `/export-csv` writes filing-grounded CSV)
8. → (**Post-Export:** `/reconcile-alex` optional benchmark QA)

**Canonicalization Path (Optional Pre-Gate):**

1. Extract artifacts in legacy form
2. → `skill-pipeline canonicalize` (span resolution, schema upgrade, dedup, NDA-gate)
3. → Canonical span-backed payloads written back to `actors_raw.json` and `events_raw.json`, plus `spans.json`
4. → Then proceed to check/verify/coverage gates

**State Management:**

- **Immutable truth**: Frozen `.txt` files in `raw/<slug>/filings/`
- **Deterministic inputs**: Chronology selection, chronology blocks, evidence
  items, source filing mirrors, and document registry
- **Extract artifacts**: Raw or canonical; canonical form requires `spans.json` sidecar
- **Stage outputs**: Per-stage artifacts in `data/skill/<slug>/{check,verify,coverage,enrich,export,canonicalize}/`
- **Artifact invalidation**: Missing or failing gate prevents downstream stages (enrich-core requires check/verify/coverage)

## Key Abstractions

**FilingCandidate & FrozenDocument:**
- Purpose: Represent SEC filing discovery candidates and fetched/frozen document state
- Examples: `skill_pipeline/pipeline_models/source.py` lines 32-56
- Pattern: Pydantic models with immutable metadata (accession number, filing type, SHA256 hashes for integrity)

**ChronologyBlock & EvidenceItem:**
- Purpose: Represent source segments parsed into semantically meaningful units for extraction
- Examples: `skill_pipeline/pipeline_models/source.py` lines 94+, evidence items lines 120+
- Pattern: JSONL format with unique per-filing IDs (B001, E001, etc.), line offsets for span resolution

**SpanRecord & Provenance Resolution:**
- Purpose: Bridge evidence references in extract artifacts back to exact text positions in source filings
- Examples: `skill_pipeline/models.py` SpanRecord, `skill_pipeline/provenance.py` resolve_text_span()
- Pattern: Match anchor text in segment via find_anchor_in_segment() with expansion fallback; store match type (EXACT, NORMALIZED, FUZZY, UNRESOLVED)

**EvidenceRef (Legacy) vs evidence_span_ids (Canonical):**
- Purpose: Legacy mode stores block_id/evidence_id references directly; canonical mode stores span_id references pointing to spans.json
- Examples: Legacy `RawSkillActorRecord.evidence_refs` (list of EvidenceRef), canonical `SkillActorRecord.evidence_span_ids` (list of str)
- Pattern: Canonical requires separate `SpanRegistryArtifact` with full span details; fallback to legacy if spans.json missing

**SkillPathSet:**
- Purpose: Centralized path computation for all deal-specific artifact locations
- Examples: `skill_pipeline/paths.py` build_skill_paths()
- Pattern: Pydantic model with computed paths for every stage and artifact type; ensures consistency across CLI commands

**LoadedExtractArtifacts:**
- Purpose: Unified loader that detects legacy vs. canonical form and returns appropriate dataclass
- Examples: `skill_pipeline/extract_artifacts.py` load_extract_artifacts()
- Pattern: Checks for `evidence_span_ids` presence to auto-detect mode; requires spans.json if canonical

**VerificationFinding & CheckFinding:**
- Purpose: Structured reporting of gate failures with severity levels and affected artifact IDs
- Examples: `skill_pipeline/models.py` CheckFinding, VerificationFinding
- Pattern: Actor/event/span IDs linked to specific failures for repair guidance

**BidClassification & Round Pairing:**
- Purpose: Classify proposals as formal vs. informal; pair round announcements with deadlines
- Examples: `skill_pipeline/enrich_core.py` _pair_rounds(), BidClassification model
- Pattern: Deterministic rules on event types and temporal ordering; produces derivable `deterministic_enrichment.json`

## Entry Points

**CLI (`skill-pipeline` via `pyproject.toml`):**
- Location: `skill_pipeline/cli.py` main()
- Triggers: `skill-pipeline <command> --deal <slug>`
- Responsibilities: Parse arguments, delegate to stage functions, handle output serialization

**seed-only Stages:**
- `raw-fetch`: `skill_pipeline/raw/stage.py` fetch_raw_deal()
- `preprocess-source`: `skill_pipeline/preprocess/source.py` preprocess_source_deal()

**Deterministic Gate Stages:**
- `check`: `skill_pipeline/check.py` run_check()
- `verify`: `skill_pipeline/verify.py` run_verify()
- `coverage`: `skill_pipeline/coverage.py` run_coverage()
- `canonicalize`: `skill_pipeline/canonicalize.py` run_canonicalize()
- `enrich-core`: `skill_pipeline/enrich_core.py` run_enrich_core()

**Deal Summary (Preflight Only):**
- `deal-agent`: `skill_pipeline/deal_agent.py` run_deal_agent()

**External Entry Points (Not In This Package):**
- `/extract-deal <slug>`: Produces extract artifacts with `evidence_refs` (legacy) or `evidence_span_ids` (canonical)
- `/verify-extraction <slug>`: Optional repair loop consuming check/verify/coverage findings
- `/enrich-deal <slug>`: Optional later interpretive enrichment layer
- `/export-csv <slug>`: Writes filing-grounded CSV from extract + enrich artifacts
- `/reconcile-alex <slug>`: Optional post-export benchmark QA (never modifies generation artifacts)

## Error Handling

**Strategy:** Fail-fast with loud errors; no silent fallbacks or partial success.

**Patterns:**

- **Missing inputs**: Raise `FileNotFoundError` immediately (raw-fetch requires seed, preprocess requires frozen docs, gates require extract artifacts)
- **Invalid state**: Raise `ValueError` with detailed context (malformed JSON, missing required fields, contradictory dates)
- **Logic violations**: Raise specific exceptions (e.g., `ValueError` for unsupported filing types in canonicalize)
- **File I/O**: Use atomic writes (`atomic_write_json` in `skill_pipeline/raw/fetch.py`) to prevent partial overwrites
- **Schema validation**: Pydantic model_validate() enforces strict schema; extra="forbid" rejects unknown fields

**Gate Blocking:**

- `check` must pass before `verify` can run (verified by check report status)
- `verify` must pass before `coverage` can run (verified by verification log status)
- `coverage` must pass before `enrich-core` can run (verified by coverage summary status)
- Canonical form requires `spans.json` sidecar or `load_extract_artifacts()` raises `FileNotFoundError`

## Cross-Cutting Concerns

**Logging:** Python logging via stdlib `logging` module; use `logger = logging.getLogger(__name__)` pattern. Stages emit JSON reports to artifact files (not logs).

**Validation:** Pydantic models enforce schema at load time. Additional runtime validation in stage orchestrators (e.g., `_require_gate_artifacts` in enrich_core.py checks gate status before running).

**Authentication:** SEC access via edgartools requires `PIPELINE_SEC_IDENTITY` (or `SEC_IDENTITY`, `EDGAR_IDENTITY`) environment variable set in `skill_pipeline/raw/stage.py` _set_identity().

**Configuration:** No config file; stage behavior is controlled by deal slug,
artifact presence, and EDGAR identity env vars for live fetch. Do not treat
provider-selection variables as part of the `skill_pipeline` contract.

**Provenance:** Every extract artifact carries filing-aware metadata (document_id, accession_number, filing_type). Span resolution preserves line/character offsets for audit trails.

---

*Architecture analysis: 2026-03-27*
