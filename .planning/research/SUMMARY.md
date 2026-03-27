# Project Research Summary

**Project:** Filing-Grounded Deal Pipeline Redesign
**Domain:** Correctness-first local-agent extraction research for structured M&A deal data from SEC filings
**Researched:** 2026-03-27
**Confidence:** HIGH

## Executive Summary

This pipeline extracts structured M&A deal chronologies (actors, events,
evidence) from SEC DEFM14A/PREM14A/SC 14D-9 filings using local-agent-driven
structured extraction, then validates every claim against the immutable source
text through a chain of deterministic gates. The existing architecture --
deterministic shell / LLM kernel, two-pass extraction, artifact-mediated
stages, fail-fast gate chain -- is fundamentally sound and aligns with 2026
best practices for controlled extraction. The redesign is not a rewrite; it is
a deepening of the existing pattern.

This research packet records optional external local-agent implementation ideas.
It is not the live `skill_pipeline` contract, and it does not authorize adding
Python-side LLM wrappers to the repo.

The adopted roadmap keeps the sequential pipeline (`raw -> preprocess -> extract -> canonicalize -> check -> verify -> coverage -> enrich -> export`) and slices the work into five phases. Phase 1 is deliberately narrow: block metadata is added inside `preprocess-source`, written directly onto `chronology_blocks.jsonl`, and no LLM behavior changes happen yet. Later phases add deterministic prompt-composition helpers, quote-before-extract, enhanced deterministic gates, and finally database/orchestration work. Canonical extract filenames remain `actors_raw.json`, `events_raw.json`, and `spans.json`; canonicalization upgrades the schema in place rather than renaming the artifacts.

The key risks are: hallucinated anchor text surviving verification (mitigated by quote-before-extract), repair loop degenerative correction (mitigated by investing in first-pass quality and constraining repair scope), over-chunking simple deals (mitigated by deferring complexity routing until later in v1), and evidence items becoming an extraction crutch rather than a coverage supplement (mitigated by restricting evidence items to the later evidence-aware prompt flow). All 9 active deals likely fit in a single context window for event extraction, so chunking complexity should remain conditional rather than assumed.

## Key Findings

### Recommended Stack

The existing stack (Python 3.11+, Pydantic 2.0+, edgartools, pytest) is
retained. The items below are researched options for external local-agent
execution and later database work; they are not adopted `skill_pipeline`
runtime dependencies today.

**External agent-side options and later-phase additions:**
- **anthropic >= 0.86**: Researched SDK option for external runners that want
  native structured outputs and prompt caching
- **openai >= 2.30**: Researched SDK option for external runners that want the
  Responses API path on GPT-5.x
- **duckdb >= 1.5**: Candidate later-phase database layer for canonical deal
  representation and export generation
- **edgartools >= 5.23, < 6.0**: Live deterministic runtime risk to monitor or
  pin regardless of agent choice

**What NOT to add:** Instructor (redundant -- native SDK Pydantic support), LangChain/LlamaIndex (heavy abstractions that fight deterministic design), fuzzywuzzy (GPL, use rapidfuzz only if fuzzy matching enhancement is pursued).

**Schema-constrained structured outputs are the intended later-phase
direction.** Do not treat any provider-specific implementation path as active
until Phase 2 planning selects an external runner approach. Extended reasoning
remains compatible with structured outputs in at least some researched
providers, but that is external-runner detail rather than repo contract.

### Expected Features

**Must have (table stakes -- missing = extraction quality suffers):**
- TS-1: Data-first prompt ordering (up to 30% quality improvement, zero cost)
- TS-2: Quote-before-extract protocol (eliminates hallucinated anchor text at source)
- TS-3: Block-aligned semantic chunk boundaries (never split mid-block)
- TS-4: Inter-chunk overlap with context tags (2-block overlap with `<prior_context>` markers)
- TS-5 through TS-10: Already implemented and validated (Pydantic schemas, deterministic gates, two-pass extraction, span-backed provenance, fail-fast, extended thinking)

