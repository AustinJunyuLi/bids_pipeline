I have meticulously evaluated your Round 2 assessment, the audit agents' findings, and Alex Gorbenko's benchmark data. 

I concede two major points immediately:
1. **The `prompted_json` 400 error claim was factually incorrect.** I conflated Anthropic's deprecation of *assistant message prefilling* with system-prompt schema injection. Your implementation injects the schema into the system prompt, which is fully supported by Claude 4.6.
2. **Stripping the dropout taxonomy was a severe overcorrection.** You are right: the LLM is performing narrative pattern matching on stated reasons (e.g., "Party A withdrew because the price was below market"), not computing relative market caps. Discarding this taxonomy destroys qualitative data. Your hybrid approach—extracting the narrative claim via LLM, then validating its chronological consistency in Stage 5—is the superior econometric design.

**However, I am pushing back fiercely on three of your conclusions:**

**Pushback 1: Retaining the Repair Loop (`LLM_JSON_REPAIR_ATTEMPTS`).**
While you proved `prompted_json` won't crash, the *repair loop* tied to it is econometric poison. If an LLM fails to output valid JSON on Pass 1, feeding the error trace back into the model means the repaired output is drawn from a fundamentally different conditional probability distribution ($P(Y|X, Error)$) than a first-pass success ($P(Y|X)$). This violates the independent and identically distributed (i.i.d.) assumptions required for measuring extraction variance. Native structured outputs (via `json_schema` strict mode) guarantee schema adherence at the logits level without contaminating the context window. **You must enforce `provider_native` and delete the repair loop.** If native validation fails, the run must fail closed.

**Pushback 2: GPT-5.4 `reasoning_effort="none"` is a false economy.**
Your config enforces `reasoning_effort="none"` because reasoning tokens consume the `max_completion_tokens` budget. Shutting off Chain-of-Thought on a 150-page legal document cripples the model's ability to resolve complex coreferences (tracking "the financial sponsor" from March to August). You must increase `max_completion_tokens` to the API maximum (e.g., `32000`) and use `reasoning_effort="high"`. If it hits the output cap, your (newly fixed) chunking infrastructure will handle it.

**Pushback 3: Refusing the N-Run Protocol Architecture.**
You argued that implementing N-run aggregation is "premature before proving single-shot works on the 9 reference deals." **This is a methodological trap.** Because SEC filings are in the pre-training data of frontier models, and because LLMs exhibit floating-point and MoE-routing non-determinism, "single-shot" will never work reliably out-of-sample. If you tune your prompts to force a perfect single-shot pass on these 9 calibration deals, you are overfitting to a phantom baseline. You must build the N-run consensus *infrastructure* now. We will default the CLI to `--n-runs=1` for fast iteration, but the architectural plumbing must exist today so you don't have to rewrite the orchestrator when you move to the holdout set.

Here is the complete, publication-ready architectural design and the 40-step atomic implementation plan.

---

### Deliverable 1: Complete Pipeline Design

#### (a) Pipeline Topology

The 7-stage DAG remains structurally intact, but the LLM boundary is extended in Stage 5, and Stage 4 is upgraded to enforce strict referential integrity.

*   **Stage 1: Raw Fetch (Det)** — Hardened with `urllib` timeouts and exception logging (fixing Bug 22, 23).
*   **Stage 2: Preprocess Source (Det)** — Centralized file I/O utilities (fixing Bug 16).
*   **Stage 3: Extract (LLM)** — Enforces `provider_native` mode. Repair loop deleted. Chunking threshold raised to 30,000 tokens (fixing Bug 1). Captures the **Frozen Inference Log**. Supports `--n-runs` concurrent execution.
*   **Stage 4: QA (Det)** — Transforms `RawDealExtraction` into `CanonicalDealExtraction` by validating spans *and* cross-entity referential integrity (Bug 11, 12).
*   **Stage 5: Enrich (Hybrid)** — **Major Upgrade.** (1) Executes exactly one targeted LLM call (first 25% of blocks) for `InitiationJudgment`. (2) Deterministically recalculates `peak_active_bidders` (fixing Bug 5/8). (3) Deterministically segments cycles. (4) Applies the formal/informal cascade using the new `invited_actor_ids` array (fixing Bug 9). (5) Validates LLM dropout types.
*   **Stage 6: Export (Det)** — Enforces the `passes_export_gate` (Bug 10). Aggregates NDAs on the same date into Alex's single-row format.
*   **Stage 7: Validate (Det)** — Executes Bipartite Graph Matching against Alex's benchmark Excel.

#### (b) Schema Changes — Complete Pydantic Models

We must augment the schemas to capture missing economic realities (financing conditionality, selective rounds), resolve the untyped `dict[str, Any]` bags (Bug 13), and split `DealExtraction` to enforce referential integrity (Bug 11, 12).

**(1) `pipeline/models/extraction.py`**
*(Note: These changes must be perfectly mirrored to the `Raw*` equivalents in `pipeline/llm/schemas.py`)*

