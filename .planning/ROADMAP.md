# Roadmap: Filing-Grounded Pipeline Redesign

## Milestones

- **v1.0 Filing-Grounded Pipeline Redesign** -- Phases 1-5 (shipped 2026-03-28) -- [archive](milestones/v1.0-ROADMAP.md)
- **v1.1 Reconciliation + Execution-Log Quality Fixes** -- Phases 6-9 (complete 2026-03-30)
- **v2.0 Observation Graph Architecture** -- Phases 10-16 (in progress)

## Phases

<details>
<summary>v1.0 Filing-Grounded Pipeline Redesign (Phases 1-5) -- SHIPPED 2026-03-28</summary>

See [v1.0 archive](milestones/v1.0-ROADMAP.md) for full phase details.

- [x] **Phase 1: Foundation + Annotation** - Block metadata enrichment in preprocessing
- [x] **Phase 2: Prompt Architecture** - Provider-neutral prompt packet composition
- [x] **Phase 3: Quote-Before-Extract** - Filing-grounded evidence protocol
- [x] **Phase 4: Enhanced Gates** - Semantic validation stage
- [x] **Phase 5: Integration + Calibration** - DuckDB storage, complexity routing, export

</details>

<details>
<summary>v1.1 Reconciliation + Execution-Log Quality Fixes (Phases 6-9) -- COMPLETE 2026-03-30</summary>

- [x] **Phase 6: Deterministic Hardening** - Mixed-schema guard, canonicalize collisions, NDA tolerance, DuckDB lock retry
- [x] **Phase 7: bid_type Rule Priority** - Final-round proposal classification fix
- [x] **Phase 8: Extraction Guidance + Enrichment Extensions** - Skill doc updates, DropTarget classification, all_cash inference
- [x] **Phase 9: Deal-Specific Fixes + Revalidation** - Zep/Medivation re-extraction, 9-deal reconciliation improvement

</details>

### v2.0 Observation Graph Architecture

- [x] **Phase 10: Pre-Migration Fixes** - Isolate all-cash bug fix and structured coverage records before any v2 work (completed 2026-03-31)
- [x] **Phase 11: Foundation Models + Path Contracts** - v2 Pydantic models and artifact directory structure (completed 2026-03-31)
- [x] **Phase 12: Artifact Loading + Canonicalization** - v2 extract loading, mode detection, and span resolution (completed 2026-03-31)
- [x] **Phase 13: Validation Stack** - Structural checks, structured coverage, and graph semantic gates for v2 observations (completed 2026-03-31)
- [x] **Phase 14: Derivation Engine** - Rule-based derivation of analyst rows from observation graph (completed 2026-03-31)
- [x] **Phase 15: DuckDB Integration + Export** - v2 tables, triple export surface, and legacy adapter (completed 2026-03-31)
- [x] **Phase 16: Extraction Contract + Migration** - v2 prompt composition, skill docs, STEC validation, and 9-deal migration (completed 2026-03-31)

## Phase Details

### Phase 10: Pre-Migration Fixes
**Goal**: Known v1 bugs are fixed and re-baselined in isolation so that v2 benchmark comparisons have a clean attribution boundary
**Depends on**: Nothing (independent fixes against v1 codebase)
**Requirements**: FIX-01, FIX-02
**Success Criteria** (what must be TRUE):
  1. Running `skill-pipeline enrich-core` on deals with all-cash consideration no longer short-circuits incorrectly -- the `_infer_all_cash_overrides()` fix is verified by regression tests and affected deals are re-baselined through db-export
  2. `CoverageCheckRecord` exists as a structured Pydantic model with status (observed/derived/not_found/ambiguous), reason codes, and observation references -- free-text `coverage_notes` is no longer the coverage output contract
  3. The 9-deal benchmark match rate is re-measured after the bug fix so v2 comparisons start from a corrected baseline
**Plans**:
  - `10-01` All-cash fallback control-flow fix plus regression coverage
  - `10-02` Structured `CoverageCheckRecord` contract for coverage detail artifacts
  - `10-03` Affected-deal reruns and corrected v1 baseline documentation

