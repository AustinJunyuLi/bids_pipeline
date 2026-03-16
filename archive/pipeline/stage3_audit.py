from __future__ import annotations

import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Iterable

from pipeline.schemas import (
    Actor,
    AuditCheckResult,
    AuditFailure,
    AuditFlags,
    Census,
    CensusPartyRosterEntry,
    CountAssertion,
    DealState,
    Event,
    EventActorLink,
    LifecycleAudit,
    ProcessCycle,
    QuoteVerifyResult,
    Reconciliation,
    SelfCheck,
    Stage3AuditResult,
    StructuralAudit,
)


logger = logging.getLogger(__name__)


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

_TEXT_NORMALIZATION_RE = re.compile(r"\s+")
_WORD_RE = re.compile(r"[A-Za-z0-9$%.,'-]+")


def _normalize_text(value: str) -> str:
    """Normalize text for robust quote matching across line wrapping and whitespace differences."""

    normalized: str = value
    replacements: dict[str, str] = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2014": "-",
        "\u2013": "-",
        "\xa0": " ",
    }
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    normalized = _TEXT_NORMALIZATION_RE.sub(" ", normalized)
    return normalized.strip()


def _lines_window(txt_lines: list[str], line_start: int, line_end: int, context: int) -> tuple[int, int, str]:
    """Return a line window and joined text around a claimed line interval."""

    start_index: int = max(line_start - 1 - context, 0)
    end_index: int = min(line_end - 1 + context, len(txt_lines) - 1)
    if end_index < start_index:
        return start_index + 1, start_index + 1, ""
    window_text: str = "\n".join(txt_lines[start_index : end_index + 1])
    return start_index + 1, end_index + 1, window_text


def _extract_distinctive_phrase(source_text: str, minimum_words: int = 8) -> str | None:
    """Extract a distinctive phrase from source text for full-file fallback matching."""

    words: list[str] = _WORD_RE.findall(_normalize_text(source_text))
    if len(words) < minimum_words:
        return None
    max_window: int = min(14, len(words))
    for window_size in range(max_window, minimum_words - 1, -1):
        for start_index in range(0, len(words) - window_size + 1):
            phrase: str = " ".join(words[start_index : start_index + window_size])
            if len(phrase) >= 40:
                return phrase
    return " ".join(words[:minimum_words])


def _find_phrase_line_bounds(phrase: str, txt_lines: list[str]) -> tuple[int, int] | None:
    """Find approximate line bounds for a phrase in the full file."""

    normalized_phrase: str = _normalize_text(phrase)
    if not normalized_phrase:
        return None
    for start_index in range(len(txt_lines)):
        joined: list[str] = []
        for end_index in range(start_index, min(start_index + 15, len(txt_lines))):
            joined.append(txt_lines[end_index])
            normalized_window: str = _normalize_text(" ".join(joined))
            if normalized_phrase in normalized_window:
                return start_index + 1, end_index + 1
    return None


def verify_quote(source_text: str, line_start: int, line_end: int, txt_lines: list[str]) -> QuoteVerifyResult:
    """Verify that a source quote exists in the frozen text snapshot.

    Verification proceeds in three deterministic steps: a local context read around the
    claimed lines, a broader local context retry, and a full-file distinctive phrase search.
    """

    normalized_quote: str = _normalize_text(source_text)
    if not normalized_quote:
        return QuoteVerifyResult(
            verified=False,
            strategy="unverified",
            original_line_start=line_start,
            original_line_end=line_end,
            matched_line_start=None,
            matched_line_end=None,
            distinctive_phrase=None,
            detail="Source text is empty after normalization and cannot be verified.",
        )

    primary_start: int
    primary_end: int
    primary_text: str
    primary_start, primary_end, primary_text = _lines_window(txt_lines, line_start, line_end, context=10)
    if normalized_quote in _normalize_text(primary_text):
        return QuoteVerifyResult(
            verified=True,
            strategy="primary",
            original_line_start=line_start,
            original_line_end=line_end,
            matched_line_start=primary_start,
            matched_line_end=primary_end,
            distinctive_phrase=None,
            detail="Quote verified within the claimed line range plus local context.",
        )

    retry_start: int
    retry_end: int
    retry_text: str
    retry_start, retry_end, retry_text = _lines_window(txt_lines, line_start, line_end, context=50)
    if normalized_quote in _normalize_text(retry_text):
        return QuoteVerifyResult(
            verified=True,
            strategy="retry_context",
            original_line_start=line_start,
            original_line_end=line_end,
            matched_line_start=retry_start,
            matched_line_end=retry_end,
            distinctive_phrase=None,
            detail="Quote verified after broadening the local search context by fifty lines on each side.",
        )

    distinctive_phrase: str | None = _extract_distinctive_phrase(source_text)
    if distinctive_phrase is not None:
        phrase_bounds: tuple[int, int] | None = _find_phrase_line_bounds(distinctive_phrase, txt_lines)
        if phrase_bounds is not None:
            matched_start, matched_end = phrase_bounds
            return QuoteVerifyResult(
                verified=True,
                strategy="full_file_search",
                original_line_start=line_start,
                original_line_end=line_end,
                matched_line_start=matched_start,
                matched_line_end=matched_end,
                distinctive_phrase=distinctive_phrase,
                detail="Quote verified by full-file search for a distinctive phrase extracted from the source text.",
            )

    return QuoteVerifyResult(
        verified=False,
        strategy="unverified",
        original_line_start=line_start,
        original_line_end=line_end,
        matched_line_start=None,
        matched_line_end=None,
        distinctive_phrase=distinctive_phrase,
        detail="Quote could not be verified after local and full-file fallback searches.",
    )


