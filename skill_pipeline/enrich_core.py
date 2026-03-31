"""Deterministic enrich-core: rounds, bid classification, cycles, formal boundary."""

from __future__ import annotations

import json
from pathlib import Path

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.extract_artifacts import LoadedExtractArtifacts, load_extract_artifacts
from skill_pipeline.models import (
    BidClassification,
    CoverageSummary,
    GateReport,
    SkillEventRecord,
    SkillCheckReport,
    SkillVerificationLog,
)
from skill_pipeline.paths import build_skill_paths, ensure_output_directories

ROUND_PAIRS = [
    ("final_round_inf_ann", "final_round_inf", "informal"),
    ("final_round_ann", "final_round", "formal"),
    ("final_round_ext_ann", "final_round_ext", "extension"),
]
BEST_AND_FINAL_MARKERS = (
    "best-and-final",
    "best and final",
    "last-and-best",
    "last and best",
)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _invalidate_enrich_outputs(paths) -> None:
    if paths.deterministic_enrichment_path.exists():
        paths.deterministic_enrichment_path.unlink()


def _require_gate_artifacts(paths) -> None:
    required_paths = [
        paths.check_report_path,
        paths.verification_log_path,
        paths.coverage_summary_path,
    ]
    for path in required_paths:
        if not path.exists():
            raise FileNotFoundError(f"Missing required input: {path}")

    check_report = SkillCheckReport.model_validate(_read_json(paths.check_report_path))
    if check_report.summary.status != "pass":
        raise ValueError(
            f"Cannot run enrich-core before check passes: {paths.check_report_path}"
        )

    verify_log = SkillVerificationLog.model_validate(_read_json(paths.verification_log_path))
    if verify_log.summary.status != "pass":
        raise ValueError(
            f"Cannot run enrich-core before verify passes: {paths.verification_log_path}"
        )

    coverage_summary = CoverageSummary.model_validate(_read_json(paths.coverage_summary_path))
    if coverage_summary.status != "pass":
        raise ValueError(
            f"Cannot run enrich-core before coverage passes: {paths.coverage_summary_path}"
        )

    if not paths.gates_report_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.gates_report_path}")

    gates_report = GateReport.model_validate(_read_json(paths.gates_report_path))
    if gates_report.summary.status != "pass":
        raise ValueError(
            f"Cannot run enrich-core before gates pass: {paths.gates_report_path}"
        )


def _cycle_ranges(events: list[SkillEventRecord]) -> list[tuple[int, int]]:
    """Return inclusive index ranges for restart-delimited cycles."""
    if not events:
        return []

    ranges: list[tuple[int, int]] = []
    start_idx = 0
    for idx, evt in enumerate(events):
        if evt.event_type == "restarted" and idx > 0:
            ranges.append((start_idx, idx - 1))
            start_idx = idx

    ranges.append((start_idx, len(events) - 1))
    return ranges


def _event_position_key(evt: SkillEventRecord, artifacts: LoadedExtractArtifacts) -> tuple[str, int] | None:
    if not evt.evidence_span_ids:
        return None
    positions: list[tuple[str, int]] = []
    for span_id in evt.evidence_span_ids:
        span = artifacts.span_index.get(span_id)
        if span is None:
            continue
        positions.append((span.document_id, (span.start_line * 1000) + (span.start_char or 0)))
    return min(positions, key=lambda item: item[1]) if positions else None


def _assertion_position_key(ca, artifacts: LoadedExtractArtifacts) -> tuple[str, int] | None:
    if not ca.evidence_span_ids:
        return None
    positions: list[tuple[str, int]] = []
    for span_id in ca.evidence_span_ids:
        span = artifacts.span_index.get(span_id)
        if span is None:
            continue
        positions.append((span.document_id, (span.start_line * 1000) + (span.start_char or 0)))
    return min(positions, key=lambda item: item[1]) if positions else None


