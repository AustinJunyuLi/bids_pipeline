# Requirements: v2.2 Reconciliation Lift + Surface Repair

**Defined:** 2026-04-01
**Core Value:** Raise benchmark-facing accuracy by repairing the highest-value
deterministic v2 gaps while preserving filing-grounded extraction and the
post-export benchmark boundary.

## Milestone Basis

Grounded in:

- `diagnosis/gptpro/2026-04-01/round_1/v2_analytical_gap_inventory_3aa65f7.md`
- `diagnosis/gptpro/2026-04-01/round_1/reponse.md`

## v2.2 Requirements

### Proposal Fidelity

- [x] **LINK-01**: proposal phase association ignores future-linked `requested_by_observation_id` values and falls back to the latest same-day-or-earlier solicitation
- [x] **LINK-02**: proposal analyst rows use proposal-local formality cues plus repaired phase context to classify `bid_type`
- [x] **LINK-03**: v2 gates block proposal links that point to non-solicitations or forward in time

### Transition And Outcome Fidelity

- [x] **TRANS-01**: `EXIT-03` and `EXIT-04` use the strongest filing-supported elimination date instead of defaulting every loss to the narrowing or execution date
- [x] **TRANS-02**: executed, restarted, and terminated rows prefer bidder or bidder-cohort actors and carry an anchored date when the filing supports one
- [x] **TRANS-03**: solicitation participant scope is recoverable enough for round rows and transitions through literal extraction, deterministic backfill, or explicit review output

### Analyst Surface Fidelity

- [x] **SURFACE-01**: agreement-family rows preserve distinct analyst event types for NDA amendments, exclusivity, standstills, and clean-team agreements
- [x] **SURFACE-02**: process-boundary rows cover bidder-originated sale approaches and advisor termination in an analyst-comparable way
- [x] **SURFACE-03**: analyst exports do not present proxy `sort_date` values as exact `date_recorded`; precision is surfaced explicitly
- [x] **SURFACE-04**: enterprise-value-only proposals export a usable value surface

### Contract And Validation Hardening

- [x] **CONTRACT-01**: the v2 observation prompt plus extract/verify skill docs require solicitation recipients, chronology-safe proposal links, bidder-scoped outcomes, and distinct agreement families
- [x] **CONTRACT-02**: v2 gates emit blocker or warning findings for missing named solicitation recipients, under-specified substantive outcomes, proxy-date leakage, and lossy agreement-family collapse

### Legacy Retirement

- [x] **RETIRE-01**: the live CLI, canonical `.claude/skills/` tree, mirrored skill trees, and repo docs expose only the live v2 workflow in the working tree
- [x] **RETIRE-02**: live v2 modules no longer import legacy v1 runtime modules, and any shared logic needed by v2 is extracted into neutral non-legacy modules
- [x] **RETIRE-03**: `data/legacy/v1/` and other v1-only working-tree artifacts are removed after the recovery path is pinned through Git history, milestone archives, and an explicit Git tag
- [x] **RETIRE-04**: regression tests and contract docs are rewritten so the repo operates cleanly without the legacy v1 runtime, skills, archive, or migration path

## Out of Scope

- benchmark-driven generation logic or pre-export benchmark consultation
- manual benchmark row editing to force reconciliation
- non-filing-grounded inference that changes event meaning beyond the supporting text
- UI or product-layer work unrelated to the extraction pipeline

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| LINK-01 | Phase 20 | Satisfied |
| LINK-02 | Phase 20 | Satisfied |
| LINK-03 | Phase 20 | Satisfied |
| TRANS-01 | Phase 21 | Satisfied |
| TRANS-02 | Phase 21 | Satisfied |
| TRANS-03 | Phase 21 | Satisfied |
| SURFACE-01 | Phase 22 | Satisfied |
| SURFACE-02 | Phase 22 | Satisfied |
| SURFACE-03 | Phase 22 | Satisfied |
| SURFACE-04 | Phase 22 | Satisfied |
| CONTRACT-01 | Phase 23 | Satisfied |
| CONTRACT-02 | Phase 23 | Satisfied |
| RETIRE-01 | Phase 24 | Satisfied |
| RETIRE-02 | Phase 24 | Satisfied |
| RETIRE-03 | Phase 24 | Satisfied |
| RETIRE-04 | Phase 24 | Satisfied |

**Coverage:**

- v2.2 requirements: 16 total
- Satisfied in phase verification reports: 16
- Unsatisfied or orphaned requirements: 0

---
*v2.1 requirement details moved to [milestones/v2.1-REQUIREMENTS.md](milestones/v2.1-REQUIREMENTS.md). v2.2 was extended on 2026-04-01 with Phase 24 for v1 retirement follow-on work.*
