# Roadmap: Filing-Grounded Pipeline Redesign

## Milestones

- **v1.0 Filing-Grounded Pipeline Redesign** -- Phases 1-5 (shipped 2026-03-28) -- [archive](milestones/v1.0-ROADMAP.md)
- **v1.1 Reconciliation + Execution-Log Quality Fixes** -- Phases 6-9

## Phases

- [x] **Phase 6: Deterministic Hardening** - Fix runtime walls from 7-deal rerun: mixed-schema loader guard, canonicalize collisions, gates+coverage rollover-CA tolerance, DuckDB lock retry (HARD-02/03 already satisfied)
- [x] **Phase 7: bid_type Rule Priority** - Fix highest-impact enrichment bug: final-round proposals misclassified as Informal across 5+ deals
- [x] **Phase 8: Extraction Guidance + Enrichment Extensions** - Update skill docs for round milestones, verbal indications, NDA exclusion; add DropTarget classification and contextual all_cash inference
- [ ] **Phase 9: Deal-Specific Fixes + Revalidation** - Fix Zep/Medivation extraction errors, re-extract affected deals, validate improved match rate across 9-deal corpus

## Phase Details

### Phase 6: Deterministic Hardening
**Goal**: Pipeline deterministic stages handle all documented edge cases from the 7-deal rerun without crashing, producing false findings, or accepting corrupt inputs
**Depends on**: Nothing (independent fixes)
**Requirements**: HARD-06, HARD-01, HARD-04, HARD-05 (HARD-02 and HARD-03 already satisfied during 7-deal rerun)
**Execution order**: HARD-06 -> HARD-01 -> HARD-04 -> HARD-05
**Success Criteria** (what must be TRUE):
  1. Loading extract artifacts where actors are canonical but events are quote-first (or vice versa) raises a dedicated `MixedSchemaError` before any stage processes them
  2. Running `skill-pipeline canonicalize` on a deal with overlapping actor/event quote_id namespaces completes without crash, produces unique cross-array quote_ids, rewrites all references consistently, and is idempotent on reruns; same-array duplicates still fail-fast
  3. Running `skill-pipeline gates` and `skill-pipeline coverage` on deals with rollover-side confidentiality agreements does not produce false NDA findings (covers rollover, bidder-bidder teaming, and target-on-target diligence CAs)
  4. Running `skill-pipeline db-export` immediately after `db-load` succeeds without DuckDB file-lock errors; bounded retry with exponential backoff on transient lock; non-lock errors not retried; exhausted retries surface a hard failure
**Plans**: 06-01 (complete), 06-02 (complete), 06-03 (complete)

### Phase 7: bid_type Rule Priority
**Goal**: Enrichment correctly classifies final-round proposals as Formal when process position (after final round announcement) overrides IOI filing language
**Depends on**: Phase 6 (hardened pipeline required for clean re-enrichment runs)
**Requirements**: ENRICH-01
**Success Criteria** (what must be TRUE):
  1. Running `skill-pipeline enrich-core` on stec, mac-gray, imprivata, penford, and providence-worcester produces `bid_type: Formal` for proposals occurring after the final round announcement
  2. Running `skill-pipeline enrich-core` on deals with early-stage IOIs (before any formal round) still produces `bid_type: Informal` -- the fix does not over-promote
  3. The `_classify_proposal()` function in enrich_core.py evaluates process-position rules before IOI-language rules, with regression tests covering both orderings
**Plans:** 1 plan
Plans:
- [x] 07-01-PLAN.md -- Reorder _classify_proposal() rule priority with TDD regression tests

