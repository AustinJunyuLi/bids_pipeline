---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: reconciliation + execution-log quality fixes
status: Ready to execute
stopped_at: Completed 09-01-PLAN.md
last_updated: "2026-03-30T15:07:14Z"
progress:
  total_phases: 4
  completed_phases: 3
  total_plans: 10
  completed_plans: 8
---

# Project State

## Current Position

Phase: 09 (deal-specific-fixes-revalidation) — EXECUTING
Plan: 2 of 3

## Progress

- [x] PROJECT.md initialized
- [x] REQUIREMENTS.md defined (16 requirements, 4 categories)
- [x] Research completed (5 documents)
- [x] ROADMAP.md created (4 phases: 6-9)
- [x] Phase 6 planned
- [x] Phase 6 executed
- [x] Phase 7 planned
- [x] Phase 7 executed
- [x] Phase 8 planned
- [x] Phase 8 executed
- [x] Phase 9 planned
- [ ] Phase 9 executed

## Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260329-hyh | Fix 4 deal-agent orchestrator issues | 2026-03-29 | 0aa4254 | [260329-hyh-fix-4-deal-agent-orchestrator-issues](./quick/260329-hyh-fix-4-deal-agent-orchestrator-issues/) |

## Historical Decisions

- No Python LLM wrapper -- all LLM calls remain in .claude/skills/
- INFRA-01/02 moved from Phase 1 to Phase 2 (skill-level changes)
- Annotation extends preprocess-source, not a separate command
- Block metadata: parsed dates, seed-based entities, evidence density, hybrid temporal phase
- Annotation fields are required on ChronologyBlock (no defaults, no optionals)
- Block builder creates placeholder annotations that annotate_chronology_blocks replaces
- Temporal phase priority: outcome > bidding > initiation from evidence types with ordinal fallback
- Removed anthropic>=0.49 from manifests -- no live import in skill_pipeline or tests
- Capped edgartools below 6.0 to guard against breaking API changes
- Kept openpyxl>=3.1 -- live workflow audit not performed
- Missing grounding is now fail-closed: canonicalize no longer synthesizes placeholder bidders/events into prod outputs
- Drop gating is sequential and cycle-local; `restarted` clears prior bidder participation state
- `canonicalize` must be idempotent on already-canonical extracts so downstream reruns work against current artifacts
- Local validation must follow actual on-disk corpus availability, not the stale 9-deal assumption in the plan
- Medivation seed was corrected from `0001193125-16-696889` to `0001193125-16-696911`; seed-quality hardening is delegated as a non-blocking todo
- Phase 2 will add a deterministic `compose-prompts` stage, provider-neutral prompt artifacts under `data/skill/<slug>/prompt/`, and extract-skill consumption of those artifacts
- Prompt packet models inherit ArtifactEnvelope for manifest-level metadata consistency
- Prompt artifacts live under data/skill/<slug>/prompt/ separate from extract/
- compose-prompts writes a manifest stub; packet rendering deferred to plan 02
- Token estimation uses ceil(word_count * 1.35) -- needs validation against stec in Plan 03
- Greedy whole-block chunking with at-least-one-block-per-window guarantee
- Packet body order: deal_context, chronology_blocks, overlap_context, evidence_checklist, actor_roster, task_instructions
- --mode all generates actors only; --mode events requires actors_raw.json (fail-fast)
- Evidence checklist groups by EvidenceType with imperative headers
- Validator checks both schema validity and rendered content tags (chronology_blocks, evidence_checklist, task_instructions, overlap_context)
- PromptStageSummary reports packet_count, actor_packet_count, event_packet_count in deal-agent
- compose-prompts documented between preprocess-source and /extract-deal in all runtime docs
- Evidence checklists are now window-local in chunked prompt packets rather than filing-wide
- Event packet composition now validates actor-roster JSON against the actor artifact schema before rendering
- Prompt composition now fails fast on duplicate source block IDs, missing event examples assets, and unknown requested block IDs
- Chunk-budget overhead remains deferred to Phase 5 complexity routing per the audit decision
- Phase 03-01 replaced raw evidence_refs with QuoteEntry-backed quote_ids and top-level quotes arrays
- Extract artifact loading now distinguishes quote_first from canonical payloads and rejects legacy evidence_refs artifacts
- PROMPT-05 remains open after 03-01 because only the schema foundation and fixtures shipped; runtime rewrites continue in later plans
- Quote-first verify now runs a filing-text quote validation pass followed by quote_id integrity checks before shared referential and structural gates
- compose-prompts task instructions and prompt assets now require quotes-first output with `quote_ids` references
- extract-deal SKILL.md now documents the quote-first schema; skill mirror sync remains deferred to verification by plan design
- Runtime consumers now dispatch only on `quote_first` and `canonical`, matching `load_extract_artifacts()`
- Quote-first coverage overlap is now block-based through `quote_id` to `block_id` lookup instead of legacy `evidence_refs`
- Phase 4 semantic validation now lives in a dedicated `gates.py` stage parallel to `check.py`, `verify.py`, and `coverage.py`
- Cross-event gate rules sort events by parsed date before evaluating restart-delimited cycles
- Gates accept wrapped `verification_findings.json` payloads because live artifacts are stored as `{ \"findings\": [...] }`
- Deal-agent summaries now expose gates as a first-class stage between coverage and verify
- Enrich-core fixtures synthesize `gates_report.json` by default because semantic gates are now a hard prerequisite
- stec gate verification restores generated `gates_report.json` after checks so repo artifacts stay clean
- Phase 5 plan 01 uses a shared `data/pipeline.duckdb` file exposed through `SkillPathSet.database_path`
- db-load reloads each deal transactionally with deal-scoped DELETE + INSERT across all DuckDB tables
- db-export writes the review CSV from DuckDB queries and preserves interpretive drop labels even when no deterministic bid row exists
- compose-prompts auto routing now classifies deals at 150 chronology blocks and forces explicit single-pass windows for simple deals
- Event prompt few-shot coverage now includes NDA groups, ambiguous drops, and terminate/restart cycle boundaries in addition to range proposals and formal-round signals
- deal-agent now reports db_load and db_export from persisted DuckDB and CSV artifacts rather than invoking stages directly
- runtime docs treat db-export as the deterministic export contract while preserving explicit pre-/export-csv benchmark-boundary wording for legacy/manual workflows
- Phase 5 db validation remains scoped to the active 9-deal calibration roster because data/seeds.csv now contains 401 rows outside this phase scope

