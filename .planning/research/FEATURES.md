# Feature Landscape: v2.0 Observation Graph Architecture

**Domain:** Observation graph data model, cohort-based actor representation, deterministic derivation engine, structured coverage records, and triple export surface for filing-grounded M&A extraction pipeline
**Researched:** 2026-03-30
**Overall Confidence:** HIGH (architecture proposal validated against 9-deal corpus evidence, GPT Pro structural review, and existing v1 artifact contracts)

---

## Scope Boundary

This document covers only the NEW observation graph features. The following
are already shipped and out of scope for this feature analysis:

- 20-type flat SkillEventRecord extraction with quote-first evidence
- Grouped actors with is_grouped/group_size/group_label
- Round pairing from event type matching (_pair_rounds)
- Bid classification via formality signals + process position rules
- Cycle segmentation from restart boundaries
- Dropout classification (bidder-withdrawal vs target-exclusion)
- All-cash inference from cycle-local consideration patterns
- DuckDB load/export with enrichment overlay
- Free-text coverage_notes on event artifacts
- Reconciliation against Alex's benchmark spreadsheet

---

## Table Stakes

Features the observation graph must have. Missing any one means the v2
architecture fails to resolve the structural bottlenecks diagnosed in v1.

---

### TS-1: Typed Observation Extraction (6 Observation Types)

| Attribute | Detail |
|-----------|--------|
| Why Expected | The core architectural thesis: SkillEventRecord is pitched at the wrong abstraction level. The extractor asks the LLM to produce analyst rows directly, which causes systematic compression loss for lower-level filing facts (solicitations, status changes, agreement amendments). Without typed observations, v2 has no reason to exist. |
| Complexity | High |
| Dependencies | Existing chronology blocks, evidence items, span infrastructure, quote-first protocol. Reuses ResolvedDate, MoneyTerms, SpanRecord from v1 models.py. |
| Confidence | HIGH -- 7 structural bottlenecks in v1 trace directly to the flat event taxonomy |

**What it provides:**

Six observation subtypes replace the 20-type flat SkillEventRecord:

1. **ProcessObservation** -- sale launches, public announcements, advisor retentions, press releases. Captures initiation-layer facts that v1 mixes into analyst event types.

2. **AgreementObservation** -- NDAs, NDA amendments, standstills, exclusivity, merger agreements, clean team arrangements. Currently v1 has only `nda_signed: bool`. The v2 model adds `agreement_kind`, `signed`, `grants_diligence_access`, `includes_standstill`, and critically `supersedes_observation_id` for agreement chains (resolves Penford second-NDA problem).

3. **SolicitationObservation** -- process letters requesting IOIs, LOIs, binding offers, best-and-final bids. Captures `requested_submission`, `binding_level`, `due_date`, `recipient_refs`, and `attachments`. This is the observation from which round structure is derived (resolves STEC informal-round problem).

4. **ProposalObservation** -- initial proposals, revisions, verbal confirmations. Links to solicitations via `requested_by_observation_id` and to prior proposals via `revises_observation_id`. Carries `delivery_mode`, `terms`, and formality-relevant signals (`mentions_non_binding`, `includes_draft_merger_agreement`, `includes_markup`).

