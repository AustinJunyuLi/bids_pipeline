# M&A Deal Extraction Pipeline — Implementation Plan v2

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a reproducible, auditable pipeline that converts SEC merger-background narratives into structured, reviewable event chronologies for takeover-auction research. The system must preserve filing text as the only factual source, separate extraction from judgment, preserve exact provenance at span level, support grouped and unnamed entities, handle multi-cycle processes, validate against the 9 reference deals before any corpus-scale run, and produce richer internal artifacts than any downstream CSV export.

**Architecture:** Six-stage per-deal DAG with one feedback loop, exposed as composable CLI commands and orchestrated by a run manager:

```
Seed Registry
    |
    v
[1] Source Discovery & Freeze
    |\
    | \--> Supplementary Snippet Index
    v
[2] Chronology Localization & Blocking
    |
    v
[3] Extraction
    |-- actor register
    |-- event extraction (single-pass or chunked)
    |-- optional targeted recovery
    v
[4] Reconciliation & QA
    |-- span resolution / quote reconstruction
    |-- actor linking / dedupe
    |-- date normalization
    |-- completeness audits
    |-- review flags
    |-- optional recovery loop back to [3]
    v
[5] Enrichment
    |-- formal/informal classification
    |-- cycle segmentation
    |-- derived metrics
    v
[6] Export & Validation
    |-- review CSV
    |-- analytics parquet/sqlite tables
    |-- Alex-compat export adapter
    |-- reference-deal metrics
```

**Tech Stack:** Python 3.11+, edgartools, anthropic (Sonnet 4.5 default, configurable), pydantic v2, SQLite (state store), openpyxl, pyarrow/parquet

**Design doc:** `docs/plans/pipeline-design-v2.md`

------------------------------------------------------------------------

## Task 0: Repo Hardening and Packaging

**Goal**
Make the project runnable from a clean checkout.

**Files**

- create `pyproject.toml`
- create `pytest.ini`
- update `requirements.txt`
- create `pipeline/cli.py`

**Implement**

- installable package metadata
- `pytest` path configuration
- base console entry point `pipeline`

**Tests**

- `pytest -q` works without `PYTHONPATH=.`
- import smoke test for `pipeline`

**Acceptance**

- clean virtualenv install succeeds
- all existing tests run

------------------------------------------------------------------------

## Task 1: Schema v2

**Goal**
Replace `pipeline/schemas.py` with versioned model modules.

**Files**

- create `pipeline/models/common.py`
- create `pipeline/models/source.py`
- create `pipeline/models/extraction.py`
- create `pipeline/models/qa.py`
- create `pipeline/models/enrichment.py`
- create `pipeline/models/export.py`
- update tests accordingly

**Implement**

- all models specified in the design doc:
    - common enums (`ActorRole`, `AdvisorKind`, `BidderKind`, `ListingStatus`, `GeographyFlag`, `DatePrecision`, `ConsiderationType`, `EventType`, `ClassificationLabel`, `QuoteMatchType`, `ReviewSeverity`)
    - `ArtifactEnvelope` base model
    - seed and source models (`SeedDeal`, `FilingCandidate`, `FrozenDocument`, `FilingDiscoveryReport`)
    - chronology models (`ChronologyCandidate`, `ChronologySelection`, `ChronologyBlock`, `SupplementarySnippet`)
    - provenance models (`SourceSpan`, `DateValue`, `MoneyTerms`)
    - actor models (`ActorRecord`, `CountAssertion`)
    - event family models (`EventBase`, `ProcessMarkerEvent`, `NDAEvent`, `ProposalEvent`, `DropEvent`, `RoundEvent`, `OutcomeEvent`, `CycleBoundaryEvent`, `EventUnion` discriminated union)
    - extraction/QA/enrichment/export models (`ExtractionExclusion`, `DealExtraction`, `QAFinding`, `QAReport`, `ProposalClassification`, `CycleRecord`, `DerivedMetrics`, `DealEnrichment`, `ReviewRow`)
- discriminated event union
- artifact envelopes
- schema version constant

**Tests**

