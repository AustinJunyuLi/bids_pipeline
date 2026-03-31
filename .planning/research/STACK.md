# Technology Stack: v2.0 Observation Graph Additions

**Project:** Filing-Grounded M&A Extraction Pipeline -- v2.0 Observation Graph
**Researched:** 2026-03-30
**Scope:** Stack additions and changes for the observation graph architecture. Does NOT re-research the validated v1 stack (Python 3.13, Pydantic 2.12, DuckDB 1.4, pytest 8, edgartools, openpyxl).

## Executive Summary

The v2.0 observation graph architecture requires **zero new dependencies**. The existing stack -- Pydantic 2.12.5 with discriminated unions, DuckDB 1.4.4 with JSON columns and `ALTER TABLE ADD COLUMN IF NOT EXISTS`, Python 3.13 with `StrEnum` and full typing support, and pytest 8 with `tmp_path` fixtures -- already provides every capability the architecture needs. The research below documents exactly which existing features to use, how to use them for the specific v2 patterns, and what NOT to add.

## Verified Stack Capabilities for v2

### 1. Pydantic Discriminated Unions for Observation Types

**Current version:** Pydantic 2.12.5 (installed), dependency spec `>=2.0`
**Confidence:** HIGH -- verified by running code against the installed version

The GPT Pro architecture proposal defines 6 observation types (`ProcessObservation`, `AgreementObservation`, `SolicitationObservation`, `ProposalObservation`, `StatusObservation`, `OutcomeObservation`) unified via a discriminated union on `obs_type`. This is the correct pattern and it works today with no changes.

**Verified behavior:**

```python
from typing import Annotated, Union, Literal
from pydantic import BaseModel, Field

Observation = Annotated[
    Union[ProcessObservation, AgreementObservation, ...],
    Field(discriminator="obs_type"),
]
```

- `model_dump(mode="json")` preserves the discriminator field in output. This matters because the codebase uses `json.dumps(model.model_dump(mode="json"))` for artifact I/O.
- `model_validate(payload)` correctly dispatches to the right subclass based on `obs_type`. Round-trip serialization works.
- `ConfigDict(extra="forbid")` (the existing `SkillModel` base) works with discriminated unions -- extra fields on any variant are rejected.

**How to integrate:** Define all observation subtypes inheriting from a shared `ObservationBase(SkillModel)`. Define the `Observation` type alias as the discriminated union. Use it in `ObservationArtifactV2.observations: list[Observation]`. The existing `_read_json` / `_write_json` patterns in `enrich_core.py` and `db_load.py` work unchanged.

**What NOT to do:** Do not use `model_config = ConfigDict(extra="allow")` on the base to handle type-specific fields generically. The discriminated union already handles dispatch. Do not use `__init_subclass__` or metaclass registration -- Pydantic's discriminator handles this natively.

### 2. Graph Traversal Patterns

**Confidence:** HIGH -- no library needed; verified pattern against codebase

The observation graph is not a general graph. It is a directed set of typed records with cross-references via ID strings (`observation_id`, `party_id`, `cohort_id`). The existing codebase already uses this exact pattern:

- `enrich_core.py:_cycle_ranges()` traverses events by index position
- `enrich_core.py:_active_counts_for_cycle()` maintains state machines over event sequences
- `enrich_core.py:_populate_invited_from_count_assertions()` does cross-entity lookups via index dicts
- `extract_artifacts.py:LoadedExtractArtifacts.span_index` builds `dict[str, SpanRecord]` for O(1) lookup
- `db_export.py:_build_event_rows()` cross-references actors, events, enrichment, cycles, and rounds via ID-keyed dicts

The v2 derivation engine needs the same patterns, just applied to the observation graph instead of the event list. The standard approach:

```python
# Index construction (already done this way in the codebase)
obs_by_id: dict[str, Observation] = {o.observation_id: o for o in observations}
obs_by_type: dict[str, list[Observation]] = defaultdict(list)
for o in observations:
    obs_by_type[o.obs_type].append(o)

# Cross-reference traversal
for proposal in obs_by_type["proposal"]:
    if proposal.requested_by_observation_id:
        solicitation = obs_by_id[proposal.requested_by_observation_id]
```

