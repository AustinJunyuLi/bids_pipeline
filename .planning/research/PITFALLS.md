# Domain Pitfalls: v2.0 Observation Graph Architecture Migration

**Domain:** Adding observation graph data model, cohort-based actor representation, deterministic derivation engine, structured coverage records, and triple export surface to an existing 9-deal filing-grounded M&A extraction pipeline
**Researched:** 2026-03-30
**Context:** 9 completed deals with full v1-contract artifacts, 12 deterministic CLI stages, 4 local-agent skills, 33 enrich-core tests alone, ~10,600 total test lines, 70.7% (157/222) atomic benchmark match rate established as baseline

---

## Critical Pitfalls

Mistakes that corrupt existing deal artifacts, silently break the 9-deal corpus, or require full re-extraction of all deals. Each is grounded in evidence from the actual codebase.

---

### Pitfall 1: Premature v1 Contract Removal Breaks 12+ Downstream Consumers

**What goes wrong:** The v2 observation model (`PartyRecord`, `CohortRecord`, `ObservationBase` subtypes) replaces `SkillActorRecord`, `SkillEventRecord`, and their artifact wrappers. If these v1 types are modified or removed before v2 is stable, every downstream consumer breaks simultaneously. The blast radius is not theoretical -- it is enumerable:

- `extract_artifacts.py` -- `LoadedExtractArtifacts` returns `SkillActorsArtifact | None` and `SkillEventsArtifact | None` (lines 24-25)
- `enrich_core.py` -- 12 functions take `list[SkillEventRecord]` as parameter types (lines 84, 100, 125, 142, 170, 222, 300, 313, 350, 389, 542, 565, 639)
- `check.py` -- `_get_actor_event_records()` dispatches on `artifacts.mode` to return v1 lists
- `verify.py` -- verifies span integrity against `evidence_span_ids` on v1 records
- `coverage.py` -- coverage cue detection operates over v1 event types
- `gates.py` -- `SUBSTANTIVE_EVENT_TYPES` is a hardcoded frozenset of the 20-type v1 taxonomy (line 25-40), `EVENT_PHASES` maps v1 event types to phases (line 46-70)
- `db_load.py` -- `_load_actors()` and `_load_events()` destructure `SkillActorsArtifact` and `SkillEventsArtifact` field by field (lines 67-168)
- `db_export.py` -- `EVENT_TYPE_PRIORITY`, `NOTE_BY_EVENT_TYPE`, `BIDDERLESS_EVENT_TYPES` are all keyed to the 20-type v1 taxonomy
- `canonicalize.py` -- converts between `RawSkillActorsArtifact`/`RawSkillEventsArtifact` and canonical forms
- `compose_prompts.py` -- loads `RawSkillActorsArtifact` or `SkillActorsArtifact` for event prompt composition
- `deal_agent.py` -- loads extract artifacts for status summary
- `provenance.py` -- uses `SpanRecord` (shared, but tightly coupled)

**Why it happens:** The natural instinct is to replace v1 models with v2 models in `models.py`. But `extra="forbid"` on `SkillModel` means any schema mismatch is a hard validation failure, not a silent degradation. One field rename and all 9 deals' existing JSON artifacts fail to deserialize.

**Consequences:** All 9 deals become unloadable. Every deterministic stage from `check` through `db-export` fails. Existing DuckDB data becomes unqueryable if schema changes are applied to `db_schema.py` simultaneously.

**Prevention:**
1. Add v2 models as NEW classes in `models.py` -- never modify v1 classes during migration
2. Add v2 artifact loading alongside v1 in `extract_artifacts.py` -- a new `mode` value (e.g., `"observation_graph"`) alongside existing `"quote_first"` and `"canonical"`
3. All 12+ downstream consumers must continue to work with `mode == "canonical"` unchanged
4. Only deprecate v1 classes after all 9 deals have been re-extracted to v2 AND the v2 pipeline passes all gates

**Detection:** Run `python -m pytest -q` after any model change. Any failure means v1 contract is broken. Gate this in CI.