def verify_all_quotes(events: list[Event], actors: list[Actor], txt_path: Path) -> list[QuoteVerifyResult]:
    """Verify every event and actor quote against the frozen text snapshot."""

    txt_lines: list[str] = txt_path.read_text(encoding="utf-8").splitlines()
    results: list[QuoteVerifyResult] = []
    for event in events:
        result: QuoteVerifyResult = verify_quote(
            event.source_text,
            event.source_line_start,
            event.source_line_end,
            txt_lines,
        ).model_copy(update={"object_type": "event", "object_id": event.event_id})
        results.append(result)
    for actor in actors:
        result = verify_quote(
            actor.first_evidence_text,
            actor.first_evidence_line_start,
            actor.first_evidence_line_end,
            txt_lines,
        ).model_copy(update={"object_type": "actor", "object_id": actor.actor_id})
        results.append(result)
    return results


def check_nda_coverage(actors: list[Actor], events: list[Event], links: list[EventActorLink]) -> AuditCheckResult:
    """Check that every bidder has an NDA event or is surfaced for review."""

    nda_event_ids: set[str] = {event.event_id for event in events if event.event_type == "nda"}
    proposal_event_ids: set[str] = {event.event_id for event in events if event.event_type == "proposal"}
    nda_actor_ids: set[str] = {link.actor_id for link in links if link.event_id in nda_event_ids}
    proposal_actor_ids: set[str] = {link.actor_id for link in links if link.event_id in proposal_event_ids}

    failures: list[AuditFailure] = []
    for actor in actors:
        if actor.actor_type != "bidder":
            continue
        if actor.actor_id in nda_actor_ids:
            continue
        if actor.actor_id in proposal_actor_ids:
            detail: str = "Bidder submitted at least one proposal but has no corresponding NDA event."
        else:
            detail = "Bidder has no corresponding NDA event in the extracted chronology."
        failures.append(
            AuditFailure(
                check="nda_coverage",
                detail=detail,
                actor_id=actor.actor_id,
            )
        )
    status: str = "pass" if not failures else "needs_review"
    return AuditCheckResult(check="nda_coverage", status=status, failures=failures)


def check_round_pairs(events: list[Event]) -> AuditCheckResult:
    """Check that each round-announcement event has a matching deadline event."""

    ordered_events: list[Event] = sorted(
        events,
        key=lambda event: (event.date, event.source_line_start, event.event_id),
    )
    pending_counts: dict[str, int] = {announcement_type: 0 for announcement_type in _ROUND_PAIR_MAP}
    failures: list[AuditFailure] = []

    for event in ordered_events:
        if event.event_type in _ROUND_PAIR_MAP:
            pending_counts[event.event_type] += 1
            continue
        for announcement_type, deadline_type in _ROUND_PAIR_MAP.items():
            if event.event_type == deadline_type and pending_counts[announcement_type] > 0:
                pending_counts[announcement_type] -= 1
                break

    for announcement_type, remaining in pending_counts.items():
        for _ in range(remaining):
            failures.append(
                AuditFailure(
                    check="round_pairs",
                    detail=f"At least one {announcement_type} event has no matching {_ROUND_PAIR_MAP[announcement_type]} event.",
                    actor_id=None,
                )
            )
    status: str = "pass" if not failures else "needs_review"
    return AuditCheckResult(check="round_pairs", status=status, failures=failures)


