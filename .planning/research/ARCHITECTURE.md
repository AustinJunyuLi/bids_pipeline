# Architecture Patterns: v2.0 Observation Graph Integration

**Domain:** Filing-grounded M&A extraction pipeline (brownfield redesign)
**Researched:** 2026-03-30
**Overall confidence:** HIGH (based on live codebase analysis + GPT Pro architectural review)

## Recommended Architecture

### Design Principle: Parallel v2 Beside v1, Not Surgery On v1

The v2 observation graph is a fundamentally different data model from the v1
event-first contract. Attempting to stretch `SkillEventRecord` into the new
shape would break every downstream consumer simultaneously. The correct approach
is to build v2 models and stages in parallel, reuse the existing infrastructure
that does not need to change (fetch, preprocess, span resolution, DuckDB
plumbing), and add a legacy adapter that maps v2 outputs back to the v1 CSV
shape for backward-compatible benchmarking.

### System Diagram

```
                   EXISTING (UNCHANGED)                   NEW v2 COMPONENTS
              +--------------------------+          +---------------------------+
              |  raw-fetch               |          |                           |
              |  preprocess-source       |          |  models_v2.py             |
              |  compose-prompts (base)  |          |  (PartyRecord,            |
              |  spans / provenance      |          |   CohortRecord,           |
              |  DuckDB plumbing         |          |   6 Observation subtypes, |
              |  normalize/              |          |   CoverageCheckRecord)    |
              +-----------+--------------+          +---------------------------+
                          |                                    |
                          v                                    v
              +-----------+--------------+          +----------+----------------+
              |  v1 extract loading      |          |  extract_artifacts_v2.py  |
              |  (extract_artifacts.py)  |          |  (load v2 artifacts)      |
              +-----------+--------------+          +----------+----------------+
                          |                                    |
         v1 pipeline      |                    v2 pipeline     |
              +-----------|----+                  +------------|---+
              | check.py       |                  | check_v2.py    |
              | verify.py      |                  | verify.py (*)  |
              | coverage.py    |                  | coverage_v2.py |
              | gates.py       |                  | gates_v2.py    |
              | enrich_core.py |                  | derive.py      |
              +-----------|----+                  +------------|---+
                          |                                    |
              +-----------|----+                  +------------|---+
              | db_load.py     |                  | db_load_v2.py  |
              | db_export.py   |                  | db_export_v2.py|
              +----------------+                  +-------|--------+
                                                          |
                                                  +-------v--------+
                                                  | legacy_adapter |
                                                  | (v2 -> v1 CSV) |
                                                  +----------------+
```

(`*` = verify.py gains a v2 code path; span verification is model-independent)

---

## Component Inventory: New vs Modified vs Unchanged

### NEW Components (build from scratch)

| Component | File | Purpose | Lines (est) |
|-----------|------|---------|-------------|
| v2 models | `models_v2.py` | PartyRecord, CohortRecord, 6 Observation subtypes, CoverageCheckRecord, DerivationBasis, derived record types | ~350 |
| v2 extract loader | `extract_artifacts_v2.py` | Load `observations.json` artifact, validate schema, provide typed access | ~80 |
| Derivation engine | `derive.py` | Rule-based engine: round derivation, exit inference, cohort lifecycle, cash regime, analyst row compilation | ~500 |
| v2 check | `check_v2.py` | Structural validation for observation graph (evidence presence, ref integrity, cohort math) | ~200 |
| v2 coverage | `coverage_v2.py` | Structured CoverageCheckRecord generation from observation graph + source cues | ~200 |
| v2 gates | `gates_v2.py` | Graph-level semantic gates (acyclic chains, deadline ordering, cohort consistency) | ~250 |
| v2 DuckDB schema | `db_schema_v2.py` | New tables: parties, cohorts, observations, derivations, coverage_checks | ~80 |
| v2 db-load | `db_load_v2.py` | Load observation graph + derivations into DuckDB | ~200 |
| v2 db-export | `db_export_v2.py` | Triple export: literal_observations.csv, analyst_rows.csv, benchmark_rows_expanded.csv | ~250 |
| Legacy adapter | `legacy_adapter.py` | Map v2 analyst rows back to v1 CSV shape for backward-compatible benchmarking | ~150 |
| v2 CLI commands | (in `cli.py`) | New subcommands for v2 stages | ~60 |

**Total new code: ~2,320 lines estimated**

### MODIFIED Components (targeted changes)

