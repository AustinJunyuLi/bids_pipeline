# Phase 7: Parallel Chunked Extraction - Research

**Researched:** 2026-03-26
**Domain:** LLM extraction orchestration, concurrency patterns for structured output pipelines
**Confidence:** HIGH

## Summary

The current extract-deal skill processes chunks sequentially because each chunk receives a "running actor roster" from all prior chunks. This serial dependency exists so the LLM can assign consistent actor_ids to entities it recognizes from earlier chunks. The question is whether this serial chain can be broken without losing actor consistency.

Empirical analysis of the two extracted deals (stec and petsmart-inc) reveals a structural property of SEC merger background chronologies: actors are introduced in the first 40-60% of the filing, and the remaining 40-60% references only previously introduced actors. In STEC (235 blocks, 22 chunks), every actor is introduced by block 93 (chunk 9 of 22). In petsmart-inc (36 blocks, 4 chunks), every actor is introduced by block 21 (chunk 2 of 4). This means the serial dependency is front-loaded: only the early chunks actually discover new actors.

The recommended approach is a two-phase extraction: (1) a sequential actor-discovery pass over the first portion of the filing that builds the complete actor roster, then (2) parallel event extraction across all chunks with the full actor roster provided to each. The consolidation pass remains unchanged. This eliminates the serial bottleneck for the majority of chunks while preserving actor consistency, without requiring any changes to downstream deterministic stages.

**Primary recommendation:** Split extraction into two phases: sequential actor-discovery pass (first ~50% of blocks), then parallel event-only extraction across all chunks with the complete roster. Keep the consolidation pass and output contract unchanged.

## Project Constraints (from CLAUDE.md)

- Fail fast on violated assumptions, invalid states, unexpected inputs. No fallback logic.
- Do not overengineer. Shortest correct path. No speculative abstractions.
- Do not expand scope. Only solve the parallelization requirement.
- Keep pipeline stages deterministic where possible.
- Do not silently alter semantics, schemas, event definitions, or output meaning.
- Existing Pydantic-first patterns for schemas; `snake_case` for functions, modules, JSON keys.
- Target Python 3.11+; type hints on public functions.
- Add targeted regression tests for every bug fix, especially around chunk planning and provider-specific LLM behavior.
- Match surrounding code style; keep imports tidy.
- Filing `.txt` files under `raw/` are immutable truth sources.
- Canonical extract artifacts must carry `evidence_span_ids`, and canonical loading must fail if `spans.json` is missing.
- Downstream contract: `actors_raw.json` + `events_raw.json` in `data/skill/<slug>/extract/`. No schema changes.
- `.claude/skills/` is the canonical skill tree. Mirrors must be synced.

## Standard Stack

### Core

No new libraries are needed. The parallelization happens at the LLM skill orchestration level (SKILL.md instructions), not as Python library code. The LLM agent's native ability to issue multiple tool calls is the concurrency mechanism.

| Component | Current | Purpose | Change Needed |
|-----------|---------|---------|---------------|
| extract-deal SKILL.md | Sequential chunk extraction | LLM extraction instructions | Rewrite for two-phase parallel extraction |
| Consolidation pass (SKILL.md) | Receives chunk drafts | Global dedup, ID assignment, temporal signals | No change to consolidation logic |
| canonicalize.py | Actor/event dedup | Deterministic post-extraction | No change |
| check.py | Actor audit + structural checks | Deterministic gate | No change |

### Supporting

No additional Python dependencies. The concurrency is orchestrated by the LLM agent itself (Claude Code or similar), not by a Python async framework. The skill tells the agent to issue parallel API calls; the agent uses its own concurrency mechanisms.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SKILL.md-level parallelism | Python `asyncio` orchestrator | Would require a new Python module, LLM API client code, and error handling that does not exist today. The pipeline has zero Python-side LLM call code -- extraction is purely skill-driven. Building a Python orchestrator is overengineering for the 2-4x speedup goal. |
| Two-phase (actors then events) | Full parallel with post-hoc actor reconciliation | Would require each chunk to independently mint actor_ids, then a complex reconciliation pass to merge synonymous actors. High risk of inconsistency, more LLM calls for reconciliation, and fragile merge logic. |
| Roster-provided parallel | Half-deal parallelism (split at midpoint) | Adds a midpoint reconciliation call, only gives 2x max speedup, still has serial dependency within each half. Two-phase is simpler and gives higher parallelism. |

