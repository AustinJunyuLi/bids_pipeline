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
