# Roadmap: Bids Data Pipeline

## Overview

This is a brownfield roadmap for an existing hybrid SEC-filing extraction pipeline. The current deterministic stages already work, but the project needs stronger workflow contracts, cleaner cross-stage verification, better cross-platform contributor hygiene, and explicit management of external dependency risk. The phases below treat the current runtime as the baseline and focus on making future work easier to plan, verify, and execute safely.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): planned milestone work
- Decimal phases (2.1, 2.2): urgent insertions if needed later

- [ ] **Phase 1: Workflow Contract Surface** - make the hybrid pipeline and project memory explicit
- [ ] **Phase 2: Deterministic Stage Interfaces** - harden the handoffs between skill outputs and deterministic stages
- [ ] **Phase 3: Regression and Policy Checks** - make verification and boundary checks easier to run and extend
- [ ] **Phase 4: Cross-Platform Contributor Operations** - keep Windows and Linux development quiet and reproducible
- [ ] **Phase 5: Dependency Risk Management** - track and mitigate external breakpoints before they block active work
- [x] **Phase 6: Chunked Extraction Architecture** - redesign extraction from two-pass single-shot to all-chunked sequential with consolidation

## Phase Details

### Phase 1: Workflow Contract Surface
**Goal**: Make the active workflow, artifact paths, and project memory explicit enough that future work starts from a shared brownfield baseline.
**Depends on**: Nothing (first phase)
**Requirements**: WFLO-01, RISK-02
**Success Criteria** (what must be TRUE):
1. Contributor can read committed docs and identify the inputs, outputs, and prerequisites for each active stage.
2. Contributor can tell which stages are deterministic CLI stages and which are skill-driven stages without ambiguity.
3. `.planning/` provides enough shared context that future phase work does not depend on private local notes.
**Plans**: 3 plans

Plans:
- [x] 01-01-PLAN.md — Publish the contributor-facing workflow contract and lock it with a doc regression test
- [x] 01-02-PLAN.md — Align `CLAUDE.md` and the canonical skills index with the hybrid deterministic vs LLM split
- [x] 01-03-PLAN.md — Capture the stabilized brownfield workflow in `.planning/` for later phases

### Phase 2: Deterministic Stage Interfaces
**Goal**: Keep the deterministic stages independently runnable and make skill-to-CLI handoff failures precise.
**Depends on**: Phase 1
**Requirements**: WFLO-02, WFLO-03, QUAL-03
**Success Criteria** (what must be TRUE):
1. Contributor can run each deterministic CLI stage from documented inputs without manual file renaming or directory cleanup.
2. Handoff failures from skill-produced extract artifacts surface as precise contract errors.
3. Legacy-versus-canonical extract expectations remain explicit wherever both modes are supported.
**Plans**: 3 plans

Plans:
- [ ] 02-01: Audit deterministic stage prerequisites and output contracts
- [ ] 02-02: Tighten skill-to-CLI artifact interface checks where ambiguity remains
- [ ] 02-03: Document safe rerun behavior for raw, preprocess, extract, and canonical stages

### Phase 3: Regression and Policy Checks
**Goal**: Make the repo's verification surface easy to run, extend, and trust.
**Depends on**: Phase 2
**Requirements**: QUAL-01, QUAL-02
**Success Criteria** (what must be TRUE):
1. Targeted regression commands cover every deterministic stage and every repo policy boundary that protects generation quality.
2. Benchmark leakage and skill-mirror drift fail automated checks before merge.
3. New bugs land with focused regression coverage rather than relying on informal reproduction notes.
**Plans**: 3 plans

Plans:
- [ ] 03-01: Expand and organize stage-focused regression commands
- [ ] 03-02: Keep benchmark-boundary and mirror-sync checks centralized and visible
- [ ] 03-03: Add any missing regression fixtures needed for contract-level debugging

### Phase 4: Cross-Platform Contributor Operations
**Goal**: Keep normal work on Windows and Linux reproducible, quiet, and low-friction.
**Depends on**: Phase 3
**Requirements**: OPS-01, OPS-02
**Success Criteria** (what must be TRUE):
1. Normal Windows/Linux development does not produce tracked line-ending churn in committed text files.
2. Local-only paths remain ignored by default while committed repo artifacts stay visible.
3. Contributors can follow one committed setup path for cross-platform work and mirror syncing.
**Plans**: 3 plans

Plans:
- [ ] 04-01: Verify repo hygiene rules against real contributor workflows
- [ ] 04-02: Keep local-only state and tracked artifact boundaries explicit
- [ ] 04-03: Tighten contributor runbook guidance for dual-machine development

### Phase 5: Dependency Risk Management
**Goal**: Surface external breakpoints before they interrupt active deal work.
**Depends on**: Phase 4
**Requirements**: RISK-01
**Success Criteria** (what must be TRUE):
1. The repo tracks dependency watchpoints that can break live fetches or adjacent provider integrations.
2. Contributors know what to test before upgrading EDGAR or LLM-adjacent dependencies.
3. Dependency risks are captured in committed project memory instead of only in commit history or local notes.
**Plans**: 3 plans

Plans:
- [ ] 05-01: Document current dependency watchlist and failure modes
- [ ] 05-02: Add or refine checks that catch risky dependency changes early
- [ ] 05-03: Fold dependency risk review into normal phase planning

### Phase 6: Chunked Extraction Architecture
**Goal**: Redesign `/extract-deal` from two-pass single-shot to all-chunked sequential extraction with consolidation pass, add deterministic actor dedup and audit, and refactor `/enrich-deal` to use event-targeted re-reads.
**Depends on**: Phase 2 (deterministic stage interfaces must be stable before changing extraction)
**Requirements**: WFLO-03 (skill-to-CLI handoff), QUAL-01 (regression coverage)
**Success Criteria** (what must be TRUE):
1. All 9 deals extract through the chunked path at ~3-4K tokens per chunk with no single-shot fallback.
2. Consolidation pass produces deduplicated actors and events with global event_ids in the same `actors_raw.json` + `events_raw.json` contract.
3. `canonicalize` actor dedup and `check` actor audit catch residual duplicates from chunk boundaries.
4. Petsmart's silent NDA signers (9 unnamed parties) are captured via improved count_assertion extraction feeding existing unnamed-party recovery.
5. `enrich-deal` uses event-targeted re-reads (~2-3K context per task) instead of full-context calls.
6. All existing tests pass. New regression tests cover chunked extraction, actor dedup, and actor audit.
**Plans**: 4 plans

Plans:
- [x] 06-01-PLAN.md — Rewrite extract-deal SKILL.md for all-chunked sequential extraction with consolidation
- [x] 06-02-PLAN.md — Add _dedup_actors to canonicalize and _check_actor_audit to check with regression tests
- [x] 06-03-PLAN.md — Refactor enrich-deal SKILL.md to event-targeted re-reads
- [x] 06-04-PLAN.md — End-to-end validation on stec (largest) and petsmart (silent NDA test case)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Workflow Contract Surface | 0/3 | Not started | - |
| 2. Deterministic Stage Interfaces | 0/3 | Not started | - |
| 3. Regression and Policy Checks | 0/3 | Not started | - |
| 4. Cross-Platform Contributor Operations | 0/3 | Not started | - |
| 5. Dependency Risk Management | 0/3 | Not started | - |
| 6. Chunked Extraction Architecture | 4/4 | Complete | 2026-03-25 |