def check_process_initiation(events: list[Event]) -> AuditCheckResult:
    """Check that the chronology contains at least one canonical initiation event."""

    initiation_types: set[str] = {"target_sale", "bidder_sale", "activist_sale", "bidder_interest"}
    if any(event.event_type in initiation_types for event in events):
        return AuditCheckResult(check="process_initiation", status="pass", failures=[])
    return AuditCheckResult(
        check="process_initiation",
        status="needs_review",
        failures=[
            AuditFailure(
                check="process_initiation",
                detail="No target_sale, bidder_sale, activist_sale, or bidder_interest event was extracted.",
                actor_id=None,
            )
        ],
    )


def check_lifecycle_consistency(actors: list[Actor], events: list[Event], links: list[EventActorLink]) -> AuditCheckResult:
    """Check that terminal actor lifecycle states have corresponding event support."""

    links_by_actor: dict[str, list[EventActorLink]] = {}
    for link in links:
        links_by_actor.setdefault(link.actor_id, []).append(link)
    event_type_by_id: dict[str, str] = {event.event_id: event.event_type for event in events}
    required_map: dict[str, set[str]] = {
        "dropped": {"drop", "drop_below_m", "drop_below_inf", "drop_at_inf"},
        "dropped_by_target": {"drop_target"},
        "winner": {"executed"},
    }
    failures: list[AuditFailure] = []
    for actor in actors:
        if actor.actor_type == "advisor":
            continue
        required_event_types: set[str] | None = required_map.get(actor.lifecycle_status)
        if required_event_types is None:
            continue
        actor_event_types: set[str] = {
            event_type_by_id[link.event_id]
            for link in links_by_actor.get(actor.actor_id, [])
            if link.event_id in event_type_by_id
        }
        if actor_event_types.intersection(required_event_types):
            continue
        failures.append(
            AuditFailure(
                check="lifecycle_consistency",
                detail=(
                    f"Actor lifecycle status {actor.lifecycle_status} is not supported by a corresponding event in the extracted chronology."
                ),
                actor_id=actor.actor_id,
            )
        )
    status: str = "pass" if not failures else "needs_review"
    return AuditCheckResult(check="lifecycle_consistency", status=status, failures=failures)


def _sorted_events(events: Iterable[Event]) -> list[Event]:
    """Return events sorted by date and source location."""

    return sorted(events, key=lambda event: (event.date, event.source_line_start, event.event_id))


def _event_index_map(events: list[Event]) -> dict[str, int]:
    """Return a mapping from event ID to sorted event index."""

    return {event.event_id: index for index, event in enumerate(events)}


def check_proposal_completeness(
    events: list[Event],
    links: list[EventActorLink],
    cycles: list[ProcessCycle],
) -> AuditCheckResult:
    """Check that every invited actor in a round has a proposal or dropout event."""

    ordered_events: list[Event] = _sorted_events(events)
    index_map: dict[str, int] = _event_index_map(ordered_events)
    event_ids_by_actor: dict[str, list[str]] = {}
    for link in links:
        event_ids_by_actor.setdefault(link.actor_id, []).append(link.event_id)

    event_by_id: dict[str, Event] = {event.event_id: event for event in ordered_events}
    failures: list[AuditFailure] = []

    for cycle in cycles:
        for round_row in cycle.rounds:
            if round_row.announcement_event_id not in index_map or round_row.deadline_event_id not in index_map:
                failures.append(
                    AuditFailure(
                        check="proposal_completeness",
                        detail=(
                            f"Round {round_row.round_id} cannot be audited because one of its boundary events is missing from events.jsonl."
                        ),
                        actor_id=None,
                    )
                )
                continue
            start_index: int = index_map[round_row.announcement_event_id]
            end_index: int = index_map[round_row.deadline_event_id]
            if end_index < start_index:
                failures.append(
                    AuditFailure(
                        check="proposal_completeness",
                        detail=f"Round {round_row.round_id} has a deadline ordered before its announcement.",
                        actor_id=None,
                    )
                )
                continue
            deadline_date: str = ordered_events[end_index].date
            # Chronology narratives often place the deadline sentence before the same-day
            # proposal or dropout rows, so include the rest of that calendar date.
            while end_index + 1 < len(ordered_events) and ordered_events[end_index + 1].date == deadline_date:
                end_index += 1
            round_event_ids: set[str] = {event.event_id for event in ordered_events[start_index : end_index + 1]}
            for actor_id in round_row.invited_set:
                actor_event_ids: list[str] = event_ids_by_actor.get(actor_id, [])
                has_proposal_or_dropout: bool = False
                for event_id in actor_event_ids:
                    if event_id not in round_event_ids:
                        continue
                    event_type: str = event_by_id[event_id].event_type
                    if event_type == "proposal" or event_type in _DROP_EVENT_TYPES:
                        has_proposal_or_dropout = True
                        break
                if has_proposal_or_dropout:
                    continue
                failures.append(
                    AuditFailure(
                        check="proposal_completeness",
                        detail=(
                            f"Actor {actor_id} was invited in round {round_row.round_id} but has no proposal or dropout event during the round window."
                        ),
                        actor_id=actor_id,
                    )
                )
    status: str = "pass" if not failures else "needs_review"
    return AuditCheckResult(check="proposal_completeness", status=status, failures=failures)


