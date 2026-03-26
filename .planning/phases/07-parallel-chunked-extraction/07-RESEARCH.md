# Phase 7: Parallel Chunked Extraction & Enrichment - Research

**Researched:** 2026-03-26 (revised)
**Domain:** LLM extraction and enrichment parallelization via Claude Code subagents
**Confidence:** HIGH (corrected with empirical data from live extraction artifacts)

## Revision History

- **v1 (2026-03-25):** Initial single-deal-parallelization research proposed Python async executor. Correctly identified enrichment as the primary parallelization target. Incorrectly dismissed subagents.
- **v2 (2026-03-26):** Parallel-chunked-extraction research proposed SKILL.md-only two-phase extraction. Based on simulated 22-chunk model (11 blocks per chunk) that does not match actual extraction output.
- **v3 (2026-03-26, this version):** Consolidated and corrected. Empirical data from live stec and petsmart-inc artifacts replaces simulated chunk model. Subagent-based parallelism replaces both the Python async executor and the fictional agent-native parallel calls. Both extraction tail and enrichment are addressed.

## Summary

The current pipeline processes all LLM work sequentially: the orchestrating agent handles one task at a time within its conversation loop. There is no Python code wrapping LLM calls -- extraction and enrichment are entirely agent-driven via SKILL.md instructions.

Empirical analysis of live extraction artifacts reveals two key findings that invalidate earlier research assumptions:

1. **The extraction tail is event-sparse.** STEC's actual extraction produced 7 chunks (not 22 as simulated). Chunks 5-7 (covering 56% of blocks) yielded only 2 of 37 events. Parallelizing the extraction tail gives near-zero speedup for STEC.

2. **The enrichment stage is the real bottleneck.** Enrich-deal performs 9-15 fully independent agent reasoning turns (dropout classification, advisory verification, count reconciliation, initiation judgment). These are self-contained tasks with no data dependencies between them.

The concurrency mechanism is **Claude Code subagents**. The orchestrating agent can spawn multiple subagents in a single message, and they execute concurrently. Each subagent is a full Claude instance with file access. This provides true wall-clock parallelism with zero new Python code -- only SKILL.md instruction changes.

**Primary recommendation:** Rewrite enrich-deal SKILL.md to spawn parallel subagents for all independent enrichment tasks. Optionally apply the same pattern to extraction tail chunks and consolidation re-reads. Keep the two-phase extraction architecture for token savings (compact roster format) even where wall-clock gains from tail parallelism are small.

## Corrections to Prior Research

### Correction 1: Chunk count and distribution (CRITICAL)

The v2 research modeled STEC as 22 chunks of ~11 blocks each. Live extraction artifacts show 7 chunks with highly non-uniform block distribution:

| Chunk | Blocks | Block Range | New Actors | Events | Notes |
|-------|--------|-------------|------------|--------|-------|
| 1 | 13 | B001-B015 | 11 | 7 | Heavy actor discovery |
| 2 | 27 | B017-B044 | 8 | 11 | Heavy actor discovery |
| 3 | 34 | B046-B081 | 1 | 12 | Most events, few new actors |
| 4 | 14 | B082-B096 | 2 | 5 | Last new actors (22 total) |
| 5 | 47 | B097-B146 | 0 | **2** | Near-empty tail |
| 6 | 39 | B147-B187 | 0 | **0** | Empty tail |
| 7 | 45 | B188-B234 | 0 | **0** | Empty tail |

**Key finding:** All 22 actors are introduced by chunk 4 (block 96, 41% through). But 35 of 37 events (95%) are also in chunks 1-4. The tail (chunks 5-7) covers 131 blocks but yields almost nothing.

Petsmart-inc (3 chunks actual):

| Chunk | Blocks | New Actors | Events |
|-------|--------|------------|--------|
| 1 | 12 | 5 | 4 |
| 2 | 13 | 6 | 12 |
| 3 | 11 | 0 | 6 |

Petsmart's tail (chunk 3) has meaningful events, so parallelization of the extraction tail has variable value across deals.