- model validation tests for every event family
- serialization round-trip tests
- invalid-combination tests:
    - grouped actor without group metadata
    - proposal without terms
    - round event without round scope
    - unresolved quote span forbidden in canonical export artifact

**Acceptance**

- complete schema test suite passes
- old `schemas.py` removed or reduced to compatibility re-exports only

------------------------------------------------------------------------

## Task 2: Seed Registry Refactor

**Goal**
Turn `seeds.py` into a proper intake layer.

**Files**

- refactor `pipeline/seeds.py`
- create `pipeline/models/seed.py`
- create `tests/test_seeds_registry.py`

**Implement**

- header validation
- normalized issuer grouping
- preservation of conflicting seed evidence
- optional `SeedDeal` artifact with row refs
- stable slug generation retained

**Tests**

- missing required columns -> clear error
- duplicate target-name variants normalize to one slug
- canonical overrides preserved
- malformed dates handled

**Acceptance**

- regenerated `seeds.csv` matches current 401 rows unless intentionally changed
- seed artifact can be emitted even without workbook row provenance

------------------------------------------------------------------------

## Task 3: State Store and Orchestration Skeleton

**Goal**
Replace `status.json` with SQLite-backed run tracking.

**Files**

- create `pipeline/state.py`
- create `pipeline/orchestrator.py`
- create `tests/test_state.py`

**Implement**

- SQLite schema:
    - `runs` (run_id, started_at, finished_at, code_version, config_hash, mode)
    - `stage_attempts` (run_id, deal_slug, stage_name, attempt_no, status, started_at, finished_at, duration_ms, error_code, error_message, review_required)
    - `artifacts` (run_id, deal_slug, artifact_type, path, sha256, schema_version, created_at)
    - `llm_calls` (call_id, run_id, deal_slug, unit_name, provider, model, prompt_version, request_id, input_tokens, cache_creation_input_tokens, cache_read_input_tokens, output_tokens, cost_usd, latency_ms, status)
    - `review_items` (review_id, deal_slug, stage_name, severity, code, message, artifact_path, status, resolved_at)
- `start_run`, `record_stage_attempt`, `record_artifact`, `record_llm_call`, `record_review_item`
- CLI subcommands:
    - `pipeline run`
    - `pipeline source discover`
    - `pipeline source locate`
    - `pipeline extract actors`
    - `pipeline extract events`
    - `pipeline qa`
    - `pipeline enrich`
    - `pipeline export`
    - `pipeline validate references`

**Tests**

- transactionality
- resume semantics
- rerun from stage
- concurrent-safe writes for simple parallel workers

**Acceptance**

- one synthetic run can be started, resumed, and summarized from SQLite

------------------------------------------------------------------------

## Task 4: Source Discovery Refactor

**Goal**
Split `pipeline/source.py` into discovery, ranking, and freeze components.

**Files**

- create `pipeline/source/discovery.py`
- create `pipeline/source/ranking.py`
- create `pipeline/source/fetch.py`
- create `tests/test_source_discovery.py`

**Implement**

- accession-first resolution from seed URL
- explicit date windowing (announcement date +/- 365 days for primary forms, +/- 180 days for supplementary forms; seed URL accession always included even outside window)
- top-k candidate retention (not just one per form)
- direct SEC fallback fetch path when EdgarTools search fails
- source artifact hashing
- atomic JSON writes
- `filing_override.yaml` manual override support

**Tests**

- seed accession preferred when valid
- stale supplementary filings outside window are rejected
- empty/failed EdgarTools call falls back correctly
- deterministic ranking fixtures

**Integration tests**

- run on all 9 reference deals and inspect candidate sets

**Acceptance**

- Zep-like stale 2007 SC 13D no longer appears as an admissible supplementary candidate for a 2015 run unless forced override

------------------------------------------------------------------------

## Task 5: Chronology Locator v2 and Block Builder

**Goal**
Upgrade localization from plain text scoring to hybrid deterministic adjudication and produce extraction blocks.

**Files**

- create `pipeline/source/locate.py`
- create `pipeline/source/blocks.py`
- create `pipeline/source/supplementary.py`
- create `tests/test_locate_reference.py`

**Implement**

