# M&A Deal Extraction Pipeline -- Design v2

| Field  | Value |
|--------|-------|
| Date   | 2026-03-16 |
| Status | Adopted (from GPT Pro Round 1 review) |
| Scope  | Same as v1: reproducible, auditable pipeline converting SEC merger-background narratives into structured, reviewable event chronologies for takeover-auction research |
| Replaces | `2026-03-16-pipeline-design.md` (4-stage pipeline) |


## Context

### v1 design

The v1 design proposed a four-stage linear pipeline: source discovery and freeze, LLM extraction (two Anthropic calls for actors and events), deterministic enrichment (formal/informal classification, cycle segmentation), and CSV export. The core research principle was correct -- filing text as the evidentiary source, formal/informal classification as deterministic logic -- but the architecture was too compressed for research-grade extraction.

### Critical findings motivating redesign

The following findings from external review are the primary drivers for replacing the v1 design:

1. **There is no reconciliation/QA stage.** The v1 design explicitly deferred this. That omission is fatal for this project. In this domain, the model should not be trusted to emit final verbatim quotes, canonical actors, or final dates. Those need deterministic repair and verification before enrichment.

2. **The current schemas cannot represent required domain facts.** The v1 schema has one `Actor` model and one generic `Event` model. That is too weak for Alex's rules. Alex requires bidder type combinations such as "non-US public S", legal advisors collected even without date events, range bids preserving both bounds, and partial-company bids excluded. The v1 schema cannot encode several of those distinctions cleanly.

3. **The current filing-selection logic is too loose for a research pipeline.** The v1 source stage searches by form and picks one filing per form based on nearest filing date, then chooses the "best" primary filing by chronology score, seed bonus, and form preference. There is no explicit date window, no top-k review, and no audit of near misses. This already produces stale supplementary noise: Zep's supplementary manifest includes an SC 13D from 2007 for a 2015 deal.

4. **The current Stage 2 gate is far too weak.** "At least 1 actor and 1 event extracted" is not a meaningful quality gate for a merger-background chronology.

5. **The four-stage linear topology is too coarse.** Source localization, extraction, deterministic repair, enrichment, and export are distinct concerns. Merging them into four broad stages hides the stage boundaries that matter most: source adjudication and post-extraction reconciliation.

6. **CSV is being treated as the internal model too early.** The v1 design goes straight to a 19-column CSV and treats 47 columns as a later expansion. That is backwards. The internal model should be richer than any export.

7. **Source provenance is too weak.** The v1 event and actor models store only `source_quote` as free text. That is not enough. Provenance needs line spans, block IDs, accession, form type, and quote-resolution status.


## Goals

Build a reproducible, auditable pipeline that converts SEC merger-background narratives into structured, reviewable event chronologies for takeover-auction research.

The system must:

- preserve filing text as the only factual source;
- separate extraction from judgment;
- preserve exact provenance at span level;
- support grouped and unnamed entities;
- handle multi-cycle processes;
- validate against the 9 reference deals before any corpus-scale run;
- produce richer internal artifacts than any downstream CSV export.

### Non-goals

The first production version does **not** need to include:

- Compustat linkage,
- estimation-ready binary indicators,
- cross-vendor ensemble extraction,
- full GUI review tooling,
- database-backed multi-user workflows.

It **does** need a lightweight human-review override path.


## Design Principles

1. **Filing text is the only factual source.**
   Alex's instructions define extraction targets, not facts about any deal.

2. **LLM outputs are provisional until reconciled.**
   The model proposes structured facts and evidence references; Python resolves quotes, validates spans, normalizes dates, and applies deterministic rules.

3. **Store spans, not just quotes.**
   Final quotes are reconstructed from line/block spans. The model does not own the verbatim evidence string.

4. **Internal model is wider than export.**
   CSVs are exports, not canonical storage.

5. **Reviewability is a first-class feature.**
   Every low-confidence source selection, unresolved actor, quote mismatch, and inferred cycle boundary becomes an explicit review item.

6. **Provider abstraction is thin.**
   Abstract only what is necessary to support another model later.


## Topology

The right topology is a **6-stage per-deal DAG with one feedback loop**, exposed as composable CLI commands and orchestrated by a run manager.

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

This is logically a DAG because source localization and supplementary indexing branch, and extraction can feed a targeted recovery pass. It should **not** be implemented as a task queue. For ~400 deals, a library-plus-CLI with optional process-pool concurrency is sufficient.


## Runtime Model

Use:

- **filesystem artifacts** for immutable source and per-deal JSON/JSONL artifacts;
- **SQLite** for run state, stage attempts, artifact registry, costs, and review queue.

Do **not** use `status.json` as the primary state store. You may generate it as a derived summary for quick inspection.


## Orchestration Boundary

### Orchestrator responsibilities

- choose deals/stages to run;
- enforce prerequisites;
- manage retries and resume;
- record attempts, artifacts, usage, and errors;
- apply review overrides;
- support `--strict` vs `--exploratory` modes.