### Correction 2: Agent concurrency model (CRITICAL)

The v2 research assumed the agent could issue parallel LLM API calls natively. The v1 research correctly identified that "the agent processes one tool call at a time."

**Neither research considered subagents.** Claude Code's `Agent` tool spawns independent subagents that run concurrently when launched in a single message. Each subagent:
- Is a full Claude instance with its own reasoning
- Has complete tool access (Read, Write, Bash, Grep, Glob)
- Can read filing text, chronology blocks, evidence items, extract artifacts
- Returns a structured result to the parent agent

This is the correct concurrency mechanism. It requires zero new Python code.

The v1 research dismissed subagents with "Subagents cannot make LLM API calls to external endpoints; they use Claude Code's own model." This is technically true but irrelevant -- the subagent IS the LLM doing the work. For enrichment tasks (dropout classification, advisory verification), the subagent reads source context and reasons about it, which is exactly what the main agent does today, just in parallel.

### Correction 3: Speedup model (recalculated)

The v2 research projected 2.2x extraction speedup for STEC. Corrected estimates using actual chunk data:

**Extraction tail parallelism (subagents for chunks past roster completion):**

| Deal | Actual Chunks | Serial (all) | Parallel tail | Events in tail | Real gain |
|------|---------------|-------------|---------------|----------------|-----------|
| stec | 7 | 7 calls | 4 serial + 3 parallel | 2/37 (5%) | Minimal |
| petsmart-inc | 3 | 3 calls | 2 serial + 1 parallel | 6/22 (27%) | Small |

**Enrichment parallelism (subagents for independent tasks):**

| Task | Sequential turns | With subagents | Savings |
|------|-----------------|----------------|---------|
| Dropout classification (5 drops) | 5 turns, ~5 min | 1 batch (5 subagents), ~2 min | ~3 min |
| Advisory verification (3-8 advisors) | 3-8 turns, ~5 min | 1 batch (3-8 subagents), ~2 min | ~3 min |
| Initiation judgment | 1 turn | 1 subagent (batched with above) | 0 |
| Count reconciliation | 1 turn | 1 subagent (batched with above) | 0 |
| **Total enrichment** | **~12 turns, ~15 min** | **1 wall-clock batch, ~2-3 min** | **~12 min** |

**Consolidation re-read parallelism (subagents for independent re-reads):**

| Task | Sequential | With subagents | Savings |
|------|-----------|----------------|---------|
| Targeted re-reads (0-5 types) | 0-5 turns, ~0-5 min | 1 batch, ~1 min | ~0-4 min |

**Total pipeline impact (STEC):**

| Component | Today | After | Saved |
|-----------|-------|-------|-------|
| Extraction (7 chunks serial) | ~15 min | ~15 min (no change) | 0 |
| Consolidation + re-reads | ~5 min | ~2 min | ~3 min |
| Deterministic gates | ~5 sec | ~5 sec | 0 |
| Verify-extraction | ~3 min | ~3 min | 0 |
| Enrich-deal | ~15 min | ~3 min | **~12 min** |
| Export | ~2 min | ~2 min | 0 |
| Agent overhead | ~20 min | ~18 min (fewer turns) | ~2 min |
| **Total** | **~60 min** | **~43 min** | **~17 min (28%)** |

The enrichment stage delivers the vast majority of savings.

## Project Constraints (from CLAUDE.md)

- Fail fast on violated assumptions, invalid states, unexpected inputs. No fallback logic.
- Do not overengineer. Shortest correct path. No speculative abstractions.
- Do not expand scope. Only solve the parallelization requirement.
- Keep pipeline stages deterministic where possible.
- Do not silently alter semantics, schemas, event definitions, or output meaning.
- Existing Pydantic-first patterns for schemas; `snake_case` for functions, modules, JSON keys.
- Target Python 3.11+; type hints on public functions.
- Filing `.txt` files under `raw/` are immutable truth sources.
- Canonical extract artifacts must carry `evidence_span_ids`; canonical loading must fail if `spans.json` is missing.
- Downstream contract: `actors_raw.json` + `events_raw.json` in `data/skill/<slug>/extract/`. No schema changes.
- `.claude/skills/` is the canonical skill tree. Mirrors must be synced.

