# Context Management and Attention Mechanisms for LLM-Based Structured Extraction

**Researched:** 2026-03-26
**Domain:** LLM extraction from long-form SEC filings (DEFM14A/PREM14A/SC 14D-9)
**Confidence:** HIGH (core findings), MEDIUM (specific parameter recommendations)

## Summary

This research surveys practical techniques for improving LLM extraction fidelity when processing long SEC filing chronology text (10K-50K+ tokens). The pipeline's only non-deterministic stage -- the LLM extraction of actors and events from chronology blocks -- is the single point where all quality originates, making context management and attention mechanisms the highest-leverage improvement area.

The findings organize along two axes. **Context Management** covers how to structure, chunk, prioritize, and compose input to the LLM. **Attention Mechanisms** covers prompting and API-level techniques that improve the model's focus on relevant evidence within the input it receives. The two axes interact: better context composition reduces the attention burden, and better attention techniques compensate for imperfect context composition.

**Primary recommendation:** The highest-ROI improvement is a three-part change: (1) restructure prompt ordering to place chronology text first and instructions/query last (exploiting recency bias for instructions, primacy bias for early evidence), (2) add an explicit "quote-then-extract" step that forces the model to cite relevant passages before emitting structured events, and (3) use extended thinking / adaptive thinking to give the model reasoning space for complex deals. These require no new infrastructure and directly address the "lost in the middle" failure mode.

---

## Context Management

### 1. The "Lost in the Middle" Problem

**Finding (HIGH confidence):** Language models perform best when relevant information appears at the beginning or end of input context, with significantly degraded performance when key information sits in the middle of long contexts. This is the single most important empirical finding for this pipeline.

**Specific data:**
- Liu et al. (2023, TACL 2024) measured a **30%+ accuracy drop** on multi-document question answering when the answer document moved from position 1 to position 10 in a 20-document context.
- The performance curve is **U-shaped**: models attend strongly to the first and last positions, with a trough in the middle. This holds even for models explicitly trained on long contexts.
- The root cause is **positional encoding bias** in the transformer architecture. Rotary Position Embedding (RoPE), used in most modern LLMs including Claude, introduces a decay effect that makes attention to middle positions weaker.
- Recent 2025 research confirms this is partly architectural (how positional encodings spread attention) and partly training-data-driven (exposure bias in pretraining corpora).

**Implication for this pipeline:** The current `extract-deal` skill sends chronology blocks in sequential order (B001 through B235 for stec). Events described in mid-chronology blocks (roughly B050-B180 in a 235-block filing) are at highest risk of being missed, misattributed, or poorly cited. This directly explains the known failure mode of "missed events in middle of long passages."

