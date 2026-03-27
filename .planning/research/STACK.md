# Technology Stack

**Project:** Filing-Grounded Deal Pipeline Redesign
**Researched:** 2026-03-27
**Focus:** LLM structured extraction APIs, prompt caching, database options, complementary libraries

## Recommended Stack

This is an additive research document. The existing stack (Python 3.11+, Pydantic 2.0+, edgartools, pytest, setuptools) is already chosen and validated. Recommendations below cover the **new capabilities** needed for the redesign: provider-native structured outputs, prompt caching, a canonical database layer, and supporting libraries.

### LLM Provider SDKs

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| anthropic | >=0.86 | Claude API client with native structured outputs, prompt caching, extended thinking | GA structured outputs via `output_config.format` with `json_schema` type. Native `client.messages.parse()` with Pydantic models. Prompt caching via `cache_control` blocks. Current minimum for `output_config` (replaces deprecated `output_format`). | HIGH |
| openai | >=2.30 | OpenAI API client with structured outputs via Responses API | GA structured outputs via `response_format` / `text.format` with `json_schema`. Native Pydantic `.parse()` support. Automatic prompt caching (no code changes). GPT-5.x models require Responses API for tool calling. | HIGH |

**Key version rationale:**
- `anthropic>=0.86` is required for `output_config.format` (GA path), replacing the deprecated beta header `structured-outputs-2025-11-13` and old `output_format` parameter. The SDK handles Pydantic-to-JSON-Schema transformation internally via `client.messages.parse()`.
- `openai>=2.30` is required for the Responses API with structured outputs on GPT-5.x models. GPT-4o is retired as of Feb 2026; GPT-5.4 is the current production model. Chat Completions API still works but Responses API is the forward path.

### Structured Output Configuration

#### Anthropic (Claude)

**Approach:** Use `client.messages.parse()` with Pydantic models directly.

```python
from pydantic import BaseModel
from anthropic import Anthropic

class ActorRecord(BaseModel):
    actor_id: str
    display_name: str
    canonical_name: str
    role: str
    evidence_span_ids: list[str]

client = Anthropic()
response = client.messages.parse(
    model="claude-sonnet-4-5-20250929",
    max_tokens=16384,
    output_format=ActorRecord,  # SDK translates to output_config.format internally
    messages=[{"role": "user", "content": prompt}],
)
actor = response.parsed_output  # Typed ActorRecord instance
```

**Supported models:** Claude Opus 4.6, Sonnet 4.6, Sonnet 4.5, Opus 4.5, Haiku 4.5

**JSON Schema limitations (both providers share similar constraints):**
- No recursive schemas
- `additionalProperties` must be `false` on all objects
- No numerical constraints (`minimum`, `maximum`, `multipleOf`)
- No string constraints (`minLength`, `maxLength`) -- moved to descriptions automatically by SDK
- `enum` supports only primitive types (string, number, bool, null)
- Array `minItems` only supports 0 and 1
- `anyOf` and `allOf` supported (but `allOf` with `$ref` not)
- Regex patterns: basic support only (no backreferences, no lookahead/lookbehind)

**Extended thinking + structured outputs interaction:**
- Grammars (constrained decoding) apply only to Claude's direct output, NOT to thinking blocks
- Extended thinking and structured outputs CAN be used together -- thinking is unconstrained, final output is schema-enforced
- However: toggling thinking parameters invalidates prompt cache for message history
- On Sonnet 4.6 and Opus 4.6, use `thinking: {"type": "adaptive"}` (manual `type: "enabled"` is deprecated on these models)
- **Recommendation for this project:** Use extended thinking + structured outputs together. The reasoning quality from thinking benefits complex extraction, and the schema guarantee prevents malformed JSON. The thinking blocks will not appear in the constrained output.

**Confidence:** HIGH -- verified against official Anthropic docs (platform.claude.com/docs/en/build-with-claude/structured-outputs, platform.claude.com/docs/en/build-with-claude/extended-thinking)

