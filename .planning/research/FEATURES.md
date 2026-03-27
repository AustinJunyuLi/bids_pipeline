# Feature Landscape

**Domain:** Correctness-first LLM extraction pipeline for structured M&A deal data from SEC filings
**Researched:** 2026-03-27
**Overall Confidence:** MEDIUM-HIGH

## Table Stakes

Features users (pipeline operators, downstream consumers) expect. Missing = extraction quality demonstrably suffers or pipeline is operationally fragile.

### TS-1: Prompt Ordering (Data First, Instructions Last)

| Attribute | Detail |
|-----------|--------|
| Why Expected | Anthropic's official docs state that placing longform data at the top and queries/instructions at the end improves response quality by up to 30% on complex multi-document inputs. This is the single highest-ROI zero-cost change available. |
| Complexity | Low |
| Status | Not yet implemented. Current extraction skill does not enforce ordering. |
| Confidence | HIGH -- Anthropic official documentation |

**What it means:** Restructure extraction prompts so chronology blocks and evidence items appear first (as `<document>` tagged content), followed by few-shot examples, then the extraction schema and instructions at the end. This exploits LLM attention patterns: models attend most strongly to the beginning (data) and end (query) of context.

**Source:** [Anthropic Prompting Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) -- "Put longform data at the top... Queries at the end can improve response quality by up to 30%."

---

### TS-2: Quote-Before-Extract Protocol (Ground Responses in Quotes)

| Attribute | Detail |
|-----------|--------|
| Why Expected | The primary failure mode the verify gate catches is hallucinated or imprecise anchor text. Forcing the LLM to identify and quote relevant passages before producing structured extraction eliminates this at the source. Official Anthropic guidance: "ask Claude to quote relevant parts of the documents first before carrying out its task." |
| Complexity | Medium |
| Status | Not yet implemented. Current extraction produces structured output directly. |
| Confidence | HIGH -- Anthropic official documentation + production pipeline reports |

**What it means:** For each event or actor being extracted, the LLM must first output the verbatim filing text that supports it (inside `<quotes>` tags or similar), then produce the structured JSON record citing that quote. This creates a verifiable chain: quote -> structured record -> downstream verification. The verify gate can then check if the anchor_text matches the quoted passage, and whether the quoted passage actually exists in the source.

**Source:** [Anthropic Prompting Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) -- "Ground responses in quotes... This helps Claude cut through the noise."

---

### TS-3: Block-Aligned Semantic Chunk Boundaries

| Attribute | Detail |
|-----------|--------|
| Why Expected | The pipeline already produces semantically meaningful chronology blocks. Splitting mid-block for chunked extraction destroys context needed to correctly extract cross-sentence events (e.g., "the following day, Company A submitted..."). Semantic chunking is the industry standard for extraction accuracy. |
| Complexity | Low |
| Status | Partially implemented. Blocks exist but chunk boundaries are not formally enforced. |
| Confidence | HIGH -- consensus across NVIDIA, Pinecone, Weaviate chunking research |

**What it means:** When filing text exceeds a single context window (or when multiple chunks are used for attention management), chunk boundaries must fall between chronology blocks, never within them. Each chunk is a contiguous sequence of complete blocks.