**Phase assignment:** Phase 1 (data model). The v2 models must be additive from day one.

---

### Pitfall 2: DuckDB Schema Evolution Corrupts the Multi-Deal Database

**What goes wrong:** The current DuckDB schema in `db_schema.py` has 6 tables (`actors`, `events`, `spans`, `enrichment`, `cycles`, `rounds`) with fixed column sets. The v2 architecture needs new tables (e.g., `parties`, `cohorts`, `observations`, `derivations`, `analyst_rows`) and potentially changes to existing tables. If schema migration is done incorrectly, one of three things happens:

1. `CREATE TABLE IF NOT EXISTS` silently leaves old schema in place when columns need to change
2. `DROP TABLE` + `CREATE TABLE` destroys existing deal data for all 9 deals
3. `ALTER TABLE ADD COLUMN` succeeds but existing rows have NULLs where downstream code expects non-NULL values

The current code already has evidence of this pattern. `db_schema.py` line 141 has an explicit `ALTER TABLE enrichment ADD COLUMN IF NOT EXISTS all_cash_override BOOLEAN` -- a previous migration that was bolted on. Repeating this pattern for v2's much larger schema delta will create a brittle migration chain.

**Why it happens:** DuckDB does not have a migration framework. The current approach is "ensure schema on connect" via `_ensure_schema()`. This works for additive columns but not for structural changes like new tables that replace old ones, or column type changes, or foreign key relationships between v1 and v2 tables.

**Consequences:** The `pipeline.duckdb` file containing all 9 deals' loaded data becomes inconsistent. `db-export` produces corrupt or empty CSVs. The `db-load` -> `db-export` round-trip, which is the canonical deterministic export path, breaks.

**Prevention:**
1. Add v2 tables alongside v1 tables -- never modify v1 table schemas during migration
2. The v2 `db-load` should write to `parties`, `cohorts`, `observations` tables while v1 `db-load` continues writing to `actors`, `events` tables
3. New `db-export` paths should read from v2 tables for `literal_observations.csv` and `analyst_rows.csv` while the legacy `deal_events.csv` export continues reading from v1 tables
4. Only drop v1 tables after confirming the v2 export produces equivalent or better benchmark results for all 9 deals
5. Consider a schema version marker in the database (a `metadata` table with `schema_version`) so `_ensure_schema()` can branch correctly

**Detection:** Before any schema change, snapshot the current `pipeline.duckdb`. After migration, verify row counts and spot-check values for all 9 deals against the snapshot.

**Phase assignment:** Phase 3 (derivation engine) or Phase 4 (triple export). Do NOT change DuckDB schema in Phase 1 (data model) -- let models stabilize first.

---

### Pitfall 3: LLM Prompt Contract Changes Affect All 9 Deals Simultaneously

**What goes wrong:** The v2 extraction contract asks the LLM to produce `PartyRecord`, `CohortRecord`, and 6 observation types instead of `RawSkillActorRecord` + `RawSkillEventRecord` with the 20-type taxonomy. The extraction prompts live in `.claude/skills/extract-deal/SKILL.md` and are compiled by `skill-pipeline compose-prompts`. Changing the SKILL.md changes the prompt for ALL deals simultaneously -- there is no per-deal prompt versioning.

This means:
- Every deal must be re-extracted after any prompt schema change
- There is no way to test a v2 prompt on one deal while keeping the other 8 on v1
- If the v2 prompt produces worse results on deal X while improving deal Y, there is no way to selectively roll back

**Why it happens:** The prompt compilation pipeline (`compose_prompts.py`) reads the skill doc once and generates packets for the requested deal. The skill doc IS the prompt contract. There is no indirection layer, no prompt versioning, no A/B testing infrastructure.

**Consequences:** A single prompt change forces re-extraction of all 9 deals. If the change regresses any deal, you must either accept the regression or revert the entire change. This creates a deadlock where improving prompt coverage on PetSmart (where cohorts matter most) might regress STEC or Imprivata (where the simpler flat model worked fine).

