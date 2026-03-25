# Phase 2: Deterministic Stage Interfaces - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-25
**Phase:** 02-deterministic-stage-interfaces
**Areas discussed:** extraction routing strategy

---

## Extraction Routing Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Keep strict full-context actor + event extraction | Preserve the current conceptual two-pass flow and feed the full chronology to both passes. Lowest orchestration complexity, but attention risk grows on complex deals. | |
| User proposal: chunk-first unified extraction | Read smaller chronology chunks, extract from each chunk, then do one full scan over everything again. Reduces per-call context load, but increases actor alias drift, duplicate event risk, and merge complexity. | |
| Recommended default: hybrid routing | Keep full-context actor extraction, run chunked event extraction only for complex deals, then do a final full-chronology recovery or audit pass. Preserves global actor context while controlling event-pass attention load. | ✓ |

**User's prompt:** "Look at the preprocessed blocks as well as the later extraction phase... provide pros and cons for this strategy."

**Notes:**
- The current preprocessed chronology blocks are already paragraph-like and reasonably sized; the attention risk comes from the total block count on complex deals, not from oversized individual blocks.
- Historical prompt design in `docs/plans/2026-03-16-prompt-engineering-spec.md` already recommended the same hybrid split for complex deals.
- Evidence items are numerous enough to work better as recovery or retrieval hints than as a second full prompt payload.

## the agent's Discretion

- Exact complexity thresholds for routing
- Exact overlap and merge rules for chunked event mode

## Deferred Ideas

- Replace chronology-first reading with a fully retrieval-driven extraction workflow
- Expand the extraction workflow beyond the current seed-only single-document boundary
