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
- ✓ CSV-style review export — existing `/export-csv` skill
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

### Active

- [ ] Raw filing text flows through a single documented local-agent
  orchestration contract into structured DB + review CSV without ad hoc stage
  handoffs
- [ ] Extraction correctness improves on complex deals through better context
  management and attention handling
- [ ] Block-level metadata enrichment (dates, entities, evidence density,
  temporal phase) in preprocessing
- [ ] Prompt ordering restructured for cognitive bias exploitation (chronology
  first, instructions last)
- [ ] 2-block overlap with explicit XML context tags in chunked extraction
- [ ] Evidence items promoted from passive appendix to active
  attention-steering checklist
- [ ] Block-aligned semantic chunk boundaries (never split mid-block)
- [ ] Reusable static prompt prefix separated from chunk-specific content so
  selected local-agent tooling can reuse repeated context where supported
- [ ] Complexity-based routing (single-pass for simple deals, multi-pass for
  complex)
- [ ] Expanded few-shot examples (4-5 covering NDA groups, ambiguous drops,
  cycle boundaries)
- [ ] Every extracted actor, event, term, and classification traceable to
  verbatim filing evidence
- [ ] Database output and CSV export generated from one canonical structured
  representation

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

Phases 1-4 are now complete: deterministic block metadata, prompt packet
composition, quote-before-extract grounding, and enhanced semantic gates all
ship in the live repository. The extraction stage remains the only
non-deterministic component. All quality originates there. The deterministic
gates (`check`, `verify`, `coverage`, `gates`) catch errors after the fact. The
remaining redesign work focuses on integration, calibration, and end-to-end
pipeline unification.

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
- **Benchmark separation**: Benchmark materials forbidden until `/export-csv`
  completes

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| RAG rejected as primary architecture | Extraction requires exhaustive recall, not selective retrieval; documents fit in context; RAG adds retrieval failure modes | ✓ Good |
| Correctness over speed/cost | User explicitly prioritized correctness; tradeoffs favor more reliable outputs | — Pending |
| Prompt ordering is highest-ROI zero-cost change | Data-first chronology packets improve long-document attention handling at effectively zero deterministic cost | — Pending |
| Quote-before-extract is most impactful structural change | Prevents hallucinated anchor text, the failure mode verify catches most often | ✓ Adopted |
| Semantic gates run as a dedicated deterministic stage after coverage | Keeps structural and semantic validation separate while giving enrich-core a single fail-fast semantic prerequisite | ✓ Adopted |
| Keep local-agent orchestration outside `skill_pipeline` | Live code has no Python LLM wrapper, and canonical skill docs already own extraction/repair/export | ✓ Adopted |
| Hybrid retrieval only for targeted recovery | If coverage finds gaps, lightweight BM25 could narrow recovery context. Implement context/attention improvements first. | — Pending |

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
*Last updated: 2026-03-28 after Phase 04 completion*