```python
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from pydantic import Field, model_validator
from pipeline.models.common import (
    ActorRole, AdvisorKind, ArtifactEnvelope, BidderKind, ConsiderationType,
    DatePrecision, EventType, GeographyFlag, ListingStatus, PipelineModel, QuoteMatchType,
)
from pipeline.models.source import ChronologySelection, SeedDeal

class SourceSpan(PipelineModel):
    span_id: str
    document_id: str
    accession_number: str | None = None
    filing_type: str
    start_line: int
    end_line: int
    start_char: int | None = None
    end_char: int | None = None
    block_ids: list[str] = Field(default_factory=list)
    anchor_text: str | None = None
    quote_text: str
    quote_text_normalized: str
    match_type: QuoteMatchType
    resolution_note: str | None = None

class DateValue(PipelineModel):
    raw_text: str
    normalized_start: date | None = None
    normalized_end: date | None = None
    sort_date: date | None = None
    precision: DatePrecision
    anchor_event_id: str | None = None
    resolution_note: str | None = None
    is_inferred: bool = False

class MoneyTerms(PipelineModel):
    raw_text: str | None = None
    currency: str = "USD"
    value_per_share: Decimal | None = None
    lower_per_share: Decimal | None = None
    upper_per_share: Decimal | None = None
    total_enterprise_value: Decimal | None = None
    is_range: bool

    @model_validator(mode="after")
    def validate_amounts(self) -> "MoneyTerms":
        has_any_amount = any(
            v is not None for v in (
                self.value_per_share, self.lower_per_share,
                self.upper_per_share, self.total_enterprise_value
            )
        )
        if not has_any_amount:
            raise ValueError("MoneyTerms requires at least one numeric amount")
        if self.is_range and self.lower_per_share is None and self.upper_per_share is None:
            raise ValueError("Range money terms require a lower or upper bound")
        return self

class ActorRecord(PipelineModel):
    actor_id: str
    display_name: str
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)
    role: ActorRole
    advisor_kind: AdvisorKind | None = None
    advised_actor_id: str | None = None  # NEW: Tracks target vs bidder counsel
    bidder_kind: BidderKind | None = None
    listing_status: ListingStatus | None = None
    geography: GeographyFlag | None = None
    is_grouped: bool
    group_size: int | None = None
    group_label: str | None = None
    parent_group_actor_id: str | None = None
    first_mention_span_ids: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_group_metadata(self) -> "ActorRecord":
        if self.is_grouped and self.group_size is None and not self.group_label:
            raise ValueError("Grouped actors require group_size or group_label")
        return self

class CountAssertion(PipelineModel):
    assertion_id: str
    count: int
    subject: Literal[
        "interested_parties", "nda_signed_bidders", "nda_signed_financial_buyers",
        "nda_signed_strategic_buyers", "final_round_invitees", "other"
    ]
    qualifier_text: str | None = None
    date: DateValue | None = None
    span_ids: list[str] = Field(default_factory=list)

class EventBase(PipelineModel):
    event_id: str
    event_type: EventType
    date: DateValue
    actor_ids: list[str] = Field(default_factory=list)
    primary_span_ids: list[str] = Field(default_factory=list)
    secondary_span_ids: list[str] = Field(default_factory=list)
    summary: str
    notes: list[str] = Field(default_factory=list)

class ProcessMarkerEvent(EventBase):
    event_type: Literal[
        EventType.TARGET_SALE, EventType.TARGET_SALE_PUBLIC, EventType.BIDDER_SALE,
        EventType.BIDDER_INTEREST, EventType.ACTIVIST_SALE, EventType.SALE_PRESS_RELEASE,
        EventType.BID_PRESS_RELEASE, EventType.IB_RETENTION
    ]

class NDAEvent(EventBase):
    event_type: Literal[EventType.NDA]
    nda_signed: bool = True

class FormalitySignals(PipelineModel):
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
    is_subject_to_financing: bool | None = None  # NEW: Tracks conditionality
    signal_span_ids: list[str] = Field(default_factory=list)

class ProposalEvent(EventBase):
    event_type: Literal[EventType.PROPOSAL]
    terms: MoneyTerms
    consideration_type: ConsiderationType
    whole_company_scope: bool | None
    whole_company_scope_note: str | None = None
    formality_signals: FormalitySignals

class DropEvent(EventBase):
    event_type: Literal[
        EventType.DROP, EventType.DROP_BELOW_M, EventType.DROP_BELOW_INF,
        EventType.DROP_AT_INF, EventType.DROP_TARGET
    ]
    drop_reason_text: str | None = None

class RoundEvent(EventBase):
    event_type: Literal[
        EventType.FINAL_ROUND_INF_ANN, EventType.FINAL_ROUND_INF, EventType.FINAL_ROUND_ANN,
        EventType.FINAL_ROUND, EventType.FINAL_ROUND_EXT_ANN, EventType.FINAL_ROUND_EXT
    ]
    round_scope: Literal["informal", "formal", "extension"]
    deadline_date: DateValue | None = None
    invited_actor_ids: list[str] = Field(default_factory=list)  # NEW: Enables selectivity check

class OutcomeEvent(EventBase):
    event_type: Literal[EventType.EXECUTED]
    executed_with_actor_id: str | None = None

class CycleBoundaryEvent(EventBase):
    event_type: Literal[EventType.TERMINATED, EventType.RESTARTED]
    boundary_note: str | None = None

EventUnion = Annotated[
    ProcessMarkerEvent | NDAEvent | ProposalEvent | DropEvent | RoundEvent | OutcomeEvent | CycleBoundaryEvent,
    Field(discriminator="event_type")
]

class ExtractionExclusion(PipelineModel):
    exclusion_id: str
    category: Literal[
        "partial_company_bid", "unsigned_nda", "stale_process_reference",
        "duplicate_mention", "non_event_context", "other"
    ]
    block_ids: list[str] = Field(default_factory=list)
    explanation: str

class RawDealExtraction(ArtifactEnvelope):
    """Output of Stage 4 initialization, before span match assertion."""
    artifact_type: str = "raw_extraction"
    seed: SeedDeal
    source_selection: ChronologySelection
    actors: list[ActorRecord] = Field(default_factory=list)
    count_assertions: list[CountAssertion] = Field(default_factory=list)
    spans: list[SourceSpan] = Field(default_factory=list)
    events: list[EventUnion] = Field(default_factory=list)
    exclusions: list[ExtractionExclusion] = Field(default_factory=list)
    unresolved_mentions: list[str] = Field(default_factory=list)
    extraction_notes: list[str] = Field(default_factory=list)

class CanonicalDealExtraction(RawDealExtraction):
    """Strict type enforcing that no spans are UNRESOLVED and entity refs exist."""
    artifact_type: str = "canonical_extraction"

    @model_validator(mode="after")
    def validate_referential_integrity(self) -> "CanonicalDealExtraction":
        actor_ids = {a.actor_id for a in self.actors}
        span_ids = {s.span_id for s in self.spans}
        
        unresolved = [s.span_id for s in self.spans if s.match_type == QuoteMatchType.UNRESOLVED]
        if unresolved:
            raise ValueError(f"Canonical extraction cannot contain unresolved quote spans: {unresolved}")
            
        for event in self.events:
            invalid_actors = [aid for aid in event.actor_ids if aid not in actor_ids]
            if invalid_actors:
                raise ValueError(f"Event {event.event_id} references unknown actors: {invalid_actors}")
                
            invalid_spans = [sid for sid in event.primary_span_ids if sid not in span_ids]
            if invalid_spans:
                raise ValueError(f"Event {event.event_id} references unknown spans: {invalid_spans}")
        return self
```

