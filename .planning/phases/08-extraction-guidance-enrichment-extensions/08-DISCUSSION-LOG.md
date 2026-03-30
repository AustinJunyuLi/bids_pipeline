# Phase 8: Extraction Guidance + Enrichment Extensions - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution
> agents. Decisions are captured in `08-CONTEXT.md`.

**Date:** 2026-03-30
**Phase:** 08-extraction-guidance-enrichment-extensions
**Areas discussed:** skill-doc scope, deterministic dropout contract,
contextual all-cash boundary

---

## Skill-Doc Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Canonical `.claude` doc update | Update `.claude/skills/extract-deal/SKILL.md` and sync mirrors; keep changes in the existing extraction contract | ✓ |
| Mirror-first edits | Edit `.codex` / `.cursor` skill copies directly | |
| Schema expansion now | Add new extraction fields or event types together with the doc update | |

**User's choice:** Auto-selected canonical `.claude` doc update path during
`$gsd-next` continuation.
**Notes:** Phase 8 is scoped to better guidance, not a new extraction schema.
Existing round event types and formality signals already cover the target
patterns.

---

## Deterministic Dropout Contract

| Option | Description | Selected |
|--------|-------------|----------|
| Sparse deterministic `DropTarget` only | Add filing-grounded `DropTarget` rows to deterministic enrichment; leave other drop events on the existing generic `Drop` fallback | ✓ |
| Full deterministic dropout taxonomy | Implement `Drop`, `DropBelowM`, `DropBelowInf`, `DropAtInf`, and `DropTarget` in `enrich_core.py` | |
| Keep dropout fully interpretive | Leave all dropout labels in `enrichment.json` only | |

**User's choice:** Auto-selected sparse deterministic `DropTarget` contract.
**Notes:** This matches the explicit ENRICH-02 requirement while avoiding scope
creep into the richer interpretive dropout taxonomy that
`.claude/skills/enrich-deal/SKILL.md` already owns.

---

## Contextual All-Cash Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit enrichment override | Keep extract literals unchanged; add a deterministic override path consumed by DB load/export when cash treatment is unambiguous | ✓ |
| Rewrite event terms | Backfill `terms.consideration_type` directly in extracted/canonical events | |
| Deal-wide heuristic | Mark all proposals cash whenever the signed deal is cash | |

**User's choice:** Auto-selected explicit enrichment override with cycle-local,
fail-closed inference.
**Notes:** This preserves filing-literal extraction and avoids false positives
for mixed/CVR deals such as Providence & Worcester.

---

## the agent's Discretion

- Exact deterministic field name for the `all_cash` override
- Exact selection and wording of round-milestone / oral-bid examples in the
  extraction skill docs
- Exact precedence between round invitation deltas and explicit
  `drop_reason_text` when both support `DropTarget`

## Deferred Ideas

- `nda_subtype` schema expansion across runtime stages
- Full deterministic dropout taxonomy beyond `DropTarget`
- Phase 9 reruns and reconciliation measurement
