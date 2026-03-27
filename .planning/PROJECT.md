# Filing-Grounded Deal Pipeline Redesign

## What This Is

Brownfield redesign of an SEC deal-extraction pipeline so raw filing text becomes the primary input and the system produces filing-grounded structured deal data in a database plus review/export CSV. The existing repository already has fetch, preprocessing, extraction, verification, coverage, enrichment, and export components; this project redesigns them into a correctness-first end-to-end pipeline rather than a fragmented manual workflow.

## Core Value

Produce the most correct filing-grounded structured deal record possible from raw text, even if that requires more computation, more verification, or a more elaborate extraction architecture.

## Requirements

### Validated

- ✓ Seed-based raw filing fetch and immutable filing freeze — existing `raw-fetch` stage
- ✓ Filing preprocessing into chronology blocks and evidence items — existing `preprocess-source` stage
- ✓ Two-pass LLM extraction (actors then events with gap re-read) — existing `/extract-deal` skill
- ✓ Raw-to-canonical schema upgrade with span resolution — existing `canonicalize` stage
- ✓ Deterministic structural, verification, coverage, and enrichment gates — existing `check`, `verify`, `coverage`, `enrich-core` stages
- ✓ CSV-style review export — existing `/export-csv` skill
- ✓ Extended thinking enabled in LLM extraction calls — confirmed operational
- ✓ Pydantic schema-first artifact design with fail-fast validation — existing `models.py`
- ✓ Multi-provider LLM support (Anthropic + OpenAI) — existing `BIDS_LLM_PROVIDER` config

### Active

- [ ] Raw filing text flows through a single end-to-end pipeline into structured DB + review CSV without manual skill handoffs
- [ ] Extraction correctness improves on complex deals through better context management and attention handling
- [ ] Block-level metadata enrichment (dates, entities, evidence density, temporal phase) in preprocessing
- [ ] Prompt ordering restructured for cognitive bias exploitation (chronology first, instructions last)
- [ ] Quote-before-extract protocol forces evidence citation before structured extraction
- [ ] 2-block overlap with explicit XML context tags in chunked extraction
- [ ] Evidence items promoted from passive appendix to active attention-steering checklist
- [ ] Block-aligned semantic chunk boundaries (never split mid-block)
- [ ] Prompt caching for system prompt + actor roster across chunk calls
- [ ] Enhanced deterministic gates: temporal consistency, cross-event logic, per-actor coverage, attention decay diagnostics
- [ ] Complexity-based routing (single-pass for simple deals, multi-pass for complex)
- [ ] Expanded few-shot examples (4-5 covering NDA groups, ambiguous drops, cycle boundaries)
- [ ] Every extracted actor, event, term, and classification traceable to verbatim filing evidence
- [ ] Database output and CSV export generated from one canonical structured representation

### Out of Scope

- Benchmark-driven generation logic — benchmark materials remain post-export diagnostics only
- Speed-first or cost-first shortcuts that reduce filing-grounded correctness — correctness is the project priority
- UI or product surface work unrelated to the extraction pipeline — backend and data-pipeline focused
- RAG as primary architecture — assessed and rejected; retrieval is fundamentally mismatched with exhaustive extraction from single documents that fit in context
- Graph RAG or Agentic RAG as pipeline backbone — assessed; overkill for 9-deal batch corpus
- Context compression or summarization of filing text — legally precise language where lossy compression risks anchor text corruption

## Context

This repository is a brownfield Python project centered on the `skill_pipeline` package (installed via `pyproject.toml` as `skill-pipeline` CLI). It already contains raw fetch, source preprocessing, canonicalization, deterministic QA gates, deterministic enrichment, and CSV export, plus skill-driven extraction and enrichment steps. The 9 active deals are: imprivata, mac-gray, medivation, penford, petsmart-inc, providence-worcester, saks, stec, zep. Only `stec` has complete pipeline artifacts (raw through export) as baseline.

The main technical uncertainty is context management inside long filings. Research completed in `.planning/research/CONTEXT_AND_ATTENTION.md` identifies the "lost in the middle" attention failure mode as the primary extraction quality bottleneck and recommends prompt ordering, quote-before-extract, and evidence anchoring as the highest-ROI improvements. Research in `.planning/research/RAG_ARCHITECTURE.md` concludes RAG is not the right primary architecture but targeted retrieval could assist recovery passes.

The LLM extraction stage is the only non-deterministic component. All quality originates there. The deterministic gates (check, verify, coverage) catch errors after the fact. The redesign improves both: better extraction quality through prompt architecture, and better error detection through enhanced gates.

## Constraints

- **Source of truth**: Filing text is the only factual source — benchmark spreadsheets and diagnostic files cannot define generation behavior
- **Project shape**: Brownfield redesign inside the current repository — preserve and learn from existing pipeline stages rather than greenfield
- **Priority**: Correctness over automation speed, token cost, or novelty — tradeoffs favor more reliable outputs
- **Traceability**: Outputs must remain evidence-linked and auditable — every record maps back to filing text
- **Multi-provider**: Must maintain Anthropic + OpenAI provider support via existing env var config
- **Python target**: 3.11+ with 4-space indentation, type hints on public functions, Pydantic-first schemas
- **Benchmark separation**: Benchmark materials forbidden until `/export-csv` completes

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| RAG rejected as primary architecture | Extraction requires exhaustive recall, not selective retrieval; documents fit in context; RAG adds retrieval failure modes | ✓ Good |
| Correctness over speed/cost | User explicitly prioritized correctness; tradeoffs favor more reliable outputs | — Pending |
| Prompt ordering is highest-ROI zero-cost change | Anthropic docs: data first + query last improves quality 10-30% at zero token cost | — Pending |
| Quote-before-extract is most impactful structural change | Prevents hallucinated anchor text, the failure mode verify catches most often | — Pending |
| Keep multi-provider support | User confirmed; maintain BIDS_LLM_PROVIDER flexibility for Anthropic and OpenAI | — Pending |
| Hybrid retrieval only for targeted recovery | If coverage finds gaps, lightweight BM25 could narrow recovery context. Implement context/attention improvements first. | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-27 after initialization*