**Prevention:**
1. Create a separate v2 extraction skill doc (e.g., `.claude/skills/extract-deal-v2/SKILL.md`) that coexists with the v1 doc during migration
2. Add a `--contract-version` flag to `compose-prompts` or use `--mode` to select between v1 and v2 prompt generation
3. Re-extract deals one at a time, validating each against the v1 benchmark before proceeding to the next
4. Keep v1 artifacts in place until v2 artifacts pass all deterministic gates for that deal
5. Track per-deal extraction status in a migration manifest (which deals are on v1, which are on v2)

**Detection:** After each deal re-extraction, run `skill-pipeline check`, `verify`, `coverage`, `gates` and compare with the v1 gate reports. Any regression is a signal to investigate before proceeding.

**Phase assignment:** Phase 2 (extraction contract). Must be designed to allow incremental per-deal migration.

---

### Pitfall 4: The All-Cash Short-Circuit Bug Fix Changes Semantics During Architecture Migration

**What goes wrong:** The GPT Pro review identified a concrete bug in `_infer_all_cash_overrides()` at `enrich_core.py` lines 660-688: when an executed event exists but has no `consideration_type`, the function `continue`s to the next cycle (line 674), skipping the fallback logic that checks whether all typed proposals are cash (lines 676-687). This produces `"all_cash_overrides": {}` even when it should produce overrides.

The temptation is to fix this bug as part of v2 migration. But fixing it in the v1 code changes existing artifact output for deals that have `executed` events without explicit cash terms. This means:
- `deterministic_enrichment.json` changes for affected deals
- `deal_events.csv` rows change (the `cash_value` column in `db_export.py` line 303-309 reads `all_cash_override`)
- The 70.7% benchmark match rate shifts -- possibly improving, possibly introducing new mismatches

**Why it happens:** Bug fixes and architecture migration are conflated. "We're changing everything anyway" makes it feel safe to fix bugs simultaneously. But the benchmark baseline was established WITH this bug. Changing it makes it impossible to isolate whether benchmark changes are from the bug fix or from the architecture migration.

**Consequences:** Cannot attribute benchmark improvements or regressions to their actual cause. If the v2 migration AND the bug fix both change results, you cannot tell which change helped and which hurt. This makes rollback decisions impossible.

**Prevention:**
1. Fix the all-cash short-circuit bug BEFORE starting v2 migration -- as a standalone v1.2 patch
2. Re-run all 9 deals through `enrich-core` -> `db-load` -> `db-export` with the fix
3. Re-run `/reconcile-alex` on affected deals to establish a new baseline
4. Document the new baseline match rate as the v2 migration starting point
5. Only then begin v2 model changes

**Detection:** After the bug fix, `deterministic_enrichment.json` diff for each deal should show ONLY `all_cash_overrides` changes. If other fields change, the fix has unintended side effects.

**Phase assignment:** Pre-Phase 1 (immediate fix). This is explicitly called out in the GPT Pro migration path as step 1.

---

### Pitfall 5: v2 Legacy Adapter Produces Subtly Different CSV Shape

**What goes wrong:** The v2 architecture proposes a legacy adapter that maps `v2 observations + derived rows` back to the current `deal_events.csv` shape for benchmark comparison continuity. But the current CSV shape is deeply entangled with v1 semantics:

- `db_export.py` `_note_value()` (line 329-334) maps `event_type` to display labels using `NOTE_BY_EVENT_TYPE`, a dict of the 20 v1 event types
- `_event_bidder_name()` (line 345-359) uses `BIDDERLESS_EVENT_TYPES`, another v1-taxonomy-keyed set
- `_assign_bidder_ids()` (line 259-276) computes synthetic bidder IDs based on NDA event position -- this logic has no v2 equivalent
- `_single_actor_type()` (line 373-397) computes type strings like "public S", "non-US F" from `bidder_kind`, `listing_status`, `geography` -- v2's `PartyRecord` has different field names (`role` includes "other", `bidder_kind` includes "unknown")
- `_format_event_row()` (line 285-326) reads directly from enrichment rows keyed by `event_id` -- v2 derived rows have `row_id`, not `event_id`

