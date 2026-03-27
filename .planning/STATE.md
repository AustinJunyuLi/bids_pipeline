# Project State

## Current Phase
Phase 2: Prompt Architecture — executing (plan 02 of 03 complete)

## Last Session
- **Stopped at:** Phase 2 Plan 02 complete (chunk planner, evidence checklist, packet renderer)
- **Resume file:** `.planning/phases/02-prompt-architecture/02-03-PLAN.md`
- **Date:** 2026-03-27

## Progress
- [x] PROJECT.md initialized
- [x] REQUIREMENTS.md defined (20 requirements, 4 categories)
- [x] ROADMAP.md created (5 phases)
- [x] Codebase mapped (7 documents)
- [x] Research completed (5 documents)
- [x] Phase 1 context gathered (13 decisions)
- [x] Phase 1 planned
- [x] Phase 1 Plan 01: Annotated block schema and preprocess integration (3/3 tasks)
- [x] Phase 1 Plan 02: Runtime contract hardening (3/3 tasks)
- [x] Phase 1 Plan 03: local validator + `stec` regeneration/downstream rerun
- [x] Phase 1 Plan 03: full 9-deal corpus validation across `imprivata`, `mac-gray`, `medivation`, `penford`, `petsmart-inc`, `providence-worcester`, `saks`, `stec`, `zep`
- [x] Phase 1 verified
- [x] Phase 2 context gathered
- [x] Phase 2 planned
- [x] Phase 2 Plan 01: Prompt packet contract — models, paths, CLI, tests (3/3 tasks)
- [x] Phase 2 Plan 02: Chunk planner, evidence checklist, packet renderer (3/3 tasks)

## Key Decisions This Session
- No Python LLM wrapper — all LLM calls remain in .claude/skills/
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

## Session Continuity
- **Last session:** 2026-03-27T23:33:07Z
- **Stopped at:** Completed 02-02-PLAN.md
- **Resume file:** `.planning/phases/02-prompt-architecture/02-03-PLAN.md`

## Accumulated Context
### Pending Todos
- Claude follow-up: investigate seed-quality guard for Medivation-style bad accession in `.planning/todos/pending/2026-03-27-investigate-seed-quality-guard-for-medivation-style-bad-accession.md`