## Standard Stack

### Core

No new Python libraries needed. The parallelization is entirely at the SKILL.md orchestration level via Claude Code subagents.

| Component | Current | Purpose | Change Needed |
|-----------|---------|---------|---------------|
| enrich-deal SKILL.md | Sequential per-task agent turns | Enrichment instructions | Rewrite to spawn parallel subagents for independent tasks |
| extract-deal SKILL.md | Sequential chunk extraction | Extraction instructions | Add two-phase architecture with optional subagent tail |
| Consolidation (SKILL.md) | Sequential re-reads | Global dedup, ID assignment | Batch re-reads as parallel subagents |
| canonicalize.py | Actor/event dedup | Deterministic post-extraction | No change |
| check.py | Actor audit + structural checks | Deterministic gate | No change |
| verify.py | Span resolution | Deterministic gate | No change |
| coverage.py | Source cue audit | Deterministic gate | No change |
| enrich_core.py | Rounds, bids, cycles | Deterministic enrichment | No change |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Subagent parallelism | Python `asyncio` executor with `AsyncAnthropic` | Works but introduces ~80 lines of new Python LLM client code into a codebase with zero existing LLM client code. New maintenance surface, new test infrastructure. Overkill for the 9-deal scope. |
| Subagent parallelism | SKILL.md prompt consolidation (batch N tasks into 1 large prompt) | Reduces turn count but does not achieve true parallelism. Quality may degrade for very large batched prompts. Useful as a lightweight fallback if subagent overhead is unacceptable. |
| Subagent parallelism | Anthropic Message Batches API | 50% cost savings but up to 24-hour latency. Unsuitable for interactive pipeline runs. |
| Two-phase extraction | Full parallel with post-hoc actor reconciliation | Requires each chunk to independently mint actor_ids, then complex reconciliation. High risk of inconsistency. |

### Escalation Path

If subagent token overhead becomes a cost concern at scale:
1. **First escalation:** SKILL.md prompt consolidation (batch multiple independent tasks into single prompts). Zero new code, ~70% of the wall-clock savings.
2. **Second escalation:** Python async executor (`skill_pipeline/parallel.py`, ~80 lines). Minimal token overhead per call, real parallelism, but introduces LLM client code into the Python codebase.

## Architecture Patterns

### Pattern 1: Subagent Parallelism for Enrichment (PRIMARY)

**What:** The orchestrating agent reads enrichment inputs, identifies all independent tasks, spawns one subagent per task in a single message, collects results, and writes the final `enrichment.json`.

**When to use:** Always for enrich-deal. This is the primary parallelization target.

**Flow:**

```text
Orchestrating agent:
  1. Read SKILL.md, deterministic_enrichment.json, actors/events
  2. Identify independent tasks:
     - 5 dropout events needing classification
     - 3 advisors needing verification
     - 1 initiation judgment
     - 1 count reconciliation
  3. Spawn 10 subagents in ONE message:
     ├─ Subagent 1: "Classify dropout for Company C. Blocks 40-55. Return JSON."
     ├─ Subagent 2: "Classify dropout for Company D. Blocks 60-70. Return JSON."
     ├─ Subagent 3: "Classify dropout for Company E. Blocks 80-85. Return JSON."
     ├─ Subagent 4: "Classify dropout for Company F. Blocks 90-95. Return JSON."
     ├─ Subagent 5: "Classify dropout for Company G. Blocks 100-110. Return JSON."
     ├─ Subagent 6: "Verify advisor Gibson Dunn. Blocks 1-15. Return JSON."
     ├─ Subagent 7: "Verify advisor BofA. Blocks 12-44. Return JSON."
     ├─ Subagent 8: "Verify advisor Latham. Blocks 46-81. Return JSON."
     ├─ Subagent 9: "Judge initiation. Blocks 1-15. Return JSON."
     └─ Subagent 10: "Reconcile counts. Roster + assertions. Return JSON."
  4. All 10 subagents execute concurrently (~2 min wall clock)
  5. Collect all 10 results
  6. Assemble enrichment.json
  7. Write to disk
```