## Performance Metrics

| Phase | Plan | Duration | Tasks | Files | Date |
|-------|------|----------|-------|-------|------|
| 05-integration-calibration | 03 | 19m | 2 | 8 | 2026-03-28 |
| 06-deterministic-hardening | 02 | 12m | 2 | 4 | 2026-03-29 |
| 06-deterministic-hardening | 03 | 14 min | 1 | 6 | 2026-03-29 |
| Phase 07-bid-type-rule-priority P01 | 2min | 2 tasks | 2 files |
| Phase 09 P01 | 21m | 2 tasks | 17 files | 2026-03-30 |

## Decisions

- Phase 6 NDA tolerance stays schema-neutral by using exact normalized substring markers instead of changing extract artifacts.
- Gates now qualify NDA events from event summaries plus matched chronology block text before lifecycle and cycle rules consume them.
- Keep DuckDB lock retry in `open_pipeline_db()` so `db-load` and `db-export` share the same bounded connection policy.
- Retry only lock-specific `duckdb.IOException` failures containing `Could not set lock on file`, and re-raise all other connection errors immediately.
- [Phase 07-bid-type-rule-priority]: Process position (after_final_round_*) overrides informal language signals in bid_type classification; rules renumbered 1-5 without fractional 2.5
- [Phase 08-extraction-guidance-enrichment-extensions]: extract-deal guidance now explicitly covers round milestones, verbal/oral priced proposals, and NDA exclusions from non-sale-process agreements.
- [Phase 08-extraction-guidance-enrichment-extensions]: deterministic enrichment emits sparse `DropTarget` labels and cycle-local `all_cash_overrides` without mutating canonical extract artifacts.
- [Phase 08-extraction-guidance-enrichment-extensions]: DuckDB export now prefers deterministic `all_cash_override`, and Windows DuckDB lock-contention detection accepts the newer "used by another process" error text.
- [Phase 09-deal-specific-fixes-revalidation]: planning should trust the live
  Zep and Medivation artifacts over stale roadmap wording; Medivation already
  has `evt_013` and `evt_017` proposals, while the live integrity mismatch is
  `coverage_notes` citing missing drop events `evt_027` and `evt_029`.

- [Phase 09-deal-specific-fixes-revalidation]: rerun only Zep and Medivation
  through export during blind generation, then measure the refreshed 9-deal
  reconciliation against the 2026-03-29 baseline.

- [Phase 09]: Zep was repaired by a clean extraction-forward rerun rather than hand-editing canonical artifacts — The refreshed extract removed New Mountain Capital from grouped 2014 proposal/drop events while preserving a clean canonicalize-through-export chain

## Session Continuity

- **Last session:** 2026-03-30T15:07:14Z
- **Stopped at:** Completed 09-01-PLAN.md
- **Resume file:** .planning/phases/09-deal-specific-fixes-revalidation/09-02-PLAN.md
- **Next action:** Continue Phase 9 with Wave 2 (`/gsd:execute-phase 9`).

## Accumulated Context

### Pending Todos

- None currently recorded.

### Key Reference Artifacts

- Cross-deal reconciliation: `data/reconciliation_cross_deal_analysis.md`
- 7-deal execution log: `quality_reports/session_logs/2026-03-29_7-deal-rerun_master.md`
- Per-deal reconciliation reports: `data/skill/<slug>/reconcile/`
