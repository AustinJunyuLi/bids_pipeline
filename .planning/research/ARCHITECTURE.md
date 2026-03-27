# Architecture Patterns

**Domain:** Correctness-first document extraction pipeline for SEC filing M&A deal data
**Researched:** 2026-03-27

## Recommended Architecture

The pipeline follows a **deterministic-shell / LLM-kernel** pattern: an immutable document layer feeds into deterministic preprocessing, which structures input for a non-deterministic LLM extraction kernel, whose outputs are then validated and enriched through a chain of deterministic gates before export. The architecture is already well-established in this codebase. The redesign deepens it by adding annotation, prompt composition, and quote-before-extract stages between preprocessing and extraction.

### Architecture Diagram

```
                    IMMUTABLE LAYER
                    ==============
seeds.csv ---------> raw-fetch -----------> raw/<slug>/filings/*.txt
                                            raw/<slug>/discovery.json
                                            raw/<slug>/document_registry.json

                    DETERMINISTIC PREPROCESSING
                    ===========================
raw filings -------> preprocess-source ----> chronology_blocks.jsonl
                                            evidence_items.jsonl

                  + [NEW] annotate --------> annotated_blocks.jsonl
                                            (dates, entities, evidence density,
                                             temporal phase per block)

                    PROMPT COMPOSITION (NEW)
                    ========================
annotated blocks --> chunk-plan ------------> chunk_plan.json
+ evidence items     (block-aligned boundaries, 2-block overlap,
+ actor roster       complexity routing)
                  -> compose-prompt --------> per-chunk prompt payloads
                     (data-first ordering, XML tags, evidence checklist,
                      few-shot examples, quote-before-extract instructions)

                    LLM EXTRACTION KERNEL
                    =====================
prompt payloads ---> extract ----------------> per-chunk quote+extract responses
                     (quote-before-extract protocol:
                      1. cite relevant passages
                      2. extract structured actors/events from citations)
                  -> merge-chunks -----------> actors_raw.json, events_raw.json
                     (cross-chunk dedup, overlap reconciliation)

                    SCHEMA UPGRADE
                    ==============
raw artifacts -----> canonicalize -----------> actors.json, events.json, spans.json
                     (span resolution, date normalization,
                      semantic dedup, NDA gating, unnamed recovery)

                    DETERMINISTIC GATE CHAIN
                    ========================
canonical ---------> check ------------------> check_report.json
                     (structural: proposal terms, bidder kind, anchor text)
                  -> verify -----------------> verification_log.json
                     (quote resolution: EXACT/NORMALIZED only)
                  -> coverage ----------------> coverage_findings.json
                     (source cue audit against extracted artifacts)
              [NEW]-> temporal-consistency ----> temporal_report.json
              [NEW]-> cross-event-logic ------> logic_report.json
              [NEW]-> per-actor-coverage -----> actor_coverage.json
              [NEW]-> attention-decay --------> decay_diagnostics.json
                  -> [optional] verify-extraction (LLM repair if repairable)

                    DETERMINISTIC ENRICHMENT
                    ========================
gates pass --------> enrich-core ------------> deterministic_enrichment.json
                     (rounds, bid classification, cycles, formal boundary)
                  -> [optional] enrich-deal --> enrichment.json

                    EXPORT
                    ======
enriched ----------> export-csv -------------> deal_events.csv
                  -> [optional] reconcile-alex (post-export only)
```

### Component Boundaries