**Subagent prompt template:**

Each subagent receives a self-contained prompt:
- The specific task (classify dropout / verify advisor / judge initiation / reconcile counts)
- The scoped block window to read (file path + block range)
- The relevant actor/event context (compact JSON)
- The expected output schema
- Instruction to return ONLY the structured JSON result

**Token overhead:** Each subagent carries ~10-20K tokens of system prompt and tool description overhead compared to ~1-2K for a bare API call. For 10 subagents, this is ~100-200K tokens of overhead. At current Claude pricing this is ~$0.30-0.60 per deal enrichment. Acceptable for 9 deals.

### Pattern 2: Two-Phase Extraction with Optional Subagent Tail

**What:** Split extraction into sequential actor discovery (Phase 1) and optional parallel event extraction (Phase 2) for tail chunks.

**When to use:** For extraction. The two-phase architecture provides token savings (compact roster) even when tail parallelism provides minimal wall-clock improvement.

**Flow:**

```text
Phase 1: Actor Discovery (SEQUENTIAL, main agent)
  chunk_1 -> chunk_2 -> ... -> chunk_K
  Each chunk extracts actors AND events with roster carry-forward.
  Stop when: 2 consecutive chunks with zero new actors AND >= 50% of chunks processed.
  Output: complete actor roster + Phase 1 event drafts

Phase 2: Event-Only Tail (PARALLEL via subagents, if remaining chunks exist)
  Main agent spawns one subagent per remaining chunk:
  ├─ Subagent: "Extract events from blocks 97-146. Roster: [compact]. Return JSON."
  ├─ Subagent: "Extract events from blocks 147-187. Roster: [compact]. Return JSON."
  └─ Subagent: "Extract events from blocks 188-234. Roster: [compact]. Return JSON."
  Each subagent receives compact roster (6 fields per actor, no evidence_refs).
  Each subagent extracts events only, does NOT mint new actors.
  Unresolved entity names go to unresolved_mentions.

Phase 3: Consolidation (SEQUENTIAL, main agent)
  Same as today. Receives all chunk outputs (Phase 1 + Phase 2).
  Dedup, global IDs, taxonomy sweep, re-reads, temporal signals.
  Output: actors_raw.json + events_raw.json (unchanged contract)
```

**Compact roster format for Phase 2 subagents:**

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

Strip evidence_refs, notes, geography, listing_status, is_grouped, group_size, group_label, advisor_kind, advised_actor_id. These fields waste prompt tokens for event-only extraction.

**When the tail is nearly empty (like STEC chunks 5-7):** The subagents complete in seconds because there is little to extract. The overhead is minimal. The architecture does not hurt even when the tail is sparse.

### Pattern 3: Subagent Consolidation Re-reads

**What:** When the taxonomy sweep identifies multiple NOT FOUND event types, spawn one subagent per missing type rather than re-reading sequentially.

**When to use:** During consolidation when 2+ targeted re-reads are needed.

**Flow:**

```text
Main agent: taxonomy sweep identifies 3 missing event types
Main agent spawns 3 subagents:
  ├─ Subagent: "Search for 'nda_execution' events in blocks 1-50. Return JSON."
  ├─ Subagent: "Search for 'regulatory_filing' events in blocks 100-234. Return JSON."
  └─ Subagent: "Search for 'shareholder_vote' events in blocks 200-234. Return JSON."
Main agent: integrates any found events into consolidated output
```

### Anti-Patterns to Avoid