**Source:** [Liu et al., Lost in the Middle (2023)](https://arxiv.org/abs/2307.03172), published in TACL 2024.

### 2. Prompt Ordering and Composition

**Finding (HIGH confidence):** Anthropic's official documentation states that for long-context prompts (20K+ tokens), placing longform data at the top of the prompt and the query/instructions at the bottom improves response quality by up to 30%.

**The recommended token budget allocation:**

| Zone | Content | Position | Budget Share |
|------|---------|----------|-------------|
| Top | Chronology blocks + evidence items | First | 60-75% |
| Middle | Actor roster (for event pass), few-shot examples | Middle | 10-20% |
| Bottom | Task instructions, schema, output format request | Last | 15-25% |

**Rationale:** This layout exploits two biases simultaneously:
- **Primacy bias** means the model attends well to early chronology blocks (where deal initiation events live).
- **Recency bias** means the model attends well to the instructions and schema that appear last, improving instruction-following fidelity.
- The actor roster in the middle is acceptably positioned because it is a compact lookup reference, not the primary extraction source.

**Current state:** The existing prompt engineering spec (2026-03-16) places deal context first, then actor roster, then chronology blocks. This is partially correct but places the chronology blocks at the END of the user message where they benefit from recency but not primacy. The system prompt with instructions is separate and processed first by the API.

**Recommendation:** For deals with >150 blocks, consider flipping the user message ordering: chronology blocks first, then actor roster, then a compact extraction query at the bottom. Keep the system prompt unchanged (it already occupies the right position as a persistent instruction layer).

**Source:** [Anthropic Prompting Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)

### 3. Chunking Strategies

The current pipeline uses sequential chunking at approximately 3-4K tokens per chunk with consolidation. This section evaluates whether this is optimal.

#### 3a. Fixed-Size Sequential Chunking (Current Approach)

**Assessment:** The current approach is reasonable for moderate-complexity deals but suboptimal for complex ones.

**Strengths:**
- Simple, deterministic, and reproducible.
- 3-4K tokens per chunk keeps each chunk well within the attention span where the model performs best (no internal "lost in the middle" within a chunk).
- Consolidation pass handles cross-chunk deduplication.

**Weaknesses:**
- Fixed boundaries may split related events across chunks (e.g., a proposal and its counter-proposal that appear in adjacent blocks).
- No semantic awareness: a chunk boundary might fall between "Party A submitted a revised bid" and "which included a termination fee of $X million" -- separating the event from its economics.
- Overlap strategy not documented in the current extraction skill. The prompt engineering spec recommends "1-block overlap" but actual implementation is unclear.

#### 3b. Semantic Chunking

**Finding (MEDIUM confidence):** Semantic chunking divides text based on meaning rather than token count. For structured legal filings with clear paragraph boundaries, the chronology blocks already provide natural semantic units.

**Recommendation:** Rather than arbitrary token-count chunks, chunk at **chronology block boundaries** with a target budget. Each chronology block is already a semantic unit (a paragraph from the filing). Group consecutive blocks until the target token budget is reached, then split. Never split mid-block.

**Implementation sketch:**
```python
def plan_chunks(blocks: list[dict], budget: int = 4000) -> list[list[str]]:
    """Group blocks into chunks respecting semantic boundaries."""
    chunks, current, current_tokens = [], [], 0
    for block in blocks:
        block_tokens = len(block["clean_text"]) // 4  # rough estimate
        if current_tokens + block_tokens > budget and current:
            chunks.append(current)
            current, current_tokens = [], 0
        current.append(block["block_id"])
        current_tokens += block_tokens
    if current:
        chunks.append(current)
    return chunks
```

#### 3c. Overlap Strategy

**Finding (HIGH confidence):** A 10-20% overlap between chunks is standard practice and helps maintain cross-boundary context. For event extraction, the overlap should be measured in whole blocks, not tokens.

**Recommendation:** Use **2-block overlap** (include the last 2 blocks of chunk N as the first 2 blocks of chunk N+1). This is small enough to avoid excessive deduplication cost but large enough to preserve event continuity. Mark overlap blocks with a `<overlap_context>` tag so the model knows these blocks were already processed and should only be used for context, not as primary extraction targets.

**Example prompt annotation:**
```xml
<overlap_context>
These blocks were included in the prior chunk for continuity.
Only extract NEW events from these blocks if they were missed.
</overlap_context>
B097 [L1520-L1525]: ...
B098 [L1526-L1530]: ...

<primary_extraction_target>
Extract events from these blocks.
</primary_extraction_target>
B099 [L1531-L1540]: ...
...
```

#### 3d. Hierarchical / Coarse-to-Fine Chunking

**Finding (MEDIUM confidence):** Multi-pass architectures where a coarse pass identifies regions of interest followed by fine-grained extraction passes are effective for complex documents but add significant latency and cost.

**Architecture:**
1. **Coarse pass:** Send the entire chronology (or a summary) to identify which blocks contain events, proposals, and key transitions. Output: a "block importance map."
2. **Fine pass:** Extract events only from blocks flagged as important, with surrounding context blocks included for disambiguation.

**Tradeoffs:**
- Adds 1 extra LLM call per deal (the coarse scan).
- Risk of the coarse pass missing events (false negatives propagate).
- Cost increase: ~30-50% more tokens consumed.
- Latency increase: ~50-100% longer per deal.

**Assessment for this pipeline:** The evidence items already serve as a "coarse pass" -- they are deterministically pre-tagged anchors for dates, actors, values, and process signals. The coverage stage then audits whether extracted events cover the evidence items. This is a better architecture than a separate LLM coarse pass because it is deterministic and introduces no additional hallucination risk.

**Recommendation:** Do not add a separate LLM coarse pass. Instead, leverage evidence items more aggressively in the extraction prompt (see Attention Mechanisms section below).

### 4. Context Compression and Summarization

**Finding (MEDIUM confidence):** Context compression removes redundant or low-information tokens before sending to the LLM. Techniques include prompt compression (removing filler words while preserving meaning) and pre-summarization (replacing verbose passages with concise summaries).

**Assessment for this pipeline:** Filing text is legally precise language where every word may carry extraction-relevant meaning. Compression risks losing the verbatim anchor text needed for evidence references. This approach is **not recommended** for this pipeline.

**Exception:** Supplementary snippets from non-primary filings could be summarized before inclusion, since they serve as hints rather than primary evidence. But the current pipeline already provides them in a compact evidence-item format, making further compression unnecessary.

### 5. Token Budget Optimization

**Current budget analysis** (from prompt engineering spec):

| Component | Tokens | Share |
|-----------|--------|-------|
| System prompt (event taxonomy + rules) | ~2,000-3,500 | 15-25% |
| Actor roster (for event pass) | ~500-1,500 | 3-10% |
| Chronology blocks (per chunk) | ~3,000-4,000 | 30-40% |
| Few-shot examples | ~500-1,000 | 5-8% |
| Output budget | ~2,000-7,000 | 15-50% |
| **Total per chunk call** | ~8,000-17,000 | 100% |

**Optimization opportunities:**

1. **Reduce system prompt size.** The event taxonomy (20 types with descriptions) consumes ~1,500 tokens. For chunked extraction, the model only needs the full taxonomy in the first chunk. Subsequent chunks could receive a compact taxonomy (type names only, ~200 tokens) with a note "refer to the event taxonomy in your system instructions." However, this conflicts with API design where system prompts are reused.

2. **Increase chunk size for simpler deals.** Deals with fewer than 150 blocks and fewer than 10 actors can safely use 6-8K token chunks or even single-pass extraction. The routing thresholds in the prompt engineering spec (simple <= 8K, moderate 8-15K, complex > 15K) are well-calibrated.

3. **Use Anthropic prompt caching.** For repeated extraction runs (repair cycles), the system prompt and actor roster are identical across calls. Prompt caching reduces cost by 10x for cached tokens ($0.02/M vs $0.25/M). This is particularly valuable during verify-extraction repair loops.

**Source:** [Anthropic Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs), [Token Counting docs](https://docs.anthropic.com/en/docs/build-with-claude/token-counting)

### 6. RAG / Retrieval-Augmented Approaches

**Finding (MEDIUM confidence):** Anthropic's Contextual Retrieval technique (2024) reduces chunk retrieval failure rates by up to 67% by prepending contextual descriptions to each chunk before embedding.

**Assessment for this pipeline:** A full RAG approach (embed chronology blocks, retrieve relevant ones per query) is unnecessary because the pipeline already has a deterministic evidence-item layer that serves the same role. The chronology blocks are the complete extraction source; the question is not "which blocks are relevant" but "extract everything from all blocks."

**Where retrieval could help:** During the **targeted recovery** phase, if the coverage stage identifies a missing event type, a retrieval query could identify the most likely blocks containing that event type, reducing the context sent to the recovery LLM call.

**Recommendation:** Do not add RAG for the main extraction path. Consider lightweight retrieval (BM25 keyword search over blocks, not embedding-based) for targeted recovery passes.

---

## Attention Mechanisms

### 7. Quote-Before-Extract (Evidence Anchoring)

**Finding (HIGH confidence):** Anthropic's official documentation explicitly recommends: "For long document tasks, ask Claude to quote relevant parts of the documents first before carrying out its task. This helps Claude cut through the noise of the rest of the document's contents."

This is the single most actionable finding. The technique is called **evidence anchoring** or **quote-then-extract**:

1. First, ask the model to identify and quote relevant passages.
2. Then, based on those quotes, perform the structured extraction.

**Why it works:** Quoting forces the model to re-attend to specific passages in the source text, counteracting the "lost in the middle" decay. It also makes the extraction verifiable -- if the quoted passage doesn't support the extracted event, the error is visible before downstream gates.

**Current state:** The existing `extract-deal` skill already requires `evidence_refs` with `anchor_text` for every event. This is structurally similar to evidence anchoring but happens simultaneously with extraction rather than as a preceding step. The model may generate anchor text that is plausible but not grounded (hallucinated anchor text), because the citing and concluding happen in the same generation step.

**Recommended improvement:** Add an explicit two-phase prompt structure within each extraction call:

```xml
<task_phase_1>
Before extracting events, scan the chronology blocks below and quote
every passage that describes an action, decision, or milestone in the
deal process. For each quote, note:
- The block_id
- The verbatim passage (3-15 words)
- What it describes (date, actor action, financial term, process step)

Place your findings in <evidence_scan> tags.
</task_phase_1>

<task_phase_2>
Using ONLY the passages you identified in Phase 1, extract structured
events. Every event MUST reference a passage from your evidence scan.
Do not extract events that are not grounded in a quoted passage.
</task_phase_2>
```

**Tradeoff:** This increases output token consumption by 30-50% (the evidence scan itself takes tokens). For the structured output API path, this may require switching to a two-call architecture (scan call -> extraction call) since structured outputs constrain the entire response to the schema.

### 8. XML Tag Architecture for Attention Steering

**Finding (HIGH confidence):** Anthropic documents confirm Claude is specifically trained to recognize and use XML tag structure. Tags serve as implicit attention anchors -- the model weights content differently based on its tag context.

**Current state:** The existing prompts use XML tags well (`<mission>`, `<source_of_truth>`, `<event_taxonomy>`, `<chronology_blocks>`, etc.). This is already a strong practice.

**Recommended refinements:**

1. **Add importance hints within chronology blocks.** Pre-annotate blocks that the evidence scanner flagged as high-confidence:

```xml
<chronology_blocks>
B042 [L1380-L1385] <high_evidence_density>: On July 15, 2016, ...
B043 [L1386-L1390]: The Special Committee met to discuss...
B044 [L1391-L1400] <high_evidence_density>: Party A submitted a revised...
</chronology_blocks>
```

2. **Segment chronology into temporal phases.** If preprocessing can identify rough temporal boundaries (early process, mid-process, late process/closing), wrapping these in semantic tags helps attention:

```xml
<chronology_blocks>
<process_phase name="initiation" blocks="B001-B025">
B001 [L1244-L1244]: Background of the Merger
...
</process_phase>
<process_phase name="bidding" blocks="B026-B180">
B026 [L1320-L1325]: ...
...
</process_phase>
<process_phase name="closing" blocks="B181-B235">
B181 [L1800-L1805]: ...
...
</process_phase>
</chronology_blocks>
```

3. **Mark the evidence appendix distinctly from the chronology:**

```xml
<primary_source type="chronology">
[chronology blocks]
</primary_source>

<supplementary_evidence type="cross_filing">
[evidence items from other filings]
</supplementary_evidence>
```

### 9. Extended Thinking / Chain of Thought

**Finding (HIGH confidence):** Claude's extended thinking (or adaptive thinking on 4.6 models) dramatically improves performance on complex extraction tasks by giving the model internal reasoning space before generating the output.

**Specific benefits for this pipeline:**
- **Actor disambiguation:** When multiple parties have similar names or aliases (Party A, Bidder A), extended thinking lets the model reason about which entity is which before committing to actor_id assignments.
- **Date resolution:** Relative dates ("later that day," "the following week") require multi-step reasoning to resolve against prior absolute dates.
- **Formality signal assessment:** Determining whether a proposal is after a final round announcement requires tracking state across the chronology.
- **Evidence completeness:** The gap re-read pass (Pass 2 in the skill) benefits from reasoning about what event types are missing.

**API configuration recommendations:**

For extraction calls via the API:
```python
# For Claude Sonnet 4.6 (primary extraction model)
client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=16384,
    thinking={"type": "enabled", "budget_tokens": 16384},
    output_config={"effort": "high"},
    messages=[...],
)

# For simpler deals (< 100 blocks, < 8 actors)
client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=8192,
    thinking={"type": "enabled", "budget_tokens": 8192},
    output_config={"effort": "medium"},
    messages=[...],
)
```

**Cost consideration:** Extended thinking tokens are billed at output-token rates. A 16K thinking budget adds significant cost per call. However, if it reduces the number of verify-extraction repair cycles from 2-3 to 0-1, the net cost may be lower.

**Source:** [Anthropic Extended Thinking](https://platform.claude.com/docs/en/build-with-claude/extended-thinking), [Claude Prompting Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)

### 10. Few-Shot Example Placement

**Finding (MEDIUM confidence):** 3-5 diverse few-shot examples reliably improve extraction accuracy and schema compliance. Examples should be wrapped in `<example>` tags and placed between the source data and the extraction instructions.

**Current state:** The prompt engineering spec includes 2 examples (range proposal + partial-company exclusion, and formal-round signal). These are minimal but well-chosen.

**Recommendation:** Expand to 4-5 examples covering:
1. Range proposal with partial-company exclusion (existing)
2. Formal-round signal (existing)
3. NDA event with grouped actors ("16 financial buyers signed confidentiality agreements")
4. Drop event with ambiguous timing ("Party B informed the company it was no longer interested")
5. Terminated/restarted cycle boundary

**Placement rule:** Examples should appear AFTER the chronology blocks and BEFORE the extraction request. This puts them in the high-attention recency zone while keeping the extraction request at the very end (strongest recency position).

**Cost consideration:** Each example adds ~200-400 tokens. 5 examples = ~1,000-2,000 tokens. This is a modest cost for meaningful accuracy improvement.

### 11. Multi-Pass Extraction Architecture

**Finding (HIGH confidence):** Multi-pass extraction, where the model processes the same text multiple times with different focuses, improves accuracy for complex documents.

**Current state:** The skill already defines Pass 1 (forward scan) and Pass 2 (gap re-read). This is a good two-pass structure.

**Assessment of current implementation:** Pass 2 runs within the same LLM call as Pass 1 (they are prompt instructions, not separate API calls). This means:
- The model's attention to Pass 2 instructions competes with the rest of the output generation.
- There is no intermediate verification step between passes.
- The model cannot "zoom in" on specific blocks for Pass 2 because the entire context is already loaded.

**Recommended improvement -- Separate API calls for complex deals:**

For deals with >150 blocks or >15 actors:

| Pass | Focus | Input | Output |
|------|-------|-------|--------|
| Pass 1: Extract | Full extraction | All chunks (sequential) | events_draft.json |
| Pass 2: Audit | Gap identification | Full chronology + events_draft summary | gap_report.json |
| Pass 3: Recovery | Targeted extraction | Gap blocks + context blocks only | recovery_events.json |
| Merge | Deterministic | events_draft + recovery_events | events_raw.json |

For deals with <150 blocks:
- Keep the current single-call two-pass structure.
- The gap re-read within a single call is sufficient.

**Tradeoff:** Adds 1-2 extra API calls for complex deals. Estimated cost increase: 50-80%. Estimated accuracy improvement: 10-25% on complex deals (based on multi-pass extraction literature).

### 12. Structured Output Schema as Implicit Attention Guide

**Finding (MEDIUM confidence):** The JSON schema itself guides the model's attention. When the schema requires specific fields (e.g., `formality_signals` with 11 boolean flags), the model is forced to attend to evidence for each flag.

**Current state:** The pipeline's Pydantic schemas are well-designed attention guides. The `FormalitySignals` model with its 11 explicit boolean fields forces the model to evaluate each signal independently rather than making a holistic judgment.

**Recommendation:** No changes needed. The schema design is already strong. Consider using Anthropic's native structured output feature (compile JSON schema into a grammar that constrains token generation) for guaranteed schema compliance, reducing post-generation validation costs.

### 13. Temperature and Sampling Parameters

**Finding (HIGH confidence):** For extraction tasks requiring precision (dates, prices, entity names, evidence citations), use temperature 0 or as close to 0 as possible. Higher temperatures introduce randomness that corrupts factual extraction.

**Recommendation:** Temperature 0.0 for all extraction calls. This maximizes determinism and precision. The cost of occasional missed events (reduced recall) is lower than the cost of hallucinated events or corrupted data (reduced precision), because the verify/coverage stages can catch omissions but cannot detect plausible-but-wrong extractions.

**Current state:** The pipeline configuration (`skill_pipeline/config.py`) should enforce temperature 0 for extraction calls. This needs verification.

### 14. Evidence Item Integration as Attention Anchors

**Finding (MEDIUM confidence):** The pipeline's pre-computed evidence items (998 items for stec) are an underutilized attention mechanism. Currently, evidence items are available to the extraction prompt but their role as attention anchors is not explicit.

**Recommended approach -- Evidence-guided extraction:**

Instead of sending evidence items as a passive appendix, transform them into active extraction targets:

```xml
<evidence_guided_extraction>
The following high-confidence evidence cues were identified deterministically
from the filing. Your extraction MUST account for each cue. If a cue does not
correspond to an extractable event, explain why in coverage_notes.

<evidence_cues>
<cue evidence_id="E0012" type="dated_action" block="B042"
     date_text="July 15, 2016" confidence="high">
  "representatives of Thoma Bravo informally approached"
</cue>
<cue evidence_id="E0045" type="financial_term" block="B098"
     value_hint="$7.50 per share" confidence="high">
  "submitted an indication of interest of $7.50"
</cue>
...
</evidence_cues>
</evidence_guided_extraction>
```

This transforms evidence items from a reference lookup into a checklist that steers the model's attention. Each cue becomes an anchor point that the model must explicitly address.

**Tradeoff:** Including all evidence items as cues adds significant tokens. Filter to high-confidence items of types `dated_action`, `financial_term`, and `process_signal` only. Estimated addition: 500-2,000 tokens depending on deal complexity.

---

## Recommendations

### Priority-Ranked Implementation Plan

| # | Technique | Effort | Expected Gain | Confidence | Cost Impact |
|---|-----------|--------|---------------|------------|-------------|
| 1 | Prompt ordering (data first, query last) | Low | 10-30% quality | HIGH | None |
| 2 | Quote-before-extract (evidence anchoring) | Medium | 15-25% quality | HIGH | +30-50% tokens |
| 3 | Extended thinking / adaptive thinking | Low | 10-20% quality | HIGH | +30-100% tokens |
| 4 | 2-block overlap with explicit tags | Low | 5-10% quality | HIGH | +10% tokens |
| 5 | Evidence items as active attention anchors | Medium | 10-15% quality | MEDIUM | +10-20% tokens |
| 6 | Semantic chunk boundaries (block-aligned) | Low | 5-10% quality | HIGH | None |
| 7 | Expand few-shot examples to 4-5 | Low | 5-10% quality | MEDIUM | +500-1000 tokens |
| 8 | Separate audit pass for complex deals | High | 10-25% quality (complex deals only) | MEDIUM | +50-80% cost |
| 9 | Temporal phase tags in chronology | Medium | 5-10% quality | LOW | +200-500 tokens |
| 10 | Prompt caching for repair cycles | Low | 0% quality, -60% cost | HIGH | -60% for repeats |

**Quality percentages are relative improvements over current extraction, estimated from research literature and the specific characteristics of this pipeline's failure modes. They are NOT absolute accuracy numbers.**

### Recommended Implementation Order

**Batch 1 (immediate, low effort):**
- Item 1: Restructure prompt ordering
- Item 4: Add 2-block overlap with XML tags
- Item 6: Ensure chunk boundaries align with block boundaries
- Item 10: Enable prompt caching

**Batch 2 (next iteration, medium effort):**
- Item 2: Add quote-before-extract protocol
- Item 3: Configure extended thinking for extraction calls
- Item 5: Transform evidence items into active attention anchors
- Item 7: Expand few-shot examples

**Batch 3 (complex deals only, high effort):**
- Item 8: Separate audit pass architecture
- Item 9: Temporal phase annotations

---

## Tradeoffs

### Cost vs Quality

| Approach | Token Increase | Quality Gain | Net Cost Change |
|----------|---------------|--------------|-----------------|
| Prompt reordering only | 0% | +10-30% | No change |
| + Extended thinking | +30-100% | +10-20% additional | +$0.01-0.05/call |
| + Evidence anchoring | +30-50% | +15-25% additional | +$0.01-0.03/call |
| + Separate audit pass | +50-80% | +10-25% additional | +$0.02-0.05/call |
| + Prompt caching | -60% on repeats | No change | -$0.01-0.03/repeat |

**Key insight:** The first three improvements (reordering, thinking, anchoring) provide the bulk of quality improvement with modest cost increases. The separate audit pass is expensive but only needed for complex deals (stec, medivation, petsmart-inc).

### Latency vs Quality

| Approach | Latency Impact | Quality Impact |
|----------|---------------|----------------|
| Extended thinking (high effort) | +5-15 seconds | +10-20% quality |
| Quote-before-extract | +3-8 seconds | +15-25% quality |
| Separate audit pass | +20-40 seconds | +10-25% quality |
| Prompt caching | -2-5 seconds on repeats | No change |

**For this pipeline's use case (9 deals, batch processing, not real-time), latency is not a meaningful constraint.** The pipeline runs in batch mode and a 30-second per-deal increase is negligible.

### Complexity vs Maintainability

| Approach | Code Complexity | Maintenance Burden |
|----------|----------------|-------------------|
| Prompt reordering | Minimal (template change) | None |
| Block-aligned chunks | Minimal (chunking logic) | Low |
| Extended thinking | API parameter change | None |
| Evidence anchoring | Prompt template + possibly 2-call architecture | Medium |
| Separate audit pass | New pipeline stage | High |
| Temporal phase tags | Preprocessing logic | Medium |

---

## Current Pipeline Evaluation

### What the Current Architecture Gets Right

1. **Two-tier source model.** Separating primary chronology (narrative backbone) from cross-filing evidence (supplementary) is sound. The chronology is the extraction source; evidence items are validation anchors.

2. **Deterministic verification pipeline.** The check/verify/coverage gates catch extraction errors after the fact. This is a strong safety net that makes aggressive extraction improvements lower-risk (the gates catch regressions).

3. **Block-level granularity.** Chronology blocks are natural semantic units. Using `block_id` as the evidence reference unit is correct.

4. **Actor-then-event two-pass design.** Extracting actors first and providing the roster to the event pass reduces actor confusion.

5. **Coverage audit as missing-event detector.** The coverage stage compares evidence items against extracted events, catching omissions. This partially compensates for attention lapses.

### What Could Be Improved

1. **Prompt ordering.** Current prompt places instructions in system, roster + blocks in user. The user message should place blocks first, roster second, query last.

2. **No explicit evidence anchoring.** The model cites evidence and extracts simultaneously. Separating these into cite-then-extract would improve grounding.

3. **No extended thinking.** The current pipeline does not appear to use extended thinking / chain-of-thought for extraction calls. This is the easiest high-impact improvement.

4. **Chunk overlap is under-specified.** The prompt engineering spec mentions "1-block overlap" but the actual skill does not implement formal overlap tracking or overlap-zone tagging.

5. **Evidence items are passive.** Evidence items are provided as an appendix but not structured as an attention-steering checklist.

6. **No complexity-based routing.** All deals get the same extraction parameters regardless of complexity. Simple deals could use single-pass, while complex deals should get multi-pass with extended thinking.

---

## Common Pitfalls

### Pitfall 1: Over-Chunking Simple Deals
**What goes wrong:** Breaking a 100-block filing into 5 chunks of 20 blocks each introduces artificial boundaries and requires an unnecessary consolidation pass.
**Why it happens:** One-size-fits-all chunking threshold.
**How to avoid:** Route deals with <150 blocks and <8K chronology tokens through single-pass extraction. Reserve chunking for complex deals only.
**Warning signs:** More deduplication work in consolidation than actual event extraction.

### Pitfall 2: Hallucinated Anchor Text
**What goes wrong:** The model generates anchor_text that is plausible but not a verbatim substring of the filing.
**Why it happens:** The model generates the anchor text from memory/understanding rather than copying from the input. This is exacerbated when the relevant passage is in the middle of long input.
**How to avoid:** Use quote-before-extract (the model quotes first, then references its own quotes). The verify stage's strict quote resolution (EXACT/NORMALIZED only, FUZZY fails) catches this, but preventing it at extraction time is better.
**Warning signs:** High FUZZY match rates in verification_findings.json.

### Pitfall 3: Actor Confusion Across Chunks
**What goes wrong:** "Party A" in chunk 2 and "Party A" in chunk 4 are assigned to different actor_ids, or the same actor is extracted as two different entities.
**Why it happens:** Chunk isolation means the model loses cross-chunk actor identity.
**How to avoid:** Always include the full actor roster in every chunk's extraction call. The current skill design already does this for event extraction (actors are provided in the roster). For actor extraction itself, consider a single-pass approach even for complex deals.
**Warning signs:** Canonicalize stage reporting duplicate actor merges.

### Pitfall 4: Thinking Token Explosion
**What goes wrong:** Extended thinking consumes 50K+ tokens of internal reasoning, driving costs through the roof with minimal quality improvement.
**Why it happens:** Unbounded thinking budget on complex prompts.
**How to avoid:** Use `budget_tokens` to cap thinking at 16K tokens for extraction calls. Monitor thinking token usage per deal and adjust.
**Warning signs:** API bills showing output tokens >> input tokens.

### Pitfall 5: Evidence-Guided Extraction Becoming a Crutch
**What goes wrong:** The model only extracts events that have pre-computed evidence cues, missing events that the deterministic scanner did not flag.
**Why it happens:** The evidence cues are framed too strongly as a complete checklist.
**How to avoid:** Frame evidence cues as "minimum expected events" not "complete event list." Explicitly instruct: "Extract all events from the chronology, not only those with evidence cues."
**Warning signs:** Extracted event count drops to match evidence cue count.

---

## Open Questions

1. **What is the current extraction call's temperature setting?**
   - What we know: The `config.py` should contain LLM parameters.
   - What's unclear: Whether temperature is set to 0 or left at default.
   - Recommendation: Verify and enforce temperature 0 for all extraction calls.

2. **How does the structured output API interact with quote-before-extract?**
   - What we know: Structured outputs constrain the entire response to a schema. A free-form evidence scan cannot precede the structured JSON.
   - What's unclear: Whether a two-call approach (scan call + extract call) or a schema that includes an evidence_scan field is better.
   - Recommendation: Add an optional `evidence_scan` field to the extraction schema rather than a separate call. This keeps the architecture simple.

3. **Does the current skill implementation actually use chunk overlap?**
   - What we know: The prompt engineering spec recommends 1-block overlap. The skill defines Pass 1 and Pass 2.
   - What's unclear: Whether the Claude Code subagent that runs `/extract-deal` implements overlap in its prompting.
   - Recommendation: Audit the actual extraction prompts by running `/extract-deal` on a test deal and examining the API calls.

4. **What is the actual token count distribution across the 9 deals?**
   - What we know: stec has 235 blocks / ~21K tokens of chronology text (the largest).
   - What's unclear: The distribution for all 9 deals (only stec has preprocessed source currently).
   - Recommendation: Run `skill-pipeline preprocess-source` for all 9 deals and measure chronology sizes to calibrate chunking thresholds.

---

## State of the Art

| Old Approach (2023-early 2024) | Current Approach (late 2024-2025) | Impact |
|-------------------------------|----------------------------------|--------|
| Dump entire document into context | Structured chunking with overlap | Better recall on long docs |
| Fixed token-count chunks | Semantic / block-aligned chunks | Fewer split-event errors |
| No attention steering | XML tags + importance hints | Better focus on key passages |
| No thinking budget | Extended / adaptive thinking | Better reasoning on complex tasks |
| Single-pass extraction | Multi-pass extract + audit + recover | Higher coverage on complex docs |
| Temperature default (1.0) | Temperature 0 for extraction | Better precision on facts |
| Prefilled responses | Structured outputs API | Guaranteed schema compliance |
| Manual JSON validation | Schema-constrained generation | Zero parse errors |

---

## Sources

### Primary (HIGH confidence)
- [Anthropic Prompting Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) - long context handling, XML tags, thinking, evidence grounding
- [Anthropic Extended Thinking](https://platform.claude.com/docs/en/build-with-claude/extended-thinking) - thinking budget configuration, interleaved thinking
- [Anthropic Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) - schema-constrained generation
- [Liu et al., "Lost in the Middle" (2023), TACL 2024](https://arxiv.org/abs/2307.03172) - U-shaped attention curve, 30%+ accuracy degradation in middle positions
- [Anthropic Contextual Retrieval (2024)](https://www.anthropic.com/news/contextual-retrieval) - chunk augmentation technique, 67% retrieval failure reduction

### Secondary (MEDIUM confidence)
- [Pinecone Chunking Strategies](https://www.pinecone.io/learn/chunking-strategies/) - overlap strategies, semantic chunking patterns
- [Unstract: Intelligent Chunking for Long Documents](https://unstract.com/blog/how-intelligent-chunking-strategies-makes-llms-better-at-extracting-long-documents/) - multi-pass extraction benefits
- [NVIDIA Chunking Strategy Guide](https://developer.nvidia.com/blog/finding-the-best-chunking-strategy-for-accurate-ai-responses/) - practical chunking benchmarks
- [Context Engineering Guide](https://www.promptingguide.ai/guides/context-engineering-guide) - prompt composition, ordering effects
- [SNH AI: Perfect Extraction from Complex Documents](https://www.snh-ai.com/content/perfect-extraction) - multi-pass accuracy improvements

### Tertiary (LOW confidence)
- [LLM MapReduce Framework](https://github.com/Godskid89/LLM_MapReduce) - map-reduce for long sequences (arXiv 2024)
- [IntuitionLabs: LLMs for Financial Document Analysis](https://intuitionlabs.ai/articles/llm-financial-document-analysis) - SEC filing extraction patterns
- [2025 positional bias research](https://techxplore.com/news/2025-06-lost-middle-llm-architecture-ai.html) - architectural causes of position bias

---

## Metadata

**Confidence breakdown:**
- Context management: HIGH - well-established research with official Anthropic documentation
- Attention mechanisms: HIGH - direct Anthropic guidance plus peer-reviewed research
- Specific parameter recommendations: MEDIUM - extrapolated from general findings to this pipeline's specific extraction task
- Quality improvement estimates: LOW - these are directional estimates, not measured on this pipeline

**Research date:** 2026-03-26
**Valid until:** 2026-06-26 (3 months; longer for foundational findings, shorter for API-specific recommendations)