**(2) `pipeline/models/enrichment.py`**

```python
from typing import Literal
from enum import StrEnum
from pydantic import Field
from pipeline.models.common import ArtifactEnvelope, ClassificationLabel, PipelineModel

class InitiationType(StrEnum):
    TARGET_DRIVEN = "target_driven"
    BIDDER_DRIVEN = "bidder_driven"
    ACTIVIST_DRIVEN = "activist_driven"
    MIXED = "mixed"

class InitiationJudgment(PipelineModel):
    initiation_type: InitiationType
    basis: str
    source_text: str
    confidence: Literal["high", "medium", "low"]

class ProposalClassification(PipelineModel):
    label: ClassificationLabel
    rule_id: str | None = None
    rule_version: str
    note: str | None = None

class CycleRecord(PipelineModel):
    cycle_id: str
    start_event_id: str
    end_event_id: str | None = None
    boundary_basis: Literal[
        "single_cycle", "explicit_terminated_restarted",
        "implicit_reinitiation_after_gap", "manual_override"
    ]
    historical_context_only: bool = False
    review_required: bool = False

class DerivedMetrics(PipelineModel):
    unique_bidders_total: int
    unique_bidders_named: int
    unique_bidders_grouped: int
    peak_active_bidders: int | None = None
    proposal_count_total: int
    proposal_count_formal: int
    proposal_count_informal: int
    nda_count: int
    duration_days: int | None = None
    cycle_count: int

class DealEnrichment(ArtifactEnvelope):
    artifact_type: str = "deal_enrichment"
    initiation_judgment: InitiationJudgment | None = None  # NEW: Promoted from System 2
    classifications: dict[str, ProposalClassification] = Field(default_factory=dict)
    cycles: list[CycleRecord] = Field(default_factory=list)
    event_sequence: dict[str, int] = Field(default_factory=dict)
    event_cycle_map: dict[str, str] = Field(default_factory=dict)
    formal_boundary_event_ids: dict[str, str | None] = Field(default_factory=dict)
    derived_metrics: DerivedMetrics
```

#### (c) New and Modified Modules

**1. `pipeline/utils/logger.py` (NEW)**
*Purpose:* Replaces scattered `print()` calls and suppresses silent failures (Bug 19).
*Implementation:* `def get_logger(name: str) -> logging.Logger:` configures standard `logging` to stream to stdout and append to `data/runs/pipeline.log`.

**2. `pipeline/utils/io.py` (NEW)**
*Purpose:* Eliminates the triple-duplicated atomic write logic (Bug 16). 
*Signatures:* `def atomic_write_json(...)`, `def atomic_write_jsonl(...)`, `def atomic_write_text(...)`.

