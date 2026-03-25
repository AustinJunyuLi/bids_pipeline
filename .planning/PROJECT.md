# Bids Data Pipeline

## What This Is

This repository is a local research pipeline for extracting structured M&A process data from SEC filings. It combines deterministic Python stages in `skill_pipeline/` with skill-driven LLM stages documented under `.claude/skills/`, and it stores both frozen filing sources and downstream artifacts directly in the repo. The primary audience is the contributor maintaining and extending the filing-grounded workflow across Windows and Linux machines.

## Core Value

Produce filing-grounded deal data that remains auditable back to SEC source text and reproducible across machines.

## Requirements

### Validated

- [validated] Operator can fetch one approved SEC filing per deal from `data/seeds.csv` into immutable `raw/<slug>/` artifacts - existing
- [validated] Operator can preprocess the frozen filing into chronology and evidence artifacts under `data/deals/<slug>/source/` and fail on multi-document drift - existing
- [validated] Operator can canonicalize extract artifacts into span-backed actors and events with deterministic deduplication, NDA gating, and unnamed-party recovery - existing
- [validated] Operator can run deterministic `check`, `verify`, and `coverage` gates and receive machine-readable outputs before enrichment - existing
- [validated] Operator can derive deterministic rounds, bid classifications, cycles, and formal-boundary artifacts only after QA passes - existing
- [validated] Contributors can keep `.claude/skills` canonical and verify `.codex/.cursor` mirrors with `scripts/sync_skill_mirrors.py` - existing
- [validated] Benchmark materials are fenced off until post-export reconciliation by committed docs and regression tests - existing
- [validated] `extract-deal` now uses sequential chunk extraction with consolidation as the only documented extraction path while preserving the `actors_raw.json` and `events_raw.json` contract - validated in Phase 06: Chunked Extraction Architecture
- [validated] `canonicalize` and `check` now absorb chunk-boundary actor duplication with deterministic dedup plus warning-level actor audit coverage - validated in Phase 06: Chunked Extraction Architecture
- [validated] `enrich-deal` now scopes interpretive rereads to event-linked chronology windows while keeping rounds, bid classifications, cycles, and formal boundary in deterministic `enrich-core` - validated in Phase 06: Chunked Extraction Architecture

### Active

- [ ] Document and stabilize the full hybrid workflow from raw fetch through export so stage ownership and artifact contracts are unambiguous
- [ ] Increase regression coverage around cross-stage handoffs, especially between skill-produced extract artifacts and deterministic CLI stages
- [ ] Reduce operational risk from external dependencies and local environment drift across Windows and Linux development
- [ ] Keep benchmark separation and post-export reconciliation boundaries explicit as new stages and docs are added

### Out of Scope

- Open-ended multi-filing discovery or automatic supplementary ingestion - the current repo intentionally uses one approved filing per deal
- Benchmark-driven generation before `/export-csv` - benchmark material is diagnostic only
- Silent fallback paths when source filings or canonical sidecars are missing - fail fast is the repository policy
- Hand-editing `.codex/skills` or `.cursor/skills` - those trees are derived mirrors, not authoring surfaces

## Context

- The tracked runtime is the `skill_pipeline` package with `skill-pipeline` as the only installed console entrypoint
- The operative workflow is hybrid: deterministic CLI stages surround LLM-driven skills such as `/extract-deal`, `/verify-extraction`, `/enrich-deal`, and `/export-csv`
- The repository carries 9 active deal slugs, with `data/seeds.csv` as the entrypoint for raw fetch
- `raw/` and tracked `data/` artifacts are part of the working dataset, not disposable scratch output
- Development happens on both Windows and Linux, with GitHub as the synchronization point
- `CLAUDE.md` remains the authoritative repository instruction source even after adopting GSD planning in `.planning/`
- Phase 06 completed the chunked extraction architecture shift: `petsmart-inc` is locally auditable through chunked extraction and unnamed-party recovery, while `stec` is approved through the Phase 06 validation summary's reported fresh rerun caveat

## Constraints

- **Source boundary**: SEC filing text is the only factual source for generation - benchmark materials are post-export only
- **Runtime shape**: upstream source preparation is seed-only and single-primary-document - multi-filing support is not part of the current design
- **Correctness**: the repo fails fast on missing data, invalid schemas, and contradictory artifacts - silent fallback behavior is not allowed
- **Cross-platform**: tracked text files must remain `LF` across Windows and Linux checkouts - `.gitattributes` is the source of truth
- **Workflow split**: deterministic CLI stages and skill-driven stages must share stable artifact contracts - there is no single tracked end-to-end runner today

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Keep `CLAUDE.md` authoritative and use `.planning/` for GSD project memory | Preserves the repo's existing operating contract while adding brownfield planning artifacts | Good |
| Treat the current deterministic pipeline as the validated baseline | Brownfield planning should start from what already works, not from a rewrite fantasy | Good |
| Use committed planning docs with standard granularity on the current branch | This repo needs durable shared memory, but not micro-phases for every small change | Pending |
| Skip external ecosystem research during initialization | The immediate goal is to frame the existing brownfield codebase, and the repo already contains enough local context for that | Pending |
| Treat chunk debug artifacts as the primary runtime proof for a specific extraction run | Final raw JSON artifacts keep the same contract before and after the chunked redesign, so run-specific validation needs direct chunk evidence | Good |

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
2. Core Value check - still the right priority?
3. Audit Out of Scope - reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-25 after Phase 06 completion*
