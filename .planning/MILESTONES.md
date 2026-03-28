# Milestones

## v1.0 Filing-Grounded Pipeline Redesign (Shipped: 2026-03-28)

**Phases completed:** 5 phases, 16 plans, 36 tasks

**Key accomplishments:**

- Required date/entity/density/phase metadata on ChronologyBlock with deterministic annotation helpers and preprocess-source integration
- Removed unused anthropic SDK, capped edgartools<6.0, added historical disclaimers to stale design docs, and regression tests for runtime-contract boundary
- Provider-neutral prompt packet schemas, deterministic artifact paths under data/skill/<slug>/prompt/, and compose-prompts CLI stage shell with contract tests
- Deterministic chunk planner with 2-block overlap, active evidence checklist, and chronology-first XML packet renderer producing real file-backed prompt artifacts
- Prompt packet validator, deal-agent prompt-stage status, runtime doc integration, skill mirror sync, and stec validation baseline
- QuoteEntry raw schema, quote-first extract loading, and suite-wide quote-linked raw test fixtures
- Quote-first canonicalization now resolves quote text directly to spans, logs orphaned quotes, and hands enrich-core canonical span-backed artifacts only
- Quote-first verify rounds for filing-text validation and quote_id integrity, plus quote-backed check gate cleanup
- Quote-first extraction guidance in compose-prompts, prompt assets, event examples, and the extract-deal skill contract
- Quote-first downstream consumers in deal_agent and coverage now accept the live extract contract, and the full pytest suite is green again
- Semantic gate stage for temporal mismatches, cross-event invariants, NDA lifecycle gaps, and verification attention decay diagnostics
- End-to-end semantic gate integration through the CLI, deal-agent status surface, enrich-core blockers, and regression coverage against real `stec` artifacts
- DuckDB-backed canonical store with transactional db-load ingestion and deterministic db-export CSV generation
- Block-count-based compose-prompts routing with explicit single-pass windows and five filing-grounded quote-first event examples
- Deal-agent db_load/db_export stage summaries with synced orchestration docs and stec DuckDB export validation

---