### Stage logic responsibilities

- pure stage-specific transformation;
- no global status mutation;
- no cross-stage directory creation;
- no silent retries;
- return structured results plus diagnostics.


## Modes

Define two modes:

### Strict mode

- used for the 9 reference deals and any sign-off run;
- low-confidence source selection blocks progression;
- unresolved quote or actor reference blocks export;
- inferred cycle boundaries require review.

### Exploratory mode

- used for wider corpus development runs;
- low-confidence source selection is allowed to proceed with flags;
- flagged deals are excluded from the "clean" export unless explicitly included.


## Directory Structure

```
repo/
  pipeline/
    cli.py
    orchestrator.py
    state.py
    logging_utils.py
    config.py
    models/
      common.py
      source.py
      extraction.py
      qa.py
      enrichment.py
      export.py
    source/
      discovery.py
      ranking.py
      locate.py
      blocks.py
      supplementary.py
    llm/
      backend.py
      anthropic_backend.py
      prompts.py
      token_budget.py
      schemas.py
    extract/
      actors.py
      events.py
      recovery.py
      merge.py
    normalize/
      spans.py
      quotes.py
      dates.py
      entities.py
    qa/
      rules.py
      completeness.py
      review.py
    enrich/
      classify.py
      cycles.py
      features.py
    export/
      flatten.py
      review_csv.py
      alex_compat.py
      parquet.py
    validate/
      reference.py
      metrics.py
      alignment.py
  data/
    seeds.csv
    deals/
      <slug>/
        source/
        extract/
        qa/
        enrich/
        export/
        review/
    runs/
      pipeline_state.sqlite
      logs/
```


## Stage Specifications

### Stage 1: Source Discovery & Freeze

**Inputs:**

- `SeedDeal`

**Outputs:**

- `FilingDiscoveryReport`
- frozen `html`, `txt`, optional `md`
- `document_registry.json`

**Responsibilities:**

- resolve issuer identity from seed URL/accession first, then CIK, then name search;
- search primary forms and supplementary forms with an explicit date window around announcement date;
- retain top-k candidates, not just one per form, for adjudication;
- freeze raw artifacts and compute hashes;
- record fetch metadata.

**Primary filing preference:**

1. seed URL accession if valid and chronology-bearing;
2. definitive target-side filing over preliminary when both have adequate chronology;
3. target-side merger background form over bidder-side or transaction mechanics form;
4. chronology quality score;
5. date proximity.

**Recommended default date window:**

- announcement date +/- 365 days for primary forms;
- announcement date +/- 180 days for supplementary forms;
- if seed URL accession exists, always include it even outside the window.

**Fallbacks:**

- direct accession fetch from seed URL;
- direct SEC document fetch when EdgarTools search fails;
- manual `filing_override.yaml` for edge cases.

**Artifacts:**

- `source/discovery.json`
- `source/document_registry.json`
- `source/filings/<doc_id>.html`
- `source/filings/<doc_id>.txt`
- `source/filings/<doc_id>.md` (optional)
- `source/candidates.json`


### Stage 2: Chronology Localization & Blocking

**Inputs:**

- frozen primary filing text/html/md
- ranked candidate metadata

**Outputs:**

- `ChronologySelection`
- `ChronologyCandidate[]`
- `ChronologyBlock[]`
- `SupplementarySnippet[]`
- source review items

**Responsibilities:**

- generate candidate chronology sections from:
  - heading regex on plain text,
  - parsed section titles if available,
  - markdown headings if available,
  - keyword search around "background of the merger/offer/transaction".
- score candidates deterministically;
- compare candidate disagreement across representations;
- create cleaned paragraph blocks with preserved raw line spans;
- index supplementary snippets by keyword for downstream optional use.

**Confidence policy:**

- **high**: deterministic winner, strong section quality, no close competitor.
- **medium**: plausible winner, but short section or close competitor.
- **low**: weak or ambiguous winner.
- **none**: no acceptable chronology.

**Control flow:**

- high: proceed
- medium: proceed + review flag
- low: strict mode blocks; exploratory mode proceeds + blocker flag
- none: source-stage failure

Crucial rule: **the authoritative evidence remains raw text line spans, not normalized block text.** Blocks are for extraction ergonomics.

**Artifacts:**

- `source/chronology_selection.json`
- `source/chronology_candidates.json`
- `source/chronology_blocks.jsonl`
- `source/supplementary_snippets.jsonl`
- `review/source_review.md`


### Stage 3: Extraction

**Inputs:**

- `ChronologyBlock[]`
- optional `SupplementarySnippet[]`
- prior actor register for event extraction

**Outputs:**

- `ActorExtractionBundle`
- `EventExtractionBundle`
- optional `RecoveryExtractionBundle`
- `llm_calls.jsonl`

**Substages:**

**3A. Actor register extraction**

