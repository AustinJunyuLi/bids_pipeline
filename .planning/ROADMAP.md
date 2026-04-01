# Roadmap: Filing-Grounded Pipeline Redesign

## Milestones

- **v1.0 Filing-Grounded Pipeline Redesign** -- Phases 1-5 (shipped 2026-03-28) -- [archive](milestones/v1.0-ROADMAP.md)
- **v1.1 Reconciliation + Execution-Log Quality Fixes** -- Phases 6-9 (complete 2026-03-30)
- **v2.0 Observation Graph Architecture** -- Phases 10-16 (shipped 2026-03-31) -- [archive](milestones/v2.0-ROADMAP.md)
- **v2.1 V2 Default Cutover + Legacy Archive** -- Phases 17-19 (complete 2026-03-31) -- [archive](milestones/v2.1-ROADMAP.md)
- **v2.2 Reconciliation Lift + Surface Repair** -- Phases 20-24 (extended 2026-04-01; Phase 24 planned) -- [audit checkpoint](milestones/v2.2-MILESTONE-AUDIT.md)

## Current Milestone

### v2.2 Reconciliation Lift + Surface Repair

- [x] **Phase 20: Proposal Linkage + Bid-Type Repair** - make proposal derivation chronology-safe, use proposal-local formality cues, and harden gates around invalid solicitation links (completed 2026-04-01)
- [x] **Phase 21: Transition + Outcome Normalization** - redesign synthetic drop dating and bidder/outcome resolution so lifecycle rows reflect the strongest filing-supported elimination points (completed 2026-04-01)
- [x] **Phase 22: Taxonomy + Export Surface Repairs** - expose agreement/process distinctions, date precision, and enterprise-value proposals on the analyst-facing export surface (completed 2026-04-01)
- [x] **Phase 23: Extraction Contract + Validation Hardening** - update prompt/skill contracts and v2 gates so recipient scope, chronology-safe links, and substantive outcome requirements are enforced before export (completed 2026-04-01)
- [ ] **Phase 24: V1 Retirement + Git-History Preservation** - remove the legacy v1 runtime and skill surface from the working tree while preserving recoverability through Git history and archived milestone artifacts

## Phase Details

### Phase 20: Proposal Linkage + Bid-Type Repair
**Goal**: Repair proposal-to-phase association and bid-type derivation so proposal rows reflect filing-supported chronology and formality signals.
**Depends on**: Phase 19 complete
**Success Criteria**:
  1. future-linked or type-incompatible `requested_by_observation_id` values are ignored or blocked, and proposals resolve to the latest same-day-or-earlier solicitation
  2. proposal rows classify `Formal` or `Informal` from proposal-local clues plus repaired phase context, with deterministic precedence on mixed signals
  3. phase-level cash-regime grouping uses the repaired proposal-phase association rather than trusting raw forward links
  4. regression tests cover future-link fallback, definitive/final proposal language, and mixed-signal non-binding cases

### Phase 21: Transition + Outcome Normalization
**Goal**: Rework dropout and outcome derivation so elimination dates and winning actors reflect the strongest filing-grounded support.
**Depends on**: Phase 20
**Success Criteria**:
  1. `EXIT-03` and `EXIT-04` use explicit exits, narrowing dates, prior-round deadlines, and winner-close fallback in a deterministic precedence ladder
  2. executed and restarted rows prefer bidder or bidder-cohort actors and recover anchored dates when the filing provides nearby exact support
  3. solicitation scope gaps feed deterministic backfill or explicit review output instead of silently producing unscoped round or drop rows
  4. regression tests cover petsmart-like narrowing, providence-style residual losers, and restarted outcome subject recovery

### Phase 22: Taxonomy + Export Surface Repairs
**Goal**: Expand the analyst surface so agreement/process rows, proxy dates, and enterprise-value proposals are represented without misleading precision.
**Depends on**: Phase 21
**Success Criteria**:
  1. exclusivity, standstill, NDA amendment, and clean-team observations export with distinct analyst event types
  2. bidder-originated sale and advisor-termination boundaries map to analyst-comparable process rows where filing support exists
  3. analyst exports distinguish exact-day dates from proxy sort dates and preserve enterprise-value-only proposals without forcing false per-share precision
  4. regression tests cover the new event types, export columns, and downstream CSV surfaces

### Phase 23: Extraction Contract + Validation Hardening
**Goal**: Update extraction instructions, skill docs, and v2 gates so the repaired derivation logic gets better inputs and failures surface before export.
**Depends on**: Phase 22
**Success Criteria**:
  1. observation prompt instructions and canonical `.claude/skills` docs explicitly require recipient refs, chronology-safe proposal links, bidder-scoped outcomes, and agreement-family distinctions
  2. `gates-v2` flags missing named solicitation recipients, forward proposal links, under-specified substantive outcomes, and lossy export warnings
  3. representative prompt and validation tests, plus at least one multi-deal smoke pass, confirm the tightened contract without weakening the benchmark boundary

### Phase 24: V1 Retirement + Git-History Preservation
**Goal**: Retire the legacy v1 runtime, skill surface, and archived working-tree artifacts from the live repository while keeping the prior implementation recoverable through Git history, milestone archives, and tags.
**Depends on**: Phase 23
**Success Criteria**:
  1. the live CLI, repo docs, and canonical skill tree stop exposing v1-only commands and legacy skills in the working tree
  2. any live v2 code that still imports or depends on legacy v1 modules is migrated, extracted, or deleted so the repo runs cleanly without the v1 runtime present
  3. `data/legacy/v1/` and other v1-only working-tree artifacts are removed only after the recovery path is explicit through Git history, archived milestone docs, and any required release tags
  4. regression tests and contract docs are updated so the repository can continue operating without the v1 surface present

## Progress

| Phase | Milestone | Status | Completed |
|-------|-----------|--------|-----------|
| 20. Proposal Linkage + Bid-Type Repair | v2.2 | Complete    | 2026-04-01 |
| 21. Transition + Outcome Normalization | v2.2 | Complete    | 2026-04-01 |
| 22. Taxonomy + Export Surface Repairs | v2.2 | Complete    | 2026-04-01 |
| 23. Extraction Contract + Validation Hardening | v2.2 | Complete    | 2026-04-01 |
| 24. V1 Retirement + Git-History Preservation | v2.2 | Planned | |

---
*Roadmap refreshed: 2026-04-01 from the GPT Pro diagnosis round_1, then extended with Phase 24 for v1 retirement follow-on work.*
