# Models and Schemas

---

## pipeline/models/common.py
```python
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


SCHEMA_VERSION = "2.0.0"
PIPELINE_VERSION = "0.1.0"


class PipelineModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


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


class ArtifactEnvelope(PipelineModel):
    schema_version: str = SCHEMA_VERSION
    artifact_type: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    pipeline_version: str = PIPELINE_VERSION
    run_id: str
    deal_slug: str | None = None
```

---

## pipeline/models/seed.py
```python
from datetime import date

from pydantic import Field

from pipeline.models.common import PipelineModel


class SeedEvidence(PipelineModel):
    row_ref: str | None = None
    provided_deal_slug: str | None = None
    target_name_raw: str
    acquirer_raw: str | None = None
    date_announced_raw: str | None = None
    primary_url_raw: str | None = None
    is_reference_raw: bool | None = None


class SeedRegistryEntry(PipelineModel):
    deal_slug: str
    target_name: str
    acquirer: str | None = None
    date_announced: date | None = None
    primary_url: str | None = None
    is_reference: bool
    evidence: list[SeedEvidence] = Field(default_factory=list)
    conflicting_evidence: dict[str, list[str]] = Field(default_factory=dict)
```

---

## pipeline/models/raw.py
```python
from typing import Literal

from pydantic import Field

from pipeline.models.common import ArtifactEnvelope
from pipeline.models.source import FilingCandidate, FrozenDocument, SeedDeal


class RawDiscoveryManifest(ArtifactEnvelope):
    artifact_type: str = "raw_discovery_manifest"
    seed: SeedDeal
    cik: str | None = None
    primary_candidates: list[FilingCandidate] = Field(default_factory=list)
    supplementary_candidates: list[FilingCandidate] = Field(default_factory=list)
    fetch_scope: Literal["all_candidates"] = "all_candidates"


class RawDocumentRegistry(ArtifactEnvelope):
    artifact_type: str = "raw_document_registry"
    documents: list[FrozenDocument] = Field(default_factory=list)
```

---

## pipeline/models/source.py
```python
from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field

from pipeline.models.common import ArtifactEnvelope, PipelineModel


class EvidenceType(StrEnum):
    DATED_ACTION = "dated_action"
    FINANCIAL_TERM = "financial_term"
    ACTOR_IDENTIFICATION = "actor_identification"
    PROCESS_SIGNAL = "process_signal"
    OUTCOME_FACT = "outcome_fact"


class SeedDeal(ArtifactEnvelope):
    artifact_type: str = "seed_deal"
    deal_slug: str
    target_name: str
    acquirer_seed: str | None = None
    date_announced_seed: date | None = None
    primary_url_seed: str | None = None
    is_reference: bool
    seed_row_refs: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class FilingCandidate(PipelineModel):
    document_id: str
    accession_number: str | None = None
    filing_type: str
    filing_date: date | None = None
    sec_url: str | None = None
    source_origin: Literal["seed_accession", "edgartools_search", "manual_override"]
    ranking_features: dict[str, Any] = Field(default_factory=dict)
    selected_for_localization: bool = False
    rejected_reason: str | None = None


class FrozenDocument(PipelineModel):
    document_id: str
    accession_number: str | None = None
    filing_type: str
    filing_date: date | None = None
    html_path: str | None = None
    txt_path: str
    md_path: str | None = None
    sha256_txt: str
    sha256_html: str | None = None
    byte_count_txt: int
    fetched_at: datetime


class FilingDiscoveryReport(ArtifactEnvelope):
    artifact_type: str = "filing_discovery_report"
    seed: SeedDeal
    cik: str | None = None
    primary_candidates: list[FilingCandidate] = Field(default_factory=list)
    supplementary_candidates: list[FilingCandidate] = Field(default_factory=list)
    frozen_documents: list[FrozenDocument] = Field(default_factory=list)


class ChronologyCandidate(PipelineModel):
    document_id: str
    heading_text: str
    heading_normalized: str
    start_line: int
    end_line: int
    score: int
    source_methods: list[
        Literal["txt_heading", "txt_search", "html_heading", "markdown_heading", "sections_api"]
    ] = Field(default_factory=list)
    is_standalone_background: bool
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class ChronologySelection(ArtifactEnvelope):
    artifact_type: str = "chronology_selection"
    document_id: str
    accession_number: str | None = None
    filing_type: str
    selected_candidate: ChronologyCandidate | None = None
    confidence: Literal["high", "medium", "low", "none"]
    adjudication_basis: str
    alternative_candidates: list[ChronologyCandidate] = Field(default_factory=list)
    review_required: bool
    confidence_factors: dict[str, Any] = Field(default_factory=dict)


class ChronologyBlock(PipelineModel):
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


class EvidenceItem(PipelineModel):
    evidence_id: str
    document_id: str
    accession_number: str | None = None
    filing_type: str
    start_line: int
    end_line: int
    raw_text: str
    evidence_type: EvidenceType
    confidence: Literal["high", "medium", "low"]
    matched_terms: list[str] = Field(default_factory=list)
    date_text: str | None = None
    actor_hint: str | None = None
    value_hint: str | None = None
    note: str | None = None


class SupplementarySnippet(PipelineModel):
    snippet_id: str
    document_id: str
    filing_type: str
    event_hint: Literal["sale_press_release", "bid_press_release", "activist_sale", "other"]
    start_line: int
    end_line: int
    raw_text: str
    keyword_hits: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"]
    evidence_id: str | None = None
```

