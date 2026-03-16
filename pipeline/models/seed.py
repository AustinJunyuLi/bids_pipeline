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
