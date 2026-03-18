from __future__ import annotations

from typing import Any

from pipeline.llm.schemas import EventExtractionOutput, RawEventRecord, RawExclusion


def merge_event_outputs(outputs: list[EventExtractionOutput]) -> EventExtractionOutput:
    merged_events: list[RawEventRecord] = []
    seen_event_keys: set[tuple[Any, ...]] = set()
    merged_exclusions: list[RawExclusion] = []
    seen_exclusion_keys: set[tuple[Any, ...]] = set()
    unresolved_mentions: list[str] = []
    coverage_notes: list[str] = []

    for output in outputs:
        for event in output.events:
            key = _event_key(event)
            if key in seen_event_keys:
                continue
            seen_event_keys.add(key)
            merged_events.append(event)
        for exclusion in output.exclusions:
            key = (exclusion.category, tuple(sorted(exclusion.block_ids)), exclusion.explanation.strip())
            if key in seen_exclusion_keys:
                continue
            seen_exclusion_keys.add(key)
            merged_exclusions.append(exclusion)
        for mention in output.unresolved_mentions:
            if mention not in unresolved_mentions:
                unresolved_mentions.append(mention)
        for note in output.coverage_notes:
            if note not in coverage_notes:
                coverage_notes.append(note)

    merged_events.sort(key=_event_sort_key)
    return EventExtractionOutput(
        events=merged_events,
        exclusions=merged_exclusions,
        unresolved_mentions=unresolved_mentions,
        coverage_notes=coverage_notes,
    )


def _event_key(event: RawEventRecord) -> tuple[Any, ...]:
    terms = event.terms
    terms_key = None
    if terms is not None:
        terms_key = (
            str(terms.value_per_share) if terms.value_per_share is not None else None,
            str(terms.lower_per_share) if terms.lower_per_share is not None else None,
            str(terms.upper_per_share) if terms.upper_per_share is not None else None,
            str(terms.total_enterprise_value) if terms.total_enterprise_value is not None else None,
            terms.is_range,
        )
    evidence_key = tuple(
        sorted(
            (
                ref.block_id or "",
                ref.evidence_id or "",
                " ".join(ref.anchor_text.lower().split()),
            )
            for ref in event.evidence_refs
        )
    )
    return (
        event.event_type.value,
        " ".join(event.date.raw_text.lower().split()),
        tuple(sorted(event.actor_ids)),
        terms_key,
        evidence_key,
    )


def _event_sort_key(event: RawEventRecord) -> tuple[Any, ...]:
    return (
        event.date.normalized_hint or "",
        event.date.raw_text,
        event.event_type.value,
        tuple(event.actor_ids),
        event.summary,
    )