def build_census(
    actors: list[Actor],
    count_assertions: list[CountAssertion],
    reconciliations: list[Reconciliation],
    structural_results: dict[str, AuditCheckResult],
) -> Census:
    """Build the full census.json artifact from actors, counts, and audit results."""

    roster: list[CensusPartyRosterEntry] = [
        CensusPartyRosterEntry(
            actor_id=actor.actor_id,
            actor_alias=actor.actor_alias,
            actor_type=actor.actor_type,
            bidder_subtype=actor.bidder_subtype,
            lifecycle_status=actor.lifecycle_status,
            source="actors.jsonl",
            first_evidence_accession_number=actor.first_evidence_accession_number,
            first_evidence_line_start=actor.first_evidence_line_start,
            first_evidence_line_end=actor.first_evidence_line_end,
            first_evidence_text=actor.first_evidence_text,
        )
        for actor in sorted(actors, key=lambda item: (item.actor_alias.lower(), item.actor_id))
    ]

    normalized_reconciliations: list[Reconciliation] = []
    for reconciliation in reconciliations:
        residual: int = reconciliation.expected - reconciliation.extracted - reconciliation.explained
        status: str = "pass" if residual == 0 else "fail"
        normalized_reconciliations.append(
            reconciliation.model_copy(update={"residual": residual, "status": status})
        )

    unresolved_actor_ids: list[str] = sorted(
        actor.actor_id
        for actor in actors
        if actor.actor_type != "advisor" and actor.lifecycle_status == "unresolved"
    )
    total_non_advisor_actors: int = sum(1 for actor in actors if actor.actor_type != "advisor")
    closed_non_advisor_actors: int = sum(
        1
        for actor in actors
        if actor.actor_type != "advisor" and actor.lifecycle_status != "unresolved"
    )
    structural_failures: list[AuditFailure] = []
    for audit_name in (
        "nda_coverage",
        "round_pairs",
        "process_initiation",
        "lifecycle_consistency",
        "proposal_completeness",
    ):
        result: AuditCheckResult = structural_results[audit_name]
        structural_failures.extend(result.failures)

    structural_audit: StructuralAudit = StructuralAudit(
        nda_coverage=structural_results["nda_coverage"].status,
        round_pairs=structural_results["round_pairs"].status,
        process_initiation=structural_results["process_initiation"].status,
        lifecycle_consistency=structural_results["lifecycle_consistency"].status,
        proposal_completeness=structural_results["proposal_completeness"].status,
        failures=structural_failures,
    )

    lifecycle_audit: LifecycleAudit = LifecycleAudit(
        total_actors=total_non_advisor_actors,
        closed_actors=closed_non_advisor_actors,
        unresolved_actors=unresolved_actor_ids,
    )

    return Census(
        party_roster=roster,
        count_assertions=list(count_assertions),
        self_check=SelfCheck(
            reconciliations=normalized_reconciliations,
            structural_audit=structural_audit,
            lifecycle_audit=lifecycle_audit,
        ),
    )