---

## pipeline/models/extraction.py
```python
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field, model_validator

from pipeline.models.common import (
    ActorRole,
    AdvisorKind,
    ArtifactEnvelope,
    BidderKind,
    ConsiderationType,
    DatePrecision,
    EventType,
    GeographyFlag,
    ListingStatus,
    PipelineModel,
    QuoteMatchType,
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
            value is not None
            for value in (
                self.value_per_share,
                self.lower_per_share,
                self.upper_per_share,
                self.total_enterprise_value,
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
        "interested_parties",
        "nda_signed_bidders",
        "nda_signed_financial_buyers",
        "nda_signed_strategic_buyers",
        "final_round_invitees",
        "other",
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
    round_scope: Literal["informal", "formal", "extension"]
    deadline_date: DateValue | None = None


class OutcomeEvent(EventBase):
    event_type: Literal[EventType.EXECUTED]
    executed_with_actor_id: str | None = None


class CycleBoundaryEvent(EventBase):
    event_type: Literal[EventType.TERMINATED, EventType.RESTARTED]
    boundary_note: str | None = None


EventUnion = Annotated[
    ProcessMarkerEvent
    | NDAEvent
    | ProposalEvent
    | DropEvent
    | RoundEvent
    | OutcomeEvent
    | CycleBoundaryEvent,
    Field(discriminator="event_type"),
]


class ExtractionExclusion(PipelineModel):
    exclusion_id: str
    category: Literal[
        "partial_company_bid",
        "unsigned_nda",
        "stale_process_reference",
        "duplicate_mention",
        "non_event_context",
        "other",
    ]
    block_ids: list[str] = Field(default_factory=list)
    explanation: str


class DealExtraction(ArtifactEnvelope):
    artifact_type: str = "deal_extraction"
    seed: SeedDeal
    source_selection: ChronologySelection
    actors: list[ActorRecord] = Field(default_factory=list)
    count_assertions: list[CountAssertion] = Field(default_factory=list)
    spans: list[SourceSpan] = Field(default_factory=list)
    events: list[EventUnion] = Field(default_factory=list)
    exclusions: list[ExtractionExclusion] = Field(default_factory=list)
    unresolved_mentions: list[str] = Field(default_factory=list)
    extraction_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_canonical_export_ready(self) -> "DealExtraction":
        if self.artifact_type == "canonical_extraction":
            unresolved_spans = [
                span.span_id
                for span in self.spans
                if span.match_type == QuoteMatchType.UNRESOLVED
            ]
            if unresolved_spans:
                raise ValueError(
                    "Canonical extraction cannot contain unresolved quote spans: "
                    + ", ".join(unresolved_spans)
                )
        return self
```