**What NOT to add:** Do not add `networkx`, `igraph`, or any graph library. The observation graph has at most hundreds of nodes per deal. Dict-based indexing with explicit traversal is simpler, faster, more testable, and consistent with the existing codebase patterns. Graph libraries are designed for thousands-to-millions of nodes with complex pathfinding. This graph needs type-filtered iteration and ID lookups.

### 3. Rule Engine Patterns

**Confidence:** HIGH -- no library needed; pattern verified against `enrich_core.py`

The derivation engine is a set of named rules that take observations as input and produce derived records as output. The existing `enrich_core.py` already implements this pattern in a less formalized way:

- `_classify_proposal()` applies numbered rules (1-5) with `rule_applied` tracking
- `_classify_dropouts()` applies signal-matching rules with `basis` provenance
- `_infer_all_cash_overrides()` applies cycle-scoped inference rules

The v2 derivation engine needs the same approach, formalized with `rule_id` provenance on every output. The correct pattern is a simple rule registry:

```python
@dataclass
class RuleResult:
    rule_id: str
    source_observation_ids: list[str]
    source_span_ids: list[str]
    confidence: Literal["high", "medium", "low"]
    explanation: str
    outputs: list[...]  # derived records produced by this rule

RuleFunc = Callable[[ObservationGraph], list[RuleResult]]

DERIVATION_RULES: list[tuple[str, RuleFunc]] = [
    ("ROUND-01", derive_informal_rounds),
    ("ROUND-02", derive_formal_rounds),
    ("EXIT-01", derive_explicit_withdrawals),
    ("EXIT-02", derive_cannot_improve_drops),
    # ...
]

def run_derivation_engine(graph: ObservationGraph) -> list[RuleResult]:
    results = []
    for rule_id, rule_func in DERIVATION_RULES:
        results.extend(rule_func(graph))
    return results
```

**What NOT to add:** Do not add a rules engine library (Durable Rules, PyKE, business-rules, etc.). The rule catalog from the GPT Pro proposal has approximately 12 rules. Each is a pure function over the observation graph. A list of callables with provenance tracking is the simplest correct implementation. Rule engine libraries add DSLs, working memory, conflict resolution, and inference chaining -- none of which this use case needs.

### 4. DuckDB Schema Evolution for Observation Tables

**Current version:** DuckDB 1.4.4 (installed), dependency spec `>=1.2`
**Confidence:** HIGH -- verified by running DDL against the installed version

The v2 architecture needs new tables alongside the existing ones during the transition period:

| New Table | Purpose | Key |
|-----------|---------|-----|
| `parties` | Named participants replacing `actors` for v2 deals | `(deal_slug, party_id)` |
| `cohorts` | Unnamed group lifecycle tracking | `(deal_slug, cohort_id)` |
| `observations` | Filing-literal typed observations | `(deal_slug, observation_id)` |
| `derivations` | Rule-produced derived records | `(deal_slug, derivation_id)` |
| `coverage_checks` | Structured coverage records | `(deal_slug, cue_family)` |
| `analyst_rows` | Derived benchmark-style rows | `(deal_slug, row_id)` |

**Verified DuckDB capabilities for this:**

- `CREATE TABLE IF NOT EXISTS` -- idempotent table creation, already used in `db_schema.py`
- `ALTER TABLE ADD COLUMN IF NOT EXISTS` -- idempotent column addition, already used in `db_schema.py:_ensure_schema()` for the `all_cash_override` migration
- `JSON` column type -- stores type-specific observation payload without needing a column per observation subtype. Verified working with DuckDB 1.4.4
- `TEXT[]` array type -- already used for `actor_ids`, `evidence_span_ids`, etc. Works for `subject_refs`, `counterparty_refs`
- Transactional `BEGIN`/`COMMIT`/`ROLLBACK` -- already used in `db_load.py` for atomic deal loads
- `DELETE FROM table WHERE deal_slug = ?` -- drop-and-reload pattern already established