def _cycle_position_bounds(
    events: list[SkillEventRecord],
    cycle_start: int,
    cycle_end: int,
    positions_by_index: dict[int, tuple[str, int] | None],
    doc_key: str,
) -> tuple[int, int] | None:
    positions = [
        pos[1]
        for idx, pos in positions_by_index.items()
        if cycle_start <= idx <= cycle_end and pos is not None and pos[0] == doc_key
    ]
    if not positions:
        return None
    return min(positions), max(positions)


def _active_counts_for_cycle(
    events: list[SkillEventRecord],
    cycle_start: int,
    cycle_end: int,
    bidder_ids: set[str],
) -> dict[int, int]:
    """Track bidder state within one cycle; restart starts a fresh inactive state."""
    counts: dict[int, int] = {}
    active_by_bidder = {bid: False for bid in bidder_ids}

    for idx in range(cycle_start, cycle_end + 1):
        counts[idx] = sum(active_by_bidder.values())
        evt = events[idx]

        if evt.event_type == "restarted":
            active_by_bidder = {bid: False for bid in bidder_ids}
            continue

        actor_ids = set(evt.actor_ids)
        if evt.event_type == "nda":
            for bid in bidder_ids.intersection(actor_ids):
                active_by_bidder[bid] = True
        elif evt.event_type == "drop":
            for bid in bidder_ids.intersection(actor_ids):
                active_by_bidder[bid] = False

    return counts


def _pair_rounds(events: list[SkillEventRecord], actors) -> list[dict]:
    """Pair round announcements with deadlines within restart-delimited cycles."""
    rounds: list[dict] = []
    bidder_ids = {a.actor_id for a in actors.actors if a.role == "bidder"}
    cycle_ranges = _cycle_ranges(events)

    active_counts_by_index: dict[int, int] = {}
    for cycle_start, cycle_end in cycle_ranges:
        active_counts_by_index.update(
            _active_counts_for_cycle(events, cycle_start, cycle_end, bidder_ids)
        )

    for ann_type, deadline_type, scope_override in ROUND_PAIRS:
        for cycle_start, cycle_end in cycle_ranges:
            ann_indices = [
                idx
                for idx in range(cycle_start, cycle_end + 1)
                if events[idx].event_type == ann_type
            ]
            for pos, idx in enumerate(ann_indices):
                next_same_family_idx = (
                    ann_indices[pos + 1] if pos + 1 < len(ann_indices) else cycle_end + 1
                )
                deadline_id = None
                for j in range(idx + 1, next_same_family_idx):
                    if events[j].event_type == deadline_type:
                        deadline_id = events[j].event_id
                        break

                active = active_counts_by_index.get(idx, 0)
                invited = events[idx].invited_actor_ids or []
                is_selective = len(invited) < active and len(invited) > 0

                rounds.append({
                    "announcement_event_id": events[idx].event_id,
                    "deadline_event_id": deadline_id,
                    "round_scope": scope_override,
                    "invited_actor_ids": invited,
                    "active_bidders_at_time": active,
                    "is_selective": is_selective,
                })

    return rounds


def _has_best_and_final_language(evt: SkillEventRecord) -> bool:
    text_parts = [evt.summary, *evt.notes]
    text = " ".join(part.lower() for part in text_parts if part)
    return any(marker in text for marker in BEST_AND_FINAL_MARKERS)


