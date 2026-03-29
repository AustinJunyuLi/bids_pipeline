# Phase 6: Deterministic Hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 06-deterministic-hardening
**Areas discussed:** Rollover CA tolerance, Quote_id renumbering, Mixed-schema guard, DuckDB retry boundary

**Pre-discussion:** Second Brain evaluation (Claude + GPT-5.4 xhigh) identified HARD-02 and HARD-03 as already satisfied, reduced open scope from 6 to 4 requirements.

---

## Rollover CA Tolerance (HARD-04)

| Option | Description | Selected |
|--------|-------------|----------|
| Text-pattern exclusion | Expand phrase lists in coverage.py and gates.py to recognize rollover/teaming/diligence language | |
| NDA subtype in extraction | Add nda_subtype field to extraction schema. More precise but requires schema change + re-extraction | |
| Gates-only suppression | Only fix gates warnings. Leaves coverage false positives unfixed | |

**User's initial choice:** NDA subtype in extraction
**Follow-up:** Asked about phasing since NDA subtype requires extraction schema changes and re-extraction.

| Option | Description | Selected |
|--------|-------------|----------|
| Split: text-pattern now + subtype later | Phase 6 ships text-pattern exclusion. Phase 8 adds nda_subtype. Phase 9 re-extracts. | ✓ |
| All in Phase 6 | Full fix in one phase. Larger scope. | |
| Defer entirely to Phase 8/9 | Accept false positives until then. | |

**User's choice:** Split approach — text-pattern now, subtype later
**Notes:** User preferred the precise NDA subtype approach long-term but agreed to split across phases for progressive improvement.

---

## Quote_id Renumbering (HARD-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Always renumber (defensive) | Event-side quote_ids always renumbered above actor-side max. Deterministic, idempotent. | ✓ |
| Only on collision | Check for overlap first, renumber only if needed. Preserves original IDs. | |

**User's choice:** Always renumber

| Option | Description | Selected |
|--------|-------------|----------|
| Log in canonicalize_log.json | Append renumber mapping to existing log artifact. Traceable. | ✓ |
| No logging | Renumber silently. | |

**User's choice:** Log in canonicalize_log.json

---

## Mixed-Schema Guard (HARD-06)

| Option | Description | Selected |
|--------|-------------|----------|
| In the shared loader | Add check in load_extract_artifacts(). One fix protects all downstream stages. | ✓ |
| In each consuming stage | Each stage validates independently. Duplicated logic. | |

**User's choice:** Shared loader

---

## DuckDB Retry Boundary (HARD-05)

| Option | Description | Selected |
|--------|-------------|----------|
| In open_pipeline_db() | Retry at connection level. Any caller gets automatic retry. Single implementation. | ✓ |
| In db-export call site only | Only db-export retries. Narrower scope. | |

**User's choice:** open_pipeline_db() with 3 retries, exponential backoff, lock-specific exceptions only

---

## Claude's Discretion

- Exact text patterns for rollover/teaming/diligence CA recognition
- MixedSchemaError class placement
- Exact DuckDB exception class for lock errors
- Internal organization of renumbering logic

## Deferred Ideas

- nda_subtype extraction schema field — Phase 8
- Per-deal artifact locking for concurrent write prevention — orchestration concern