5. **StatusObservation** -- expressed interest, withdrew, not interested, cannot improve, cannot proceed, limited assets only, excluded by board, selected to advance. This is the filing-literal observation from which drop rows are derived (resolves STEC "cannot improve" problem where Company H's status statement had to be over-interpreted into a `drop` event).

6. **OutcomeObservation** -- executed, terminated, restarted. Clean terminal events.

**Extraction contract shift:** The LLM no longer produces analyst rows. It produces filing-literal observations with spans. The derivation engine produces analyst rows.

**Every observation subtype uses Literal discriminator on `obs_type`**, enabling Pydantic discriminated union validation. This is production-proven and avoids the performance cost of left-to-right union matching.

---

### TS-2: PartyRecord Replacing v1 Actor Schema

| Attribute | Detail |
|-----------|--------|
| Why Expected | Named entity extraction is the foundation. PartyRecord is structurally similar to SkillActorRecord but adds the `"other"` role option and drops grouped-actor fields (those move to CohortRecord). Without a clean party model, observations have no subjects. |
| Complexity | Low |
| Dependencies | Existing actor extraction pass (pass 1 of extract-deal). Reuses canonical_name, aliases, advisor_kind, advised_party_id, bidder_kind from v1. |
| Confidence | HIGH -- straightforward schema reshaping |

**What changes from v1 SkillActorRecord:**
- Drops `is_grouped`, `group_size`, `group_label` (moved to CohortRecord)
- Drops `listing_status`, `geography` (these are enrichment-layer attributes, not filing-literal party attributes -- can be re-added to derivation if needed)
- Adds `role: "other"` for entities that are not bidder/advisor/activist/target_board
- Renames `actor_id` to `party_id` for clarity
- Renames `quote_ids` / `evidence_span_ids` to just `evidence_span_ids` (already canonical in v1)

---

### TS-3: CohortRecord for Unnamed Group Lifecycles

| Attribute | Detail |
|-----------|--------|
| Why Expected | Grouped actors in v1 are counts, not lifecycle participants. One grouped actor can only toggle as one thing. PetSmart's 15 NDA signers, 6 IOI submitters, 4 finalists, and 2 screened-out bidders cannot be individually represented. CohortRecord is the architectural answer to this. Without it, unnamed-party lifecycle tracking remains impossible. |
| Complexity | Medium |
| Dependencies | PartyRecord (for known_member_party_ids). Observations (for created_by_observation_id). |
| Confidence | HIGH -- PetSmart reconciliation makes the failure mode explicit |

**What it provides:**

- `cohort_id`, `label`, `exact_count`
- `known_member_party_ids` -- the named members (can be empty)
- `unknown_member_count` -- equals `exact_count - len(known_member_party_ids)`
- `parent_cohort_id` -- enables cohort nesting (15 NDA signers -> 6 IOI submitters -> 4 finalists)
- `membership_basis` -- what defined this group ("signed NDA", "submitted IOI", "advanced to final round")
- `created_by_observation_id` -- which observation established this cohort
- `evidence_span_ids` -- filing grounding

**Cohort arithmetic invariant:**
- `unknown_member_count == exact_count - len(known_member_party_ids)` -- enforced at validation time
- Child cohort counts cannot exceed parent counts
- If a cohort split is declared exhaustive, child counts must sum to parent

**Observations reference cohorts via `subject_refs` and `counterparty_refs`**, which accept both party_ids and cohort_ids. This is the key design that lets unnamed groups participate in the observation graph as first-class entities.

---

### TS-4: Deterministic Derivation Engine

| Attribute | Detail |
|-----------|--------|
| Why Expected | The whole point of separating literal observations from analyst rows is that derivation becomes explicit, rule-based, and provenance-bearing. Without the derivation engine, the observation graph is just a different extraction format with no analytical output. |
| Complexity | High |
| Dependencies | All observation types (TS-1), PartyRecord (TS-2), CohortRecord (TS-3). Replaces and subsumes current enrich_core.py logic (_pair_rounds, _classify_proposal, _classify_dropouts, _infer_all_cash_overrides, _segment_cycles). |
| Confidence | HIGH -- rule catalog is concrete and maps directly to diagnosed v1 failures |

**Derived record types:**

1. **ProcessPhaseRecord** -- informal round, formal round, extension, endgame. Derived from SolicitationObservation + deadline observations. Replaces v1's indirect round reconstruction from event-type pairing.

2. **LifecycleTransitionRecord** -- tracks party/cohort state changes: unknown -> identified -> under_nda -> active -> submitted -> finalist -> inactive -> winner. Each transition carries a `reason_kind` (literal, not_invited, cannot_improve, lost_to_winner) and a `DerivationBasis` with source observation IDs.

3. **CashRegimeRecord** -- all_cash/mixed/unknown scoped to a cycle or phase. Replaces v1's sparse `all_cash_overrides` dict. Fixes the all-cash short-circuit bug where `_infer_all_cash_overrides()` exits early when an executed event exists with missing consideration type.

4. **JudgmentRecord** -- initiation type, advisory link, ambiguous exit reason, ambiguous phase. Captures the small set of genuinely ambiguous decisions that require analytical judgment.

5. **AnalystRowRecord** -- the benchmark-compatible row surface. Each row carries `origin` (literal/derived/synthetic_anonymous), `analyst_event_type` (the 20 v1 event types), `basis` with source observation IDs, `rule_id`, and `review_flags`.

**Every derived record carries a `DerivationBasis`:**
```python
class DerivationBasis(SkillModel):
    rule_id: str                    # e.g., "ROUND-01", "EXIT-02"
    source_observation_ids: list[str]
    source_span_ids: list[str]
    confidence: Literal["high", "medium", "low"]
    explanation: str
```

**Core rule catalog (initial):**

| Rule | Input | Output | Resolves |
|------|-------|--------|----------|
| ROUND-01 | Solicitation requesting non-binding IOIs by due date | Informal phase + final_round_inf_ann/inf rows | STEC informal round |
| ROUND-02 | Solicitation requesting LOIs/binding/best-and-final + DMA/markup | Formal phase + final_round_ann/final_round rows | Mac-Gray formal round |
| EXIT-01 | StatusObservation(withdrew/not_interested/cannot_proceed) | Literal drop row | Direct withdrawals |
| EXIT-02 | StatusObservation(cannot_improve) after prior proposal | Inferred drop row with subtype | STEC Company H |
| EXIT-03 | Selected-subset observation; active parties absent from subset | Inferred target-elimination transitions | PetSmart screening |
| EXIT-04 | Exclusivity/execution with one bidder; other active parties | lost_to_winner closure | Endgame drops |
| AGREEMENT-01 | Agreement with supersedes_observation_id | Amendment/chain row | Penford second NDA |
| CASH-01 | Explicit proposal consideration type | Row-level cash flag | Direct |
| CASH-02 | Cash merger agreement | Cycle/phase cash regime | Saks |
| CASH-03 | All typed proposals in phase are cash, no contrary evidence | Untyped proposals inherit all_cash | STEC |

---

### TS-5: Structured Coverage Records (CoverageCheckRecord)

| Attribute | Detail |
|-----------|--------|
| Why Expected | Free-text coverage_notes is the diagnosed source of stale references, unstructured reasoning, and unrepairable drift. Medivation's stale notes that outlived the event array they referenced demonstrate the failure mode. Without structured coverage, the v2 system inherits v1's most fragile artifact. |
| Complexity | Low-Medium |
| Dependencies | Observation IDs and span IDs for referential integrity. |
| Confidence | HIGH -- directly addresses diagnosed v1 failure |

**What it provides:**

```python
class CoverageCheckRecord(SkillModel):
    cue_family: str                                    # e.g., "proposal", "nda", "withdrawal"
    status: Literal["observed", "derived", "not_found", "ambiguous"]
    supporting_observation_ids: list[str]
    supporting_span_ids: list[str]
    reason_code: str | None = None
    note: str | None = None                            # structured, not free-text essay
```

**Key design properties:**
- Coverage is regenerated from observations and derivations every run
- No free-text references to event IDs that can drift
- `not_found` requires a `reason_code`, not a prose essay
- `ambiguous` surfaces cases that need review flags, not silent coverage_notes
- Coverage records are keyed to `cue_family` (matching existing coverage.py's cue detection), making them drop-in replacements for the current CoverageFinding model

**What it replaces:** `coverage_notes: list[str]` on RawSkillEventsArtifact/SkillEventsArtifact (models.py:300-306)

---

### TS-6: Legacy Adapter (v2 -> v1 CSV Shape)

| Attribute | Detail |
|-----------|--------|
| Why Expected | The 9-deal benchmark reconciliation infrastructure, the DuckDB export pipeline, and the reconcile-alex skill all consume the v1 CSV shape. Without a legacy adapter, v2 cannot be tested against v1's benchmark baseline. Migration is impossible without backward compatibility. |
| Complexity | Medium |
| Dependencies | AnalystRowRecord from derivation engine (TS-4). Existing db_export.py column layout. |
| Confidence | HIGH -- essential for incremental migration |

**What it provides:**
- Maps v2 AnalystRowRecord back to the v1 CSV column layout: BidderID, Note, BidderName, Type, BidType, Value, Range, DateR, DateP, Cash, C1, C2, C3, ReviewFlags
- Preserves all existing reconciliation compatibility
- Allows v1 and v2 to run in parallel on the same deal, producing comparable outputs
- Implemented as a thin mapping layer in db_export.py or a new v2_export.py

**Not a feature to defer.** The legacy adapter is table stakes because without it there is no way to verify that v2 is at least as correct as v1.

---

## Differentiators

Features that set the v2 architecture apart from v1. Not strictly required for
parity, but they are the reason to build v2 in the first place.

---

### D-1: Triple Export Surface

| Attribute | Detail |
|-----------|--------|
| Value Proposition | Separates filing audit, analyst analysis, and benchmark comparison into three distinct CSV surfaces. Eliminates the v1 problem where one CSV must serve all three purposes, conflating filing-grounded facts with analyst interpretations and benchmark-format requirements. |
| Complexity | Medium |
| Dependencies | Derivation engine (TS-4), CohortRecord (TS-3). DuckDB schema additions for v2 tables. |
| Confidence | HIGH -- directly implements the GPT Pro recommendation |

**Three surfaces:**

1. **literal_observations.csv** -- strict filing-grounded observations only. This is the audit surface. Each row is one observation with obs_type, date, subject, counterparty, summary, and evidence span references. No derived content.

2. **analyst_rows.csv** -- derived benchmark-style rows with provenance columns: `origin` (literal/derived/synthetic_anonymous), `rule_id`, `source_observation_ids`, `confidence`, `review_flags`. This is the analytical surface.

3. **benchmark_rows_expanded.csv** -- analyst rows with optional synthetic anonymous slot expansion for cohort rows. PetSmart's "15 NDA signers" becomes 15 individual `synthetic_anonymous` rows (anon_slot_001 through anon_slot_015), clearly marked as synthetic. This is the benchmark-parity surface.

**Export 3 is where unnamed cohorts get expanded.** Not in the core model. Synthetic slots never drive derivation, never appear in the literal table, and are always marked as non-factual identities.

---

### D-2: Observation-to-Observation References (Graph Edges)

| Attribute | Detail |
|-----------|--------|
| Value Proposition | Filing facts are not independent events -- proposals revise earlier proposals, agreements supersede earlier agreements, solicitations request submissions that become proposals. Cross-observation references create a graph structure that enables correct derivation without stringly-typed heuristics. |
| Complexity | Low (schema only, validation is the work) |
| Dependencies | All observation types. |
| Confidence | HIGH -- schema fields already defined in the architecture proposal |

**Reference fields across observation types:**

| Source Type | Reference Field | Target Type | Semantics |
|-------------|----------------|-------------|-----------|
| ProposalObservation | revises_observation_id | ProposalObservation | Price revision chain |
| ProposalObservation | requested_by_observation_id | SolicitationObservation | Response to process letter |
| AgreementObservation | supersedes_observation_id | AgreementObservation | NDA amendment, standstill overlay |
| StatusObservation | related_observation_id | Any Observation | What the status refers to |
| OutcomeObservation | related_observation_id | Any Observation | What was executed/terminated |

**Graph validation gates:**
- Revision and supersession chains must be acyclic
- Reference targets must exist in the observation array
- Deadlines cannot precede solicitations
- Execution cannot happen before the winning party becomes active

---

### D-3: Derivation Provenance and Review Flags

| Attribute | Detail |
|-----------|--------|
| Value Proposition | Every derived fact (phase, transition, analyst row) carries explicit provenance: which rule produced it, from which observations, with what confidence. Medium/low-confidence derived rows surface review flags. This makes the analytical layer transparent and auditable, unlike v1 where enrichment annotations have opaque `basis: str` fields. |
| Complexity | Low (schema design) to Medium (consistent application) |
| Dependencies | DerivationBasis model, derivation engine (TS-4). |
| Confidence | HIGH |

**What it enables:**
- Analyst can trace any benchmark row back to the specific filing observations that produced it
- When reconciliation finds a mismatch, the `rule_id` immediately identifies which derivation rule to examine
- Review flags surface on the export CSV, not buried in enrichment artifacts
- Policy disagreements (Providence-Worcester Informal-vs-Formal) are identifiable at the rule level, not confused with extraction failures

---

### D-4: Mismatch Classification in Reconciliation

| Attribute | Detail |
|-----------|--------|
| Value Proposition | v1 reconciliation conflates extraction failures with policy disagreements, anonymous expansion gaps, date precision differences, and benchmark errors. Structured mismatch families allow each disagreement to be classified and counted separately, so Providence-style policy disagreements stop contaminating extraction-quality metrics. |
| Complexity | Low-Medium |
| Dependencies | Triple export surface (D-1), derivation provenance (D-3). |
| Confidence | MEDIUM -- reconciliation classification is conceptually clear but implementation requires validation against all 9 deals |

**Mismatch families:**

| Family | Description | Example |
|--------|-------------|---------|
| literal_missing | Filing fact not extracted as observation | Missed NDA |
| derived_missing | Derivation rule did not fire or produced wrong result | Missing inferred drop |
| anonymous_expansion_gap | Cohort row count differs from benchmark individual rows | PetSmart unnamed bidders |
| policy_disagreement | Filing supports pipeline, but benchmark uses different coding convention | Providence Informal/Formal |
| date_precision_difference | Same event, different date resolution | Month-level vs day-level |
| benchmark_error | Filing contradicts benchmark | Providence filing supports pipeline |

---

### D-5: Parallel v1/v2 Contract Execution

| Attribute | Detail |
|-----------|--------|
| Value Proposition | Running v1 and v2 extraction on the same deal produces comparable outputs, enabling direct quality comparison during migration. This avoids the big-bang migration risk where v2 must be perfect before it can replace v1. |
| Complexity | Medium |
| Dependencies | Legacy adapter (TS-6). Separate artifact paths for v2 outputs. |
| Confidence | MEDIUM -- requires careful path separation to avoid artifact contamination |

**Implementation pattern:**

- v2 observations write to `data/skill/<slug>/extract_v2/` (not `data/skill/<slug>/extract/`)
- v2 derivations write to `data/skill/<slug>/derive/`
- v2 DuckDB tables use `v2_` prefix or separate schema (`CREATE SCHEMA v2`)
- v2 exports write to `data/skill/<slug>/export_v2/`
- Legacy adapter maps v2 analyst rows to v1 CSV shape for direct diff
- v1 artifacts remain untouched until v2 is validated stable across all 9 deals

**Schema versioning pattern:** Use Pydantic discriminated unions on a `schema_version` field in the artifact root. The extract_artifacts loader detects v1 vs v2 format and routes accordingly, similar to the existing quote_first vs canonical mode detection.

---

## Anti-Features

Features to explicitly NOT build. These would add complexity without advancing
the v2 architectural goals or would violate project constraints.

---

### AF-1: Graph Database Backend

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Neo4j, ArangoDB, or any graph DB as storage | 9-deal batch corpus does not justify graph DB operational complexity. DuckDB handles array/JSON types natively and is already embedded. The observation "graph" is a conceptual model, not a storage topology. | Keep DuckDB. Add v2 tables (parties, cohorts, observations, derivations) alongside existing v1 tables. Use foreign-key-style ID references for graph edges. |

---

### AF-2: LLM-Based Derivation

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Using an LLM to produce analyst rows from observations | Derivation must be deterministic and reproducible. LLM derivation re-introduces the non-determinism problem that v2 is designed to eliminate from the analytical layer. The v1 enrichment layers are already annotation-only sidecars constrained to existing event IDs -- making derivation LLM-based would repeat that mistake at a different layer. | Deterministic rule engine with explicit rule_id provenance. LLM involvement stays narrowly scoped: extraction of filing-literal observations (pass A/B) and targeted repair (pass C). JudgmentRecord handles the small set of genuinely ambiguous cases. |

---

### AF-3: Dynamic Schema Evolution

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Allowing observation subtypes to be added at runtime without schema changes | Pydantic discriminated unions require compile-time Literal values. Dynamic schema evolution would require abandoning type safety, which contradicts the Pydantic-first schema design and fail-fast project philosophy. | Use `other` + `other_detail: str` on every observation subtype's kind enum. Novel patterns get captured as `other` with free-text detail. Promoting `other` to a new enum value is a deliberate schema change with a test, not a runtime discovery. |

---

### AF-4: Synthetic Slot Expansion in Core Model

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Expanding anonymous cohorts into individual rows in the observation graph or derivation layer | Synthetic slots are not factual identities. If they appear in the core model, they drive derivation and create fake lifecycle chains for non-existent individual parties. PetSmart's anon_slot_007 is not a real bidder and should never have a "drop" event attributed to it at the literal layer. | Keep cohorts as cohorts in the core graph. Expand only at the benchmark_rows_expanded.csv export surface. Mark all synthetic rows with `origin: "synthetic_anonymous"`. |

---

### AF-5: Benchmark-Driven Extraction Rules

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Tuning observation extraction or derivation rules to match Alex's spreadsheet | The filing is the source of truth, not the benchmark. Benchmark-driven tuning is the feedback loop that v2 is designed to break -- it conflates extraction failures with policy disagreements. | Keep benchmark materials post-export only. When reconciliation finds a mismatch, classify it (D-4). If it is a literal_missing or derived_missing, fix the extraction or rule. If it is a policy_disagreement, leave it and document the policy difference. |

---

### AF-6: Interpretive Enrichment in Derivation Engine

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Folding interpretive enrichment (initiation judgment, advisory verification, count reconciliation) into the deterministic derivation engine | Interpretive enrichment requires analyst judgment and LLM reasoning. Mixing it with deterministic rules muddies the provenance boundary between "rule said X" and "analyst judged X". | Keep interpretive enrichment as a separate optional layer (the existing `/enrich-deal` skill pattern). JudgmentRecord in the derivation engine handles the narrow set of cases where derivation rules flag ambiguity, but the judgment itself stays outside the deterministic engine. |

---

## Feature Dependencies

```
PartyRecord (TS-2)
  |
  v
CohortRecord (TS-3) -------> Typed Observations (TS-1)
  |                              |
  |                              v
  |                   Observation References (D-2)
  |                              |
  +------------------------------+
  |
  v
Derivation Engine (TS-4)
  |
  +---> Derivation Provenance (D-3)
  |
  v
Structured Coverage (TS-5) --- regenerated from observations + derivations
  |
  v
Legacy Adapter (TS-6) ------> Triple Export (D-1)
                                  |
                                  v
                          Mismatch Classification (D-4)
                                  |
                                  v
                          Parallel v1/v2 Execution (D-5)
```

**Critical path:** TS-2 -> TS-3 -> TS-1 -> TS-4 -> TS-6 -> validation against 9 deals

**Independent of critical path:** TS-5 (can be built alongside TS-1), D-2 (schema-only, validated later), D-3 (schema-only, built into TS-4)

---

## MVP Recommendation

### Phase 1: Schema + Immediate Fixes (before any v2 extraction)

Prioritize:
1. **All-cash short-circuit bug fix** -- fix `_infer_all_cash_overrides()` in current v1 codebase. Zero migration risk, immediate correctness improvement.
2. **Structured coverage records** (TS-5) -- replace `coverage_notes: list[str]` with `CoverageCheckRecord` even in v1 artifact shape. Low risk, immediately useful, and the model carries forward unchanged into v2.
3. **v2 Pydantic models** -- define PartyRecord, CohortRecord, all 6 observation subtypes, DerivationBasis, all derived record types, and AnalystRowRecord in a new `models_v2.py`. No runtime impact until extraction uses them.

### Phase 2: v2 Extraction Contract

Prioritize:
4. **v2 extraction skill** -- new `/extract-deal-v2` skill that produces parties, cohorts, and observations using the existing prompt packet infrastructure. Write to `extract_v2/` path.
5. **v2 canonicalization** -- span resolution for v2 artifacts (reuses existing canonicalize infrastructure with new model types).
6. **v2 validation gates** -- literal-layer gates (span references, ID resolution, cohort arithmetic) and graph gates (acyclic references, temporal consistency).

### Phase 3: Derivation Engine

Prioritize:
7. **Round derivation rules** (ROUND-01, ROUND-02) -- highest-impact rules, resolve STEC/Mac-Gray round problems.
8. **Exit inference rules** (EXIT-01 through EXIT-04) -- resolve STEC Company H, PetSmart screening, endgame drops.
9. **Cash regime rules** (CASH-01 through CASH-03) -- resolve Saks/STEC all-cash problems.
10. **AnalystRowRecord compilation** -- the rule that produces benchmark-compatible rows from observations and derivations.

### Phase 4: Export + Migration

Prioritize:
11. **Legacy adapter** (TS-6) -- map v2 rows to v1 CSV shape.
12. **Triple export** (D-1) -- literal_observations.csv, analyst_rows.csv, benchmark_rows_expanded.csv.
13. **v2 DuckDB tables** -- parties, cohorts, observations, derivations alongside existing v1 tables.
14. **9-deal validation run** -- v2 on all 9 deals, compare against v1 benchmark scores.

**Defer:**
- **Mismatch classification** (D-4): valuable but non-blocking; implement after v2 export is stable
- **Parallel v1/v2 execution** (D-5): useful during migration but can be done with simple path separation rather than a formal framework
- **Interpretive enrichment for v2**: the existing `/enrich-deal` skill works on v1 artifacts; v2 interpretive enrichment can wait until the deterministic layer is validated

---

## Complexity Summary

| Feature | Complexity | Primary Risk |
|---------|------------|-------------|
| TS-1: Typed Observations | High | Extraction prompt design for 6 subtypes instead of 20-type flat list |
| TS-2: PartyRecord | Low | Straightforward schema reshaping |
| TS-3: CohortRecord | Medium | Cohort arithmetic invariants, parent-child lineage validation |
| TS-4: Derivation Engine | High | Rule catalog completeness, edge cases across 9 deals |
| TS-5: Structured Coverage | Low-Medium | Drop-in replacement for coverage_notes |
| TS-6: Legacy Adapter | Medium | Column mapping fidelity to v1 CSV shape |
| D-1: Triple Export | Medium | DuckDB schema additions, three CSV writers |
| D-2: Observation References | Low | Schema-only; validation is the work |
| D-3: Derivation Provenance | Low-Medium | Consistent DerivationBasis on all derived records |
| D-4: Mismatch Classification | Low-Medium | Classification taxonomy validation across 9 deals |
| D-5: Parallel v1/v2 | Medium | Path separation, artifact contamination prevention |

---

## Infrastructure Reuse Assessment

What can be reused from v1 almost unchanged:

| v1 Component | Reuse Level | Notes |
|-------------|------------|-------|
| raw-fetch | 100% | Immutable filing ingress, no model changes |
| preprocess-source | 100% | Chronology blocks, evidence items unchanged |
| compose-prompts | ~80% | Prompt packet infrastructure reused; task instructions change for v2 observation types |
| canonicalize (span resolution) | ~70% | Span matching logic reused; new model types need new resolution paths |
| ResolvedDate | 100% | Date parsing/normalization unchanged |
| MoneyTerms | 100% | Proposal terms model unchanged |
| SpanRecord | 100% | Span infrastructure unchanged |
| DuckDB connection/schema plumbing | ~90% | open_pipeline_db, lock retry logic unchanged; new tables added |
| verify (quote matching) | ~60% | Quote verification logic reused; new model types need new verification paths |
| coverage (cue detection) | ~50% | Cue family detection logic partially reusable; coverage output model changes to CoverageCheckRecord |
| gates (semantic validation) | ~40% | Temporal/attention-decay logic reusable; event-type-specific gates need rewrite for observation types |
| enrich_core | ~20% | Logic subsumed by derivation engine; classification rules migrate to rule catalog |
| db_export | ~30% | CSV formatting logic partially reusable; triple export replaces single surface |

What must be replaced:

| v1 Component | Replacement | Reason |
|-------------|-------------|--------|
| RawSkillEventRecord / SkillEventRecord | 6 Observation subtypes | Wrong abstraction level |
| RawSkillActorRecord / SkillActorRecord | PartyRecord + CohortRecord | Grouped actors cannot model lifecycles |
| coverage_notes: list[str] | CoverageCheckRecord | Stale free-text references |
| _pair_rounds() | ROUND-01/ROUND-02 derivation rules | Round structure reconstructed from row taxonomy |
| _classify_dropouts() | EXIT-01 through EXIT-04 rules | Limited to existing drop events |
| _infer_all_cash_overrides() | CASH-01 through CASH-03 rules | Short-circuit bug, wrong scope |
| DeterministicEnrichmentArtifact | Derived records with DerivationBasis | Annotation-only sidecar cannot create missing structure |

---

## Sources

- GPT Pro architectural review (2026-03-31): `/home/austinli/Projects/bids_pipeline/diagnosis/gptpro/2026-03-31/round_1/response.md`
- Current v1 models: `/home/austinli/Projects/bids_pipeline/skill_pipeline/models.py`
- Current enrichment logic: `/home/austinli/Projects/bids_pipeline/skill_pipeline/enrich_core.py`
- Current DuckDB schema: `/home/austinli/Projects/bids_pipeline/skill_pipeline/db_schema.py`
- Current export logic: `/home/austinli/Projects/bids_pipeline/skill_pipeline/db_export.py`
- STEC export artifact: `/home/austinli/Projects/bids_pipeline/data/skill/stec/export/deal_events.csv`
- Pydantic discriminated unions: [Pydantic Unions docs](https://docs.pydantic.dev/latest/concepts/unions/)
- DuckDB schema evolution: [DuckDB ALTER TABLE](https://duckdb.org/docs/stable/sql/statements/alter_table)
- W3C PROV provenance standard: [Data Lineage and Provenance](https://www.promptcloud.com/blog/data-lineage-and-provenance/)
- Rule-based inference engines: [Nected rule engine overview](https://www.nected.ai/us/blog-us/rule-based-inference-engine)
- Knowledge graph lifecycle management: [VLDB 2025](https://www.vldb.org/pvldb/vol18/p1390-geisler.pdf)