def _classify_proposal(
    evt: SkillEventRecord,
    rounds: list[dict],
    event_order: list[str],
) -> BidClassification:
    """Apply deterministic bid classification. Residual -> Uncertain."""
    sig = evt.formality_signals
    if not sig:
        return BidClassification(
            label="Uncertain",
            rule_applied=None,
            basis="No formality_signals; residual case.",
        )

    # Rule 1: Explicit formal signals (strongest evidence)
    if (
        sig.includes_draft_merger_agreement
        or sig.includes_marked_up_agreement
        or sig.mentions_binding_offer
    ):
        return BidClassification(
            label="Formal",
            rule_applied=1,
            basis="Observable formal signal from formality_signals.",
        )

    # Rule 2: Process position unless the event is only a range IOI without finality language
    if (sig.after_final_round_deadline or sig.after_final_round_announcement) and (
        not sig.contains_range or _has_best_and_final_language(evt)
    ):
        if sig.contains_range:
            basis = (
                "Range proposal submitted in final-round context and described as "
                "best-and-final."
            )
        else:
            basis = (
                "Proposal after final round announcement/deadline; "
                "process position overrides informal language."
            )
        return BidClassification(
            label="Formal",
            rule_applied=2,
            basis=basis,
        )

    # Rule 3: Informal signals
    if (
        sig.contains_range
        or sig.mentions_indication_of_interest
        or sig.mentions_preliminary
        or sig.mentions_non_binding
    ):
        return BidClassification(
            label="Informal",
            rule_applied=3,
            basis="Observable informal signal from formality_signals.",
        )

    # Rule 4: Formal after selective round
    evt_idx = event_order.index(evt.event_id) if evt.event_id in event_order else -1
    for r in reversed(rounds):
        ann_idx = event_order.index(r["announcement_event_id"]) if r["announcement_event_id"] in event_order else -1
        if ann_idx >= 0 and evt_idx > ann_idx and r.get("is_selective"):
            return BidClassification(
                label="Formal",
                rule_applied=4,
                basis="Proposal after selective final round.",
            )

    # Rule 5: Residual -> Uncertain
    return BidClassification(
        label="Uncertain",
        rule_applied=None,
        basis="No deterministic rule matched; residual case.",
    )


def _classify_proposals(
    events: list[SkillEventRecord],
    rounds: list[dict],
) -> dict[str, dict]:
    event_order = [e.event_id for e in events]
    result: dict[str, dict] = {}
    for evt in events:
        if evt.event_type != "proposal":
            continue
        cls = _classify_proposal(evt, rounds, event_order)
        result[evt.event_id] = cls.model_dump(mode="json")
    return result


def _segment_cycles(events: list[SkillEventRecord]) -> list[dict]:
    """Segment events into cycles by restarted boundaries. terminated alone does not create a cycle."""
    if not events:
        return []

    cycle_ranges = _cycle_ranges(events)
    has_restarted = any(e.event_type == "restarted" for e in events)
    if len(cycle_ranges) == 1 and not has_restarted:
        has_terminated = any(e.event_type == "terminated" for e in events)
        boundary_basis = (
            "Single cycle -- terminated but no restart."
            if has_terminated
            else "Single cycle -- no termination events"
        )
        return [{
            "cycle_id": "cycle_1",
            "start_event_id": events[0].event_id,
            "end_event_id": events[-1].event_id,
            "boundary_basis": boundary_basis,
        }]

    cycles: list[dict] = []
    for cycle_num, (start_idx, end_idx) in enumerate(cycle_ranges, start=1):
        boundary_basis = "Restarted event." if cycle_num < len(cycle_ranges) else "Final cycle."
        cycles.append({
            "cycle_id": f"cycle_{cycle_num}",
            "start_event_id": events[start_idx].event_id,
            "end_event_id": events[end_idx].event_id,
            "boundary_basis": boundary_basis,
        })

    return cycles


def _compute_formal_boundary(
    cycles: list[dict],
    bid_classifications: dict[str, dict],
    events: list[SkillEventRecord],
) -> dict[str, dict]:
    """First Formal proposal per cycle creates boundary; else event_id null."""
    event_order = [e.event_id for e in events]
    result: dict[str, dict] = {}

    for cyc in cycles:
        cid = cyc["cycle_id"]
        start_id = cyc["start_event_id"]
        end_id = cyc["end_event_id"]
        try:
            start_idx = event_order.index(start_id)
            end_idx = event_order.index(end_id)
        except ValueError:
            result[cid] = {"event_id": None, "basis": "Cycle bounds not found in events."}
            continue

        first_formal_id = None
        for eid in event_order[start_idx : end_idx + 1]:
            cls = bid_classifications.get(eid)
            if cls and cls.get("label") == "Formal":
                first_formal_id = eid
                break

        if first_formal_id:
            result[cid] = {
                "event_id": first_formal_id,
                "basis": f"First formal proposal in cycle: {first_formal_id}.",
            }
        else:
            result[cid] = {
                "event_id": None,
                "basis": "No formal proposals in this cycle.",
            }

    return result