| Component | File | Change | Risk |
|-----------|------|--------|------|
| `canonicalize.py` | Add v2 path that resolves quotes to spans for observation artifacts (reuse `_resolve_quotes_to_spans`) | LOW -- existing span resolution logic is generic |
| `cli.py` | Register v2 subcommands | LOW -- additive only |
| `paths.py` + `SkillPathSet` | Add v2 artifact paths (observations.json, derivations.json, coverage_checks.json, v2 export paths) | LOW -- additive fields |
| `verify.py` | Add v2 code path for quote-to-span verification on observation artifacts | MEDIUM -- needs to handle new evidence_span_ids layout |
| `db_schema.py` | Add v2 tables via migration DDL (additive, does not touch v1 tables) | LOW -- additive |
| `enrich_core.py` | Fix all-cash short-circuit bug at line 674 (v1 fix, immediate value) | LOW -- isolated bugfix |

### UNCHANGED Components (reuse as-is)

| Component | Why Unchanged |
|-----------|---------------|
| `raw/` fetch stages | Filing ingress is contract-version-independent |
| `preprocess/` source stages | Chronology blocks and evidence items feed both v1 and v2 |
| `provenance.py` | Span resolution is generic -- works for any quote/block pair |
| `normalize/` | Date parsing, quote normalization are version-independent |
| `pipeline_models/` | Source models (ChronologyBlock, EvidenceItem) are shared |
| `seeds.py` | Seed roster is pipeline-version-independent |
| `config.py` | Global config unchanged |
| `complexity.py` | Block-count routing is version-independent |

---

## Component Boundaries

### models_v2.py -- The v2 Data Model

**Responsibility:** Define all Pydantic models for the observation graph layer.

**Communicates with:** extract_artifacts_v2.py, derive.py, check_v2.py, db_load_v2.py

**Key design decisions:**

1. **Inherit from `SkillModel`**, not a new base. This preserves `extra="forbid"`,
   `model_config`, and serialization conventions established in the v1 codebase.

2. **Reuse existing shared types** -- `ResolvedDate`, `MoneyTerms`, `SpanRecord`,
   `SpanRegistryArtifact`, `SkillExclusionRecord` are all version-independent.
   They live in `models.py` and `pipeline_models/common.py` and work for both
   v1 and v2.

3. **Discriminated union for observations** via `obs_type` field, exactly as
   proposed in the GPT Pro review. Pydantic's
   `Annotated[Union[...], Field(discriminator="obs_type")]` gives type-safe
   deserialization. The v1 codebase already uses Literal types extensively for
   `event_type` discrimination -- this extends the same approach.

4. **CoverageCheckRecord replaces `coverage_notes: list[str]`** -- structured
   records with `cue_family`, `status`, `supporting_observation_ids`, and
   `reason_code`. This eliminates the stale-prose drift problem documented in
   the GPT Pro review (Part 1, section 5).

5. **PartyRecord extends SkillActorRecord's fields** with one critical addition:
   it drops the `is_grouped` / `group_size` / `group_label` fields. Group
   semantics move to `CohortRecord`. A party is always an individual entity.

6. **CohortRecord is entirely new** -- replaces grouped actors and free-text
   `RawCountAssertion`. Cohorts have parent-child lineage, member tracking, and
   a mandatory `created_by_observation_id` back-reference.

```python
# models_v2.py -- key type sketches

class PartyRecord(SkillModel):
    party_id: str
    display_name: str
    canonical_name: str | None = None
    aliases: list[str] = Field(default_factory=list)
    role: Literal["bidder", "advisor", "activist", "target_board", "other"]
    bidder_kind: Literal["strategic", "financial", "unknown"] | None = None
    advisor_kind: Literal["financial", "legal", "other"] | None = None
    advised_party_id: str | None = None
    listing_status: Literal["public", "private"] | None = None
    geography: Literal["domestic", "non_us"] | None = None
    evidence_span_ids: list[str] = Field(default_factory=list)

class CohortRecord(SkillModel):
    cohort_id: str
    label: str
    parent_cohort_id: str | None = None
    exact_count: int
    known_member_party_ids: list[str] = Field(default_factory=list)
    unknown_member_count: int
    membership_basis: str
    created_by_observation_id: str
    evidence_span_ids: list[str] = Field(default_factory=list)

class CoverageCheckRecord(SkillModel):
    cue_family: str
    status: Literal["observed", "derived", "not_found", "ambiguous"]
    supporting_observation_ids: list[str] = Field(default_factory=list)
    supporting_span_ids: list[str] = Field(default_factory=list)
    reason_code: str | None = None
    note: str | None = None

class ObservationArtifactV2(SkillModel):
    parties: list[PartyRecord]
    cohorts: list[CohortRecord]
    observations: list[Observation]  # discriminated union
    exclusions: list[SkillExclusionRecord] = Field(default_factory=list)
    coverage: list[CoverageCheckRecord] = Field(default_factory=list)
```

