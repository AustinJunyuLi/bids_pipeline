from __future__ import annotations

from pipeline.models.common import EventType, ReviewSeverity
from pipeline.models.extraction import DealExtraction
from pipeline.models.qa import QAFinding
from pipeline.models.source import EvidenceItem


def compute_completeness_metrics(
    extraction: DealExtraction,
    *,
    evidence_items: list[EvidenceItem],
) -> tuple[dict[str, int | bool], list[QAFinding]]:
    proposal_count = sum(1 for event in extraction.events if event.event_type == EventType.PROPOSAL)
    nda_count = sum(1 for event in extraction.events if event.event_type == EventType.NDA)
    outcome_count = sum(
        1
        for event in extraction.events
        if event.event_type in {EventType.EXECUTED, EventType.TERMINATED}
    )
    financial_item_count = sum(1 for item in evidence_items if item.evidence_type.value == "financial_term")
    process_item_count = sum(1 for item in evidence_items if item.evidence_type.value == "process_signal")
    unresolved_span_count = sum(1 for span in extraction.spans if span.match_type.value == "unresolved")

    findings: list[QAFinding] = []
    if proposal_count == 0 and financial_item_count > 0:
        findings.append(
            QAFinding(
                finding_id="qa-missing-proposal",
                severity=ReviewSeverity.WARNING,
                code="missing_proposal_events",
                message="Financial evidence items were detected but no proposal events were extracted.",
                review_required=True,
            )
        )
    if nda_count == 0 and process_item_count > 0:
        findings.append(
            QAFinding(
                finding_id="qa-missing-nda",
                severity=ReviewSeverity.WARNING,
                code="missing_nda_events",
                message="Process evidence items were detected but no NDA events were extracted.",
                review_required=True,
            )
        )
    if outcome_count == 0:
        findings.append(
            QAFinding(
                finding_id="qa-missing-outcome",
                severity=ReviewSeverity.WARNING,
                code="missing_outcome_event",
                message="No executed or terminated outcome event was extracted.",
                review_required=True,
            )
        )
    if unresolved_span_count:
        findings.append(
            QAFinding(
                finding_id="qa-unresolved-spans",
                severity=ReviewSeverity.BLOCKER,
                code="unresolved_spans_present",
                message="One or more evidence spans could not be resolved exactly.",
                related_span_ids=[span.span_id for span in extraction.spans if span.match_type.value == "unresolved"],
                review_required=True,
            )
        )

    return {
        "actor_count": len(extraction.actors),
        "event_count": len(extraction.events),
        "proposal_count": proposal_count,
        "nda_count": nda_count,
        "outcome_count": outcome_count,
        "financial_evidence_item_count": financial_item_count,
        "process_evidence_item_count": process_item_count,
        "unresolved_span_count": unresolved_span_count,
        "passes_basic_completeness": outcome_count > 0 and proposal_count > 0,
    }, findings
