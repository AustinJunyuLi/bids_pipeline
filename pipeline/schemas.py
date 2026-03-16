from enum import StrEnum

from pydantic import BaseModel


class ActorType(StrEnum):
    BIDDER = "bidder"
    ADVISOR = "advisor"
    ACTIVIST = "activist"
    TARGET_BOARD = "target_board"


class BidderSubtype(StrEnum):
    STRATEGIC = "strategic"
    FINANCIAL = "financial"
    NON_US = "non_us"


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


class EventEvidence(BaseModel):
    preceded_by_process_letter: bool | None = None
    accompanied_by_merger_agreement: bool | None = None
    post_final_round: bool | None = None
    filing_language: str | None = None


class Actor(BaseModel):
    actor_id: str
    name: str
    aliases: list[str]
    actor_type: ActorType
    bidder_subtype: BidderSubtype | None = None
    is_grouped: bool
    group_size: int | None = None
    source_quote: str


class ActorExtraction(BaseModel):
    actors: list[Actor]
    count_assertions: list[str]


class Event(BaseModel):
    event_id: str
    event_type: EventType
    date: str
    date_normalized: str | None = None
    actor_ids: list[str]
    value: float | None = None
    value_lower: float | None = None
    value_upper: float | None = None
    consideration_type: str | None = None
    evidence: EventEvidence
    source_quote: str
    note: str | None = None


class DealMetadata(BaseModel):
    target_name: str
    acquirer: str | None = None
    deal_outcome: str | None = None
    date_announced: str | None = None
    date_effective: str | None = None
    consideration_type: str | None = None


class EventExtraction(BaseModel):
    events: list[Event]
    deal_metadata: DealMetadata


class EnrichedEvent(BaseModel):
    """Event with classification and cycle info appended."""

    event: Event
    bid_type: str | None = None
    classification_rule: str | None = None
    cycle_id: str | None = None


class Enrichment(BaseModel):
    enriched_events: list[EnrichedEvent]
    initiation_type: str | None = None
    formal_boundary_event_id: str | None = None


class ChronologyBookmark(BaseModel):
    accession_number: str
    heading: str
    start_line: int
    end_line: int
    confidence: str | None = None
    selection_basis: str | None = None


class FilingRecord(BaseModel):
    filing_type: str
    accession_number: str | None = None
    filing_date: str | None = None
    url: str | None = None
    disposition: str
    html_path: str | None = None
    txt_path: str | None = None


class FilingManifest(BaseModel):
    deal_slug: str
    cik: str | None = None
    target_name: str
    filings: list[FilingRecord]


class DealStatus(BaseModel):
    status: str
    last_stage: str | None = None
    cost_usd: float = 0.0
    events_extracted: int = 0
    actors_extracted: int = 0
    error: str | None = None
    timestamp: str | None = None