**3. `pipeline/utils/schema.py` (NEW)**
*Purpose:* Deep-inlines JSON schemas to prevent OpenAI strict mode `$ref` rejection (Bug 5).
*Signature:* `def inline_json_refs(schema: dict[str, Any]) -> dict[str, Any]:`

**4. `pipeline/enrich/initiation.py` (NEW)**
*Purpose:* Stage 5 LLM inference for causality.
*Signature:* `def extract_initiation_judgment(blocks: list[ChronologyBlock], backend: LLMBackend) -> InitiationJudgment:`
*Control Flow:* Extracts `blocks[:max(15, len(blocks)//4)]`. Injects into an `INITIATION_SYSTEM_PROMPT` containing Alex's causal logic. Invokes backend in `provider_native` mode. Returns populated `InitiationJudgment` model.

**5. `pipeline/enrich/dropout_validation.py` (NEW)**
*Purpose:* Deterministically validates the LLM's dropout subclassifications.
*Signature:* `def validate_dropouts(extraction: CanonicalDealExtraction) -> list[QAFinding]:`
*Control Flow:* Traverses events. If an event is `EventType.DROP_BELOW_INF` for Actor X, searches backward for a `ProposalEvent` from Actor X classified as `INFORMAL` in the same cycle. If absent, generates a `QAFinding` (Warning) that the dropout type lacks chronological support.

**6. `pipeline/enrich/features.py` (MODIFIED)**
*Purpose:* Fixes `peak_active_bidders` monotonically increasing across dropouts (Bug 5, 8).
*Logic:*
```python
def _peak_active_bidders(extraction: CanonicalDealExtraction) -> int:
    bidder_ids = {a.actor_id for a in extraction.actors if a.role == ActorRole.BIDDER}
    active: set[str] = set()
    peak = 0
    ordered = sorted(extraction.events, key=lambda e: (e.date.sort_date or date.max, e.event_id))
    
    for event in ordered:
        if event.event_type in {EventType.DROP, EventType.DROP_BELOW_M, EventType.DROP_BELOW_INF, EventType.DROP_AT_INF, EventType.DROP_TARGET, EventType.EXECUTED}:
            for actor_id in event.actor_ids:
                active.discard(actor_id)
        elif event.event_type == EventType.TERMINATED:
            active.clear()
        elif event.event_type in {EventType.NDA, EventType.PROPOSAL}:
            for actor_id in event.actor_ids:
                if actor_id in bidder_ids:
                    active.add(actor_id)
        peak = max(peak, len(active))
    return peak
```

#### (d) Classification Cascade (`pipeline/enrich/classify.py`)

Rewritten to fix `last_round_event` leaking across cycle boundaries (Bug 9) and to implement Rule F2 selectivity using `invited_actor_ids`.

```python
def classify_proposals(
    extraction: CanonicalDealExtraction,
    cycles: list[CycleRecord],
    event_cycle_map: dict[str, str],
    peak_active_bidders: int  # Passed from features.py
) -> dict[str, ProposalClassification]:
    classifications: dict[str, ProposalClassification] = {}
    
    for cycle in cycles:
        # Isolate events to this cycle to prevent state bleed
        cycle_events = sorted(
            [e for e in extraction.events if event_cycle_map.get(e.event_id) == cycle.cycle_id],
            key=lambda x: x.date.sort_date or date.max
        )
        last_round_event: RoundEvent | None = None
        
        for event in cycle_events:
            if isinstance(event, RoundEvent):
                last_round_event = event
                continue
            if not isinstance(event, ProposalEvent):
                continue

            signals = event.formality_signals
            terms = event.terms

            # Priority 1: Range Bids
            if terms.is_range:
                classifications[event.event_id] = ProposalClassification(
                    label=ClassificationLabel.INFORMAL, rule_id="I1_range_bid", rule_version="2026-03-18-v2"
                )
                continue
                
            # Priority 2: Explicit Informal Language
            if signals.mentions_indication_of_interest or signals.mentions_preliminary or signals.mentions_non_binding:
                classifications[event.event_id] = ProposalClassification(
                    label=ClassificationLabel.INFORMAL, rule_id="I2_explicit_informal", rule_version="2026-03-18-v2"
                )
                continue
                
            # Priority 3: Binding Package
            if signals.includes_draft_merger_agreement or signals.mentions_binding_offer:
                classifications[event.event_id] = ProposalClassification(
                    label=ClassificationLabel.FORMAL, rule_id="F1_binding_package", rule_version="2026-03-18-v2"
                )
                continue
                
            # Priority 4: Selective Final Round Context
            if last_round_event and last_round_event.event_type in {EventType.FINAL_ROUND_ANN, EventType.FINAL_ROUND_EXT_ANN, EventType.FINAL_ROUND}:
                if signals.after_final_round_announcement or signals.requested_binding_offer_via_process_letter:
                    is_selective = True
                    if last_round_event.invited_actor_ids:
                        if len(last_round_event.invited_actor_ids) >= peak_active_bidders and peak_active_bidders > 1:
                            is_selective = False
                    if is_selective or event.actor_ids[0] in last_round_event.invited_actor_ids:
                        classifications[event.event_id] = ProposalClassification(
                            label=ClassificationLabel.FORMAL, rule_id="F2_formal_round_context_selective", rule_version="2026-03-18-v2"
                        )
                        continue

            # Priority 5: Non-Selective Round Context Fallback
            if last_round_event:
                if last_round_event.event_type in {EventType.FINAL_ROUND_INF_ANN, EventType.FINAL_ROUND_INF}:
                    classifications[event.event_id] = ProposalClassification(
                        label=ClassificationLabel.INFORMAL, rule_id="I3_informal_round_context", rule_version="2026-03-18-v2"
                    )
                    continue
                elif last_round_event.event_type in {EventType.FINAL_ROUND_ANN, EventType.FINAL_ROUND, EventType.FINAL_ROUND_EXT_ANN}:
                    classifications[event.event_id] = ProposalClassification(
                        label=ClassificationLabel.FORMAL, rule_id="F3_formal_round_context_non_selective", rule_version="2026-03-18-v2"
                    )
                    continue

            # Default
            classifications[event.event_id] = ProposalClassification(
                label=ClassificationLabel.INFORMAL, rule_id="U1_default_informal", rule_version="2026-03-18-v2"
            )
            
    return classifications
```