---

## pipeline/models/enrichment.py
```python
from typing import Literal

from pydantic import Field

from pipeline.models.common import ArtifactEnvelope, ClassificationLabel, PipelineModel


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
        "single_cycle",
        "explicit_terminated_restarted",
        "implicit_reinitiation_after_gap",
        "manual_override",
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
    classifications: dict[str, ProposalClassification] = Field(default_factory=dict)
    cycles: list[CycleRecord] = Field(default_factory=list)
    event_sequence: dict[str, int] = Field(default_factory=dict)
    event_cycle_map: dict[str, str] = Field(default_factory=dict)
    formal_boundary_event_ids: dict[str, str | None] = Field(default_factory=dict)
    derived_metrics: DerivedMetrics
```

---

## pipeline/models/qa.py
```python
from typing import Any

from pydantic import Field

from pipeline.models.common import ArtifactEnvelope, PipelineModel, ReviewSeverity


class QAFinding(PipelineModel):
    finding_id: str
    severity: ReviewSeverity
    code: str
    message: str
    related_actor_ids: list[str] = Field(default_factory=list)
    related_event_ids: list[str] = Field(default_factory=list)
    related_span_ids: list[str] = Field(default_factory=list)
    auto_fix_applied: bool = False
    review_required: bool = False


class QAReport(ArtifactEnvelope):
    artifact_type: str = "qa_report"
    blocker_count: int
    warning_count: int
    findings: list[QAFinding] = Field(default_factory=list)
    completeness_metrics: dict[str, Any] = Field(default_factory=dict)
    passes_export_gate: bool
```

---

## pipeline/models/export.py
```python
from datetime import date
from decimal import Decimal

from pydantic import Field

from pipeline.models.common import PipelineModel


class ReviewRow(PipelineModel):
    deal_slug: str
    target_name: str
    event_sequence: int
    cycle_id: str | None = None
    event_id: str
    event_type: str
    actor_id: str | None = None
    actor_name: str | None = None
    actor_role: str | None = None
    bidder_kind: str | None = None
    listing_status: str | None = None
    geography: str | None = None
    raw_date: str
    sort_date: date | None = None
    value_per_share: Decimal | None = None
    lower_per_share: Decimal | None = None
    upper_per_share: Decimal | None = None
    consideration_type: str | None = None
    proposal_classification: str | None = None
    classification_rule: str | None = None
    accession_number: str | None = None
    filing_type: str | None = None
    source_lines: str
    source_quote_full: str
    qa_flags: list[str] = Field(default_factory=list)
```

---

