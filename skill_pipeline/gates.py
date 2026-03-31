"""Semantic gates for extracted skill artifacts."""

from __future__ import annotations

import json
import math
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Literal

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.coverage import _has_non_sale_nda_marker, _normalize_coverage_text
from skill_pipeline.extract_artifacts import LoadedExtractArtifacts, load_extract_artifacts
from skill_pipeline.models import (
    GateAttentionDecay,
    GateFinding,
    GateReport,
    GateReportSummary,
    VerificationFinding,
)
from skill_pipeline.paths import build_skill_paths, ensure_output_directories
from skill_pipeline.pipeline_models.source import ChronologyBlock

SUBSTANTIVE_EVENT_TYPES = frozenset(
    {
        "proposal",
        "nda",
        "drop",
        "final_round_ann",
        "final_round",
        "final_round_inf_ann",
        "final_round_inf",
        "final_round_ext_ann",
        "final_round_ext",
        "executed",
        "terminated",
        "restarted",
    }
)
MIN_DATABLE_BLOCKS = 3
DATE_MISMATCH_DAYS = 730
WINDOW_SIZE = 5
HOT_SPOT_THRESHOLD = 3

EVENT_PHASES: dict[str, set[str]] = {
    "target_sale": {"initiation"},
    "target_sale_public": {"initiation"},
    "bidder_sale": {"initiation"},
    "bidder_interest": {"initiation"},
    "activist_sale": {"initiation"},
    "sale_press_release": {"initiation", "other"},
    "bid_press_release": {"initiation", "other"},
    "ib_retention": {"initiation"},
    "nda": {"initiation", "bidding"},
    "proposal": {"bidding"},
    "drop": {"bidding", "outcome"},
    "final_round_inf_ann": {"bidding"},
    "final_round_inf": {"bidding"},
    "final_round_ann": {"bidding"},
    "final_round": {"bidding"},
    "final_round_ext_ann": {"bidding"},
    "final_round_ext": {"bidding"},
    "executed": {"outcome"},
    "terminated": {"outcome"},
    "restarted": {"outcome"},
}

ROUND_ANNOUNCEMENT_RULES = {
    "final_round": "final_round_ann",
    "final_round_inf": "final_round_inf_ann",
    "final_round_ext": "final_round_ext_ann",
}


def _read_json(path: Path) -> dict | list:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, report: GateReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")


def _get_actor_event_records(artifacts: LoadedExtractArtifacts) -> tuple[list, list]:
    if artifacts.mode == "quote_first":
        return artifacts.raw_actors.actors, artifacts.raw_events.events
    return artifacts.actors.actors, artifacts.events.events


def _parse_iso_date(raw_value: str | date | None) -> date | None:
    if raw_value is None:
        return None
    if isinstance(raw_value, date):
        return raw_value
    try:
        return date.fromisoformat(raw_value)
    except ValueError:
        return None


def _event_date_value(event) -> date | None:
    sort_date = getattr(event.date, "sort_date", None)
    if sort_date is not None:
        return sort_date

    normalized_hint = getattr(event.date, "normalized_hint", None)
    parsed_hint = _parse_iso_date(normalized_hint)
    if parsed_hint is not None:
        return parsed_hint

    normalized_start = getattr(event.date, "normalized_start", None)
    return _parse_iso_date(normalized_start)


def _sort_events_by_date(events: list) -> tuple[list, list[str]]:
    dated_events: list[tuple[date, int, object]] = []
    undated_events: list[tuple[int, object]] = []
    for idx, event in enumerate(events):
        parsed_date = _event_date_value(event)
        if parsed_date is None:
            undated_events.append((idx, event))
            continue
        dated_events.append((parsed_date, idx, event))

    dated_events.sort(key=lambda item: (item[0], item[1]))
    sorted_events = [event for _, _, event in dated_events]
    sorted_events.extend(event for _, event in undated_events)
    undated_event_ids = [event.event_id for _, event in undated_events]
    return sorted_events, undated_event_ids


def _cycle_ranges(events: list) -> list[tuple[int, int]]:
    if not events:
        return []

    ranges: list[tuple[int, int]] = []
    start_idx = 0
    for idx, event in enumerate(events):
        if event.event_type == "restarted" and idx > 0:
            ranges.append((start_idx, idx - 1))
            start_idx = idx

    ranges.append((start_idx, len(events) - 1))
    return ranges


def _load_chronology_blocks(paths) -> list[ChronologyBlock]:
    if not paths.chronology_blocks_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.chronology_blocks_path}")

    blocks: list[ChronologyBlock] = []
    for line in paths.chronology_blocks_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        blocks.append(ChronologyBlock.model_validate(json.loads(line)))
    return blocks


