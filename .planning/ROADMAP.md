# Roadmap: Filing-Grounded Pipeline Redesign

## Milestones

- **v1.0 Filing-Grounded Pipeline Redesign** -- Phases 1-5 (shipped 2026-03-28) -- [archive](milestones/v1.0-ROADMAP.md)
- **v1.1 Reconciliation + Execution-Log Quality Fixes** -- Phases 6-9 (complete 2026-03-30)
- **v2.0 Observation Graph Architecture** -- Phases 10-16 (shipped 2026-03-31) -- [archive](milestones/v2.0-ROADMAP.md)
- **v2.1 V2 Default Cutover + Legacy Archive** -- Phases 17-19 (complete 2026-03-31) -- [archive](milestones/v2.1-ROADMAP.md)
- **v2.2 Reconciliation Lift + Surface Repair** -- Phases 20-24 (complete 2026-04-01) -- [audit](milestones/v2.2-MILESTONE-AUDIT.md)
- **v2.3 Structured Field Recovery** -- Phases 25-29 (in progress)

## Current Milestone

### v2.3 Structured Field Recovery

- [ ] **Phase 25: Repair Module + Field Parsers** - build the deterministic repair module with all field extractors, classifiers, and their unit tests
- [ ] **Phase 26: Canonicalize Integration** - wire the repair module into canonicalize.py in both quote-first and canonical modes with integration tests
- [ ] **Phase 27: Semantic Completeness Gates** - add blocker and warning findings to gates_v2.py for missing cue-backed structured fields
- [ ] **Phase 28: Prompt + Schema Hardening** - add structured field completeness obligations to prompts, worked examples, and schema guidance
- [ ] **Phase 29: Re-Extraction Validation** - validate repair + prompt changes across all 9 existing deals and 3 re-extracted deals

## Phase Details

### Phase 25: Repair Module + Field Parsers
**Goal**: A standalone repair module exists that can deterministically extract structured fields from observation summaries and linked evidence spans, with unit tests proving each parser and classifier works correctly in isolation
**Depends on**: Phase 24 complete
**Requirements**: REPR-01, REPR-03, REPR-04, PRICE-01, PRICE-02, PRICE-03, CTYPE-01, CTYPE-02, DLVR-01, DLVR-02, BKIND-01, BKIND-02, BOOL-01, BOOL-02, BOOL-03, TEST-01, TEST-02
**Success Criteria** (what must be TRUE):
  1. Running the repair module on an observation with a price in its summary but null `per_share` populates `per_share` with the correct headline value and leaves already-populated fields untouched
  2. The price parser correctly disambiguates headline totals from component amounts in mixed offers (e.g., "$21.50 including $19.00 cash and $2.50 CVR" yields `per_share=21.50`, `consideration_type=mixed`, null ranges)
  3. Consideration type, delivery mode, and secondary booleans are recovered from filing cues when the corresponding structured field is null, with false-positive guards rejecting financing language and out-of-scope mentions
  4. Bidder kind classification returns a value only when one class has strong dominant evidence from the filing; ambiguous cases remain `unknown`
  5. Unit tests pass for all parser and classifier paths including edge cases (later-vs-earlier prices, stock-price false positives, each delivery mode, ambiguous bidder kind, and all three secondary boolean patterns)
**Plans**: TBD

### Phase 26: Canonicalize Integration
**Goal**: The repair module runs automatically during canonicalization in both processing modes, with integration tests proving fill-only behavior and idempotence
**Depends on**: Phase 25
**Requirements**: REPR-02, TEST-03
**Success Criteria** (what must be TRUE):
  1. Running `skill-pipeline canonicalize-v2 --deal <slug>` invokes the repair layer immediately before final Pydantic validation in both quote-first and canonical modes
  2. Re-running canonicalize on already-repaired observations produces identical output (idempotent)
  3. Populated fields are never overwritten by repair -- only null or missing fields are filled
  4. Integration tests cover canonical-mode repair, quote-first-mode repair, idempotence, and the fill-only invariant
**Plans**: TBD

### Phase 27: Semantic Completeness Gates
**Goal**: The validation gates detect and report structured fields that should have been populated based on surface cues but were not, blocking or warning before export
**Depends on**: Phase 26
**Requirements**: GATE-01, GATE-02, TEST-04
**Success Criteria** (what must be TRUE):
  1. `skill-pipeline gates-v2 --deal <slug>` produces blocker findings for proposals where surface text contains price or range cues but `per_share` or `range_low/high` remain null after repair
  2. `skill-pipeline gates-v2 --deal <slug>` produces warning findings for missing `consideration_type`, `delivery_mode`, `bidder_kind`, and secondary booleans when surface cues exist in the observation text
  3. Gate tests verify that findings are generated for observations with cue-backed gaps and not generated when fields are correctly populated
  4. Prompt render tests assert that new enforcement language is present in the rendered observation prompt
**Plans**: TBD

### Phase 28: Prompt + Schema Hardening
**Goal**: The extraction prompts and schema reference explicitly require structured field population, with worked examples showing correct extraction patterns so future LLM extractions produce fewer missing fields
**Depends on**: Phase 25
**Requirements**: PRMT-01, PRMT-02, PRMT-03, PRMT-04
**Success Criteria** (what must be TRUE):
  1. The rendered observations prompt contains an explicit structured field completeness block that frames field population as an obligation, not a suggestion
  2. The observations prompt contains a bidder kind completeness block requiring `bidder_kind` when the filing gives a literal cue
  3. Worked examples in the prompt cover range-to-range_low/high mapping, mixed-offer headline totals, delivery mode mapping, and parenthetical bidder kind classification
  4. `schema_ref.py` generates semantic guidance for `MoneyTerms.per_share`, `range_low`, `range_high`, `Proposal.delivery_mode`, and `PartyRecord.bidder_kind` that is included in the prompt context
**Plans**: TBD

### Phase 29: Re-Extraction Validation
**Goal**: The full pipeline with repair layer, gates, and prompt changes runs cleanly across all existing deals and shows measurable improvement on re-extracted deals
**Depends on**: Phase 26, Phase 27, Phase 28
**Requirements**: VALID-01, VALID-02
**Success Criteria** (what must be TRUE):
  1. All 9 existing deals pass `canonicalize-v2 -> derive -> db-export-v2 -> gates-v2` through the repair layer without regression (no new blocker findings, no previously passing fields now null)
  2. 3-deal re-extraction (mac-gray, petsmart-inc, imprivata) after prompt changes produces measurably more populated structured fields compared to pre-v2.3 extraction output
  3. No benchmark material is consulted before the export boundary during validation
**Plans**: TBD

## Progress

| Phase | Milestone | Status | Completed |
|-------|-----------|--------|-----------|
| 25. Repair Module + Field Parsers | v2.3 | Not started | - |
| 26. Canonicalize Integration | v2.3 | Not started | - |
| 27. Semantic Completeness Gates | v2.3 | Not started | - |
| 28. Prompt + Schema Hardening | v2.3 | Not started | - |
| 29. Re-Extraction Validation | v2.3 | Not started | - |

---
*Roadmap created: 2026-04-04 for milestone v2.3 Structured Field Recovery*
