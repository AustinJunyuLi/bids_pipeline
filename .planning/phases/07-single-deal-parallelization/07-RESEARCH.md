# Phase 7: Single-Deal Pipeline Parallelization - Research

**Researched:** 2026-03-25
**Domain:** Parallel LLM API orchestration within a Claude Code agent-driven extraction pipeline
**Confidence:** HIGH

## Summary

The bids pipeline runs 4 AI stages per deal (extract, verify-extraction, enrich, export), each orchestrated by a Claude Code agent reading SKILL.md instructions. The agent itself makes sequential LLM API calls -- there is no Python code wrapping the LLM calls. For stec (largest deal, 234 blocks), the current sequential pipeline takes roughly 80 minutes end-to-end.

The primary parallelization opportunity is NOT in extract-deal (which has a hard serial dependency via roster carry-forward between chunks), but in enrich-deal's independent per-event LLM calls (dropout classification, advisory verification, count reconciliation, initiation judgment). A secondary opportunity exists in consolidation re-reads during extract-deal. The critical architectural question -- can a Claude Code agent issue parallel LLM calls? -- has a clear answer: **no, not directly**. The agent processes one tool call at a time. Parallelization requires either (a) new Python infrastructure that wraps the LLM calls, or (b) restructuring skills so the agent batches independent prompts into fewer, larger calls.

**Primary recommendation:** Build a thin Python async executor in `skill_pipeline/` that accepts a list of independent LLM prompts, fires them concurrently against the Anthropic API, and returns results. Update SKILL.md files to instruct the agent to prepare all independent prompts as a batch, invoke the Python executor once, and process the collected results. This is the minimum viable path to under-30-minute wall time for stec.

## Project Constraints (from CLAUDE.md)

The following directives from CLAUDE.md constrain implementation:

- **Python 3.11+** with 4-space indentation and type hints on public functions
- **Pydantic-first** patterns for schemas
- **Fail fast** on violated assumptions, invalid states, unexpected inputs -- no silent fallback
- **Deterministic stages remain deterministic** -- do not add fallback logic to keep them running on missing inputs
- **`skill_pipeline/` is the only Python package** -- new code goes here
- **`anthropic>=0.49`** already in dependencies
- **Skills are canonical in `.claude/skills/`** -- mirrors sync from there
- **Filing text under `raw/` is immutable** -- never touched by parallelization
- **Existing tests must pass** -- pytest with `tests/` as root
- **No overengineering** -- shortest correct path, no speculative abstractions

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `anthropic` | >=0.49 (already installed) | Async LLM API client via `AsyncAnthropic` | Already a dependency; provides native async support with `asyncio` |
| `asyncio` | stdlib (Python 3.11+) | Concurrent coroutine execution | Standard library; `asyncio.gather()` for parallel API calls |
| `pydantic` | >=2.0 (already installed) | Request/response schemas for batch prompts | Already used throughout the codebase |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `asyncio.Semaphore` | stdlib | Rate-limit concurrent requests | Always -- prevents exceeding Anthropic RPM limits |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Python async executor | Anthropic Message Batches API | 50% cost savings but up to 24-hour latency; unsuitable for interactive pipeline runs |
| Python async executor | Claude Code subagents in parallel | Subagents cannot make LLM API calls to external endpoints; they use Claude Code's own model |
| Python async executor | SKILL.md "mega-prompt" batching | Combines N independent tasks into 1 large prompt; lower quality than N focused prompts |
| `asyncio` | `threading` | Both work for I/O-bound LLM calls; asyncio is cleaner for structured concurrency |

**Installation:**
No new packages needed. `anthropic` and `pydantic` are already installed.

## Architecture Patterns

### Recommended Project Structure

```
skill_pipeline/
  parallel.py           # Async LLM executor: fire N prompts, collect N results
  parallel_schemas.py   # Pydantic models for parallel request/response batches
  cli.py                # New subcommand: skill-pipeline parallel-llm (or integrated into existing stages)
```

### Pattern 1: Async LLM Executor

**What:** A Python module that accepts a list of `(prompt_id, system_prompt, user_message)` tuples, fires them all concurrently via `AsyncAnthropic.messages.create()` with a semaphore for rate limiting, and returns a dict mapping `prompt_id` to response content.

