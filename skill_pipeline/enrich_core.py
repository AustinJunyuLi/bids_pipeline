"""Deterministic enrich-core: rounds, bid classification, cycles, formal boundary."""

from __future__ import annotations

import json
from pathlib import Path

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.extract_artifacts import LoadedExtractArtifacts, load_extract_artifacts
from skill_pipeline.models import (
    BidClassification,
    SkillEventRecord,
)
from skill_pipeline.paths import build_skill_paths, ensure_output_directories

ROUND_PAIRS = [
    ("final_round_inf_ann", "final_round_inf", "informal"),
    ("final_round_ann", "final_round", "formal"),
    ("final_round_ext_ann", "final_round_ext", "extension"),
]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _pair_rounds(events: list[SkillEventRecord], actors) -> list[dict]:
    """Pair round announcements with deadlines. Preserve extension rounds as round_scope='extension'."""
    rounds: list[dict] = []
    bidder_ids = {a.actor_id for a in actors.actors if a.role == "bidder"}

    for ann_type, deadline_type, scope_override in ROUND_PAIRS:
        for i, evt in enumerate(events):
            if evt.event_type != ann_type:
                continue
            deadline_id = None
            for j in range(i + 1, len(events)):
                if events[j].event_type == deadline_type:
                    deadline_id = events[j].event_id
                    break

            # active_bidders_at_time: actors with NDA and no prior drop before this announcement
            active = 0
            for bid in bidder_ids:
                has_nda = False
                has_drop = False
                for k in range(i):
                    e = events[k]
                    if e.event_type == "nda" and bid in e.actor_ids:
                        has_nda = True
                    if e.event_type == "drop" and bid in e.actor_ids:
                        has_drop = True
                if has_nda and not has_drop:
                    active += 1

            invited = evt.invited_actor_ids or []
            is_selective = (
                len(invited) < active and len(invited) > 0
            )

            rounds.append({
                "announcement_event_id": evt.event_id,
                "deadline_event_id": deadline_id,
                "round_scope": scope_override,
                "invited_actor_ids": invited,
                "active_bidders_at_time": active,
                "is_selective": is_selective,
            })

    return rounds


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

    # Rule 1: Informal
    if (
        sig.contains_range
        or sig.mentions_indication_of_interest
        or sig.mentions_preliminary
        or sig.mentions_non_binding
    ):
        return BidClassification(
            label="Informal",
            rule_applied=1,
            basis="Observable informal signal from formality_signals.",
        )

    # Rule 2: Formal
    if (
        sig.includes_draft_merger_agreement
        or sig.includes_marked_up_agreement
        or sig.mentions_binding_offer
    ):
        return BidClassification(
            label="Formal",
            rule_applied=2,
            basis="Observable formal signal from formality_signals.",
        )

    # Rule 2.5: After final round with no informal signals
    if sig.after_final_round_deadline or sig.after_final_round_announcement:
        return BidClassification(
            label="Formal",
            rule_applied=2.5,
            basis="Proposal after final round announcement/deadline with no informal signals.",
        )

    # Rule 3: Formal after selective round
    evt_idx = event_order.index(evt.event_id) if evt.event_id in event_order else -1
    for r in reversed(rounds):
        ann_idx = event_order.index(r["announcement_event_id"]) if r["announcement_event_id"] in event_order else -1
        if ann_idx >= 0 and evt_idx > ann_idx and r.get("is_selective"):
            return BidClassification(
                label="Formal",
                rule_applied=3,
                basis="Proposal after selective final round.",
            )

    # Rule 4: Residual -> Uncertain
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

    has_restarted = any(e.event_type == "restarted" for e in events)
    if not has_restarted:
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
    cycle_num = 1
    start_idx = 0

    for i, evt in enumerate(events):
        if evt.event_type == "restarted":
            if i > 0:
                cycles.append({
                    "cycle_id": f"cycle_{cycle_num}",
                    "start_event_id": events[start_idx].event_id,
                    "end_event_id": events[i - 1].event_id,
                    "boundary_basis": "Restarted event.",
                })
                cycle_num += 1
            start_idx = i

    if start_idx < len(events):
        cycles.append({
            "cycle_id": f"cycle_{cycle_num}",
            "start_event_id": events[start_idx].event_id,
            "end_event_id": events[-1].event_id,
            "boundary_basis": "Final cycle.",
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
    if artifacts.mode == "legacy":
        actors = artifacts.raw_actors
        invitee_assertions = [
            ca for ca in actors.count_assertions if ca.subject == "final_round_invitees"
        ]
    else:
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

    for ca in invitee_assertions:
        # Try to match actor names from anchor text
        matched_ids: list[str] = []
        if artifacts.mode == "legacy":
            anchors = [ref.anchor_text.lower() for ref in ca.evidence_refs]
        else:
            span_index = artifacts.span_index
            anchors = [
                span_index[span_id].anchor_text.lower()
                for span_id in ca.evidence_span_ids
                if span_id in span_index and span_index[span_id].anchor_text
            ]

        for anchor in anchors:
            for name, aid in name_to_id.items():
                if name in anchor and aid not in matched_ids:
                    matched_ids.append(aid)

        if not matched_ids:
            continue

        # Find the best matching round announcement event (with empty invited_actor_ids)
        for evt in events:
            if evt.event_type in ann_types and not evt.invited_actor_ids:
                evt.invited_actor_ids = matched_ids
                break  # Only populate the first matching empty announcement


def run_enrich_core(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    """Run deterministic enrich-core. Writes enrich/deterministic_enrichment.json.

    Returns 0 on success.
    """
    paths = build_skill_paths(deal_slug, project_root=project_root)

    if not paths.actors_raw_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.actors_raw_path}")
    if not paths.events_raw_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.events_raw_path}")

    artifacts = load_extract_artifacts(paths)
    actors = artifacts.raw_actors if artifacts.mode == "legacy" else artifacts.actors
    events = artifacts.raw_events.events if artifacts.mode == "legacy" else artifacts.events.events

    _populate_invited_from_count_assertions(events, artifacts)

    rounds = _pair_rounds(events, actors)
    bid_classifications = _classify_proposals(events, rounds)
    cycles = _segment_cycles(events)
    formal_boundary = _compute_formal_boundary(cycles, bid_classifications, events)

    ensure_output_directories(paths)
    _write_json(
        paths.deterministic_enrichment_path,
        {
            "rounds": rounds,
            "bid_classifications": bid_classifications,
            "cycles": cycles,
            "formal_boundary": formal_boundary,
        },
    )
    return 0