## pipeline/models/__init__.py
```python
from pipeline.models.common import (
    ActorRole,
    AdvisorKind,
    ArtifactEnvelope,
    BidderKind,
    ClassificationLabel,
    ConsiderationType,
    DatePrecision,
    EventType,
    GeographyFlag,
    ListingStatus,
    QuoteMatchType,
    ReviewSeverity,
    SCHEMA_VERSION,
)
from pipeline.models.enrichment import CycleRecord, DealEnrichment, DerivedMetrics, ProposalClassification
from pipeline.models.export import ReviewRow
from pipeline.models.extraction import (
    ActorRecord,
    CountAssertion,
    CycleBoundaryEvent,
    DateValue,
    DealExtraction,
    DropEvent,
    EventBase,
    EventUnion,
    ExtractionExclusion,
    FormalitySignals,
    MoneyTerms,
    NDAEvent,
    OutcomeEvent,
    ProcessMarkerEvent,
    ProposalEvent,
    RoundEvent,
    SourceSpan,
)
from pipeline.models.qa import QAFinding, QAReport
from pipeline.models.raw import RawDiscoveryManifest, RawDocumentRegistry
from pipeline.models.source import (
    ChronologyBlock,
    ChronologyCandidate,
    ChronologySelection,
    EvidenceItem,
    EvidenceType,
    FilingCandidate,
    FilingDiscoveryReport,
    FrozenDocument,
    SeedDeal,
    SupplementarySnippet,
)

__all__ = [
    "ActorRecord",
    "ActorRole",
    "AdvisorKind",
    "ArtifactEnvelope",
    "BidderKind",
    "ChronologyBlock",
    "ChronologyCandidate",
    "ChronologySelection",
    "EvidenceItem",
    "EvidenceType",
    "ClassificationLabel",
    "ConsiderationType",
    "CountAssertion",
    "CycleBoundaryEvent",
    "CycleRecord",
    "DatePrecision",
    "DateValue",
    "DealEnrichment",
    "DealExtraction",
    "DerivedMetrics",
    "DropEvent",
    "EventBase",
    "EventType",
    "EventUnion",
    "ExtractionExclusion",
    "FilingCandidate",
    "FilingDiscoveryReport",
    "FormalitySignals",
    "FrozenDocument",
    "GeographyFlag",
    "ListingStatus",
    "MoneyTerms",
    "NDAEvent",
    "OutcomeEvent",
    "ProcessMarkerEvent",
    "ProposalClassification",
    "ProposalEvent",
    "QAFinding",
    "QAReport",
    "QuoteMatchType",
    "RawDiscoveryManifest",
    "RawDocumentRegistry",
    "ReviewRow",
    "ReviewSeverity",
    "RoundEvent",
    "SCHEMA_VERSION",
    "SeedDeal",
    "SourceSpan",
    "SupplementarySnippet",
]
```

---

