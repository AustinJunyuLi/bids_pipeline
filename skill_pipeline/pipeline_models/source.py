from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field

from skill_pipeline.pipeline_models.common import ArtifactEnvelope, DatePrecision, PipelineModel


class BlockDateMention(PipelineModel):
    raw_text: str
    normalized: str | None
    precision: DatePrecision


class BlockEntityMention(PipelineModel):
    raw_text: str
    entity_type: Literal["target", "acquirer", "party_alias", "committee"]


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
    date_mentions: list[BlockDateMention]
    entity_mentions: list[BlockEntityMention]
    evidence_density: int
    temporal_phase: Literal["initiation", "bidding", "outcome", "other"]


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
    actor_hints: list[str] = Field(default_factory=list)
    count_hint: str | None = None
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