### extract_artifacts_v2.py -- v2 Artifact Loading

**Responsibility:** Load, validate, and provide typed access to v2 observation
artifacts from disk.

**Communicates with:** models_v2.py (types), derive.py / check_v2.py / gates_v2.py (consumers)

**Key design decisions:**

1. **Separate loader from v1** -- do not add v2 detection logic into
   `extract_artifacts.py`. The v1 loader has complex mode detection
   (quote_first vs canonical at lines 40-83) that does not apply to v2. v2
   artifacts are always canonical (span-backed from the start or canonicalized
   from quotes).

2. **Fail-fast** on missing or malformed artifacts. No silent fallbacks. Same
   discipline as v1's `MixedSchemaError`.

3. **Return a typed dataclass** similar to `LoadedExtractArtifacts` but with
   v2-specific fields and indexes.

```python
@dataclass
class LoadedObservationArtifacts:
    observations: ObservationArtifactV2
    spans: SpanRegistryArtifact
    derivations: DerivedArtifactV2 | None = None

    @property
    def span_index(self) -> dict[str, SpanRecord]:
        return {span.span_id: span for span in self.spans.spans}

    @property
    def party_index(self) -> dict[str, PartyRecord]:
        return {p.party_id: p for p in self.observations.parties}

    @property
    def cohort_index(self) -> dict[str, CohortRecord]:
        return {c.cohort_id: c for c in self.observations.cohorts}

    @property
    def observation_index(self) -> dict[str, Observation]:
        return {o.observation_id: o for o in self.observations.observations}
```

### derive.py -- Deterministic Derivation Engine

**Responsibility:** Replace the interleaved enrichment logic in `enrich_core.py`
with a structured rule engine over the observation graph. This is where v2's
real intelligence lives.

**Communicates with:** extract_artifacts_v2.py (reads observations), models_v2.py (types), db_load_v2.py (writes derivations to DuckDB)

**Key design decisions:**

1. **Rule catalog, not deal heuristics.** Each rule has a stable ID, operates on
   observation types (not deal names), and produces derived records with full
   provenance via `DerivationBasis`.

2. **Rule families map to current enrich_core logic:**

| v1 Function (enrich_core.py) | v2 Rule Family | What Changes |
|------------------------------|----------------|--------------|
| `_pair_rounds()` (lines 170-212) | ROUND-01, ROUND-02 | Derives from SolicitationObservation, not event type pairs |
| `_classify_proposals()` (lines 299-310) | Built into AnalystRowRecord compilation | Classification is a property of the derived row, not a sidecar |
| `_segment_cycles()` (lines 313-344) | Cycle derivation from Process/Outcome observations | Cycles come from observation semantics, not `restarted` event scanning |
| `_classify_dropouts()` (lines 564-635) | EXIT-01 through EXIT-04 | Derives from StatusObservation, not drop event heuristics |
| `_infer_all_cash_overrides()` (lines 638-689) | CASH-01 through CASH-03 | CashRegimeRecord at phase/cycle level, not sparse event overrides |
| `_compute_formal_boundary()` (lines 347-385) | Part of phase derivation | Boundary is a property of ProcessPhaseRecord |
| `_populate_invited_from_count_assertions()` (lines 388-482) | Cohort lifecycle in derive.py | Invitation is modeled via CohortRecord membership, not anchor-text matching |

3. **Execution order is dependency-driven:**
   - Step 1: Process phases from solicitation/agreement observations
   - Step 2: Lifecycle transitions from status/outcome observations
   - Step 3: Cash regime from proposal + outcome observations
   - Step 4: Analyst row compilation from all of the above

4. **Every derived record carries `DerivationBasis`** with `rule_id`,
   `source_observation_ids`, `source_span_ids`, `confidence`, and `explanation`.

5. **Gate-before-derive** -- derive.py refuses to run unless check_v2, verify,
   coverage_v2, and gates_v2 all pass. Same pattern as enrich_core.py lines 47-81.

```python
class DerivedArtifactV2(SkillModel):
    phases: list[ProcessPhaseRecord]
    transitions: list[LifecycleTransitionRecord]
    cash_regimes: list[CashRegimeRecord]
    judgments: list[JudgmentRecord]
    analyst_rows: list[AnalystRowRecord]
```

### Validation Stack (check_v2.py, coverage_v2.py, gates_v2.py)

**Responsibility:** Three-layer validation matching the existing v1 pattern but
operating on observation graph structure.

**Layer separation (matching v1 precedent):**

