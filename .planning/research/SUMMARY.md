# Project Research Summary

**Project:** Filing-Grounded Deal Pipeline Redesign
**Domain:** Correctness-first LLM extraction pipeline for structured M&A deal data from SEC filings
**Researched:** 2026-03-27
**Confidence:** HIGH

## Executive Summary

This pipeline extracts structured M&A deal chronologies (actors, events, evidence) from SEC DEFM14A/PREM14A/SC 14D-9 filings using LLM structured output, then validates every claim against the immutable source text through a chain of deterministic gates. The existing architecture -- deterministic shell / LLM kernel, two-pass extraction, artifact-mediated stages, fail-fast gate chain -- is fundamentally sound and aligns with 2026 best practices for controlled LLM extraction. The redesign is not a rewrite; it is a deepening of the existing pattern by adding a prompt composition layer (data-first ordering, quote-before-extract protocol, block-aligned chunking with overlap) between preprocessing and extraction, then upgrading to provider-native structured outputs with prompt caching.

The recommended approach is to keep the sequential pipeline (raw -> preprocess -> extract -> canonicalize -> check -> verify -> coverage -> enrich -> export), add three new deterministic stages between preprocess and extract (annotate, chunk-plan, compose-prompt), and upgrade the extraction call to use provider-native structured outputs (Anthropic `output_config.format`, OpenAI Responses API `text_format`) with explicit prompt caching. The quote-before-extract protocol -- forcing the LLM to cite verbatim passages before producing structured records -- is the single highest-ROI change, directly addressing the primary failure mode (hallucinated anchor text) that drives verify gate failures. DuckDB replaces ad-hoc JSON/CSV export with a proper analytical query layer.

The key risks are: hallucinated anchor text surviving verification (mitigated by quote-before-extract), repair loop degenerative correction (mitigated by investing in first-pass quality and constraining repair scope), over-chunking simple deals (mitigated by complexity-based routing with a high threshold), and evidence items becoming an extraction crutch rather than a coverage supplement (mitigated by restricting evidence items to Pass 2 only). All 9 active deals likely fit in a single context window for event extraction, so chunking complexity can be deferred until proven necessary.

## Key Findings

### Recommended Stack

The existing stack (Python 3.11+, Pydantic 2.0+, edgartools, pytest) is retained. Three changes are needed.

**Core additions/updates:**
- **anthropic >= 0.86**: Required for `output_config.format` GA structured outputs and `client.messages.parse()` with native Pydantic support. Replaces the deprecated beta structured outputs header.
- **openai >= 2.30**: Required for Responses API structured outputs on GPT-5.x (`client.responses.parse()` with `text_format`). GPT-4o is retired; GPT-5.4 is current.
- **duckdb >= 1.5**: Embedded column-oriented analytics database for canonical deal representation and export generation. Single-file deployment, native Parquet/CSV I/O, SQL-first querying.
- **edgartools >= 5.23, < 6.0**: Pin upper bound to avoid breaking v6 changes. Known deprecation risk.

**What NOT to add:** Instructor (redundant -- native SDK Pydantic support), LangChain/LlamaIndex (heavy abstractions that fight deterministic design), fuzzywuzzy (GPL, use rapidfuzz only if fuzzy matching enhancement is pursued).

**Provider-native structured outputs become the default.** `BIDS_LLM_STRUCTURED_MODE` switches from `prompted_json` to `provider_native`. Both providers guarantee schema-compliant JSON via constrained decoding. Extended thinking is compatible with structured outputs on Anthropic (thinking is unconstrained, final output is schema-enforced).

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

**Defer (v2+):**
- D-2: Block-level metadata enrichment (useful for complexity routing, not blocking)
- D-3: Complexity-based routing (9-deal corpus does not justify routing infrastructure yet)
- D-8: Cross-event logical consistency checks (incremental, add when error patterns emerge)

### Architecture Approach

The architecture follows **deterministic shell / LLM kernel**: an immutable filing layer feeds deterministic preprocessing, which structures input for a non-deterministic LLM extraction kernel, whose outputs are validated by deterministic gates before enrichment and export. The redesign inserts three new stages between preprocessing and extraction: **annotate** (block metadata), **chunk-plan** (block-aligned boundaries), and **compose-prompt** (data-first ordering, evidence checklist, few-shot examples, quote-before-extract instructions). Data flows strictly forward through filesystem artifacts. No stage modifies upstream artifacts. The only re-entry is the optional LLM repair loop.