- **Full parallel extraction without actor discovery phase:** Each chunk independently mints actor_ids, requiring O(N^2) reconciliation. The two-phase approach avoids this entirely.
- **Python-side LLM orchestrator for 9 deals:** Building `parallel.py` + tests + CLI integration introduces a new maintenance surface for minimal cost savings at current scale. Consider only if processing hundreds of deals.
- **Subagents for serial-dependent work:** Do not spawn subagents for chunk extraction during Phase 1 (actor discovery). Roster carry-forward creates a hard serial dependency.
- **Mega-prompts that combine unrelated tasks:** Batching all enrichment tasks (dropout + advisory + initiation + counts) into one enormous prompt degrades quality. Use one subagent per logically distinct task.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM call parallelism | Python asyncio executor | Claude Code subagents | Zero new code; subagents provide true parallelism with file access |
| Actor reconciliation | Custom string-matching dedup | Two-phase extraction (sequential actors, parallel events) | Reconciliation is error-prone; two-phase avoids it |
| Chunk planning | Custom Python chunk planner | SKILL.md instructions | Chunking is already documented in SKILL.md |
| Global event ID assignment | Custom re-numbering script | Consolidation pass (already exists) | Consolidation already handles this |
| Prompt templating | Custom Python formatter | Subagent prompt in SKILL.md | The agent builds the prompt naturally |

## Empirical Data: Actual Extraction Artifacts

### STEC (largest deal: 234 blocks, 7 actual chunks at ~3,800 token budget)

| Chunk | Block Range | Usable Blocks | New Actors | Cumulative Actors | Events | Event % |
|-------|-------------|---------------|------------|-------------------|--------|---------|
| 1 | B001-B015 | 13 | 11 | 11 (50%) | 7 | 19% |
| 2 | B017-B044 | 27 | 8 | 19 (86%) | 11 | 30% |
| 3 | B046-B081 | 34 | 1 | 20 (91%) | 12 | 32% |
| 4 | B082-B096 | 14 | 2 | 22 (100%) | 5 | 14% |
| 5 | B097-B146 | 47 | 0 | 22 | 2 | 5% |
| 6 | B147-B187 | 39 | 0 | 22 | 0 | 0% |
| 7 | B188-B234 | 45 | 0 | 22 | 0 | 0% |

**Actor discovery:** Complete at chunk 4 (block 96, 41% through filing).
**Event density:** 95% of events in chunks 1-4. Tail (chunks 5-7) is near-empty.
**Implication:** Extraction tail parallelism provides minimal speedup for STEC. The win is in enrichment.

### Petsmart-Inc (small deal: 36 blocks, 3 actual chunks)

| Chunk | Blocks | New Actors | Cumulative Actors | Events |
|-------|--------|------------|-------------------|--------|
| 1 | 12 | 5 | 5 (45%) | 4 |
| 2 | 13 | 6 | 11 (100%) | 12 |
| 3 | 11 | 0 | 11 | 6 |

**Actor discovery:** Complete at chunk 2 (61% through filing).
**Event density:** Chunk 3 has 27% of events -- more meaningful tail than STEC.
**Implication:** Small deals have too few chunks for meaningful parallelism anyway.

### Cross-deal actor reference rate

