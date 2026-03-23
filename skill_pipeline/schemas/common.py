from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


SCHEMA_VERSION = "2.0.0"
PIPELINE_VERSION = "0.1.0"


class PipelineModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


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


class QuoteMatchType(StrEnum):
    EXACT = "exact"
    NORMALIZED = "normalized"
    FUZZY = "fuzzy"
    UNRESOLVED = "unresolved"


class ArtifactEnvelope(PipelineModel):
    schema_version: str = SCHEMA_VERSION
    artifact_type: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    pipeline_version: str = PIPELINE_VERSION
    run_id: str
    deal_slug: str | None = None
