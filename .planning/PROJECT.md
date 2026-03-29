# Filing-Grounded Deal Pipeline Redesign

## What This Is

Brownfield redesign of an SEC deal-extraction pipeline so raw filing text
becomes the primary input and the system produces filing-grounded structured
deal data in a database plus review/export CSV. The existing repository already
has deterministic fetch, preprocessing, canonicalization, QA, and enrichment
stages, plus local-agent extraction, repair, and export workflows. This project
strengthens correctness and unifies those artifact contracts into a cleaner
end-to-end pipeline.

## Core Value

Produce the most correct filing-grounded structured deal record possible from
raw text, even if that requires more computation, more verification, or a more
elaborate extraction architecture.

## Requirements

### Validated

- ✓ Seed-based raw filing fetch and immutable filing freeze — existing
  `raw-fetch` stage
- ✓ Filing preprocessing into chronology blocks and evidence items — existing
  `preprocess-source` stage
- ✓ Two-pass local-agent extraction (actors then events with gap re-read) —
  existing `/extract-deal` skill
- ✓ Raw-to-canonical schema upgrade with span resolution — existing
  `canonicalize` stage
- ✓ Deterministic structural, verification, coverage, and enrichment gates —
  existing `check`, `verify`, `coverage`, `enrich-core` stages
- ✓ CSV-style review export — now `skill-pipeline db-export` (deterministic)
- ✓ Reasoning-enabled extraction in local-agent workflows — confirmed
  operational
- ✓ Pydantic schema-first artifact design with fail-fast validation — existing
  `models.py`
- ✓ No Python LLM wrapper in the live architecture — extraction, repair,
  interpretive enrichment, and export remain outside `skill_pipeline`
- ✓ Canonical local-agent workflow docs under `.claude/skills/` — current repo
  contract
- ✓ Quote-before-extract protocol forces evidence citation before structured
  extraction — validated in Phase 3
- ✓ Enhanced deterministic gates: temporal consistency, cross-event logic,
  per-actor coverage, attention decay diagnostics — validated in Phase 4
- ✓ Raw filing text now flows through one documented local-agent
  orchestration contract into DuckDB-backed structured outputs plus review CSV
  — validated in Phase 5
- ✓ Complexity-based routing (single-pass for simple deals, multi-pass for
  complex) — validated in Phase 5
- ✓ Expanded few-shot examples covering NDA groups, ambiguous drops, cycle
  boundaries, range proposals, and formal-round signals — validated in Phase 5
- ✓ Database output and deterministic CSV export now derive from one canonical
  DuckDB representation — validated in Phase 5
- ✓ Block-level metadata enrichment (dates, entities, evidence density,
  temporal phase) in preprocessing — validated in Phase 1
- ✓ Prompt ordering restructured for cognitive bias exploitation (chronology
  first, instructions last) — validated in Phase 2
- ✓ 2-block overlap with explicit XML context tags in chunked extraction —
  validated in Phase 2
- ✓ Evidence items promoted from passive appendix to active
  attention-steering checklist — validated in Phase 2
- ✓ Block-aligned semantic chunk boundaries (never split mid-block) —
  validated in Phase 2
- ✓ Reusable static prompt prefix separated from chunk-specific content —
  validated in Phase 2
- ✓ Every extracted actor, event, term, and classification traceable to
  verbatim filing evidence — validated in Phase 3

### Active

(No active requirements — next milestone defines new scope via `/gsd:new-milestone`)

### Out of Scope

- Benchmark-driven generation logic — benchmark materials remain post-export
  diagnostics only
- Speed-first or cost-first shortcuts that reduce filing-grounded correctness —
  correctness is the project priority
- UI or product surface work unrelated to the extraction pipeline — backend and
  data-pipeline focused
- RAG as primary architecture — assessed and rejected; retrieval is
  fundamentally mismatched with exhaustive extraction from single documents that
  fit in context
- Graph RAG or Agentic RAG as pipeline backbone — assessed; overkill for a
  9-deal batch corpus
- Context compression or summarization of filing text — legally precise
  language where lossy compression risks anchor text corruption

## Context

This repository is a brownfield Python project centered on the `skill_pipeline`
package (installed via `pyproject.toml` as the `skill-pipeline` CLI). It
already contains raw fetch, source preprocessing, canonicalization,
deterministic QA gates, deterministic enrichment, and CSV export, plus
skill-driven extraction and enrichment steps. The 9 active deals are:
imprivata, mac-gray, medivation, penford, petsmart-inc,
providence-worcester, saks, stec, zep. Only `stec` has complete pipeline
artifacts (raw through export) as baseline.

