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
- ✓ Shared extract loading now rejects mixed actor/event schema modes before
  downstream processing — validated in Phase 6
- ✓ Canonicalize now renumbers cross-array quote IDs deterministically while
  preserving same-array fail-fast duplicate checks — validated in Phase 6
- ✓ Coverage and gates now suppress non-sale NDA false positives without
  weakening real sale-process NDA detection — validated in Phase 6
- ✓ DuckDB connection handling now retries transient file-lock contention in
  the shared DB helper with bounded backoff — validated in Phase 6
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
- ✓ bid_type classification evaluates process position before IOI language so
  final-round proposals are correctly classified as Formal — validated in
  Phase 7
- ✓ extract-deal guidance now explicitly covers round milestones, verbal/oral
  priced proposals, and NDA exclusions for non-sale-process agreements —
  validated in Phase 8
- ✓ deterministic enrichment now emits sparse `DropTarget` labels and
  cycle-local `all_cash` overrides without mutating canonical extract
  artifacts — validated in Phase 8
- ✓ deterministic `all_cash` and deterministic dropout labels now flow through
  DuckDB load/export to the CSV surface — validated in Phase 8
- ✓ Zep rerun removed New Mountain Capital from the grouped 2014 proposal/drop
  actor sets and regenerated the deterministic artifact chain through export —
  validated in Phase 9
- ✓ Medivation rerun restored filing-grounded proposal/drop coverage and
  eliminated dangling `coverage_notes` event references without flattening the
  bidder-round chronology — validated in Phase 9
- ✓ 9-deal reconciliation rerun improved the corpus benchmark from
  `70.3% (156/222)` to `70.7% (157/222)` atomic match rate and reduced
  Alex-favored contradictions from `16` to `13` — validated in Phase 9

### Active

None yet — v2.0 requirements being defined.

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

## Current Milestone: v2.0 Observation Graph Architecture

**Goal:** Replace the event-first extraction contract with an observation graph
that separates filing-literal facts from analyst-derived rows, enabling correct
capture of cohort lifecycles, process structure, agreement chains, and
consideration regimes.

**Target features:**

- New data model: PartyRecord + CohortRecord replacing grouped actors; 6 typed
  observations (Process, Agreement, Solicitation, Proposal, Status, Outcome)
  replacing 20-type flat SkillEventRecord
- Extraction contract narrowing: LLM extracts filing-literal parties, cohorts,
  and observations with spans; no longer asked to produce analyst rows directly
- Deterministic derivation engine: rule-based engine producing ProcessPhases,
  LifecycleTransitions, CashRegimes, JudgmentRecords, and AnalystRows from the
  observation graph
- Structured coverage: CoverageCheckRecord replaces free-text coverage_notes
- Triple export surface: literal_observations.csv, analyst_rows.csv,
  benchmark_rows_expanded.csv
- Legacy adapter: v2 observations + derived rows map back to current CSV shape
  during transition
- Immediate fixes: all-cash short-circuit bug, structured coverage records

## Current State

**v1.0 shipped 2026-03-28. v1.1 complete 2026-03-30. v2.0 milestone started
2026-03-30.** All 9 deals have complete v1-contract pipeline artifacts through
DuckDB export. The live runtime includes 12 deterministic CLI stages plus 4
local-agent skills. The 9-deal cross-deal reconciliation records `70.7%
(157/222)` atomic match rate with 46 pipeline-favored vs 13 Alex-favored
arbitrations.

The GPT Pro architectural review (2026-03-31) identified 7 structural
bottlenecks in the v1 contract: SkillEventRecord pitched at wrong abstraction
level, enrichment constrained to annotating existing event IDs, grouped actors
incapable of modeling cohort lifecycles, rounds reconstructed from row taxonomy
instead of stored directly, reasoning stored in unstructured coverage_notes,
all-cash propagation partly broken, and benchmark policy disagreements conflated
with extraction failures. The v2.0 milestone addresses all 7 by introducing an
observation graph with derived analytical views.

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
*Last updated: 2026-03-30 — v2.0 milestone started*