- candidate generation from text, sections API, markdown headings, search hits
- confidence model:
    - **high**: deterministic winner, strong section quality, no close competitor
    - **medium**: plausible winner, but short section or close competitor
    - **low**: weak or ambiguous winner
    - **none**: no acceptable chronology
- control flow:
    - high: proceed
    - medium: proceed + review flag
    - low: strict mode blocks; exploratory mode proceeds + blocker flag
    - none: source-stage failure
- block builder that joins wrapped lines into paragraphs while preserving raw line spans
- supplementary snippet indexer (keyword-based, for sale_press_release, bid_press_release, activist_sale, public-announcement corroboration)

**Tests**

- synthetic locator tests retained
- frozen-reference tests for all 9 selected filings
- alternate filing tests for `mac-gray`, `medivation`, `zep`
- short chronology confidence behavior tests for `petsmart-inc` and `providence-worcester`

**Acceptance**

- 9/9 reference deals produce a plausible selected chronology
- confidence labels are stable and review-aware

------------------------------------------------------------------------

## Task 6: Span Resolution, Quote Reconstruction, and Date Normalizer

**Goal**
Build the deterministic normalization substrate before any model integration.

**Files**

- create `pipeline/normalize/spans.py`
- create `pipeline/normalize/quotes.py`
- create `pipeline/normalize/dates.py`
- create `tests/test_quotes.py`
- create `tests/test_dates.py`

**Implement**

- resolve `block_id + anchor_text` to exact raw line span
- reconstruct authoritative quote text from raw filing lines
- whitespace-normalized and punctuation-normalized matching (curly quotes, em-dashes)
- date parsing for:
    - exact days
    - month-only dates
    - early/mid/late-month dates
    - quarter references
    - relative dates anchored to prior explicit event

**Tests**

- exact quote match
- normalized quote match with curly quotes/dashes
- unresolved quote path
- `mid-February 2013` -> correct `DateValue`
- relative date anchored to prior exact date

**Acceptance**

- canonical quote span objects can be generated from synthetic inputs and real filing blocks

------------------------------------------------------------------------

## Task 7: LLM Backend and Prompt Pack

**Goal**
Create a provider-neutral structured-output layer with Anthropic backend first.

**Files**

- create `pipeline/llm/backend.py`
- create `pipeline/llm/anthropic_backend.py`
- create `pipeline/llm/prompts.py`
- create `pipeline/llm/schemas.py`
- create `pipeline/llm/token_budget.py`
- create `tests/test_llm_backend.py`

**Implement**

- protocol:
    - `count_tokens`
    - `invoke_structured`
    - `repair_structured`
- Anthropic backend using current structured outputs API (`output_config.format`)
- prompt versioning and prompt hash recording
- caching controls (stable system prompt + taxonomy cached across deals; chronology block payload cached across actor and event calls on same deal)
- token-route decision function:
    - simple: <= 8k prompt-counted chronology tokens or <= 150 raw chronology lines
    - moderate: 8k-15k tokens or 151-400 lines
    - complex: > 15k tokens or > 400 lines or expected actor count > 15
- cost computation using official API usage fields:
    - `cost_usd = input_tokens * uncached_input_rate + cache_creation_input_tokens * cache_write_rate + cache_read_input_tokens * cache_read_rate + output_tokens * output_rate`

**Tests**

- request payload assembly
- usage parsing and cost computation
- validation-error repair path with mocked provider
- cache metadata recording

**Acceptance**

- provider can emit validated dummy outputs without live API calls

------------------------------------------------------------------------

## Task 8: Actor Extraction

**Goal**
Implement actor register extraction and deterministic reconciliation.

**Files**

- create `pipeline/extract/actors.py`
- create `tests/test_extract_actors.py`

**Implement**

- full chronology actor extraction call
- grouped actor handling (unnamed groups, count assertions, group-to-member reconciliation)
- count assertions
- unresolved mention capture
- actor dedupe/alias merge
- bidder dimension extraction (bidder_kind + listing_status + geography)
- legal and financial advisor distinction

**Tests**