**Major components (new or modified):**
1. **annotate** -- Enrich chronology blocks with dates, entities, evidence density, temporal phase
2. **chunk-plan** -- Compute block-aligned chunk boundaries with 2-block overlap; route simple deals to single-pass
3. **compose-prompt** -- Assemble per-chunk prompt payloads with data-first ordering and cache breakpoints
4. **extract (modified)** -- Quote-before-extract protocol with provider-native structured outputs
5. **merge-chunks (new)** -- Cross-chunk deduplication by block_id overlap (only needed for multi-chunk deals)
6. **Enhanced gates (new)** -- Temporal consistency, cross-event logic, per-actor coverage (additive, parallel with existing gates)

### Critical Pitfalls

1. **Hallucinated anchor text (P1)** -- The primary failure mode. LLMs reconstruct quotes from semantic memory rather than copying verbatim. Mitigate with quote-before-extract protocol: force the LLM to cite passages inside `<quote>` tags before producing structured records. If >10% of anchors fail EXACT/NORMALIZED on first pass, the prompt architecture is the problem.

2. **Repair loop degenerative correction (P2)** -- Fixing one error introduces new errors. Self-correction research shows LLMs exhibit "self-bias" and repaired outputs come from a contaminated distribution. Mitigate by investing in first-pass quality, constraining repair scope to only flagged items, tracking repair deltas, and capping at 2 rounds.

3. **Over-chunking simple deals (P3)** -- Chunking creates overlap regions, deduplication complexity, and actor confusion. Most of the 9 deals fit in a single context window. Mitigate with complexity-based routing: only chunk when chronology exceeds ~150k tokens. Default to single-pass.

4. **Evidence items becoming extraction crutch (P4)** -- If evidence items are presented during primary extraction, the LLM treats them as a closed-world specification and ignores events not on the list. Mitigate by restricting evidence items to Pass 2 gap re-read only. Pass 1 operates on chronology blocks alone.

5. **Thinking token explosion (P5)** -- Extended thinking on complex schemas (20 event types, 11 formality signals) can generate 50k-100k+ thinking tokens. Mitigate with adaptive thinking (`effort="high"`, not manual `budget_tokens`), set `max_tokens >= 64000`, and monitor thinking-to-output token ratio.

## Implications for Roadmap

### Phase 1: Prompt Architecture and Schema

**Rationale:** All four research files converge on this: prompt quality is the highest-leverage change. Quote-before-extract, data-first ordering, and evidence separation are prerequisites for every downstream improvement. Zero LLM cost for most of this work (composing and testing prompt templates).

**Delivers:** New prompt composition layer (compose-prompt), block annotation stage (annotate), chunk planning (chunk-plan), updated Pydantic schemas for raw vs canonical artifacts, prompt structure regression tests.

**Addresses features:** TS-1 (prompt ordering), TS-2 (quote-before-extract), TS-3 (block-aligned chunks), TS-4 (inter-chunk overlap), D-5 (prompt caching structure)

**Avoids pitfalls:** P1 (hallucinated anchors), P3 (over-chunking -- routing logic), P4 (evidence crutch -- Pass 1/2 separation), P5 (thinking explosion -- effort control), P6 (few-shot overfitting -- diverse examples), P7 (prompt ordering regression -- template enforcement), P12 (Pydantic extra="forbid" -- use "ignore" on raw artifacts), P13 (schema complexity -- validate against provider limits)

### Phase 2: Extraction Upgrade and Chunk Merge

**Rationale:** Depends on Phase 1 prompt templates being ready. This is where LLM calls change. Provider-native structured outputs, quote-before-extract response parsing, and cross-chunk reconciliation.

**Delivers:** Modified extract stage with new prompts, merge-chunks stage (if chunking is needed), provider-native structured output integration for both Anthropic and OpenAI, prompt caching wired into extraction calls.

**Addresses features:** D-5 (prompt caching operational), TS-10 (adaptive thinking configured)