| Layer | v1 Module | v2 Module | What It Validates |
|-------|-----------|-----------|-------------------|
| Structural | check.py (256 lines) | check_v2.py | Evidence presence, ref integrity, proposal terms, cohort math |
| Quote/span | verify.py (586 lines) | verify.py (shared v2 path) | Anchor text matches filing text. Model-independent. |
| Coverage | coverage.py (423 lines) | coverage_v2.py | Source cue coverage via CoverageCheckRecord |
| Semantic | gates.py (603 lines) | gates_v2.py | Graph-level gates: acyclic chains, deadline ordering, cohort counts |

**v2-specific structural checks (check_v2.py):**
- Every observation must have `evidence_span_ids`
- Every `subject_refs` and `counterparty_refs` entry must resolve to a party_id or cohort_id
- Proposals must have a bidder subject and either terms or a reason code
- Agreements with `supersedes_observation_id` must point to another agreement
- Every cohort must satisfy `unknown_member_count == exact_count - len(known_member_party_ids)`

**v2-specific graph gates (gates_v2.py):**
- Cohort child counts cannot exceed parent counts
- Revision and supersession chains must be acyclic
- Deadlines cannot precede their solicitations
- Execution/exclusivity cannot happen before the winning party becomes active

**Key difference from v1:** Coverage becomes a first-class structured output
(list of `CoverageCheckRecord`) rather than a side-audit. The coverage stage
both validates existing coverage records AND generates new ones from source
evidence items.

---

## DuckDB Schema Evolution

**Strategy: New tables alongside v1 tables. No v1 table modifications.**

The v1 DuckDB schema has 6 tables (defined in `db_schema.py` lines 13-99):
`actors`, `events`, `spans`, `enrichment`, `cycles`, `rounds`. These remain
untouched for v1 pipeline runs.

v2 adds new tables with a `v2_` prefix to prevent collision:

```sql
CREATE TABLE IF NOT EXISTS v2_parties (
    deal_slug TEXT NOT NULL,
    party_id TEXT NOT NULL,
    display_name TEXT NOT NULL,
    canonical_name TEXT,
    aliases TEXT[],
    role TEXT NOT NULL,
    bidder_kind TEXT,
    advisor_kind TEXT,
    advised_party_id TEXT,
    listing_status TEXT,
    geography TEXT,
    evidence_span_ids TEXT[],
    PRIMARY KEY (deal_slug, party_id)
);

CREATE TABLE IF NOT EXISTS v2_cohorts (
    deal_slug TEXT NOT NULL,
    cohort_id TEXT NOT NULL,
    label TEXT NOT NULL,
    parent_cohort_id TEXT,
    exact_count INTEGER NOT NULL,
    known_member_party_ids TEXT[],
    unknown_member_count INTEGER NOT NULL,
    membership_basis TEXT NOT NULL,
    created_by_observation_id TEXT NOT NULL,
    evidence_span_ids TEXT[],
    PRIMARY KEY (deal_slug, cohort_id)
);

CREATE TABLE IF NOT EXISTS v2_observations (
    deal_slug TEXT NOT NULL,
    observation_id TEXT NOT NULL,
    obs_type TEXT NOT NULL,
    date_raw_text TEXT,
    date_sort DATE,
    date_precision TEXT,
    subject_refs TEXT[],
    counterparty_refs TEXT[],
    summary TEXT NOT NULL,
    evidence_span_ids TEXT[],
    type_fields JSON,
    PRIMARY KEY (deal_slug, observation_id)
);

CREATE TABLE IF NOT EXISTS v2_derivations (
    deal_slug TEXT NOT NULL,
    record_id TEXT NOT NULL,
    record_type TEXT NOT NULL,
    rule_id TEXT NOT NULL,
    confidence TEXT NOT NULL,
    source_observation_ids TEXT[],
    source_span_ids TEXT[],
    record_fields JSON NOT NULL,
    PRIMARY KEY (deal_slug, record_id)
);

CREATE TABLE IF NOT EXISTS v2_coverage_checks (
    deal_slug TEXT NOT NULL,
    cue_family TEXT NOT NULL,
    status TEXT NOT NULL,
    supporting_observation_ids TEXT[],
    supporting_span_ids TEXT[],
    reason_code TEXT,
    note TEXT
);
```

**Why `v2_` prefix:** DuckDB supports schemas but the existing pipeline uses a
flat namespace. Adding schema support is unnecessary complexity for a 9-deal
corpus. The prefix is explicit, grep-friendly, and requires zero infrastructure
changes.

