from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import date
from pathlib import Path
from typing import Iterable

from pipeline.schemas import (
    BidClassification,
    DealState,
    Decision,
    Event,
    EventActorLink,
    FormalBoundary,
    Initiation,
    Judgment,
    ProcessCycle,
    Round,
    Stage3Result,
)


logger = logging.getLogger(__name__)


_EVENT_SORT_PRIORITY: dict[str, int] = {
    "activist_sale": 0,
    "target_sale": 1,
    "target_sale_public": 2,
    "sale_press_release": 3,
    "bidder_sale": 4,
    "bidder_interest": 5,
    "bid_press_release": 6,
    "ib_retention": 7,
    "final_round_inf_ann": 8,
    "final_round_inf": 9,
    "final_round_ann": 10,
    "final_round": 11,
    "final_round_ext_ann": 12,
    "final_round_ext": 13,
    "nda": 14,
    "proposal": 15,
    "drop_target": 16,
    "drop": 17,
    "drop_below_m": 18,
    "drop_below_inf": 19,
    "drop_at_inf": 20,
    "executed": 21,
    "terminated": 22,
    "restarted": 23,
}

_DROP_EVENT_TYPES: set[str] = {
    "drop",
    "drop_below_m",
    "drop_below_inf",
    "drop_at_inf",
    "drop_target",
}

_ROUND_PAIR_MAP: dict[str, str] = {
    "final_round_inf_ann": "final_round_inf",
    "final_round_ann": "final_round",
    "final_round_ext_ann": "final_round_ext",
}

_ROUND_PAIR_REVERSE_MAP: dict[str, str] = {value: key for key, value in _ROUND_PAIR_MAP.items()}


def _parse_iso_date(value: str) -> date:
    """Parse an ISO date string into a ``date`` object."""

    year_str, month_str, day_str = value.split("-")
    return date(int(year_str), int(month_str), int(day_str))


def _event_sort_key(event: Event) -> tuple[date, int, int, str]:
    """Return a stable sort key for chronology events."""

    return (
        _parse_iso_date(event.date),
        event.source_line_start,
        _EVENT_SORT_PRIORITY.get(event.event_type, 999),
        event.event_id,
    )


def _sorted_events(events: Iterable[Event]) -> list[Event]:
    """Return events sorted into a deterministic chronology order."""

    return sorted(events, key=_event_sort_key)