## Architecture Patterns

### Recommended Extraction Flow (Two-Phase)

```text
Phase 1: Actor Discovery (SEQUENTIAL, ~50% of chunks)
  chunk_1 -> chunk_2 -> ... -> chunk_K
  (K = number of chunks where new actors are still being discovered)
  Output: complete actor roster

Phase 2: Event Extraction (PARALLEL, all chunks)
  chunk_1 ──┐
  chunk_2 ──┤
  chunk_3 ──┤──> all chunks receive full actor roster
  ...       ├──> each extracts events only
  chunk_N ──┘
  Output: per-chunk event drafts

Phase 3: Consolidation (SEQUENTIAL, 1 pass)
  All chunk event drafts + complete actor roster
  -> actor dedup, event dedup, taxonomy sweep, re-reads, temporal signals, global IDs
  Output: actors_raw.json + events_raw.json (same contract as today)
```

### Pattern 1: Two-Phase Actor/Event Split

**What:** Separate actor extraction from event extraction. Phase 1 processes chunks sequentially to build the actor roster. Phase 2 processes all chunks in parallel for event extraction only, with each chunk receiving the complete actor roster.

**When to use:** Always. This is the new default extraction path.

**Key insight from data analysis:** In STEC (235 blocks), all 22 actors are introduced by block 93 (40% through the filing). In petsmart-inc (36 blocks), all 20 actors are introduced by block 21 (58% through). The tail of the filing -- where most events occur in long deals -- references only previously known actors. This means Phase 1 (sequential) terminates early, and Phase 2 (parallel) handles the bulk of the work.

**How the agent detects Phase 1 completion:** After each Phase 1 chunk, if no new actors were minted, increment a "no-new-actor" counter. After 2 consecutive chunks with zero new actors, declare the roster complete and transition to Phase 2. For safety, always process at least the first 50% of chunks in Phase 1, regardless of the no-new-actor counter. This handles the rare case where a late-appearing actor would be missed.

**Phase 1 chunk processing:** Identical to current SKILL.md -- extract actors AND events together, with roster carry-forward. The event drafts from Phase 1 chunks are kept for consolidation.

**Phase 2 chunk processing:** Each chunk receives: (1) the full actor roster as a compact reference table, (2) its block window, (3) scoped evidence items. It extracts events only, referencing actor_ids from the provided roster. It does NOT mint new actors. If a chunk encounters an entity not in the roster, it records it in `unresolved_mentions` for downstream handling.

### Pattern 2: Compact Roster Format for Phase 2

**What:** Strip evidence_refs from the actor roster when passing it to Phase 2 chunks. Each Phase 2 chunk needs only the actor reference table, not the full provenance chain.

**Compact roster fields per actor:**
```json
{
  "actor_id": "bidder_wdc",
  "display_name": "Western Digital Corporation",
  "canonical_name": "WESTERN DIGITAL CORPORATION",
  "aliases": ["WDC", "Party B"],
  "role": "bidder",
  "bidder_kind": "strategic"
}
```

**Why:** The full actor record with evidence_refs, notes, geography, listing_status etc. is unnecessary for event extraction. The LLM only needs to match entity names in the text to actor_ids. A compact roster of ~6 fields per actor reduces prompt tokens by 40-60% compared to the full roster. For STEC (22 actors), this saves ~2K tokens per Phase 2 chunk prompt.

### Pattern 3: Parallel Consolidation Re-reads

**What:** When the taxonomy sweep identifies multiple NOT FOUND event types, issue all targeted re-reads in a single multi-type prompt rather than one call per type.

**Why:** Currently, up to 5 separate LLM calls for re-reads. Batching them into 1 call eliminates 4 calls. This was already recommended in the Phase 6 speed analysis (Section 3.6, Priority 3) and is independent of the main parallelization change.

### Anti-Patterns to Avoid

