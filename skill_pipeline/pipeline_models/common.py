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