**Why JSON for type-specific fields:** Each observation subtype has different
fields (SolicitationObservation has `requested_submission`, `due_date`,
`recipient_refs`; ProposalObservation has `terms`, `delivery_mode`, etc.).
A JSON column avoids 30+ sparse columns. Pydantic enforces schema at the Python
layer. DuckDB's JSON functions provide query-time access.

**Spans table is SHARED** between v1 and v2. The `SpanRecord` format is
model-independent -- it maps quotes to filing line ranges regardless of whether
the quote came from an event or an observation.

---

## Data Flow

### v2 End-to-End Pipeline

```
data/seeds.csv
  -> skill-pipeline raw-fetch --deal <slug>              [UNCHANGED]
  -> raw/<slug>/*
  -> skill-pipeline preprocess-source --deal <slug>       [UNCHANGED]
  -> data/deals/<slug>/source/*
  -> skill-pipeline compose-prompts-v2 --deal <slug>      [NEW prompt mode]
  -> data/skill/<slug>/prompt_v2/*
  -> /extract-deal-v2 <slug>                              [NEW local-agent skill]
  -> data/skill/<slug>/extract_v2/observations_raw.json
  -> skill-pipeline canonicalize-v2 --deal <slug>         [NEW CLI command]
  -> data/skill/<slug>/extract_v2/observations.json
  -> data/skill/<slug>/extract_v2/spans.json              [SHARED format]
  -> skill-pipeline check-v2 --deal <slug>                [NEW]
  -> skill-pipeline verify-v2 --deal <slug>               [NEW or modified verify]
  -> skill-pipeline coverage-v2 --deal <slug>             [NEW]
  -> skill-pipeline gates-v2 --deal <slug>                [NEW]
  -> /verify-extraction-v2 <slug>                         [NEW local-agent skill]
  -> skill-pipeline derive --deal <slug>                  [NEW]
  -> data/skill/<slug>/derive/derivations.json
  -> skill-pipeline db-load-v2 --deal <slug>              [NEW]
  -> skill-pipeline db-export-v2 --deal <slug>            [NEW]
  -> data/skill/<slug>/export_v2/literal_observations.csv
  -> data/skill/<slug>/export_v2/analyst_rows.csv
  -> data/skill/<slug>/export_v2/benchmark_rows_expanded.csv
```

### v1 Pipeline Continues Unchanged

All existing v1 commands, artifacts, and DuckDB tables remain operational.
A deal can have both v1 and v2 artifacts simultaneously during migration.

---

## Artifact Path Contract for v2

New paths added to `SkillPathSet`:

```python
# Additive fields in paths.py
extract_v2_dir: Path            # data/skill/<slug>/extract_v2/
observations_raw_path: Path     # data/skill/<slug>/extract_v2/observations_raw.json
observations_path: Path         # data/skill/<slug>/extract_v2/observations.json
spans_v2_path: Path             # data/skill/<slug>/extract_v2/spans.json
check_v2_dir: Path              # data/skill/<slug>/check_v2/
check_v2_report_path: Path      # data/skill/<slug>/check_v2/check_report.json
coverage_v2_dir: Path           # data/skill/<slug>/coverage_v2/
gates_v2_dir: Path              # data/skill/<slug>/gates_v2/
derive_dir: Path                # data/skill/<slug>/derive/
derivations_path: Path          # data/skill/<slug>/derive/derivations.json
derive_log_path: Path           # data/skill/<slug>/derive/derive_log.json
export_v2_dir: Path             # data/skill/<slug>/export_v2/
literal_observations_path: Path # data/skill/<slug>/export_v2/literal_observations.csv
analyst_rows_path: Path         # data/skill/<slug>/export_v2/analyst_rows.csv
benchmark_rows_expanded_path: Path  # data/skill/<slug>/export_v2/benchmark_rows_expanded.csv
prompt_v2_dir: Path             # data/skill/<slug>/prompt_v2/
```

**Decision: Separate `extract_v2/` directory, not mixed into `extract/`.**
This prevents any confusion about which contract version artifacts belong to
and makes it safe to run both pipelines on the same deal.

---

## Build Order (Dependency-Driven)

### Phase 1: Foundation Models + Immediate Fixes
**Dependencies:** None
**Deliverables:**
1. `models_v2.py` -- all v2 Pydantic models (PartyRecord, CohortRecord, 6 observation subtypes, CoverageCheckRecord, DerivationBasis, all derived record types)
2. Fix all-cash short-circuit bug in `enrich_core.py` line 674 (v1 fix, immediate value)
3. Path additions to `paths.py` / `SkillPathSet` for v2 artifact locations