def _jsonl_dump_lines(rows: Iterable[object]) -> str:
    """Serialize Pydantic rows to deterministic JSONL text."""

    serialized: list[str] = []
    for row in rows:
        if hasattr(row, "model_dump"):
            payload: object = row.model_dump(mode="json")
        else:
            payload = row
        serialized.append(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return "\n".join(serialized) + ("\n" if serialized else "")


def _atomic_write_text(path: Path, text: str) -> None:
    """Write text atomically to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor: int
    tmp_path_str: str
    file_descriptor, tmp_path_str = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp_path: Path = Path(tmp_path_str)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def _load_existing_decisions(path: Path) -> list[Decision]:
    """Load any existing append-only decision records from disk."""

    if not path.exists():
        return []
    decisions: list[Decision] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line: str = raw_line.strip()
            if not line:
                continue
            decisions.append(Decision.model_validate_json(line))
    return decisions


def _write_decisions(path: Path, decisions: list[Decision]) -> None:
    """Persist the complete append-only decision log atomically."""

    _atomic_write_text(path, _jsonl_dump_lines(decisions))


def _find_event_indexes(events: list[Event]) -> dict[str, int]:
    """Return a mapping from event identifier to its sorted position."""

    return {event.event_id: index for index, event in enumerate(events)}


def _events_between(events: list[Event], start_event_id: str, end_event_id: str) -> list[Event]:
    """Return the sorted event slice between two inclusive boundary event identifiers."""

    index_map: dict[str, int] = _find_event_indexes(events)
    if start_event_id not in index_map or end_event_id not in index_map:
        return []
    start_index: int = index_map[start_event_id]
    end_index: int = index_map[end_event_id]
    if end_index < start_index:
        return []
    return events[start_index : end_index + 1]


def segment_cycles(events: list[Event], deal_slug: str) -> list[ProcessCycle]:
    """Segment a deal chronology into one or more process cycles.

    Cycles are primarily split by explicit ``terminated`` and ``restarted`` events. In the
    common single-cycle case, the full chronology is assigned to one cycle. Earlier cycles
    ending in ``terminated`` are marked terminated, while a final cycle is marked completed
    when it contains ``executed`` and withdrawn otherwise.
    """

    ordered_events: list[Event] = _sorted_events(events)
    if not ordered_events:
        return []

    restart_indexes: set[int] = {
        index
        for index, event in enumerate(ordered_events)
        if event.event_type == "restarted"
    }
    cycles: list[ProcessCycle] = []
    cycle_start_index: int = 0
    cycle_sequence: int = 1

    for index, event in enumerate(ordered_events):
        if event.event_type != "terminated":
            continue
        cycle_events: list[Event] = ordered_events[cycle_start_index : index + 1]
        if not cycle_events:
            continue
        segmentation_basis: str
        if cycle_start_index == 0:
            segmentation_basis = (
                f"Cycle 1 starts at the earliest extracted event and ends at explicit termination event {event.event_id}."
            )
        else:
            segmentation_basis = (
                f"Cycle {cycle_sequence} starts after explicit restart and ends at explicit termination event {event.event_id}."
            )
        cycles.append(
            ProcessCycle(
                cycle_id=f"{deal_slug}_c{cycle_sequence}",
                cycle_sequence=cycle_sequence,
                start_event_id=cycle_events[0].event_id,
                end_event_id=cycle_events[-1].event_id,
                status="terminated",
                segmentation_basis=segmentation_basis,
                rounds=[],
            )
        )
        cycle_sequence += 1
        next_restart_index: int | None = None
        for candidate_index in range(index + 1, len(ordered_events)):
            if candidate_index in restart_indexes:
                next_restart_index = candidate_index
                break
        if next_restart_index is None:
            cycle_start_index = len(ordered_events)
            break
        cycle_start_index = next_restart_index

    if cycle_start_index < len(ordered_events):
        final_cycle_events: list[Event] = ordered_events[cycle_start_index:]
        final_status: str
        if any(event.event_type == "executed" for event in final_cycle_events):
            final_status = "completed"
        elif any(event.event_type == "terminated" for event in final_cycle_events):
            final_status = "terminated"
        else:
            final_status = "withdrawn"
        if cycle_start_index == 0:
            basis = "No terminated and restarted boundary was found; the entire chronology forms a single cycle."
        else:
            basis = (
                f"Cycle {cycle_sequence} begins at explicit restart event {final_cycle_events[0].event_id} "
                "and runs through the end of the extracted chronology."
            )
        cycles.append(
            ProcessCycle(
                cycle_id=f"{deal_slug}_c{cycle_sequence}",
                cycle_sequence=cycle_sequence,
                start_event_id=final_cycle_events[0].event_id,
                end_event_id=final_cycle_events[-1].event_id,
                status=final_status,
                segmentation_basis=basis,
                rounds=[],
            )
        )

    if not cycles:
        only_events: list[Event] = ordered_events
        status: str = "completed" if any(event.event_type == "executed" for event in only_events) else "withdrawn"
        cycles.append(
            ProcessCycle(
                cycle_id=f"{deal_slug}_c1",
                cycle_sequence=1,
                start_event_id=only_events[0].event_id,
                end_event_id=only_events[-1].event_id,
                status=status,
                segmentation_basis="Fallback single-cycle segmentation applied because no explicit boundary events were found.",
                rounds=[],
            )
        )
    return cycles


def build_rounds(events: list[Event], links: list[EventActorLink], cycle: ProcessCycle) -> list[Round]:
    """Build round objects for a process cycle using announcement-deadline pairs.

    Round invitations are inferred from event-actor links attached to the announcement and
    matching deadline events. Pairing is done sequentially within the cycle.
    """

    ordered_events: list[Event] = _sorted_events(events)
    cycle_events: list[Event] = _events_between(ordered_events, cycle.start_event_id, cycle.end_event_id)
    if not cycle_events:
        return []

    links_by_event_id: dict[str, list[EventActorLink]] = {}
    for link in links:
        links_by_event_id.setdefault(link.event_id, []).append(link)

    pending_announcements: dict[str, list[Event]] = {announcement_type: [] for announcement_type in _ROUND_PAIR_MAP}
    rounds: list[Round] = []
    deal_round_prefix: str = cycle.cycle_id.rsplit("_c", maxsplit=1)[0]
    round_sequence: int = 1

    for event in cycle_events:
        if event.event_type in _ROUND_PAIR_MAP:
            pending_announcements[event.event_type].append(event)
            continue
        if event.event_type not in _ROUND_PAIR_REVERSE_MAP:
            continue
        announcement_type: str = _ROUND_PAIR_REVERSE_MAP[event.event_type]
        if not pending_announcements[announcement_type]:
            continue
        announcement_event: Event = pending_announcements[announcement_type].pop(0)
        invited_actor_ids: set[str] = {
            link.actor_id
            for link in links_by_event_id.get(announcement_event.event_id, [])
            if link.actor_id
        }
        invited_actor_ids.update(
            {
                link.actor_id
                for link in links_by_event_id.get(event.event_id, [])
                if link.actor_id
            }
        )
        rounds.append(
            Round(
                round_id=f"{deal_round_prefix}_r{round_sequence}",
                announcement_event_id=announcement_event.event_id,
                deadline_event_id=event.event_id,
                invited_set=sorted(invited_actor_ids),
                source_text=announcement_event.source_text,
            )
        )
        round_sequence += 1

    return rounds


def classify_bid(proposal: Event, events: list[Event], links: list[EventActorLink]) -> BidClassification:
    """Classify a proposal event as formal or informal using the four-rule cascade.

    Rules are applied in the documented priority order:
      1. proposal after a final formal round announcement => formal
      2. accompanied by a merger agreement draft => formal
      3. filing language indicates an indication of interest or value range => informal
      4. default prior => informal
    """

    del links
    ordered_events: list[Event] = _sorted_events(events)
    formal_round_announcements: list[Event] = [
        event for event in ordered_events if event.event_type in {"final_round_ann", "final_round_ext_ann"}
    ]
    proposal_date: date = _parse_iso_date(proposal.date)
    rule_1_matches: list[Event] = []
    for announcement in formal_round_announcements:
        announcement_date: date = _parse_iso_date(announcement.date)
        if proposal_date > announcement_date:
            rule_1_matches.append(announcement)
            continue
        if proposal_date == announcement_date and proposal.source_line_start > announcement.source_line_start:
            rule_1_matches.append(announcement)
    if rule_1_matches:
        return BidClassification(
            judgment_type="bid_classification",
            scope="event",
            scope_id=proposal.event_id,
            value="formal",
            classification_rule="post_final_round_announcement",
            confidence="high",
        )

    if proposal.evidence_attributes and proposal.evidence_attributes.accompanied_by_merger_agreement is True:
        return BidClassification(
            judgment_type="bid_classification",
            scope="event",
            scope_id=proposal.event_id,
            value="formal",
            classification_rule="merger_agreement_draft",
            confidence="high",
        )

    filing_language: str = ""
    if proposal.evidence_attributes and proposal.evidence_attributes.filing_language:
        filing_language = proposal.evidence_attributes.filing_language.lower()
    if "indication of interest" in filing_language or (
        proposal.value_lower is not None and proposal.value_upper is not None
    ):
        confidence: str = "high" if "indication of interest" in filing_language else "medium"
        return BidClassification(
            judgment_type="bid_classification",
            scope="event",
            scope_id=proposal.event_id,
            value="informal",
            classification_rule="indication_or_range",
            confidence=confidence,
        )

    return BidClassification(
        judgment_type="bid_classification",
        scope="event",
        scope_id=proposal.event_id,
        value="informal",
        classification_rule="default_informal",
        confidence="medium",
    )


def determine_formal_boundary(
    proposals: list[Event],
    classifications: dict[str, BidClassification],
    events: list[Event],
) -> FormalBoundary | None:
    """Determine the formal-boundary judgment for the deal.

    The chosen event is the nearest final-round announcement preceding the first formal
    proposal when such an announcement exists. When no explicit round announcement is
    available, the first formal proposal itself becomes the boundary. Deals with no formal
    proposals return ``None`` and should be materialized by the caller as a null boundary
    judgment if desired.
    """

    ordered_proposals: list[Event] = _sorted_events(proposals)
    ordered_events: list[Event] = _sorted_events(events)
    informal_proposals: list[Event] = [
        proposal for proposal in ordered_proposals if classifications.get(proposal.event_id, None) and classifications[proposal.event_id].value == "informal"
    ]
    formal_proposals: list[Event] = [
        proposal for proposal in ordered_proposals if classifications.get(proposal.event_id, None) and classifications[proposal.event_id].value == "formal"
    ]
    if not formal_proposals:
        return None

    first_formal: Event = formal_proposals[0]
    last_informal_before_first_formal: Event | None = None
    for proposal in informal_proposals:
        if _event_sort_key(proposal) < _event_sort_key(first_formal):
            last_informal_before_first_formal = proposal

    candidate_announcements: list[Event] = [
        event
        for event in ordered_events
        if event.event_type in {"final_round_ann", "final_round_ext_ann"}
        and _event_sort_key(event) <= _event_sort_key(first_formal)
    ]
    if last_informal_before_first_formal is not None:
        candidate_announcements = [
            event
            for event in candidate_announcements
            if _event_sort_key(event) >= _event_sort_key(last_informal_before_first_formal)
        ] or candidate_announcements

    if candidate_announcements:
        boundary_event: Event = candidate_announcements[-1]
        basis: str
        confidence: Literal["high", "medium", "low"]
        if last_informal_before_first_formal is not None:
            basis = (
                f"The last informal proposal occurs at {last_informal_before_first_formal.event_id}, and the next explicit formal-round announcement "
                f"before the first formal proposal is {boundary_event.event_id}."
            )
            confidence = "high"
        else:
            basis = (
                f"The earliest formal proposal is {first_formal.event_id}, and explicit formal-round announcement {boundary_event.event_id} "
                "is the closest trigger preceding it."
            )
            confidence = "medium"
        alternative_value: str | None = first_formal.event_id if boundary_event.event_id != first_formal.event_id else None
        alternative_basis: str | None = None
        if alternative_value is not None:
            alternative_basis = (
                "A defensible alternative is the first formal proposal itself when the announcement-to-submission transition is compressed."
            )
        return FormalBoundary(
            judgment_type="formal_boundary",
            scope="deal",
            scope_id="",
            value=boundary_event.event_id,
            basis=basis,
            source_text=boundary_event.source_text,
            confidence=confidence,
            alternative_value=alternative_value,
            alternative_basis=alternative_basis,
        )

    basis = "No explicit formal-round announcement precedes the first formal proposal, so the first formal proposal itself is used as the boundary."
    alternative_basis = None
    alternative_value = None
    if last_informal_before_first_formal is not None:
        alternative_basis = (
            f"A softer alternative is the last informal proposal {last_informal_before_first_formal.event_id}, reflecting a gradual transition zone."
        )
        alternative_value = last_informal_before_first_formal.event_id
    return FormalBoundary(
        judgment_type="formal_boundary",
        scope="deal",
        scope_id="",
        value=first_formal.event_id,
        basis=basis,
        source_text=first_formal.source_text,
        confidence="low",
        alternative_value=alternative_value,
        alternative_basis=alternative_basis,
    )


def determine_initiation(events: list[Event], links: list[EventActorLink]) -> Initiation:
    """Determine the initiation judgment for the deal.

    Initiation is anchored on the earliest qualifying initiation event among target-driven,
    bidder-driven, and activist-driven signals. If multiple categories appear tied at the
    earliest point in the chronology, the deal is classified as mixed.
    """

    links_by_event_id: dict[str, list[EventActorLink]] = {}
    for link in links:
        links_by_event_id.setdefault(link.event_id, []).append(link)

    qualifying_events: list[Event] = [
        event
        for event in _sorted_events(events)
        if event.event_type in {"target_sale", "bidder_sale", "activist_sale", "bidder_interest"}
    ]
    if not qualifying_events:
        return Initiation(
            judgment_type="initiation",
            scope="deal",
            scope_id="",
            value="mixed",
            basis="No canonical initiation event exists in the extracted chronology; initiation remains indeterminate and is conservatively labeled mixed.",
            source_text="",
            confidence="low",
            alternative_value=None,
            alternative_basis=None,
        )

    def category_for_event(event: Event) -> str:
        if event.event_type == "target_sale":
            return "target_driven"
        if event.event_type in {"bidder_sale", "bidder_interest"}:
            return "bidder_driven"
        return "activist_driven"

    earliest_event: Event = qualifying_events[0]
    earliest_key: tuple[date, int, int, str] = _event_sort_key(earliest_event)
    tied_earliest_events: list[Event] = [
        event for event in qualifying_events if _event_sort_key(event)[:2] == earliest_key[:2]
    ]
    tied_categories: set[str] = {category_for_event(event) for event in tied_earliest_events}
    if len(tied_categories) > 1:
        values_text: str = ", ".join(sorted(tied_categories))
        return Initiation(
            judgment_type="initiation",
            scope="deal",
            scope_id="",
            value="mixed",
            basis=(
                f"Multiple initiation categories occur at the earliest chronology point on {earliest_event.date}: {values_text}."
            ),
            source_text=earliest_event.source_text,
            confidence="medium",
            alternative_value=None,
            alternative_basis=None,
        )

    selected_value: Literal["target_driven", "bidder_driven", "activist_driven", "mixed"] = category_for_event(earliest_event)
    actor_ids: list[str] = sorted(
        {
            link.actor_id
            for link in links_by_event_id.get(earliest_event.event_id, [])
            if link.participation_role in {"initiator", "bidder", "counterparty"} and link.actor_id
        }
    )
    actor_fragment: str = f" involving {', '.join(actor_ids)}" if actor_ids else ""
    basis: str = (
        f"The earliest qualifying initiation event is {earliest_event.event_type} on {earliest_event.date}{actor_fragment}."
    )
    alternative_value: Literal["target_driven", "bidder_driven", "activist_driven", "mixed"] | None = None
    alternative_basis: str | None = None
    later_categories: list[str] = []
    for event in qualifying_events[1:]:
        later_category: str = category_for_event(event)
        if later_category != selected_value and later_category not in later_categories:
            later_categories.append(later_category)
    if later_categories:
        alternative_value = later_categories[0]  # type: ignore[assignment]
        alternative_basis = (
            f"A secondary interpretation could emphasize later {later_categories[0]} signals that appear after the earliest initiating event."
        )
    confidence: Literal["high", "medium", "low"] = "high" if not tied_earliest_events[1:] else "medium"
    return Initiation(
        judgment_type="initiation",
        scope="deal",
        scope_id="",
        value=selected_value,
        basis=basis,
        source_text=earliest_event.source_text,
        confidence=confidence,
        alternative_value=alternative_value,
        alternative_basis=alternative_basis,
    )


def _event_to_cycle_map(events: list[Event], cycles: list[ProcessCycle]) -> dict[str, ProcessCycle]:
    """Map each event identifier to its containing process cycle."""

    ordered_events: list[Event] = _sorted_events(events)
    index_map: dict[str, int] = _find_event_indexes(ordered_events)
    mapping: dict[str, ProcessCycle] = {}
    for cycle in cycles:
        if cycle.start_event_id not in index_map or cycle.end_event_id not in index_map:
            continue
        start_index: int = index_map[cycle.start_event_id]
        end_index: int = index_map[cycle.end_event_id]
        for event in ordered_events[start_index : end_index + 1]:
            mapping[event.event_id] = cycle
    return mapping


def _proposal_rule_conflicts(proposal: Event, cycle_events: list[Event]) -> list[str]:
    """Return a list of multiple matching rule labels for a proposal, when applicable."""

    matches: list[str] = []
    proposal_date: date = _parse_iso_date(proposal.date)
    for announcement in cycle_events:
        if announcement.event_type not in {"final_round_ann", "final_round_ext_ann"}:
            continue
        announcement_date: date = _parse_iso_date(announcement.date)
        if proposal_date > announcement_date or (
            proposal_date == announcement_date and proposal.source_line_start > announcement.source_line_start
        ):
            matches.append("post_final_round_announcement")
            break
    if proposal.evidence_attributes and proposal.evidence_attributes.accompanied_by_merger_agreement is True:
        matches.append("merger_agreement_draft")
    filing_language: str = ""
    if proposal.evidence_attributes and proposal.evidence_attributes.filing_language:
        filing_language = proposal.evidence_attributes.filing_language.lower()
    if "indication of interest" in filing_language or (
        proposal.value_lower is not None and proposal.value_upper is not None
    ):
        matches.append("indication_or_range")
    return matches


def run_stage3(deal_state: DealState) -> Stage3Result:
    """Run deterministic enrichment for cycle segmentation and bid classification.

    The function writes ``process_cycles.jsonl`` and ``judgments.jsonl`` to the deal's
    enrichment directory, and appends any new deterministic decisions to the shared
    ``decisions.jsonl`` log in the extraction directory.
    """

    logger.info("stage3 starting deal_slug=%s", deal_state.deal_slug)
    events: list[Event] = _sorted_events(deal_state.events)
    links: list[EventActorLink] = sorted(
        deal_state.event_actor_links,
        key=lambda link: (link.event_id, link.actor_id, link.participation_role),
    )
    cycles: list[ProcessCycle] = segment_cycles(events, deal_state.deal_slug)
    cycle_event_map: dict[str, ProcessCycle] = _event_to_cycle_map(events, cycles)

    enriched_cycles: list[ProcessCycle] = []
    stage_decisions: list[Decision] = []
    for cycle in cycles:
        rounds: list[Round] = build_rounds(events, links, cycle)
        enriched_cycle: ProcessCycle = cycle.model_copy(update={"rounds": rounds})
        enriched_cycles.append(enriched_cycle)
        if cycle.cycle_sequence > 1:
            stage_decisions.append(
                Decision(
                    skill="stage3_enrichment",
                    decision_type="cycle_boundary",
                    detail=cycle.segmentation_basis,
                    artifact_affected="enrichment/process_cycles.jsonl",
                    target_id=cycle.cycle_id,
                    confidence="high" if "explicit" in cycle.segmentation_basis.lower() else "medium",
                )
            )

    bid_classifications: list[BidClassification] = []
    proposal_events: list[Event] = [event for event in events if event.event_type == "proposal"]
    for proposal in proposal_events:
        containing_cycle: ProcessCycle | None = cycle_event_map.get(proposal.event_id)
        cycle_events: list[Event]
        if containing_cycle is None:
            cycle_events = events
        else:
            cycle_events = _events_between(events, containing_cycle.start_event_id, containing_cycle.end_event_id)
        classification: BidClassification = classify_bid(proposal, cycle_events, links)
        bid_classifications.append(classification)
        rule_conflicts: list[str] = _proposal_rule_conflicts(proposal, cycle_events)
        if len(rule_conflicts) > 1:
            stage_decisions.append(
                Decision(
                    skill="stage3_enrichment",
                    decision_type="event_type_choice",
                    detail=(
                        f"Proposal {proposal.event_id} matched multiple classification signals {', '.join(rule_conflicts)}; "
                        f"priority cascade selected {classification.classification_rule}."
                    ),
                    artifact_affected="enrichment/judgments.jsonl",
                    target_id=proposal.event_id,
                    confidence=classification.confidence,
                )
            )

    classification_map: dict[str, BidClassification] = {classification.scope_id: classification for classification in bid_classifications}
    boundary: FormalBoundary | None = determine_formal_boundary(proposal_events, classification_map, events)
    if boundary is None:
        formal_boundary_judgment: FormalBoundary = FormalBoundary(
            judgment_type="formal_boundary",
            scope="deal",
            scope_id=deal_state.deal_slug,
            value=None,
            basis="No proposal was classified as formal, so the deal has no formal bidding boundary.",
            source_text="",
            confidence="high",
            alternative_value=None,
            alternative_basis=None,
        )
    else:
        formal_boundary_judgment = boundary.model_copy(update={"scope_id": deal_state.deal_slug})

    initiation: Initiation = determine_initiation(events, links).model_copy(update={"scope_id": deal_state.deal_slug})
    judgments: list[Judgment] = [*bid_classifications, initiation, formal_boundary_judgment]

    enrichment_dir: Path = deal_state.deal_dir / "enrichment"
    extraction_dir: Path = deal_state.deal_dir / "extraction"
    enrichment_dir.mkdir(parents=True, exist_ok=True)
    extraction_dir.mkdir(parents=True, exist_ok=True)

    _atomic_write_text(enrichment_dir / "process_cycles.jsonl", _jsonl_dump_lines(enriched_cycles))
    _atomic_write_text(enrichment_dir / "judgments.jsonl", _jsonl_dump_lines(judgments))

    decisions_path: Path = extraction_dir / "decisions.jsonl"
    existing_decisions: list[Decision] = [
        decision for decision in _load_existing_decisions(decisions_path) if decision.skill != "stage3_enrichment"
    ]
    combined_decisions: list[Decision] = [*existing_decisions, *stage_decisions]
    _write_decisions(decisions_path, combined_decisions)

    deal_state.process_cycles = enriched_cycles
    deal_state.judgments = judgments
    deal_state.decisions = combined_decisions

    logger.info(
        "stage3 complete deal_slug=%s cycles=%s proposals=%s",
        deal_state.deal_slug,
        len(enriched_cycles),
        len(proposal_events),
    )
    return Stage3Result(
        process_cycles=enriched_cycles,
        judgments=judgments,
        decisions=stage_decisions,
    )
