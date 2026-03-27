> **Historical document.** This plan predates the current `skill_pipeline` +
> `.claude/skills/` architecture. References to a `pipeline/` package,
> provider-specific backends, and model-pinned guidance are superseded by the
> live implementation described in `CLAUDE.md`. Retained as design background
> only.

# Pipeline Design v3 — Evidence-First Informal Bids Extraction Pipeline

Date: 2026-03-16
Supersedes: `docs/plans/2026-03-16-pipeline-design-v2.md`

## 1. Purpose

This document specifies the end-to-end architecture for the `bids_data` pipeline.
It updates v2 in two material ways:

1. **Enhanced preprocess** now scans **all frozen filings** for a deal, not only the selected primary filing. The primary chronology remains the narrative backbone, but the pipeline now emits a second evidence tier derived from every available filing.
2. **Chronology confidence** is now decomposed into two separate questions:
   - *ambiguity / wrong-section risk*
   - *coverage adequacy / short-but-probably-correct risk*

All other v2 decisions remain in force unless explicitly changed below.

## 2. Hard Invariants

The following rules are non-negotiable:

- Frozen filing `.txt` snapshots under `raw/` are immutable and never rewritten.
- Filing text is the only factual source of truth.
- Alex's instructions are the extraction spec, not factual evidence for any deal.
- Facts are extracted before judgments; proposals are classified formal/informal only in deterministic Python.
- Every exported fact must trace to a source document and verbatim reconstructed source text.
- Range bids preserve lower and upper bounds separately.
- Partial-company proposals are excluded, not classified.
- All stage outputs are versioned JSON/JSONL/CSV artifacts written atomically.

## 3. Pipeline Overview

The pipeline is a filesystem-backed, SQLite-tracked, stage-oriented architecture:

1. **Raw discovery & freeze**
2. **Enhanced preprocess / source build**
3. **LLM extraction**
   - actor register
   - event extraction
   - targeted recovery
4. **Reconciliation & QA**
5. **Enrichment**
6. **Export**
7. **Reference validation**

The canonical data flow is:

```text
seeds.csv
  -> raw/*/{discovery.json,document_registry.json,filings/*}
  -> data/deals/<slug>/source/*
  -> data/deals/<slug>/extract/*
  -> data/deals/<slug>/qa/*
  -> data/deals/<slug>/enrich/*
  -> data/deals/<slug>/export/*
  -> data/validate/reference_summary.json
```

Run/state tracking lives in `data/runs/pipeline_state.sqlite`.

## 4. Stage 1 — Raw Discovery & Freeze

### 4.1 Inputs

- `data/seeds.csv`
- direct seed URL / accession if present
- EdgarTools search results and deterministic fallback logic

### 4.2 Outputs

Per deal under `raw/<slug>/`:

- `discovery.json`
- `document_registry.json`
- `filings/<accession>.txt`
- optional `.html` / `.md`

### 4.3 Responsibilities

- resolve issuer identity from seed URL/accession before free-text company lookup
- search primary and supplementary filing types
- keep candidate ranking features in the manifest
- freeze all retrieved filings immutably

### 4.4 Non-responsibilities

- no chronology extraction
- no semantic event extraction
- no classification

## 5. Stage 2 — Enhanced Preprocess / Source Build

This stage is the main v3 change.

### 5.1 Objective

Produce a two-tier source bundle:

**Tier 1 — Primary chronology blocks**  
The selected chronology section from the best primary filing. This is the narrative backbone.

**Tier 2 — Cross-filing evidence items**  
Deterministic evidence extracted from **every frozen filing** for the deal, including the primary filing outside the chronology section and all supplementary filings.

### 5.2 Why the two-tier model exists

The chronology section gives temporal order and process logic. Supplementary filings often add:

- actor enrichment (activists, co-investors, counsel, lenders)
- process characterization (standstill, process letter, due diligence references)
- financial terms (termination fees, sponsor equity, valuation references)
- outcome facts (closing, litigation, vote details)

Those filings are useful, but they are not a substitute for the main chronology. Therefore:

- chronology blocks remain the extraction backbone,
- cross-filing evidence becomes a labeled appendix.

### 5.3 Stage 2 outputs