- named bidder + grouped bidder in same deal
- advisor legal/financial distinction
- bidder dimension extraction (strategic/financial + public/private + domestic/non_us)
- actor merge across aliases
- count assertion mismatch flagged

**Integration tests**

- at least 3 reference deals with grouped entities and advisor mentions

**Acceptance**

- actor canonical artifact builds with no unresolved schema issues

------------------------------------------------------------------------

## Task 9: Event Extraction, Chunking, Merge, and Targeted Recovery

**Goal**
Implement adaptive event extraction with completeness-aware recovery.

**Files**

- create `pipeline/extract/events.py`
- create `pipeline/extract/merge.py`
- create `pipeline/extract/recovery.py`
- create `tests/test_extract_events.py`

**Implement**

- simple vs chunked routing (based on token count thresholds from Task 7)
- event extraction using locked actor roster
- overlap-aware event merge (for chunked extraction: 3-5 chunks of ~4k-6k tokens each, with 1-block overlap)
- proposal whole-company scope enforcement (exclude partial-company bids)
- missing-category recovery trigger:
    - proposal-like dollar mentions without proposal events
    - final-round language without round events
    - count assertions implying more NDAs than extracted actors explain
    - no executed/terminated outcome in a complete process
- schema-repair loop (JSON repair pass on validation failure)

**Tests**

- chunk split/merge dedupe
- range proposal preserved (never averaged)
- partial-company proposal excluded
- drop subtype fallback to generic `drop`
- missing final-round marker triggers recovery

**Integration tests**

- full run on STEC and Zep frozen filings with mocked provider outputs
- optional live smoke tests behind env var

**Acceptance**

- canonical raw extraction artifacts can be produced for all 9 deals

------------------------------------------------------------------------

## Task 10: Reconciliation and QA Gates

**Goal**
Build the stage the current architecture is missing.

**Files**

- create `pipeline/qa/rules.py`
- create `pipeline/qa/completeness.py`
- create `pipeline/qa/review.py`
- create `tests/test_qa.py`

**Implement**

- quote verification (resolve evidence refs to exact spans, reconstruct authoritative quotes)
- actor-event structural consistency (resolve actor references in events)
- event ordering (build chronological event ordering, enforce invariants)
- date normalization application
- count-assertion consistency checks
- completeness heuristics
- review-item generation
- override file application (`review/overrides.template.yaml`)
- blockers:
    - unresolved actor ref on an exported event
    - unresolved quote span
    - averaged range bid
    - partial-company proposal not excluded
    - chronology missing for exported deal
    - invalid cycle chronology order

**Tests**

- unresolved actor reference -> blocker
- unresolved quote -> blocker
- proposal count too low -> warning/recovery
- grouped actor count inconsistency -> review flag
- manual override patch application

**Acceptance**

- every canonical extraction artifact ships with a QA report and explicit export gate

------------------------------------------------------------------------

## Task 11: Enrichment

**Goal**
Implement deterministic classification, cycles, and metrics.

**Files**

- create `pipeline/enrich/classify.py`
- create `pipeline/enrich/cycles.py`
- create `pipeline/enrich/features.py`
- create `tests/test_enrichment.py`

**Implement**