- full chronology, all blocks
- identify actors, aliases, grouped entities, count assertions, unresolved mentions

**3B. Event extraction**

Adaptive routing:

- simple deals: one full-chronology event pass
- complex deals: chunked extraction with overlap and later deterministic merge

Complexity thresholds:

- simple: <= 8k prompt-counted chronology tokens or <= 150 raw chronology lines
- moderate: 8k-15k tokens or 151-400 lines
- complex: > 15k tokens or > 400 lines or expected actor count > 15

Use official token counting before request routing.

**3C. Targeted recovery**

Triggered when QA heuristics detect likely missing categories, such as:

- proposal-like dollar mentions without proposal events,
- final-round language without round events,
- count assertions implying more NDAs than extracted actors explain,
- no executed/terminated outcome in a complete process.

The model should return **evidence refs**, not final quotes:

- `block_id`
- `anchor_text`
- optional line hint

**Artifacts:**

- `extract/actors_raw.json`
- `extract/events_raw.json`
- `extract/recovery_raw.json` (optional)
- `extract/usage.jsonl`


### Stage 4: Reconciliation & QA

**Inputs:**

- raw actor/event bundles
- chronology blocks
- source documents

**Outputs:**

- canonical `DealExtraction`
- `SpanRegistry`
- `QAReport`
- review items

**Responsibilities:**

- resolve evidence refs to exact spans;
- reconstruct authoritative quotes from raw text;
- validate quote matching;
- deduplicate actors and events;
- resolve actor references in events;
- normalize dates and preserve raw dates;
- build event ordering;
- enforce invariants;
- compute completeness diagnostics;
- generate review flags.

This stage is the heart of the redesigned pipeline.

**Blockers:**

- unresolved actor ref on an exported event
- unresolved quote span
- averaged range bid
- partial-company proposal not excluded
- chronology missing for exported deal
- invalid cycle chronology order

**Artifacts:**

- `qa/span_registry.jsonl`
- `qa/extraction_canonical.json`
- `qa/report.json`
- `review/overrides.template.yaml`


### Stage 5: Enrichment

**Inputs:**

- canonical `DealExtraction`

**Outputs:**

- `DealEnrichment`
- `CycleRecord[]`
- `DerivedMetrics`

**Responsibilities:**

- formal/informal classification
- cycle segmentation
- phase/round labeling
- sequence numbering
- per-cycle and per-deal metrics

This stage is deterministic and versioned.

**Artifacts:**

- `enrich/deal_enrichment.json`


### Stage 6: Export & Validation

**Inputs:**

- `DealExtraction`
- `DealEnrichment`
- review overrides
- reference comparison config

**Outputs:**

- human review CSV
- analytics parquet / SQLite tables
- Alex-compat export
- validation metrics

**Artifacts:**

- `export/events_long.csv`
- `export/events.parquet`
- `export/actors.parquet`
- `export/deal_summary.csv`
- `export/alex_compat.csv` (provisional until workbook is available)
- `validate/reference_metrics.json`
- `validate/reference_diff.md`


## Canonical Schema Definitions

A tagged schema family, not 23 tiny bespoke classes and not one monolithic `Event`.

### Common Enums

```python
class ActorRole(StrEnum):
    BIDDER = "bidder"
    ADVISOR = "advisor"
    ACTIVIST = "activist"
    TARGET_BOARD = "target_board"

class AdvisorKind(StrEnum):
    FINANCIAL = "financial"
    LEGAL = "legal"
    OTHER = "other"
    UNKNOWN = "unknown"

class BidderKind(StrEnum):
    STRATEGIC = "strategic"
    FINANCIAL = "financial"
    UNKNOWN = "unknown"

class ListingStatus(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"
    UNKNOWN = "unknown"

class GeographyFlag(StrEnum):
    DOMESTIC = "domestic"
    NON_US = "non_us"
    UNKNOWN = "unknown"

class DatePrecision(StrEnum):
    EXACT_DAY = "exact_day"
    MONTH = "month"
    MONTH_EARLY = "month_early"
    MONTH_MID = "month_mid"
    MONTH_LATE = "month_late"
    QUARTER = "quarter"
    YEAR = "year"
    RANGE = "range"
    RELATIVE = "relative"
    UNKNOWN = "unknown"

class ConsiderationType(StrEnum):
    CASH = "cash"
    STOCK = "stock"
    MIXED = "mixed"
    OTHER = "other"
    UNKNOWN = "unknown"

class EventType(StrEnum):
    TARGET_SALE = "target_sale"
    TARGET_SALE_PUBLIC = "target_sale_public"
    BIDDER_SALE = "bidder_sale"
    BIDDER_INTEREST = "bidder_interest"
    ACTIVIST_SALE = "activist_sale"
    SALE_PRESS_RELEASE = "sale_press_release"
    BID_PRESS_RELEASE = "bid_press_release"
    IB_RETENTION = "ib_retention"
    NDA = "nda"
    PROPOSAL = "proposal"
    DROP = "drop"
    DROP_BELOW_M = "drop_below_m"
    DROP_BELOW_INF = "drop_below_inf"
    DROP_AT_INF = "drop_at_inf"
    DROP_TARGET = "drop_target"
    FINAL_ROUND_INF_ANN = "final_round_inf_ann"
    FINAL_ROUND_INF = "final_round_inf"
    FINAL_ROUND_ANN = "final_round_ann"
    FINAL_ROUND = "final_round"
    FINAL_ROUND_EXT_ANN = "final_round_ext_ann"
    FINAL_ROUND_EXT = "final_round_ext"
    EXECUTED = "executed"
    TERMINATED = "terminated"
    RESTARTED = "restarted"

class ClassificationLabel(StrEnum):
    FORMAL = "formal"
    INFORMAL = "informal"
    UNCERTAIN = "uncertain"
    NOT_APPLICABLE = "not_applicable"

class QuoteMatchType(StrEnum):
    EXACT = "exact"
    NORMALIZED = "normalized"
    FUZZY = "fuzzy"
    UNRESOLVED = "unresolved"

class ReviewSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    BLOCKER = "blocker"
```