### Phase 11: Foundation Models + Path Contracts
**Goal**: All v2 Pydantic models exist as importable, tested schema definitions and v2 artifact paths are registered in `SkillPathSet`
**Depends on**: Phase 10 (bug fixes establish clean baseline before v2 schema work)
**Requirements**: MODEL-01, MODEL-02, MODEL-03, MODEL-04, MODEL-05, MODEL-06, INFRA-03
**Success Criteria** (what must be TRUE):
  1. `PartyRecord` can be instantiated with role, bidder_kind, advisor_kind, advised_party_id, and evidence_span_ids -- round-trip JSON serialization preserves all fields
  2. `CohortRecord` can represent unnamed group lifecycles with exact_count, known_member_party_ids, unknown_member_count, and parent lineage -- validated against PetSmart-style nesting patterns
  3. All 6 observation subtypes (Process, Agreement, Solicitation, Proposal, Status, Outcome) deserialize correctly via Pydantic discriminated union on `obs_type`, including observation-to-observation references (revises, supersedes, requested_by, related)
  4. `DerivationBasis` and all derived record types (ProcessPhaseRecord, LifecycleTransitionRecord, CashRegimeRecord, JudgmentRecord, AnalystRowRecord) are defined with provenance fields
  5. `SkillPathSet` exposes `extract_v2/` and `export_v2/` directory paths and v1 paths remain unchanged
**Plans**:
  - `11-01` Additive `models_v2.py` schema module plus focused validation tests
  - `11-02` Additive v2 `SkillPathSet` path contract, regression coverage, and `CLAUDE.md` memory update

### Phase 12: Artifact Loading + Canonicalization
**Goal**: v2 extract artifacts can be loaded, mode-detected (v1 vs v2), and canonicalized with span resolution using the existing span infrastructure
**Depends on**: Phase 11 (v2 models must exist for loading and canonicalization)
**Requirements**: INFRA-01, INFRA-02
**Success Criteria** (what must be TRUE):
  1. v2 artifact loading correctly distinguishes v1 and v2 payloads on disk and returns the appropriate typed objects without cross-contamination
  2. v2 canonicalization resolves observation quotes to spans using the existing `_resolve_quotes_to_spans` machinery and writes a shared `spans.json` sidecar
  3. A `canonicalize-v2` CLI command exists and completes successfully on synthetic v2 test fixtures
**Plans**:
  - `12-01` Separate v2 loader module plus explicit v1/v2 version routing
  - `12-02` `canonicalize-v2` runtime path, CLI wiring, fixture tests, and memory update

### Phase 13: Validation Stack
**Goal**: v2 observations pass through structural, coverage, and semantic validation gates that catch schema errors, coverage gaps, and graph-level inconsistencies before derivation
**Depends on**: Phase 12 (validated v2 loading required for check/coverage/gates to consume observations)
**Requirements**: VALID-01, VALID-02, VALID-03
**Success Criteria** (what must be TRUE):
  1. `check_v2` rejects observations missing evidence spans, unresolved party/cohort references, and proposals without bidder subjects -- verified by failing-input test fixtures
  2. `coverage_v2` generates structured `CoverageCheckRecord` entries for every expected observation with status and reason codes, replacing free-text coverage notes entirely for v2
  3. `gates_v2` validates graph-level invariants: revision/supersession chains are acyclic, cohort child counts do not exceed parent, and deadlines occur after their solicitations
  4. All three validation stages have CLI commands and produce JSON report artifacts under `data/skill/<slug>/`
**Plans**:
  - `13-01` `check_v2` structural runtime, report typing, and failing-fixture regression coverage
  - `13-02` `coverage_v2` structured coverage generation from source cues and canonical observations
  - `13-03` `gates_v2` graph invariants, CLI wiring, and repo-memory updates

### Phase 14: Derivation Engine
**Goal**: A deterministic rule engine transforms validated observation graphs into derived analytical records (rounds, exits, cash regimes, agreements, analyst rows, judgments) with explicit provenance on every output
**Depends on**: Phase 13 (derivation requires validated observation graph; validation gates must pass before derivation runs)
**Requirements**: DERIVE-01, DERIVE-02, DERIVE-03, DERIVE-04, DERIVE-05, DERIVE-06
**Success Criteria** (what must be TRUE):
  1. Round derivation rules (ROUND-01 informal, ROUND-02 formal) produce `ProcessPhaseRecord` from `SolicitationObservation` with correct phase boundaries
  2. Exit inference rules (EXIT-01 through EXIT-04) produce `LifecycleTransitionRecord` covering literal withdrawal, cannot-improve, not-invited, and lost-to-winner patterns
  3. Cash regime rules (CASH-01 through CASH-03) produce `CashRegimeRecord` from explicit terms, merger agreements, and phase-level inference without the all-cash short-circuit bug
  4. `AnalystRowRecord` compilation produces graph-linked, filing-grounded rows with `subject_ref`, `row_count`, date/terms fields, and `DerivationBasis` provenance tracing back to source observations and spans; benchmark-expanded anonymous slot emission remains deferred to Phase 15 export
  5. `JudgmentRecord` captures genuinely ambiguous cases (initiation, advisory link, ambiguous exit, ambiguous phase) with explicit human-review flags rather than silent defaults
