from __future__ import annotations

from collections import defaultdict

from pipeline.models.enrichment import DealEnrichment
from pipeline.models.export import ReviewRow
from pipeline.models.extraction import DealExtraction, ProposalEvent
from pipeline.models.qa import QAReport


def flatten_review_rows(
    extraction: DealExtraction,
    enrichment: DealEnrichment,
    qa_report: QAReport,
) -> list[ReviewRow]:
    actor_lookup = {actor.actor_id: actor for actor in extraction.actors}
    span_lookup = {span.span_id: span for span in extraction.spans}
    event_flags = _event_flags(qa_report)
    rows: list[ReviewRow] = []

    ordered_events = sorted(
        extraction.events,
        key=lambda event: enrichment.event_sequence.get(event.event_id, 10**9),
    )

    for event in ordered_events:
        span = _primary_span(event.primary_span_ids, span_lookup)
        classification = enrichment.classifications.get(event.event_id)
        actor_ids = event.actor_ids or [None]
        for actor_id in actor_ids:
            actor = actor_lookup.get(actor_id) if actor_id else None
            row = ReviewRow(
                deal_slug=extraction.deal_slug or "",
                target_name=extraction.seed.target_name,
                event_sequence=enrichment.event_sequence.get(event.event_id, 0),
                cycle_id=enrichment.event_cycle_map.get(event.event_id),
                event_id=event.event_id,
                event_type=event.event_type.value,
                actor_id=actor_id,
                actor_name=actor.display_name if actor else None,
                actor_role=actor.role.value if actor else None,
                bidder_kind=actor.bidder_kind.value if actor and actor.bidder_kind else None,
                listing_status=actor.listing_status.value if actor and actor.listing_status else None,
                geography=actor.geography.value if actor and actor.geography else None,
                raw_date=event.date.raw_text,
                sort_date=event.date.sort_date,
                value_per_share=event.terms.value_per_share if isinstance(event, ProposalEvent) else None,
                lower_per_share=event.terms.lower_per_share if isinstance(event, ProposalEvent) else None,
                upper_per_share=event.terms.upper_per_share if isinstance(event, ProposalEvent) else None,
                consideration_type=event.consideration_type.value if isinstance(event, ProposalEvent) else None,
                proposal_classification=classification.label.value if classification else None,
                classification_rule=classification.rule_id if classification else None,
                accession_number=span.accession_number if span else None,
                filing_type=span.filing_type if span else None,
                source_lines=_source_lines(span),
                source_quote_full=span.quote_text if span else "",
                qa_flags=event_flags.get(event.event_id, []),
            )
            rows.append(row)
    return rows


def _primary_span(primary_span_ids, span_lookup):
    for span_id in primary_span_ids:
        span = span_lookup.get(span_id)
        if span is not None:
            return span
    return None


def _source_lines(span) -> str:
    if span is None:
        return ""
    if span.start_line == span.end_line:
        return f"L{span.start_line}"
    return f"L{span.start_line}-L{span.end_line}"


def _event_flags(report: QAReport) -> dict[str, list[str]]:
    flags: dict[str, list[str]] = defaultdict(list)
    for finding in report.findings:
        targets = finding.related_event_ids or []
        for event_id in targets:
            flags[event_id].append(finding.code)
    return flags
