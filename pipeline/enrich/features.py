from __future__ import annotations

from datetime import date

from pipeline.models.common import ActorRole, ClassificationLabel
from pipeline.models.enrichment import CycleRecord, DerivedMetrics, ProposalClassification
from pipeline.models.extraction import DealExtraction, NDAEvent, ProposalEvent


def compute_derived_metrics(
    extraction: DealExtraction,
    *,
    classifications: dict[str, ProposalClassification],
    cycles: list[CycleRecord],
    event_cycle_map: dict[str, str],
) -> DerivedMetrics:
    bidder_actors = [actor for actor in extraction.actors if actor.role == ActorRole.BIDDER]
    named_bidders = [actor for actor in bidder_actors if not actor.is_grouped]
    grouped_bidders = [actor for actor in bidder_actors if actor.is_grouped]

    proposal_events = [event for event in extraction.events if isinstance(event, ProposalEvent)]
    nda_events = [event for event in extraction.events if isinstance(event, NDAEvent)]

    formal_count = sum(
        1
        for event in proposal_events
        if classifications.get(event.event_id)
        and classifications[event.event_id].label == ClassificationLabel.FORMAL
    )
    informal_count = sum(
        1
        for event in proposal_events
        if classifications.get(event.event_id)
        and classifications[event.event_id].label == ClassificationLabel.INFORMAL
    )

    duration_days = _duration_days(extraction)
    peak_active_bidders = _peak_active_bidders(extraction)

    return DerivedMetrics(
        unique_bidders_total=len(bidder_actors),
        unique_bidders_named=len(named_bidders),
        unique_bidders_grouped=len(grouped_bidders),
        peak_active_bidders=peak_active_bidders,
        proposal_count_total=len(proposal_events),
        proposal_count_formal=formal_count,
        proposal_count_informal=informal_count,
        nda_count=len(nda_events),
        duration_days=duration_days,
        cycle_count=len(cycles),
    )


def _duration_days(extraction: DealExtraction) -> int | None:
    dated_events = [
        event.date.sort_date or event.date.normalized_start
        for event in extraction.events
        if event.date.sort_date is not None or event.date.normalized_start is not None
    ]
    if not dated_events:
        return None
    return (max(dated_events) - min(dated_events)).days


def _peak_active_bidders(extraction: DealExtraction) -> int | None:
    active: set[str] = set()
    peak = 0
    ordered = sorted(
        extraction.events,
        key=lambda event: (event.date.sort_date or event.date.normalized_start or date.max, event.event_id),
    )
    for event in ordered:
        for actor_id in event.actor_ids:
            active.add(actor_id)
        peak = max(peak, len(active))
    return peak or None
