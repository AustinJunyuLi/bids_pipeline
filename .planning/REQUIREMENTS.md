# Requirements: v2.0 Observation Graph Architecture

**Defined:** 2026-03-30
**Core Value:** Produce the most correct filing-grounded structured deal record
possible from raw text, by separating filing-literal observations from
analyst-derived rows so that cohort lifecycles, process structure, agreement
chains, and consideration regimes are correctly captured.

## v2.0 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Pre-Migration Fixes

- [ ] **FIX-01**: All-cash short-circuit bug in `_infer_all_cash_overrides()` fixed and re-baselined across affected deals
- [ ] **FIX-02**: Free-text `coverage_notes` replaced with structured `CoverageCheckRecord` keyed to observations with reason codes

### Schema / Models

- [ ] **MODEL-01**: `PartyRecord` replacing `SkillActorRecord` with role, bidder_kind, advisor_kind, advised_party_id, evidence_span_ids
- [ ] **MODEL-02**: `CohortRecord` for unnamed group lifecycle tracking with exact_count, known_member_party_ids, unknown_member_count, parent lineage
- [ ] **MODEL-03**: 6 typed observation subtypes (Process, Agreement, Solicitation, Proposal, Status, Outcome) via Pydantic discriminated union on `obs_type`
- [ ] **MODEL-04**: `DerivationBasis` with rule_id, source_observation_ids, source_span_ids, confidence, explanation on every derived record
- [ ] **MODEL-05**: Observation-to-observation references: `revises_observation_id`, `supersedes_observation_id`, `requested_by_observation_id`, `related_observation_id`
- [ ] **MODEL-06**: Derived record types: `ProcessPhaseRecord`, `LifecycleTransitionRecord`, `CashRegimeRecord`, `JudgmentRecord`, `AnalystRowRecord`

### Artifact Infrastructure

- [ ] **INFRA-01**: v2 extract artifact loading with mode detection distinguishing v1 and v2 payloads
- [ ] **INFRA-02**: v2 canonicalization path resolving v2 observation quotes to spans
- [ ] **INFRA-03**: v2 path additions to `SkillPathSet` (`extract_v2/`, `export_v2/` directories)

### Validation Stack

- [ ] **VALID-01**: `check_v2` structural validation: every observation has evidence spans, all party/cohort refs resolve, proposals have bidder subject
- [ ] **VALID-02**: `coverage_v2` generates structured `CoverageCheckRecord` from observations with status (observed/derived/not_found/ambiguous) and reason codes
- [ ] **VALID-03**: `gates_v2` graph semantic validation: acyclic revision/supersession chains, cohort child counts <= parent, deadlines after solicitations

### Derivation Engine

- [ ] **DERIVE-01**: Round derivation rules (ROUND-01 informal, ROUND-02 formal) producing `ProcessPhaseRecord` from `SolicitationObservation`
- [ ] **DERIVE-02**: Exit inference rules (EXIT-01 literal withdrawal, EXIT-02 cannot-improve, EXIT-03 not-invited, EXIT-04 lost-to-winner) producing `LifecycleTransitionRecord`
- [ ] **DERIVE-03**: Cash regime rules (CASH-01 explicit, CASH-02 merger agreement, CASH-03 phase-level inference) producing `CashRegimeRecord`
- [ ] **DERIVE-04**: Agreement rule (AGREEMENT-01 supersession/amendment) producing analyst NDA-family rows
- [ ] **DERIVE-05**: `AnalystRowRecord` compilation from observations + derived records with origin (literal/derived/synthetic_anonymous)
- [ ] **DERIVE-06**: `JudgmentRecord` for genuinely ambiguous cases (initiation, advisory link, ambiguous exit, ambiguous phase)

### DuckDB / Export