**Should have (differentiators -- measurably improve correctness):**
- D-1: Evidence items as active attention-steering checklist (Pass 2 only, not Pass 1)
- D-4: Expanded few-shot examples (3-5 diverse scenarios, cached in prompt prefix)
- D-5: Prompt caching for system prompt + actor roster (90% input token savings on Anthropic)
- D-6: Temporal consistency gate (cross-event date ordering validation)
- D-7: Per-actor coverage audit (lifecycle completeness per named bidder)

**Later in the v1 roadmap:**
- D-2: Block-level metadata enrichment (already adopted into active Phase 1 scope)
- D-3: Complexity-based routing (deferred to Phase 5, not needed before the prompt overhaul proves it is useful)
- D-8: Cross-event logical consistency checks (active Phase 4 work, not a v2-only idea)

### Architecture Approach

The architecture follows **deterministic shell / LLM kernel**: an immutable filing layer feeds deterministic preprocessing, which structures input for a non-deterministic LLM extraction kernel, whose outputs are validated by deterministic gates before enrichment and export. The active roadmap keeps Phase 1 annotation inside `preprocess-source`, then adds Phase 2 prompt-composition responsibilities around extraction. Whether those later responsibilities become serialized helper artifacts (`chunk_plan.json`, prompt payload files) or remain internal deterministic helpers is still a Phase 2 planning choice, not an approved runtime contract today. Data flows strictly forward through filesystem artifacts. The only re-entry is the optional LLM repair loop.

**Major components (new or modified):**
1. **preprocess-source (modified in Phase 1)** -- Enrich chronology blocks with dates, entities, evidence density, temporal phase
2. **prompt composition helpers (planned for Phase 2)** -- Compute block-aligned chunk boundaries, overlaps, evidence checklists, and data-first prompt layout
3. **extract (modified later)** -- Quote-before-extract protocol with schema-constrained external extraction
4. **enhanced gates (planned for Phase 4)** -- Temporal consistency, cross-event logic, per-actor coverage, attention decay diagnostics
5. **database/orchestration (planned for Phase 5)** -- Canonical store plus a documented orchestration flow

### Critical Pitfalls

1. **Hallucinated anchor text (P1)** -- The primary failure mode. LLMs reconstruct quotes from semantic memory rather than copying verbatim. Mitigate with quote-before-extract protocol: force the LLM to cite passages inside `<quote>` tags before producing structured records. If >10% of anchors fail EXACT/NORMALIZED on first pass, the prompt architecture is the problem.

2. **Repair loop degenerative correction (P2)** -- Fixing one error introduces new errors. Self-correction research shows LLMs exhibit "self-bias" and repaired outputs come from a contaminated distribution. Mitigate by investing in first-pass quality, constraining repair scope to only flagged items, tracking repair deltas, and capping at 2 rounds.

3. **Over-chunking simple deals (P3)** -- Chunking creates overlap regions, deduplication complexity, and actor confusion. Most of the 9 deals fit in a single context window. Mitigate with complexity-based routing: only chunk when chronology exceeds ~150k tokens. Default to single-pass.

4. **Evidence items becoming extraction crutch (P4)** -- If evidence items are presented during primary extraction, the LLM treats them as a closed-world specification and ignores events not on the list. Mitigate by restricting evidence items to Pass 2 gap re-read only. Pass 1 operates on chronology blocks alone.

5. **Thinking token explosion (P5)** -- Extended thinking on complex schemas (20 event types, 11 formality signals) can generate 50k-100k+ thinking tokens. Mitigate with adaptive thinking (`effort="high"`, not manual `budget_tokens`), set `max_tokens >= 64000`, and monitor thinking-to-output token ratio.

## Implications for Roadmap

### Phase 1: Foundation + Annotation

**Rationale:** This is the lowest-risk prerequisite work. It improves deterministic source artifacts without changing extraction behavior, which keeps the baseline stable while creating the metadata later prompt work needs.