**When to use:** Any time the SKILL.md identifies N independent LLM calls that share no data dependencies.

**Example:**

```python
# Source: Anthropic Python SDK docs + asyncio stdlib
import asyncio
from anthropic import AsyncAnthropic

async def run_parallel_prompts(
    prompts: list[dict],
    *,
    model: str,
    max_tokens: int = 4096,
    max_concurrent: int = 5,
) -> dict[str, str]:
    """Fire independent LLM prompts concurrently, return {id: response_text}."""
    client = AsyncAnthropic()  # reads ANTHROPIC_API_KEY from env
    semaphore = asyncio.Semaphore(max_concurrent)

    async def _call(prompt_id: str, system: str, user_msg: str) -> tuple[str, str]:
        async with semaphore:
            response = await client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user_msg}],
            )
            return prompt_id, response.content[0].text

    tasks = [
        _call(p["id"], p["system"], p["user"])
        for p in prompts
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    output = {}
    for result in results:
        if isinstance(result, Exception):
            raise result  # Fail fast -- do not silently swallow
        prompt_id, text = result
        output[prompt_id] = text
    return output
```

### Pattern 2: SKILL.md Batched Preparation

**What:** The SKILL.md instructs the agent to prepare all independent prompts as JSON, write them to a file, invoke the Python executor via CLI, and read back the results file.

**When to use:** For enrich-deal tasks (dropout classification, advisory verification, count reconciliation) where the agent can prepare all prompt contexts in advance.

**Example SKILL.md instruction:**
```
For dropout classification: prepare a JSON file at
data/skill/<slug>/enrich/_parallel_dropout_prompts.json containing one
entry per drop event, each with {id, system, user} fields. Then run:

  skill-pipeline parallel-llm --input data/skill/<slug>/enrich/_parallel_dropout_prompts.json --output data/skill/<slug>/enrich/_parallel_dropout_results.json

Read the results file and integrate each response into the
dropout_classifications section of enrichment.json.
```

### Pattern 3: Consolidation Re-Read Batching

**What:** During extract-deal consolidation, instead of issuing targeted re-reads one at a time for each NOT FOUND event type, the agent prepares all re-read prompts and fires them through the parallel executor.

**When to use:** Consolidation pass step 5 (targeted re-reads).

### Anti-Patterns to Avoid

- **Agent-level parallelism for LLM calls:** Claude Code agents process tool calls sequentially. Telling the agent "fire these 5 calls in parallel" in SKILL.md does nothing -- the agent will still execute them one at a time.
- **Anthropic Batch API for interactive use:** The Message Batches API has up to 24-hour latency. It is designed for offline processing, not interactive pipelines.
- **Parallelizing chunk extraction:** Chunks 1-N have a hard serial dependency via roster carry-forward. Do not attempt to parallelize chunk extraction unless roster carry-forward is redesigned (which is out of scope for this phase).
- **Thread-based parallelism for API calls:** While `threading` works, `asyncio` is the standard pattern for I/O-bound concurrent HTTP calls in modern Python. Do not mix paradigms.
- **Silent retry on rate-limit errors:** Fail fast on 429 errors with clear diagnostics. Do not implement automatic retry with backoff unless explicitly requested.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async HTTP client | Custom HTTP wrapper | `AsyncAnthropic` from `anthropic` SDK | Handles auth, retries, streaming, error types natively |
| Rate limiting | Custom token bucket | `asyncio.Semaphore(N)` | Stdlib, proven, no edge cases to debug |
| Structured output parsing | Manual JSON parsing of LLM responses | Pydantic model validation on response text | Already the project pattern; catches schema violations |
| Prompt templating | Custom string formatting | Prepare full prompt dicts in the SKILL.md agent step | The agent already reads filing context and builds prompts |
| Batch job orchestration | Custom queue/worker system | `asyncio.gather()` with fail-fast | Stdlib; the batch sizes here (5-15 concurrent) are trivial |

**Key insight:** The LLM call parallelization is a thin wrapper -- the hard part is restructuring the SKILL.md instructions to separate "prepare all prompts" from "execute all prompts" from "integrate all results." The Python infrastructure is minimal.

## LLM Call Inventory (Full Pipeline)

### Stage 1: Extract-Deal (Agent-driven, SKILL.md)