Per deal under `data/deals/<slug>/source/`:

- `chronology_selection.json`
- `chronology_blocks.jsonl`
- `evidence_items.jsonl`
- `supplementary_snippets.jsonl`
- `chronology.json` (legacy bookmark / compatibility)
- `filings/*.txt` materialized copies for downstream span resolution

### 5.4 Chronology selection

Chronology selection is still deterministic and still primary-filing-centric.

The algorithm:

1. evaluate each admissible primary candidate independently;
2. collect chronology candidates via heading heuristics and section scanning;
3. score candidates;
4. choose the best candidate using confidence-aware adjudication.

### 5.5 Confidence model

v2 treated short chronology length as a major confidence penalty. v3 separates confidence into:

- `ambiguity_risk`: is this likely the wrong section, or is there a close competing candidate?
- `coverage_assessment`: if this section is short, does it still look complete and self-contained?

`chronology_selection.json` now stores `confidence_factors`, including:

- `section_length`
- `score_gap`
- `ambiguity_risk`
- `coverage_assessment`

Interpretation:

- **high confidence**: low ambiguity risk; coverage may be `full`, `adequate`, or `short_but_probably_complete`
- **medium confidence**: plausible section with some ambiguity or reduced coverage
- **low confidence**: wrong-section risk or weak evidence of completeness
- **none**: no acceptable chronology

### 5.6 Evidence item scan across all files

The deterministic scanner processes every available filing paragraph-by-paragraph and emits `EvidenceItem` records.

#### Evidence types

- `dated_action`
- `financial_term`
- `actor_identification`
- `process_signal`
- `outcome_fact`

#### Evidence fields

Each `EvidenceItem` includes:

- `evidence_id`
- `document_id`
- `accession_number`
- `filing_type`
- `start_line`
- `end_line`
- `raw_text`
- `evidence_type`
- `confidence`
- `matched_terms`
- `date_text`
- `actor_hint`
- `value_hint`
- `note`

### 5.7 Supplementary snippet contract

`supplementary_snippets.jsonl` is now derived from the evidence scan rather than ad hoc filing-type rules.

It is a filtered view over evidence items intended to support:

- `sale_press_release`
- `bid_press_release`
- `activist_sale`
- `other`

These snippets are not the full evidence registry. They are an extraction appendix.

### 5.8 Key preprocess modules

- `pipeline/preprocess/source.py`
- `pipeline/source/locate.py`
- `pipeline/source/blocks.py`
- `pipeline/source/evidence.py`
- `pipeline/source/supplementary.py`

## 6. Stage 3 — LLM Extraction

The LLM stage consumes:

- chronology blocks
- selected cross-filing evidence items
- later, the locked actor roster

### 6.1 Substage 3A — Actor register extraction

Module: `pipeline/extract/actors.py`

Responsibilities:

- identify actors mentioned in the chronology and appendix
- assign actor role
- capture bidder dimensions when supported
- preserve grouped actors
- emit count assertions
- store unresolved mentions instead of inventing actor links

Outputs:

- `extract/actors_raw.json`
- `extract/actor_usage.json`

### 6.2 Substage 3B — Event extraction

Module: `pipeline/extract/events.py`

Responsibilities:

- classify extraction complexity using token count, line count, and actor count
- route simple deals through a single event pass
- route complex deals through chunked event extraction with overlap
- inject actor roster and selected evidence appendix
- merge chunk outputs deterministically

Outputs:

- `extract/events_raw.json`
- `extract/event_chunks.jsonl`
- `extract/event_usage.json`

### 6.3 Substage 3C — Targeted recovery

Module: `pipeline/extract/recovery.py`

Triggered when deterministic heuristics suggest omissions:

- financial evidence without proposal events
- process-signal evidence without NDA events
- outcome evidence without executed/terminated events
- very sparse event count relative to evidence

Outputs:

- `extract/recovery_raw.json`
- `extract/recovery_usage.json`

### 6.4 Prompt contract

The LLM is asked to cite:

- `block_id` for chronology evidence
- `evidence_id` for cross-filing appendix evidence

The LLM is **not** asked to produce final authoritative quotes. It only points to evidence references and anchor text.

### 6.5 Prompt implementation

System prompts remain sourced from:

- `docs/plans/2026-03-16-prompt-engineering-spec.md`

User-message rendering is implemented in:

- `pipeline/llm/prompts.py`

v3 extends the prompt renderer to include a cross-filing evidence appendix.

## 7. Stage 4 — Reconciliation & QA

This is where provisional LLM output becomes canonical research data.

### 7.1 Responsibilities

- resolve evidence references to exact spans
- reconstruct authoritative source quotes from raw filing lines
- canonicalize actor ids
- reconcile actor/event references
- normalize dates while preserving raw date text
- enforce structural invariants
- detect blockers and review flags

### 7.2 Inputs

- `source/*`
- `extract/actors_raw.json`
- `extract/events_raw.json`

### 7.3 Outputs

- `qa/extraction_canonical.json`
- `qa/report.json`
- `qa/span_registry.jsonl`

### 7.4 Canonicalization rules

- actor ids are deterministic and deduplicated
- unresolved event actor references become blockers
- proposal events missing required term fields become blockers
- range bids lacking both bounds become blockers
- partial-company proposals are excluded and flagged if they reach canonical reconciliation
- unresolved spans become blockers for export

### 7.5 QA findings

`QAReport` records findings with severity:

- `info`
- `warning`
- `error`
- `blocker`

Current deterministic diagnostics include:

- unknown actor references
- unresolved spans
- missing chronology
- evidence/event completeness mismatches

### 7.6 Key modules

- `pipeline/qa/rules.py`
- `pipeline/qa/completeness.py`
- `pipeline/qa/review.py`
- `pipeline/normalize/spans.py`
- `pipeline/normalize/quotes.py`
- `pipeline/normalize/dates.py`

## 8. Stage 5 — Enrichment

This stage is fully deterministic.

### 8.1 Responsibilities

- formal/informal proposal classification
- event sequencing
- cycle segmentation
- formal-boundary detection
- derived metrics

### 8.2 Formal / informal classification

Implemented in `pipeline/enrich/classify.py`.

Current cascade:

1. range bids -> informal
2. explicit informal language (`indication of interest`, `preliminary`, `non-binding`) -> informal
3. explicit binding package (`draft merger agreement`, `marked-up agreement`, `binding offer`) -> formal
4. formal-round context / process-letter signal -> formal
5. informal-round context -> informal
6. residual -> uncertain

### 8.3 Cycle segmentation

Implemented in `pipeline/enrich/cycles.py`.

Rules:

- explicit `restarted` starts a new cycle on that event
- explicit `terminated` marks the prior cycle as one with explicit termination/restart basis
- long gaps plus reinitiation events can trigger inferred cycles
- inferred cycle boundaries are marked as review-relevant

### 8.4 Derived metrics

Implemented in `pipeline/enrich/features.py`.

Currently includes:

- bidder counts
- proposal counts (formal / informal)
- NDA count
- cycle count
- duration
- peak active bidders

### 8.5 Outputs

- `enrich/deal_enrichment.json`

## 9. Stage 6 — Export

The export layer is deliberately split from the canonical model.

### 9.1 Outputs

Per deal:

- `export/events_long.csv`
- `export/alex_compat.csv`
- `export/canonical_export.json`
- `export/reference_metrics.json`

### 9.2 Review CSV

`events_long.csv` is the canonical row-wise review surface.

Shape:

- one row per actor-event pair
- actorless events still produce a row with blank actor columns
- source quote is full, not truncated

### 9.3 Alex-compatible export

`alex_compat.csv` is a 47-column adapter layer.

Important details:

- `bidderID` is derived from deterministic event sequence
- `bid_type` carries proposal classification (`formal` / `informal` / `uncertain`)
- `bid_note` is blank for proposal rows and populated for non-proposal event types
- source provenance columns are retained even though the historical workbook did not cleanly separate them
- this adapter is necessarily provisional because the corrected workbook itself is not bundled in the snapshot

### 9.4 Canonical export JSON

`canonical_export.json` packages:

- canonical extraction
- QA report
- enrichment

This file is intended for downstream reproducibility and audit.

### 9.5 Key modules

- `pipeline/export/flatten.py`
- `pipeline/export/alex_compat.py`
- `pipeline/export/review_csv.py`