#### (e) Validation Framework (`pipeline/validate/matcher.py`)

Because Alex uses fractional IDs and "rough" dates, a simple merge fails. We compute a Cost Matrix and apply Scipy's `linear_sum_assignment` to find the optimal global bipartite match.

```python
import numpy as np
from scipy.optimize import linear_sum_assignment
import jellyfish # for Jaro-Winkler
from datetime import date

def match_events(pipeline_events: list[dict], alex_events: list[dict]) -> tuple[list, dict]:
    cost_matrix = np.full((len(pipeline_events), len(alex_events)), fill_value=1000.0)
    for i, p_evt in enumerate(pipeline_events):
        for j, a_evt in enumerate(alex_events):
            cost = 0.0
            
            # Temporal cost: +10 penalty per day diff. >3 days = infinity
            p_date = p_evt.get("sort_date") or date.max
            a_date = a_evt.get("bid_date_rough") or date.max
            if p_date != date.max and a_date != date.max:
                day_diff = abs((p_date - a_date).days)
                if day_diff > 3:
                    continue # infinite cost
                cost += day_diff * 10
            
            # Actor cost: Jaro-Winkler distance * 100
            jw_sim = jellyfish.jaro_winkler_similarity(str(p_evt.get("actor_name", "")), str(a_evt.get("Bidder", "")))
            if jw_sim < 0.75:
                cost += 500 # Heavy penalty but matchable if date is perfect
            else:
                cost += (1.0 - jw_sim) * 100
                
            cost_matrix[i, j] = cost
            
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    
    matches = [(pipeline_events[r], alex_events[c]) for r, c in zip(row_ind, col_ind) if cost_matrix[r, c] < 1000.0]
    
    # Compute Metrics
    precision = len(matches) / len(pipeline_events) if pipeline_events else 0
    recall = len(matches) / len(alex_events) if alex_events else 0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    
    mape_list = []
    for p, a in matches:
        p_val = p.get('bid_value_pershare')
        a_val = a.get('bid_value_pershare')
        if p_val and a_val:
            mape_list.append(abs(float(p_val) - float(a_val)) / float(a_val))
            
    mape = sum(mape_list) / len(mape_list) if mape_list else 0.0
            
    return matches, {"f1_score": f1, "mape": mape}
```

#### (f) Export Specification (`pipeline/export/alex_compat.py`)

Deterministically map the pipeline structure to the 47-column CSV, implementing the NDA Aggregation grouping.

```python
def build_alex_compat_rows(extraction, enrichment, qa_report):
    from collections import defaultdict
    nda_by_date = defaultdict(list)
    other_events = []
    
    ordered_events = sorted(extraction.events, key=lambda e: enrichment.event_sequence.get(e.event_id, 10**9))
    
    # Pre-group NDAs
    for event in ordered_events:
        if event.event_type == EventType.NDA and event.date.sort_date:
            nda_by_date[event.date.sort_date].append(event)
        else:
            other_events.append(event)
            
    rows = []
    
    # Process NDA groups into single rows
    for dt, ndas in nda_by_date.items():
        counts = [c for c in extraction.count_assertions if c.subject == "nda_signed_bidders" and c.date and c.date.sort_date == dt]
        total = counts[0].count if counts else len(ndas)
        
        named = []
        types = []
        for nda in ndas:
            for aid in nda.actor_ids:
                actor = next((a for a in extraction.actors if a.actor_id == aid), None)
                if actor:
                    named.append(actor.display_name)
                    if actor.bidder_kind == BidderKind.STRATEGIC: types.append("S")
                    elif actor.bidder_kind == BidderKind.FINANCIAL: types.append("F")
        
        bidder_str = f"{total} parties"
        if named:
            bidder_str = f"{total} parties, including {', '.join(named)}" if total > len(named) else ", ".join(named)
                
        type_str = ""
        if types:
            s_count, f_count = types.count("S"), types.count("F")
            parts = []
            if s_count: parts.append(f"{s_count}S")
            if f_count: parts.append(f"{f_count}F")
            type_str = ", ".join(parts)
            
        rows.append({
            "TargetName": extraction.seed.target_name,
            "EventType": "nda",
            "Bidder": bidder_str,
            "bidder_type_note": type_str,
            "bid_date_rough": dt.strftime("%m/%d/%Y"),
            # ... remaining schema fields left blank/NA
        })
        
    # Process other_events normally
    # Mappings:
    # `is_subject_to_financing` -> `comments_2`
    # `advised_actor_id` -> prefix `bidder_type_note` with "Legal counsel to [Name]"
    # `initiation_judgment` -> `comments_3` (on the first row only)
```