def _load_verification_findings(paths) -> list[VerificationFinding] | None:
    if not paths.verification_findings_path.exists():
        return None

    payload = _read_json(paths.verification_findings_path)
    if isinstance(payload, dict):
        raw_findings = payload.get("findings")
        if not isinstance(raw_findings, list):
            raise ValueError(
                f"verification_findings.json must contain a list under 'findings': "
                f"{paths.verification_findings_path}"
            )
    elif isinstance(payload, list):
        raw_findings = payload
    else:
        raise ValueError(
            f"Unsupported verification findings payload type at {paths.verification_findings_path}"
        )

    return [VerificationFinding.model_validate(finding) for finding in raw_findings]


def _quote_block_index(artifacts: LoadedExtractArtifacts) -> dict[str, str]:
    quote_index: dict[str, str] = {}
    if artifacts.raw_actors:
        for quote in artifacts.raw_actors.quotes:
            quote_index[quote.quote_id] = quote.block_id
    if artifacts.raw_events:
        for quote in artifacts.raw_events.quotes:
            quote_index[quote.quote_id] = quote.block_id
    return quote_index


def _event_block_ids(artifacts: LoadedExtractArtifacts, event) -> list[str]:
    if artifacts.mode == "quote_first":
        quote_index = _quote_block_index(artifacts)
        return [quote_index[quote_id] for quote_id in event.quote_ids if quote_id in quote_index]

    block_ids: list[str] = []
    for span_id in event.evidence_span_ids:
        span = artifacts.span_index.get(span_id)
        if span is None:
            continue
        block_ids.extend(span.block_ids)
    return block_ids


def _qualifies_as_sale_process_nda(
    artifacts: LoadedExtractArtifacts,
    block_index: dict[str, ChronologyBlock],
    event,
) -> bool:
    normalized_parts: list[str] = []
    if event.summary:
        normalized_parts.append(event.summary)

    for block_id in sorted(set(_event_block_ids(artifacts, event))):
        block = block_index.get(block_id)
        if block is None:
            continue
        normalized_parts.append(block.raw_text)
        if block.clean_text != block.raw_text:
            normalized_parts.append(block.clean_text)

    return not _has_non_sale_nda_marker(_normalize_coverage_text(" ".join(normalized_parts)))


def _gate_temporal_consistency(
    artifacts: LoadedExtractArtifacts,
    blocks: list[ChronologyBlock],
) -> list[GateFinding]:
    datable_block_ids = {
        block.block_id
        for block in blocks
        if any(_parse_iso_date(mention.normalized) is not None for mention in block.date_mentions)
    }
    if len(datable_block_ids) < MIN_DATABLE_BLOCKS:
        return []

    _, events = _get_actor_event_records(artifacts)
    block_index = {block.block_id: block for block in blocks}
    findings: list[GateFinding] = []

    for event in events:
        event_date = _event_date_value(event)
        if event_date is None:
            continue

        block_ids = sorted(set(_event_block_ids(artifacts, event)))
        if not block_ids:
            continue

        expected_phases = EVENT_PHASES.get(event.event_type)
        matched_block_dates: list[date] = []
        matched_phases: set[str] = set()
        for block_id in block_ids:
            block = block_index.get(block_id)
            if block is None:
                continue
            matched_phases.add(block.temporal_phase)
            for mention in block.date_mentions:
                parsed_mention = _parse_iso_date(mention.normalized)
                if parsed_mention is not None:
                    matched_block_dates.append(parsed_mention)

        if matched_block_dates and all(
            abs((event_date - block_date).days) > DATE_MISMATCH_DAYS
            for block_date in matched_block_dates
        ):
            findings.append(
                GateFinding(
                    gate_id="temporal_consistency",
                    rule_id="date_block_mismatch",
                    severity="blocker",
                    description=(
                        f"Event {event.event_id} date {event_date.isoformat()} differs by more than "
                        f"two years from all evidence block dates."
                    ),
                    event_ids=[event.event_id],
                    actor_ids=sorted(event.actor_ids),
                    block_ids=block_ids,
                )
            )

        if expected_phases is not None and matched_phases and matched_phases.isdisjoint(expected_phases):
            findings.append(
                GateFinding(
                    gate_id="temporal_consistency",
                    rule_id="temporal_phase_mismatch",
                    severity="warning",
                    description=(
                        f"Event {event.event_id} type {event.event_type} is grounded only in "
                        f"{sorted(matched_phases)} blocks."
                    ),
                    event_ids=[event.event_id],
                    actor_ids=sorted(event.actor_ids),
                    block_ids=block_ids,
                )
            )

    return findings