The main technical uncertainty is context management inside long filings. The
active research packet is split across `.planning/research/SUMMARY.md`,
`.planning/research/ARCHITECTURE.md`, `.planning/research/PITFALLS.md`, and
`.planning/research/STACK.md`. Those documents explain the rationale, but
`.planning/ROADMAP.md` plus the current phase context file are the execution
authority for what is actually in scope.

Phases 1-5 are now complete: deterministic block metadata, prompt packet
composition, quote-before-extract grounding, enhanced semantic gates,
complexity-based routing, and DuckDB-backed integration/export all ship in the
live repository. The extraction stage remains the only non-deterministic
component. All quality originates there. The deterministic gates (`check`,
`verify`, `coverage`, `gates`) catch errors after the fact, and the new
`db-load`/`db-export` stages provide the canonical deterministic storage and
export surface. A full deterministic 9-deal DB rerun still depends on upstream
canonical extract plus deterministic enrichment artifacts for eight active
deals.

## Current State

**v1.0 shipped 2026-03-28.** The live runtime includes 12 deterministic CLI
stages (`source-discover`, `raw-fetch`, `preprocess-source`, `compose-prompts`,
`canonicalize`, `check`, `verify`, `coverage`, `gates`, `enrich-core`,
`db-load`, `db-export`) plus 4 local-agent skills (`extract-deal`,
`verify-extraction`, `enrich-deal`). 8,967 LOC in
`skill_pipeline/`, 9,074 LOC in tests (265 passing). stec validated
end-to-end through DuckDB export. 8 other deals await upstream extraction.

## Constraints

- **Source of truth**: Filing text is the only factual source — benchmark
  spreadsheets and diagnostic files cannot define generation behavior
- **Project shape**: Brownfield redesign inside the current repository —
  preserve and learn from existing pipeline stages rather than greenfield
- **Priority**: Correctness over automation speed, token cost, or novelty —
  tradeoffs favor more reliable outputs
- **Traceability**: Outputs must remain evidence-linked and auditable — every
  record maps back to filing text
- **Runtime split**: `skill_pipeline` stays deterministic; extraction, repair,
  interpretive enrichment, and export remain local-agent stages rather than
  Python provider wrappers
- **Agent/provider agnosticism**: Planning and repo-truth docs must not depend
  on a specific LLM vendor, API, or SDK contract
- **Python target**: 3.11+ with 4-space indentation, type hints on public
  functions, Pydantic-first schemas
- **Benchmark separation**: Benchmark materials forbidden until
  `skill-pipeline db-export` completes

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| RAG rejected as primary architecture | Extraction requires exhaustive recall, not selective retrieval; documents fit in context; RAG adds retrieval failure modes | ✓ Good |
| Correctness over speed/cost | User explicitly prioritized correctness; tradeoffs favor more reliable outputs | ✓ Good |
| Prompt ordering is highest-ROI zero-cost change | Data-first chronology packets improve long-document attention handling at effectively zero deterministic cost | ✓ Adopted |
| Quote-before-extract is most impactful structural change | Prevents hallucinated anchor text, the failure mode verify catches most often | ✓ Adopted |
| Semantic gates run as a dedicated deterministic stage after coverage | Keeps structural and semantic validation separate while giving enrich-core a single fail-fast semantic prerequisite | ✓ Adopted |
| Keep local-agent orchestration outside `skill_pipeline` | Live code has no Python LLM wrapper, and canonical skill docs already own extraction/repair/export | ✓ Adopted |
| DuckDB as canonical structured store | Embedded, zero-config, native array/JSON types, COPY TO CSV; replaces JSON artifact export | ✓ Adopted |
| Block-count-only complexity routing | 150-block threshold cleanly separates 6 simple / 3 complex deals; actor count redundant for corpus | ✓ Adopted |
| Drop-and-reload per deal in DuckDB | Simpler and safer than upsert for full-deal artifact reloads | ✓ Adopted |
| Hybrid retrieval only for targeted recovery | If coverage finds gaps, lightweight BM25 could narrow recovery context. Implement context/attention improvements first. | — Deferred to v2 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? Move to Out of Scope with reason
2. Requirements validated? Move to Validated with phase reference
3. New requirements emerged? Add to Active
4. Decisions to log? Add to Key Decisions
5. "What This Is" still accurate? Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-28 after v1.0 milestone completion*