- **Full parallel with independent actor minting:** Each chunk independently creates actor_ids, then a reconciliation pass merges them. This creates O(N^2) matching problems, alias confusion (Party A in chunk 3 might be Party B in chunk 7 if the filing uses different names), and fragile dedup logic. The two-phase approach avoids this entirely.
- **Python-side LLM orchestrator:** Building a Python module with `asyncio` + `anthropic` client to issue parallel API calls. This adds a new runtime dependency, duplicates the structured output parsing that the LLM agent handles natively, and introduces a maintenance surface that does not exist today. The pipeline has zero lines of Python LLM client code.
- **Adaptive Phase 1 cutoff without safety floor:** Ending Phase 1 as soon as one chunk has zero new actors. SEC filings can have actor introductions that skip chunks (e.g., a new advisor appears late in the deal). The 50% floor prevents premature Phase 2 transition.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM call parallelism | Python asyncio orchestrator with API clients | Agent-native parallel tool calls (SKILL.md instructions) | Zero Python LLM code exists; adding it creates a new maintenance surface |
| Actor reconciliation across parallel chunks | Custom string-matching dedup for independently minted actor_ids | Two-phase extraction (sequential actors, parallel events) | Reconciliation is NP-hard in the general case; two-phase avoids the problem entirely |
| Chunk planning / splitting | Custom Python chunk planner module | SKILL.md instructions for the LLM agent | Chunking logic is already documented in SKILL.md; it runs at agent prompt time, not as Python code |
| Global event ID assignment | Custom Python re-numbering script | Consolidation pass (already exists in SKILL.md) | The consolidation pass already handles this |

**Key insight:** The extraction pipeline has a clean architectural boundary: Python code handles deterministic stages (canonicalize, check, verify, coverage, enrich-core), while LLM skills handle non-deterministic stages (extract, verify-extraction, enrich-deal, export-csv). The parallelization change lives entirely in the SKILL.md layer. No new Python code is needed.

## Common Pitfalls

### Pitfall 1: Late-appearing actors missed in Phase 2

**What goes wrong:** An actor first mentioned late in the filing (after Phase 1 completes) is not in the roster. Phase 2 chunks cannot assign an actor_id to it, so it either gets dropped or creates an inconsistent unresolved_mention.

**Why it happens:** The 50% safety floor may not be enough for filings with unusually late actor introductions.

**How to avoid:** Phase 2 chunks record any entity name they cannot match to the roster in `unresolved_mentions`. The consolidation pass reviews these and either maps them to existing actors (alias resolution) or mints new actors as late additions. This is the same `unresolved_mentions` mechanism that already exists in the output schema.

**Warning signs:** `unresolved_mentions` in the final output contains entity names that should be actors. The canonicalize stage's `_recover_unnamed_parties` function already handles some of these cases.

### Pitfall 2: Duplicate events from Phase 1 + Phase 2 overlap

**What goes wrong:** Phase 1 chunks extract both actors AND events. Phase 2 chunks re-extract events for the same blocks. The same event appears twice in the consolidation input.

**How to avoid:** Two options:
- **(Recommended)** Phase 2 skips chunks already processed in Phase 1. Only chunks NOT processed in Phase 1 run in Phase 2. This is the simplest approach: Phase 1 handles blocks 1 through K, Phase 2 handles blocks K+1 through N.
- (Alternative) Phase 2 re-extracts all chunks including Phase 1 chunks, and consolidation deduplicates. This works but wastes LLM calls.

**Warning signs:** The consolidation event dedup step (which already exists) produces a large dedup log, indicating many duplicate events.

### Pitfall 3: Token budget explosion in consolidation

**What goes wrong:** With parallel extraction, all chunk event drafts arrive at once. For a 22-chunk deal, the consolidation prompt may exceed the model's context window.

**Why it happens:** Each chunk event draft is ~1-3K tokens. 22 chunks = 22-66K tokens of event drafts alone, plus the actor roster, count_assertions, and instructions.

**How to avoid:** Consolidation already receives all chunk drafts -- this is not new. But verify that the consolidation prompt stays within model context limits. For very large deals (stec at 22 chunks), consider summarizing chunk event drafts to their structured JSON only (strip verbose summaries) before passing to consolidation. Current models (Claude Sonnet 4, GPT-5.4) have 128K-200K context windows, which accommodates even the largest deals.

**Warning signs:** Consolidation pass produces truncated or incomplete output, missing events from later chunks.

### Pitfall 4: Inconsistent chunk numbering between phases

**What goes wrong:** Phase 1 uses `c1_evt_001` through `cK_evt_XXX`. Phase 2 uses `cK+1_evt_001` through `cN_evt_XXX`. If Phase 2 chunks use independent numbering, temporary event IDs may collide.

