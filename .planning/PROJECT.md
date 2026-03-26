# Filing-Grounded Deal Pipeline Redesign

## What This Is

Brownfield redesign of the existing SEC deal-extraction repository so raw filing text becomes the primary input and the system produces filing-grounded structured deal data in a database plus review/export CSV. The current repo already has fetch, preprocessing, extraction, verification, coverage, enrichment, and export components; this project is to redesign them into a correctness-first end-to-end pipeline rather than a fragmented manual workflow.

## Core Value

Produce the most correct filing-grounded structured deal record possible from raw text, even if that requires more computation, more verification, or a more elaborate extraction architecture.

## Requirements

### Validated

- ✓ Seed-based raw filing fetch and immutable filing freeze already exist — existing repository capability
- ✓ Filing preprocessing into chronology and evidence artifacts already exists — existing repository capability
- ✓ Deterministic structural, verification, coverage, and enrichment gates already exist — existing repository capability
- ✓ CSV-style review export already exists — existing repository capability

### Active

- [ ] Raw filing text can flow through a single end-to-end pipeline into a structured database and review/export CSV without manual skill handoffs between core stages
- [ ] The redesigned pipeline improves extraction correctness on complex deals through better context management and attention handling
- [ ] The redesign explicitly researches whether retrieval-assisted methods, including AgenticRAG-style approaches, improve correctness enough to belong in the main architecture
- [ ] Every extracted actor, event, term, and classification remains traceable back to verbatim filing evidence
- [ ] The database output and CSV export are generated from one canonical structured representation so downstream outputs do not drift

### Out of Scope

- Benchmark-driven generation logic before a filing-grounded pipeline exists — benchmark materials remain post-export diagnostics only
- Speed-first or cost-first shortcuts that reduce filing-grounded correctness — correctness is the project priority
- UI or product surface work unrelated to the extraction pipeline redesign — the work is backend and data-pipeline focused

## Context

This repository is a brownfield Python project centered on the `skill_pipeline` package. It already contains raw fetch, source preprocessing, canonicalization, deterministic QA gates, deterministic enrichment, and CSV export, plus skill-driven extraction and enrichment steps. The current user goal is not to incrementally patch that flow but to rethink the whole pipeline boundary so the system starts from raw filing text and ends in a structured database plus CSV with maximum correctness.

The main technical uncertainty is context management inside long filings and whether retrieval should become part of the redesigned architecture. Existing local research in `.planning/research/CONTEXT_AND_ATTENTION.md` already identifies long-context attention failure modes and suggests that retrieval may help most in targeted recovery or evidence-guided extraction rather than as a naive replacement for full-document processing. That research should inform, not pre-commit, the redesign.

## Constraints

- **Source of truth**: Filing text is the only factual source — benchmark spreadsheets and diagnostic files cannot define generation behavior
- **Project shape**: Brownfield redesign inside the current repository — preserve and learn from existing pipeline stages rather than pretending this is a greenfield app
- **Priority**: Correctness over automation speed, token cost, or novelty — tradeoffs should favor more reliable outputs
- **Traceability**: Outputs must remain evidence-linked and auditable — every important record should map back to filing text
- **Architecture**: Structured DB choice is secondary to correctness — choose the simplest database representation that preserves a clean canonical model

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Treat this as a full pipeline redesign, not an incremental tweak | The desired end state is raw text to DB/CSV, not improvement of a fragmented handoff flow | — Pending |
| Optimize for maximum correctness | User explicitly prioritized correctness over speed, cost, and convenience | — Pending |
| Keep LLM extraction in scope and research RAG as a possible architectural component | The open question is whether retrieval materially improves correctness in this domain | — Pending |
| Use one canonical structured representation to drive both DB and CSV outputs | Prevent divergence between storage, QA, and export paths | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `$gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `$gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check -> still the right priority?
3. Audit Out of Scope -> reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-26 after initialization*
