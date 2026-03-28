# Roadmap: Filing-Grounded Pipeline Redesign

**Created:** 2026-03-27
**Milestone:** v1 — Correctness-first end-to-end pipeline
**Validation strategy:** stec (primary baseline), medivation (complexity stress
test)

## Phases

### Phase 1: Foundation + Annotation

**Goal:** Enrich chronology block preprocessing with deterministic metadata and
harden the live deterministic runtime contract. No LLM behavior changes.

**Requirements:** INFRA-04, INFRA-06

**Scope:**
- Annotate each chronology block with deterministic metadata: parsed date
  mentions, seed-based entity mentions, evidence density score, temporal phase
  hint (hybrid: content-signal primary, position fallback)
- Annotation runs as final step inside `preprocess-source`, not a separate
  subcommand
- New metadata fields are required on `ChronologyBlock`; stale blocks without
  metadata fail on load
- Re-run `preprocess-source` for all 9 deals to produce annotated blocks
- Harden repo-truth and planning docs so they no longer describe a Python-side
  LLM wrapper or provider-specific runtime env vars as part of `skill_pipeline`
- If dependency hygiene is touched, limit it to live deterministic runtime
  risks such as `edgartools<6.0`, not new Python-side LLM SDK requirements

**Exit criteria:**
- `python -m pytest -q` passes
- Unit tests for each annotation function (dates, entities, density, phase)
- stec annotated blocks spot-checked for correctness
- All 9 deals have annotated `chronology_blocks.jsonl`
- Planning docs align with the deterministic Python runtime plus local-agent
  orchestration split

**Depends on:** nothing

---

### Phase 2: Prompt Architecture

**Goal:** Build the deterministic prompt composition engine that assembles
extraction prompt packets from annotated blocks.

**Requirements:** INFRA-01, INFRA-02, INFRA-03, INFRA-05, PROMPT-01,
PROMPT-02, PROMPT-03, PROMPT-04

**Scope:**
- Prompt composition engine: annotated blocks, evidence checklist, actor
  roster, and few-shot examples in, assembled prompt packets out
- Data-first ordering: chronology text at top, instructions/query at bottom
- Block-aligned chunk boundaries: never split mid-block, group by token budget
- 2-block overlap with `<overlap_context>` XML tags for chunked extraction
- Evidence items formatted as an active checklist the agent must address
- Stable prompt prefix separated from per-chunk body so the selected local-agent
  tooling can reuse repeated context when supported
- Keep provider- or agent-specific calling details out of `skill_pipeline`

**Exit criteria:**
- Composition engine is deterministic and testable without LLM calls
- stec extraction through new prompt packets passes deterministic gates (check,
  verify, coverage)
- Prompt packets clearly separate stable prefix content from chunk-specific
  content without adding a Python-side provider wrapper

**Depends on:** Phase 1 (block metadata feeds composition)

---

### Phase 3: Quote-Before-Extract

**Goal:** Force the LLM to cite verbatim filing passages before emitting
structured events.

**Requirements:** PROMPT-05

**Plans:** 5 plans

Plans:
- [x] 03-01-PLAN.md — Schema foundation: QuoteEntry model, extract loader, test fixture conversion
- [x] 03-02-PLAN.md — Canonicalize rewrite: quote-to-span resolution, enrich_core cleanup
- [x] 03-03-PLAN.md — Verify + Check rewrite: quote validation, quote_id integrity
- [x] 03-04-PLAN.md — Prompt instructions + extract-deal SKILL.md update
- [x] 03-05-PLAN.md — Gap closure: deal_agent and coverage migration to quote_first contract

**Scope:**
- New extraction response format: quoted passages first, then structured events
  referencing those quotes
- Canonicalize updated to consume quote-first output and map quoted passages to
  span IDs
- Verify updated to validate quote-first output against source

**Exit criteria:**
- stec extraction with quote-before-extract produces equal or better
  actor/event recall
- Verify stage passes with higher EXACT match rates on the new extraction flow
- medivation extraction tested as complexity stress case

**Depends on:** Phase 2 (composition engine assembles the quote-first prompt)

---

### Phase 4: Enhanced Gates

**Goal:** Add deterministic checks that catch error classes the current gates
miss.

**Requirements:** GATE-01, GATE-02, GATE-03, GATE-04

**Plans:** 2 plans

Plans:
- [ ] 04-01-PLAN.md — Gate models, paths, gates.py core logic (all 4 gates), unit tests
- [ ] 04-02-PLAN.md — CLI wiring, deal-agent summary, enrich-core gating, CLAUDE.md, integration tests

**Scope:**
- Temporal consistency: event dates vs evidence positions in filing
- Cross-event logic: domain invariants (no proposal after executed in same
  cycle, no NDA after drop without restart)
- Per-actor lifecycle: every NDA signer must appear in a downstream event
- Attention decay diagnostics: cluster verification failures by block position

**Exit criteria:**
- All 4 gates implemented as extensions to existing check/verify/coverage
  stages
- stec passes all new gates, or findings are confirmed real issues
- medivation tested; new gates catch at least one error class the old gates
  missed

**Depends on:** Phase 3 (validates quote-before-extract output quality)

---

### Phase 5: Integration + Calibration

**Goal:** Wire everything into an end-to-end pipeline with DuckDB as canonical
store and a documented local-agent orchestration entrypoint.

**Requirements:** DB-01, DB-02, DB-03, PROMPT-06, INFRA-07

**Scope:**
- DuckDB canonical database: actors, events, spans, enrichment as tables
- End-to-end orchestration entrypoint or run contract:
  `raw-fetch -> preprocess -> extract -> canonicalize -> check -> verify -> coverage -> enrich -> export`
- CSV export generated from DuckDB, not JSON artifacts
- Complexity routing: simple deals (`<=150` blocks, `<=8` actors) use
  single-pass extraction; complex deals use multi-chunk
- Few-shot examples expanded to 4-5 covering NDA groups, ambiguous drops, cycle
  boundaries

**Exit criteria:**
- One documented orchestration flow processes stec end-to-end
- All 9 deals processed through the full pipeline
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