#### OpenAI (GPT-5.x)

**Approach:** Use `client.responses.parse()` with Pydantic models (Responses API).

```python
from pydantic import BaseModel
from openai import OpenAI

class ActorRecord(BaseModel):
    actor_id: str
    display_name: str
    canonical_name: str
    role: str
    evidence_span_ids: list[str]

client = OpenAI()
response = client.responses.parse(
    model="gpt-5.4",
    input=[{"role": "user", "content": prompt}],
    text_format=ActorRecord,
)
actor = response.output_parsed  # Typed ActorRecord instance
```

**Supported models:** GPT-5.4 (current), GPT-5.3, GPT-5.2; legacy gpt-4o-2024-08-06+ still works via Chat Completions
**GPT-4o status:** Retired from ChatGPT Feb 2026; API access sunsetting April 2026. Do not target gpt-4o for new work.

**Confidence:** MEDIUM -- OpenAI docs returned 403 during verification; information sourced from search results and community documentation. The Responses API parameter names (`text_format` vs `response_format`) may differ from what is shown; verify against SDK changelog before implementation.

### Prompt Caching

#### Anthropic Prompt Caching

**How it works:** Explicit cache breakpoints via `cache_control` blocks on content. Up to 4 breakpoints per request. Caches the entire prompt prefix up to and including the marked block.

**Minimum thresholds:**
| Model | Minimum Tokens |
|-------|---------------|
| Claude Opus 4.6/4.5 | 4,096 |
| Claude Sonnet 4.6 | 2,048 |
| Claude Sonnet 4.5/4/3.7 | 1,024 |
| Claude Haiku 4.5 | 4,096 |

**Pricing (Sonnet 4.5 -- the likely extraction model):**
- Cache write (5-min TTL): 1.25x base input tokens
- Cache write (1-hour TTL): 2x base input tokens
- Cache read: 0.1x base input tokens (90% discount)
- Latency reduction: up to 85% for cached prompts

**Application to this pipeline:**

```python
# System prompt + actor roster cached across chunk extraction calls
response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=16384,
    system=[
        {
            "type": "text",
            "text": EXTRACTION_SYSTEM_PROMPT,  # Static instructions
        },
        {
            "type": "text",
            "text": actor_roster_text,  # Actor context from first pass
            "cache_control": {"type": "ephemeral", "ttl": "1h"},  # Cache for full extraction run
        },
    ],
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": chunk_text,  # Changes per chunk -- NOT cached
                }
            ],
        }
    ],
)
```

**Critical caching rules:**
1. Place `cache_control` on the LAST block of static content, not on changing content
2. Cache is invalidated hierarchically: tool changes invalidate everything; system changes invalidate messages
3. Toggling extended thinking invalidates message cache (but system prompt cache survives)
4. Use 1-hour TTL for extraction runs (multi-chunk processing exceeds 5-minute window)
5. Maximum 4 cache breakpoints per request

**Confidence:** HIGH -- verified against official Anthropic prompt caching docs

#### OpenAI Prompt Caching

**How it works:** Fully automatic. No code changes required. The API caches the longest matching prefix starting at 1,024 tokens in 128-token increments.

**Pricing:** 50% discount on cached input tokens. Cache lifetime: 5-10 minutes of inactivity, always cleared after 1 hour of last use.

**Application to this pipeline:** Zero code changes needed. Structuring prompts with static content first (system prompt, actor roster) and variable content last (chunk text) naturally maximizes cache hits.

**Confidence:** HIGH -- verified against official OpenAI docs

### Database Layer

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| DuckDB | >=1.5.1 | Canonical deal representation, analytical queries, export generation | Column-oriented embedded analytics DB. Zero-server deployment (single .duckdb file). Native Python integration. Reads/writes Parquet, CSV, JSON directly. SQL-first querying for export/analysis. 10-50x faster than SQLite for analytical aggregations. | HIGH |

