# Phase 1: Foundation + Annotation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-27
**Phase:** 01-foundation-annotation
**Areas discussed:** SDK + structured outputs, Block metadata design, Annotation integration, Backward compatibility, Restructure requirements, Testing strategy

---

## SDK + Structured Outputs

| Option | Description | Selected |
|--------|-------------|----------|
| Bump versions only | Update pyproject.toml. No Python LLM wrapper. Skills handle LLM interaction. | |
| Build Python LLM layer | Create skill_pipeline/llm/ module wrapping Anthropic + OpenAI calls. | |
| You decide | Claude picks based on project trajectory | |

**User's choice:** Free text — "in this pipeline we have no intention to use python llm wrapper. this is very confusing. so we need to get rid of the discuss of python llm wrapper recordings in claude.md"
**Notes:** Hard constraint. All LLM calls remain in .claude/skills/ markdown. The skill_pipeline package stays deterministic. INFRA-01/02 move to Phase 2 as skill-level changes.

---

## Block Metadata - Date Mentions

| Option | Description | Selected |
|--------|-------------|----------|
| Raw date strings | Just extract date-like text patterns from the block | |
| Parsed dates | Extract AND parse into normalized form, reusing dates.py | ✓ |
| You decide | Claude picks based on downstream needs | |

**User's choice:** Asked for recommendation, accepted parsed dates.
**Notes:** Downstream prompt composition needs normalized dates for temporal ordering.

---

## Block Metadata - Entity Mentions

| Option | Description | Selected |
|--------|-------------|----------|
| Seed-based matching | Match company names from seeds.csv + Party A/B/C patterns | ✓ |
| Evidence-derived | Cross-reference with evidence_items.jsonl actor_hint field | |
| You decide | Claude picks | |

**User's choice:** Seed-based matching
**Notes:** Minimal regex, no NLP.

---

## Block Metadata - Temporal Phase

| Option | Description | Selected |
|--------|-------------|----------|
| Position-based | First 20% = initiation, middle 60% = bidding, last 20% = closing | |
| Content-signal-based | Use evidence cue types to infer phase | |
| You decide | Claude picks best signal-to-complexity ratio | ✓ |

**User's choice:** You decide
**Notes:** Claude selected hybrid: content-signal primary, position fallback.

---

## Annotation Integration

| Option | Description | Selected |
|--------|-------------|----------|
| Extend preprocess-source | Add annotation as final step inside existing command | ✓ |
| New annotate subcommand | Separate skill-pipeline annotate command | |
| You decide | Claude picks based on dependency structure | |

**User's choice:** You decide
**Notes:** Claude selected extend preprocess-source. Annotation depends on both blocks and evidence, always runs together.

---

## Backward Compatibility (explored in second round)

**Option explored:** New metadata fields optional on ChronologyBlock (default None/empty).
**Final outcome:** Rejected by the final phase context. `01-CONTEXT.md` is authoritative: metadata fields are required and stale blocks fail on load.

## Restructure Requirements (explored in second round)

**Decision:** INFRA-01/02 move to Phase 2. Phase 1 = INFRA-04 (block metadata) + INFRA-06 (deterministic runtime/doc hardening) + cleanup.

## Testing Strategy (explored in second round)

**Decision:** Unit tests per annotation function + stec regression test.

---

## Claude's Discretion

- Exact regex patterns for entity matching beyond seeds
- Internal data structure for parsed date mentions
- Evidence density counting logic
- Position-based fallback thresholds for temporal phase

## Deferred Ideas

- Schema-constrained external extraction flows (INFRA-01, INFRA-02) — moved to Phase 2
- Cleanup of misleading provider-mode references — Phase 1 or 2
