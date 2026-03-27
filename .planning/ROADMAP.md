# Roadmap: Filing-Grounded Pipeline Redesign

**Created:** 2026-03-27
**Milestone:** v1 — Correctness-first end-to-end pipeline
**Validation strategy:** stec (primary baseline), medivation (complexity stress test)

## Phases

### Phase 1: Foundation + Annotation

**Goal:** Enrich chronology block preprocessing with deterministic metadata and clean up project dependencies. No LLM behavior changes.

**Requirements:** INFRA-04, INFRA-06

**Scope:**
- Bump `anthropic>=0.86`, add `openai>=2.30`, pin `edgartools>=5.23,<6.0` in `pyproject.toml`
- Annotate each chronology block with deterministic metadata: parsed date mentions, seed-based entity mentions, evidence density score, temporal phase hint (hybrid: content-signal primary, position fallback)
- Annotation runs as final step inside `preprocess-source`, not a separate subcommand
- New metadata fields are required on `ChronologyBlock` — stale blocks without metadata fail on load
- Re-run `preprocess-source` for all 9 deals to produce annotated blocks

**Exit criteria:**
- `python -m pytest -q` passes
- Unit tests for each annotation function (dates, entities, density, phase)
- stec annotated blocks spot-checked for correctness
- All 9 deals have annotated `chronology_blocks.jsonl`

**Depends on:** nothing

---

### Phase 2: Prompt Architecture

**Goal:** Build the deterministic prompt composition engine that assembles extraction prompts from annotated blocks.

**Requirements:** INFRA-01, INFRA-02, INFRA-03, INFRA-05, PROMPT-01, PROMPT-02, PROMPT-03, PROMPT-04

**Scope:**
- Prompt composition engine: takes annotated blocks, evidence checklist, actor roster, few-shot examples → assembled prompt
- Data-first ordering: chronology text at top, instructions/query at bottom
- Block-aligned chunk boundaries: never split mid-block, group by token budget
- 2-block overlap with `<overlap_context>` XML tags for chunked extraction
- Evidence items formatted as active checklist the LLM must address
- Anthropic prompt caching with `cache_control` breakpoints on system prompt + actor roster

**Exit criteria:**
- Composition engine is deterministic and testable without LLM calls
- stec extraction through new prompts produces equal or better quality vs baseline
- Prompt caching reduces input token cost on chunked extraction (verify via API response headers)

**Depends on:** Phase 1 (block metadata feeds composition)

---

### Phase 3: Quote-Before-Extract

**Goal:** Force the LLM to cite verbatim filing passages before emitting structured events.

**Requirements:** PROMPT-05

**Scope:**
- New extraction response format: LLM outputs quoted passages first, then structured events referencing those quotes
- Canonicalize stage updated to consume quote-first response format and map quoted passages to span IDs
- Verify stage updated to validate quotes against source (should be trivially passing since quotes are verbatim)

**Exit criteria:**
- stec extraction with quote-before-extract produces equal or better actor/event recall
- Verify stage passes with higher EXACT match rate (fewer NORMALIZED/FUZZY)
- medivation extraction tested as complexity stress case

**Depends on:** Phase 2 (composition engine assembles the quote-first prompt)

---

### Phase 4: Enhanced Gates

**Goal:** Add deterministic checks that catch error classes the current gates miss.

**Requirements:** GATE-01, GATE-02, GATE-03, GATE-04

**Scope:**
- Temporal consistency: event dates vs evidence positions in filing
- Cross-event logic: domain invariants (no proposal after executed in same cycle, no NDA after drop without restart)
- Per-actor lifecycle: every NDA signer must appear in a downstream event
- Attention decay diagnostics: cluster verification failures by block position

**Exit criteria:**
- All 4 gates implemented as extensions to existing check/verify/coverage stages
- stec passes all new gates (or findings are confirmed real issues)
- medivation tested — new gates catch at least one error class the old gates missed

**Depends on:** Phase 3 (validates quote-before-extract output quality)

---

### Phase 5: Integration + Calibration

**Goal:** Wire everything into an end-to-end pipeline with DuckDB as canonical store.

**Requirements:** DB-01, DB-02, DB-03, PROMPT-06, INFRA-07

**Scope:**
- DuckDB canonical database: actors, events, spans, enrichment as tables
- End-to-end CLI command: raw-fetch → preprocess → extract → canonicalize → check → verify → coverage → enrich → export
- CSV export generated from DuckDB, not JSON artifacts
- Complexity routing: simple deals (<=150 blocks, <=8 actors) → single-pass; complex → multi-chunk
- Few-shot examples expanded to 4-5 covering NDA groups, ambiguous drops, cycle boundaries

**Exit criteria:**
- Single CLI command processes stec end-to-end
- All 9 deals processed through full pipeline
- CSV export from DuckDB matches or improves on JSON-based export

**Depends on:** Phase 4 (all gates in place before full-corpus run)

## Traceability

| Requirement | Phase |
|-------------|-------|
| INFRA-04 | 1 |
| INFRA-06 | 1 |
| INFRA-01 | 2 |
| INFRA-02 | 2 |
| INFRA-03 | 2 |
| INFRA-05 | 2 |
| PROMPT-01 | 2 |
| PROMPT-02 | 2 |
| PROMPT-03 | 2 |
| PROMPT-04 | 2 |
| PROMPT-05 | 3 |
| GATE-01 | 4 |
| GATE-02 | 4 |
| GATE-03 | 4 |
| GATE-04 | 4 |
| DB-01 | 5 |
| DB-02 | 5 |
| DB-03 | 5 |
| PROMPT-06 | 5 |
| INFRA-07 | 5 |