def _gate_cross_event_logic(
    artifacts: LoadedExtractArtifacts,
    block_index: dict[str, ChronologyBlock],
    sorted_events: list,
    cycle_ranges: list[tuple[int, int]],
    undated_event_ids: list[str],
) -> list[GateFinding]:
    findings: list[GateFinding] = []
    undated_event_ids_set = set(undated_event_ids)

    for cycle_start, cycle_end in cycle_ranges:
        seen_announcements: set[str] = set()
        dropped_actor_ids: set[str] = set()
        executed_event = None

        for idx in range(cycle_start, cycle_end + 1):
            event = sorted_events[idx]
            if event.event_id in undated_event_ids_set:
                continue

            if event.event_type == "restarted":
                seen_announcements.clear()
                dropped_actor_ids.clear()
                executed_event = None
                continue

            if event.event_type in ROUND_ANNOUNCEMENT_RULES.values():
                seen_announcements.add(event.event_type)

            if event.event_type in ROUND_ANNOUNCEMENT_RULES:
                required_announcement = ROUND_ANNOUNCEMENT_RULES[event.event_type]
                if required_announcement not in seen_announcements:
                    findings.append(
                        GateFinding(
                            gate_id="cross_event_logic",
                            rule_id="announcement_before_deadline",
                            severity="blocker",
                            description=(
                                f"Event {event.event_id} ({event.event_type}) appears before "
                                f"{required_announcement} in the same cycle."
                            ),
                            event_ids=[event.event_id],
                            actor_ids=sorted(event.actor_ids),
                        )
                    )

            if event.event_type == "drop":
                dropped_actor_ids.update(event.actor_ids)

            if (
                event.event_type == "nda"
                and _qualifies_as_sale_process_nda(artifacts, block_index, event)
                and dropped_actor_ids.intersection(event.actor_ids)
            ):
                findings.append(
                    GateFinding(
                        gate_id="cross_event_logic",
                        rule_id="nda_after_drop",
                        severity="blocker",
                        description=(
                            f"Event {event.event_id} signs an NDA after the same bidder dropped "
                            f"from the active cycle."
                        ),
                        event_ids=[event.event_id],
                        actor_ids=sorted(dropped_actor_ids.intersection(event.actor_ids)),
                    )
                )

            if executed_event is not None and event.event_type == "proposal":
                findings.append(
                    GateFinding(
                        gate_id="cross_event_logic",
                        rule_id="proposal_after_executed",
                        severity="blocker",
                        description=(
                            f"Proposal {event.event_id} occurs after executed event "
                            f"{executed_event.event_id} in the same cycle."
                        ),
                        event_ids=[executed_event.event_id, event.event_id],
                        actor_ids=sorted(event.actor_ids),
                    )
                )

            if (
                executed_event is not None
                and event.event_type in SUBSTANTIVE_EVENT_TYPES
                and event.event_type != "executed"
            ):
                findings.append(
                    GateFinding(
                        gate_id="cross_event_logic",
                        rule_id="executed_last_in_cycle",
                        severity="warning",
                        description=(
                            f"Event {event.event_id} follows executed event "
                            f"{executed_event.event_id} in the same cycle."
                        ),
                        event_ids=[executed_event.event_id, event.event_id],
                        actor_ids=sorted(event.actor_ids),
                    )
                )

            if event.event_type == "executed":
                executed_event = event

    for event in sorted_events:
        if event.event_id not in undated_event_ids_set:
            continue
        if event.event_type not in SUBSTANTIVE_EVENT_TYPES:
            continue
        findings.append(
            GateFinding(
                gate_id="cross_event_logic",
                rule_id="undated_event_in_sequence",
                severity="warning",
                description=(
                    f"Event {event.event_id} ({event.event_type}) has no parseable date and was "
                    f"excluded from chronological sequence checks."
                ),
                event_ids=[event.event_id],
                actor_ids=sorted(event.actor_ids),
            )
        )

    return findings


def _gate_actor_lifecycle(
    artifacts: LoadedExtractArtifacts,
    block_index: dict[str, ChronologyBlock],
    actors: list,
    events: list,
) -> list[GateFinding]:
    nda_signer_ids: set[str] = set()
    downstream_actor_ids: set[str] = set()

    for event in events:
        if event.event_type == "nda" and _qualifies_as_sale_process_nda(
            artifacts, block_index, event
        ):
            nda_signer_ids.update(event.actor_ids)
        if event.event_type in {"proposal", "drop", "executed", "terminated"}:
            downstream_actor_ids.update(event.actor_ids)

    actor_index = {actor.actor_id: actor for actor in actors}
    findings: list[GateFinding] = []
    for actor_id in sorted(nda_signer_ids - downstream_actor_ids):
        actor = actor_index.get(actor_id)
        findings.append(
            GateFinding(
                gate_id="actor_lifecycle",
                rule_id="nda_signer_no_downstream",
                severity="warning",
                description=(
                    f"NDA signer {actor_id} does not appear in any downstream proposal, "
                    f"drop, executed, or terminated event."
                ),
                actor_ids=[actor_id],
                event_ids=[],
                block_ids=[],
            )
        )
        if actor is not None and actor.role != "bidder":
            raise ValueError(f"Unexpected non-bidder NDA signer: {actor.actor_id}")

    return findings


