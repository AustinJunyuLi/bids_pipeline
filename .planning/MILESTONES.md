# Milestones

## v1.0 Filing-Grounded Pipeline Redesign (Shipped: 2026-03-28)

**Phases completed:** 5 phases, 16 plans, 36 tasks

**Archive:** [v1.0 roadmap](milestones/v1.0-ROADMAP.md), [v1.0 requirements](milestones/v1.0-REQUIREMENTS.md), [v1.0 audit](milestones/v1.0-MILESTONE-AUDIT.md)

---

## v1.1 Reconciliation + Execution-Log Quality Fixes (Complete: 2026-03-30)

**Phases completed:** 4 phases (6-9), 10 plans

**Key accomplishments:**

- mixed-schema hardening and canonicalization fixes
- bid-type rule priority correction
- extraction guidance and deterministic enrichment improvements
- 9-deal reconciliation uplift

---

## v2.0 Observation Graph Architecture (Shipped: 2026-03-31)

**Phases completed:** 7 phases (10-16), 19 plans

**Archive:** [v2.0 roadmap](milestones/v2.0-ROADMAP.md), [v2.0 requirements](milestones/v2.0-REQUIREMENTS.md), [v2.0 audit](milestones/v2.0-MILESTONE-AUDIT.md)

**Key accomplishments:**

- quote-first observation graph with typed parties, cohorts, and observations
- canonical v2 validation stack
- deterministic derivation engine
- additive DuckDB `v2_*` schema and triple export surface
- 9-deal migration to the v2 extraction contract

---

## v2.1 V2 Default Cutover + Legacy Archive (Complete: 2026-03-31)

**Phases completed:** 3 phases (17-19)

**Key accomplishments:**

- `/deal-agent` and `/reconcile-alex` now point at the live v2 workflow
- explicit legacy skills preserve the retired v1 path
- v1 outputs archived under `data/legacy/v1/`
- live `data/pipeline.duckdb` rebuilt from v2 artifacts only
- repo docs and tests now enforce the live/legacy split