def _populate_invited_from_count_assertions(
    events: list[SkillEventRecord],
    artifacts: LoadedExtractArtifacts,
) -> None:
    """Populate invited_actor_ids on round announcement events from count_assertions.

    Mutates events in place. Only acts on assertions with subject 'final_round_invitees'
    whose anchor text can be matched to actors in the roster.
    """
    actors = artifacts.actors
    invitee_assertions = [
        ca for ca in actors.count_assertions if ca.subject == "final_round_invitees"
    ]
    if not invitee_assertions:
        return

    # Build name -> actor_id lookup (display_name, canonical_name, aliases)
    name_to_id: dict[str, str] = {}
    for actor in actors.actors:
        if actor.role != "bidder":
            continue
        name_to_id[actor.display_name.lower()] = actor.actor_id
        name_to_id[actor.canonical_name.lower()] = actor.actor_id
        for alias in actor.aliases:
            name_to_id[alias.lower()] = actor.actor_id

    # Round announcement event types
    ann_types = {"final_round_ann", "final_round_inf_ann", "final_round_ext_ann"}
    cycle_ranges = _cycle_ranges(events)
    event_positions = {idx: _event_position_key(evt, artifacts) for idx, evt in enumerate(events)}
    span_index = artifacts.span_index

    for ca in invitee_assertions:
        # Try to match actor names from anchor text
        matched_ids: list[str] = []
        anchors = []
        for span_id in ca.evidence_span_ids:
            span = span_index.get(span_id)
            if span and span.anchor_text:
                anchors.append(span.anchor_text.lower())

        for anchor in anchors:
            for name, aid in name_to_id.items():
                if name in anchor and aid not in matched_ids:
                    matched_ids.append(aid)

        if not matched_ids:
            continue

        assertion_position = _assertion_position_key(ca, artifacts)
        if assertion_position is None:
            continue

        best_choice: tuple[int, int] | None = None
        best_idx: int | None = None

        for cycle_start, cycle_end in cycle_ranges:
            cycle_bounds = _cycle_position_bounds(
                events,
                cycle_start,
                cycle_end,
                event_positions,
                assertion_position[0],
            )
            if cycle_bounds is None:
                continue

            cycle_min, cycle_max = cycle_bounds
            if assertion_position[1] < cycle_min or assertion_position[1] > cycle_max:
                continue

            candidate_indices: list[tuple[int, int]] = []
            for idx in range(cycle_start, cycle_end + 1):
                evt = events[idx]
                if evt.event_type not in ann_types or evt.invited_actor_ids:
                    continue
                evt_position = event_positions.get(idx)
                if evt_position is None or evt_position[0] != assertion_position[0]:
                    continue
                candidate_indices.append((idx, abs(assertion_position[1] - evt_position[1])))

            if not candidate_indices:
                continue

            candidate_idx, candidate_distance = min(
                candidate_indices,
                key=lambda item: (item[1], -item[0]),
            )
            choice = (candidate_distance, -candidate_idx)
            if best_choice is None or choice < best_choice:
                best_choice = choice
                best_idx = candidate_idx

        if best_idx is not None:
            events[best_idx].invited_actor_ids = matched_ids


_BIDDER_WITHDRAWAL_SIGNALS = (
    "could not improve",
    "would not improve",
    "would not be in a position",
    "no longer interested",
    "unable to proceed",
    "would not move forward",
    "not prepared to move forward",
    "declined to improve",
    "was not able to increase",
    "not in a position to actively conduct",
    "could not increase",
    "would not continue",
    "cannot proceed",
    "would not proceed",
)