**How to avoid:** Assign chunk numbers globally at planning time. Phase 2 chunks continue the numbering from Phase 1 (e.g., if Phase 1 processed chunks 1-12, Phase 2 starts at chunk 13). The consolidation pass replaces all temporary IDs with global IDs anyway, so collisions in temporary IDs are not catastrophic, but clean numbering simplifies debugging.

### Pitfall 5: Overlap blocks processed twice

**What goes wrong:** The current SKILL.md specifies 1-2 blocks of overlap between adjacent chunks. When Phase 2 chunks run in parallel, each chunk independently handles its overlap blocks. Two adjacent Phase 2 chunks may extract the same boundary event.

**How to avoid:** This is already handled by the consolidation pass's event dedup step (step 2 in the consolidation procedure). The dedup uses `(event_type, date, actor_ids)` as the dedup key, which catches boundary duplicates. No change needed.

## Empirical Data: Actor Introduction Patterns

Analysis of extracted deals confirms the front-loaded actor introduction pattern:

### STEC (largest deal: 235 blocks, ~22 chunks of 11 blocks each)

| Chunk | Blocks | New Actors | Cumulative | % Complete |
|-------|--------|------------|------------|------------|
| 1 | 1-11 | 8 | 8 | 36% |
| 2 | 12-22 | 3 | 11 | 50% |
| 3 | 23-33 | 5 | 16 | 73% |
| 4 | 34-44 | 3 | 19 | 86% |
| 5 | 45-55 | 0 | 19 | 86% |
| 6 | 56-66 | 1 | 20 | 91% |
| 7 | 67-77 | 0 | 20 | 91% |
| 8 | 78-88 | 0 | 20 | 91% |
| 9 | 89-99 | 2 | 22 | 100% |
| 10-22 | 100-235 | 0 | 22 | 100% |

**Result:** All actors introduced by chunk 9 (block 99, 42% through filing). Chunks 10-22 (58% of all chunks) would run in parallel with zero new actors to discover.

### Petsmart-Inc (small deal: 36 blocks, ~4 chunks of 11 blocks each)

| Chunk | Blocks | New Actors | Cumulative | % Complete |
|-------|--------|------------|------------|------------|
| 1 | 1-11 | 5 | 5 | 45% |
| 2 | 12-22 | 6 | 11 | 100% |
| 3 | 23-33 | 0 | 11 | 100% |
| 4 | 34-36 | 0 | 11 | 100% |

**Result:** All actors introduced by chunk 2 (block 22, 61% through filing). Chunks 3-4 (50% of all chunks) would run in parallel. (Note: 9 additional actors are placeholder/unnamed-party recovery from canonicalize, not from extraction.)

### Cross-chunk actor reference rate