**Plans**:
  - `14-01` Schema alignment plus gated derive skeleton for rounds, cash regimes, and judgments
  - `14-02` Exit derivation plus graph-linked analyst-row compilation
  - `14-03` Live derive CLI, artifact writing, parser coverage, and memory updates

### Phase 15: DuckDB Integration + Export
**Goal**: v2 observations and derived records load into DuckDB via additive schema and export through a triple CSV surface plus a legacy adapter that maps v2 analyst rows back to v1 CSV shape for benchmark regression
**Depends on**: Phase 14 (derivation engine must produce the records that DB integration loads and exports)
**Requirements**: EXPORT-01, EXPORT-02, EXPORT-03
**Success Criteria** (what must be TRUE):
  1. v2 DuckDB tables (`v2_parties`, `v2_cohorts`, `v2_observations`, `v2_derivations`, `v2_coverage_checks`) are created additively alongside v1 tables without modifying existing schema
  2. Triple export produces `literal_observations.csv`, `analyst_rows.csv`, and `benchmark_rows_expanded.csv` from DuckDB queries under `data/skill/<slug>/export_v2/`, with optional synthetic anonymous slot expansion only in `benchmark_rows_expanded.csv`
  3. Legacy adapter maps v2 analyst rows to the v1 14-column CSV shape, verified by byte-level comparison tests against known v1 export outputs
  4. `db-load-v2` and `db-export-v2` CLI commands exist and complete successfully on synthetic fixtures
**Plans**:
  - `15-01` Additive DuckDB schema plus `db-load-v2`
  - `15-02` `db-export-v2` triple surface and benchmark-only anonymous expansion
  - `15-03` Legacy adapter, CLI wiring, parser coverage, and memory updates

### Phase 16: Extraction Contract + Migration
**Goal**: The LLM extraction contract narrows to filing-literal observations, STEC validates end-to-end through the v2 pipeline, and all 9 deals are migrated with benchmark comparison against v1 baseline
**Depends on**: Phase 15 (full deterministic v2 pipeline must be operational before extraction skill docs are finalized and deals are migrated)
**Requirements**: EXTRACT-01, EXTRACT-02, EXTRACT-03, EXTRACT-04, EXTRACT-05
**Success Criteria** (what must be TRUE):
  1. v2 prompt composition mode produces extraction packets that instruct the LLM to emit parties, cohorts, and 6 observation types with quote/span support -- not analyst rows
  2. `/extract-deal-v2` and `/verify-extraction-v2` skill docs exist under `.claude/skills/` with filing-grounded examples for each observation subtype
  3. STEC is extracted end-to-end through the v2 pipeline (extract -> canonicalize-v2 -> check-v2 -> coverage-v2 -> gates-v2 -> derive -> db-load-v2 -> db-export-v2) and the legacy adapter output is compared against v1 STEC export
  4. All 9 deals are extracted through v2 with per-deal validation and the legacy adapter benchmark comparison shows the observation graph captures information that the v1 flat event taxonomy structurally could not
**Plans**:
  - `16-01` v2 prompt composition contract, validator routing, and skill-doc surface
  - `16-02` deterministic v1->v2 migration bridge plus migration hardening for bidder-interest, extension rounds, and coverage parity
  - `16-03` STEC reference validation, 9-deal migration, and benchmark comparison summary

## Progress

**Execution Order:**
Phases execute in numeric order: 10 -> 11 -> 12 -> 13 -> 14 -> 15 -> 16

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
| 9. Deal-Specific Fixes + Revalidation | v1.1 | 3/3 | Complete | 2026-03-30 |
| 10. Pre-Migration Fixes | v2.0 | 3/3 | Complete   | 2026-03-31 |
| 11. Foundation Models + Path Contracts | v2.0 | 2/2 | Complete   | 2026-03-31 |
| 12. Artifact Loading + Canonicalization | v2.0 | 2/2 | Complete | 2026-03-31 |
| 13. Validation Stack | v2.0 | 3/3 | Complete | 2026-03-31 |
| 14. Derivation Engine | v2.0 | 3/3 | Complete | 2026-03-31 |
| 15. DuckDB Integration + Export | v2.0 | 3/3 | Complete | 2026-03-31 |
| 16. Extraction Contract + Migration | v2.0 | 3/3 | Complete | 2026-03-31 |

---
*Roadmap created: 2026-03-29*
*v2.0 phases added: 2026-03-30*
*For full v1.0 phase details, see [v1.0 archive](milestones/v1.0-ROADMAP.md).*