_TARGET_EXCLUSION_SIGNALS = (
    "did not invite",
    "determined not to invite",
    "determined not to include",
    "excluded from",
    "not selected to participate",
    "was not invited",
    "were not invited",
    "not included in",
    "narrowed the field",
    "reduced the group",
)


def _is_bidder_signaled_withdrawal(drop_reason_text: str | None) -> bool:
    """Return True when the filing grounds the drop in bidder-initiated withdrawal."""
    if not drop_reason_text:
        return False
    lower = drop_reason_text.lower()
    return any(signal in lower for signal in _BIDDER_WITHDRAWAL_SIGNALS)


def _has_target_exclusion_language(drop_reason_text: str | None) -> bool:
    if not drop_reason_text:
        return False
    lower = drop_reason_text.lower()
    return any(signal in lower for signal in _TARGET_EXCLUSION_SIGNALS)


def _cycle_range_for_index(
    cycle_ranges: list[tuple[int, int]],
    idx: int,
) -> tuple[int, int] | None:
    for cycle_start, cycle_end in cycle_ranges:
        if cycle_start <= idx <= cycle_end:
            return cycle_start, cycle_end
    return None


def _was_actor_active_before_index(
    events: list[SkillEventRecord],
    *,
    actor_id: str,
    cycle_start: int,
    target_idx: int,
) -> bool:
    """Track NDA/drop state for one bidder within a cycle up to a target event."""
    active = False
    for idx in range(cycle_start, target_idx):
        evt = events[idx]
        if evt.event_type == "restarted":
            active = False
            continue
        if actor_id not in evt.actor_ids:
            continue
        if evt.event_type == "nda":
            active = True
        elif evt.event_type == "drop":
            active = False
    return active


def _classify_dropouts(
    events: list[SkillEventRecord],
    rounds: list[dict],
) -> dict[str, dict]:
    """Deterministically emit sparse DropTarget labels from filing-grounded exclusion."""
    if not events:
        return {}

    event_order = [evt.event_id for evt in events]
    index_by_event = {event_id: idx for idx, event_id in enumerate(event_order)}
    cycle_ranges = _cycle_ranges(events)
    result: dict[str, dict] = {}

    for drop_idx, evt in enumerate(events):
        if evt.event_type != "drop":
            continue
        if _is_bidder_signaled_withdrawal(evt.drop_reason_text):
            continue
        if not evt.actor_ids:
            continue

        cycle_range = _cycle_range_for_index(cycle_ranges, drop_idx)
        if cycle_range is None:
            continue
        cycle_start, _ = cycle_range

        prior_rounds: list[tuple[int, dict]] = []
        for round_record in rounds:
            ann_id = round_record.get("announcement_event_id")
            ann_idx = index_by_event.get(ann_id)
            if ann_idx is None or ann_idx < cycle_start or ann_idx >= drop_idx:
                continue
            if not round_record.get("invited_actor_ids"):
                continue
            prior_rounds.append((ann_idx, round_record))

        if prior_rounds:
            _, round_record = max(prior_rounds, key=lambda item: item[0])
            invited = set(round_record.get("invited_actor_ids") or [])
            excluded_actors = [
                actor_id
                for actor_id in evt.actor_ids
                if actor_id not in invited
                and _was_actor_active_before_index(
                    events,
                    actor_id=actor_id,
                    cycle_start=cycle_start,
                    target_idx=index_by_event[round_record["announcement_event_id"]],
                )
            ]
            if excluded_actors:
                result[evt.event_id] = {
                    "label": "DropTarget",
                    "basis": (
                        "Actor(s) "
                        + ", ".join(excluded_actors)
                        + " were active before round announcement "
                        + str(round_record["announcement_event_id"])
                        + " but absent from invited_actor_ids."
                    ),
                    "source_text": evt.drop_reason_text or "",
                }
                continue

        if _has_target_exclusion_language(evt.drop_reason_text):
            result[evt.event_id] = {
                "label": "DropTarget",
                "basis": "Drop reason text contains explicit target-exclusion language.",
                "source_text": evt.drop_reason_text or "",
            }

    return result


