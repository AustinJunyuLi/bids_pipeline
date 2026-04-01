# Filing-Grounded Deal Pipeline Redesign

## What This Is

Brownfield redesign of an SEC deal-extraction pipeline so raw filing text is
the primary input and the live output is a filing-grounded v2 observation graph
plus derived analyst rows and benchmark-facing exports.

The repository now has a clean live surface:

- live v2 work under `data/skill/<slug>/`
- retired v1 recovery through tag `v1-working-tree-2026-04-01` plus milestone archives

## Core Value

Produce the most correct filing-grounded structured deal record possible from
raw text, even when that requires more validation, stricter boundaries, and
clean separation between literal facts and analyst-derived rows.

## Requirements

### Validated

- ✓ Seed-based raw filing fetch and immutable filing freeze
- ✓ Filing preprocessing into chronology blocks and evidence items
- ✓ Quote-first v2 observation extraction contract
- ✓ Canonical span-backed v2 observations
- ✓ Deterministic v2 validation stack (`check-v2`, `coverage-v2`, `gates-v2`)
- ✓ Deterministic derivation of analyst rows from observations
- ✓ DuckDB-backed v2 load/export surface
- ✓ Live v2 default skill/docs cutover with archived v1 outputs
- ✓ Chronology-safe proposal linkage and proposal-local bid-type inference — v2.2
- ✓ Stronger elimination-date and bidder-scoped outcome derivation — v2.2
- ✓ Analyst/export surface repairs for agreement taxonomy, date precision, and enterprise value — v2.2
- ✓ Stronger v2 prompt, skill, and gate contract using the 2026-04-01 GPT Pro diagnosis as post-export planning input — v2.2
- ✓ Working-tree v1 retirement with Git-history recovery preserved through a tagged pre-retirement commit — v2.2

### Active

None currently defined. The next milestone has not been planned yet.

### Out of Scope

- benchmark-driven generation logic
- UI or product surface work unrelated to the extraction pipeline
- reintroducing a live v1 runtime surface into the working tree

## Context

This repository is centered on the `skill_pipeline` package and canonical
`.claude/skills/` workflow docs, with `.codex/skills/` and `.cursor/skills/`
maintained as mirrors. The live default is the v2 observation-graph pipeline:

`raw-fetch -> preprocess-source -> compose-prompts(v2) -> extract-deal-v2 ->
canonicalize-v2 -> check-v2 -> coverage-v2 -> gates-v2 -> verify-extraction-v2
-> derive -> db-load-v2 -> db-export-v2`

The 9 active deals are:

- imprivata
- mac-gray
- medivation
- penford
- petsmart-inc
- providence-worcester
- saks
- stec
- zep

## Latest Completed Milestone

### v2.2 Reconciliation Lift + Surface Repair

**Goal:** convert the 2026-04-01 GPT Pro diagnosis into filing-grounded
deterministic fixes that raise reconciliation quality without weakening the
post-export benchmark boundary.

**Target features:**

- chronology-safe proposal phase association and proposal-local bid-type inference
- better drop-date and outcome derivation with bidder-scoped actors
- analyst-comparable agreement/process/export surfaces, including date precision
  and enterprise value
- extraction-contract and v2-gate hardening to stop the same errors from
  reappearing

## Current State

**v1.0 shipped 2026-03-28. v1.1 completed 2026-03-30. v2.0 shipped 2026-03-31.
v2.1 cutover completed 2026-03-31. v2.2 completed and audited 2026-04-01.**

That milestone was anchored to
`diagnosis/gptpro/2026-04-01/round_1/v2_analytical_gap_inventory_3aa65f7.md`
and targeted the highest-value deterministic gaps first:

- proposal linkage and bid-type errors
- synthetic drop dating and outcome normalization
- agreement/process taxonomy and export-surface fidelity
- prompt, skill, and gate hardening for solicitation recipients and
  chronology-safe links
- retirement of the last live v1 working-tree surface after recoverability was
  pinned in Git history

All 16 mapped v2.2 requirements passed phase verification. The recovery anchor
for the last pre-retirement tree is tag `v1-working-tree-2026-04-01` at commit
`82a4966`.

The live repo surface remains intentionally slim:

- `CLAUDE.md` and `docs/design.md` describe only the live v2 default and the
  Git-history recovery path for retired v1
- `.planning/milestones/` stores archived milestone detail and milestone audits
- `/deal-agent` is the live clean-rerun orchestration skill

## Constraints

- **Source of truth**: filing text is the only factual source
- **Benchmark boundary**: benchmark materials are forbidden before
  `skill-pipeline db-export-v2 --deal <slug>` completes in the live workflow
- **Project shape**: brownfield redesign inside the current repository
- **Runtime split**: `skill_pipeline` stays deterministic; LLM-facing steps live in skill docs
- **Traceability**: outputs must remain evidence-linked and auditable

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Make v2 the live default | The observation graph is the shipped architecture; mixed live defaults would keep the repo confusing | ✓ Adopted |
| Preserve v1 only in Git history and milestone archives | Users still need historical recovery, but it should not pollute the live working tree | ✓ Adopted |
| Retire `data/legacy/v1/` from the working tree after tagging the last pre-retirement commit | Keeps the repo clean while leaving a visible recovery anchor on GitHub | ✓ Adopted |
| Rebuild live DuckDB from v2 only | Another agent should not face mixed v1/v2 database state during reconciliation or reruns | ✓ Adopted |
| Remove `migrate-extract-v1-to-v2` and other legacy runtime shims once v2 is self-contained | Migration helpers were no longer part of the live contract after cutover | ✓ Retired on 2026-04-01 |
| Treat the 2026-04-01 GPT Pro diagnosis as post-export planning input only | lets the team prioritize deterministic fixes without turning benchmark notes into hidden generation requirements | ✓ Adopted |

---
*Last updated: 2026-04-01 after completing and auditing v2.2, including Phase 24 v1 retirement*