**Rationale:** Models must exist before anything else can be built. The all-cash
fix is a standalone v1 bugfix that the GPT Pro review identified as partly
broken -- it exits the cycle early when an executed event exists but has no
consideration type, skipping the all-typed-proposals-are-cash fallback logic.
Path additions are mechanical and enable all subsequent phases.

**Estimated effort:** ~400 lines new code, ~10 lines bugfix

### Phase 2: v2 Artifact Loading + Canonicalization
**Dependencies:** Phase 1 (models)
**Deliverables:**
1. `extract_artifacts_v2.py` -- load/validate v2 observation artifacts
2. v2 path in `canonicalize.py` -- resolve quotes to spans for observation artifacts (reuse existing `_resolve_quotes_to_spans` at lines 88-142)
3. `canonicalize-v2` CLI command

**Rationale:** Artifact loading is required by every downstream stage.
Span resolution for v2 reuses existing `_resolve_quotes_to_spans` with
adaptation to handle observation-level `evidence_span_ids` instead of
event-level `quote_ids`.

**Estimated effort:** ~150 lines new code, ~80 lines modified

### Phase 3: v2 Validation Stack
**Dependencies:** Phase 2 (artifact loading)
**Deliverables:**
1. `check_v2.py` -- structural validation (evidence presence, ref integrity, cohort math)
2. `verify.py` v2 code path for span verification on observation artifacts
3. `coverage_v2.py` -- structured coverage generation and validation
4. `gates_v2.py` -- graph-level semantic gates

**Rationale:** Validation must be in place before the derivation engine. The
derive stage should refuse to run on invalid observation graphs, matching v1's
pattern where `enrich_core.py` requires all gates to pass (lines 47-81). Building
validation first catches schema bugs in models_v2.py early.

**Estimated effort:** ~850 lines new code, ~50 lines modified

### Phase 4: Derivation Engine
**Dependencies:** Phase 3 (validation)
**Deliverables:**
1. `derive.py` -- the rule engine with all rule families
2. Rule families: ROUND-01/02, EXIT-01 through EXIT-04, CASH-01 through CASH-03, AGREEMENT-01
3. `DerivedArtifactV2` output artifact
4. `derive` CLI command

**Build order within this phase (incremental):**
- First: round derivation (ROUND-01, ROUND-02) -- most frequently failing in v1
- Second: exit inference (EXIT-01 through EXIT-04) -- second most impactful
- Third: cash regime (CASH-01 through CASH-03) -- fixes the v1 all-cash propagation gap
- Fourth: analyst row compilation from phases + transitions + regimes

**Rationale:** The derivation engine is the core intellectual contribution of v2.
It depends on validated observation graphs. Building incrementally by rule family
enables testing each family against known deals before adding the next.

**Estimated effort:** ~500 lines new code

### Phase 5: DuckDB Integration + Export
**Dependencies:** Phase 4 (derivation engine)
**Deliverables:**
1. `db_schema_v2.py` or additions to `db_schema.py` (v2 DDL)
2. `db_load_v2.py` -- load observation graph + derivations into DuckDB
3. `db_export_v2.py` -- triple export surface (literal_observations.csv, analyst_rows.csv, benchmark_rows_expanded.csv)
4. `legacy_adapter.py` -- v2 analyst rows to v1 CSV shape
5. CLI commands: `db-load-v2`, `db-export-v2`

**Rationale:** DB integration is the terminal deterministic stage. Legacy adapter
enables running existing reconciliation infrastructure against v2 outputs for
direct comparison with v1 metrics.

**Estimated effort:** ~680 lines new code

### Phase 6: Extraction Contract + CLI
**Dependencies:** Phases 1-5
**Deliverables:**
1. v2 prompt packet composition mode in `compose_prompts.py` or new `compose_prompts_v2.py`
2. `/extract-deal-v2` local-agent skill documentation in `.claude/skills/`
3. `/verify-extraction-v2` local-agent skill documentation
4. Full CLI command registration for all v2 stages

**Rationale:** Extraction skill docs depend on the finalized observation model
and validation stack. The extraction contract narrows compared to v1 -- the LLM
extracts filing-literal parties, cohorts, and observations with spans, and is
explicitly told NOT to produce analyst rows directly.

**Estimated effort:** ~200 lines new code + skill documentation

---

## v1/v2 Coexistence Strategy

### Principle: Both Pipelines Run Simultaneously

A deal can have both `data/skill/<slug>/extract/` (v1) and
`data/skill/<slug>/extract_v2/` (v2) directories. Both can be loaded into
DuckDB (v1 into `actors`/`events`/`enrichment` tables, v2 into
`v2_parties`/`v2_observations`/`v2_derivations` tables). Both can produce CSV
exports in their respective `export/` and `export_v2/` directories.

