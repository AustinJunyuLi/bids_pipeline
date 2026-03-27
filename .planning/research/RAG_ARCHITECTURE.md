# RAG Architecture for Structured M&A Event Extraction from SEC Filings

**Researched:** 2026-03-26
**Domain:** RAG / Retrieval-Augmented Generation for structured information extraction
**Confidence:** HIGH (core assessment), MEDIUM (specific component recommendations)

---

## Summary

This research evaluates whether a RAG (Retrieval-Augmented Generation) architecture is the right approach for extracting structured M&A deal data from SEC filings. The pipeline processes 9 deals, each with a primary filing of 10K-50K tokens of chronology text, producing structured JSON (actors, events, evidence references) and CSV export.

**The honest answer is: RAG is not the right primary architecture for this problem, but specific RAG components can meaningfully improve the existing pipeline.** The core issue is that RAG was designed to find relevant passages from large corpora in response to queries. This pipeline needs to extract ALL structured events from individual documents -- a fundamentally different task where completeness (recall) matters more than relevance (precision). RAG optimizes for the wrong objective.

However, three specific RAG-adjacent techniques do address real pain points in the current pipeline: (1) hybrid retrieval for targeted recovery passes when the coverage stage identifies missed events, (2) embedding-based semantic similarity for deduplication and entity resolution during canonicalization, and (3) contextual chunking with metadata-enriched embeddings for better chunk-level retrieval during repair cycles.

**Primary recommendation:** Do not rebuild the pipeline around RAG. Instead, adopt a hybrid architecture (Option D below) that keeps the existing deterministic pipeline as the backbone and adds targeted retrieval capabilities for the specific stages where retrieval solves a real problem.

---

## 1. Is RAG the Right Frame?

### RAG vs. This Problem: A Fundamental Mismatch

**Confidence: HIGH**

RAG was designed to answer: "Given a question, which passages from my corpus are most relevant?" This pipeline needs to answer: "Given a document, extract EVERY structured event it contains." These are opposite retrieval paradigms:

| Dimension | RAG (Q&A) | This Pipeline (Extraction) |
|-----------|-----------|---------------------------|
| Query direction | Query -> find passages | Document -> find all events |
| Optimization target | Precision (relevant results) | Recall (miss nothing) |
| Corpus size | Large (millions of docs) | Small (1 document per deal) |
| Document count | Many documents, retrieve few | 1 document, process all of it |
| Success metric | Answer quality | Completeness of extraction |
| Failure mode | Irrelevant passages | Missed events |

**The retrieval step in RAG is designed to FILTER.** For extraction, filtering is the enemy -- you need to process everything.

### When RAG Makes Sense for Extraction

RAG becomes useful for extraction under specific conditions that partially apply here:

1. **Document too long for context window.** The chronology text for the largest deal (stec) is ~21K tokens. Claude Sonnet 4.6 has a 1M-token context window. The entire chronology fits comfortably in a single context window with room to spare. RAG's chunking-and-retrieval value proposition disappears when the full document fits in context.

2. **Cross-document extraction.** If you needed to extract events across ALL 9 deals simultaneously (cross-referencing actors who appear in multiple deals, finding industry patterns), RAG would add value. The current pipeline processes deals independently.

3. **Targeted recovery.** When the coverage stage identifies that specific event types are missing, retrieval can efficiently find the most likely blocks containing those events -- narrowing the LLM's focus rather than re-reading everything. This is where RAG genuinely helps.

### Alternative Retrieval-Augmented Patterns

Several RAG variants are more relevant than standard RAG:

**Agentic RAG:** An agent with retrieval tools that iteratively extracts, checks its own work, retrieves more context, and extracts again. This maps more naturally to the extraction problem than static retrieve-then-generate. The agent decides WHEN to retrieve based on gaps it identifies.

**Graph RAG:** Builds entity-relationship graphs from text, enabling queries like "which actors are connected to this proposal?" This is structurally aligned with M&A extraction (actors, events, relationships are the core schema). However, the entity extraction step that builds the graph IS the extraction problem -- Graph RAG doesn't solve it, it just reframes it.

**RAPTOR (Tree-Based RAG):** Recursively clusters and summarizes chunks into a tree structure, then retrieves at multiple levels of abstraction. This helps with thematic understanding but adds cost (3-5x more LLM calls for indexing) and does not address the completeness problem.

**Self-RAG:** The model itself decides when retrieval is needed. This maps well to the "extract, check, retrieve more if needed" pattern but requires fine-tuned models or complex prompting to implement.

### SEC Filing Characteristics That Affect RAG

**Makes RAG harder:**
- Temporal ordering matters. Events must be extracted in chronological sequence. Retrieval disrupts reading order.
- Cross-referencing between paragraphs. "The proposal described above" requires context from earlier blocks.
- Repetitive legal language. Dense embeddings struggle to differentiate paragraphs that use identical phrasing with different actors/dates.
- Entity ambiguity. "Party A," "the Company," "Bidder" refer to different entities depending on context. Embeddings lose this context.

**Makes RAG easier:**
- Clear section structure. "Background of the Merger" is a well-defined section.
- Date anchors. Most paragraphs start with dates, providing natural metadata for filtering.
- Domain-specific terminology. Financial/legal vocabulary is distinct, aiding embedding quality with specialized models.

### Assessment

**Confidence: HIGH.** Standard RAG is a poor fit for this problem. The documents are too small (fit in context), the task requires exhaustive extraction (not selective retrieval), and temporal ordering matters (retrieval disrupts sequence). Specific retrieval techniques can improve targeted recovery, but the primary extraction path should not be retrieval-based.

---

## 2. Embedding Strategy

### Embedding Model Comparison for SEC Filings