| Component | Responsibility | Inputs | Outputs | Communicates With |
|-----------|---------------|--------|---------|-------------------|
| **raw-fetch** | Discover and freeze SEC filings immutably | seeds.csv, SEC EDGAR | Immutable .txt files, discovery.json, document_registry.json | preprocess-source (downstream) |
| **preprocess-source** | Parse frozen filings into chronology blocks and evidence items | Frozen .txt files, document registry | chronology_blocks.jsonl, evidence_items.jsonl | annotate (downstream) |
| **annotate** (NEW) | Enrich blocks with metadata: dates, entities, evidence density, temporal phase | chronology_blocks.jsonl, evidence_items.jsonl | annotated_blocks.jsonl | chunk-plan, compose-prompt (downstream) |
| **chunk-plan** (NEW) | Decide chunk boundaries (block-aligned), overlap, complexity routing | annotated_blocks.jsonl | chunk_plan.json | compose-prompt (downstream) |
| **compose-prompt** (NEW) | Build per-chunk prompt payloads with data-first ordering, XML tags, evidence checklist, few-shot examples | chunk_plan.json, annotated_blocks.jsonl, evidence_items.jsonl, actor roster (if multi-pass) | Prompt payloads (in-memory or serialized) | extract (downstream) |
| **extract** | LLM calls with quote-before-extract protocol | Prompt payloads | Per-chunk quote + structured responses | merge-chunks (downstream) |
| **merge-chunks** (NEW) | Cross-chunk deduplication, overlap reconciliation, actor roster merging | Per-chunk responses | actors_raw.json, events_raw.json | canonicalize (downstream) |
| **canonicalize** | Schema upgrade: span resolution, date normalization, semantic dedup, NDA gating | Raw extract artifacts, frozen filings, chronology blocks, evidence items | Canonical actors.json, events.json, spans.json | check (downstream) |
| **check** | Structural blocker gate | Canonical extract artifacts | check_report.json | verify (downstream, gated) |
| **verify** | Quote resolution and referential integrity | Canonical artifacts, frozen filings, blocks, evidence | verification_log.json, verification_findings.json | coverage (downstream, gated) |
| **coverage** | Source evidence coverage audit | Canonical artifacts, evidence items, blocks | coverage_findings.json, coverage_summary.json | enrich-core (downstream, gated) |
| **temporal-consistency** (NEW) | Cross-event date ordering validation | Canonical events | temporal_report.json | Parallel with other enhanced gates |
| **cross-event-logic** (NEW) | Logical consistency (drop after NDA, proposal after NDA, etc.) | Canonical actors + events | logic_report.json | Parallel with other enhanced gates |
| **per-actor-coverage** (NEW) | Per-actor event trajectory completeness | Canonical actors + events, evidence items | actor_coverage.json | Parallel with other enhanced gates |
| **attention-decay** (NEW) | Detect position-correlated extraction gaps | Canonical events, chunk_plan.json, annotated_blocks.jsonl | decay_diagnostics.json | Diagnostic only |
| **enrich-core** | Deterministic rounds, bid classification, cycles, formal boundary | Canonical artifacts, gate reports | deterministic_enrichment.json | export (downstream) |
| **export-csv** | Filing-grounded CSV from extract + enrich artifacts | Canonical artifacts, enrichment | deal_events.csv | reconcile-alex (post-export) |

### Data Flow

**Forward flow is strictly linear and artifact-mediated.** Each component reads from upstream artifacts on the filesystem and writes its own artifacts. There are no in-process callbacks or bidirectional data flow between stages (except the optional LLM repair loop between gate findings and extraction).

1. **Immutable truth**: Filing .txt files frozen by raw-fetch are never modified. All downstream processing reads from these.
2. **Source artifacts**: chronology_blocks.jsonl and evidence_items.jsonl are deterministic derivations of the frozen text.
3. **Annotated artifacts** (NEW): annotated_blocks.jsonl adds computed metadata to blocks without modifying them -- purely additive enrichment.
4. **Prompt payloads**: Ephemeral or serialized prompt structures composed from annotated blocks, evidence items, actor rosters, and few-shot examples.
5. **LLM responses**: Raw structured output from the extraction kernel, one per chunk.
6. **Merged raw artifacts**: actors_raw.json, events_raw.json after cross-chunk reconciliation.
7. **Canonical artifacts**: Span-backed actors.json, events.json, spans.json after schema upgrade.
8. **Gate reports**: Each gate writes a report with status (pass/fail), findings, and diagnostics. Gates are sequential: check must pass before verify, verify before coverage.
9. **Enrichment**: Deterministic derivations (rounds, bids, cycles) from canonical artifacts and passing gate reports.
10. **Export**: Final structured output from enrichment + canonical artifacts.

**Key data flow principle**: Information only flows forward. No downstream stage modifies upstream artifacts. The only exception is the optional LLM repair loop, which rewrites extract artifacts based on gate findings -- but this is an explicit re-entry into the extraction stage, not a gate modifying its own inputs.