**Avoids pitfalls:** P1 (hallucinated anchors -- quote protocol live), P9 (actor confusion -- actors-first with full roster per chunk), P10 (cache invalidation -- static/dynamic separation verified), P8 (dedup errors -- evidence-based dedup)

### Phase 3: Verification and Coverage Hardening

**Rationale:** Once extraction quality improves from Phase 1-2, the repair loop workload decreases and the gates can be enhanced. Depends on having extraction output from the new prompts.

**Delivers:** Constrained repair loop (scope-limited, delta-tracked), enhanced deterministic gates (temporal consistency, per-actor coverage, cross-event logic), expanded coverage regex patterns.

**Addresses features:** D-6 (temporal consistency gate), D-7 (per-actor coverage), D-8 (cross-event logic)

**Avoids pitfalls:** P2 (repair degenerative correction -- constrained scope), P8 (dedup errors -- if chunking used), P11 (coverage false negatives -- expanded patterns + block coverage metric)

### Phase 4: Database Layer and Export

**Rationale:** Independent of LLM extraction improvements. Can proceed in parallel with Phase 2-3 if needed, but logically comes after extraction is stable because DuckDB ingests canonical artifacts.

**Delivers:** DuckDB schema for canonical deal data, SQL-based export generation replacing ad-hoc CSV construction, analytical query layer for cross-deal analysis.

**Addresses features:** Canonical deal representation, export generation

**Avoids pitfalls:** None specific -- standard database work.

### Phase 5: Pipeline Orchestration and Automation

**Rationale:** Wire everything together end-to-end. Depends on all individual stages being functional.

**Delivers:** End-to-end CLI orchestration, complexity routing (single-pass vs multi-chunk), `--n-runs` interface (plumbing only, aggregation deferred), benchmark boundary enforcement tooling, cache hit monitoring, thinking token monitoring.

**Addresses features:** D-3 (complexity routing), pipeline automation

**Avoids pitfalls:** P14 (N-run premature complexity -- interface only, no aggregation logic), P15 (benchmark contamination -- automated enforcement)

### Phase Ordering Rationale

- Prompt architecture (Phase 1) is zero-LLM-cost and independently testable. Every other improvement depends on it.
- Extraction upgrade (Phase 2) depends on Phase 1 templates. This is where LLM API changes land.
- Verification hardening (Phase 3) depends on having extraction output from the improved prompts. Enhanced gates validate improved output.
- Database (Phase 4) is orthogonal to extraction but needs stable canonical artifacts to ingest. Can start in parallel with Phase 3.
- Orchestration (Phase 5) depends on all individual stages being functional.

### Research Flags

**Phases likely needing deeper research during planning:**
- **Phase 2 (Extraction Upgrade):** OpenAI Responses API exact parameter names need verification (docs returned 403 during research). Anthropic structured output + prompt caching interaction needs testing. Quote-before-extract response parsing format needs experimentation.
- **Phase 3 (Verification Hardening):** Repair loop scope constraints need calibration against real extraction output. Enhanced gate thresholds need tuning.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Prompt Architecture):** Well-documented Anthropic best practices. Template construction is straightforward Python.
- **Phase 4 (Database Layer):** Standard DuckDB usage. Schema design is implementation detail.
- **Phase 5 (Orchestration):** Standard CLI wiring. No novel patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Anthropic APIs verified against official docs. OpenAI is MEDIUM (docs returned 403). DuckDB is well-established. |
| Features | MEDIUM-HIGH | Table stakes grounded in Anthropic official documentation and academic research. Differentiators are logical extensions with less direct validation. |
| Architecture | HIGH | Existing architecture is validated. New stages follow established patterns. Build order is dependency-driven. |
| Pitfalls | HIGH | Critical pitfalls confirmed by project diagnosis history, Anthropic documentation, and self-correction research. |

**Overall confidence:** HIGH

### Gaps to Address

- **OpenAI Responses API parameter names:** The `text_format` parameter name is from search results, not verified official docs. Verify against SDK changelog before Phase 2 implementation.
- **Prompt caching + structured output interaction:** Anthropic injects an internal system prompt for structured outputs. Whether this affects cache breakpoint behavior needs testing.
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
*Ready for roadmap: yes*