**Schema pattern for polymorphic observations in DuckDB:**

Use a single `observations` table with `obs_type` discriminator column plus a `JSON` column for type-specific payload. This avoids 6 separate tables while preserving queryability:

```sql
CREATE TABLE IF NOT EXISTS observations (
    deal_slug TEXT NOT NULL,
    observation_id TEXT NOT NULL,
    obs_type TEXT NOT NULL,
    date_sort DATE,
    date_precision TEXT,
    summary TEXT NOT NULL,
    subject_refs TEXT[],
    counterparty_refs TEXT[],
    evidence_span_ids TEXT[],
    type_payload JSON,
    PRIMARY KEY (deal_slug, observation_id)
);
```

The `type_payload` JSON column holds subtype-specific fields (e.g., `proposal_kind`, `agreement_kind`, `terms`). DuckDB's JSON functions (`json_extract`, `json_extract_string`) allow querying into the payload when needed, but the primary access pattern is load-all-for-deal then filter in Python -- matching the existing `db_export.py` pattern.

**What NOT to do:** Do not create 6 separate tables for 6 observation types. Do not use DuckDB's `UNION` type for observations (it adds complexity without benefit when the access pattern is always load-all-for-deal). Do not use DuckDB's `STRUCT` type for nested observation fields -- `JSON` is simpler for variable-shape payloads and DuckDB handles it well.

**Migration approach:** Add new tables via `CREATE TABLE IF NOT EXISTS` in the `SCHEMA_DDL` string in `db_schema.py`. Keep all existing v1 tables. The legacy adapter writes to v1 tables so existing export works. v2 export reads from v2 tables.

### 5. Testing Infrastructure

**Current framework:** pytest 8+ (installed), dependency spec `>=8.0`
**Confidence:** HIGH -- verified against existing test suite

The existing test infrastructure is well-suited for v2. Key patterns already established:

| Pattern | Where Used | v2 Applicability |
|---------|------------|------------------|
| `tmp_path` fixture for isolated deal artifacts | `test_skill_enrich_core.py`, `test_skill_db_load.py` | Observation graph fixtures |
| Quote-first fixture builders with canonicalization | `test_skill_enrich_core.py:_write_quote_first_extract_fixture()` | v2 observation fixtures |
| DuckDB in-memory testing | `test_skill_db_load.py` | v2 table load/export |
| `build_skill_paths(slug, project_root=tmp_path)` | All stage tests | v2 stage tests |

**New test patterns needed for v2:**

1. **Observation fixture builders** -- Analogous to `_base_event()` in `test_skill_enrich_core.py` but for each observation type. No new library needed; follow the existing factory-function pattern.

2. **Derivation rule unit tests** -- Each rule is a pure function `(ObservationGraph) -> list[RuleResult]`. Test each rule in isolation with minimal observation graphs. No new library needed.

3. **Legacy adapter regression tests** -- v2 observations + derivations must produce the same CSV output as v1 for existing deals. Build comparison fixtures from the 9-deal corpus. No new library needed.

4. **Graph invariant assertions** -- Custom assertion helpers for checking acyclicity of supersession chains, cohort count consistency, reference integrity. These are simple Python functions, not a test framework feature.

**What NOT to add:** Do not add `hypothesis` for property-based testing (the observation graph has domain constraints too specific for random generation to be useful). Do not add `pytest-benchmark` (this is a correctness pipeline, not a performance pipeline). Do not add `factory_boy` or `faker` (the fixture factories are simple enough as plain functions, matching the existing style).

## Recommended Stack (Complete)

### Existing -- No Changes Required

| Technology | Version (Installed) | Spec | Purpose |
|------------|-------------------|------|---------|
| Python | 3.13.5 | `>=3.11` | Runtime |
| Pydantic | 2.12.5 | `>=2.0` | Schema validation, discriminated unions, JSON serialization |
| DuckDB | 1.4.4 | `>=1.2` | Structured store, schema evolution, JSON columns |
| pytest | 8.x | `>=8.0` | Test framework |
| edgartools | 5.x | `>=5.23,<6.0` | SEC filing access |
| openpyxl | 3.x | `>=3.1` | Spreadsheet I/O |

