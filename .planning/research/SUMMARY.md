# Project Research Summary

**Project:** Filing-Grounded M&A Extraction Pipeline -- v2.0 Observation Graph
**Domain:** Brownfield architecture migration (additive v2 beside existing v1)
**Researched:** 2026-03-30
**Confidence:** HIGH

## Executive Summary

The v2.0 observation graph architecture is a well-scoped brownfield redesign of an existing 9-deal M&A extraction pipeline. The core thesis -- that the v1 flat 20-type `SkillEventRecord` conflates filing facts, analytical interpretations, and export row shapes, causing systematic extraction loss -- is strongly supported by the GPT Pro architectural review and validated against concrete deal failures (STEC informal rounds, PetSmart unnamed cohorts, Penford NDA chains, Medivation stale coverage notes). The research consistently finds that the correct approach is to build v2 models and stages in parallel alongside v1, never modifying v1 contracts until v2 is validated across all 9 deals. This is not a rewrite; it is a disciplined additive migration.

The recommended approach requires zero new dependencies. The existing stack -- Python 3.13, Pydantic 2.12 (discriminated unions), DuckDB 1.4 (JSON columns, additive schema evolution), and pytest 8 -- provides every capability the architecture needs. The v2 data model introduces 6 typed observation subtypes via Pydantic discriminated unions, separates named parties from unnamed cohorts, and replaces the interleaved enrichment logic with a deterministic rule engine carrying explicit derivation provenance. Approximately 2,320 lines of new code are estimated across 11 new modules, with roughly 140 lines of modifications to existing files.

The dominant risk is breaking the operational v1 pipeline during migration. The v1 contract has 12+ downstream consumers that depend on exact field names and model shapes, and Pydantic's `extra="forbid"` makes any schema mismatch a hard validation failure. The mitigation is strict additivity: new files (`models_v2.py`, `derive.py`, `db_load_v2.py`), new directories (`extract_v2/`, `export_v2/`), new DuckDB tables (`v2_parties`, `v2_observations`), and a legacy adapter for backward-compatible benchmarking. A pre-migration all-cash bug fix must be isolated and re-baselined before any v2 work begins.

## Key Findings

### Recommended Stack

No dependency changes required. Every capability for the v2 architecture is provided by the installed stack. This is the strongest possible starting position for a brownfield migration -- zero dependency risk.

**Core technologies (all existing, verified against installed versions):**
- **Pydantic 2.12.5:** Discriminated unions on `obs_type` for type-safe polymorphic observation deserialization. Round-trip serialization verified. `extra="forbid"` on `SkillModel` base class enforces structural integrity.
- **DuckDB 1.4.4:** `CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ADD COLUMN IF NOT EXISTS`, `JSON` column type for polymorphic observation storage. Additive schema evolution is proven (existing `all_cash_override` migration).
- **Python 3.13:** `StrEnum` for observation kind enums, full typing support including `Literal` discriminators.
- **pytest 8:** `tmp_path` fixtures, existing factory-function test patterns. No test framework additions needed.

**Explicitly rejected additions:** networkx (graph too small), hypothesis (domain constraints too specific), business-rules/PyKE (12 rules, plain callables suffice), alembic (DuckDB additive DDL is enough), factory_boy (existing fixture style works).

### Expected Features