## pipeline/llm/schemas.py
```python
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pipeline.models.common import (
    ActorRole,
    AdvisorKind,
    BidderKind,
    ConsiderationType,
    EventType,
    GeographyFlag,
    ListingStatus,
)


class LLMOutputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RawEvidenceRef(LLMOutputModel):
    block_id: str | None = None
    evidence_id: str | None = None
    anchor_text: str

    @model_validator(mode="after")
    def validate_location(self) -> "RawEvidenceRef":
        if not self.block_id and not self.evidence_id:
            raise ValueError("RawEvidenceRef requires block_id or evidence_id")
        return self


class RawActorRecord(LLMOutputModel):
    actor_id: str
    display_name: str
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)
    role: ActorRole
    advisor_kind: AdvisorKind | None = None
    bidder_kind: BidderKind | None = None
    listing_status: ListingStatus | None = None
    geography: GeographyFlag | None = None
    is_grouped: bool
    group_size: int | None = None
    group_label: str | None = None
    evidence_refs: list[RawEvidenceRef] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_group_metadata(self) -> "RawActorRecord":
        if self.is_grouped and self.group_size is None and not self.group_label:
            raise ValueError("Grouped actors require group_size or group_label")
        return self


class RawCountAssertion(LLMOutputModel):
    count: int
    subject: Literal[
        "interested_parties",
        "nda_signed_bidders",
        "nda_signed_financial_buyers",
        "nda_signed_strategic_buyers",
        "final_round_invitees",
        "other",
    ]
    qualifier_text: str | None = None
    evidence_refs: list[RawEvidenceRef] = Field(default_factory=list)


class ActorExtractionOutput(LLMOutputModel):
    actors: list[RawActorRecord] = Field(default_factory=list)
    count_assertions: list[RawCountAssertion] = Field(default_factory=list)
    unresolved_mentions: list[str] = Field(default_factory=list)


class RawDateHint(LLMOutputModel):
    raw_text: str
    normalized_hint: str | None = None
    relative_to: str | None = None


class RawMoneyTerms(LLMOutputModel):
    raw_text: str | None = None
    currency: str = "USD"
    value_per_share: Decimal | None = None
    lower_per_share: Decimal | None = None
    upper_per_share: Decimal | None = None
    total_enterprise_value: Decimal | None = None
    is_range: bool = False

    @model_validator(mode="after")
    def validate_amounts(self) -> "RawMoneyTerms":
        if not any(
            value is not None
            for value in (
                self.value_per_share,
                self.lower_per_share,
                self.upper_per_share,
                self.total_enterprise_value,
            )
        ):
            raise ValueError("Money terms require at least one amount")
        if self.is_range and self.lower_per_share is None and self.upper_per_share is None:
            raise ValueError("Range money terms require lower_per_share or upper_per_share")
        return self


class RawFormalitySignals(LLMOutputModel):
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


class RawEventRecord(LLMOutputModel):
    event_type: EventType
    date: RawDateHint
    actor_ids: list[str] = Field(default_factory=list)
    summary: str
    evidence_refs: list[RawEvidenceRef] = Field(default_factory=list)
    terms: RawMoneyTerms | None = None
    consideration_type: ConsiderationType | None = None
    whole_company_scope: bool | None = None
    whole_company_scope_note: str | None = None
    formality_signals: RawFormalitySignals | None = None
    drop_reason_text: str | None = None
    round_scope: Literal["informal", "formal", "extension"] | None = None
    deadline_date: RawDateHint | None = None
    executed_with_actor_id: str | None = None
    boundary_note: str | None = None
    nda_signed: bool = True
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_event_shape(self) -> "RawEventRecord":
        if self.event_type == EventType.PROPOSAL:
            if self.terms is None:
                raise ValueError("Proposal events require terms")
            if self.formality_signals is None:
                raise ValueError("Proposal events require formality_signals")
        if self.event_type in {
            EventType.FINAL_ROUND_INF_ANN,
            EventType.FINAL_ROUND_INF,
            EventType.FINAL_ROUND_ANN,
            EventType.FINAL_ROUND,
            EventType.FINAL_ROUND_EXT_ANN,
            EventType.FINAL_ROUND_EXT,
        } and self.round_scope is None:
            raise ValueError("Round events require round_scope")
        return self


class RawExclusion(LLMOutputModel):
    category: Literal[
        "partial_company_bid",
        "unsigned_nda",
        "stale_process_reference",
        "duplicate_mention",
        "non_event_context",
        "other",
    ]
    block_ids: list[str] = Field(default_factory=list)
    explanation: str


class EventExtractionOutput(LLMOutputModel):
    events: list[RawEventRecord] = Field(default_factory=list)
    exclusions: list[RawExclusion] = Field(default_factory=list)
    unresolved_mentions: list[str] = Field(default_factory=list)
    coverage_notes: list[str] = Field(default_factory=list)


class RecoveryTarget(LLMOutputModel):
    target_type: str
    block_ids: list[str] = Field(default_factory=list)
    reason: str
    anchor_text: str
    suggested_event_types: list[EventType] = Field(default_factory=list)


class RecoveryAuditOutput(LLMOutputModel):
    recovery_targets: list[RecoveryTarget] = Field(default_factory=list)


def pydantic_to_anthropic_schema(model_cls: type[BaseModel]) -> dict[str, Any]:
    schema = model_cls.model_json_schema(mode="validation")
    definitions = deepcopy(schema.pop("$defs", {}))
    return _inline_refs(schema, definitions)


def _inline_refs(value: Any, definitions: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        if "$ref" in value:
            ref = value["$ref"]
            if not ref.startswith("#/$defs/"):
                raise ValueError(f"Unsupported schema reference: {ref}")
            definition_name = ref.removeprefix("#/$defs/")
            resolved = deepcopy(definitions[definition_name])
            return _inline_refs(resolved, definitions)
        return {key: _inline_refs(child, definitions) for key, child in value.items()}
    if isinstance(value, list):
        return [_inline_refs(child, definitions) for child in value]
    return value
```

