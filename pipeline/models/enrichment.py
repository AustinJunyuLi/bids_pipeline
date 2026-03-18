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


class InitiationJudgment(PipelineModel):
    type: Literal["target_driven", "bidder_driven", "activist_driven", "mixed"]
    basis: str
    source_text: str
    confidence: Literal["high", "medium", "low"]


class DealEnrichment(ArtifactEnvelope):
    artifact_type: str = "deal_enrichment"
    classifications: dict[str, ProposalClassification] = Field(default_factory=dict)
    cycles: list[CycleRecord] = Field(default_factory=list)
    event_sequence: dict[str, int] = Field(default_factory=dict)
    event_cycle_map: dict[str, str] = Field(default_factory=dict)
    formal_boundary_event_ids: dict[str, str | None] = Field(default_factory=dict)
    derived_metrics: DerivedMetrics
    initiation_judgment: InitiationJudgment | None = None