def _hot_spots(failure_ordinals: list[int], total_blocks: int) -> list[dict]:
    if not failure_ordinals:
        return []

    counts_by_ordinal = Counter(failure_ordinals)
    hot_spots: list[dict] = []
    if total_blocks <= 0:
        return hot_spots

    for start in range(1, total_blocks + 1):
        end = min(total_blocks, start + WINDOW_SIZE - 1)
        failure_count = sum(
            count
            for ordinal, count in counts_by_ordinal.items()
            if start <= ordinal <= end
        )
        if failure_count >= HOT_SPOT_THRESHOLD:
            hot_spots.append(
                {
                    "block_ordinal_start": start,
                    "block_ordinal_end": end,
                    "failure_count": failure_count,
                }
            )
    return hot_spots


def _gate_attention_decay(
    verification_findings: list[VerificationFinding],
    blocks: list[ChronologyBlock],
) -> GateAttentionDecay:
    block_ordinals = {block.block_id: block.ordinal for block in blocks}
    failure_ordinals: list[int] = []

    for finding in verification_findings:
        for block_id in finding.block_ids:
            ordinal = block_ordinals.get(block_id)
            if ordinal is not None:
                failure_ordinals.append(ordinal)

    if not failure_ordinals:
        return GateAttentionDecay(
            quartile_counts=[0, 0, 0, 0],
            hot_spots=[],
            decay_score=1.0,
            note=None,
        )

    total_blocks = max(len(blocks), 1)
    quartile_counts = [0, 0, 0, 0]
    quartile_size = total_blocks / 4
    for ordinal in failure_ordinals:
        quartile_index = min(int((ordinal - 1) / quartile_size), 3)
        quartile_counts[quartile_index] += 1

    total_failures = sum(quartile_counts)
    entropy = 0.0
    for count in quartile_counts:
        if count == 0:
            continue
        share = count / total_failures
        entropy -= share * math.log(share)
    decay_score = round(entropy / math.log(4), 3)

    note = None
    if total_failures <= 2:
        note = "Too few failures for statistical significance"
    elif decay_score < 0.5:
        dominant_quartile = quartile_counts.index(max(quartile_counts)) + 1
        note = f"Attention decay pattern detected: failures concentrated in Q{dominant_quartile}"

    return GateAttentionDecay(
        quartile_counts=quartile_counts,
        hot_spots=_hot_spots(failure_ordinals, total_blocks),
        decay_score=decay_score,
        note=note,
    )


def _build_report(
    findings: list[GateFinding],
    attention_decay: GateAttentionDecay | None,
) -> GateReport:
    blocker_count = sum(1 for finding in findings if finding.severity == "blocker")
    warning_count = sum(1 for finding in findings if finding.severity == "warning")
    status: Literal["pass", "fail"] = "fail" if blocker_count > 0 else "pass"
    return GateReport(
        findings=findings,
        attention_decay=attention_decay,
        summary=GateReportSummary(
            blocker_count=blocker_count,
            warning_count=warning_count,
            status=status,
        ),
    )


def run_gates(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    """Run semantic gates on extracted skill artifacts."""

    paths = build_skill_paths(deal_slug, project_root=project_root)
    ensure_output_directories(paths, include_legacy=True)

    artifacts = load_extract_artifacts(paths)
    blocks = _load_chronology_blocks(paths)
    block_index = {block.block_id: block for block in blocks}
    actors, events = _get_actor_event_records(artifacts)

    findings: list[GateFinding] = []
    findings.extend(_gate_temporal_consistency(artifacts, blocks))

    sorted_events, undated_event_ids = _sort_events_by_date(events)
    findings.extend(
        _gate_cross_event_logic(
            artifacts,
            block_index,
            sorted_events,
            _cycle_ranges(sorted_events),
            undated_event_ids,
        )
    )
    findings.extend(_gate_actor_lifecycle(artifacts, block_index, actors, events))

    verification_findings = _load_verification_findings(paths)
    attention_decay = None
    if verification_findings is not None:
        attention_decay = _gate_attention_decay(verification_findings, blocks)

    report = _build_report(findings, attention_decay)
    _write_json(paths.gates_report_path, report)
    return 1 if report.summary.status == "fail" else 0