In STEC, 66% of event-actor references are cross-chunk (the event is in a later chunk than the actor's first appearance). This confirms the roster is heavily used by later chunks, validating the two-phase architecture for token savings even when wall-clock gains are small.

### Why the tail is empty (structural explanation)

SEC merger background chronologies follow a consistent narrative arc:
1. **Early blocks:** Board decisions, advisor retention, initial contacts, NDAs, early bids -- high event density, many actor introductions.
2. **Middle blocks:** Bid revisions, negotiations, due diligence, committee meetings -- moderate event density, few new actors.
3. **Late blocks:** Fairness opinions, legal analysis, regulatory review, voting procedures, boilerplate disclosures -- low event density, zero new actors.

The tail is structurally sparse because the deal narrative is front-loaded. This pattern is expected to hold across all 9 deals.

## Common Pitfalls

### Pitfall 1: Subagent returns malformed or incomplete result

**What goes wrong:** A subagent crashes, returns non-JSON text, or omits required fields.
**How to avoid:** The orchestrating agent validates each subagent's response against the expected schema before integrating it. On validation failure, the agent retries or reports the error. Do not silently drop malformed results.
**Warning signs:** Missing entries in enrichment.json for specific events/advisors.

### Pitfall 2: Subagent reads wrong file or block range

**What goes wrong:** A subagent prompt specifies the wrong block range or file path, producing hallucinated classifications.
**How to avoid:** The orchestrating agent constructs subagent prompts with explicit absolute file paths and exact block ID ranges derived from the extract artifacts. Do not pass vague instructions like "read the relevant blocks."
**Warning signs:** Enrichment results that contradict the filing text at the cited block range.

### Pitfall 3: Late-appearing actors missed in extraction Phase 2

**What goes wrong:** An actor first mentioned after Phase 1 completes is not in the roster.
**How to avoid:** Phase 2 subagents record unmatched entity names in `unresolved_mentions`. The consolidation pass reviews these and either maps them to existing actors (alias resolution) or mints new actors as late additions. The existing `unresolved_mentions` mechanism and canonicalize's `_recover_unnamed_parties` handle this.
**Warning signs:** `unresolved_mentions` in output contains entity names that should be actors.

### Pitfall 4: Duplicate events from Phase 1 + Phase 2 overlap

**What goes wrong:** Phase 1 chunks extract events. Phase 2 subagents re-extract events for overlapping blocks.
**How to avoid:** Phase 2 subagents process only chunks NOT already handled in Phase 1. Phase 1 handles chunks 1 through K, Phase 2 handles K+1 through N. No overlap.
**Warning signs:** Consolidation dedup log shows many boundary duplicates.

### Pitfall 5: Subagent token overhead exceeds budget at scale

**What goes wrong:** At 10 subagents per deal * 9 deals = 90 subagent conversations. Total overhead tokens become significant.
**How to avoid:** Monitor total token usage per deal. If subagent overhead exceeds 2x the sequential baseline cost, switch to the escalation path (prompt consolidation first, then Python async executor). For 9 deals, subagent overhead is ~$3-5 total, which is acceptable.
**Warning signs:** Per-deal cost exceeds $1.50 for enrichment alone.

### Pitfall 6: Roster carry-forward broken by premature Phase 2 transition

**What goes wrong:** Phase 1 ends too early, missing late-appearing actors.
**How to avoid:** Require both conditions: (a) at least 50% of chunks processed in Phase 1, AND (b) 2 consecutive chunks with zero new actors. This is conservative enough for outlier filings.
**Warning signs:** Phase 2 subagents report many unresolved_mentions.

## Open Questions

### Resolved

1. **Agent concurrency capabilities** -- RESOLVED. Claude Code subagents provide true parallelism. The orchestrating agent spawns multiple subagents in one message; they run concurrently and return results. This was missed by both v1 and v2 research.

2. **Chunk count model** -- RESOLVED. Live artifacts show 7 chunks for STEC (not 22 simulated). Block distribution is highly non-uniform (13-47 blocks per chunk). Speedup estimates are recalculated using actual data.

3. **Phase 2 event quality** -- RESOLVED. Not a concern because (a) the tail is event-sparse in practice, (b) each chunk's block text contains full narrative context, and (c) consolidation handles cross-chunk reasoning.

### Still Open

1. **Event density in the 7 unextracted deals**
   - What we know: STEC tail is nearly empty, petsmart tail has some events.
   - What's unclear: Whether mac-gray, medivation, zep (larger deals) have heavier tails.
   - Recommendation: Accept variable tail density. The architecture works regardless -- subagent tail extraction is either fast (empty tail) or useful (dense tail). No need to validate before implementation.

2. **Subagent result format consistency**
   - What we know: Subagents are full Claude instances that can produce structured JSON.
   - What's unclear: How reliably subagents adhere to a specific JSON schema without Pydantic validation.
   - Recommendation: The orchestrating agent validates subagent output before integration. Include explicit JSON schema examples in subagent prompts.

3. **Optimal subagent batch size**
   - What we know: Claude Code can launch multiple subagents in one message.
   - What's unclear: Whether there is a practical limit on concurrent subagents (10? 20?).
   - Recommendation: Start with the natural task count (typically 5-15 for enrichment). If Claude Code throttles, split into 2 batches.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | `pytest.ini` |
| Quick run command | `pytest -q tests/test_skill_canonicalize.py tests/test_skill_check.py -x` |
| Full suite command | `pytest -q` |

### Phase Requirements -> Test Map

This phase modifies only SKILL.md files (LLM skill instructions). No Python code changes are required. Validation is end-to-end: run the modified skill on a deal and verify downstream deterministic stages pass.

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PAR-01 | Subagent enrichment produces valid enrichment.json | e2e (manual) | `/enrich-deal stec` then inspect output | N/A (skill-level) |
| PAR-02 | Two-phase extraction produces valid actors_raw.json + events_raw.json | e2e (manual) | `/extract-deal stec` then `skill-pipeline canonicalize --deal stec` | N/A (skill-level) |
| PAR-03 | Existing canonicalize tests pass unchanged | unit | `pytest -q tests/test_skill_canonicalize.py -x` | Yes |
| PAR-04 | Existing check tests pass unchanged | unit | `pytest -q tests/test_skill_check.py -x` | Yes |
| PAR-05 | Existing verify/coverage tests pass unchanged | unit | `pytest -q tests/test_skill_verify.py tests/test_skill_coverage.py -x` | Yes |
| PAR-06 | Existing enrich-core tests pass unchanged | unit | `pytest -q tests/test_skill_enrich_core.py -x` | Yes |
| PAR-07 | Existing pipeline integration tests pass | integration | `pytest -q tests/test_skill_pipeline.py -x` | Yes |
| PAR-08 | Full test suite green | regression | `pytest -q` | Yes |

### Sampling Rate

- **Per task commit:** `pytest -q tests/test_skill_enrich_core.py tests/test_skill_canonicalize.py -x`
- **Per wave merge:** `pytest -q`
- **Phase gate:** Full suite green + manual `/enrich-deal stec` and `/extract-deal` validation

### Wave 0 Gaps

None. This phase modifies SKILL.md instructions only. Existing test infrastructure covers all deterministic stage requirements. The phase's primary deliverable is SKILL.md changes validated by running skills and checking downstream gates.

## Sources

### Primary (HIGH confidence)

- `data/skill/stec/extract/chunks/chunk_{1..7}.json` -- live extraction artifacts with actual block counts, actor rosters, and event counts per chunk
- `data/skill/petsmart-inc/extract/chunks/chunk_{1..3}.json` -- live petsmart extraction artifacts
- `.claude/skills/extract-deal/SKILL.md` -- current extraction architecture
- `.claude/skills/enrich-deal/SKILL.md` -- current enrichment architecture
- `skill_pipeline/canonicalize.py`, `check.py`, `verify.py`, `coverage.py`, `enrich_core.py` -- deterministic gate implementations (confirmed zero changes needed)
- Claude Code Agent tool documentation -- subagent spawning, concurrent execution, result collection

### Secondary (MEDIUM confidence)

- `.planning/phases/06-chunked-extraction-architecture/06-CONTEXT.md` -- Phase 6 design decisions
- `.planning/research/2026-03-25-alex-conventions-discrepancies-speed.md` -- prior speed analysis

### Superseded

- `.planning/phases/07-single-deal-parallelization/07-RESEARCH.md` -- v1 research (Python async executor proposal). Correctly identified enrichment as primary target. Incorrectly dismissed subagents. Superseded by this document.
- `.planning/phases/07-parallel-chunked-extraction/07-RESEARCH.md` v2 -- prior version of this document. Based on simulated 22-chunk model. Superseded by corrected empirical data.

## Metadata

**Confidence breakdown:**
- Empirical data: HIGH -- derived from live extraction artifacts, not simulated chunk boundaries
- Architecture: HIGH -- subagent parallelism is a proven Claude Code capability
- Speedup estimates: MEDIUM-HIGH -- based on actual chunk/event counts, but enrichment timing is estimated from turn counts
- Pitfalls: HIGH -- failure modes identified from first-principles analysis of data flow and subagent behavior
- Cost estimates: MEDIUM -- subagent token overhead is estimated, not measured

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (stable architecture, no fast-moving dependencies)