### Artifact Envelope

Every JSON root artifact should include:

```python
class ArtifactEnvelope(BaseModel):
    schema_version: str
    artifact_type: str
    created_at: datetime
    pipeline_version: str
    run_id: str
    deal_slug: str | None = None
```

### Seed and Source Models

```python
class SeedDeal(ArtifactEnvelope):
    deal_slug: str
    target_name: str
    acquirer_seed: str | None
    date_announced_seed: date | None
    primary_url_seed: str | None
    is_reference: bool
    seed_row_refs: list[str]            # workbook row ids if available later
    notes: list[str] = []

class FilingCandidate(BaseModel):
    document_id: str                    # stable internal id
    accession_number: str | None
    filing_type: str
    filing_date: date | None
    sec_url: str | None
    source_origin: Literal["seed_accession","edgartools_search","manual_override"]
    ranking_features: dict[str, Any]    # seed match, date distance, form preference, etc.
    selected_for_localization: bool = False
    rejected_reason: str | None = None

class FrozenDocument(BaseModel):
    document_id: str
    accession_number: str | None
    filing_type: str
    filing_date: date | None
    html_path: str | None
    txt_path: str
    md_path: str | None
    sha256_txt: str
    sha256_html: str | None
    byte_count_txt: int
    fetched_at: datetime

class FilingDiscoveryReport(ArtifactEnvelope):
    seed: SeedDeal
    cik: str | None
    primary_candidates: list[FilingCandidate]
    supplementary_candidates: list[FilingCandidate]
    frozen_documents: list[FrozenDocument]
```

### Chronology Models

```python
class ChronologyCandidate(BaseModel):
    document_id: str
    heading_text: str
    heading_normalized: str
    start_line: int
    end_line: int
    score: int
    source_methods: list[Literal["txt_heading","txt_search","html_heading","markdown_heading","sections_api"]]
    is_standalone_background: bool
    diagnostics: dict[str, Any]

class ChronologySelection(ArtifactEnvelope):
    document_id: str
    accession_number: str | None
    filing_type: str
    selected_candidate: ChronologyCandidate | None
    confidence: Literal["high","medium","low","none"]
    adjudication_basis: str
    alternative_candidates: list[ChronologyCandidate]
    review_required: bool

class ChronologyBlock(BaseModel):
    block_id: str
    document_id: str
    ordinal: int
    start_line: int
    end_line: int
    raw_text: str
    clean_text: str
    is_heading: bool
    page_break_before: bool = False
    page_break_after: bool = False

class SupplementarySnippet(BaseModel):
    snippet_id: str
    document_id: str
    filing_type: str
    event_hint: Literal["sale_press_release","bid_press_release","activist_sale","other"]
    start_line: int
    end_line: int
    raw_text: str
    keyword_hits: list[str]
    confidence: Literal["high","medium","low"]
```

### Provenance and Normalization Models

```python
class SourceSpan(BaseModel):
    span_id: str
    document_id: str
    accession_number: str | None
    filing_type: str
    start_line: int
    end_line: int
    start_char: int | None = None
    end_char: int | None = None
    block_ids: list[str]
    anchor_text: str | None
    quote_text: str                     # authoritative quote reconstructed from raw text
    quote_text_normalized: str
    match_type: QuoteMatchType
    resolution_note: str | None = None

class DateValue(BaseModel):
    raw_text: str
    normalized_start: date | None
    normalized_end: date | None
    sort_date: date | None
    precision: DatePrecision
    anchor_event_id: str | None = None
    resolution_note: str | None = None
    is_inferred: bool = False

class MoneyTerms(BaseModel):
    raw_text: str | None
    currency: str = "USD"
    value_per_share: Decimal | None = None
    lower_per_share: Decimal | None = None
    upper_per_share: Decimal | None = None
    total_enterprise_value: Decimal | None = None
    is_range: bool
```