**Confidence: MEDIUM** (based on published benchmarks, not tested on this pipeline's data)

| Model | Dimensions | Context | Price/MTok | Financial Perf | Best For |
|-------|-----------|---------|------------|---------------|----------|
| Voyage finance-2 | 1024 | 32K | $0.12 | 54% on SEC data (best) | Domain-specific financial retrieval |
| Voyage 3-large | 1024-2048 | 32K | $0.18 | Outperforms finance-2 on general benchmarks | General + financial (best overall) |
| OpenAI text-embedding-3-large | 3072 | 8K | $0.13 | 38.5% on SEC data | General purpose, wide ecosystem |
| Cohere embed-v4 | 256-1536 | 128K | $0.12 | Strong general, no SEC-specific benchmark | Multimodal, long context |

**Key finding:** Voyage finance-2 outperformed OpenAI text-embedding-3-small by 40% on SEC filings data (54% vs 38.5% accuracy in direct financial queries). Domain-specific embeddings matter significantly for legal/financial text. However, Voyage 3-large now outperforms the older finance-specific model even on financial benchmarks.

**Recommendation:** Voyage 3-large for best overall quality, or Voyage finance-2 if budget-constrained. OpenAI text-embedding-3-large is acceptable but measurably worse on financial documents.

### Chunk Size for Embedding

For this pipeline, the chronology blocks ARE the natural chunks. Each block is a paragraph (typically 50-300 tokens). Options:

| Strategy | Chunk Size | Pros | Cons |
|----------|-----------|------|------|
| Block-level | 50-300 tokens | Natural semantic units, precise retrieval | Very small for embedding quality |
| Multi-block (3-5 blocks) | 200-1000 tokens | Better embedding quality, maintains local context | May span topic boundaries |
| Section-level | 1000-4000 tokens | Rich context for embeddings | Too coarse for targeted retrieval |

**Recommendation:** Embed at multi-block level (groups of 3-5 consecutive blocks, ~500-1000 tokens). This balances embedding quality with retrieval granularity. Include block IDs as metadata for line-level provenance.

### Contextual Retrieval (Anthropic's Approach)

Anthropic's contextual retrieval technique prepends document-level context to each chunk before embedding. For SEC filings, this would look like:

```
Original chunk: "On July 15, 2016, representatives of Thoma Bravo
informally approached the Company about a potential acquisition."

Contextualized chunk: "This is from the Background of the Merger section
of Imprivata's DEFM14A filing. The acquirer is Thoma Bravo. This paragraph
describes an early-stage approach event. On July 15, 2016, representatives
of Thoma Bravo informally approached the Company about a potential acquisition."
```

**Performance:** Reduces retrieval failure rate by up to 67% (35% from contextual embeddings alone, 49% combined with contextual BM25).

**Cost:** For 235 blocks at ~200 tokens each, plus ~100 tokens of context per block = ~70K tokens of LLM calls to generate contexts. At $3/MTok (Sonnet input), this is ~$0.21 per deal for one-time indexing. Negligible.

**Assessment:** Contextual retrieval is genuinely useful IF you build a retrieval path. For this pipeline, it matters only for the targeted recovery use case.

### Hybrid Search: Dense + Sparse (BM25)

**Confidence: HIGH** (well-established technique with strong empirical support)

Hybrid retrieval combining BM25 keyword search with dense embeddings improves recall by 15-30% over either method alone. For legal/financial text specifically:

- **BM25 excels at:** Exact entity names ("Thoma Bravo"), specific financial terms ("$7.50 per share"), accession numbers, dates.
- **Dense embeddings excel at:** Semantic similarity ("preliminary indication of interest" vs "initial proposal"), paraphrased concepts.
- **Combined:** Catches both exact keyword matches (critical for entity/date retrieval in legal text) and semantic matches.

**Recommendation:** If building a retrieval component, always use hybrid search. For legal/financial text, weight BM25 slightly higher (60/40 BM25/dense) because exact terminology matters more than in conversational text.

### Multi-Vector (ColBERT-Style)

ColBERT's late-interaction approach preserves token-level information rather than compressing to a single vector. This helps with entity-dense legal text where individual terms carry high information value.

**Assessment:** Overkill for 9 deals. ColBERT's advantages emerge at scale (millions of documents). The storage overhead (one vector per token) is unnecessary for a corpus this small. Not recommended.

---

## 3. Vector Database & Indexing

### Scale Assessment

**Confidence: HIGH**

The numbers for this pipeline:
- 9 deals, each with ~100-235 chronology blocks
- Total blocks across all deals: ~1,000-2,000
- At multi-block chunking (3-5 blocks per chunk): ~300-600 chunks total
- Embedding dimensions: 1024 (Voyage) or 3072 (OpenAI)
- Total vector storage: < 10 MB

This is a **trivially small** dataset for any vector database. The choice should optimize for simplicity and developer experience, not performance at scale.

### Vector DB Comparison for This Use Case

| Database | Type | Hybrid Search | Persistence | Complexity | Verdict |
|----------|------|--------------|-------------|------------|---------|
| ChromaDB 1.5 | Embedded | BM25 + dense (new) | Local files | Minimal | **Best fit** |
| LanceDB | Embedded | BM25 + dense | Disk-based (Arrow) | Minimal | Strong alternative |
| FAISS | Library | Dense only (add BM25 separately) | Manual save/load | Low | Too bare-bones |
| Qdrant | Server | Dense + sparse | Server or embedded | Medium | Overkill |
| Pinecone | Cloud | Dense + sparse | Cloud-managed | Medium | Wrong scale, adds cloud dependency |
| pgvector | Postgres extension | Dense + SQL | Postgres | High | Adds database dependency |

**Recommendation:** ChromaDB for simplicity, LanceDB if you want hybrid search with more control. Both are embedded (no server), Python-native, and support persistence. ChromaDB now supports BM25 sparse vector search as of recent releases.

### Index Architecture

**Per-deal indexes** (recommended over shared):
- Each deal is processed independently
- Per-deal indexes avoid cross-contamination
- Clean teardown: delete the deal's index to re-process
- Metadata per chunk: `{deal_slug, block_ids, start_line, end_line, date_mentions, entity_mentions, evidence_item_ids}`

```
data/skill/<slug>/index/
    chroma.sqlite3          # or lance/ directory
    metadata.json           # index creation params, embedding model
```

### Metadata Schema for SEC Chunks

```python
{
    "deal_slug": "imprivata",
    "document_id": "0001193125-16-465791",
    "block_ids": ["B042", "B043", "B044"],  # blocks in this chunk
    "start_line": 1380,
    "end_line": 1400,
    "date_mentions": ["July 15, 2016"],
    "entity_mentions": ["Thoma Bravo", "the Company", "Special Committee"],
    "evidence_item_ids": ["E0012", "E0013"],
    "has_financial_terms": true,
    "has_process_signals": true,
    "section": "background_of_merger"
}
```

This metadata enables filtered retrieval: "find chunks from July 2016 mentioning Thoma Bravo" becomes a metadata filter + semantic query.

---

## 4. Retrieval Strategy for Structured Extraction

### The Core Problem: RAG Optimizes for Precision, Extraction Needs Recall

**Confidence: HIGH**

Standard RAG retrieves the top-K most relevant passages. For structured extraction, you need ALL passages containing events. These are fundamentally different:

- Top-K retrieval: "Find the 5 best passages about Thoma Bravo's bid."
- Exhaustive extraction: "Find EVERY passage that mentions ANY event by ANY actor."

The second query is essentially "return all blocks" -- which defeats the purpose of retrieval.

### When Retrieval Actually Helps: Targeted Recovery

The one scenario where retrieval genuinely improves this pipeline is **targeted recovery after coverage audit**:

1. Full-context extraction runs (current approach)
2. Deterministic coverage audit identifies: "No withdrawal event extracted, but evidence item E0087 at block B145 contains a withdrawal signal"
3. **Retrieval query:** "Find all blocks related to withdrawal, declining, or exiting the process near block B145"
4. Recovery LLM call receives ONLY the relevant blocks + context, not the entire chronology
5. Focused extraction of the missed event

This is valuable because:
- The recovery LLM call sees fewer tokens, so attention is concentrated
- The retrieval query is specific (generated from the coverage finding), so precision is high
- It avoids re-processing the entire document for a single missed event

### Query Decomposition for Recovery

Generate retrieval queries from coverage findings:

```python
def coverage_finding_to_queries(finding: CoverageFinding) -> list[str]:
    queries = []
    # By event type
    for event_type in finding.suggested_event_types:
        queries.append(f"Event: {event_type}")
    # By evidence text
    for term in finding.matched_terms:
        queries.append(f"Action: {term}")
    # By block neighborhood
    for block_id in finding.block_ids:
        queries.append(f"Events near {block_id}")
    return queries
```

### Multi-Query Retrieval

For each coverage gap, generate 3-5 retrieval queries (by event type, by keyword, by actor, by date range) and union the results. This maximizes recall for the recovery pass.

### Iterative/Recursive Retrieval

Not recommended for the primary extraction path. The cost of iterate-retrieve-extract-check-retrieve-again cycles exceeds the cost of a single full-context pass for documents this size.

However, for repair cycles:
1. Extract (full context) -> check/verify/coverage
2. If coverage gaps: retrieve targeted blocks -> extract missing events
3. If still gaps: retrieve with broader queries -> extract again
4. Maximum 2 retrieval-recovery cycles before flagging for human review

### Evidence-Guided Retrieval

The existing deterministic evidence scanning (DATE_FRAGMENT_RE, MONEY_RE, ACTION_TERMS, PROCESS_TERMS from `source/evidence.py`) already identifies the blocks most likely to contain events. This is functionally equivalent to a retrieval step -- and it is deterministic, reproducible, and free (no embedding cost).

**Key insight:** The current pipeline's evidence item system IS a retrieval system. It uses regex-based keyword matching (equivalent to BM25) to identify important blocks. Adding embedding-based semantic retrieval on top of this provides marginal improvement for most cases.

---

## 5. End-to-End Architecture Options

### Option A: Classic RAG

```
EDGAR .txt
  |
  v
Chunk (by block groups, 3-5 blocks each)
  |
  v
Embed (Voyage 3-large)
  |
  v
Vector DB (ChromaDB)
  |
  v
For each event type: generate query -> retrieve top-K chunks -> LLM extract -> JSON
  |
  v
Merge + Dedup
  |
  v
check/verify/coverage/enrich
  |
  v
CSV export
```

**Components:**
- Embedding: Voyage 3-large ($0.18/MTok)
- Vector DB: ChromaDB (free, embedded)
- Orchestration: Raw API calls (no framework needed at this scale)
- LLM: Claude Sonnet 4.6 ($3/$15 input/output per MTok)

**Data flow:**
1. Chunk chronology blocks into groups of 3-5
2. Embed each chunk with contextualized descriptions
3. Store in ChromaDB with metadata
4. For each of ~20 event types, generate 2-3 retrieval queries
5. Retrieve top-10 chunks per query (with dedup)
6. Send retrieved chunks to LLM for extraction
7. Merge extracted events across all queries

**LLM calls:** ~40-60 per deal (20 event types x 2-3 queries, batched)

**Estimated cost per deal:**
- Embedding: ~50K tokens x $0.18/MTok = $0.01
- LLM calls: ~40 calls x ~8K input tokens x $3/MTok + ~2K output tokens x $15/MTok = ~$2.16
- Total: ~$2.20 per deal

**Strengths:**
- Each LLM call focuses on a specific event type, reducing confusion
- Smaller context per call means better attention
- Evidence is pre-filtered

**Weaknesses:**
- **Completeness is not guaranteed.** If the query doesn't retrieve a passage, the event is missed.
- 40-60 LLM calls per deal is expensive vs 3-8 calls in the current pipeline
- Event deduplication across queries is complex
- Temporal ordering is lost (retrieval returns chunks out of order)
- Cross-event relationships are invisible (the LLM extracting NDA events doesn't see the related proposal events)
- **Estimated 2-3x more expensive than current approach** for worse completeness guarantees

**Verdict: NOT RECOMMENDED.** Worse completeness at higher cost.

### Option B: Agentic RAG

```
EDGAR .txt
  |
  v
Chunk + Embed + Index (same as Option A)
  |
  v
Agent loop:
  |-- Tool: retrieve_chunks(query, filters)
  |-- Tool: extract_events(chunks, schema)
  |-- Tool: check_coverage(events_so_far, evidence_items)
  |-- Tool: get_context(block_ids) -> raw text around blocks
  |
  |-- Agent decides what to retrieve based on gaps
  |-- Iterates until coverage is satisfactory
  |
  v
Structured JSON (actors, events)
  |
  v
check/verify/coverage/enrich
  |
  v
CSV export
```

**Components:**
- Embedding: Voyage 3-large
- Vector DB: ChromaDB
- Agent: Claude Sonnet 4.6 with tool use
- Tools: retrieve, extract, check_coverage, get_raw_text
- Orchestration: Custom agent loop (no framework needed)

**Data flow:**
1. Index deal as in Option A
2. Agent starts with: "Extract all M&A events from this deal"
3. Agent retrieves initial chunks, extracts events
4. Agent checks coverage against evidence items
5. Agent retrieves additional chunks for gaps
6. Agent iterates until coverage is satisfactory or max iterations reached

**LLM calls:** 5-15 per deal (agent loop iterations), but each call is larger (tool definitions + conversation history)

**Estimated cost per deal:**
- Embedding: $0.01
- Agent loop: ~10 iterations x ~15K input tokens x $3/MTok + ~5K output tokens x $15/MTok = ~$1.20
- Total: ~$1.25 per deal

**Strengths:**
- Self-correcting: agent identifies and fills its own gaps
- Flexible: can focus attention on complex sections
- Uses retrieval surgically, not exhaustively

**Weaknesses:**
- **Agent reliability.** The agent must correctly decide WHEN to stop retrieving. Premature termination misses events. Over-retrieval wastes budget.
- Tool use adds token overhead (tool definitions ~700 tokens per call)
- Conversation history grows with each iteration
- Non-deterministic: different runs may extract different events
- Hard to debug: multi-turn agent behavior is opaque
- The agent's check_coverage tool is a reimplementation of the existing deterministic coverage stage

**Verdict: INTERESTING BUT RISKY.** The self-correcting loop is appealing, but agent reliability at this complexity level is unproven. The existing deterministic pipeline already has a coverage check -- the agent would be reimplementing it worse.

### Option C: Graph RAG / Knowledge Graph

```
EDGAR .txt
  |
  v
Chunk + Embed
  |
  v
Entity extraction (LLM: identify all actors, dates, financial terms)
  |
  v
Relationship extraction (LLM: identify actor-event-date triples)
  |
  v
Knowledge graph (Neo4j / NetworkX)
  |
  v
Graph queries: "all events involving Thoma Bravo" + "all proposals > $X" + ...
  |
  v
Structured JSON
  |
  v
check/verify/coverage/enrich
  |
  v
CSV export
```

**Components:**
- Entity extraction: Claude Sonnet 4.6
- Graph storage: NetworkX (in-memory, sufficient at this scale) or Neo4j (overkill)
- Graph queries: Python traversal (NetworkX) or Cypher (Neo4j)
- LLM: Claude Sonnet 4.6

**Data flow:**
1. LLM extracts entities (actors, dates, amounts) from each chunk
2. LLM extracts relationships (actor-did-thing-on-date triples)
3. Build a knowledge graph from entities + relationships
4. Query the graph for structured event records
5. Convert graph query results to JSON schema

**LLM calls:** 50-100+ per deal (entity + relationship extraction per chunk, plus graph refinement)

**Estimated cost per deal:**
- Entity extraction: ~50 chunks x ~3K input + ~1K output = ~$0.95
- Relationship extraction: ~50 chunks x ~5K input + ~2K output = ~$2.25
- Graph refinement: ~5 calls x ~10K input + ~3K output = ~$0.38
- Total: ~$3.60 per deal

**Strengths:**
- Explicit entity-relationship structure mirrors the M&A domain
- Enables cross-entity queries ("all events connected to Party A")
- Graph visualization aids human review
- Good for cross-deal analysis (build one graph per deal, then link)

**Weaknesses:**
- **The entity/relationship extraction step IS the hard problem.** Graph RAG doesn't solve extraction; it adds a layer on top of it.
- 3-5x more expensive than current approach
- Entity extraction accuracy is 60-85% depending on domain, meaning the graph starts with errors
- Deduplication and entity resolution in the graph is a hard problem itself
- Dramatically more complex to build and maintain
- The existing pipeline's actor/event schema is already a de facto knowledge graph -- it just stores as JSON instead of a graph database

**Verdict: NOT RECOMMENDED.** Adds cost and complexity without solving the core extraction problem. The existing Pydantic schema (actors with relationships to events) is already a structured knowledge representation.

### Option D: Hybrid (RAG + Current Deterministic Gates)

```
EDGAR .txt
  |
  v
[EXISTING] raw-fetch + preprocess-source
  |
  v
[EXISTING] Deterministic evidence scanning -> evidence_items.jsonl
  |
  v
[NEW] Embed chronology blocks (one-time indexing per deal)
  |
  v
[EXISTING] Full-context LLM extraction -> actors_raw, events_raw
  |
  v
[EXISTING] canonicalize -> check -> verify -> coverage
  |
  v
[NEW] If coverage gaps:
  |     coverage_findings -> retrieval queries -> targeted chunks
  |     -> focused recovery LLM call -> merge recovered events
  |     -> re-run check/verify/coverage
  |
  v
[EXISTING] enrich-core -> export-csv
```

**Components:**
- Embedding: Voyage 3-large (for recovery index only)
- Vector DB: ChromaDB (for recovery index only)
- LLM: Claude Sonnet 4.6 (same as current)
- Everything else: existing pipeline unchanged

**Data flow:**
1. Current pipeline runs exactly as-is through extraction and coverage
2. If coverage identifies gaps: new retrieval-based recovery step
3. Coverage findings generate targeted retrieval queries
4. Retrieve relevant chunks from pre-built index
5. Focused LLM call extracts missed events from retrieved chunks
6. Merge recovered events with existing extraction
7. Re-run deterministic gates

**LLM calls:** Same as current pipeline + 1-3 recovery calls per deal (only when needed)

**Estimated cost per deal:**
- Embedding (one-time): $0.01
- Current pipeline: ~$0.50-1.50 (varies by deal complexity)
- Recovery calls (when needed): ~$0.10-0.30 per call, 1-3 calls = $0.10-0.90
- Total: ~$0.60-2.40 per deal (marginal increase over current)

**Strengths:**
- **Preserves everything that works.** The current pipeline's deterministic gates, fail-fast behavior, and evidence provenance are unchanged.
- **Addresses the actual pain point.** The "lost in the middle" problem manifests as coverage gaps -- this option directly targets those gaps.
- **Minimal new infrastructure.** Adds an embedding step and a recovery stage; reuses existing stages.
- **Incremental cost.** Embedding is cheap ($0.01/deal). Recovery calls happen only when needed.
- **Non-disruptive.** Can be added without modifying existing stages. Falls back to current behavior if recovery is not needed.

**Weaknesses:**
- Still uses full-context extraction as the primary path (inherits attention decay issues, though mitigated by the context management improvements from prior research)
- Adds complexity to the pipeline (new stage, new dependency on ChromaDB/Voyage)
- Recovery may not catch all gaps (retrieval is still precision-oriented)
- Requires maintaining an embedding index per deal

**Verdict: RECOMMENDED.** This is the right balance of improvement vs. complexity. It addresses the real problem (missed events from attention decay) without throwing away the pipeline's existing strengths (deterministic verification, fail-fast gates, evidence provenance).

---

## 6. The Completeness Problem

### Why Completeness Is the Dealbreaker

**Confidence: HIGH**

For M&A deal extraction, missing a single event can invalidate the analysis. A missed counter-proposal changes the bid narrative. A missed NDA affects the actor roster. A missed withdrawal alters the deal timeline. The pipeline's value depends on extracting EVERY event, not just the important ones.

RAG systems are fundamentally recall-limited. Published benchmarks show:
- Top-20 chunk retrieval failure rates of 35-67% depending on technique (Anthropic's contextual retrieval paper)
- Hybrid search (BM25 + dense) improves recall by 15-30% but does not guarantee 100%
- Multi-query retrieval helps but adds cost and still misses edge cases

### How the Current Pipeline Handles Completeness

The existing pipeline has a strong completeness architecture:

1. **Full-context extraction.** The LLM reads the entire chronology (or chunked with overlap), so nothing is filtered out at the retrieval stage. The only failure mode is attention decay within the LLM's processing.

2. **Deterministic evidence scanning.** The coverage stage uses regex patterns to identify blocks containing dates, financial terms, process signals, and action terms. This creates a deterministic "expected events" checklist.

3. **Coverage audit.** The coverage stage compares extracted events against the evidence item checklist. Uncovered high-confidence critical evidence triggers a failure.

4. **Repair cycle.** The verify-extraction step can trigger a repair loop to fill gaps.

This is a defense-in-depth approach: full-context processing (attempt to miss nothing) + deterministic coverage check (detect what was missed) + repair cycle (fill gaps). RAG's retrieval step ADDS a failure mode (retrieval misses) that the current architecture avoids.

### Guaranteeing Completeness with RAG

If you insist on using RAG for the primary extraction path, guaranteeing completeness requires:

1. **Retrieve ALL chunks for at least one pass.** This defeats the purpose of retrieval.
2. **Full-context sweep after RAG extraction.** A final LLM pass reads the entire document to catch anything the retrieval missed. This makes RAG redundant (you still need a full-context pass).
3. **Exhaustive multi-query retrieval.** Generate retrieval queries for every possible event type, date range, actor, and keyword. This converges to "retrieve everything" for documents this size.

**Bottom line:** For a 21K-token document, there is no retrieval strategy that is both more complete AND cheaper than simply reading the whole thing. RAG's value proposition is that it avoids reading everything. When you need to read everything, RAG adds overhead without adding value.

### Where Completeness and Retrieval CAN Coexist

The one scenario where retrieval improves completeness is **targeted recovery** (Option D):

1. Full-context extraction (attempt completeness)
2. Deterministic coverage check (detect gaps)
3. Targeted retrieval for SPECIFIC gaps (efficient recovery)

The retrieval step in (3) does not need to guarantee completeness -- it only needs to find the blocks relevant to a SPECIFIC known gap. This is a much easier retrieval problem with much higher precision.

---

## 7. Technology Stack

### Recommended Stack for Option D (Hybrid)

**Confidence: MEDIUM** (component recommendations based on published benchmarks, not tested on this pipeline)

#### Embedding Model

**Primary:** Voyage 3-large
- Why: Best overall performance including financial domains. 9.74% better than OpenAI v3-large across benchmarks.
- Dimensions: 1024 (can reduce to 512 with Matryoshka for storage savings)
- Context: 32K tokens (more than sufficient for multi-block chunks)
- Price: $0.18/MTok ($0.01 for the entire deal corpus)
- Install: `pip install voyageai`

**Fallback:** OpenAI text-embedding-3-large
- Why: Already in the project's dependency chain (OPENAI_API_KEY env var exists)
- Dimensions: 3072 (or reduced to 1024 via Matryoshka)
- Price: $0.13/MTok
- Install: Already available via `openai` package

#### Vector Database

**Primary:** ChromaDB 1.5
- Why: Embedded (no server), Python-native, now supports BM25 for hybrid search, persistent storage, simplest API
- Install: `pip install chromadb>=1.5`
- Storage: `data/skill/<slug>/index/` (per-deal, gitignored)

**Alternative:** LanceDB
- Why: Disk-based (Arrow format), built-in hybrid search, better for larger-than-memory datasets
- Install: `pip install lancedb`
- Advantage: More efficient disk I/O for repeated queries

#### Orchestration Framework

**Recommendation: None (raw API calls)**
- Why: The pipeline processes 9 deals with ~3-8 LLM calls each. LangChain/LlamaIndex/Haystack add ~5-14ms of framework overhead per call, which is negligible, but they add significant dependency complexity, abstraction layers, and API churn.
- The existing `skill_pipeline` already has clean stage separation. Adding a framework on top of `cli.py` -> `canonicalize.py` -> `check.py` -> `verify.py` -> `coverage.py` would not simplify anything.
- At this scale, raw `voyageai.Client().embed()` and `chromadb.PersistentClient()` are simpler and more maintainable than any framework's wrapper.

#### LLM for Extraction

**Primary:** Claude Sonnet 4.6
- Why: Already the pipeline's primary model. 1M context at standard pricing ($3/$15 per MTok). Extended thinking support.
- For recovery calls: Same model, smaller context window, focused prompt.

**Cost optimization:**
- Batch API: 50% discount ($1.50/$7.50 per MTok) for non-urgent batch processing of all 9 deals.
- Prompt caching: 90% discount on cached input tokens ($0.30/MTok) for system prompts and actor rosters reused across chunk calls.

#### Python Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| `voyageai` | latest | Embedding generation |
| `chromadb` | >= 1.5 | Vector storage + hybrid search |
| `anthropic` | latest | Claude API (already a dependency) |
| `pydantic` | >= 2.0 | Schema validation (already a dependency) |

**No new major dependencies.** The hybrid approach adds only `voyageai` and `chromadb` to `pyproject.toml`.

---

## 8. Honest Assessment

### For THIS Specific Problem, Is RAG Better?

**No.** For 9 deals with individual documents of 10K-50K tokens that fit entirely within the LLM's context window, RAG is not better than the current approach. Here is the reasoning:

**What RAG buys you (vs current pipeline):**
1. Targeted recovery for missed events. This is real value, but can be added incrementally (Option D) without rebuilding the pipeline.
2. Metadata-enriched search for repair queries. The coverage findings already identify which blocks to re-examine; adding semantic search makes this more precise.
3. Future scalability to more deals. If the pipeline grows to 100+ deals with cross-deal queries, a shared index becomes useful.

**What RAG costs you (vs current pipeline):**
1. **Completeness risk.** Retrieval-based extraction cannot guarantee it found all events. The current full-context approach reads everything -- imperfect due to attention decay, but with a higher completeness floor.
2. **Complexity.** Adding embeddings, a vector database, and retrieval queries adds infrastructure that must be maintained, debugged, and tested.
3. **Cost.** Embedding costs are negligible, but retrieval-based extraction typically requires more LLM calls (40-60 per deal for Option A vs 3-8 for the current approach).
4. **Determinism loss.** Embedding similarity is non-deterministic (model updates change results). The current pipeline's regex-based evidence scanning is fully deterministic.
5. **Temporal ordering disruption.** Retrieval returns chunks by relevance, not chronological order. The extraction LLM loses the narrative flow that helps it understand event sequences.

### When Would RAG Become Clearly Superior?

| Condition | Why RAG Wins | Threshold |
|-----------|-------------|-----------|
| Many more deals | Shared index enables cross-deal queries, pattern detection | > 50-100 deals |
| Much longer documents | Full-context extraction becomes impossible or too expensive | > 200K tokens per filing |
| Real-time processing | Retrieval is faster than full-context processing | Latency matters (not batch) |
| Cross-deal analysis | "Find all deals where Party X was an advisor" | Cross-deal queries required |
| Continuous ingestion | New filings added daily, need incremental updates | Ongoing pipeline, not batch |

For the current 9-deal, batch-processing, individual-document use case, none of these conditions apply.

### The Right Architecture for This Problem

**Confidence: 8/10**

1. **Keep the current pipeline** as the backbone. Full-context extraction + deterministic gates is the right architecture for exhaustive event extraction from individual documents.

2. **Implement the context management improvements** from the prior research (CONTEXT_AND_ATTENTION.md). Prompt ordering, extended thinking, evidence anchoring, and block-aligned chunking with overlap address the "lost in the middle" problem directly.

3. **Add targeted retrieval (Option D)** as a recovery stage. When coverage identifies gaps, use embedding-based retrieval to find relevant blocks for focused recovery calls.

4. **Do NOT rebuild around RAG.** The cost/complexity/completeness tradeoffs are unfavorable for this problem size and structure.

### Cost Comparison Summary

| Architecture | LLM Calls/Deal | Est. Cost/Deal | Completeness | Complexity |
|-------------|----------------|----------------|-------------|------------|
| Current pipeline | 3-8 | $0.50-1.50 | Good (attention decay in middle) | Moderate |
| Current + context improvements | 3-10 | $0.60-2.00 | Better (addresses attention decay) | Moderate |
| **Option D: Hybrid (recommended)** | **4-11** | **$0.60-2.40** | **Best (recovery fills gaps)** | **Moderate+** |
| Option A: Classic RAG | 40-60 | ~$2.20 | Worse (retrieval misses) | High |
| Option B: Agentic RAG | 5-15 | ~$1.25 | Variable (agent dependent) | Very High |
| Option C: Graph RAG | 50-100+ | ~$3.60 | Good (if entity extraction works) | Very High |

---

## Common Pitfalls

### Pitfall 1: RAG as a Silver Bullet
**What goes wrong:** Team rebuilds pipeline around RAG, discovers that retrieval-based extraction misses more events than full-context extraction.
**Why it happens:** RAG hype obscures the fact that retrieval is a filter -- and filtering reduces recall.
**How to avoid:** Always ask: "Does this problem need retrieval (finding relevant subsets) or processing (extracting from everything)?"
**Warning signs:** Retrieval-based extraction consistently scores lower on coverage audit than full-context extraction.

### Pitfall 2: Over-Engineering the Vector Database
**What goes wrong:** Setting up Pinecone/Qdrant/Weaviate server infrastructure for 1,000 vectors.
**Why it happens:** Defaulting to "production-grade" infrastructure regardless of scale.
**How to avoid:** Use embedded databases (ChromaDB/LanceDB) for anything under 100K vectors. Graduate to a server when you need it.
**Warning signs:** More time spent on database infrastructure than on extraction quality.

### Pitfall 3: Losing Temporal Ordering
**What goes wrong:** Retrieval returns chunks by similarity, not chronological order. The LLM extracts events out of sequence, losing "the following week" / "subsequently" temporal references.
**Why it happens:** Semantic similarity ignores document position.
**How to avoid:** Always re-sort retrieved chunks by document position (start_line) before sending to the LLM. Include temporal metadata in the prompt.
**Warning signs:** Events extracted from retrieval-based calls have more date resolution errors than full-context calls.

### Pitfall 4: Embedding Model Drift
**What goes wrong:** Embedding model updates change similarity scores, causing previously-working retrieval queries to miss passages.
**Why it happens:** Embedding models are versioned; API updates can change behavior.
**How to avoid:** Pin embedding model versions. Re-index when upgrading. Include embedding model version in index metadata.
**Warning signs:** Retrieval quality degrades after an API update you didn't trigger.

### Pitfall 5: BM25 Dominance in Legal Text
**What goes wrong:** Dense embeddings add little value over BM25 for SEC filings because legal text uses consistent, specific terminology (not paraphrasing).
**Why it happens:** SEC filings are formulaic. "The Special Committee met" is always "The Special Committee met," never "the board subgroup convened."
**How to avoid:** Test BM25-only retrieval before adding dense embeddings. If BM25 alone achieves >90% of hybrid performance, skip the embedding cost.
**Warning signs:** Hybrid search results are dominated by BM25 matches, with dense embeddings adding few new results.

---

## Architecture Patterns for Option D Implementation

### Recovery Stage Design

```python
# Conceptual architecture -- NOT implementation code

class RecoveryStage:
    """Targeted retrieval-based recovery for coverage gaps."""

    def __init__(self, deal_slug: str, index: ChromaCollection):
        self.deal_slug = deal_slug
        self.index = index

    def recover(
        self,
        coverage_findings: list[CoverageFinding],
        existing_events: list[CanonicalEvent],
    ) -> list[RecoveredEvent]:
        recovered = []
        for finding in coverage_findings:
            if finding.severity != "error":
                continue
            queries = self._finding_to_queries(finding)
            chunks = self._retrieve_chunks(queries, k=10)
            chunks = self._sort_chronologically(chunks)
            new_events = self._extract_from_chunks(chunks, finding)
            recovered.extend(new_events)
        return recovered

    def _finding_to_queries(self, finding):
        """Generate retrieval queries from a coverage finding."""
        ...

    def _retrieve_chunks(self, queries, k):
        """Hybrid BM25 + dense retrieval, deduplicated."""
        ...

    def _extract_from_chunks(self, chunks, finding):
        """Focused LLM call to extract specific event type."""
        ...
```

### Index Build Step

```python
# One-time per deal, after preprocess-source

def build_recovery_index(deal_slug: str) -> ChromaCollection:
    """Build a hybrid search index from chronology blocks."""
    blocks = load_chronology_blocks(deal_slug)
    chunks = group_blocks(blocks, target_size=5)

    client = chromadb.PersistentClient(
        path=f"data/skill/{deal_slug}/index"
    )
    collection = client.get_or_create_collection(
        name="chronology",
        metadata={"embedding_model": "voyage-3-large"}
    )

    # Embed and store
    for chunk in chunks:
        embedding = voyage_client.embed(
            [chunk.text],
            model="voyage-3-large",
        ).embeddings[0]

        collection.add(
            ids=[chunk.chunk_id],
            embeddings=[embedding],
            documents=[chunk.text],
            metadatas=[chunk.metadata],
        )

    return collection
```

### Pipeline Integration Point

```
skill-pipeline preprocess-source --deal <slug>
  |
  v
[NEW] skill-pipeline build-index --deal <slug>  (optional, only if recovery enabled)
  |
  v
/extract-deal <slug>
  |
  v
skill-pipeline canonicalize -> check -> verify -> coverage
  |
  v
[NEW] skill-pipeline recover --deal <slug>  (only if coverage has error-level gaps)
  |
  v
skill-pipeline canonicalize -> check -> verify -> coverage  (re-run on merged artifacts)
  |
  v
skill-pipeline enrich-core -> export-csv
```

---

## Open Questions

1. **Does BM25-only retrieval perform as well as hybrid for SEC filings?**
   - What we know: Legal text uses consistent terminology, which favors keyword search.
   - What's unclear: Whether semantic retrieval adds meaningful recall for edge cases (paraphrased events, implicit references).
   - Recommendation: Test BM25-only first. Add dense embeddings only if coverage improvement is measurable.

2. **What is the optimal chunk size for embedding chronology blocks?**
   - What we know: Individual blocks (50-300 tokens) are too small for quality embeddings. The contextual retrieval technique (prepending context) helps.
   - What's unclear: Whether 3-block or 5-block or 10-block groups produce better retrieval.
   - Recommendation: Start with 5-block groups (~500-1000 tokens). Evaluate on a held-out deal.

3. **Should the recovery index include evidence items as separate entries?**
   - What we know: Evidence items contain pre-identified dates, amounts, and process signals. They could be embedded alongside chronology chunks.
   - What's unclear: Whether this improves recovery precision or just adds noise.
   - Recommendation: Start with chronology chunks only. Add evidence items to the index only if retrieval precision is insufficient.

4. **Is the recovery stage worth the complexity for the current 9 deals?**
   - What we know: The prior research (CONTEXT_AND_ATTENTION.md) identifies prompt ordering, extended thinking, and evidence anchoring as higher-ROI improvements that don't require any new infrastructure.
   - What's unclear: Whether implementing those improvements first makes the recovery stage unnecessary.
   - Recommendation: Implement context management improvements (Batch 1+2 from CONTEXT_AND_ATTENTION.md) BEFORE building the retrieval recovery stage. Measure coverage improvement. Only add retrieval recovery if coverage gaps persist.

---

## State of the Art

| Old Approach (2023) | Current Approach (2025-2026) | Impact |
|---------------------|------------------------------|--------|
| Simple top-K retrieval | Hybrid BM25 + dense + reranking | 15-30% recall improvement |
| Generic embeddings | Domain-specific (Voyage finance) | 40% accuracy improvement on SEC data |
| Flat chunk embedding | Contextual retrieval (prepend context) | 67% fewer retrieval failures |
| Single-vector (DPR) | Multi-vector (ColBERT) or Matryoshka | Better token-level precision |
| Static RAG pipeline | Agentic/Self-RAG with iterative retrieval | Self-correcting retrieval |
| RAG everywhere | Long-context LLMs reducing RAG need | 1M context windows fit most documents |
| Separate embedding + BM25 | ChromaDB/LanceDB native hybrid search | Single-system hybrid retrieval |

**The biggest shift:** 1M-token context windows (Claude Sonnet 4.6, Gemini) mean most individual documents fit in context without retrieval. RAG's primary value is shifting from "can't fit in context" to "cross-document search" and "targeted precision."

---

## Sources

### Primary (HIGH confidence)
- [Anthropic Pricing](https://platform.claude.com/docs/en/about-claude/pricing) -- verified Claude Sonnet 4.6 at $3/$15 per MTok, 1M context at standard pricing
- [Anthropic Contextual Retrieval (2024)](https://www.anthropic.com/news/contextual-retrieval) -- 67% retrieval failure reduction with contextual embeddings + BM25
- [Anthropic Context Windows](https://platform.claude.com/docs/en/build-with-claude/context-windows) -- Claude Sonnet 4.6 1M context GA
- [Liu et al., "Lost in the Middle" (2023), TACL 2024](https://arxiv.org/abs/2307.03172) -- U-shaped attention curve, foundational for understanding context management
- [Long Context vs. RAG for LLMs: An Evaluation and Revisits (2025)](https://arxiv.org/abs/2501.01880) -- systematic comparison showing long-context outperforms RAG for single-document tasks

### Secondary (MEDIUM confidence)
- [Voyage finance-2 blog](https://blog.voyageai.com/2024/06/03/domain-specific-embeddings-finance-edition-voyage-finance-2/) -- 54% accuracy on SEC data vs 38.5% for OpenAI
- [Voyage 3-large blog](https://blog.voyageai.com/2025/01/07/voyage-3-large/) -- outperforms finance-2 on general benchmarks including financial domains
- [RAG vs GraphRAG Systematic Evaluation (2025)](https://arxiv.org/abs/2502.11371) -- GraphRAG's 4-8x indexing cost, 30-60% latency increase
- [Best Embedding Models for Financial RAG (2025)](https://deeprightai.substack.com/p/best-embedding-models-for-financial) -- comparative benchmarks on SEC filing data
- [Agentic RAG Survey (2025)](https://arxiv.org/abs/2501.09136) -- comprehensive survey of agentic retrieval patterns
- [ChromaDB sparse vector search](https://www.trychroma.com/project/sparse-vector-search) -- BM25 + SPLADE support in ChromaDB
- [RAPTOR (ICLR 2024)](https://arxiv.org/abs/2401.18059) -- tree-based hierarchical retrieval
- [Self-RAG (ICLR 2024)](https://selfrag.github.io/) -- model-directed retrieval decisions

### Tertiary (LOW confidence)
- [RAG is DEAD (Medium)](https://medium.com/@reliabledataengineering/rag-is-dead-and-why-thats-the-best-news-you-ll-hear-all-year-0f3de8c44604) -- provocative but captures the long-context vs RAG tension
- [Fin-RATE SEC Filing Benchmark (2025)](https://arxiv.org/html/2602.07294) -- financial analytics benchmark on SEC filings
- [From RAG to Context: 2025 Year-End Review](https://ragflow.io/blog/rag-review-2025-from-rag-to-context) -- industry trends overview

---

## Metadata

**Confidence breakdown:**
- Core assessment (RAG not the right primary architecture): HIGH -- supported by published research on long-context vs RAG, verified document sizes, and first-principles analysis of the completeness problem
- Embedding model recommendations: MEDIUM -- based on published benchmarks, not tested on this pipeline's specific data
- Architecture options: HIGH for Option D recommendation, MEDIUM for cost estimates
- Technology stack: MEDIUM -- component recommendations are sound but version/API specifics may change
- Cost estimates: LOW-MEDIUM -- order-of-magnitude correct, actual costs depend on deal complexity and LLM output length

**Research date:** 2026-03-26
**Valid until:** 2026-06-26 (3 months; embedding model recommendations may shift faster as new models release)