A legacy adapter that gets any of these mappings slightly wrong will produce CSVs that look correct but diff against the v1 baseline in ways that contaminate benchmark comparison.

**Why it happens:** CSV compatibility requires not just getting the values right but getting the exact formatting, ordering, and edge-case handling right. The current export has 14 columns with specific formatting rules. Any mismatch between the adapter's output and the v1 export's output is indistinguishable from a real extraction difference in reconciliation.

**Consequences:** Reconciliation against Alex's spreadsheet becomes meaningless -- you cannot tell whether a mismatch is a real v2 extraction difference or a legacy adapter formatting bug. The 70.7% baseline becomes unusable as a comparison point.

**Prevention:**
1. Build the legacy adapter as a separate export stage, not a replacement for the existing `db-export`
2. Before deploying the adapter on real deals, create a synthetic test where v2 observations are crafted to be exactly equivalent to a v1 deal's events, then verify the adapter produces byte-identical CSV output
3. Run both v1 `db-export` and v2 `legacy-adapter-export` in parallel during migration, diff the outputs, and fix adapter bugs until they converge
4. Only retire v1 `db-export` after all 9 deals produce identical CSVs through both paths

**Detection:** `diff` between v1-exported and v2-adapter-exported CSVs for the same deal. Any difference, even whitespace, is a bug.

**Phase assignment:** Phase 4 (triple export). Must be validated with byte-level comparison tests.

---

## Moderate Pitfalls

Mistakes that cause significant rework or delayed migration but do not corrupt existing data.

---

### Pitfall 6: Derivation Rule Engine Complexity Creep

**What goes wrong:** The GPT Pro proposal lists 8 named derivation rules (`ROUND-01`, `ROUND-02`, `EXIT-01` through `EXIT-04`, `AGREEMENT-01`, `CASH-01` through `CASH-03`). The natural implementation path is to build these one at a time. But rules interact: `EXIT-03` (screening elimination) depends on `ROUND-01`/`ROUND-02` having already identified phases. `CASH-03` (regime propagation) depends on cycle segmentation, which depends on phases. `EXIT-04` (lost-to-winner closure) depends on `EXIT-01` through `EXIT-03` having already classified other exits.

If rules are implemented without a clear execution ordering contract and explicit input/output dependency graph, the engine becomes order-dependent in non-obvious ways. Adding a new rule or modifying an existing one can change the output of downstream rules.

**Why it happens:** The current `enrich_core.py` already exhibits this pattern. `_pair_rounds()` output feeds into `_classify_proposals()`, which feeds into `_compute_formal_boundary()`. `_classify_dropouts()` depends on `rounds` output. These are implicit dependencies encoded in function call order within `run_enrich_core()` (lines 715-722). The v2 derivation engine will have more rules with more complex interdependencies.

**Consequences:** Rule debugging becomes non-local -- changing `ROUND-01` can silently change `EXIT-03` output. Test coverage must be combinatorial rather than per-rule. Adding the 9th rule to fix a PetSmart edge case breaks the STEC classification.

**Prevention:**
1. Define an explicit rule dependency DAG before implementing any rules
2. Each rule declares its required inputs (which observation types, which prior derived records) and its outputs
3. The engine executes rules in topological order of the DAG
4. Unit tests for each rule provide synthetic observations and assert derived output, independent of other rules
5. Integration tests run the full rule chain on real deal observation graphs and compare against expected derived output
6. Start with the 3 rule families causing most v1 pain: round derivation, exit inference, and cohort lifecycle -- as the GPT Pro review recommends

**Detection:** If a rule's test passes in isolation but fails when run with the full engine, there is an undeclared dependency.

**Phase assignment:** Phase 3 (derivation engine). The DAG design is the first task before any rule implementation.

---

### Pitfall 7: Cohort Model Edge Cases in Real Deal Data

