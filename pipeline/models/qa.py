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
