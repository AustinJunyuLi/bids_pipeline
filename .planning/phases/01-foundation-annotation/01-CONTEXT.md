# Phase 1: Foundation + Annotation - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Enrich chronology block preprocessing with deterministic metadata annotations and clean up project dependencies. No LLM behavior changes. No extraction skill changes. No new pipeline stages — annotation extends the existing `preprocess-source` command.

</domain>

<decisions>
## Implementation Decisions

### SDK + Dependencies
- **D-01:** No Python LLM wrapper module. All LLM calls live in `.claude/skills/` markdown files. The `skill_pipeline` package remains entirely deterministic.
- **D-02:** INFRA-01 and INFRA-02 (schema-constrained external extraction flows) move to Phase 2 — they are skill-level changes, not Python code changes.
- **D-03:** Phase 1 dependency hygiene is limited to the live deterministic runtime path, such as pinning `edgartools>=5.23,<6.0` if needed.
- **D-04:** Clean up misleading references to provider-mode abstractions and Python-side LLM wrappers in CLAUDE.md and docs if they imply Python code handles LLM calls.

### Block Metadata Design
- **D-05:** Date mentions: parsed dates using existing `dates.py` logic. Each block carries a list of `{raw_text, normalized, precision}` objects extracted from `clean_text`.
- **D-06:** Entity mentions: seed-based matching. Match company names from `seeds.csv` (target, acquirer) plus common filing patterns (`Party A/B/C`, `the Company`, `the Board`). Minimal regex, no NLP.
- **D-07:** Evidence density: integer count of evidence items whose line ranges overlap with the block's `start_line`/`end_line`.
- **D-08:** Temporal phase: hybrid approach. Primary signal from evidence cue types overlapping the block (process_initiation cues = `initiation`, proposal/nda/financial cues = `bidding`, outcome_fact cues = `closing`). Position-based fallback for blocks with no evidence cues.

### Annotation Integration
- **D-09:** Annotation runs as a final step inside `preprocess-source`, not as a separate CLI subcommand. One command produces blocks + evidence + annotation.
- **D-10:** New metadata fields are **required** on the `ChronologyBlock` Pydantic model. No defaults, no optionals. Old blocks without metadata fail on load — this forces re-running `preprocess-source` before any downstream stage works.
- **D-11:** Re-run `preprocess-source` for all 9 deals as part of Phase 1 to produce annotated blocks. Stale blocks are an error, not a graceful degradation.

### Testing
- **D-12:** Unit tests for each annotation function: date extraction per block, entity matching, evidence density counting, temporal phase assignment.
- **D-13:** Regression test on stec: preprocess-source produces annotated blocks, spot-check specific blocks have correct metadata.

### Claude's Discretion
- Exact regex patterns for entity matching (beyond seed names and Party A/B/C)
- Internal data structure for parsed date mentions (lighter-weight version of ResolvedDate)
- Evidence density counting logic (simple line-range overlap check)
- Position-based fallback thresholds for temporal phase (e.g., first 20% vs 25%)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Pipeline Models
- `skill_pipeline/pipeline_models/source.py` — `ChronologyBlock` and `EvidenceItem` model definitions (lines 94-121)
- `skill_pipeline/models.py` — `ResolvedDate`, `SpanRecord`, and canonical artifact schemas

### Preprocessing
- `skill_pipeline/preprocess/source.py` — Orchestrator for `preprocess_source_deal()`, where annotation step will be added
- `skill_pipeline/source/blocks.py` — Block building logic from chronology candidate
- `skill_pipeline/source/evidence.py` — Evidence item scanning with 5 cue families

### Date + Entity Patterns
- `skill_pipeline/normalize/dates.py` — Date parsing and precision inference (reuse for block date extraction)
- `skill_pipeline/source/evidence.py` — `DATE_FRAGMENT_RE` and other regex patterns available for reuse

### Dependencies
- `pyproject.toml` — Current dependency pins (anthropic>=0.49, no openai)
- `data/seeds.csv` — Deal seed data with target_name, acquirer columns for entity matching

### Existing Tests
- `tests/test_skill_preprocess_source.py` — Existing preprocessing tests to extend

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `skill_pipeline/normalize/dates.py`: Date parsing logic (exact, month, quarter, relative) — reuse for block-level date extraction
- `skill_pipeline/source/evidence.py`: Evidence cue families and regex patterns — reuse for temporal phase inference and entity pattern matching
- `EvidenceItem.date_text`, `actor_hint`, `value_hint`: Already-extracted metadata per evidence item — cross-reference for block annotation

### Established Patterns
- `PipelineModel` base class with `ConfigDict(extra="forbid")` — all new fields must be explicit
- JSONL serialization for blocks and evidence items — annotation metadata serializes the same way
- Fail-fast validation — Pydantic rejects unexpected fields, missing required fields crash

### Integration Points
- `preprocess_source_deal()` in `preprocess/source.py` — annotation step added after blocks and evidence are both built
- `ChronologyBlock` model — new required metadata fields added here
- `data/deals/<slug>/source/chronology_blocks.jsonl` — output file, now carries metadata

</code_context>

<specifics>
## Specific Ideas

- User explicitly stated: "in this pipeline we have no intention to use python llm wrapper" — this is a hard constraint, not a preference
- Annotation is about giving downstream prompt composition (Phase 2) richer input, not about changing extraction behavior

</specifics>

<deferred>
## Deferred Ideas

- Schema-constrained external extraction flows (INFRA-01, INFRA-02) — moved to Phase 2 (skill-level change)
- Cleanup of misleading provider-mode references — can happen in Phase 1 or 2, not blocking

</deferred>

---

*Phase: 01-foundation-annotation*
*Context gathered: 2026-03-27*