**Delivers:** Required block metadata on `ChronologyBlock`, annotation
integrated into `preprocess-source`, reprocessed source artifacts for all 9
deals, and regression tests for the annotation logic.

**Addresses features:** D-2 (block metadata enrichment)

**Avoids pitfalls:** P3 (premature chunking complexity), P10 (changing LLM behavior too early), stale source artifacts flowing into later phases

### Phase 2: Prompt Architecture

**Rationale:** Once annotated blocks exist, prompt composition can be built deterministically and tested without changing the underlying extraction contract all at once.

**Delivers:** Deterministic prompt-composition helpers, data-first ordering, evidence checklist formatting, block-aligned chunk planning, overlap tags, and prompt-caching structure.

**Addresses features:** TS-1, TS-3, TS-4, D-1, D-4, D-5

**Avoids pitfalls:** P1 (hallucinated anchors), P3 (over-chunking), P4 (evidence items becoming a crutch), P7 (prompt-ordering regression)

### Phase 3: Quote-Before-Extract

**Rationale:** Quote-before-extract is the highest-leverage extraction change, but it should land only after prompt composition is stable.

**Delivers:** Extraction prompt/response changes, quote-first parsing expectations, and canonicalization/verification updates needed to consume the new output shape safely.

**Addresses features:** TS-2

**Avoids pitfalls:** P1 (hallucinated anchors), P2 (repair-loop overuse), P9 (actor confusion), P10 (cache invalidation mistakes)

### Phase 4: Enhanced Gates

**Rationale:** Once the improved extraction path exists, deterministic checks can be extended to catch the remaining failure modes the current gate chain misses.

**Delivers:** Temporal consistency, cross-event logic, per-actor coverage, and attention-decay diagnostics.

**Addresses features:** D-6, D-7, D-8

**Avoids pitfalls:** P2 (repair degenerative correction), P11 (coverage blind spots)

### Phase 5: Integration + Calibration

**Rationale:** Final orchestration and database work should happen after the stage-level contracts have settled.

**Delivers:** DuckDB canonical store, end-to-end orchestration, complexity routing, calibration on the 9-deal corpus, and export generation from a single canonical representation.

**Addresses features:** D-3 plus the DB/integration requirements

**Avoids pitfalls:** P14 (premature multi-run complexity), P15 (benchmark contamination)

### Phase Ordering Rationale

- Foundation + annotation (Phase 1) is deterministic prerequisite work and keeps the current extraction behavior untouched.
- Prompt architecture (Phase 2) depends on Phase 1 metadata. This is where prompt composition lands without yet forcing the quote-first extraction contract.
- Quote-before-extract (Phase 3) depends on Phase 2 prompt composition. This is where LLM API and parsing changes land.
- Enhanced gates (Phase 4) depend on the improved extraction path so they validate the right output contract.
- Integration + calibration (Phase 5) depends on all individual stage contracts being stable enough to wire together end-to-end.

### Research Flags

**Phases likely needing deeper research during planning:**
- **Phase 2 (Prompt Architecture):** Exact helper boundaries (`chunk_plan.json` and serialized prompt payloads versus in-memory deterministic helpers) still need planning decisions.
- **Phase 3 (Quote-Before-Extract):** External-runner structured-output field
  names, prompt-caching behavior, and quote-first response parsing still need
  verification in the selected agent/tooling path.
- **Phase 4 (Enhanced Gates):** Repair-loop scope constraints and enhanced-gate thresholds need calibration against real extraction output.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Foundation + Annotation):** Deterministic metadata enrichment over existing source artifacts.
- **Phase 5 (Integration + Calibration):** Standard CLI and DuckDB wiring once the upstream contracts are settled.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Agent-side Anthropic docs were verified. OpenAI remains MEDIUM confidence. DuckDB is well-established. |
| Features | MEDIUM-HIGH | Table stakes grounded in Anthropic official documentation and academic research. Differentiators are logical extensions with less direct validation. |
| Architecture | HIGH | Existing architecture is validated. New stages follow established patterns. Build order is dependency-driven. |
| Pitfalls | HIGH | Critical pitfalls confirmed by project diagnosis history, Anthropic documentation, and self-correction research. |