### Actor Models

```python
class ActorRecord(BaseModel):
    actor_id: str
    display_name: str
    canonical_name: str
    aliases: list[str]
    role: ActorRole
    advisor_kind: AdvisorKind | None = None
    bidder_kind: BidderKind | None = None
    listing_status: ListingStatus | None = None
    geography: GeographyFlag | None = None
    is_grouped: bool
    group_size: int | None = None
    group_label: str | None = None
    parent_group_actor_id: str | None = None
    first_mention_span_ids: list[str]
    notes: list[str] = []

class CountAssertion(BaseModel):
    assertion_id: str
    count: int
    subject: Literal[
        "interested_parties",
        "nda_signed_bidders",
        "nda_signed_financial_buyers",
        "nda_signed_strategic_buyers",
        "final_round_invitees",
        "other"
    ]
    qualifier_text: str | None = None
    date: DateValue | None = None
    span_ids: list[str]
```

### Event Family Models

```python
class EventBase(BaseModel):
    event_id: str
    event_type: EventType
    date: DateValue
    actor_ids: list[str]
    primary_span_ids: list[str]
    secondary_span_ids: list[str] = []
    summary: str
    notes: list[str] = []

class ProcessMarkerEvent(EventBase):
    event_type: Literal[
        EventType.TARGET_SALE,
        EventType.TARGET_SALE_PUBLIC,
        EventType.BIDDER_SALE,
        EventType.BIDDER_INTEREST,
        EventType.ACTIVIST_SALE,
        EventType.SALE_PRESS_RELEASE,
        EventType.BID_PRESS_RELEASE,
        EventType.IB_RETENTION,
    ]

class NDAEvent(EventBase):
    event_type: Literal[EventType.NDA]
    nda_signed: bool = True

class FormalitySignals(BaseModel):
    contains_range: bool = False
    mentions_indication_of_interest: bool = False
    mentions_preliminary: bool = False
    mentions_non_binding: bool = False
    mentions_binding_offer: bool = False
    includes_draft_merger_agreement: bool = False
    includes_marked_up_agreement: bool = False
    requested_binding_offer_via_process_letter: bool = False
    after_final_round_announcement: bool = False
    after_final_round_deadline: bool = False
    signal_span_ids: list[str] = []

class ProposalEvent(EventBase):
    event_type: Literal[EventType.PROPOSAL]
    terms: MoneyTerms
    consideration_type: ConsiderationType
    whole_company_scope: bool | None
    whole_company_scope_note: str | None = None
    formality_signals: FormalitySignals

class DropEvent(EventBase):
    event_type: Literal[
        EventType.DROP,
        EventType.DROP_BELOW_M,
        EventType.DROP_BELOW_INF,
        EventType.DROP_AT_INF,
        EventType.DROP_TARGET,
    ]
    drop_reason_text: str | None = None

class RoundEvent(EventBase):
    event_type: Literal[
        EventType.FINAL_ROUND_INF_ANN,
        EventType.FINAL_ROUND_INF,
        EventType.FINAL_ROUND_ANN,
        EventType.FINAL_ROUND,
        EventType.FINAL_ROUND_EXT_ANN,
        EventType.FINAL_ROUND_EXT,
    ]
    round_scope: Literal["informal","formal","extension"]
    deadline_date: DateValue | None = None

class OutcomeEvent(EventBase):
    event_type: Literal[EventType.EXECUTED]
    executed_with_actor_id: str | None

class CycleBoundaryEvent(EventBase):
    event_type: Literal[EventType.TERMINATED, EventType.RESTARTED]
    boundary_note: str | None = None

EventUnion = Annotated[
    ProcessMarkerEvent | NDAEvent | ProposalEvent | DropEvent | RoundEvent | OutcomeEvent | CycleBoundaryEvent,
    Field(discriminator="event_type")
]
```

### Extraction, QA, Enrichment, Export Models