**What goes wrong:** The `CohortRecord` model proposes `exact_count`, `known_member_party_ids`, and `unknown_member_count` with the invariant `unknown_member_count == exact_count - len(known_member_party_ids)`. Real filing text violates this invariant in several ways:

- **PetSmart:** "approximately 15 parties were contacted" -- the count is approximate, not exact. `exact_count` is a misnomer.
- **Overlapping membership:** "6 IOI submitters" and "4 finalists" where all 4 finalists were IOI submitters. Parent-child cohort lineage must handle overlapping sets, not just strict subsets.
- **Changing counts:** "15 parties signed NDAs" early in the filing, then "the Company was aware of 12 parties with active NDAs" later -- the cohort count changes over time, but the model has a single `exact_count`.
- **Multiple membership bases:** A party can be in multiple cohorts simultaneously (NDA cohort + IOI cohort + finalist cohort). The model needs to handle multi-membership without duplicating the party.

The current grouped actor model (`is_grouped`, `group_size`, `group_label` on `SkillActorRecord`) avoids these problems by being intentionally simple -- it is just a count label. The cohort model promises more but must actually deliver on these edge cases.

**Why it happens:** The cohort model is designed from clean abstraction, not from messy filing reality. The GPT Pro review proposes it based on PetSmart's needs but does not address how approximate counts, temporal count changes, or overlapping memberships should be handled.

**Consequences:** Cohort validation gates fail on real deals. Extraction prompts must be increasingly complex to explain when `exact_count` is approximate versus exact. The LLM produces cohorts that fail invariant checks, requiring repair passes that were not planned.

**Prevention:**
1. Rename `exact_count` to something that allows approximation (e.g., `count` with a separate `count_precision: Literal["exact", "approximate", "at_least"]` field)
2. Add temporal scoping to cohort records -- a cohort count is valid at a specific point in the deal timeline, not universally
3. Handle parent-child relationships as references, not containment constraints -- a child cohort's count need not sum to the parent's count unless explicitly marked as exhaustive
4. Test the cohort model against ALL 9 deals' filing text before finalizing the schema, not just PetSmart
5. Build the GPT Pro's proposed cohort validation gate (child counts cannot exceed parent counts) but make it a warning, not a blocker, for approximate counts

**Detection:** Extract cohort data from 3 representative deals (PetSmart for complex cohorts, Imprivata for simple, Medivation for medium) and validate against the model before committing to the schema.

**Phase assignment:** Phase 1 (data model). The cohort model must be validated against real data before extraction prompts reference it.

---

### Pitfall 8: Test Coverage Gap During Parallel v1/v2 Contract Period

**What goes wrong:** The existing test suite has 33 enrich-core tests and ~10,600 total test lines, all written against v1 contracts. During migration, both v1 and v2 code paths must work. But:

- v1 tests assert specific v1 model field names (`event_type`, `actor_ids`, `evidence_span_ids`)
- v2 models use different field names (`obs_type`, `subject_refs`, `evidence_span_ids`)
- Test fixtures (like `_base_event()` in `test_skill_enrich_core.py` line 15-43) construct v1 payloads -- v2 needs parallel fixture functions
- The `_write_quote_first_extract_fixture()` helper (line 58) writes v1 artifact files -- v2 artifacts go to different paths or have different schemas
- Test assertions check specific enrichment output shapes (`bid_classifications`, `dropout_classifications`) that v2 derivation will replace

If v2 tests are not written before v2 code, there is no safety net. If v1 tests are modified to accommodate v2, the v1 safety net is removed.

**Why it happens:** Writing tests for both v1 and v2 is double the effort. The temptation is to modify existing tests incrementally as v2 code is added. But each modification removes a v1 regression guard.

**Consequences:** Silent v1 regressions during migration. The 9 existing deals may break without any test catching it, because the tests were modified to expect v2 behavior.