def _infer_all_cash_overrides(
    events: list[SkillEventRecord],
    cycles: list[dict],
) -> dict[str, bool]:
    """Infer cycle-local all-cash overrides when the filing context is unambiguous."""
    if not events or not cycles:
        return {}

    event_order = [evt.event_id for evt in events]
    index_by_event = {event_id: idx for idx, event_id in enumerate(event_order)}
    result: dict[str, bool] = {}

    for cycle in cycles:
        start_id = cycle.get("start_event_id")
        end_id = cycle.get("end_event_id")
        start_idx = index_by_event.get(start_id)
        end_idx = index_by_event.get(end_id)
        if start_idx is None or end_idx is None:
            continue

        cycle_events = events[start_idx : end_idx + 1]
        executed_events = [evt for evt in cycle_events if evt.event_type == "executed"]
        untyped_proposals = [
            evt
            for evt in cycle_events
            if evt.event_type == "proposal"
            and (evt.terms is None or evt.terms.consideration_type is None)
        ]
        if not untyped_proposals:
            continue

        if executed_events:
            executed = executed_events[-1]
            executed_consideration_type = (
                executed.terms.consideration_type if executed.terms else None
            )
            if executed_consideration_type == "cash":
                for evt in untyped_proposals:
                    result[evt.event_id] = True
                continue
            if executed_consideration_type is not None:
                continue

        typed_proposals = [
            evt
            for evt in cycle_events
            if evt.event_type == "proposal"
            and evt.terms is not None
            and evt.terms.consideration_type is not None
        ]
        if executed_events and len(typed_proposals) < 2:
            continue
        if typed_proposals and all(
            evt.terms.consideration_type == "cash" for evt in typed_proposals
        ):
            for evt in untyped_proposals:
                result[evt.event_id] = True

    return result


def run_enrich_core(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    """Run deterministic enrich-core. Writes enrich/deterministic_enrichment.json.

    Returns 0 on success.
    """
    paths = build_skill_paths(deal_slug, project_root=project_root)

    try:
        if not paths.actors_raw_path.exists():
            raise FileNotFoundError(f"Missing required input: {paths.actors_raw_path}")
        if not paths.events_raw_path.exists():
            raise FileNotFoundError(f"Missing required input: {paths.events_raw_path}")

        _require_gate_artifacts(paths)
        artifacts = load_extract_artifacts(paths)
        if artifacts.mode != "canonical":
            raise ValueError(
                "enrich-core requires canonical extract artifacts with spans.json. "
                "Run 'skill-pipeline canonicalize --deal <slug>' first."
            )
        actors = artifacts.actors
        events = artifacts.events.events

        _populate_invited_from_count_assertions(events, artifacts)

        rounds = _pair_rounds(events, actors)
        bid_classifications = _classify_proposals(events, rounds)
        cycles = _segment_cycles(events)
        formal_boundary = _compute_formal_boundary(cycles, bid_classifications, events)
        dropout_classifications = _classify_dropouts(events, rounds)
        all_cash_overrides = _infer_all_cash_overrides(events, cycles)

        ensure_output_directories(paths, include_legacy=True)
        _write_json(
            paths.deterministic_enrichment_path,
            {
                "rounds": rounds,
                "bid_classifications": bid_classifications,
                "cycles": cycles,
                "formal_boundary": formal_boundary,
                "dropout_classifications": dropout_classifications,
                "all_cash_overrides": all_cash_overrides,
            },
        )
    except Exception:
        _invalidate_enrich_outputs(paths)
        raise
    return 0