### What Enables Coexistence

1. **Separate artifact directories:** `extract/` vs `extract_v2/`, `export/` vs `export_v2/`
2. **Separate DuckDB tables:** v1 tables untouched, v2 tables prefixed with `v2_`
3. **Separate CLI commands:** `check` vs `check-v2`, `db-load` vs `db-load-v2`
4. **Shared spans table:** Both v1 and v2 use the same span format. Shared DuckDB `spans` table keyed by `(deal_slug, span_id)`.
5. **Shared source artifacts:** Both read from `data/deals/<slug>/source/` (unchanged)
6. **Shared raw filings:** Both read from `raw/<slug>/` (immutable)
7. **Independent gate chains:** v1 gates (`check`, `verify`, `coverage`, `gates`) are separate from v2 gates (`check-v2`, `verify-v2`, `coverage-v2`, `gates-v2`)

### Migration Path

| Step | Action | When |
|------|--------|------|
| 1 | Build v2 alongside v1 | Phases 1-6 |
| 2 | Run both pipelines on STEC (reference deal) | After Phase 5 |
| 3 | Compare v2 legacy-adapter CSV against v1 CSV via existing reconciliation | After Phase 5 |
| 4 | Run v2 on all 9 deals | After STEC validation |
| 5 | Evaluate v2 reconciliation metrics against v1 baseline (70.7% atomic match) | After 9-deal run |
| 6 | Deprecate v1 pipeline stages | Only after v2 metrics are stable and >= v1 |

### What Does NOT Change During Migration

- `data/seeds.csv` format
- Raw filing fetch and freeze (`raw-fetch`)
- Source preprocessing (`preprocess-source`)
- The reconciliation infrastructure (compares CSVs, not internal models)
- DuckDB connection handling and lock retry (`db_schema.py`)
- Span resolution and provenance (`provenance.py`)
- Date normalization (`normalize/`)

---

## Patterns to Follow

### Pattern 1: Discriminated Union for Observation Types

**What:** Use Pydantic's discriminated union with a literal `obs_type` field.

**When:** Any time a list contains heterogeneous observation subtypes.

**Example:**
```python
Observation = Annotated[
    Union[
        ProcessObservation,
        AgreementObservation,
        SolicitationObservation,
        ProposalObservation,
        StatusObservation,
        OutcomeObservation,
    ],
    Field(discriminator="obs_type"),
]
```

**Why:** Established Pydantic pattern for type-safe polymorphic deserialization.
The v1 codebase uses Literal types extensively for `event_type` -- this extends
the approach to a proper discriminated union.

### Pattern 2: DerivationBasis on Every Derived Record

**What:** Every record produced by `derive.py` carries a `DerivationBasis`.

**When:** Always, for every derived record.

**Example:**
```python
class DerivationBasis(SkillModel):
    rule_id: str
    source_observation_ids: list[str]
    source_span_ids: list[str]
    confidence: Literal["high", "medium", "low"]
    explanation: str
```

**Why:** This solves the v1 problem where enrichment decisions were opaque
annotations on existing event IDs. In v1, `BidClassification` has `basis: str`
and `rule_applied: float | None` (models.py line 369-372) but no link back to
source observations. `DerivationBasis` makes provenance explicit and machine-readable.

### Pattern 3: Gate-Before-Derive

**What:** `derive.py` refuses to run unless all v2 gate stages pass.

**When:** Always. Matching enrich_core.py `_require_gate_artifacts()` at lines 46-81.

**Why:** Prevents the derivation engine from operating on structurally invalid
or semantically inconsistent observation graphs. This is the exact same pattern
that makes v1's deterministic stages reliable.

### Pattern 4: Drop-and-Reload Per Deal

**What:** `db_load_v2.py` deletes all v2 rows for a `deal_slug`, then reloads
from artifacts, inside a single transaction.

**When:** Every `db-load-v2` invocation.

**Why:** Established v1 pattern (`_delete_deal` in `db_load.py` lines 62-64).
Simpler and safer than upsert for full-deal artifact reloads. The `deal_slug`
primary key prefix makes this clean.

### Pattern 5: Subject Refs as Union of Party/Cohort IDs

**What:** `subject_refs` and `counterparty_refs` on observations accept both
`party_id` and `cohort_id` values. Consumer code resolves via both indexes.

**When:** Any observation that references actors.

**Example:**
```python
def resolve_subject(ref: str, artifacts: LoadedObservationArtifacts) -> PartyRecord | CohortRecord:
    party = artifacts.party_index.get(ref)
    if party is not None:
        return party
    cohort = artifacts.cohort_index.get(ref)
    if cohort is not None:
        return cohort
    raise ValueError(f"Unresolved subject ref: {ref}")
```