**Prevention:**
1. Freeze v1 tests -- do not modify any existing test during v2 migration
2. Create a parallel `tests/test_v2_*` test tree for v2 code paths
3. Both v1 and v2 test suites must pass on every commit during migration
4. v1 tests can only be removed when the v1 code path they test is explicitly deprecated
5. For shared infrastructure (like `extract_artifacts.py`), add NEW tests for v2 loading without modifying existing v1 tests

**Detection:** `git diff` on any `tests/test_skill_*.py` file during migration should show only additions, never modifications or deletions of existing test functions.

**Phase assignment:** Every phase. Parallel test coverage is a continuous requirement, not a phase-specific task.

---

### Pitfall 9: Observation ID Namespace Collision with Event IDs

**What goes wrong:** v1 uses `event_id` (e.g., `evt_001`, `evt_002`) and `actor_id` (e.g., `bidder_a`, `advisor_bank`). v2 introduces `observation_id`, `party_id`, `cohort_id`, `phase_id`, `transition_id`, `row_id`. During the parallel period, both ID namespaces exist in the codebase and potentially in the DuckDB database.

If v2 observation IDs collide with v1 event IDs (e.g., both use `evt_001` or both use prefixed IDs like `obs_001` that could match a pattern), cross-reference bugs appear: v1 enrichment keyed by `event_id` accidentally matches a v2 `observation_id`, or DuckDB joins between v1 and v2 tables produce spurious matches.

**Why it happens:** ID generation is currently done by the LLM during extraction (the SKILL.md says "stable event_id e.g. evt_001, evt_002"). There is no centralized ID allocation, no prefix convention enforced by the code, no namespace validation.

**Consequences:** Silent data corruption in enrichment lookups. Incorrect joins in DuckDB queries. Reconciliation artifacts that reference the wrong record type.

**Prevention:**
1. Define distinct ID prefixes: `obs_` for observations, `pty_` for parties, `coh_` for cohorts, `phs_` for phases, `trn_` for transitions, `row_` for analyst rows, `jdg_` for judgments
2. Add a model validator on each v2 model that rejects IDs not matching its prefix
3. Ensure v1 `evt_` and `actor_` prefixes are reserved and never used by v2 models
4. DuckDB v2 tables should have different primary key column names (e.g., `observation_id` not `event_id`) to prevent accidental joins

**Detection:** A Pydantic `model_validator` that rejects cross-namespace IDs. Add a test that asserts no v2 ID prefix matches any v1 ID prefix.

**Phase assignment:** Phase 1 (data model). ID conventions must be established before any extraction produces v2 artifacts.

---

### Pitfall 10: Reconciliation Infrastructure Breaks During Architecture Transition

**What goes wrong:** The `/reconcile-alex` skill compares `deal_events.csv` against Alex's spreadsheet. The comparison is row-by-row, matching on bidder name + date + event type. The v2 triple export produces three CSVs (`literal_observations.csv`, `analyst_rows.csv`, `benchmark_rows_expanded.csv`). None of these have the same shape as `deal_events.csv`.

During migration, reconciliation must continue working to measure whether v2 is better or worse than v1. But:
- The reconciliation skill reads `deal_events.csv` at a fixed path (`data/skill/<slug>/export/deal_events.csv`)
- Alex's spreadsheet uses v1 event type labels ("NDA", "Drop", "Final Round Ann")
- The legacy adapter must produce these exact labels from v2 observation types
- The reconciliation skill's row-matching logic depends on v1 semantics (e.g., "Drop" vs v2's `StatusObservation(status_kind="withdrew")`)

**Why it happens:** Reconciliation was built for v1. The v2 architecture changes the meaning of rows. Even if the adapter produces rows with v1 labels, the provenance information in v2 (which observation created this row, which rule derived it) is lost in the flattening.

**Consequences:** Cannot measure v2 improvement during migration. The 70.7% baseline becomes meaningless if the comparison surface changes. Cannot make go/no-go decisions on v2 per-deal migration.