## Patterns to Follow

### Pattern 1: Deterministic Shell, LLM Kernel

**What:** All stages except extraction are deterministic Python. The LLM is the only source of non-determinism, and its outputs are validated by deterministic gates.

**When:** Always. This is the core architectural invariant.

**Why:** Deterministic code is testable, reproducible, and debuggable. LLM outputs are not. Confining non-determinism to a single stage makes the system auditable.

**Implementation:**
```python
# Every deterministic stage follows this pattern:
def run_stage(deal_slug: str, *, project_root: Path) -> int:
    paths = build_skill_paths(deal_slug, project_root=project_root)
    # 1. Validate inputs exist
    if not paths.required_input.exists():
        raise FileNotFoundError(f"Missing required input: {paths.required_input}")
    # 2. Load inputs via Pydantic models
    data = Model.model_validate_json(paths.input_path.read_text())
    # 3. Compute deterministic output
    result = compute(data)
    # 4. Write output atomically
    ensure_output_directories(paths)
    paths.output_path.write_text(result.model_dump_json(indent=2))
    # 5. Return exit code
    return 1 if result.status == "fail" else 0
```

**Confidence:** HIGH -- this is the existing pattern and aligns with best practices from controlled LLM pipeline research.

### Pattern 2: Quote-Before-Extract Protocol

**What:** Force the LLM to cite verbatim passages from the source text before producing structured extractions. The extraction schema references span IDs rather than generating citation text inline.

**When:** Every extraction call.

**Why:** This is the highest-ROI structural change for correctness. Anthropic's own documentation recommends it for long-document tasks: "ask Claude to quote relevant parts of the documents first before carrying out its task." The deterministic quoting pattern demonstrates that when quotes are retrieved via lookup rather than LLM generation, hallucinated citations drop to zero.

**Implementation approach:**
```xml
<instructions>
For each event you identify in the chronology blocks below:
1. First, cite the exact passage(s) that describe the event.
   Use <quote block_id="B042">verbatim text from block</quote> tags.
2. Then, extract the structured event record referencing those quotes.

Do NOT extract any event you cannot first quote evidence for.
</instructions>

<chronology>
  <block id="B042" lines="1273-1279">
    [block text here]
  </block>
  ...
</chronology>
```

**Confidence:** HIGH -- supported by Anthropic official documentation and the deterministic quoting research pattern.

### Pattern 3: Data-First Prompt Ordering

**What:** Place the long document content (chronology blocks, evidence items) at the top of the prompt, with instructions, schema, and examples at the bottom.

**When:** Every extraction prompt.

**Why:** Anthropic's testing shows queries at the end improve response quality by up to 30% for complex, multi-document inputs. This exploits recency bias in attention: the model attends more strongly to content near the query.

**Implementation:**
```
[System prompt: role, taxonomy, schema, few-shot examples]

[User message top: chronology blocks with XML tags and metadata]
[User message middle: evidence items as attention-steering checklist]
[User message bottom: extraction instructions and query]
```

**Confidence:** HIGH -- directly from Anthropic's official prompt engineering documentation.

### Pattern 4: Block-Aligned Semantic Chunking

**What:** When a filing exceeds the practical extraction context window, split at block boundaries (never mid-block), with 2-block overlap between adjacent chunks.

**When:** Filings that exceed the single-pass extraction budget.

**Why:** Blocks are the natural semantic units of the chronology section. Splitting mid-block risks severing a multi-sentence event description. The 2-block overlap provides enough context for the model to handle events that span block boundaries, while remaining cheap compared to full document duplication.

**Implementation considerations:**
- Block-level metadata (dates, entities, evidence density) from the annotate stage informs chunk boundary selection
- Prefer splitting at heading blocks or temporal phase transitions
- Track which blocks appear in multiple chunks for deduplication during merge
- Complexity routing: simple deals (fewer blocks, fewer actors) can use single-pass extraction; complex deals require multi-chunk

**Confidence:** HIGH -- block-aligned splitting is a natural extension of the existing block structure. The 2-block overlap is a domain-informed choice (not a general chunking recommendation).

### Pattern 5: Artifact-Mediated Stage Communication