**Must have (table stakes -- v2 fails without these):**
- **TS-1: 6 typed observation subtypes** (Process, Agreement, Solicitation, Proposal, Status, Outcome) replacing the 20-type flat event taxonomy
- **TS-2: PartyRecord** replacing SkillActorRecord (drops grouped fields, adds `role: "other"`)
- **TS-3: CohortRecord** for unnamed group lifecycle tracking (PetSmart's 15->6->4 cohort nesting)
- **TS-4: Deterministic derivation engine** with rule catalog (ROUND, EXIT, CASH, AGREEMENT families) producing analyst rows with `DerivationBasis` provenance
- **TS-5: CoverageCheckRecord** replacing free-text `coverage_notes` with structured records
- **TS-6: Legacy adapter** (v2 -> v1 CSV shape) for benchmark regression testing

**Should have (differentiators -- the reason to build v2):**
- **D-1: Triple export surface** (literal_observations.csv, analyst_rows.csv, benchmark_rows_expanded.csv)
- **D-2: Observation-to-observation references** (proposal revision chains, agreement supersession, solicitation-response links)
- **D-3: Derivation provenance and review flags** (every derived fact traceable to source observations and filing spans)

**Defer (v2+):**
- **D-4: Mismatch classification** in reconciliation (6 mismatch families) -- valuable but non-blocking
- **D-5: Parallel v1/v2 execution framework** -- achievable with simple path separation during migration
- Interpretive enrichment for v2 -- existing `/enrich-deal` skill works on v1; v2 interpretive layer waits

### Architecture Approach

The architecture follows a "parallel beside, not surgery on" principle. Eleven new modules are added alongside the existing pipeline, sharing only version-independent infrastructure (raw fetch, preprocess, span resolution, DuckDB connection plumbing, date normalization). The v2 pipeline has its own artifact directories (`extract_v2/`, `export_v2/`), its own DuckDB tables (`v2_` prefix), and its own CLI commands (`check-v2`, `db-load-v2`). A legacy adapter maps v2 analyst rows back to the v1 CSV shape so existing reconciliation infrastructure measures v2 quality against the 70.7% benchmark baseline.

**Major components:**
1. **models_v2.py** (~350 lines) -- All Pydantic models: PartyRecord, CohortRecord, 6 observation subtypes via discriminated union, CoverageCheckRecord, DerivationBasis, derived record types (ProcessPhaseRecord, LifecycleTransitionRecord, CashRegimeRecord, JudgmentRecord, AnalystRowRecord)
2. **derive.py** (~500 lines) -- Deterministic rule engine with dependency-ordered execution: round derivation, exit inference, cash regime, analyst row compilation. Each rule is a pure function producing `DerivationBasis`-backed records.
3. **Validation stack** (check_v2.py ~200, coverage_v2.py ~200, gates_v2.py ~250) -- Three-layer validation matching v1 precedent: structural checks, structured coverage generation, graph-level semantic gates (acyclic chains, deadline ordering, cohort arithmetic)
4. **DuckDB integration** (db_schema_v2.py ~80, db_load_v2.py ~200, db_export_v2.py ~250, legacy_adapter.py ~150) -- New tables with `v2_` prefix, triple export, and backward-compatible CSV mapping

### Critical Pitfalls

1. **Premature v1 contract removal breaks 12+ downstream consumers.** Every v1 model has `extra="forbid"`, so any field rename or removal is a hard deserialization failure across all 9 deals. Prevention: v2 models are NEW classes; never modify v1 classes during migration.

2. **All-cash short-circuit bug fix must be isolated from v2 migration.** The bug in `_infer_all_cash_overrides()` changes existing artifact output. Fixing it during v2 work makes benchmark changes unattributable. Prevention: fix and re-baseline BEFORE starting any v2 work.

3. **LLM prompt changes affect all 9 deals simultaneously.** No per-deal prompt versioning exists. Prevention: create a separate v2 extraction skill doc (`/extract-deal-v2`) and migrate deals one at a time with per-deal validation.

4. **Legacy adapter CSV shape must be byte-identical to v1 export.** The v1 export has 14 columns with specific formatting rules across 5+ helper functions. Any mismatch contaminates benchmark comparison. Prevention: byte-level diff tests between v1 and v2 adapter outputs for deals with both pipelines.

5. **Derivation rule complexity creep from undeclared dependencies.** Rules interact (EXIT-03 depends on ROUND-01/02 having already run; CASH-03 depends on cycle segmentation). Prevention: explicit rule dependency DAG with topological execution order, declared before any rule implementation.

## Implications for Roadmap

Based on combined research, the dependency chain is clear: models -> artifact loading -> validation -> derivation -> export -> extraction skill. The feature dependency graph (FEATURES.md) and architecture build order (ARCHITECTURE.md) agree on this sequencing. All four research files independently converge on the same phase structure with one pre-migration step.

### Pre-Phase: Isolate Bug Fix and Re-Baseline

**Rationale:** The all-cash short-circuit bug fix changes v1 artifact output. PITFALLS.md (Pitfall 4) and FEATURES.md (MVP Recommendation) both identify this as mandatory pre-migration work. Conflating the bug fix with v2 migration makes benchmark changes unattributable.
**Delivers:** Fixed `_infer_all_cash_overrides()`, re-run enrichment and export for affected deals, new baseline match rate.
**Addresses:** Immediate correctness improvement independent of v2.
**Avoids:** Pitfall 4 (semantic change during architecture migration).

### Phase 1: Foundation Models and Path Contracts

**Rationale:** Every subsequent component depends on the v2 Pydantic models existing. The models are pure schema definitions with no runtime impact until extraction uses them. Path additions are mechanical.
**Delivers:** `models_v2.py` (PartyRecord, CohortRecord, 6 observation subtypes, CoverageCheckRecord, DerivationBasis, all derived record types), v2 path additions to `SkillPathSet`.
**Addresses:** TS-1 (schema), TS-2, TS-3, TS-5 (schema), D-2 (schema), D-3 (schema).
**Avoids:** Pitfall 1 (additive models only), Pitfall 7 (validate cohort model against real deal data), Pitfall 9 (establish ID prefix conventions).

### Phase 2: Artifact Loading and Canonicalization

**Rationale:** Artifact loading is required by every downstream v2 stage. Span resolution for v2 reuses existing `_resolve_quotes_to_spans` with minimal adaptation.
**Delivers:** `extract_artifacts_v2.py`, v2 canonicalization path, `canonicalize-v2` CLI command.
**Addresses:** Prerequisite infrastructure for all subsequent phases.
**Avoids:** Pitfall 12 (span reuse -- shared `spans.json`, do not modify SpanRecord).

### Phase 3: Validation Stack

**Rationale:** Validation must be in place before derivation. The v1 pipeline learned this lesson -- `enrich_core.py` requires all gates to pass. Building validation first catches schema bugs in models_v2.py early.
**Delivers:** `check_v2.py` (structural checks), v2 path in `verify.py` (span verification), `coverage_v2.py` (structured coverage), `gates_v2.py` (graph semantic gates).
**Addresses:** TS-5 (full implementation), v2-specific structural checks, graph-level gates.
**Avoids:** Anti-Pattern 4 from ARCHITECTURE.md (building derivation before validation).

### Phase 4: Derivation Engine

**Rationale:** The derivation engine is the core intellectual contribution of v2. It depends on validated observation graphs. Building incrementally by rule family enables testing each family against known deals.
**Delivers:** `derive.py` with rule families (ROUND-01/02, EXIT-01-04, CASH-01-03, AGREEMENT-01), `DerivedArtifactV2`, `derive` CLI command.
**Addresses:** TS-4 (full implementation), D-3 (DerivationBasis on every record).
**Avoids:** Pitfall 6 (explicit rule DAG, topological execution order), Pitfall 13 (provenance storage design before rules).

### Phase 5: DuckDB Integration and Export

**Rationale:** DB integration is the terminal deterministic stage. The legacy adapter enables running existing reconciliation infrastructure against v2 outputs.
**Delivers:** v2 DuckDB tables (`v2_parties`, `v2_cohorts`, `v2_observations`, `v2_derivations`, `v2_coverage_checks`), `db_load_v2.py`, `db_export_v2.py` (triple export), `legacy_adapter.py` (v2 -> v1 CSV).
**Addresses:** TS-6 (legacy adapter), D-1 (triple export surface).
**Avoids:** Pitfall 2 (additive tables only, no v1 schema changes), Pitfall 5 (byte-level CSV comparison tests), Pitfall 10 (parallel reconciliation during migration).

### Phase 6: Extraction Contract and Migration

**Rationale:** Extraction skill docs depend on the finalized observation model, validation stack, and export surface. The extraction contract narrows compared to v1 -- the LLM extracts filing-literal observations, not analyst rows.
**Delivers:** v2 prompt composition mode, `/extract-deal-v2` skill doc, `/verify-extraction-v2` skill doc, per-deal migration across 9-deal corpus.
**Addresses:** All TS and D features at the extraction layer.
**Avoids:** Pitfall 3 (separate v2 skill doc, per-deal migration), Pitfall 14 (monitor `other` enum usage rates).

### Phase Ordering Rationale

- **Dependency chain is strict:** models -> loading -> validation -> derivation -> export -> extraction. Each phase produces the inputs the next phase requires.
- **Risk reduction by ordering:** The highest-risk components (models, validation) come first when they can be tested in isolation. The derivation engine -- the most complex new component -- builds on a validated foundation.
- **Bug fix isolation (pre-phase) prevents attribution confusion.** Every research file independently identifies this requirement.
- **Testing is continuous, not phased.** PITFALLS.md (Pitfall 8) requires parallel v1/v2 test suites from Phase 1 onward. v1 tests are frozen; v2 tests grow with each phase.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (Models):** CohortRecord edge cases need validation against real deal data -- PetSmart approximate counts, temporal count changes, overlapping memberships (Pitfall 7). The `exact_count` field may need renaming to `count` with a `count_precision` qualifier.
- **Phase 4 (Derivation Engine):** Rule dependency DAG design requires careful analysis of cross-rule interactions. The GPT Pro rule catalog has ~10 rules but their interdependencies are implicit. Must be made explicit before implementation.
- **Phase 6 (Extraction Contract):** v2 extraction prompt design for 6 observation subtypes (instead of 20-type flat list) is the highest-uncertainty deliverable. The LLM must produce filing-literal observations without reverting to analyst-row production.

Phases with standard patterns (skip phase research):
- **Phase 2 (Artifact Loading):** Follows established `extract_artifacts.py` pattern. Well-documented in codebase.
- **Phase 3 (Validation Stack):** Follows established check/verify/coverage/gates pattern. v1 precedent provides clear templates.
- **Phase 5 (DuckDB Integration):** Follows established `db_load.py`/`db_export.py` pattern. Additive DDL is proven.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Zero new dependencies. All capabilities verified by running code against installed versions. |
| Features | HIGH | Feature catalog maps directly to diagnosed v1 failures across 9 deals. GPT Pro review provides concrete rule catalog. |
| Architecture | HIGH | Live codebase analysis (5,000+ lines reviewed). Component boundaries, data flow, and coexistence strategy grounded in actual module dependencies. |
| Pitfalls | HIGH | Every pitfall grounded in specific code locations (line numbers, function names, module dependencies). Prevention strategies are concrete and testable. |

**Overall confidence:** HIGH

### Gaps to Address

- **CohortRecord schema for approximate counts:** The `exact_count` field assumes precision that filing text often does not provide ("approximately 15 parties"). Needs validation against 3+ deals before schema is finalized. Handle during Phase 1 planning.

- **Derivation rule interaction testing:** The rule catalog lists ~10 rules, but cross-rule dependencies (EXIT-03 depending on ROUND-01/02 output) are described conceptually, not formally. The dependency DAG must be designed as the first task of Phase 4.

- **v2 extraction prompt effectiveness:** No empirical evidence yet that the LLM can reliably produce the 6 observation types with the quality required for deterministic derivation. This is the highest-uncertainty aspect of the entire v2 effort. Handle by extracting a single reference deal (STEC) before committing to 9-deal migration.

- **Legacy adapter fidelity across all 14 CSV columns:** The v1 export has formatting rules spread across 5+ helper functions. Byte-identical reproduction through the v2 adapter has not been tested. Handle during Phase 5 with synthetic test fixtures.

## Sources

### Primary (HIGH confidence -- live codebase verification)
- Pydantic 2.12.5: discriminated unions, `extra="forbid"`, `model_dump(mode="json")` -- verified against installed version
- DuckDB 1.4.4: JSON columns, `CREATE TABLE IF NOT EXISTS`, `ALTER TABLE ADD COLUMN IF NOT EXISTS` -- verified against installed version
- Live codebase modules: `models.py` (596 lines), `enrich_core.py` (739 lines), `db_schema.py` (142 lines), `db_load.py` (385 lines), `db_export.py` (456 lines), `extract_artifacts.py` (94 lines), `check.py` (256 lines), `verify.py` (586 lines), `coverage.py` (423 lines), `gates.py` (603 lines), `canonicalize.py` (566 lines)
- Existing test suite: `test_skill_enrich_core.py` (33 tests), `test_skill_db_load.py`, ~10,600 total test lines

### Secondary (HIGH confidence -- expert architectural review)
- GPT Pro architectural review (2026-03-31): `diagnosis/gptpro/2026-03-31/round_1/response.md` -- 570-line structural review identifying 7 bottlenecks and proposing observation graph architecture
- 9-deal benchmark corpus: 70.7% (157/222) atomic match rate baseline

### Tertiary (MEDIUM confidence -- conceptual validation needed)
- CohortRecord schema adequacy for approximate counts and temporal changes -- needs validation against real deal data
- v2 extraction prompt effectiveness for 6 observation types -- needs empirical testing
- Rule dependency DAG completeness -- needs formal specification

---
*Research completed: 2026-03-30*
*Ready for roadmap: yes*