**Prevention:**
1. During migration, always produce `deal_events.csv` through the v1 path for deals still on v1
2. For deals migrated to v2, produce `deal_events.csv` through the legacy adapter AND produce `analyst_rows.csv` through the v2 path
3. Run reconciliation against both: v1 reconciliation for regression detection, v2 reconciliation for improvement measurement
4. Extend reconciliation to classify mismatches into the 6 families proposed in the GPT Pro review (literal missing, derived missing, anonymous expansion gap, policy disagreement, date precision, filing supports pipeline)
5. The v2 reconciliation surface should compare `analyst_rows.csv` + `benchmark_rows_expanded.csv` against Alex, not `deal_events.csv`

**Detection:** If `deal_events.csv` does not exist after a v2 deal pipeline run, reconciliation is broken. Gate this with a file-existence check.

**Phase assignment:** Phase 4 (triple export). The legacy adapter and v2 reconciliation surface must be built together.

---

## Minor Pitfalls

Mistakes that cause localized friction but are recoverable.

---

### Pitfall 11: Structured Coverage Records Lose Free-Text Analytical Reasoning

**What goes wrong:** The v2 `CoverageCheckRecord` replaces free-text `coverage_notes: list[str]` with structured records (`cue_family`, `status`, `supporting_observation_ids`, `reason_code`, `note`). The GPT Pro review correctly identifies that free-text notes drift and lose referential integrity. But the current coverage notes contain genuinely useful analytical reasoning that does not fit cleanly into structured fields:

- "actor_lifecycle: Company H remained a remote superior-proposal possibility... so no explicit drop event was extracted" (STEC)
- "Sanofi's engagement straddled an earlier terminated process and the restarted process" (Medivation)

Converting these to `status: "not_found"` + `reason_code: "remote_possibility"` loses the nuance. But keeping a free-text `note` field recreates the original problem.

**Prevention:**
1. Allow a structured `note` field but validate it is subordinate to the structured fields -- the `cue_family`, `status`, and `reason_code` must be filled before `note` is populated
2. Define a finite set of `reason_code` values that cover the known analytical patterns
3. Accept that some nuance is lost -- structured coverage is better than drifting prose even if it is less expressive

**Phase assignment:** Phase 1 (data model, as part of `CoverageCheckRecord` definition).

---

### Pitfall 12: Span Reuse Between v1 Events and v2 Observations

**What goes wrong:** v1 events and v2 observations reference the same underlying `spans.json` file via `evidence_span_ids`. During parallel operation, a span might be referenced by both a v1 `SkillEventRecord` and a v2 `ProposalObservation`. This is correct behavior -- the same filing text supports both representations. But if the canonicalize stage is modified for v2 without preserving v1 span resolution, existing v1 span references break.

**Prevention:**
1. `spans.json` is a shared artifact -- do not modify the `SpanRecord` model or `SpanRegistryArtifact` during migration
2. v2 extraction can ADD new spans but must not modify or remove existing spans
3. If v2 needs additional span metadata (e.g., observation-type annotations), add it in a v2-specific sidecar, not by extending `SpanRecord`

**Phase assignment:** Phase 2 (extraction contract). Span sharing must be explicit in the extraction design.

---

### Pitfall 13: Rule Engine DerivationBasis Provenance Overhead

**What goes wrong:** Every derived record (`ProcessPhaseRecord`, `LifecycleTransitionRecord`, `CashRegimeRecord`, `JudgmentRecord`, `AnalystRowRecord`) carries a `DerivationBasis` with `rule_id`, `source_observation_ids`, `source_span_ids`, `confidence`, and `explanation`. For a deal like PetSmart with many observations, the derivation layer could produce hundreds of derived records, each with provenance. The resulting JSON artifacts become large and difficult to inspect manually.

**Prevention:**
1. DerivationBasis is essential for auditability -- do not remove it
2. Add a summary view that shows derived records without provenance for human review
3. Consider storing derivation provenance in a separate sidecar file rather than inline in every record
4. The DuckDB load can flatten provenance into a `derivation_log` table rather than embedding it in every derived record table

**Phase assignment:** Phase 3 (derivation engine). Design the provenance storage before building rules.

---

### Pitfall 14: `other` Enum Escape Hatch Creates Classification Debt