**What:** Stages communicate exclusively through filesystem artifacts (JSON, JSONL, CSV). No in-process function calls between stages. No shared state except the filesystem.

**When:** Always.

**Why:** This makes stages independently testable, retryable, and debuggable. You can inspect any intermediate artifact to understand what happened. You can rerun a single stage without rerunning the entire pipeline. The existing architecture already follows this pattern well.

**Implementation:**
- Every stage reads from `SkillPathSet` paths and writes to `SkillPathSet` paths
- Artifact schemas are defined in Pydantic models with `extra="forbid"` for strict validation
- Atomic writes prevent partial artifacts from corrupting downstream stages

**Confidence:** HIGH -- existing pattern, well-validated.

### Pattern 6: Sequential Gate Chain with Fail-Fast

**What:** Deterministic gates run in a strict sequence. Each gate must pass before the next can run. Any gate failure blocks all downstream processing.

**When:** After extraction produces canonical artifacts.

**Why:** This prevents corrupted or incomplete data from propagating. The existing pattern (check -> verify -> coverage -> enrich-core) works well. The redesign adds more gates (temporal-consistency, cross-event-logic, per-actor-coverage) but maintains the same pattern.

**Gate ordering rationale:**
1. **check**: Structural completeness (cheapest, catches obvious schema violations)
2. **verify**: Quote resolution (more expensive, verifies evidence grounding)
3. **coverage**: Source cue audit (most expensive, compares extraction to source evidence)
4. Enhanced gates (temporal, logic, actor) run after the core three pass
5. **enrich-core**: Only runs when all gates pass

**Confidence:** HIGH -- existing pattern, straightforward to extend.

### Pattern 7: Prompt Caching for Multi-Chunk Extraction

**What:** Cache the system prompt (role, taxonomy, schema, few-shot examples) and the actor roster across chunk extraction calls using Anthropic's prompt caching.

**When:** Multi-chunk extraction where the same system prompt and actor roster are sent with each chunk.

**Why:** The system prompt and actor roster are identical across chunks for a given deal. Prompt caching reduces cost by 90% and latency by up to 85% for the cached prefix. The cache hierarchy (tools -> system -> messages) means the system prompt cache is preserved as long as the system prompt does not change.

**Implementation:**
- System prompt + actor roster = cached prefix (stable across chunks)
- Per-chunk chronology blocks + evidence items + instructions = variable suffix
- Cache breakpoints set after system prompt and after actor roster

**Confidence:** HIGH -- directly supported by Anthropic API, straightforward application.

### Pattern 8: Two-Pass Extraction (Actors Then Events)

**What:** Extract actors first in a dedicated pass, then extract events in a second pass that includes the established actor roster as context.

**When:** Always. The actor roster is needed to correctly attribute events to actors.

**Why:** This is the existing pattern and it is correct for this domain. M&A deals involve many actors with aliases and complex relationships. Establishing the actor roster first means event extraction can reference stable actor IDs rather than trying to co-discover actors and events simultaneously. The actor roster also enables prompt caching across event extraction chunks.

**Confidence:** HIGH -- existing validated pattern. The redesign preserves it.

## Anti-Patterns to Avoid

### Anti-Pattern 1: RAG for Primary Extraction

**What:** Using retrieval-augmented generation as the primary extraction architecture.

**Why bad:** RAG is designed for selective retrieval (find the most relevant passages for a question). Extraction requires exhaustive recall (find every relevant passage in the document). RAG's relevance scoring will miss low-salience but important events. The documents fit in context, so retrieval adds a failure mode without solving a real problem.

**When acceptable:** Lightweight BM25 retrieval for targeted recovery passes after coverage identifies gaps.

**Confidence:** HIGH -- explicitly assessed and rejected in PROJECT.md.

### Anti-Pattern 2: LLM for Deterministic Tasks

**What:** Using the LLM for tasks that can be done deterministically: chronology localization, date parsing, bid classification, round pairing.

**Why bad:** LLM outputs are non-deterministic, expensive, and slow. If a task can be encoded in Python rules, it should be. The existing codebase correctly keeps these tasks deterministic.

**Instead:** Keep the LLM confined to extraction (the task that genuinely requires language understanding) and let Python handle everything else.

