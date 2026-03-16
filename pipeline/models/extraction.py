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
