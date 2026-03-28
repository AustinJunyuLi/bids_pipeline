# Phase 3: Quote-Before-Extract - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-28
**Phase:** 03-quote-before-extract
**Areas discussed:** response format, format compatibility, downstream updates

---

## Response Format

| Option | Description | Selected |
|--------|-------------|----------|
| Separate quotes block | LLM emits numbered quotes array with verbatim text + block_id, then structured events referencing quote IDs. Clean separation of evidence from interpretation. | ✓ |
| Inline but quoted first | Keep current evidence_refs structure but add task instruction requiring quotes before JSON. Simpler but quotes aren't machine-linkable. | |

**User's choice:** Separate quotes block — single JSON response with top-level `quotes` array followed by `actors`/`events`.
**Notes:** User also chose single JSON over two-step sequential (one response vs two LLM calls).

---

## Format Compatibility

| Option | Description | Selected |
|--------|-------------|----------|
| New format only | Commit to quote-first format. Re-extract stec and medivation. No dual-path code. Old extractions become stale. | ✓ |
| Dual format support | Canonicalize and verify detect and handle both formats. More code, format ambiguity risk. | |
| New format + adapter | Migration script converts old evidence_refs to quotes. No dual runtime but requires conversion step. | |

**User's choice:** New format only — clean break, old code paths removed.
**Notes:** Stec and medivation must be re-extracted before exit criteria validation.

---

## Downstream Updates

| Option | Description | Selected |
|--------|-------------|----------|
| Full quote-aware pipeline | Canonicalize maps quotes to spans directly. Verify validates quotes first, then checks quote_id references. Richer validation chain. | ✓ |
| Thin adapter only | Convert quote_ids to evidence_refs internally, run same span resolution. Minimal code change but misses richer validation. | |

**User's choice:** Full quote-aware pipeline — canonicalize and verify both rewritten for native quote consumption.
**Notes:** Expected outcome is higher EXACT match rates in verify.

---

## Claude's Discretion

- Exact JSON schema field names for quote-first response
- Whether to keep evidence_refs as deprecated alias or remove immediately
- Internal refactoring approach for canonicalize
- How prompt assets communicate the quote-first requirement

## Deferred Ideas

- Chunk-budget overhead (Phase 5)
- Complexity routing (Phase 5)
- Few-shot expansion (Phase 5)