---

### Deliverable 2: Ultra-Meticulous Implementation Plan

This plan is exactly 40 steps grouped into 6 phases, ordered strictly by dependency. It builds the N-Run framework but defaults the CLI to `1` so you can calibrate the 9-deal set seamlessly.

#### Phase 0: Eradicate Critical Bugs & Consolidate Utilities
*Objective: Eliminate all agent-identified crashes and stabilize I/O.*

1. **File:** `pipeline/utils/logger.py` (NEW)
   *Action:* Create file returning `logging.getLogger("bids-pipeline")` with a basic stdout `StreamHandler`.
   *Test:* Verify `pytest` captures output.
   *Complexity:* Trivial.
2. **File:** `pipeline/utils/io.py` (NEW)
   *Action:* Create file. Move `atomic_write_json`, `atomic_write_jsonl`, and `atomic_write_text` here from `extract/utils.py` and `preprocess/source.py`. Update all imports across the codebase.
   *Test:* `pytest tests/` (ensures import refactor didn't break paths).
   *Complexity:* Small.
3. **File:** `pipeline/llm/backend.py`
   *Action:* Add `import json` to the top of the file. (Fixes Bug 2 latent crash in `_system_to_text`).
   *Test:* `pytest tests/test_llm_backend.py -v`.
   *Complexity:* Trivial.
4. **File:** `pipeline/extract/events.py`
   *Action:* Line 73: Change `if complexity != "simple":` to `if complexity != ComplexityClass.SIMPLE:`. (Fixes Bug 1 chunking override).
   *Test:* `pytest tests/test_extract_pipeline.py -v`.
   *Complexity:* Trivial.
5. **File:** `pipeline/llm/token_budget.py`
   *Action:* Update `classify_complexity`. Raise `SIMPLE` bounds to `30_000` tokens and `800` lines.
   *Test:* Modify `test_classify_complexity_respects_thresholds`.
   *Complexity:* Small.
6. **File:** `pipeline/runs/state.py`
   *Action:* Add `run_id TEXT` to the `CREATE TABLE review_items` SQL. Update `record_review_item` and `summarize_run` queries to use `WHERE run_id = ?`. (Fixes Bug 3).
   *Test:* `pytest tests/test_state.py -v`.
   *Complexity:* Small.
7. **File:** `pipeline/qa/review.py`
   *Action:* Change `finding.severity == "blocker"` to `finding.severity == ReviewSeverity.BLOCKER`. Repeat for `"warning"`. (Fixes Bug 4).
   *Test:* `pytest tests/test_qa_stage.py -v`.
   *Complexity:* Trivial.
8. **File:** `pipeline/llm/prompts.py`
   *Action:* Move `PROMPT_SPEC_PATH.read_text()` inside the `_prompt_spec_text` function to prevent import-time file I/O crashes (Fixes Bug 7).
   *Test:* `pytest tests/test_llm_backend.py -v`.
   *Complexity:* Trivial.
9. **File:** `pipeline/source/fetch.py` & `pipeline/source/discovery.py`
   *Action:* In `fetch.py`, add `timeout=30` to `urlopen`. In `discovery.py:27`, change `except Exception:` to `except Exception as e:` and `logger.error("EDGAR search failed", exc_info=True)`. (Fixes Bugs 22/23).
   *Complexity:* Trivial.
10. **File:** `pipeline/orchestrator.py`
    *Action:* Wrap the core loop contents of `run_actor_extraction_batch`, `run_event_extraction_batch`, etc., in `try/except Exception as e`. Call `logger.error` and `state_store.record_stage_attempt(..., status="failed")`, then `continue`. (Fixes Bug 6).
    *Test:* `pytest tests/test_cli.py -v`.
    *Complexity:* Small.

#### Phase 1: Schema Migrations & Strict Typing
*Objective: Add required relational fields and enforce Pydantic types.*

11. **File:** `pipeline/models/common.py`
    *Action:* Add `model_config = ConfigDict(use_enum_values=True, strict=True, extra="forbid")` to `PipelineModel`.
    *Complexity:* Trivial.
12. **File:** `pipeline/models/extraction.py`
    *Action:* Rename `DealExtraction` to `CanonicalDealExtraction`. Define `RawDealExtraction` (without span validation). Have `Canonical` inherit `Raw`. Add `validate_referential_integrity` to `Canonical` (checks `actor_ids` vs `actors`). Update imports in `qa/`, `enrich/`, `export/`. (Fixes Bug 11, 12).
    *Test:* `pytest tests/test_models_v2.py -v`.
    *Complexity:* Medium.
13. **File:** `pipeline/models/extraction.py` & `pipeline/llm/schemas.py`
    *Action:* Add `advised_actor_id: str | None = None` to `ActorRecord` / `RawActorRecord`.
    *Complexity:* Trivial.
14. **File:** `pipeline/models/extraction.py` & `pipeline/llm/schemas.py`
    *Action:* Add `invited_actor_ids: list[str] = Field(default_factory=list)` to `RoundEvent` / `RawEventRecord`.
    *Complexity:* Trivial.
15. **File:** `pipeline/models/extraction.py` & `pipeline/llm/schemas.py`
    *Action:* Add `is_subject_to_financing: bool | None = None` to `FormalitySignals` / `RawFormalitySignals`.
    *Complexity:* Trivial.
16. **File:** `pipeline/models/enrichment.py` & `pipeline/llm/schemas.py`
    *Action:* Create `InitiationType(StrEnum)` and `InitiationJudgment` model. Add `initiation_judgment` to `DealEnrichment`.
    *Test:* `pytest tests/test_schemas.py -v`.
    *Complexity:* Small.
17. **File:** `pipeline/models/export.py` & `pipeline/qa.py`
    *Action:* Change `ReviewRow` fields (`event_type`, `actor_role`) to Enum types (Fixes Bug 14). In `qa.py`, replace `dict[str, Any]` with typed Pydantic models (Fixes Bug 13).
    *Test:* `pytest tests/test_export_stage.py -v`.
    *Complexity:* Small.
18. **File:** `pipeline/qa/rules.py`
    *Action:* Map new raw fields (`advised_actor_id`, `invited_actor_ids`, `is_subject_to_financing`) to canonical fields inside `_reconcile_actors` and `_build_event_model`. If `match_type == QuoteMatchType.FUZZY`, append a `ReviewSeverity.WARNING` finding to `QAReport`.
    *Test:* `pytest tests/test_qa_stage.py -v`.
    *Complexity:* Medium.

#### Phase 2: LLM Architecture & Frozen Logs
*Objective: Enforce Strict Outputs, implement N-Run plumbing, and build replication logs.*

19. **File:** `pipeline/utils/schema.py` (NEW)
    *Action:* Move `inline_json_refs` here from `llm/schemas.py`.
    *Complexity:* Small.
20. **File:** `pipeline/llm/openai_backend.py`
    *Action:* Import `inline_json_refs`. Apply it to `output_schema.model_json_schema()` before assigning to `response_format` to fix `$ref` strict mode rejection (Fixes Bug 5). Hardcode `max_completion_tokens = 32000` to prevent CoT truncation.
    *Test:* `pytest tests/test_llm_backend.py -v`.
    *Complexity:* Small.
21. **File:** `pipeline/config.py` & `pipeline/llm/backend.py`
    *Action:* Change `DEFAULT_STRUCTURED_OUTPUT_MODE = "provider_native"`. Delete `_repair_loop` and `arepair_structured` completely. Force `resolved_mode = "provider_native"`. Raise `ValidationError` if output fails parsing.
    *Test:* Remove repair tests in `test_llm_backend.py`. Run `pytest`.
    *Complexity:* Medium.
22. **File:** `pipeline/runs/state.py`
    *Action:* Add `CREATE TABLE frozen_inference_logs (request_id TEXT PRIMARY KEY, run_id TEXT, deal_slug TEXT, raw_request TEXT, raw_response TEXT)`.
    *Complexity:* Small.
23. **File:** `pipeline/llm/anthropic_backend.py` & `pipeline/llm/openai_backend.py`
    *Action:* Capture raw request dict and raw response string in `_agenerate_text` and `_ainvoke_provider_native`. Pass to `LLMUsage`.
    *Complexity:* Medium.
24. **File:** `pipeline/cli.py` & `pipeline/orchestrator.py`
    *Action:* In `_record_usage_calls`, insert `LLMUsage.raw_json` into `frozen_inference_logs`. Add `--n-runs` (default=1) to the `extract events` CLI parser. Pass it down to `run_event_extraction`.
    *Test:* `pytest tests/test_state.py -v`.
    *Complexity:* Medium.
25. **File:** `pipeline/extract/consensus.py` (NEW)
    *Action:* Write `resolve_event_consensus(runs: list[EventExtractionOutput]) -> EventExtractionOutput`. Group events by hash. Require `count >= N//2 + 1`. Calculate medians for numeric fields. 
    *Test:* `pytest tests/test_consensus.py`
    *Complexity:* Large.
26. **File:** `pipeline/extract/events.py`
    *Action:* If `n_runs > 1`, wrap `_invoke_event_call` in an `asyncio.gather` list comprehension. Pass results to `resolve_event_consensus`.
    *Test:* `pytest tests/test_extract_pipeline.py -v`.
    *Complexity:* Medium.
27. **File:** `pipeline/llm/prompts.py`
    *Action:* Update System Prompts. Add instructions to extract `advised_actor_id`, `invited_actor_ids`, and `is_subject_to_financing`. Create `INITIATION_SYSTEM_PROMPT`.
    *Complexity:* Small.

#### Phase 3: Stage 5 Enrichment
*Objective: Integrate Initiation LLM call and cycle-aware classification.*

28. **File:** `pipeline/enrich/features.py`
    *Action:* Rewrite `_peak_active_bidders` using the set addition/removal logic specified in Design (c) to track only `ActorRole.BIDDER` (Fixes Bug 8).
    *Test:* `pytest tests/test_enrichment_stage.py -v`.
    *Complexity:* Medium.
29. **File:** `pipeline/enrich/classify.py`
    *Action:* Rewrite `classify_proposals` to iterate per-cycle (Fixes Bug 9). Reset `last_round_event` per cycle. Implement Rule F2 Selectivity check against `peak_active_bidders`.
    *Test:* `pytest tests/test_enrichment_stage.py -v`.
    *Complexity:* Medium.
30. **File:** `pipeline/enrich/dropout_validation.py` (NEW)
    *Action:* Implement `validate_dropouts(events)`. If `DROP_BELOW_INF` occurs, assert a prior `INFORMAL` proposal exists. Return `QAFinding` warnings.
    *Complexity:* Small.
31. **File:** `pipeline/enrich/initiation.py` (NEW)
    *Action:* Implement `extract_initiation_judgment`. Select `blocks[:max(15, len(blocks)//4)]`. Invoke backend in native mode.
    *Complexity:* Medium.
32. **File:** `pipeline/enrich/__init__.py` & `pipeline/cli.py`
    *Action:* Update `run_enrichment` to accept `backend: LLMBackend`. Call `extract_initiation_judgment` and `validate_dropouts`. In `cli.py`, parse `--provider` for the `enrich` command and pass instantiated backend.
    *Test:* `pytest tests/test_enrichment_stage.py -v`.
    *Complexity:* Medium.

#### Phase 4: Stage 6 Export & Stage 7 Validation
*Objective: Enforce QA gates, aggregate NDAs, and build Bipartite Matcher.*

33. **File:** `pipeline/export/review_csv.py`
    *Action:* Enforce export gate. Add `if not qa_report.passes_export_gate: raise RuntimeError("Export Blocked")` (Fixes Bug 10).
    *Test:* `pytest tests/test_export_stage.py -v`.
    *Complexity:* Trivial.
34. **File:** `pipeline/export/alex_compat.py`
    *Action:* Implement NDA Aggregation. Group `NDAEvent`s by date, lookup `CountAssertion`, merge into single row. Map `is_subject_to_financing`, `advised_actor_id`, and `initiation_judgment` into comments.
    *Test:* Add `test_nda_aggregation` to `test_export_stage.py`.
    *Complexity:* Large.
35. **File:** `pyproject.toml`
    *Action:* Add `scipy` and `jellyfish` to dependencies. Run `pip install -e .`.
    *Complexity:* Trivial.
36. **File:** `pipeline/validate/bipartite.py` & `pipeline/validate/metrics.py` (NEW)
    *Action:* Implement `match_events` using `scipy.optimize.linear_sum_assignment` over Date/Actor similarity cost matrix. Compute F1 and MAPE.
    *Test:* Create `tests/test_validate_bipartite.py`.
    *Complexity:* Large.
37. **File:** `pipeline/cli.py`
    *Action:* Update `validate` command to invoke Bipartite matching and output `reference_summary.json`. Print F1/MAPE to console.
    *Complexity:* Small.

#### Phase 5: End-to-End System Verification
38. **Execution Script:**
    ```bash
    # 1. Clean environment
    rm data/runs/pipeline_state.sqlite
    rm -rf data/deals/imprivata

    # 2. Fetch & Preprocess
    pipeline raw fetch --deal imprivata
    pipeline preprocess source --deal imprivata

    # 3. Extract (Tests single-shot, native schema, frozen logs, and raised chunk bounds)
    pipeline extract actors --deal imprivata --provider anthropic
    pipeline extract events --deal imprivata --provider anthropic --n-runs 1

    # 4. QA (Verifies referential integrity and fuzzy match warnings)
    pipeline qa --deal imprivata

    # 5. Enrich (Tests Stage 5 Initiation LLM Call)
    pipeline enrich --deal imprivata --provider anthropic

    # 6. Export & Validate (Tests NDA grouping and Bipartite Matcher)
    pipeline export --deal imprivata
    pipeline validate references --deal imprivata
    ```
    **Pass Criteria:** `alex_compat.csv` contains exactly 47 columns. `event_usage.json` confirms `chunk_mode: single_pass`. SQLite `frozen_inference_logs` contains raw JSON. The script exits 0, outputting an F1 score > 0.85 and MAPE < 0.05.