**What goes wrong:** Every v2 observation type has an `other` variant plus an `other_detail: str` field. The GPT Pro review says "use other plus other_detail rather than forcing a novel pattern into the wrong enum." This is correct for extraction robustness. But if the extraction LLM uses `other` frequently, the derivation engine cannot derive from it -- rules key on specific `obs_type` and `*_kind` values, not on `other`.

Over time, `other` accumulates unclassified observations that the engine ignores. These are not coverage gaps (the observation exists) but are derivation gaps (no analyst row is produced). The coverage gate says "observed" but the analyst surface is incomplete.

**Prevention:**
1. Track `other` usage rates per deal and per observation type
2. If `other` exceeds 10% of observations for any deal, investigate whether a new enum value is needed
3. Derivation rules should explicitly handle `other` by emitting a review flag, not by silently skipping
4. Coverage gates should distinguish "observed as other" from "observed as typed" in their reporting

**Phase assignment:** Phase 2 (extraction contract) and Phase 3 (derivation engine). Monitor `other` rates from the first extraction.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Pre-Phase 1: Bug fixes | All-cash short-circuit fix changes baseline (Pitfall 4) | Fix and re-baseline BEFORE starting v2 work |
| Phase 1: Data model | Premature v1 removal (Pitfall 1), cohort edge cases (Pitfall 7), ID collisions (Pitfall 9) | Additive models only, validate against real deals, prefix conventions |
| Phase 2: Extraction contract | Prompt changes affect all deals (Pitfall 3), span reuse (Pitfall 12), `other` escape hatch (Pitfall 14) | Separate v2 skill doc, per-deal migration, monitor `other` rates |
| Phase 3: Derivation engine | Rule complexity creep (Pitfall 6), provenance overhead (Pitfall 13) | Explicit rule DAG, separate provenance storage |
| Phase 4: Triple export | Legacy adapter CSV shape (Pitfall 5), reconciliation breakage (Pitfall 10) | Byte-level comparison tests, parallel reconciliation |
| All phases: Testing | Test coverage gap (Pitfall 8) | Freeze v1 tests, parallel v2 test tree |
| All phases: DuckDB | Schema evolution (Pitfall 2) | Additive tables only, snapshot before changes |

---

## Sources

- `skill_pipeline/models.py` -- v1 model definitions, field names, `extra="forbid"` on `SkillModel`
- `skill_pipeline/enrich_core.py` -- all-cash bug at lines 660-688, round pairing at lines 170-212, dropout classification at lines 564-635
- `skill_pipeline/extract_artifacts.py` -- `LoadedExtractArtifacts` dual-mode loading, `MixedSchemaError`
- `skill_pipeline/db_schema.py` -- DuckDB schema DDL, bolt-on `ALTER TABLE` at line 141
- `skill_pipeline/db_load.py` -- v1-specific field destructuring in `_load_actors()`, `_load_events()`
- `skill_pipeline/db_export.py` -- v1 taxonomy maps (`EVENT_TYPE_PRIORITY`, `NOTE_BY_EVENT_TYPE`, `BIDDERLESS_EVENT_TYPES`), `_format_event_row()` output shape
- `skill_pipeline/gates.py` -- `SUBSTANTIVE_EVENT_TYPES` and `EVENT_PHASES` hardcoded to v1 taxonomy
- `diagnosis/gptpro/2026-03-31/round_1/response.md` -- GPT Pro architectural review identifying 7 structural bottlenecks and proposed observation graph architecture
- `.claude/skills/extract-deal/SKILL.md` -- extraction prompt contract, quote-before-extract protocol
- `.claude/skills/reconcile-alex/SKILL.md` -- reconciliation procedure against benchmark spreadsheet
- `tests/test_skill_enrich_core.py` -- 33 tests with v1-specific fixtures and assertions
- `tests/test_skill_db_load.py` -- v1-specific canonical fixture helpers and DuckDB assertions
- `tests/test_skill_extract_artifacts.py` -- v1 schema mode detection tests
