# Requirements: Filing-Grounded Pipeline Redesign

**Defined:** 2026-03-27
**Core Value:** Produce the most correct filing-grounded structured deal record
possible from raw text.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Prompt Architecture

- [x] **PROMPT-01**: Extraction prompts place chronology text first and
  instructions/query last, exploiting primacy + recency bias
- [x] **PROMPT-02**: Chunk boundaries align with chronology block boundaries;
  never split mid-block
- [x] **PROMPT-03**: Chunked extraction includes 2-block overlap with explicit
  `<overlap_context>` XML tags distinguishing context from primary extraction
  targets
- [x] **PROMPT-04**: Pre-computed evidence items are formatted as an active
  checklist the LLM must address, not a passive appendix
- [x] **PROMPT-05**: Quote-before-extract protocol forces the LLM to cite
  verbatim passages before emitting structured events
- [ ] **PROMPT-06**: Complexity-based routing sends simple deals (`<=150`
  blocks, `<=8` actors) through single-pass extraction and complex deals
  through multi-chunk

### Extraction Infrastructure

- [x] **INFRA-01**: Local-agent extraction flows can enforce schema-constrained
  structured outputs without introducing a Python-side provider wrapper in
  `skill_pipeline`
- [x] **INFRA-02**: Repo-level extraction and orchestration contracts remain
  agent- and provider-agnostic; provider-specific calling details stay outside
  `skill_pipeline` and repo-truth docs
- [x] **INFRA-03**: Prompt composition exposes a reusable static prefix
  (system guidance, actor roster, examples) separate from chunk-specific
  content so local-agent tooling can reuse repeated context where supported
- [ ] **INFRA-04**: Each chronology block carries deterministic metadata: date
  mentions, entity mentions, evidence density score, temporal phase hint
- [x] **INFRA-05**: A deterministic prompt composition engine assembles
  extraction prompt packets from annotated blocks, evidence checklist, actor
  roster, and few-shot examples
- [x] **INFRA-06**: Deterministic runtime dependencies and planning docs are
  hardened around the live Python path only; no new Python-side LLM SDK
  requirement is introduced as part of v1
- [ ] **INFRA-07**: Few-shot examples expanded to 4-5 covering NDA groups,
  ambiguous drops, cycle boundaries, range proposals, and formal-round signals

### Enhanced Deterministic Gates

- [ ] **GATE-01**: Temporal consistency check validates that event dates are
  chronologically consistent with their evidence positions in the filing
- [ ] **GATE-02**: Cross-event logic validation enforces domain invariants (no
  proposal after executed in same cycle, no NDA after drop without restart,
  round announcements precede deadlines)
- [ ] **GATE-03**: Per-actor lifecycle coverage verifies that every actor who
  signs an NDA eventually appears in a proposal, drop, or outcome event
- [ ] **GATE-04**: Attention decay diagnostics cluster verification failures by
  block position to detect mid-document attention loss patterns

### Database & Integration

- [ ] **DB-01**: DuckDB canonical database stores structured deal data (actors,
  events, spans, enrichment) as the single source driving both queries and CSV
  export
- [ ] **DB-02**: End-to-end pipeline run is orchestrated through a local-agent
  workflow without manual handoffs between core stages
- [ ] **DB-03**: CSV export and any future query interface are generated from
  the DuckDB canonical representation, not from JSON artifacts

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Recovery & Repair

- **REC-01**: Targeted retrieval recovery uses BM25 keyword search over blocks
  to narrow context for missed-event recovery when coverage identifies gaps
- **REC-02**: Embedding-based semantic similarity assists deduplication during
  canonicalization for borderline cases

### Scale & Performance

- **SCALE-01**: Cross-deal queries enable finding actors who appear across
  multiple deals
- **SCALE-02**: Pipeline supports `>50` deals with parallelized extraction

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

| Requirement | Phase |
|-------------|-------|
| INFRA-04 | 1 — Foundation + Annotation |
| INFRA-06 | 1 — Foundation + Annotation |
| INFRA-01 | 2 — Prompt Architecture |
| INFRA-02 | 2 — Prompt Architecture |
| INFRA-03 | 2 — Prompt Architecture |
| INFRA-05 | 2 — Prompt Architecture |
| PROMPT-01 | 2 — Prompt Architecture |
| PROMPT-02 | 2 — Prompt Architecture |
| PROMPT-03 | 2 — Prompt Architecture |
| PROMPT-04 | 2 — Prompt Architecture |
| PROMPT-05 | 3 — Quote-Before-Extract |
| GATE-01 | 4 — Enhanced Gates |
| GATE-02 | 4 — Enhanced Gates |
| GATE-03 | 4 — Enhanced Gates |
| GATE-04 | 4 — Enhanced Gates |
| DB-01 | 5 — Integration + Calibration |
| DB-02 | 5 — Integration + Calibration |
| DB-03 | 5 — Integration + Calibration |
| PROMPT-06 | 5 — Integration + Calibration |
| INFRA-07 | 5 — Integration + Calibration |