| Call Type | Count (stec) | Serial Dependency | Parallelizable |
|-----------|-------------|-------------------|----------------|
| Chunk extraction (sequential) | 7 | YES -- roster carry-forward | NO |
| Consolidation pass | 1 | YES -- needs all chunk outputs | NO |
| Consolidation targeted re-reads | 0-5 | NO -- independent per event type | YES |
| **Subtotal** | **8-13** | | **0-5 parallelizable** |

### Stage 2: Verify-Extraction (Agent-driven, SKILL.md)

| Call Type | Count (stec) | Serial Dependency | Parallelizable |
|-----------|-------------|-------------------|----------------|
| Deterministic gates (canonicalize, check, verify, coverage) | 0 LLM | N/A (Python CLI) | N/A |
| LLM repair loop Round 1 (if needed) | 1 | YES -- needs all findings | NO |
| LLM repair loop Round 2 (re-check) | 0-1 | YES -- needs Round 1 output | NO |
| **Subtotal** | **1-2** | | **0 parallelizable** |

Note: The deterministic gates (`skill-pipeline canonicalize/check/verify/coverage`) are Python CLI commands with zero LLM calls. They run in seconds.

### Stage 3: Enrich-Deal (Agent-driven, SKILL.md)

| Call Type | Count (stec) | Serial Dependency | Parallelizable |
|-----------|-------------|-------------------|----------------|
| Tasks 2-5 (deterministic, from enrich-core) | 0 LLM | N/A (Python CLI) | N/A |
| Task 1: Dropout classification | 5 (one per drop) | NO -- each drop is independent | YES |
| Task 6: Initiation judgment | 1 | NO -- reads first 10-15 blocks | YES (with task 1) |
| Task 7: Advisory verification | 2-8 (one per advisor) | NO -- each advisor is independent | YES |
| Task 8: Count reconciliation | 1 | NO -- reads roster + assertions | YES (with task 7) |
| **Subtotal** | **9-15** | | **9-15 all parallelizable** |

### Stage 4: Export-CSV (Agent-driven, SKILL.md)

| Call Type | Count (stec) | Serial Dependency | Parallelizable |
|-----------|-------------|-------------------|----------------|
| CSV generation | 1 | YES -- needs all enrichment | NO |
| **Subtotal** | **1** | | **0 parallelizable** |

### Full Pipeline Summary (stec)

| Category | Calls | Wall Time (sequential est.) | Parallelizable |
|----------|-------|---------------------------|----------------|
| Extract chunk passes | 7 | ~7-14 min | NO |
| Extract consolidation + re-reads | 1-6 | ~2-6 min | 0-5 of these |
| Verify-extraction repair | 1-2 | ~1-2 min | NO |
| Enrich-deal LLM tasks | 9-15 | ~5-15 min | ALL |
| Export-CSV | 1 | ~1-2 min | NO |
| Agent overhead (SKILL reading, file I/O, artifact writing) | N/A | ~15-25 min | N/A |
| **Total** | **~20-41** | **~30-64 min LLM + ~15-25 min overhead** | **~14-20 parallelizable** |

### Parallelization Impact Estimate

With the async executor parallelizing all independent calls:

| Scenario | Sequential | Parallel (5 concurrent) | Savings |
|----------|-----------|------------------------|---------|
| Enrich-deal (9-15 calls) | 9-15 min | 2-3 min | ~7-12 min |
| Consolidation re-reads (0-5 calls) | 0-5 min | 0-1 min | ~0-4 min |
| **Total savings** | | | **~7-16 min** |

Combined with agent overhead reduction (fewer sequential tool call round-trips), estimated total pipeline time for stec: **20-35 minutes** (down from ~80 minutes).

The remaining bottleneck is the 7 sequential chunk extraction passes (~7-14 min) and agent overhead (~10-15 min). Agent overhead cannot be eliminated without replacing the agent-driven model entirely.

## Anthropic API Rate Limits (Official, verified)