```python
class ExtractionExclusion(BaseModel):
    exclusion_id: str
    category: Literal[
        "partial_company_bid",
        "unsigned_nda",
        "stale_process_reference",
        "duplicate_mention",
        "non_event_context",
        "other"
    ]
    block_ids: list[str]
    explanation: str

class DealExtraction(ArtifactEnvelope):
    seed: SeedDeal
    source_selection: ChronologySelection
    actors: list[ActorRecord]
    count_assertions: list[CountAssertion]
    spans: list[SourceSpan]
    events: list[EventUnion]
    exclusions: list[ExtractionExclusion]
    unresolved_mentions: list[str]
    extraction_notes: list[str]

class QAFinding(BaseModel):
    finding_id: str
    severity: ReviewSeverity
    code: str
    message: str
    related_actor_ids: list[str] = []
    related_event_ids: list[str] = []
    related_span_ids: list[str] = []
    auto_fix_applied: bool = False
    review_required: bool = False

class QAReport(ArtifactEnvelope):
    blocker_count: int
    warning_count: int
    findings: list[QAFinding]
    completeness_metrics: dict[str, Any]
    passes_export_gate: bool

class ProposalClassification(BaseModel):
    label: ClassificationLabel
    rule_id: str | None
    rule_version: str
    note: str | None = None

class CycleRecord(BaseModel):
    cycle_id: str
    start_event_id: str
    end_event_id: str | None
    boundary_basis: Literal[
        "single_cycle",
        "explicit_terminated_restarted",
        "implicit_reinitiation_after_gap",
        "manual_override"
    ]
    historical_context_only: bool = False
    review_required: bool = False

class DerivedMetrics(BaseModel):
    unique_bidders_total: int
    unique_bidders_named: int
    unique_bidders_grouped: int
    peak_active_bidders: int | None
    proposal_count_total: int
    proposal_count_formal: int
    proposal_count_informal: int
    nda_count: int
    duration_days: int | None
    cycle_count: int

class DealEnrichment(ArtifactEnvelope):
    classifications: dict[str, ProposalClassification]     # event_id -> classification
    cycles: list[CycleRecord]
    event_sequence: dict[str, int]                         # event_id -> stable order
    event_cycle_map: dict[str, str]                        # event_id -> cycle_id
    formal_boundary_event_ids: dict[str, str | None]      # cycle_id -> event_id
    derived_metrics: DerivedMetrics

class ReviewRow(BaseModel):
    deal_slug: str
    target_name: str
    event_sequence: int
    cycle_id: str | None
    event_id: str
    event_type: str
    actor_id: str | None
    actor_name: str | None
    actor_role: str | None
    bidder_kind: str | None
    listing_status: str | None
    geography: str | None
    raw_date: str
    sort_date: date | None
    value_per_share: Decimal | None
    lower_per_share: Decimal | None
    upper_per_share: Decimal | None
    consideration_type: str | None
    proposal_classification: str | None
    classification_rule: str | None
    accession_number: str | None
    filing_type: str | None
    source_lines: str
    source_quote_full: str
    qa_flags: list[str]
```


## Event Taxonomy Definitions

Some subtype semantics are **certain** from Alex's collection instructions, and some are **inferred** because the more detailed taxonomy file referenced in the implementation plan is excluded from the review package.

### Certain (from collection instructions)

- `final_round_inf_ann`, `final_round_inf`, `final_round_ann`, `final_round`, `final_round_ext_ann`, `final_round_ext` are directly supported by Alex's instructions.
- `executed`, `terminated`, `restarted` are directly supported.

### Inferred but necessary for implementation

- `drop_below_m`: bidder withdraws because its bid is below the target's required level / management threshold / indicated minimum.
- `drop_below_inf`: same pattern, but in an explicitly informal-round context.
- `drop_at_inf`: dropout occurring at the informal final-round stage where neither target elimination nor below-threshold rationale is clearly stated.
- Rule: if the filing does not clearly support a subtype, emit generic `drop`.

That removes ambiguity for implementation while preserving a conservative fallback.


## Source Stage Design Decisions

### EDGAR client

Keep EdgarTools as the primary client. It is feature-capable enough because it already exposes text, markdown, search, section listing, parsing, and save/load capabilities. The missing robustness should be supplied by the pipeline's own caching, date-windowing, and fallback fetch strategy, not by swapping clients prematurely.

### Chronology locator

Keep deterministic localization as the default, but make it hybrid:

1. candidate generation from parsed/section/markdown/html/text representations;
2. deterministic scoring on content quality;
3. optional LLM adjudication only for low-confidence or split-decision cases.

Do **not** make the locator LLM-first. Source localization is infrastructure, not interpretation.

### Low-confidence handling

- PetSmart-like short sections should not automatically fail just because they are short.
- Low confidence means "needs review," not "wrong."
- In strict mode, low confidence blocks export.
- In exploratory mode, low confidence proceeds with a blocker flag.

### Supplementary filings

Supplementary filings should be indexed, not ignored.

Use them for:

- `sale_press_release`
- `bid_press_release`
- `activist_sale`
- public-announcement corroboration
- early bidder outreach omitted from the main chronology

Do **not** automatically interleave supplementary snippets into the main chronology. Use them as secondary evidence with their own spans and document IDs.


## Extraction Design Decisions

### Number of passes

The right answer is **adaptive**, not always two and not always one.

- Actor pass is always separate.
- Event pass is one full pass for simple deals.
- Event pass is chunked for complex deals.
- Recovery pass is conditional.
- There is also a schema-repair pass only on validation failure.

This is more complex than the v1 two-call plan, but it is justified by the variance from PetSmart to STEC.

### Structured output strategy

