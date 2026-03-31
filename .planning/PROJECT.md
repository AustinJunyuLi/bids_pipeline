# Filing-Grounded Deal Pipeline Redesign

## What This Is

Brownfield redesign of an SEC deal-extraction pipeline so raw filing text is
the primary input and the live output is a filing-grounded v2 observation graph
plus derived analyst rows and benchmark-facing exports.

The repository now has a clean split:

- live v2 work under `data/skill/<slug>/`
- archived v1 work under `data/legacy/v1/`

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

### Active

None. The next milestone is not yet defined.

### Out of Scope

- benchmark-driven generation logic
- UI or product surface work unrelated to the extraction pipeline
- removal of preserved legacy runtime code without an explicit follow-up milestone

## Context

This repository is centered on the `skill_pipeline` package and canonical
`.claude/skills/` workflow docs. The live default is the v2 observation-graph
pipeline:

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

## Current Milestone

### v2.1 V2 Default Cutover + Legacy Archive

**Outcome:** complete on 2026-03-31

The repository now presents v2 as the live default, preserves v1 only behind
explicit legacy skill names, stores retired v1 outputs under `data/legacy/v1/`,
and rebuilds the live DuckDB file from v2 artifacts only.

## Current State

**v1.0 shipped 2026-03-28. v1.1 completed 2026-03-30. v2.0 shipped 2026-03-31.
v2.1 cutover completed 2026-03-31.**

The live repo surface is now intentionally slim:

- `CLAUDE.md` and `docs/design.md` describe only the live v2 default and the
  explicit legacy split
- `.planning/milestones/` stores archived v1.0 and v2.0 milestone detail
- `/deal-agent` is the live clean-rerun orchestration skill
- `/deal-agent-legacy` preserves the old v1 event-first flow

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
| Preserve v1 only under explicit legacy names | Users still need historical reference paths, but they should not pollute the live surface | ✓ Adopted |
| Archive v1 artifacts under `data/legacy/v1/` | Keeps historical results available while preventing accidental reuse during live v2 work | ✓ Adopted |
| Rebuild live DuckDB from v2 only | Another agent should not face mixed v1/v2 database state during reconciliation or reruns | ✓ Adopted |
| Keep `migrate-extract-v1-to-v2` as historical support only | Useful for backfill provenance, but it is not the live extraction contract | ✓ Adopted |

---
*Last updated: 2026-03-31 after v2 default cutover*