Source: [Anthropic Rate Limits](https://platform.claude.com/docs/en/api/rate-limits)

| Tier | RPM | ITPM (Sonnet 4.x) | OTPM (Sonnet 4.x) |
|------|-----|-------------------|-------------------|
| Tier 1 ($5 deposit) | 50 | 30,000 | 8,000 |
| Tier 2 ($40 deposit) | 1,000 | 450,000 | 90,000 |
| Tier 3 ($200 deposit) | 2,000 | 800,000 | 160,000 |
| Tier 4 ($400 deposit) | 4,000 | 2,000,000 | 400,000 |

**For this pipeline:** Even Tier 1 (50 RPM) supports 5 concurrent calls easily. At 5 concurrent requests with ~3-4K input tokens each, that is 15-20K ITPM -- well within Tier 1's 30K ITPM limit for Sonnet 4.x.

**Cached input tokens do NOT count toward ITPM** for Sonnet 4.x models. If the system prompt is cached across calls in a batch, effective throughput increases further.

**Recommendation:** Set `max_concurrent=5` as the default semaphore limit. This is conservative for Tier 1 and leaves headroom. Users on Tier 2+ can increase to 10-15.

### Anthropic Message Batches API

Source: [Batch Processing Docs](https://platform.claude.com/docs/en/build-with-claude/batch-processing)

| Property | Value |
|----------|-------|
| Max batch size | 100,000 requests or 256 MB |
| Processing time | Most finish <1 hour; max 24 hours |
| Cost savings | 50% of standard API prices |
| Result availability | 29 days after creation |

**Verdict: NOT suitable for this use case.** The pipeline needs interactive latency (results within seconds per call, not hours per batch). The Batch API is designed for offline bulk processing. The 50% cost savings are attractive but the latency guarantee (up to 24 hours) is incompatible with interactive deal processing.

**Future consideration:** If the pipeline later needs to process all 9 deals in bulk (non-interactive), the Batch API becomes relevant. But that is cross-deal parallelism, not single-deal parallelism.

## Common Pitfalls

### Pitfall 1: Agent Cannot Issue Parallel Calls

**What goes wrong:** SKILL.md instructions say "fire these 5 calls in parallel" but the Claude Code agent processes tool calls sequentially. No wall-clock speedup occurs.
**Why it happens:** The agent is a single-threaded conversation loop. Each tool call blocks until completion.
**How to avoid:** Move parallelization to Python infrastructure. The agent prepares prompts, invokes a single CLI command that runs them concurrently, and reads back results.
**Warning signs:** Pipeline timing unchanged after SKILL.md changes that claim parallelism.

### Pitfall 2: Rate Limit Exceeded on Concurrent Burst

**What goes wrong:** 15 concurrent API calls hit the RPM or ITPM limit, causing 429 errors.
**Why it happens:** No concurrency throttling.
**How to avoid:** Use `asyncio.Semaphore(max_concurrent)` with a conservative default (5). Fail fast on 429 rather than silent retry.
**Warning signs:** HTTP 429 responses in executor output.

### Pitfall 3: Partial Failure Silently Corrupts Results

**What goes wrong:** 4 of 5 concurrent calls succeed, 1 fails. The executor returns partial results. The SKILL.md agent writes incomplete enrichment.
**Why it happens:** `asyncio.gather()` with `return_exceptions=True` returns exceptions mixed with results. Code must check each result.
**How to avoid:** Fail fast on any exception. If one call fails, the entire batch fails. The agent retries the entire batch or reports the error.
**Warning signs:** Enrichment JSON missing entries for some events.

### Pitfall 4: Structured Output Parsing Across Concurrent Calls

**What goes wrong:** One of N concurrent calls returns malformed JSON. The executor silently drops it or crashes mid-batch.
**Why it happens:** LLM structured output is not guaranteed to be valid JSON 100% of the time.
**How to avoid:** Validate each response with Pydantic immediately after receipt, before returning the batch. Fail fast on validation errors.
**Warning signs:** Pydantic ValidationError in executor output.

### Pitfall 5: Agent Overhead Dominates After LLM Parallelization

**What goes wrong:** LLM calls are now fast (2-3 min total), but the agent still takes 20-30 minutes because it reads files, writes artifacts, and processes SKILL.md instructions sequentially.
**Why it happens:** The agent's own conversation turns (reading SKILL.md, reasoning about next steps, writing files) are not parallelizable.
**How to avoid:** Accept this as a floor. The agent overhead is ~15-25 minutes for a full pipeline. Parallelizing LLM calls reduces the LLM-bound time but not the agent-bound time. Document this expectation.
**Warning signs:** Pipeline time plateaus at ~25-30 minutes regardless of concurrency settings.

### Pitfall 6: Roster Carry-Forward Broken by Premature Parallelization

**What goes wrong:** Someone attempts to parallelize chunk extraction despite the serial dependency, producing duplicate or missing actors.
**Why it happens:** Chunk N-1's actors are needed before chunk N starts.
**How to avoid:** Mark chunk extraction as NON-PARALLELIZABLE in SKILL.md and the executor. Only re-reads and enrichment tasks are eligible.
**Warning signs:** Duplicate actors in actors_raw.json, missing actor references in events.

## Code Examples

### Parallel Executor CLI Entry Point

```python
# Source: project pattern from skill_pipeline/cli.py + asyncio stdlib
import asyncio
import json
import sys
from pathlib import Path

from skill_pipeline.parallel import run_parallel_prompts


def main_parallel_llm(input_path: str, output_path: str, *, max_concurrent: int = 5) -> int:
    """CLI wrapper: read prompts JSON, fire concurrently, write results JSON."""
    prompts = json.loads(Path(input_path).read_text())
    model = prompts.get("model", "claude-sonnet-4-20250514")
    max_tokens = prompts.get("max_tokens", 4096)
    requests = prompts["requests"]

    results = asyncio.run(
        run_parallel_prompts(
            requests,
            model=model,
            max_tokens=max_tokens,
            max_concurrent=max_concurrent,
        )
    )
    Path(output_path).write_text(json.dumps(results, indent=2))
    return 0
```

### Prompt Preparation for Dropout Classification

```python
# Source: enrich-deal SKILL.md task 1 specification
# The agent prepares this JSON; the executor fires the calls.
{
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 2048,
    "requests": [
        {
            "id": "dropout_evt_016",
            "system": "You are classifying a bidder dropout event...",
            "user": "Drop event context:\n[scoped blocks]\n\nClassify into: Drop, DropBelowM, DropBelowInf, DropAtInf, DropTarget.\nRespond with JSON: {\"label\": ..., \"basis\": ..., \"source_text\": ...}"
        },
        {
            "id": "dropout_evt_023",
            "system": "You are classifying a bidder dropout event...",
            "user": "Drop event context:\n[scoped blocks]\n..."
        }
    ]
}
```

### Response Schema Validation

```python
# Source: project pattern from skill_pipeline/models.py
from pydantic import BaseModel

class DropoutResult(BaseModel):
    label: str  # One of: Drop, DropBelowM, DropBelowInf, DropAtInf, DropTarget
    basis: str
    source_text: str

class AdvisoryResult(BaseModel):
    advised_actor_id: str | None
    verified: bool
    source_text: str

class ParallelBatchResponse(BaseModel):
    results: dict[str, str]  # prompt_id -> raw response text
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Sequential LLM calls via agent tool loop | Agent prepares batch, Python executor fires concurrently | This phase | ~50-70% reduction in LLM-bound time |
| Full-context enrichment prompts | Event-targeted re-reads with scoped blocks (Phase 6) | 2026-03-25 | ~60% token reduction per call already achieved |
| Single model for all calls | Single model still recommended | N/A | Model tiering deferred (accuracy risk, validation overhead) |

**Deprecated/outdated:**
- Anthropic SDK < 0.49: Older versions lacked stable `AsyncAnthropic`. The project already requires `>=0.49`.
- `threading` for API calls: While functional, `asyncio` is now the consensus approach for I/O-bound concurrent HTTP in Python 3.11+.

## Open Questions

1. **What is the user's current Anthropic API tier?**
   - What we know: Even Tier 1 supports 5 concurrent calls within limits.
   - What's unclear: The actual tier determines how aggressively we can parallelize (5 vs 15 concurrent).
   - Recommendation: Default to `max_concurrent=5`, make it configurable via environment variable `BIDS_MAX_CONCURRENT_LLM`.

2. **Should the executor support OpenAI as well?**
   - What we know: `BIDS_LLM_PROVIDER` supports `anthropic|openai`. The executor currently targets Anthropic only.
   - What's unclear: Whether OpenAI parallel calls are needed for this phase.
   - Recommendation: Build for Anthropic first. OpenAI support is a follow-up if needed (the pattern is identical -- `AsyncOpenAI` + `asyncio.gather()`).

3. **Exact agent overhead breakdown**
   - What we know: Agent overhead (SKILL reading, file I/O, reasoning) is ~15-25 minutes per full pipeline run.
   - What's unclear: How much of this is compressible vs fundamental.
   - Recommendation: Measure before and after. If overhead exceeds 30 minutes, the <30 min target may require converting some agent-driven stages to fully Python-driven stages (a larger architectural change).

4. **Whether `asyncio.run()` works correctly in the Claude Code agent's Python subprocess**
   - What we know: The agent invokes `skill-pipeline` via Bash. Python's `asyncio.run()` should work in a subprocess.
   - What's unclear: Whether the agent's shell environment has any event loop interference.
   - Recommendation: Test early. If `asyncio.run()` fails, fall back to `threading.Thread` + `concurrent.futures`.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >= 8.0 |
| Config file | `pytest.ini` |
| Quick run command | `pytest -q tests/test_skill_pipeline.py` |
| Full suite command | `pytest -q` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PAR-01 | Parallel executor fires N prompts concurrently | unit (mock API) | `pytest tests/test_parallel.py::test_concurrent_execution -x` | Wave 0 |
| PAR-02 | Semaphore limits concurrency to max_concurrent | unit (mock API) | `pytest tests/test_parallel.py::test_semaphore_limit -x` | Wave 0 |
| PAR-03 | Partial failure fails the entire batch | unit (mock API) | `pytest tests/test_parallel.py::test_fail_fast_on_error -x` | Wave 0 |
| PAR-04 | Response validation catches malformed JSON | unit | `pytest tests/test_parallel.py::test_response_validation -x` | Wave 0 |
| PAR-05 | CLI reads input JSON, writes output JSON | integration | `pytest tests/test_parallel.py::test_cli_roundtrip -x` | Wave 0 |
| PAR-06 | Enrichment results match sequential execution | integration (live API) | Manual -- compare enrichment.json | Manual only |
| PAR-07 | Existing tests still pass after changes | regression | `pytest -q` | Existing |

### Sampling Rate

- **Per task commit:** `pytest -q tests/test_parallel.py`
- **Per wave merge:** `pytest -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_parallel.py` -- covers PAR-01 through PAR-05
- [ ] `tests/conftest.py` additions -- mock `AsyncAnthropic` fixture for unit tests without live API calls

## Sources

### Primary (HIGH confidence)

- [Anthropic Rate Limits](https://platform.claude.com/docs/en/api/rate-limits) - Tier-based RPM/ITPM/OTPM limits, cache-aware ITPM
- [Anthropic Batch Processing](https://platform.claude.com/docs/en/build-with-claude/batch-processing) - Message Batches API latency, pricing, limitations
- [Claude Code Subagents](https://code.claude.com/docs/en/sub-agents) - Agent parallelism capabilities and limitations
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python) - `AsyncAnthropic` async client

### Secondary (MEDIUM confidence)

- [Asynchronous LLM API Calls Guide](https://www.unite.ai/asynchronous-llm-api-calls-in-python-a-comprehensive-guide/) - `asyncio.gather()` pattern for parallel API calls
- [Claude Code Async Workflows](https://claudefa.st/blog/guide/agents/async-workflows) - Background agent and parallel task patterns

### Tertiary (LOW confidence)

- Agent overhead timing estimates (15-25 minutes) -- based on the existing research doc's rough estimates and stec pipeline observations, not rigorous benchmarking

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - `anthropic` SDK with `AsyncAnthropic` is well-documented, already a dependency
- Architecture: HIGH - The "agent prepares prompts, executor fires concurrently, agent reads results" pattern is well-established
- Rate limits: HIGH - Verified against official Anthropic docs (March 2026)
- Call inventory: HIGH - Derived from actual stec artifacts (7 chunks, 5 drops, 2 advisors, 1 count assertion)
- Agent overhead estimate: LOW - Based on rough observation, not measured
- Pitfalls: MEDIUM - Derived from community patterns and first-principles analysis

**Research date:** 2026-03-25
**Valid until:** 2026-04-25 (rate limits and SDK patterns are stable; agent capabilities may evolve faster)