### New Dependencies Required

**None.**

Every capability needed for the v2 observation graph, cohort tracking, derivation engine, coverage records, triple export, and legacy adapter is provided by the existing stack. The architecture proposal's data model uses Pydantic discriminated unions (existing), the derivation engine uses pure Python functions with provenance (existing pattern), DuckDB handles schema evolution and polymorphic storage (existing), and the test infrastructure supports all needed patterns (existing).

## Alternatives Considered

| Capability | Considered | Why Not |
|------------|-----------|---------|
| Graph traversal | `networkx` | At most hundreds of nodes per deal. Dict-based indexing is faster, simpler, and consistent with existing codebase. |
| Rule engine | `durable-rules`, `business-rules` | Approximately 12 deterministic rules. A list of callables with provenance tracking is simpler than any DSL. |
| Property-based testing | `hypothesis` | Domain constraints are too specific for useful random generation. Manual fixtures match existing test style. |
| Schema migration tool | `alembic`, custom migration system | DuckDB's `CREATE TABLE IF NOT EXISTS` and `ALTER TABLE ADD COLUMN IF NOT EXISTS` handle additive schema evolution. No destructive migrations needed during v1/v2 coexistence. |
| JSON schema validation | `jsonschema` | Pydantic already validates all JSON artifact I/O with fail-fast on unexpected fields. |
| Immutable data structures | `attrs`, `frozendict` | Pydantic models with `ConfigDict(extra="forbid")` already enforce structural integrity. Observations are created once and traversed, not mutated. |
| Type-safe enums | Custom enum library | Python 3.11+ `StrEnum` already used throughout the codebase (`pipeline_models/common.py`). |

## Integration Points with Existing Code

### Where v2 Models Plug In

| Existing Module | v2 Touch Point | Change Type |
|----------------|----------------|-------------|
| `models.py` | Add `ObservationBase`, 6 subtypes, `PartyRecord`, `CohortRecord`, `CoverageCheckRecord`, `ObservationArtifactV2`, derivation records, `AnalystRowRecord` | Additive -- new classes alongside existing |
| `extract_artifacts.py` | Add `load_v2_artifacts()` parallel to `load_extract_artifacts()` | Additive -- new loader function |
| `db_schema.py` | Add `CREATE TABLE IF NOT EXISTS` for 6 new tables in `SCHEMA_DDL` | Additive -- existing tables unchanged |
| `db_load.py` | Add `_load_parties()`, `_load_cohorts()`, `_load_observations()`, `_load_derivations()`, `_load_coverage_checks()`, `_load_analyst_rows()` | Additive -- existing load functions unchanged |
| `db_export.py` | Add `run_v2_export()` for triple surface; keep `run_db_export()` for legacy | Additive -- existing export unchanged |
| `enrich_core.py` | Derivation engine is a NEW module (`derive.py` or `derivation_engine.py`), not a modification of `enrich_core.py` | New module -- existing enrichment unchanged |
| `paths.py` / `SkillPathSet` | Add paths for v2 artifacts (`observations_path`, `derivations_path`, etc.) | Additive -- existing paths unchanged |
| `pipeline_models/common.py` | May add new `StrEnum` types for observation kinds | Additive -- existing enums unchanged |

### What Must NOT Change

| Module | Reason |
|--------|--------|
| `enrich_core.py` logic | v1 deals still need v1 enrichment during transition |
| `db_schema.py` existing tables | v1 deals still load into v1 tables |
| `db_export.py` existing export | v1 CSV shape must remain available via legacy adapter |
| `extract_artifacts.py` existing loader | v1 artifacts (`actors_raw.json`, `events_raw.json`) still need loading |
| `canonicalize.py` | v1 canonicalization path stays for v1 deals |
| `check.py`, `verify.py`, `coverage.py`, `gates.py` | v1 QA gates stay; v2 gets its own gate implementations |