**Why:** This is how cohorts participate in the observation graph as first-class
entities alongside named parties. In v1, grouped actors used the same `actor_id`
namespace but could not express cohort evolution. In v2, the dual-namespace
resolution makes the intent explicit.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Modifying v1 Models to Support v2

**What:** Adding v2 fields to `SkillEventRecord` or `SkillActorRecord`.

**Why bad:** Breaks the v1 contract for all 9 existing deals. Every v1 stage
that loads these models (check.py, verify.py, coverage.py, gates.py,
enrich_core.py, db_load.py, db_export.py) would need updating. The v1 pipeline
must remain independently operational.

**Instead:** Create `models_v2.py` with entirely separate types. Share only
generic types (`ResolvedDate`, `MoneyTerms`, `SpanRecord`).

### Anti-Pattern 2: Single Loader That Auto-Detects v1 vs v2

**What:** Extending `extract_artifacts.py` to also detect and load v2 artifacts.

**Why bad:** The v1 loader already has complex mode detection (quote_first vs
canonical, lines 40-83). Adding v2 detection creates a three-way branch with
fragile heuristics. The two contracts are fundamentally different shapes --
v1 has `actors` + `events` arrays; v2 has `parties` + `cohorts` +
`observations`.

**Instead:** Separate `extract_artifacts_v2.py`. Each loader is simple and
focused. Callers explicitly choose which version they want.

### Anti-Pattern 3: Reusing v1 DuckDB Tables for v2 Data

**What:** Loading v2 observations into the `events` table with a version flag.

**Why bad:** The column sets are fundamentally different. v2 observations have
`subject_refs` (list of party/cohort IDs), not `actor_ids`. They have `obs_type`
not `event_type`. Forcing v2 data into v1 columns would require NULLing most
columns and adding many new ones, making queries fragile.

**Instead:** New tables with `v2_` prefix. Clean schema, clean queries, no
backward-compatibility hacks.

### Anti-Pattern 4: Building Derivation Before Validation

**What:** Implementing `derive.py` before `check_v2.py` and `gates_v2.py`.

**Why bad:** The derivation engine assumes its inputs are structurally valid.
Without validation, subtle input errors (broken ref links, impossible cohort
counts, acyclic chain violations) produce silently wrong derived records. The
v1 pipeline learned this lesson -- enrich_core requires all gates to pass.

**Instead:** Build validation first (Phase 3), then derivation (Phase 4).

### Anti-Pattern 5: Conflating Literal Observations with Derived Rows

**What:** Having the LLM produce analyst-style rows directly in v2 (reproducing
the v1 problem).

**Why bad:** This is the entire motivation for the v2 redesign. The GPT Pro
review's core diagnosis (Part 1, section 1) is that `SkillEventRecord` carries
filing facts, analytical interpretations, and export row shapes in one object.
v2 separates these layers.

**Instead:** LLM extracts filing-literal observations. Derivation engine produces
analyst rows with provenance. Export surfaces them separately.

---

## Scalability Considerations

| Concern | At 9 deals (current) | At 100 deals | At 400+ deals |
|---------|---------------------|--------------|---------------|
| DuckDB size | ~1MB, trivial | ~10MB, trivial | ~50MB, fine for embedded DB |
| JSON column queries | Instant | Index on `obs_type`, `record_type` if slow | Consider column-per-subtype if JSON bottlenecks |
| Derivation engine | <1s per deal (rule-based, not O(n^2)) | <1s per deal | Add progress logging |
| v1+v2 table coexistence | Clean | Clean (prefixed) | Consider schema namespaces if more versions emerge |
| Legacy adapter | Simple mapping | Simple mapping | Remove when v1 is deprecated |
| Span table growth | Shared is fine | Shared is fine | Add deal_slug index if scan costs grow |

---

## Sources

- Live codebase analysis: `skill_pipeline/models.py` (596 lines), `enrich_core.py` (739 lines), `db_schema.py` (142 lines), `db_load.py` (385 lines), `db_export.py` (456 lines), `canonicalize.py` (566 lines), `extract_artifacts.py` (94 lines), `check.py` (256 lines), `verify.py` (586 lines), `coverage.py` (423 lines), `gates.py` (603 lines), `cli.py` (312 lines), `paths.py` (86 lines), `pipeline_models/common.py` (120 lines)
- GPT Pro architectural review: `diagnosis/gptpro/2026-03-31/round_1/response.md` (570 lines)
- Project context: `.planning/PROJECT.md` (242 lines)