**Source:** [NVIDIA Chunking Guide](https://developer.nvidia.com/blog/finding-the-best-chunking-strategy-for-accurate-ai-responses/), [Weaviate Chunking Strategies](https://weaviate.io/blog/chunking-strategies-for-rag)

---

### TS-4: Inter-Chunk Overlap with Context Tags

| Attribute | Detail |
|-----------|--------|
| Why Expected | Events that span block boundaries (NDA signed at end of one section, referenced in next) get lost without overlap. 2-block overlap with explicit XML context markers (e.g., `<prior_context>`, `<current_chunk>`) prevents boundary blindness without creating duplicate extractions. |
| Complexity | Low-Medium |
| Status | Not implemented. |
| Confidence | MEDIUM -- industry best practice for semantic chunking |

**What it means:** When extracting from chunk N, include the last 2 blocks of chunk N-1 wrapped in `<prior_context already_extracted="true">` tags. The LLM reads them for continuity but knows not to re-extract from them. Similarly, include the first 2 blocks of chunk N+1 as `<upcoming_context>` for forward reference.

---

### TS-5: Pydantic Schema-First Structured Output

| Attribute | Detail |
|-----------|--------|
| Why Expected | Schema enforcement is the industry-standard approach for reliable structured extraction. Without it, LLMs drift in field naming, omit optional fields, or add unexpected keys. |
| Complexity | Low (already exists) |
| Status | Implemented. `extra="forbid"` on all SkillModel subclasses. |
| Confidence | HIGH -- already validated in this codebase |

**What it means:** Every extraction artifact (actors, events, spans) is validated against strict Pydantic models. Unknown fields cause immediate rejection. This is already a strength of the pipeline and should be preserved.

---

### TS-6: Deterministic Verification Gates (Check, Verify, Coverage)

| Attribute | Detail |
|-----------|--------|
| Why Expected | LLM extraction is inherently non-deterministic. Without deterministic post-extraction validation, errors propagate silently into enrichment and export. The verify/coverage separation (structural integrity vs quote fidelity vs source completeness) is the correct decomposition. |
| Complexity | Medium (already exists) |
| Status | Implemented. check -> verify -> coverage -> enrich-core gate chain. |
| Confidence | HIGH -- already validated, industry convergence on generate-then-verify |

**What it means:** The existing fail-fast gate chain where each gate must pass before the next runs. This is a core strength. Research confirms the 2026 best practice is multi-layered evaluation: deterministic checks first, LLM-based evaluation only when deterministic methods cannot apply.

**Source:** [Deterministic vs LLM Evaluators Study 2026](https://dev.to/anshd_12/deterministic-vs-llm-evaluators-a-2026-technical-trade-off-study-11h)

---

### TS-7: Two-Pass Extraction (Forward Scan + Gap Re-Read)

| Attribute | Detail |
|-----------|--------|
| Why Expected | Single-pass extraction systematically misses low-salience events (NDAs for minor parties, advisor retentions mentioned in passing). The gap re-read forces explicit coverage of the full event taxonomy against the source. Research shows reflexive self-correction yields 9-15% absolute accuracy gains. |
| Complexity | Medium (already exists) |
| Status | Implemented. Pass 1 extracts actors then events; Pass 2 does taxonomy sweep + re-reads. |
| Confidence | HIGH -- already validated + academic confirmation of reflexive improvement |

**What it means:** The existing two-pass design. Pass 1 is the forward extraction. Pass 2 systematically checks each of 20 event types, re-reads relevant sections for gaps, and audits actor lifecycle completeness. This is retained and can be enhanced.

**Source:** [SCoRe: Multi-turn RL self-correction (ICLR 2025)](https://proceedings.iclr.cc/paper_files/paper/2025/file/871ac99fdc5282d0301934d23945ebaa-Paper-Conference.pdf)

---

### TS-8: Span-Backed Evidence Provenance

| Attribute | Detail |
|-----------|--------|
| Why Expected | Every extracted fact must trace to exact line/character positions in the immutable filing text. Without provenance, downstream auditing is impossible and verification degrades to keyword search. |
| Complexity | Medium (already exists) |
| Status | Implemented. SpanRecord with document_id, start_line, end_line, start_char, end_char, match_type. |
| Confidence | HIGH -- already validated, fundamental to correctness-first design |

**What it means:** The existing span registry (`spans.json`) that maps every evidence reference back to exact positions in frozen filing text. The canonical schema upgrade from legacy `evidence_refs` to `evidence_span_ids` + `spans.json` is the correct direction.

---

### TS-9: Fail-Fast Error Handling

| Attribute | Detail |
|-----------|--------|
| Why Expected | In correctness-first extraction, partial success is worse than loud failure. Silent fallbacks (returning empty results, substituting defaults, swallowing exceptions) contaminate downstream analysis. Fail-fast on violated assumptions is the only safe policy. |
| Complexity | Low (already exists, needs hardening) |
| Status | Mostly implemented. Some exceptions noted in CONCERNS.md (broad except in enrich_core.py). |
| Confidence | HIGH -- fundamental pipeline design principle |

**What it means:** No try/except swallowing. No fallback logic. No partial outputs. If a stage cannot produce correct output, it crashes with a specific error. This is already the stated design philosophy but has known violations to fix.

---

### TS-10: Extended Thinking / Adaptive Thinking for Extraction

| Attribute | Detail |
|-----------|--------|
| Why Expected | Complex M&A deal chronologies require multi-step reasoning: understanding temporal sequences, disambiguating party references, classifying formality signals from context. Extended/adaptive thinking lets the model reason before committing to structured output. |
| Complexity | Low (API parameter, already enabled) |
| Status | Implemented. CLAUDE.md confirms extended thinking is operational. |
| Confidence | HIGH -- Anthropic official guidance for complex extraction |

**What it means:** Enable adaptive thinking (`thinking: {type: "adaptive"}` with appropriate effort level) for extraction calls. For complex deals, use `high` effort. The model's internal reasoning about temporal ordering, party disambiguation, and formality signals is more reliable when thinking is enabled.

**Source:** [Anthropic Adaptive Thinking](https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking)

---

## Differentiators

Features that set the pipeline apart from naive LLM extraction. Not expected, but produce measurably better correctness when implemented.

### D-1: Evidence Items as Active Attention-Steering Checklist

| Attribute | Detail |
|-----------|--------|
| Value Proposition | Evidence items (pre-tagged date, actor, value, and process signal anchors from preprocessing) are currently a passive appendix. Promoting them to an active checklist the LLM must address forces attention on signals that might otherwise be lost in the middle of long chronologies. |
| Complexity | Medium |
| Status | Not implemented. Evidence items exist but are not structured as a must-address checklist. |
| Confidence | MEDIUM -- logical extension of "lost in the middle" mitigation + quote grounding |

**What it means:** Before extraction, compile evidence items into a structured checklist grouped by cue family (proposal, NDA, drop, process initiation, advisor). The prompt instructs the LLM: "For each evidence item below, indicate which extracted event addresses it or explain why no event applies." This converts passive source material into an active attention mechanism.

---

### D-2: Block-Level Metadata Enrichment in Preprocessing

| Attribute | Detail |
|-----------|--------|
| Value Proposition | Adding metadata to chronology blocks (approximate dates, named entities, evidence density score, temporal phase classification) during preprocessing gives the LLM structured context about each block before reading it. This pre-computation reduces extraction burden and enables complexity-based routing. |
| Complexity | Medium |
| Status | Not implemented. Blocks currently have block_id, document_id, start_line, end_line, text. |
| Confidence | MEDIUM -- logical extension but unvalidated in this specific domain |

**What it means:** During `preprocess-source`, annotate each block with: `approximate_date_range` (from regex date parsing), `entity_mentions` (party names detected), `evidence_density` (count of evidence items overlapping this block), `temporal_phase` (early/mid/late in chronology). The LLM receives these annotations as block-level context.

---

### D-3: Complexity-Based Routing (Single-Pass vs Multi-Pass)

| Attribute | Detail |
|-----------|--------|
| Value Proposition | Not all deals require the same extraction intensity. Simple deals (few parties, short chronology, single cycle) can use a more efficient single-pass extraction. Complex deals (many parties, multiple cycles, ambiguous drops) need multi-pass with overlap. Routing saves cost on simple deals and focuses compute on complex ones. |
| Complexity | Medium |
| Status | Not implemented. All deals use the same extraction approach. |
| Confidence | MEDIUM -- routing is a validated pattern but complexity heuristics need calibration |

**What it means:** After preprocessing, compute a complexity score based on: number of chronology blocks, number of evidence items, number of distinct entity mentions, presence of termination/restart events. Route to appropriate extraction configuration:
- **Simple** (score < threshold): Single chunk, single pass, lower thinking effort
- **Complex** (score >= threshold): Multi-chunk with overlap, two passes, high thinking effort

**Source:** [LLM Routing Research](https://arxiv.org/pdf/2603.12646)

---

### D-4: Expanded Few-Shot Examples (4-5 Diverse Scenarios)

| Attribute | Detail |
|-----------|--------|
| Value Proposition | Anthropic docs: "A few well-crafted examples can dramatically improve accuracy and consistency." With prompt caching, including 4-5 diverse examples adds minimal marginal cost. Examples covering NDA groups, ambiguous drops, cycle boundaries, and unnamed aggregates address the specific failure modes of M&A extraction. |
| Complexity | Medium-High (requires manual curation of gold-standard examples) |
| Status | Not implemented systematically. Extraction skill has inline examples but not diverse few-shot coverage. |
| Confidence | MEDIUM-HIGH -- Anthropic official guidance + prompt caching makes cost negligible |

**What it means:** Curate 4-5 complete input/output example pairs that cover:
1. Standard single-cycle deal with named bidders
2. Deal with NDA groups and unnamed aggregates ("15 parties signed confidentiality agreements")
3. Deal with ambiguous drops (bidder-initiated vs target-initiated)
4. Multi-cycle deal with termination and restart
5. Deal with complex formality signal classification (mixed informal/formal bids)

Place examples in the static prefix for prompt caching benefit.

**Source:** [Anthropic Prompting Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)

---

### D-5: Prompt Caching for System Prompt + Actor Roster

| Attribute | Detail |
|-----------|--------|
| Value Proposition | When extracting from multiple chunks of the same deal, the system prompt, few-shot examples, schema definition, and actor roster (from Pass 1) are identical across calls. Caching these static prefixes reduces cost by up to 90% and latency by up to 85% on subsequent chunk calls. |
| Complexity | Low-Medium |
| Status | Not implemented. Each extraction call sends the full prompt. |
| Confidence | HIGH -- Anthropic official documentation with concrete metrics |

**What it means:** Structure extraction calls with cache breakpoints:
1. **Cache layer 1:** System prompt + extraction schema + few-shot examples (static across all deals)
2. **Cache layer 2:** Actor roster from Pass 1 (static across chunks within a deal)
3. **Cache layer 3:** Current chunk's chronology blocks (varies per call)
4. **Uncached:** Instructions + query (at the end, per prompt ordering)

Up to 4 cache breakpoints are available per call.

**Source:** [Anthropic Prompt Caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)

---

### D-6: Temporal Consistency Gate

| Attribute | Detail |
|-----------|--------|
| Value Proposition | Events should be globally monotonic in time (with exceptions for cycles). Detecting temporal inconsistencies (e.g., a proposal dated before the process initiation, or an NDA after a drop for the same actor) catches extraction errors that structural and quote verification miss. |
| Complexity | Medium |
| Status | Partially implemented. verify-extraction SKILL.md mentions date monotonicity as a warning check. Not in deterministic gates. |
| Confidence | MEDIUM -- logical correctness check, straightforward to implement |

**What it means:** Add a deterministic gate (or enhance existing check/verify) that:
- Validates global date ordering (with exceptions for cycle boundaries)
- Validates per-actor lifecycle consistency (NDA before proposal before drop)
- Flags impossible temporal sequences (drop before any involvement, proposal after executed)

---

### D-7: Per-Actor Coverage Audit

| Attribute | Detail |
|-----------|--------|
| Value Proposition | Current coverage audits source evidence cues against extracted events. Per-actor coverage goes further: for each named actor, verify they have a complete lifecycle (entry event, optional proposals, exit event or final-deal involvement). Actors who appear and disappear without explanation indicate extraction gaps. |
| Complexity | Medium |
| Status | Partially implemented. Pass 2 gap re-read checks actor lifecycle but not as a deterministic gate. |
| Confidence | MEDIUM -- logical extension of existing coverage gate |

**What it means:** For each non-grouped actor with role=bidder:
- Verify they have at least one entry event (NDA, bidder_interest, or process invitation)
- If they have proposals, verify temporal ordering (entry before proposal)
- Verify they have either a drop event, an executed event, or appear in the final round
- Flag actors with incomplete lifecycles for re-examination

---

### D-8: Cross-Event Logical Consistency Checks

| Attribute | Detail |
|-----------|--------|
| Value Proposition | Beyond temporal ordering, certain event combinations are logically impossible: a bidder cannot be both executed-with and dropped; a round cannot have more invited bidders than active bidders; a formal round should not have fewer participants than an earlier informal round. |
| Complexity | Medium |
| Status | Not implemented as deterministic gate. Some checks exist in enrich-core round pairing. |
| Confidence | MEDIUM -- domain-specific correctness rules |

**What it means:** Add deterministic checks for:
- No actor appears in both `executed_with_actor_id` and a `drop` event
- `invited_actor_ids` count <= `active_bidders_at_time` in round structure
- Selective round (is_selective=true) should have fewer invitees than prior round
- Every `executed` event's counterparty should have a prior NDA or proposal

---

## Anti-Features

Features to explicitly NOT build. Each adds complexity that damages correctness, maintainability, or both.

### AF-1: RAG as Primary Architecture

| Anti-Feature | RAG-based retrieval for primary extraction |
|--------------|------------------------------------------|
| Why Avoid | Extraction requires exhaustive recall (every event in the filing), not selective retrieval. RAG introduces retrieval failure modes where relevant passages are missed by embedding similarity search. The filing fits in context. RAG was formally assessed and rejected in PROJECT.md. |
| What to Do Instead | Direct full-document or chunked extraction with block-aligned boundaries. Use targeted retrieval only for recovery passes when coverage identifies gaps. |
| Confidence | HIGH -- formally assessed and rejected |

---

### AF-2: Context Compression or Summarization

| Anti-Feature | Summarizing or compressing filing text before extraction |
|--------------|--------------------------------------------------------|
| Why Avoid | SEC filings use legally precise language where every word matters. "Indication of interest" vs "binding offer" is a single-word difference that changes formality classification. Summarization is lossy and risks destroying anchor text needed for verification. |
| What to Do Instead | Preserve verbatim filing text. Use chunking with overlap to manage context length. |
| Confidence | HIGH -- formally listed as out of scope |

---

### AF-3: LLM-as-Judge for Verification

| Anti-Feature | Using a second LLM to evaluate extraction quality |
|--------------|--------------------------------------------------|
| Why Avoid | LLM-based verification introduces a second source of non-determinism. When the judge and generator disagree, there is no ground truth to break the tie. Deterministic substring matching against filing text is provably correct. Adding an LLM judge layer adds cost, latency, and a new failure mode without improving correctness. |
| What to Do Instead | Use deterministic verification (exact/normalized substring matching) for quote verification. Use deterministic rules for structural and referential integrity checks. Reserve LLM involvement for the repair loop only (fix verified errors, not detect them). |
| Confidence | HIGH -- deterministic verification is provably more reliable for substring matching |

---

### AF-4: Self-Consistency via Majority Voting

| Anti-Feature | Running extraction N times and taking majority vote |
|--------------|-----------------------------------------------------|
| Why Avoid | Research shows self-consistency (sampling multiple outputs and voting) improves F1 only marginally while costing 3x tokens. For structured extraction with 20+ event types and complex schemas, defining "majority" across heterogeneous records is intractable. The deterministic verify/coverage gates catch errors more reliably than statistical agreement. |
| What to Do Instead | Single high-quality extraction with extended thinking, followed by deterministic verification and targeted repair. |
| Confidence | HIGH -- research confirms marginal ROI for structured extraction |

**Source:** [Self-Correction Benchmark (2025)](https://arxiv.org/html/2510.16062v1)

---

### AF-5: Fine-Tuned Domain-Specific Model

| Anti-Feature | Fine-tuning a model specifically for SEC filing extraction |
|--------------|----------------------------------------------------------|
| Why Avoid | 9-deal corpus is far too small for meaningful fine-tuning. Fine-tuning loses the general reasoning capability needed for novel deal structures. Prompt engineering with few-shot examples on frontier models outperforms fine-tuned smaller models on complex extraction. Fine-tuning also creates model lock-in, incompatible with multi-provider support. |
| What to Do Instead | Use frontier models (Claude, GPT) with well-engineered prompts and few-shot examples. Maintain multi-provider flexibility. |
| Confidence | HIGH -- corpus too small, multi-provider requirement |

---

### AF-6: Agentic Multi-Agent Orchestration

| Anti-Feature | Using multiple specialized LLM agents (one for actors, one for events, one for enrichment, etc.) communicating via message passing |
|--------------|--------------------------------------------------------------------------------------------------------------------------------|
| Why Avoid | Recent research (March 2026) shows reflexive/multi-agent architectures achieve the highest F1 (0.943) but at 2.3x the cost. For a 9-deal corpus, the complexity overhead is massive. The existing two-pass + deterministic gate architecture achieves similar quality at much lower complexity. Multi-agent introduces coordination failures and state consistency problems. |
| What to Do Instead | Keep the existing sequential pipeline: extract -> canonicalize -> check -> verify -> coverage -> repair -> enrich -> export. Each stage is a deterministic function or a single LLM call, not a multi-agent conversation. |
| Confidence | MEDIUM-HIGH -- multi-agent may be warranted for larger corpora but is overkill for 9 deals |

**Source:** [Multi-Agent Financial Document Processing Benchmark (2026)](https://arxiv.org/abs/2603.22651)

---

### AF-7: Automatic Retry/Fallback on Extraction Failure

| Anti-Feature | Automatically retrying failed extractions with relaxed parameters or fallback models |
|--------------|------------------------------------------------------------------------------------|
| Why Avoid | Retry with relaxed parameters means accepting lower quality output. Fallback to a weaker model means accepting less capable extraction. In a correctness-first pipeline, the right response to extraction failure is to fail loud and investigate, not to silently produce lower-quality output. Retries also mask systematic prompt issues that should be fixed. |
| What to Do Instead | Fail fast on extraction errors. Log the failure with full context. Fix the root cause (prompt issue, context overflow, schema mismatch) rather than retrying around it. |
| Confidence | HIGH -- core design principle of this pipeline |

---

### AF-8: Graph RAG or Knowledge Graph Construction

| Anti-Feature | Building a knowledge graph from extracted data and using graph traversal for enrichment |
|--------------|--------------------------------------------------------------------------------------|
| Why Avoid | Assessed in PROJECT.md and rejected. The 9-deal corpus does not warrant graph infrastructure. The deterministic enrichment (round pairing, bid classification, cycle segmentation) works correctly as sequential logic over flat event lists. Graph adds complexity without correctness benefit at this scale. |
| What to Do Instead | Keep flat event/actor lists with deterministic enrichment logic. The existing round_pairs, bid_classifications, cycles, and formal_boundary outputs are correct as-is. |
| Confidence | HIGH -- formally assessed and rejected |

---

### AF-9: Streaming/Incremental Extraction

| Anti-Feature | Processing filing text as a stream with incremental updates to extraction state |
|--------------|-------------------------------------------------------------------------------|
| Why Avoid | Extraction decisions are context-dependent: whether an event is a "proposal" vs "bidder_interest" depends on whether a prior NDA exists; formality classification depends on whether a final round has been announced. Streaming extraction would need to retroactively reclassify earlier events as later context arrives, creating state management complexity without benefit. |
| What to Do Instead | Batch extraction per chunk with full context (including overlap from adjacent chunks). The two-pass design already handles the need for context-dependent reclassification. |
| Confidence | HIGH -- context dependency makes streaming fundamentally unsuitable |

---

## Feature Dependencies

```
TS-1 (Prompt Ordering) -- no dependencies, implement first
  |
  v
TS-2 (Quote-Before-Extract) -- depends on TS-1 for optimal placement
  |
  v
TS-3 (Block-Aligned Chunks) -- independent, but prerequisite for:
  |
  +-> TS-4 (Inter-Chunk Overlap) -- depends on TS-3
  |
  +-> D-2 (Block Metadata) -- depends on block structure from TS-3
  |
  +-> D-3 (Complexity Routing) -- depends on D-2 for complexity signals

D-1 (Evidence Checklist) -- depends on TS-2 (quote protocol) for consistency

D-4 (Few-Shot Examples) -- independent, but benefits from:
  +-> D-5 (Prompt Caching) -- few-shot examples in cached prefix

D-5 (Prompt Caching) -- depends on TS-1 (static content at top)

D-6 (Temporal Consistency) -- independent deterministic gate
D-7 (Per-Actor Coverage) -- independent deterministic gate
D-8 (Cross-Event Logic) -- depends on D-6 (temporal ordering) + D-7 (actor lifecycle)

TS-5 through TS-10 are already implemented -- maintain and harden.
```

**Critical path:** TS-1 -> TS-2 -> TS-3 + TS-4 -> D-1 -> D-4 + D-5

**Independent track:** D-6 -> D-7 -> D-8 (enhanced deterministic gates, can proceed in parallel)

---

## MVP Recommendation

### Prioritize (highest correctness impact per effort):

1. **TS-1: Prompt Ordering** -- Zero-cost, up to 30% quality improvement. Implement immediately.
2. **TS-2: Quote-Before-Extract** -- Eliminates the most common verification failure mode at the source. Medium effort, highest correctness impact.
3. **TS-3 + TS-4: Block-Aligned Chunks with Overlap** -- Prevents boundary-induced extraction errors. Low-medium effort.
4. **D-5: Prompt Caching** -- Low effort, immediate cost/latency savings once prompt ordering is in place.
5. **D-1: Evidence Items as Checklist** -- Addresses "lost in the middle" for critical signals. Medium effort.

### Defer:

- **D-2: Block Metadata** -- Useful but not blocking. Implement when complexity routing is needed.
- **D-3: Complexity Routing** -- 9-deal corpus does not yet justify routing infrastructure. Implement after all deals are processed once and complexity variation is understood.
- **D-4: Few-Shot Examples** -- High value but requires manual curation of gold-standard examples from completed deals. Implement after stec baseline is validated.
- **D-6/D-7/D-8: Enhanced Gates** -- Valuable but incremental. Implement as needed when specific error patterns emerge.

---

## Sources

### Official Documentation (HIGH confidence)
- [Anthropic Prompting Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
- [Anthropic Prompt Caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)
- [Anthropic Adaptive Thinking](https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking)

### Academic/Research (MEDIUM-HIGH confidence)
- [Multi-Agent Financial Document Processing Benchmark (arxiv 2603.22651)](https://arxiv.org/abs/2603.22651)
- [LLM Self-Correction Benchmark (arxiv 2510.16062)](https://arxiv.org/html/2510.16062v1)
- [SCoRe: Self-Correction via RL (ICLR 2025)](https://proceedings.iclr.cc/paper_files/paper/2025/file/871ac99fdc5282d0301934d23945ebaa-Paper-Conference.pdf)
- [Lost in the Middle (TACL)](https://direct.mit.edu/tacl/article/doi/10.1162/tacl_a_00638/119630/)
- [Automated Self-Refinement for Product Attribute Extraction (arxiv 2501.01237)](https://arxiv.org/html/2501.01237v1)

### Industry/Blog (MEDIUM confidence)
- [Lessons from Running LLM Document Processing Pipeline in Production (Alan/Medium)](https://medium.com/alan/lessons-from-running-an-llm-document-processing-pipeline-in-production-33d87f99cdb1)
- [NVIDIA Chunking Strategy Guide](https://developer.nvidia.com/blog/finding-the-best-chunking-strategy-for-accurate-ai-responses/)
- [Weaviate Chunking Strategies](https://weaviate.io/blog/chunking-strategies-for-rag)
- [Pinecone Chunking Strategies](https://www.pinecone.io/learn/chunking-strategies/)
- [Deterministic vs LLM Evaluators 2026](https://dev.to/anshd_12/deterministic-vs-llm-evaluators-a-2026-technical-trade-off-study-11h)
- [LLM Routing Research (arxiv 2603.12646)](https://arxiv.org/pdf/2603.12646)
- [Unstract Intelligent Chunking](https://unstract.com/blog/how-intelligent-chunking-strategies-makes-llms-better-at-extracting-long-documents/)

---

*Feature landscape analysis: 2026-03-27*