---

## pipeline/llm/schema_profile.py
```python
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from pipeline.llm.json_utils import inline_json_refs


@dataclass(slots=True)
class SchemaProfile:
    schema_bytes: int
    optional_param_count: int
    union_param_count: int
    pattern_count: int
    object_count: int
    array_count: int
    max_depth: int


def profile_model_schema(model_cls: type[BaseModel]) -> SchemaProfile:
    schema = inline_json_refs(model_cls.model_json_schema(mode="validation"))
    counters = {
        "optional_param_count": 0,
        "union_param_count": 0,
        "pattern_count": 0,
        "object_count": 0,
        "array_count": 0,
        "max_depth": 0,
    }
    _walk_schema(schema, counters, depth=1)
    return SchemaProfile(
        schema_bytes=len(json.dumps(schema, sort_keys=True)),
        optional_param_count=counters["optional_param_count"],
        union_param_count=counters["union_param_count"],
        pattern_count=counters["pattern_count"],
        object_count=counters["object_count"],
        array_count=counters["array_count"],
        max_depth=counters["max_depth"],
    )


def _walk_schema(node: Any, counters: dict[str, int], *, depth: int) -> None:
    if isinstance(node, dict):
        counters["max_depth"] = max(counters["max_depth"], depth)
        if "pattern" in node:
            counters["pattern_count"] += 1
        if "anyOf" in node or "oneOf" in node:
            counters["union_param_count"] += 1
        if node.get("type") == "object" or "properties" in node:
            counters["object_count"] += 1
            required = set(node.get("required", []))
            for key, child in node.get("properties", {}).items():
                if key not in required:
                    counters["optional_param_count"] += 1
                _walk_schema(child, counters, depth=depth + 1)
        if node.get("type") == "array" or "items" in node:
            counters["array_count"] += 1
            _walk_schema(node.get("items"), counters, depth=depth + 1)
        for key, child in node.items():
            if key in {"properties", "items"}:
                continue
            _walk_schema(child, counters, depth=depth + 1)
        return
    if isinstance(node, list):
        for child in node:
            _walk_schema(child, counters, depth=depth + 1)


# These gates are intentionally conservative. The pipeline's production schemas
# should take the provider-neutral prompted-JSON path by default.
ANTHROPIC_NATIVE_MAX_OPTIONAL_PARAMS = 12
ANTHROPIC_NATIVE_MAX_UNION_PARAMS = 8
ANTHROPIC_NATIVE_MAX_SCHEMA_BYTES = 3_000

OPENAI_NATIVE_MAX_OPTIONAL_PARAMS = 20
OPENAI_NATIVE_MAX_UNION_PARAMS = 12
OPENAI_NATIVE_MAX_SCHEMA_BYTES = 4_500


def anthropic_native_safe(profile: SchemaProfile) -> bool:
    return (
        profile.optional_param_count <= ANTHROPIC_NATIVE_MAX_OPTIONAL_PARAMS
        and profile.union_param_count <= ANTHROPIC_NATIVE_MAX_UNION_PARAMS
        and profile.pattern_count == 0
        and profile.schema_bytes <= ANTHROPIC_NATIVE_MAX_SCHEMA_BYTES
        and profile.max_depth <= 8
    )


def openai_native_safe(profile: SchemaProfile) -> bool:
    return (
        profile.optional_param_count <= OPENAI_NATIVE_MAX_OPTIONAL_PARAMS
        and profile.union_param_count <= OPENAI_NATIVE_MAX_UNION_PARAMS
        and profile.pattern_count <= 1
        and profile.schema_bytes <= OPENAI_NATIVE_MAX_SCHEMA_BYTES
        and profile.max_depth <= 10
    )
```