**Overall confidence:** HIGH

### Gaps to Address

- **Selected external runner contract:** The repo has not chosen a final
  provider/SDK execution path for local-agent extraction. Phase 2 planning must
  make that decision explicitly if it becomes necessary.
- **Prompt caching + structured output interaction:** Provider-specific caching
  behavior still needs testing in the selected external runner, if such caching
  is used.
- **edgartools v6 timeline:** Breaking changes confirmed but release date unknown. Monitor and pin `<6.0`.
- **Chunk threshold calibration:** The 150k-token threshold for chunking is a reasonable default but needs validation against actual deal chronology sizes. Measure token counts for all 9 deals before finalizing.
- **Few-shot example curation:** Requires completed gold-standard extractions from validated deals. Cannot be done until at least 1-2 deals pass the full pipeline with the new prompts.
- **DuckDB schema design:** No research on specific table schemas for deal data. This is implementation detail for Phase 4.

## Sources

### Primary (HIGH confidence)
- [Anthropic Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) -- GA `output_config.format`, Pydantic `.parse()`, schema limitations
- [Anthropic Prompt Caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) -- cache breakpoints, TTL, pricing, minimum thresholds
- [Anthropic Extended Thinking](https://platform.claude.com/docs/en/build-with-claude/extended-thinking) -- compatibility with structured outputs, adaptive thinking
- [Anthropic Prompting Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) -- data-first ordering, quote grounding, few-shot guidance
- [Anthropic Reduce Hallucinations](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations) -- quote-before-extract, citation verification
- [Anthropic Long Context Tips](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/long-context-tips) -- XML tags, data-first strategy
- [OpenAI Prompt Caching](https://platform.openai.com/docs/guides/prompt-caching) -- automatic caching, 1024-token minimum

### Secondary (MEDIUM-HIGH confidence)
- [Multi-Agent Financial Document Processing Benchmark (arxiv 2603.22651)](https://arxiv.org/abs/2603.22651) -- sequential vs multi-agent for SEC filings
- [LLM Self-Correction Benchmark (arxiv 2510.16062)](https://arxiv.org/html/2510.16062v1) -- self-consistency marginal ROI for structured extraction
- [SCoRe: Self-Correction via RL (ICLR 2025)](https://proceedings.iclr.cc/paper_files/paper/2025/file/871ac99fdc5282d0301934d23945ebaa-Paper-Conference.pdf) -- reflexive improvement yields 9-15% gains
- [Lost in the Middle (TACL)](https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00638/119630/) -- 30%+ accuracy drops at middle positions
- [The Few-shot Dilemma (arxiv 2509.13196)](https://arxiv.org/abs/2509.13196) -- performance degradation with excessive examples
- [LLMQuoter: Quote Extraction for RAG (arxiv 2501.05554)](https://arxiv.org/html/2501.05554v1) -- quote-first-then-answer, 20-point accuracy gains
- Project diagnosis rounds 1-3 and CONCERNS.md -- repair loop contamination, reasoning effort tradeoffs

### Tertiary (MEDIUM confidence)
- [OpenAI Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs) -- docs returned 403; info from search results
- [DuckDB vs SQLite comparison](https://www.analyticsvidhya.com/blog/2026/01/duckdb-vs-sqlite/) -- feature comparison
- [NVIDIA Chunking Guide](https://developer.nvidia.com/blog/finding-the-best-chunking-strategy-for-accurate-ai-responses/) -- semantic chunking best practices
- [Deterministic vs LLM Evaluators 2026](https://dev.to/anshd_12/deterministic-vs-llm-evaluators-a-2026-technical-trade-off-study-11h) -- multi-layered evaluation
- PyPI package registries for version verification (anthropic 0.86.0, openai 2.30.0, duckdb 1.5.1, edgartools 5.26.1)

---

*Research completed: 2026-03-27*
*Roadmap status: adopted into `.planning/ROADMAP.md`*