Use provider-neutral JSON schemas, implemented through Anthropic structured outputs with `output_config.format`. For this pipeline, direct schema-conforming JSON is simpler and easier to keep provider-neutral than strict tool use for validated tool inputs.

### Prompt caching

Use prompt caching in two places:

1. the stable system prompt + taxonomy + schema instructions, reused across all deals;
2. the chronology block payload reused across actor and event calls on the same deal when using a full-chronology route.

Anthropic's prompt-caching minimum is 1024 tokens for Sonnet 4.5 and 2048 for Sonnet 4.6, and usage accounting is exposed via `input_tokens`, `cache_creation_input_tokens`, and `cache_read_input_tokens`. The included chronologies are well above those thresholds.

### Date normalization

Use both model hints and deterministic normalization.

- Model extracts `raw_text`, optional normalized hints, and contextual relation.
- Python validates and resolves:
  - exact dates,
  - month-only dates,
  - early/mid/late-month dates,
  - quarter references,
  - relative dates when anchored to a previous explicit event.

The final authoritative normalized date lives in `DateValue`, not in raw model JSON.


## Enrichment Rule Specifications

### Formal/Informal Classification

This should produce `formal`, `informal`, or `uncertain`.

Rule order:

**F0. Not applicable**
If event type is not `proposal`, label `not_applicable`.

**I1. Range bids are informal**
If `terms.is_range == True`, classify `informal`.
Rationale: Alex explicitly says any range bid is informal.

**I2. Explicit informal language**
If signals include `mentions_indication_of_interest`, `mentions_preliminary`, or `mentions_non_binding`, classify `informal`.

**F1. Explicit binding package**
If signals include `includes_draft_merger_agreement`, `includes_marked_up_agreement`, or `mentions_binding_offer`, classify `formal`.

**F2. Formal-round process letter**
If a prior `final_round_ann` or `final_round_ext_ann` requested final binding bids or markup of merger agreement, and proposal occurs after that event in same cycle, classify `formal`.

**F3. Final-round deadline context**
If proposal is submitted after `final_round` deadline announcement and the round is clearly a binding round, classify `formal`.

**I3. Informal final round**
If proposal is tied to `final_round_inf_ann` / `final_round_inf`, classify `informal`.

**U1. Uncertain residual**
Otherwise classify `uncertain`, not default informal.

Outputs per proposal:

- label
- fired rule id
- supporting event/span ids
- rule version

Manual override allowed via review patch.

### Cycle Segmentation

Rules:

1. Start with chronological ordering.
2. Explicit `terminated` closes a cycle.
3. Explicit `restarted` opens the next cycle.
4. If there is a `terminated` but no explicit `restarted`, infer a new cycle when a later initiation cluster appears:
   - `target_sale`, `bidder_sale`, `bidder_interest`, `activist_sale`, or `ib_retention`,
   - plus a material gap (default 30+ days),
   - or a fresh NDA wave.
5. If no explicit termination exists, infer a new cycle only when:
   - gap >= 180 days,
   - and there is a clear re-initiation cluster,
   - and actors or advisors materially reset.
6. All inferred boundaries require review.

Store:

- `cycle_id`
- `boundary_basis`
- `historical_context_only`
- `review_required`

### Formal Boundary

Determine per cycle, not per deal.

For each cycle:

- formal boundary = earliest proposal classified `formal`
- if none, boundary null
- if multiple formal rounds/extensions exist, keep:
  - first formal proposal event id
  - round events separately
  - extension events separately

### Derived Metrics

Produce at least:

- unique named bidders
- unique grouped bidders
- NDA count
- proposal count total
- formal proposal count
- informal proposal count
- peak active bidders
- cycle count
- duration from first process event to executed/terminated
- winning bidder actor id if identifiable
- whether sale was bidder-initiated / target-initiated / activist-initiated


## Output Specifications

### Internal storage

Canonical internal representation should be:

- per-deal JSON artifacts for source/extract/qa/enrich;
- SQLite state store for run metadata;
- Parquet or SQLite export tables for analysis.

Do **not** make CSV the internal system of record.

### Export surfaces

**A. `events_long.csv`**
One row per actor-event pair. This is the human-review format.

**B. `events.parquet` / SQLite tables**
Canonical analytics export:

- `deals`
- `actors`
- `events`
- `event_actor_links`
- `spans`
- `classifications`
- `cycles`
- `qa_findings`

**C. `alex_compat.csv`**
Workbook adapter. Provisional until the excluded workbook is available.

### Multi-actor events

Canonical model:

- one event
- many actor links

CSV review export:

- one row per actor-event pair
- if event has no actor, actor columns blank
- if event has many actors, duplicate event columns across rows

This is superior to comma-separated actor columns.

### `bid_note` mapping

Internal rule:

- keep `event_type` as the canonical field
- keep `proposal_classification` separate
- keep `export_bid_note` as an adapter-layer field

Do **not** make `proposal` map to blank internally.