**Confidence:** HIGH -- existing design principle, well-validated.

### Anti-Pattern 3: Silent Fallbacks in Gates

**What:** Gates that log warnings and continue instead of failing when they find errors.

**Why bad:** Silent failures propagate corrupted data downstream. The gate's entire purpose is to stop bad data. If a gate passes when it should fail, the system's correctness guarantee is compromised.

**Instead:** Fail fast and loud. Gates return exit code 1 on any error-level finding. Downstream stages refuse to run if gate artifacts are missing or show failure status.

**Confidence:** HIGH -- existing design principle from CLAUDE.md.

### Anti-Pattern 4: Mid-Block Chunk Splitting

**What:** Splitting chunks at arbitrary token boundaries that bisect chronology blocks.

**Why bad:** A chronology block often describes a single event or a tightly related sequence. Splitting mid-block means the model sees half an event in one chunk and the other half in the next, with no guarantee that overlap captures the full context. The quote-before-extract protocol depends on having complete blocks to cite from.

**Instead:** Always split at block boundaries. Use the annotate stage to identify good split points (heading blocks, temporal phase transitions, natural narrative breaks).

**Confidence:** HIGH -- domain-specific reasoning that follows from block-aligned evidence architecture.

### Anti-Pattern 5: Over-Engineering Chunk Merge

**What:** Building a complex graph-based deduplication system for cross-chunk merge with fuzzy matching, embedding similarity, and conflict resolution.

**Why bad:** With block-aligned chunking and 2-block overlap, the merge problem is constrained: the same blocks appear in at most 2 chunks. Deduplication can be done by block_id overlap. Events grounded in the same block(s) from adjacent chunks are candidates for dedup. Simple deterministic rules suffice.

**Instead:** Merge by block_id overlap. For events in the overlap zone, prefer the version from the chunk where the event's primary block_id is not at the boundary.

**Confidence:** MEDIUM -- the approach is sound but edge cases may require refinement during implementation.

## Scalability Considerations

This pipeline processes 9 deals, each with 1 primary filing. Scale concerns are minimal but worth documenting.

| Concern | Current (9 deals) | At 50 deals | At 500 deals |
|---------|--------------------|-------------|--------------|
| Filing size | 50-300KB text, fits in context | Same | Same; DEFM14A filings have consistent size range |
| LLM API cost | ~$2-5/deal (multi-chunk) | ~$100-250 total | Need batch API or parallel workers |
| Processing time | 5-15 min/deal sequential | 4-12 hours sequential | Parallelize per-deal; pipeline stages are independent across deals |
| Artifact storage | ~1MB/deal in JSON | ~50MB total | Negligible |
| Gate chain time | <30s/deal (deterministic) | <25 min total | Negligible; embarrassingly parallel across deals |

The bottleneck is always the LLM extraction kernel. All other stages are fast deterministic Python. Per-deal parallelism is trivial since deals share no artifacts.

## Build Order Implications

Components have strict dependency ordering that determines the build sequence:

### Layer 1: Foundation (No Changes Needed)
Already implemented and working:
- **raw-fetch**: Immutable filing freeze
- **preprocess-source**: Chronology blocks and evidence items

These are stable. Do not modify during redesign unless fixing bugs.

### Layer 2: Annotation (New, Prerequisite for Improved Extraction)
- **annotate**: Block-level metadata enrichment
  - Depends on: preprocess-source outputs
  - No downstream dependency until chunk-plan is built
  - Can be implemented and tested independently

### Layer 3: Prompt Architecture (New, Prerequisite for Extraction Improvement)
- **chunk-plan**: Block-aligned chunk boundary computation
  - Depends on: annotated blocks
- **compose-prompt**: Prompt payload assembly with data-first ordering
  - Depends on: chunk-plan, annotated blocks, evidence items, actor roster (from previous extraction or empty for actors-first pass)
  - This is where quote-before-extract, evidence checklist, and few-shot examples are wired in

### Layer 4: Extraction Improvement (Modified)
- **extract**: LLM calls with new prompt payloads
  - Depends on: compose-prompt outputs
  - Prompt caching configuration
  - Quote-before-extract response parsing
