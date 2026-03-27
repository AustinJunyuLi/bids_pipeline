# Phase 2: Prompt Architecture - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-27
**Phase:** 02-prompt-architecture
**Areas discussed:** prompt engine boundary, packet layout, chunking and overlap, evidence and few-shot packaging

---

## Prompt Engine Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Deterministic engine in `skill_pipeline`, provider calls stay in `.claude/skills/` | Compose provider-neutral prompt artifacts in Python, keep model invocation outside Python | ✓ |
| Compose prompts ad hoc inside `/extract-deal` only | No persisted packet artifacts; skill text owns everything | |
| Hybrid helper layer with no stable artifact contract | Some code assistance, but prompt packets are not first-class outputs | |

**User's choice:** Auto-selected recommended default: deterministic engine in `skill_pipeline`, provider calls remain in `.claude/skills/`.
**Notes:** `[auto]` Selected because it satisfies INFRA-01, INFRA-02, and the Phase 1 no-wrapper constraint while keeping prompt composition testable.

---

## Packet Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Data-first packet with stable prefix + chunk-specific body | Chronology blocks first, instructions last, reusable prefix separated from variable body | ✓ |
| Single rendered prompt blob | One combined string with no reusable prefix boundary | |
| Instruction-first conventional prompt | Instructions at top, chronology later | |

**User's choice:** Auto-selected recommended default: data-first packet with stable prefix and chunk-specific body.
**Notes:** `[auto]` Selected because PROMPT-01 and INFRA-03 explicitly call for chronology-first ordering and reusable stable context.

---

## Chunking And Overlap

| Option | Description | Selected |
|--------|-------------|----------|
| One deterministic contract supporting single-pass and chunked modes | Whole-block chunking, explicit 2-block overlap, caller chooses mode | ✓ |
| Chunked-only architecture | Always chunk, even for simple deals | |
| Single-pass-only for now | Delay chunk contract until a later phase | |

**User's choice:** Auto-selected recommended default: one deterministic contract supporting both single-pass and chunked modes.
**Notes:** `[auto]` Selected because Phase 2 scope requires chunk construction and overlap, but final complexity-routing policy is deferred to Phase 5.

---

## Evidence And Few-Shot Packaging

| Option | Description | Selected |
|--------|-------------|----------|
| Active checklist + provider-neutral prompt assets | Render concise evidence checklist, optional actor roster, file-backed few-shots | ✓ |
| Raw appendix dump | Include evidence items as an unstructured appendix | |
| Keep few-shots and checklist manual in the skill only | No deterministic prompt-asset layer | |

**User's choice:** Auto-selected recommended default: active checklist plus provider-neutral prompt assets.
**Notes:** `[auto]` Selected because PROMPT-04 and INFRA-05 require deterministic composition of evidence checklist, actor roster, and examples.

---

## the agent's Discretion

- Exact prompt packet filenames and manifest schema
- Exact token-budget estimator and chunk sizing heuristic
- Exact location of reusable prompt asset files, provided they stay provider-neutral and versioned

## Deferred Ideas

- Complexity auto-routing thresholds belong to Phase 5
- Quote-before-extract protocol belongs to Phase 3
- Seed-quality hardening remains a separate Claude todo outside Phase 2
