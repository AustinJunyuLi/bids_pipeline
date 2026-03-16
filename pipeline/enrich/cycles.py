from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from pipeline.models.common import ClassificationLabel, EventType
from pipeline.models.enrichment import CycleRecord, ProposalClassification
from pipeline.models.extraction import CycleBoundaryEvent, DealExtraction, ProcessMarkerEvent, ProposalEvent


REINITIATION_EVENT_TYPES = {
    EventType.TARGET_SALE,
    EventType.TARGET_SALE_PUBLIC,
    EventType.BIDDER_SALE,
    EventType.BIDDER_INTEREST,
    EventType.ACTIVIST_SALE,
    EventType.IB_RETENTION,
    EventType.NDA,
}


def assign_event_sequence(extraction: DealExtraction) -> dict[str, int]:
    ordered = sorted(
        enumerate(extraction.events, start=1),
        key=lambda pair: _event_sort_key(pair[1], pair[0]),
    )
    return {event.event_id: ordinal for ordinal, (_original_index, event) in enumerate(ordered, start=1)}


def order_events(extraction: DealExtraction) -> list:
    return sorted(
        extraction.events,
        key=lambda event: _event_sort_key(event, 0),
    )


def segment_cycles(
    extraction: DealExtraction,
    *,
    classifications: dict[str, ProposalClassification] | None = None,
) -> tuple[list[CycleRecord], dict[str, str], dict[str, str | None]]:
    ordered_events = order_events(extraction)
    if not ordered_events:
        return [], {}, {}

    cycles: list[CycleRecord] = []
    event_cycle_map: dict[str, str] = {}
    formal_boundary_event_ids: dict[str, str | None] = {}

    cycle_index = 1
    current_cycle_id = f"cycle-{cycle_index:03d}"
    current_start_event_id = ordered_events[0].event_id
    current_basis = "single_cycle"

    def close_cycle(end_event_id: str | None, *, review_required: bool = False) -> None:
        nonlocal current_cycle_id, current_start_event_id, current_basis
        cycles.append(
            CycleRecord(
                cycle_id=current_cycle_id,
                start_event_id=current_start_event_id,
                end_event_id=end_event_id,
                boundary_basis=current_basis,
                review_required=review_required,
            )
        )
        formal_boundary_event_ids[current_cycle_id] = _first_formal_proposal(
            current_cycle_id,
            ordered_events,
            event_cycle_map,
            classifications or {},
        )

    previous_event = None
    for event in ordered_events:
        # Explicit restart begins a new cycle on the restart event itself.
        if event.event_type == EventType.RESTARTED and previous_event is not None:
            if previous_event.event_id in event_cycle_map and previous_event.event_id != current_start_event_id:
                close_cycle(previous_event.event_id)
            elif previous_event.event_id in event_cycle_map and previous_event.event_id == current_start_event_id:
                close_cycle(previous_event.event_id)
            cycle_index += 1
            current_cycle_id = f"cycle-{cycle_index:03d}"
            current_start_event_id = event.event_id
            current_basis = "explicit_terminated_restarted"

        elif previous_event is not None and _should_infer_new_cycle(previous_event, event):
            close_cycle(previous_event.event_id, review_required=True)
            cycle_index += 1
            current_cycle_id = f"cycle-{cycle_index:03d}"
            current_start_event_id = event.event_id
            current_basis = "implicit_reinitiation_after_gap"

        event_cycle_map[event.event_id] = current_cycle_id
        if event.event_type == EventType.TERMINATED:
            current_basis = "explicit_terminated_restarted"

        previous_event = event

    close_cycle(ordered_events[-1].event_id)
    return cycles, event_cycle_map, formal_boundary_event_ids


def _event_sort_key(event, original_index: int) -> tuple[date, int, int]:
    sort_date = event.date.sort_date or event.date.normalized_start or date.max
    start_line = 10**9
    if event.primary_span_ids:
        # Event sequence has already been preserved in input ordering; line-based sorting is handled in QA/export.
        start_line = original_index
    return (sort_date, start_line, original_index)


def _should_infer_new_cycle(previous_event, event) -> bool:
    prev_date = previous_event.date.sort_date or previous_event.date.normalized_start
    curr_date = event.date.sort_date or event.date.normalized_start
    if prev_date is None or curr_date is None:
        return False
    gap_days = (curr_date - prev_date).days
    if gap_days < 180:
        return False
    return event.event_type in REINITIATION_EVENT_TYPES


def _first_formal_proposal(
    cycle_id: str,
    ordered_events: Iterable,
    event_cycle_map: dict[str, str],
    classifications: dict[str, ProposalClassification],
) -> str | None:
    for event in ordered_events:
        if event_cycle_map.get(event.event_id) != cycle_id:
            continue
        if not isinstance(event, ProposalEvent):
            continue
        classification = classifications.get(event.event_id)
        if classification and classification.label == ClassificationLabel.FORMAL:
            return event.event_id
    return None