- **merge-chunks**: Cross-chunk reconciliation
  - Depends on: per-chunk extraction responses

### Layer 5: Schema Upgrade (Existing, May Need Updates)
- **canonicalize**: Span resolution for quote-before-extract output format
  - May need updates to handle new evidence reference format from quote-before-extract

### Layer 6: Enhanced Gates (New, Additive)
These can be built in parallel with each other after core gates exist:
- **temporal-consistency**: Date ordering validation
- **cross-event-logic**: Logical consistency checks
- **per-actor-coverage**: Actor trajectory completeness
- **attention-decay**: Position-correlated gap detection

### Layer 7: Existing Deterministic Chain (Minimal Changes)
- **check**, **verify**, **coverage**: May need schema updates for new enhanced gate integration
- **enrich-core**: May need to check enhanced gate results before running
- **export-csv**: No changes expected

### Recommended Build Sequence

```
Phase 1: annotate (Layer 2) + compose-prompt skeleton (Layer 3)
  - Independent, testable, no LLM cost
  - Validates block metadata and prompt structure

Phase 2: chunk-plan (Layer 3) + compose-prompt full (Layer 3)
  - Block-aligned chunking logic
  - Full prompt payload assembly with data-first ordering
  - Testable with fixture data

Phase 3: extract with quote-before-extract (Layer 4) + merge-chunks (Layer 4)
  - Wire up new prompts to LLM calls
  - Implement quote response parsing
  - Cross-chunk merge
  - End-to-end test on one deal

Phase 4: canonicalize updates (Layer 5) + enhanced gates (Layer 6)
  - Update span resolution for new evidence format
  - Add temporal, logic, coverage, decay gates
  - Each gate independently testable

Phase 5: Integration + pipeline orchestration
  - Wire stages into end-to-end CLI
  - Complexity routing (single-pass vs multi-chunk)
  - Prompt caching optimization
  - Run on all 9 deals
```

**Rationale for this ordering:**
1. Annotation and prompt composition are zero-LLM-cost, independently testable improvements
2. Extraction improvement depends on prompt composition
3. Enhanced gates depend on having extraction output to validate
4. Pipeline orchestration depends on all stages being individually functional

## Sources

- [Anthropic Long Context Tips](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/long-context-tips) -- data-first ordering, XML tags, quote-first strategy (HIGH confidence)
- [Anthropic Prompting Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) -- structured prompts, XML tags, role setting (HIGH confidence)
- [Anthropic Prompt Caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) -- cost/latency reduction for repeated prefixes (HIGH confidence)
- [Deterministic Quoting](https://mattyyeung.github.io/deterministic-quoting) -- quote text via database lookup, not LLM generation (HIGH confidence)
- [Anthropic Reduce Hallucinations](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations) -- verification with citations, retract if no supporting quote (HIGH confidence)
- [Controlled LLM-Based Generation Pipeline](https://www.emergentmind.com/topics/controlled-llm-based-generation-pipeline) -- deterministic shell / LLM kernel pattern (MEDIUM confidence)
- [Deterministic Blackboard Pipelines](https://community.unix.com/t/preprint-deterministic-blackboard-pipelines-with-specialized-llm-knowledge-sources-a-generalizable-architecture-for-intelligent-multi-stage-reasoning/397461) -- staged pipeline with deterministic control and specialized LLM knowledge sources (MEDIUM confidence)
- [Benchmarking Multi-Agent LLM for Financial Documents](https://arxiv.org/html/2603.22651) -- sequential pipeline, parallel fan-out, reflexive self-correcting loop for SEC filings (MEDIUM confidence)
- [Chunking Strategies for LLM Pipelines](https://www.typedef.ai/resources/tackle-chunking-context-windows-llm-data-pipelines) -- overlap, deduplication, context-enriched chunks (MEDIUM confidence)
- Existing codebase architecture at `.planning/codebase/ARCHITECTURE.md` (HIGH confidence)
- V3 pipeline design at `docs/plans/2026-03-16-pipeline-design-v3.md` (HIGH confidence)
- Prompt engineering spec at `docs/plans/2026-03-16-prompt-engineering-spec.md` (HIGH confidence)

---

*Architecture research: 2026-03-27*