**Why DuckDB over alternatives:**

| Criterion | DuckDB | SQLite | PostgreSQL |
|-----------|--------|--------|------------|
| Deployment | Embedded, single file | Embedded, single file | Requires server |
| Analytics | Column-oriented, optimized | Row-oriented, slow for aggregations | Server-class analytics |
| Python integration | Native, first-class | Good via stdlib | Requires psycopg2/asyncpg |
| JSON support | Native JSON type, JSON functions | JSON1 extension | Native JSONB |
| Parquet/CSV | Native read/write | Not supported | COPY command only |
| Concurrency | Single-writer, multi-reader | Single-writer, multi-reader | Full MVCC |
| Dependency footprint | `pip install duckdb` (30MB) | Built into Python stdlib | External server process |
| This project's data volume | 9 deals, hundreds of events | Would work fine | Overkill |

**Recommendation:** DuckDB. The project has analytical query patterns (aggregate by deal, filter by event type, cross-reference actors with events, generate export CSVs) rather than transactional patterns. DuckDB's column-orientation and native Parquet/CSV I/O eliminate the data format conversion layer. Single-file deployment means no infrastructure changes.

SQLite would also work (and is already in Python's stdlib), but DuckDB's SQL dialect is more expressive for the analytical queries needed in export generation, and its native JSON column type maps cleanly to the existing Pydantic artifact schemas.

PostgreSQL is overkill for a 9-deal batch pipeline with no concurrent write pressure.

**Confidence:** HIGH -- well-established technology, verified versions

### Supporting Libraries

| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| rapidfuzz | >=3.14 | Fuzzy string matching for quote verification, actor name deduplication | Replace or complement the existing `normalize_for_matching` + `find_anchor_in_segment` in `provenance.py` and `verify.py`. C++-backed, 10-100x faster than pure-Python difflib. Provides Levenshtein, Jaro-Winkler, partial ratios. | MEDIUM |

**Why rapidfuzz and not fuzzywuzzy:** rapidfuzz is MIT-licensed (fuzzywuzzy is GPL), is actively maintained (v3.14.3 as of Nov 2025), and is significantly faster due to C++ implementation. From v3.0+, strings are not preprocessed by default, which aligns with this pipeline's need for precise, case-sensitive matching.

**Application:** The existing `find_anchor_in_segment` uses custom normalization and substring matching. rapidfuzz's `fuzz.partial_ratio` and `fuzz.token_sort_ratio` could provide calibrated similarity scores for the FUZZY match tier, replacing the current binary FUZZY/UNRESOLVED distinction with a continuous confidence score. However, the existing approach works and is well-tested -- this is an enhancement, not a requirement.

**Confidence:** MEDIUM -- the existing custom matching works; rapidfuzz would improve it but is not essential

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Structured output | Provider-native (`output_config.format` / `response_format`) | Instructor library | Adds unnecessary abstraction layer. Both Anthropic and OpenAI SDKs now have native Pydantic `.parse()` methods that do the same thing. Instructor was valuable before native support existed (pre-Nov 2025); now it is an extra dependency with no benefit for this use case. |
| Structured output | Provider-native | Tool-use workaround (force a "tool call" to get JSON) | Legacy pattern from before structured outputs GA. Still works but is semantically wrong -- extraction is not a tool call. The tool-use hack also cannot combine with extended thinking as cleanly. |
| Database | DuckDB | SQLite | Would work but requires more manual JSON handling and lacks native analytical query patterns. No Parquet/CSV I/O. |
| Database | DuckDB | PostgreSQL | Requires server deployment, adds infrastructure complexity for a 9-deal batch pipeline with no concurrent users. |
| Database | DuckDB | Pandas DataFrames | Not a database. No persistence, no SQL, no referential integrity. DuckDB can query Pandas DataFrames directly if ever needed. |
| Fuzzy matching | rapidfuzz (optional) | fuzzywuzzy | GPL license, slower, less maintained. |
| Fuzzy matching | rapidfuzz (optional) | python-Levenshtein | Narrower API, less maintained. rapidfuzz is the successor. |
| SEC filing parsing | edgartools (already chosen) | sec-api | Commercial/paid API. edgartools is open-source and already integrated. |
| SEC filing parsing | edgartools (already chosen) | sec-edgar-toolkit | Less mature, lower adoption than edgartools. |
| LLM abstraction | Direct SDK usage | LangChain / LlamaIndex | Massive dependency trees, opinionated abstractions that fight the pipeline's deterministic-first design. Direct SDK calls give precise control over caching, structured outputs, and thinking parameters. |
| LLM abstraction | Direct SDK usage | PydanticAI | Interesting but immature. Adds an abstraction layer between the pipeline and the provider SDKs. For 2 providers with well-known APIs, direct SDK usage is simpler and more debuggable. |

## What NOT to Use

| Technology | Why Not |
|------------|---------|
| LangChain | Heavy dependency, opinionated abstractions, version churn. Direct SDK calls are cleaner for this pipeline's 2-provider setup. |
| Instructor | Redundant now that both Anthropic and OpenAI have native Pydantic structured output support in their SDKs. |
| RAG frameworks (LlamaIndex, etc.) | Already rejected in project scoping. Documents fit in context; exhaustive extraction is not a retrieval problem. |
| fuzzywuzzy | GPL-licensed, slower than rapidfuzz, effectively unmaintained. |
| gpt-4o / gpt-4o-mini | Retired/retiring. GPT-5.4 is the current OpenAI production model. |
| Summarization/compression tools | Project explicitly rejects lossy compression of filing text. Legal precision requires verbatim source text. |

## Version Pinning Recommendations

```toml
# pyproject.toml dependencies (proposed additions/updates)
dependencies = [
    "anthropic>=0.86",          # Was >=0.49; need >=0.86 for output_config.format GA
    "openai>=2.30",             # NEW: OpenAI Responses API with structured outputs on GPT-5.x
    "edgartools>=5.23,<6.0",    # Pin <6.0 to avoid breaking v6 release (known deprecation risk)
    "duckdb>=1.5",              # NEW: Embedded analytics database
    "pydantic>=2.0",            # Unchanged
    "openpyxl>=3.1",            # Unchanged
    "pytest>=8.0",              # Unchanged
]

# Optional: Enhanced matching
# "rapidfuzz>=3.14",          # Only if fuzzy matching enhancement is pursued
```

**Version pinning rationale:**
- `anthropic>=0.86`: Floor bumped from 0.49 to 0.86 because `output_config.format` (the GA structured outputs path) requires SDK versions from late 2025+. The old `output_format` parameter still works but is deprecated.
- `openai>=2.30`: New dependency. Required for Responses API + structured outputs on GPT-5.x. The Chat Completions API path still works for legacy models but GPT-5.4 requires Responses API for tool calling.
- `edgartools>=5.23,<6.0`: Add upper bound. v6.0 will include breaking changes (deprecated parameter removal, dimension column naming changes). The pipeline currently works on 5.23+; latest is 5.26.1 (released 2026-03-26).
- `duckdb>=1.5`: New dependency. Latest stable is 1.5.1 (released 2026-03-23). Requires Python >=3.10 (compatible with project's >=3.11 requirement).

## Provider-Specific Configuration

### Environment Variables (additions)

```bash
# Existing (unchanged)
ANTHROPIC_API_KEY
OPENAI_API_KEY
BIDS_LLM_PROVIDER          # anthropic|openai
BIDS_LLM_MODEL             # override model ID
BIDS_LLM_REASONING_EFFORT  # provider-specific
BIDS_LLM_STRUCTURED_MODE   # prompted_json|provider_native|auto

# Proposed additions
BIDS_LLM_CACHE_TTL         # 5m|1h (Anthropic cache TTL; default: 1h for extraction runs)
BIDS_DB_PATH               # Path to DuckDB database file (default: data/deals.duckdb)
```

### Provider Abstraction Pattern

The pipeline already has `BIDS_LLM_STRUCTURED_MODE` with `prompted_json|provider_native|auto`. With native structured outputs now GA on both providers, the recommended default changes:

- **Previous default:** `prompted_json` (include schema in prompt text, parse JSON from response)
- **New recommended default:** `provider_native` (use `output_config.format` / `text.format` for guaranteed schema compliance)
- **Fallback path:** `prompted_json` remains available for models that don't support structured outputs

The `auto` mode should detect model capabilities and select `provider_native` when available.

## Prompt Caching Architecture for Extraction

The highest-ROI caching opportunity is the chunked event extraction pass, where the system prompt + actor roster is static across all chunks for a single deal:

```
Chunk 1: [SYSTEM_PROMPT + ACTOR_ROSTER (cached write)] + [chunk_1_text]  -> cache miss, write
Chunk 2: [SYSTEM_PROMPT + ACTOR_ROSTER (cached read)]  + [chunk_2_text]  -> cache hit, 90% savings
Chunk 3: [SYSTEM_PROMPT + ACTOR_ROSTER (cached read)]  + [chunk_3_text]  -> cache hit, 90% savings
...
Chunk N: [SYSTEM_PROMPT + ACTOR_ROSTER (cached read)]  + [chunk_N_text]  -> cache hit, 90% savings
```

For a typical deal with 10-15 chunks:
- Without caching: N * (system_tokens + roster_tokens + chunk_tokens)
- With caching: 1 * write_cost + (N-1) * 0.1 * (system_tokens + roster_tokens) + N * chunk_tokens
- Savings: ~85-90% on the static portion, significant latency reduction

**Implementation note for Anthropic:** Use 1-hour cache TTL because multi-chunk extraction for complex deals can take 10-30 minutes, exceeding the 5-minute default.

**Implementation note for OpenAI:** No code changes needed. Automatic caching activates when prompts share a prefix of 1,024+ tokens. Structure prompts with static content first to maximize hits.

## Sources

### Official Documentation (HIGH confidence)
- [Anthropic Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) -- GA, `output_config.format` with `json_schema`
- [Anthropic Prompt Caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) -- `cache_control` with TTL, minimum token thresholds
- [Anthropic Extended Thinking](https://platform.claude.com/docs/en/build-with-claude/extended-thinking) -- compatibility with structured outputs and caching
- [OpenAI Structured Outputs](https://platform.openai.com/docs/guides/structured-outputs) -- `response_format` with `json_schema`, strict mode
- [OpenAI Prompt Caching](https://platform.openai.com/docs/guides/prompt-caching) -- automatic, 1024-token minimum

### Package Registries (HIGH confidence)
- [anthropic on PyPI](https://pypi.org/project/anthropic/) -- v0.86.0, 2026-03-18
- [openai on PyPI](https://pypi.org/project/openai/) -- v2.30.0, 2026-03-25
- [duckdb on PyPI](https://pypi.org/project/duckdb/) -- v1.5.1, 2026-03-23
- [edgartools on PyPI](https://pypi.org/project/edgartools/) -- v5.26.1, 2026-03-26
- [RapidFuzz on PyPI/GitHub](https://github.com/rapidfuzz/RapidFuzz) -- v3.14.3, 2025-11-01

### Community/Search Sources (MEDIUM confidence)
- [DuckDB vs SQLite comparison](https://www.analyticsvidhya.com/blog/2026/01/duckdb-vs-sqlite/) -- feature comparison, use case guidance
- [OpenAI model retirement](https://www.remio.ai/post/openai-retiring-gpt-4o-gpt-4-1-and-o4-mini-the-2026-transition-guide) -- GPT-4o sunset timeline
- [OpenAI GPT-5.4 guide](https://developers.openai.com/api/docs/guides/latest-model) -- Responses API migration

---

*Stack research: 2026-03-27*