def build_audit_flags(deal_slug: str, census: Census, unverified_quotes: list[str]) -> AuditFlags:
    """Derive audit_flags.json from census results and quote verification failures."""

    flags: list[str] = []
    unresolved_actors: list[str] = list(census.self_check.lifecycle_audit.unresolved_actors)
    unresolved_counts: list[str] = [
        reconciliation.assertion_id
        for reconciliation in census.self_check.reconciliations
        if reconciliation.status == "fail"
    ]
    structural_failures: list[AuditFailure] = list(census.self_check.structural_audit.failures)

    if unresolved_actors:
        flags.append("unresolved_actors")
    if unverified_quotes:
        flags.append("unverified_quotes")
    if unresolved_counts:
        flags.append("count_mismatch")
    if census.self_check.structural_audit.nda_coverage != "pass":
        flags.append("missing_nda")
    if census.self_check.structural_audit.round_pairs != "pass":
        flags.append("missing_round_pair")
    if census.self_check.structural_audit.process_initiation != "pass":
        flags.append("missing_initiation")
    if census.self_check.structural_audit.lifecycle_consistency != "pass":
        flags.append("lifecycle_inconsistency")
    if census.self_check.structural_audit.proposal_completeness != "pass":
        flags.append("proposal_completeness")

    ordered_flags: list[str] = []
    for flag in (
        "unresolved_actors",
        "unverified_quotes",
        "count_mismatch",
        "missing_nda",
        "missing_round_pair",
        "missing_initiation",
        "lifecycle_inconsistency",
        "proposal_completeness",
    ):
        if flag in flags:
            ordered_flags.append(flag)

    return AuditFlags(
        deal_slug=deal_slug,
        flags=ordered_flags,
        unresolved_actors=unresolved_actors,
        unresolved_counts=sorted(unresolved_counts),
        unverified_quotes=sorted(unverified_quotes),
        structural_failures=structural_failures,
    )


def _json_dump(payload: object) -> str:
    """Serialize a payload to deterministic JSON text."""

    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


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


def _primary_txt_path(deal_state: DealState) -> Path:
    """Resolve the primary frozen text path from the deal state manifest."""

    if deal_state.corpus_manifest:
        primary_entries: list[object] = [entry for entry in deal_state.corpus_manifest if entry.role == "primary"]
        if primary_entries:
            primary_entry = primary_entries[0]
            return deal_state.deal_dir / primary_entry.txt_filename
    raise FileNotFoundError(f"Primary txt file could not be resolved for deal {deal_state.deal_slug}")


def run_stage3_audit(deal_state: DealState) -> Stage3AuditResult:
    """Run deterministic quote verification and structural audit.

    The function writes ``census.json`` and ``audit_flags.json`` to the deal's extraction
    directory. Count reconciliation rows are expected to already be present in the deal
    state from stage 2 provider output.
    """

    logger.info("stage3_audit starting deal_slug=%s", deal_state.deal_slug)
    txt_path: Path = _primary_txt_path(deal_state)
    quote_results: list[QuoteVerifyResult] = verify_all_quotes(deal_state.events, deal_state.actors, txt_path)
    unverified_ids: list[str] = sorted(
        result.object_id
        for result in quote_results
        if not result.verified and result.object_id is not None
    )

    structural_results: dict[str, AuditCheckResult] = {
        "nda_coverage": check_nda_coverage(deal_state.actors, deal_state.events, deal_state.event_actor_links),
        "round_pairs": check_round_pairs(deal_state.events),
        "process_initiation": check_process_initiation(deal_state.events),
        "lifecycle_consistency": check_lifecycle_consistency(
            deal_state.actors,
            deal_state.events,
            deal_state.event_actor_links,
        ),
        "proposal_completeness": check_proposal_completeness(
            deal_state.events,
            deal_state.event_actor_links,
            deal_state.process_cycles,
        ),
    }

    census: Census = build_census(
        actors=deal_state.actors,
        count_assertions=deal_state.count_assertions,
        reconciliations=deal_state.reconciliations,
        structural_results=structural_results,
    )
    audit_flags: AuditFlags = build_audit_flags(deal_state.deal_slug, census, unverified_ids)

    extraction_dir: Path = deal_state.deal_dir / "extraction"
    extraction_dir.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(extraction_dir / "census.json", _json_dump(census.model_dump(mode="json")))
    _atomic_write_text(extraction_dir / "audit_flags.json", _json_dump(audit_flags.model_dump(mode="json")))

    deal_state.census = census
    deal_state.audit_flags = audit_flags

    logger.info(
        "stage3_audit complete deal_slug=%s unverified_quotes=%s flags=%s",
        deal_state.deal_slug,
        len(unverified_ids),
        len(audit_flags.flags),
    )
    return Stage3AuditResult(quote_results=quote_results, census=census, audit_flags=audit_flags)
