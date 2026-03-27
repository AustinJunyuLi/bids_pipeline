# Requirements: Filing-Grounded Pipeline Redesign

**Defined:** 2026-03-27
**Core Value:** Produce the most correct filing-grounded structured deal record possible from raw text.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Prompt Architecture

- [ ] **PROMPT-01**: Extraction prompts place chronology text first and instructions/query last, exploiting primacy + recency bias
- [ ] **PROMPT-02**: Chunk boundaries align with chronology block boundaries — never split mid-block
- [ ] **PROMPT-03**: Chunked extraction includes 2-block overlap with explicit `<overlap_context>` XML tags distinguishing context from primary extraction targets
- [ ] **PROMPT-04**: Pre-computed evidence items are formatted as an active checklist the LLM must address, not a passive appendix
- [ ] **PROMPT-05**: Quote-before-extract protocol forces the LLM to cite verbatim passages before emitting structured events
- [ ] **PROMPT-06**: Complexity-based routing sends simple deals (<=150 blocks, <=8 actors) through single-pass extraction and complex deals through multi-chunk

### Extraction Infrastructure

- [ ] **INFRA-01**: Anthropic extraction calls use provider-native structured outputs via `output_config.format` with Pydantic schema enforcement
- [ ] **INFRA-02**: OpenAI extraction calls use provider-native structured outputs via the Responses API with schema enforcement
- [ ] **INFRA-03**: System prompt and actor roster are cached across chunk calls using Anthropic prompt caching with `cache_control` breakpoints
- [ ] **INFRA-04**: Each chronology block carries deterministic metadata: date mentions, entity mentions, evidence density score, temporal phase hint
- [ ] **INFRA-05**: A deterministic prompt composition engine assembles extraction prompts from annotated blocks, evidence checklist, actor roster, and few-shot examples
- [ ] **INFRA-06**: SDK dependencies upgraded: `anthropic>=0.86`, `openai>=2.30`, `edgartools>=5.23,<6.0`
- [ ] **INFRA-07**: Few-shot examples expanded to 4-5 covering NDA groups, ambiguous drops, cycle boundaries, range proposals, and formal-round signals

### Enhanced Deterministic Gates

- [ ] **GATE-01**: Temporal consistency check validates that event dates are chronologically consistent with their evidence positions in the filing
- [ ] **GATE-02**: Cross-event logic validation enforces domain invariants (no proposal after executed in same cycle, no NDA after drop without restart, round announcements precede deadlines)
- [ ] **GATE-03**: Per-actor lifecycle coverage verifies that every actor who signs an NDA eventually appears in a proposal, drop, or outcome event
- [ ] **GATE-04**: Attention decay diagnostics cluster verification failures by block position to detect mid-document attention loss patterns

### Database & Integration

- [ ] **DB-01**: DuckDB canonical database stores structured deal data (actors, events, spans, enrichment) as the single source driving both queries and CSV export
- [ ] **DB-02**: End-to-end pipeline CLI runs raw-fetch through export as a single command without manual skill handoffs between core stages
- [ ] **DB-03**: CSV export and any future query interface are generated from the DuckDB canonical representation, not from JSON artifacts

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Recovery & Repair

- **REC-01**: Targeted retrieval recovery uses BM25 keyword search over blocks to narrow context for missed-event recovery when coverage identifies gaps
- **REC-02**: Embedding-based semantic similarity assists deduplication during canonicalization for borderline cases

### Scale & Performance

- **SCALE-01**: Cross-deal queries enable finding actors who appear across multiple deals
- **SCALE-02**: Pipeline supports >50 deals with parallelized extraction

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| RAG as primary architecture | Extraction requires exhaustive recall; documents fit in context; RAG adds retrieval failure modes |
| Graph RAG / Agentic RAG backbone | Overkill for 9-deal batch corpus; assessed and rejected |
| Context compression / summarization | Filing text is legally precise; lossy compression risks anchor text corruption |
| Multi-agent voting / self-consistency | Research confirms marginal ROI (0.943 F1 at 2.3x cost); existing two-pass + gates is better |
| UI or product surface | Backend and data-pipeline focused |
| Benchmark-driven generation logic | Benchmark materials remain post-export diagnostics only |
| Speed-first shortcuts | Correctness is the project priority |

## Traceability

Filled by roadmap creation.

| Requirement | Phase |
|-------------|-------|
| (Populated after ROADMAP.md created) | |