## 10. Stage 7 — Reference Validation

### 10.1 Current contract

The bundle does not include the corrected workbook needed for row-level truth alignment, so v3 implements an internal reference-validation surface rather than a full ground-truth comparator.

Current outputs:

- `data/validate/reference_summary.json`

Per-deal metrics are aggregated from:

- QA blocker / warning counts
- export pass/fail gate
- event counts
- proposal counts
- cycle counts
- source confidence

### 10.2 Future extension

Once the corrected workbook is available in-repo, this stage should be extended to:

- match pipeline rows to workbook rows
- score event recall / precision
- score proposal classification accuracy
- score cycle-boundary agreement

### 10.3 Key modules

- `pipeline/validate/reference.py`
- `pipeline/validate/metrics.py`

## 11. Data Model Summary

### 11.1 Source-layer models

- `SeedDeal`
- `FilingCandidate`
- `FrozenDocument`
- `ChronologyCandidate`
- `ChronologySelection`
- `ChronologyBlock`
- `EvidenceItem`
- `SupplementarySnippet`

### 11.2 Extraction-layer models

- `ActorRecord`
- `CountAssertion`
- `SourceSpan`
- `DateValue`
- `MoneyTerms`
- event union models
- `DealExtraction`

### 11.3 QA / enrichment / export models

- `QAFinding`
- `QAReport`
- `ProposalClassification`
- `CycleRecord`
- `DerivedMetrics`
- `DealEnrichment`
- `ReviewRow`

## 12. State and Orchestration

### 12.1 State store

SQLite database at `data/runs/pipeline_state.sqlite` tracks:

- runs
- stage attempts
- artifacts
- LLM calls
- review items

### 12.2 CLI

The CLI is stage-aware and now wires actual implementations for:

- `raw fetch`
- `preprocess source`
- `extract actors`
- `extract events`
- `qa`
- `enrich`
- `export`
- `validate references`

### 12.3 Batch orchestration

`pipeline/orchestrator.py` exposes batch entry points for each concrete stage.

## 13. Cost and Context Control

v3 preserves the v2 principle that preprocessing is the main cost-control mechanism.

The pipeline avoids dumping all filings directly into the model. Instead it provides:

- compact chronology blocks
- compact evidence appendix
- optional recovery subsets

This reduces cost, improves provenance control, and lowers noise.

## 14. Testing Strategy

The codebase is expected to pass `pytest` from repo root.

Testing layers:

- unit tests for deterministic utilities
- mocked LLM tests for extraction orchestration
- real raw-data tests for the two focus deals included with full frozen filings
- end-to-end synthetic stage tests for QA, enrichment, export, and validation

## 15. Known Limits

The following are intentionally left for a future revision:

- direct workbook truth alignment against Alex's corrected spreadsheet
- provider-agnostic multi-model audit beyond the backend abstraction
- richer human review UI beyond JSON overrides and QA flags
- analytic parquet / SQLite fact-table exports beyond current CSV + canonical JSON outputs

## 16. Implementation Map

The current v3 implementation lives in:

- raw: `pipeline/raw/*`
- preprocess/source: `pipeline/preprocess/source.py`, `pipeline/source/*`
- LLM backend + prompts: `pipeline/llm/*`
- extraction orchestration: `pipeline/extract/*`
- normalization: `pipeline/normalize/*`
- QA: `pipeline/qa/*`
- enrichment: `pipeline/enrich/*`
- export: `pipeline/export/*`
- validation: `pipeline/validate/*`
- orchestration / CLI / state: `pipeline/orchestrator.py`, `pipeline/cli.py`, `pipeline/state.py`

## 17. Summary of v3 Changes Relative to v2

- preprocess now scans **all filings** and emits `evidence_items.jsonl`
- supplementary snippets are derived from evidence items, not filing-type heuristics alone
- chronology confidence separates ambiguity risk from coverage adequacy
- extraction prompts now accept cross-filing evidence ids in addition to chronology block ids
- extraction orchestration is implemented end to end
- reconciliation / QA is implemented end to end
- enrichment is implemented end to end
- export is implemented end to end
- reference validation summary is implemented
- CLI and orchestrator now wire the full deterministic pipeline

