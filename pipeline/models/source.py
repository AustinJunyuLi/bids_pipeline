from datetime import date, datetime
from typing import Any, Literal

from pydantic import Field

from pipeline.models.common import ArtifactEnvelope, PipelineModel


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