## Specific Implementation Guidance

### Discriminated Union Layout in models.py

Place the v2 models in a new section of `models.py` (or a new `models_v2.py` if the file gets unwieldy). Keep the `SkillModel` base class. Follow the exact pattern from the GPT Pro proposal, with one adjustment: use `SkillModel` instead of re-declaring `ConfigDict(extra="forbid")`:

```python
class ObservationBase(SkillModel):
    observation_id: str
    obs_type: str  # overridden by Literal in subtypes
    date: ResolvedDate | None = None
    subject_refs: list[str] = Field(default_factory=list)
    counterparty_refs: list[str] = Field(default_factory=list)
    summary: str
    evidence_span_ids: list[str] = Field(default_factory=list)

class ProcessObservation(ObservationBase):
    obs_type: Literal["process"]
    process_kind: Literal[...]
    # ...

# ... other subtypes ...

Observation = Annotated[
    Union[ProcessObservation, AgreementObservation, ...],
    Field(discriminator="obs_type"),
]
```

### DuckDB Observation Loading Pattern

Follow the existing `_load_events()` pattern in `db_load.py`. Flatten common fields into columns; pack type-specific fields into the `JSON` column:

```python
def _load_observations(con, deal_slug: str, observations: list[Observation]) -> None:
    rows = []
    for obs in observations:
        common = obs.model_dump(mode="json")
        type_fields = {k: v for k, v in common.items()
                       if k not in COMMON_OBSERVATION_COLUMNS}
        rows.append((
            deal_slug,
            obs.observation_id,
            obs.obs_type,
            obs.date.sort_date if obs.date else None,
            obs.date.precision.value if obs.date else None,
            obs.summary,
            obs.subject_refs,
            obs.counterparty_refs,
            obs.evidence_span_ids,
            json.dumps(type_fields),
        ))
    # ... executemany INSERT ...
```

### Derivation Engine Module Structure

Create `skill_pipeline/derive.py` (or `skill_pipeline/derivation_engine.py`). Do not modify `enrich_core.py`. The derivation engine:

1. Loads v2 observation artifacts
2. Builds the observation graph (dict-based indexes)
3. Runs each rule function in order
4. Collects `DerivationBasis` provenance for every output
5. Writes derivation artifacts

Each rule is a standalone function. Unit-testable in isolation. The rule registry is a simple list, not a plugin system.

### Test File Naming

Follow the existing `test_skill_*.py` convention:

- `test_skill_observation_models.py` -- model validation, discriminated union dispatch
- `test_skill_derive.py` -- individual rule unit tests
- `test_skill_v2_db_load.py` -- v2 table loading
- `test_skill_v2_export.py` -- triple export surface
- `test_skill_legacy_adapter.py` -- v2-to-v1 CSV shape mapping

## Version Pinning Recommendation

No changes to `pyproject.toml` dependency specifications. The current specs (`pydantic>=2.0`, `duckdb>=1.2`, `pytest>=8.0`) are already correct lower bounds. The installed versions (Pydantic 2.12.5, DuckDB 1.4.4) have all needed capabilities. Do not tighten the lower bounds unless a specific v2 feature requires it (none identified).

## Sources

- Pydantic 2.12.5 discriminated unions: verified by running code against installed version
- DuckDB 1.4.4 JSON columns and schema evolution: verified by running DDL against installed version
- Python 3.13.5 typing features: verified by running code against installed version
- Existing codebase patterns: `skill_pipeline/models.py`, `skill_pipeline/enrich_core.py`, `skill_pipeline/db_schema.py`, `skill_pipeline/db_load.py`, `skill_pipeline/extract_artifacts.py`, `skill_pipeline/db_export.py`
- Architecture proposal: `diagnosis/gptpro/2026-03-31/round_1/response.md`
- Test patterns: `tests/test_skill_enrich_core.py`, `tests/test_skill_db_load.py`