For `alex_compat.csv`, allow configurable mappings:

- if Alex workbook truly expects blank bid_note for proposals, exporter can do that;
- otherwise exporter can emit `Formal Bid` / `Informal Bid`.

### Wide export design

Design for the future 47-column format now by making internal exports a superset. Because the workbook is excluded, exact final column names are provisional, but the exporter should already carry fields for:

- seed metadata
- event sequence
- cycle
- actor role and bidder dimensions
- bid values and ranges
- classification
- source accession/form
- source line spans
- full quote
- QA flags
- review notes


## Error Handling and Observability

### Logging

Use two channels:

1. human-readable console logs
2. JSONL structured logs per run and per deal

Each log entry should include:

- timestamp
- run_id
- deal_slug
- stage
- attempt_no
- severity
- message
- structured payload

### SQLite state tables

```sql
runs(
  run_id TEXT PRIMARY KEY,
  started_at TEXT,
  finished_at TEXT,
  code_version TEXT,
  config_hash TEXT,
  mode TEXT
);

stage_attempts(
  run_id TEXT,
  deal_slug TEXT,
  stage_name TEXT,
  attempt_no INTEGER,
  status TEXT,
  started_at TEXT,
  finished_at TEXT,
  duration_ms INTEGER,
  error_code TEXT,
  error_message TEXT,
  review_required INTEGER,
  PRIMARY KEY(run_id, deal_slug, stage_name, attempt_no)
);

artifacts(
  run_id TEXT,
  deal_slug TEXT,
  artifact_type TEXT,
  path TEXT,
  sha256 TEXT,
  schema_version TEXT,
  created_at TEXT
);

llm_calls(
  call_id TEXT PRIMARY KEY,
  run_id TEXT,
  deal_slug TEXT,
  unit_name TEXT,
  provider TEXT,
  model TEXT,
  prompt_version TEXT,
  request_id TEXT,
  input_tokens INTEGER,
  cache_creation_input_tokens INTEGER,
  cache_read_input_tokens INTEGER,
  output_tokens INTEGER,
  cost_usd REAL,
  latency_ms INTEGER,
  status TEXT
);

review_items(
  review_id TEXT PRIMARY KEY,
  deal_slug TEXT,
  stage_name TEXT,
  severity TEXT,
  code TEXT,
  message TEXT,
  artifact_path TEXT,
  status TEXT,
  resolved_at TEXT
);
```

### Partial failures

Default behavior:

- keep completed deals completed
- continue batch on single-deal failure
- mark failed stage for that deal
- downstream stages for that deal do not run
- `--fail-fast` available for debugging only

### Retry policy

- network / 429 / transient 5xx: 3 retries with backoff
- schema validation failure: 1 repair pass
- low-confidence source: no automatic blind retry; escalate to review
- quote mismatch: deterministic repair first, then review


## Cost Model

Use official API usage fields, not hand estimates.

Per call:

```
cost_usd =
    input_tokens * uncached_input_rate +
    cache_creation_input_tokens * cache_write_rate +
    cache_read_input_tokens * cache_read_rate +
    output_tokens * output_rate
```

For Sonnet 4.5, official pricing is $3/MTok input, $3.75/MTok 5-minute cache write, $0.30/MTok cache read, and $15/MTok output; batch processing halves input and output costs. Sonnet 4.6 carries the same base input/output rates.

Practical estimate from the included reference filings:

- simple deal, actor + event pass: roughly $0.08-0.14
- complex deal with chunking/recovery: roughly $0.14-0.25
- 400 deals after prompt stabilization: roughly $40-$80 synchronous, or ~$20-$40 in batch mode

That estimate is based on the included chronology sizes plus official pricing, so treat it as a planning range rather than a guaranteed invoice.


## What This Design Does Not Include (Deferred)

### Deferred until after reference sign-off

- **Message Batches API for corpus runs.** Useful because of the 50% cost discount, but harder to debug. Use synchronous calls first.
- **Cross-vendor audit.** Add once canonical artifacts and metrics exist.
- **Compustat linkage and estimation indicators.** These are downstream transforms, not extraction-core requirements.
- **Open-world `actors_extended.jsonl` minting.** Not needed until actor normalization is stable.

### Cut from current design

- `status.json` as primary tracker
- 19-column CSV as the primary internal target
- unconditional two-call extraction
- direct `source_quote` authority from the model
- default-informal fallback classification


## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| Python | >= 3.11 | Runtime (StrEnum, `X \| Y` union syntax) |
| pydantic | >= 2.0 | Schema models, discriminated unions, validation |
| anthropic | latest | LLM backend (structured outputs, prompt caching, token counting) |
| edgartools | latest | EDGAR search, filing fetch, section/markdown/text access |
| openpyxl | latest | Seed workbook intake |
| pytest | latest | Test framework |
| pyarrow | latest | Parquet export |
| sqlite3 | stdlib | Run state, analytics export tables |