- classification cascade (priority order):
    - **F0**: not `proposal` -> `not_applicable`
    - **I1**: `terms.is_range == True` -> `informal` (range bids are informal per Alex's spec)
    - **I2**: signals include `mentions_indication_of_interest`, `mentions_preliminary`, or `mentions_non_binding` -> `informal`
    - **F1**: signals include `includes_draft_merger_agreement`, `includes_marked_up_agreement`, or `mentions_binding_offer` -> `formal`
    - **F2**: prior `final_round_ann` or `final_round_ext_ann` requested final binding bids and proposal occurs after that event in same cycle -> `formal`
    - **F3**: proposal is submitted after `final_round` deadline and round is clearly binding -> `formal`
    - **I3**: proposal tied to `final_round_inf_ann` / `final_round_inf` -> `informal`
    - **U1**: otherwise -> `uncertain` (not default informal)
- explicit and implicit cycle segmentation:
    - explicit `terminated` closes a cycle; explicit `restarted` opens next
    - if `terminated` but no explicit `restarted`, infer new cycle when later initiation cluster appears (target_sale, bidder_sale, bidder_interest, activist_sale, ib_retention) plus material gap (30+ days) or fresh NDA wave
    - if no explicit termination, infer new cycle only when gap >= 180 days and clear re-initiation cluster and actors/advisors materially reset
    - all inferred boundaries require review
- per-cycle formal boundary (earliest proposal classified `formal`; null if none)
- event sequence numbering
- derived metrics:
    - unique named bidders
    - unique grouped bidders
    - NDA count
    - proposal count total, formal, informal
    - peak active bidders
    - cycle count
    - duration from first process event to executed/terminated
    - winning bidder actor id if identifiable
    - initiation type (bidder/target/activist)

**Tests**

- range bid beats formal-round signal -> informal
- draft merger agreement -> formal
- informal final round -> informal
- Zep-like terminated + renewed process -> two cycles
- single-cycle simple deal -> one cycle

**Acceptance**

- enrichment is deterministic and versioned

------------------------------------------------------------------------

## Task 12: Exporters

**Goal**
Produce stable review and analytics outputs from canonical artifacts.

**Files**

- create `pipeline/export/flatten.py`
- create `pipeline/export/review_csv.py`
- create `pipeline/export/parquet.py`
- create `pipeline/export/alex_compat.py`
- create `tests/test_export.py`

**Implement**

- one-row-per-actor-event review CSV (`events_long.csv`)
- Parquet/SQLite table exports (deals, actors, events, event_actor_links, spans, classifications, cycles, qa_findings)
- full quote and source-line export (source_quote not truncated)
- adapter mapping for Alex-compatible fields (`alex_compat.csv` — provisional until workbook is available)
- export exclusion for blocked deals (deals with unresolved blockers excluded from clean export)
- multi-actor event handling:
    - one event, many actor links in canonical model
    - one row per actor-event pair in CSV review export
    - if event has no actor, actor columns blank
    - if event has many actors, duplicate event columns across rows
- `bid_note` mapping:
    - keep `event_type` as canonical field internally
    - keep `proposal_classification` separate
    - `export_bid_note` is adapter-layer only
    - `alex_compat.csv` allows configurable mappings

**Tests**

- multi-actor event expands to multiple rows
- actorless event keeps blank actor columns
- source quote not truncated in canonical export
- provisional Alex mapping configurable

**Acceptance**

- exports build from canonical artifacts without provider access

------------------------------------------------------------------------

## Task 13: Reference Validation Harness

**Goal**
Create the acceptance framework that determines whether the pipeline can run on the corpus.

**Files**

- create `pipeline/validate/reference.py`
- create `pipeline/validate/metrics.py`
- create `pipeline/validate/alignment.py`
- create `tests/test_reference_metrics.py`

**Implement**

- deal-level alignment between pipeline output and reference truth
- actor matching, event matching, proposal-value accuracy, classification accuracy, cycle accuracy
- HTML/markdown diff report
- threshold enforcement

**Tests**

- synthetic alignment cases
- tolerance windows for rough dates
- unmatched-row reporting

**Acceptance**

- produces machine-readable metrics and human-readable diffs for the 9 reference deals

------------------------------------------------------------------------

## Integration Checkpoints

**Checkpoint A: after Task 5**
Source layer on 9 references:

- 9/9 chronology selections generated
- review flags limited and understandable

**Checkpoint B: after Task 10**
Canonical extraction artifacts exist for all 9 references with QA reports.

**Checkpoint C: after Task 11**
Formal/informal and cycle outputs stable enough for comparison.

**Checkpoint D: after Task 13**
Reference metrics determine go/no-go for corpus run.

------------------------------------------------------------------------

## Acceptance Criteria for Corpus Launch

Minimum green-light:

- source selection exact on all 9 references
- zero unresolved quote spans in exported records
- zero unresolved actor refs in exported records
- proposal range preservation 100%
- proposal classification agreement >= 95%
- overall event-type F1 >= 90%
- proposal recall >= 98%
- cycle segmentation exact on all multi-cycle reference deals

------------------------------------------------------------------------

## Summary: Task Execution Order

| Task | Description                                      | Depends on     | ~Effort  |
|------|--------------------------------------------------|----------------|----------|
| 0    | Repo hardening and packaging                     | --             | 30 min   |
| 1    | Schema v2                                        | Task 0         | 90 min   |
| 2    | Seed registry refactor                           | Tasks 0, 1     | 45 min   |
| 3    | State store and orchestration skeleton            | Tasks 0, 1     | 90 min   |
| 4    | Source discovery refactor                         | Tasks 1, 3     | 90 min   |
| 5    | Chronology locator v2 and block builder           | Tasks 1, 4     | 90 min   |
| 6    | Span resolution, quote reconstruction, dates      | Task 1         | 90 min   |
| 7    | LLM backend and prompt pack                       | Tasks 1, 6     | 120 min  |
| 8    | Actor extraction                                  | Tasks 5, 7     | 90 min   |
| 9    | Event extraction, chunking, merge, recovery       | Tasks 7, 8     | 120 min  |
| 10   | Reconciliation and QA gates                       | Tasks 6, 9     | 120 min  |
| 11   | Enrichment                                        | Task 10        | 60 min   |
| 12   | Exporters                                         | Tasks 10, 11   | 90 min   |
| 13   | Reference validation harness                      | Task 12        | 90 min   |

**Total estimated effort: ~19 hours**

Tasks 2 and 3 can run in parallel after Task 1. Task 6 can be developed in parallel with Tasks 4-5 since it depends only on Task 1. Tasks 4-5 are sequential (discovery before localization). Tasks 8-10 are strictly sequential (each stage's output is the next stage's input). Tasks 11-13 are sequential (enrichment before export before validation).

**Recommended build order:**

- **First:** Tasks 0-5 (source layer, schemas, state store, block builder)
- **Second:** Tasks 6-10 (normalization, LLM backend, extraction, QA -- all on 9 frozen filings only)
- **Third:** Tasks 11-13 (enrichment, export, validation harness)
- **Then:** corpus-scale run on ~400 deals

------------------------------------------------------------------------

## Risk Mitigation Plan

**Risk: source-stage false selection**
Mitigation:

- top-k candidate retention
- confidence model
- review gate
- accession/date-window overrides

**Risk: missing events on long chronologies**
Mitigation:

- adaptive chunking
- completeness heuristics
- targeted recovery pass

**Risk: quote drift / hallucinated evidence**
Mitigation:

- model returns span refs, not authoritative quotes
- deterministic quote reconstruction
- export blocks unresolved spans

**Risk: taxonomy ambiguity in excluded files**
Mitigation:

- define subtype semantics explicitly in code now
- isolate exporter label mapping so workbook-specific conventions can be changed later without touching the core model

**Risk: reference validation blocked by missing workbook**
Mitigation:

- build the alignment harness now
- keep Alex-compat export provisional
- request the excluded corrected workbook before final validation sign-off

------------------------------------------------------------------------

## Build Priority

### Build first

**First:** Tasks 0-5
Get the source layer, schemas, state store, and block builder right before touching the model. This will surface whether the 9 reference deals are cleanly localized and whether provenance can be made deterministic.

**Second:** Tasks 6-10
Build the extraction, reconciliation, and enrichment path end to end on the 9 frozen filings only. Do not start the 400-deal corpus until QA gates exist.

**Third:** Tasks 11-13
Add exporters and the reference validation harness. Only then decide whether the reference accuracy is good enough for corpus-scale extraction.

### Defer

Defer these until after reference sign-off:

- **Message Batches API for corpus runs** -- useful because of the 50% cost discount, but harder to debug. Use synchronous calls first.
- **Cross-vendor audit** -- add once canonical artifacts and metrics exist.
- **Compustat linkage and estimation indicators** -- downstream transforms, not extraction-core requirements.
- **Open-world `actors_extended.jsonl` minting** -- not needed until actor normalization is stable.

### Cut

Cut these from the current design:

- `status.json` as primary tracker
- 19-column CSV as the primary internal target
- unconditional two-call extraction
- direct `source_quote` authority from the model
- default-informal fallback classification