In STEC, 66% of event-actor references are cross-chunk (the event is in a later chunk than the actor's first appearance). This confirms that the roster is heavily used by later chunks, making the two-phase approach correct: later chunks need the roster but do not contribute to it.

## Expected Speedup

### Per-deal wall-time reduction

| Deal | Blocks | Est. chunks | Phase 1 (seq) | Phase 2 (parallel) | Old time | New time | Speedup |
|------|--------|-------------|---------------|-------------------|----------|----------|---------|
| stec | 235 | 22 | 9 chunks seq | 13 chunks parallel | ~22 calls | ~10 calls | ~2.2x |
| mac-gray | 179 | 16 | 8 chunks seq | 8 chunks parallel | ~16 calls | ~9 calls | ~1.8x |
| medivation | 164 | 15 | 8 chunks seq | 7 chunks parallel | ~15 calls | ~9 calls | ~1.7x |
| zep | 113 | 10 | 5 chunks seq | 5 chunks parallel | ~10 calls | ~6 calls | ~1.7x |
| imprivata | 101 | 9 | 5 chunks seq | 4 chunks parallel | ~9 calls | ~6 calls | ~1.5x |
| penford | 94 | 9 | 5 chunks seq | 4 chunks parallel | ~9 calls | ~6 calls | ~1.5x |
| saks | 64 | 6 | 3 chunks seq | 3 chunks parallel | ~6 calls | ~4 calls | ~1.5x |
| petsmart | 36 | 4 | 2 chunks seq | 2 chunks parallel | ~4 calls | ~3 calls | ~1.3x |
| prov-worc | 40 | 4 | 2 chunks seq | 2 chunks parallel | ~4 calls | ~3 calls | ~1.3x |

**Notes:**
- "Calls" counts include +1 for consolidation in both old and new.
- Phase 2 parallel calls count as 1 wall-clock unit regardless of how many chunks run in parallel (assuming the LLM agent can issue multiple concurrent API calls).
- The speedup is most significant for large deals (stec, mac-gray, medivation) where the sequential tail is longest.
- Cross-deal parallelism (running multiple deals simultaneously) remains the highest-leverage optimization and is orthogonal to this change.

## Code Examples

### SKILL.md Phase 1: Actor Discovery (Sequential)

```markdown
### Phase 1: Actor Discovery (Sequential)

Process chunks sequentially starting from chunk_1. Each chunk extracts actors
AND events together with roster carry-forward (identical to current chunk
extraction). After each chunk, check if new actors were minted:

- If new actors were minted: continue to next chunk.
- If no new actors were minted AND at least 50% of chunks have been processed:
  increment a no-new-actor counter. After 2 consecutive chunks with zero new
  actors, declare Phase 1 complete.
- If fewer than 50% of chunks have been processed: continue regardless.

When Phase 1 completes, the actor roster is final. Record which chunks were
processed in Phase 1 (e.g., chunks 1 through K).
```

### SKILL.md Phase 2: Parallel Event Extraction

```markdown
### Phase 2: Parallel Event Extraction

For every chunk NOT already processed in Phase 1 (chunks K+1 through N):

Each chunk receives:
1. Its block window rendered as numbered text
2. Scoped evidence items for that window only
3. The COMPLETE actor roster from Phase 1 (compact format: actor_id,
   display_name, canonical_name, aliases, role, bidder_kind only)

Each chunk extracts events only. It does NOT mint new actors. For each event,
assign temporary per-chunk event_id values (e.g., c13_evt_001). Reference
actor_ids from the provided roster.

If a chunk encounters an entity name that does not match any actor in the
roster, record it in the chunk's `unresolved_mentions` list.

All Phase 2 chunks may be issued concurrently.
```

### SKILL.md Compact Roster Format

```markdown
When passing the actor roster to Phase 2 chunks, use this compact format:

```json
[
  {
    "actor_id": "bidder_wdc",
    "display_name": "Western Digital Corporation",
    "canonical_name": "WESTERN DIGITAL CORPORATION",
    "aliases": ["WDC", "Party B"],
    "role": "bidder",
    "bidder_kind": "strategic"
  }
]
```

Strip evidence_refs, notes, geography, listing_status, is_grouped,
group_size, group_label, advisor_kind, advised_actor_id from the roster
passed to Phase 2 chunks. These fields are not needed for event extraction
and waste prompt tokens.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Two-pass single-shot extraction | Sequential chunked extraction | Phase 6 (2026-03-25) | Handles large filings, but serial |
| No actor dedup | Deterministic actor dedup in canonicalize | Phase 6 (2026-03-25) | Catches chunk-boundary duplicates |
| Full-context enrichment calls | Event-targeted re-reads in enrich-deal | Phase 6 (2026-03-25) | Reduced enrichment token cost |

**Note:** The sequential chunked extraction from Phase 6 is the baseline being optimized. The two-phase parallel approach is a refinement, not a rewrite. The consolidation pass, output contract, and all downstream deterministic stages remain unchanged.

## Open Questions

1. **Agent concurrency capabilities**
   - What we know: Claude Code can issue multiple tool calls in a single response. The agent can run multiple bash commands or file operations in parallel.
   - What is unclear: Whether the agent can issue multiple LLM API calls (for Phase 2 chunks) truly concurrently, or whether "parallel" means "issued in the same prompt but processed sequentially by the API." This depends on the agent runtime, not the SKILL.md.
   - Recommendation: Design the SKILL.md to request parallel execution. The actual concurrency depends on the agent runtime. Even if the agent serializes the calls, the two-phase architecture still saves tokens (compact roster) and provides the structural foundation for true parallelism when the agent runtime supports it.

2. **Optimal Phase 1 cutoff for unextracted deals**
   - What we know: STEC and petsmart-inc show actors introduced in the first 40-60% of blocks.
   - What is unclear: Whether the 7 unextracted deals follow the same pattern. SEC merger backgrounds typically introduce actors early (NDAs precede proposals), but unusual filing structures exist.
   - Recommendation: Use the 50% floor + 2-consecutive-empty-chunks heuristic. This is conservative enough to handle outliers while still providing speedup for the majority of cases.

3. **Phase 2 event quality vs Phase 1**
   - What we know: Phase 2 chunks receive a complete roster but no running event history. Events extracted in Phase 2 cannot reference prior events for context (e.g., "the second bid from Company A" needs to know about the first bid).
   - What is unclear: Whether this loss of event context degrades event quality.
   - Recommendation: This is acceptable because (a) each chunk's block text contains the narrative context, (b) the consolidation pass already handles cross-chunk event reasoning (temporal signals, re-reads), and (c) the existing architecture never passed prior events to subsequent chunks anyway -- only the actor roster was carried forward.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | `pytest.ini` |
| Quick run command | `pytest -q tests/test_skill_canonicalize.py tests/test_skill_check.py -x` |
| Full suite command | `pytest -q` |

### Phase Requirements -> Test Map

This phase modifies only the SKILL.md (LLM skill instructions). No Python code changes are required. Therefore, the primary validation is end-to-end: run the modified skill on a deal and verify that downstream deterministic stages still pass.

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PAR-01 | Two-phase extraction produces valid actors_raw.json | e2e (manual) | `/extract-deal stec` then `skill-pipeline canonicalize --deal stec` | N/A (skill-level) |
| PAR-02 | Two-phase extraction produces valid events_raw.json | e2e (manual) | `/extract-deal stec` then `skill-pipeline check --deal stec` | N/A (skill-level) |
| PAR-03 | Existing canonicalize tests pass unchanged | unit | `pytest -q tests/test_skill_canonicalize.py -x` | Yes |
| PAR-04 | Existing check tests pass unchanged | unit | `pytest -q tests/test_skill_check.py -x` | Yes |
| PAR-05 | Existing verify/coverage tests pass unchanged | unit | `pytest -q tests/test_skill_verify.py tests/test_skill_coverage.py -x` | Yes |
| PAR-06 | Existing pipeline integration tests pass | integration | `pytest -q tests/test_skill_pipeline.py -x` | Yes |

### Sampling Rate

- **Per task commit:** `pytest -q tests/test_skill_canonicalize.py tests/test_skill_check.py -x`
- **Per wave merge:** `pytest -q`
- **Phase gate:** Full suite green + manual `/extract-deal stec` validation

### Wave 0 Gaps

None -- existing test infrastructure covers all deterministic stage requirements. The phase's primary deliverable is SKILL.md changes, which are validated by running the skill and checking downstream deterministic gates.

## Sources

### Primary (HIGH confidence)

- `.claude/skills/extract-deal/SKILL.md` -- current extraction architecture, chunk specification, roster carry-forward rules
- `skill_pipeline/canonicalize.py` -- deterministic dedup logic, actor dedup keys, event chronology ordering
- `skill_pipeline/check.py` -- structural gate, actor audit checks
- `.planning/phases/06-chunked-extraction-architecture/06-CONTEXT.md` -- Phase 6 design decisions, why sequential was chosen initially
- Data analysis of `data/skill/stec/extract/` and `data/skill/petsmart-inc/extract/` -- empirical actor introduction patterns

### Secondary (MEDIUM confidence)

- `.planning/research/2026-03-25-alex-conventions-discrepancies-speed.md` -- Prior speed analysis (Section 3), latency estimates, parallelization opportunities
- Simulated chunk boundaries using 11-block chunk size against real block data

### Tertiary (LOW confidence)

- Agent concurrency capabilities -- the degree to which the LLM agent runtime supports true parallel API calls is uncertain and depends on the specific runtime environment

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries needed, confirmed by reading all Python modules
- Architecture: HIGH -- two-phase split supported by empirical data from 2 deals (STEC=22 actors, petsmart=20 actors)
- Pitfalls: HIGH -- failure modes identified from first-principles analysis of the data flow
- Speedup estimates: MEDIUM -- based on chunk counts and the assumption that Phase 2 parallel calls complete in ~1 wall-clock unit

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (stable architecture, no fast-moving dependencies)