- [ ] **EXPORT-01**: v2 DuckDB tables (`v2_parties`, `v2_cohorts`, `v2_observations`, `v2_derivations`, `v2_coverage_checks`) with additive schema
- [ ] **EXPORT-02**: Triple export surface: `literal_observations.csv`, `analyst_rows.csv`, `benchmark_rows_expanded.csv`
- [ ] **EXPORT-03**: Legacy adapter mapping v2 analyst rows to v1 CSV shape with byte-level comparison tests

### Extraction Contract

- [ ] **EXTRACT-01**: v2 prompt composition mode producing filing-literal observation extraction packets
- [ ] **EXTRACT-02**: `/extract-deal-v2` skill doc instructing LLM to emit parties, cohorts, and 6 observation types with quote/span support
- [ ] **EXTRACT-03**: `/verify-extraction-v2` skill doc for v2 artifact repair
- [ ] **EXTRACT-04**: STEC reference deal extracted and validated end-to-end through v2 pipeline
- [ ] **EXTRACT-05**: Remaining 8 deals extracted and validated through v2 pipeline with benchmark comparison

## Future Requirements

Deferred to future milestone. Tracked but not in current roadmap.

### Reconciliation Improvements

- **RECON-01**: Mismatch classification into 6 stable families (literal missing, derived missing, anonymous expansion gap, policy disagreement, date precision, benchmark error)
- **RECON-02**: Reconciliation surface comparison on analyst-row layer while retaining literal-observation audit surface

### Interpretive Enrichment v2

- **ENRICH-V2-01**: Interpretive enrichment skill doc for v2 observation graph (dropout classifications, initiation judgment, advisory verification)

### v1 Deprecation

- **DEPRECATE-01**: Remove v1 extraction contract and v1-only stages after v2 is stable on 9+ deals

## Out of Scope

| Feature | Reason |
|---------|--------|
| Graph database backend (Neo4j, etc.) | DuckDB is sufficient for 9-deal corpus; observation graph is hundreds of nodes per deal |
| LLM-based derivation rules | Defeats determinism; derivation must be rule-based with explicit provenance |
| Dynamic schema evolution framework | Breaks Pydantic type safety; additive DDL is sufficient |
| Synthetic slot expansion in core model | Fake identities corrupt derivation; expansion is export-only |
| Benchmark-driven extraction rules | v2 breaks this feedback loop by design; filing text is sole source of truth |
| Interpretive enrichment in derivation engine | Muddies provenance boundary; keep deterministic and interpretive separate |
| UI or product surface | Backend pipeline focused |
| New deal onboarding beyond 9-deal corpus | v2 validates on existing calibration set first |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FIX-01 | — | Pending |
| FIX-02 | — | Pending |
| MODEL-01 | — | Pending |
| MODEL-02 | — | Pending |
| MODEL-03 | — | Pending |
| MODEL-04 | — | Pending |
| MODEL-05 | — | Pending |
| MODEL-06 | — | Pending |
| INFRA-01 | — | Pending |
| INFRA-02 | — | Pending |
| INFRA-03 | — | Pending |
| VALID-01 | — | Pending |
| VALID-02 | — | Pending |
| VALID-03 | — | Pending |
| DERIVE-01 | — | Pending |
| DERIVE-02 | — | Pending |
| DERIVE-03 | — | Pending |
| DERIVE-04 | — | Pending |
| DERIVE-05 | — | Pending |
| DERIVE-06 | — | Pending |
| EXPORT-01 | — | Pending |
| EXPORT-02 | — | Pending |
| EXPORT-03 | — | Pending |
| EXTRACT-01 | — | Pending |
| EXTRACT-02 | — | Pending |
| EXTRACT-03 | — | Pending |
| EXTRACT-04 | — | Pending |
| EXTRACT-05 | — | Pending |

**Coverage:**
- v2.0 requirements: 28 total
- Mapped to phases: 0
- Unmapped: 28

---
*Requirements defined: 2026-03-30*
*Last updated: 2026-03-30 after initial definition*