### Phase 8: Extraction Guidance + Enrichment Extensions
**Goal**: Extraction skill docs cover round milestones, verbal indications, and NDA exclusions; enrichment adds deterministic DropTarget classification and contextual all_cash inference
**Depends on**: Phase 7 (skill docs must reference corrected bid_type behavior; enrichment extensions build on corrected rule infrastructure)
**Requirements**: EXTRACT-01, EXTRACT-02, EXTRACT-03, ENRICH-02, ENRICH-03
**Success Criteria** (what must be TRUE):
  1. Extraction skill docs contain explicit guidance and filing-grounded examples for round milestone events (Final Round Inf Ann, Final Round Inf, deadlines) such that a new extraction run can produce them
  2. Extraction skill docs contain explicit guidance and examples for verbal/oral price indications drawn from mac-gray and penford filing patterns
  3. Extraction skill docs contain explicit NDA exclusion guidance that distinguishes rollover-side and non-target confidentiality agreements from sale-process NDAs
  4. Running `skill-pipeline enrich-core` on a deal with committee-driven field narrowing produces deterministic DropTarget dropout classifications from round invitation context while preserving bidder-withdrawal-first directionality
  5. Running `skill-pipeline enrich-core` on a deal where the executed event has explicit cash consideration propagates all_cash=true to proposals that lack explicit per-proposal mention, while deals with mixed consideration (e.g., cash+CVR) are not falsely tagged
**Plans:** 1/3 plans executed
Plans:
- [x] 08-01-PLAN.md -- Add round milestone, verbal indication, and NDA exclusion guidance to extraction skill docs
- [x] 08-02-PLAN.md -- Add DropTarget classification and all_cash inference to enrich_core.py
- [x] 08-03-PLAN.md -- Wire dropout_classifications and all_cash_overrides through DB schema, load, and export

### Phase 9: Deal-Specific Fixes + Revalidation
**Goal**: Known extraction errors in Zep and Medivation are corrected, affected deals are re-extracted with updated skill docs, and cross-deal reconciliation shows measurable improvement
**Depends on**: Phase 8 (updated skill docs and enrichment extensions required before re-extraction)
**Requirements**: EXTRACT-04, EXTRACT-05, RERUN-01, RERUN-02
**Success Criteria** (what must be TRUE):
  1. Zep events_raw.json no longer lists NMC in the actor_ids for evt_005 and evt_008
  2. Medivation events_raw.json contains evt_013 and evt_017 with filing-grounded evidence quotes
  3. All affected deals have been re-extracted and successfully pass the full deterministic pipeline (canonicalize through db-export) without errors
  4. 9-deal reconciliation re-run shows a higher atomic match rate and fewer filing-contradicted pipeline claims compared to the pre-v1.1 baseline
**Plans:** 3/3 plans executed
Plans:
- [x] 09-01-PLAN.md -- Re-extract Zep and run full deterministic pipeline through db-export
- [x] 09-02-PLAN.md -- Re-extract Medivation and run full deterministic pipeline through db-export
- [x] 09-03-PLAN.md -- Run 9-deal reconciliation and measure improvement against baseline

## Progress

| Phase | Milestone | Plans | Status | Completed |
|-------|-----------|-------|--------|-----------|
| 1. Foundation + Annotation | v1.0 | 3/3 | Complete | 2026-03-27 |
| 2. Prompt Architecture | v1.0 | 3/3 | Complete | 2026-03-27 |
| 3. Quote-Before-Extract | v1.0 | 5/5 | Complete | 2026-03-28 |
| 4. Enhanced Gates | v1.0 | 2/2 | Complete | 2026-03-28 |
| 5. Integration + Calibration | v1.0 | 3/3 | Complete | 2026-03-28 |
| 6. Deterministic Hardening | v1.1 | 3/3 | Complete | 2026-03-29 |
| 7. bid_type Rule Priority | v1.1 | 1/1 | Complete | 2026-03-30 |
| 8. Extraction Guidance + Enrichment Extensions | v1.1 | 3/3 | Complete | 2026-03-30 |
| 9. Deal-Specific Fixes + Revalidation | v1.1 | 3/3 | In Progress |   |

---
*Roadmap created: 2026-03-29*
*For full v1.0 phase details, see [v1.0 archive](milestones/v1.0-ROADMAP.md).*
