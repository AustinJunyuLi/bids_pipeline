"""Deterministic canonicalization: dedup, NDA-gate, unnamed-party recovery."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.models import SkillActorsArtifact, SkillEventsArtifact
from skill_pipeline.paths import build_skill_paths, ensure_output_directories


def _normalize_date(date_hint: dict) -> str:
    """Extract YYYY-MM-DD from normalized_hint or raw_text."""
    hint = date_hint.get("normalized_hint") or date_hint.get("raw_text") or ""
    match = re.search(r"\d{4}-\d{2}-\d{2}", str(hint))
    return match.group(0) if match else str(hint)[:10]


def _dedup_events(events: list[dict]) -> tuple[list[dict], dict[str, str]]:
    """Collapse duplicate events. Returns (deduped_events, dedup_log).

    Duplicates match on: same event_type, same normalized date, same actor_ids
    set, and at least one shared block_id in evidence_refs.
    """
    dedup_log: dict[str, str] = {}

    # Group by (event_type, normalized_date, frozenset(actor_ids))
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for evt in events:
        key = (
            evt["event_type"],
            _normalize_date(evt["date"]),
            frozenset(evt.get("actor_ids", [])),
        )
        groups[key].append(evt)

    kept: list[dict] = []
    for key, group in groups.items():
        if len(group) == 1:
            kept.append(group[0])
            continue

        # Cluster by overlapping block_ids
        clusters: list[list[dict]] = []
        for evt in group:
            evt_blocks = {r.get("block_id") for r in evt.get("evidence_refs", []) if r.get("block_id")}
            merged = False
            for cluster in clusters:
                cluster_blocks: set[str] = set()
                for ce in cluster:
                    for r in ce.get("evidence_refs", []):
                        if r.get("block_id"):
                            cluster_blocks.add(r["block_id"])
                if evt_blocks & cluster_blocks:
                    cluster.append(evt)
                    merged = True
                    break
            if not merged:
                clusters.append([evt])

        for cluster in clusters:
            if len(cluster) == 1:
                kept.append(cluster[0])
            else:
                # Keep the event with the longest summary
                survivor = max(cluster, key=lambda e: len(e.get("summary", "")))
                # Merge evidence_refs
                seen_refs: set[tuple] = set()
                merged_refs: list[dict] = []
                for evt in cluster:
                    for ref in evt.get("evidence_refs", []):
                        ref_key = (ref.get("block_id"), ref.get("evidence_id"), ref.get("anchor_text"))
                        if ref_key not in seen_refs:
                            seen_refs.add(ref_key)
                            merged_refs.append(ref)
                survivor["evidence_refs"] = merged_refs
                # Union notes
                all_notes: list[str] = []
                for evt in cluster:
                    for n in evt.get("notes", []):
                        if n not in all_notes:
                            all_notes.append(n)
                survivor["notes"] = all_notes
                kept.append(survivor)
                for evt in cluster:
                    if evt["event_id"] != survivor["event_id"]:
                        dedup_log[evt["event_id"]] = survivor["event_id"]

    # Preserve original order
    id_order = {evt["event_id"]: i for i, evt in enumerate(events)}
    kept.sort(key=lambda e: id_order.get(e["event_id"], 0))

    return kept, dedup_log


def _gate_drops_by_nda(events: list[dict]) -> tuple[list[dict], list[dict]]:
    """Remove drop events for actors without a prior NDA. Returns (filtered, log)."""
    nda_actors: set[str] = set()
    for evt in events:
        if evt["event_type"] == "nda":
            nda_actors.update(evt.get("actor_ids", []))

    kept: list[dict] = []
    gate_log: list[dict] = []
    for evt in events:
        if evt["event_type"] == "drop":
            drop_actors = set(evt.get("actor_ids", []))
            if not drop_actors or not drop_actors.issubset(nda_actors):
                missing = drop_actors - nda_actors if drop_actors else {"(empty)"}
                gate_log.append({
                    "removed_event_id": evt["event_id"],
                    "reason": f"Drop actor(s) {missing} have no prior NDA.",
                })
                continue
        kept.append(evt)

    return kept, gate_log


_KIND_SUBJECTS = {
    "financial": "nda_signed_financial_buyers",
    "strategic": "nda_signed_strategic_buyers",
}


def _recover_unnamed_parties(
    actors_dict: dict,
    events: list[dict],
) -> tuple[dict, list[dict], list[dict]]:
    """Synthesize placeholder actors and events from count_assertion gaps.

    Returns (updated_actors_dict, new_events, recovery_log).
    Fail-closed: only creates placeholders when count_assertions and
    unresolved_mentions agree.
    """
    recovery_log: list[dict] = []
    new_events: list[dict] = []

    nda_actor_ids: set[str] = set()
    for evt in events:
        if evt["event_type"] == "nda":
            nda_actor_ids.update(evt.get("actor_ids", []))

    for kind, subject in _KIND_SUBJECTS.items():
        assertions = [ca for ca in actors_dict.get("count_assertions", []) if ca["subject"] == subject]
        if not assertions:
            continue
        asserted_count = assertions[0]["count"]
        actual_count = sum(
            1 for a in actors_dict["actors"]
            if a.get("bidder_kind") == kind and a["role"] == "bidder" and a["actor_id"] in nda_actor_ids
        )
        gap = asserted_count - actual_count
        if gap <= 0:
            continue

        # Search unresolved_mentions for matching description
        matching_mentions = [
            m for m in actors_dict.get("unresolved_mentions", [])
            if kind in m.lower() and ("sponsor" in m.lower() or "buyer" in m.lower() or "bidder" in m.lower())
        ]
        if not matching_mentions:
            continue

        for i in range(min(gap, len(matching_mentions))):
            placeholder_id = f"placeholder_{kind}_{i + 1}"
            mention = matching_mentions[i]
            has_drop = "declined" in mention.lower() or "dropped" in mention.lower()

            placeholder_actor = {
                "actor_id": placeholder_id,
                "display_name": f"Another {kind} sponsor",
                "canonical_name": f"ANOTHER {kind.upper()} SPONSOR",
                "aliases": [],
                "role": "bidder",
                "advisor_kind": None,
                "advised_actor_id": None,
                "bidder_kind": kind,
                "listing_status": "private",
                "geography": "domestic",
                "is_grouped": False,
                "group_size": None,
                "group_label": None,
                "evidence_refs": [],
                "notes": [f"Synthesized from unresolved_mention: {mention}"],
            }
            actors_dict["actors"].append(placeholder_actor)

            nda_event = {
                "event_id": f"{placeholder_id}_nda",
                "event_type": "nda",
                "date": {"raw_text": "unknown", "normalized_hint": None},
                "actor_ids": [placeholder_id],
                "summary": f"Placeholder NDA for {placeholder_id}.",
                "evidence_refs": [],
                "terms": None,
                "formality_signals": None,
                "whole_company_scope": None,
                "drop_reason_text": None,
                "round_scope": None,
                "invited_actor_ids": [],
                "deadline_date": None,
                "executed_with_actor_id": None,
                "boundary_note": None,
                "nda_signed": True,
                "notes": ["Synthesized from count_assertion gap."],
            }
            new_events.append(nda_event)

            if has_drop:
                drop_event = {
                    "event_id": f"{placeholder_id}_drop",
                    "event_type": "drop",
                    "date": {"raw_text": "unknown", "normalized_hint": None},
                    "actor_ids": [placeholder_id],
                    "summary": f"Placeholder drop: {mention}",
                    "evidence_refs": [],
                    "terms": None,
                    "formality_signals": None,
                    "whole_company_scope": None,
                    "drop_reason_text": mention,
                    "round_scope": None,
                    "invited_actor_ids": [],
                    "deadline_date": None,
                    "executed_with_actor_id": None,
                    "boundary_note": None,
                    "nda_signed": None,
                    "notes": ["Synthesized from count_assertion gap."],
                }
                new_events.append(drop_event)

            recovery_log.append({
                "placeholder_id": placeholder_id,
                "kind": kind,
                "source_mention": mention,
                "events_created": [e["event_id"] for e in new_events if placeholder_id in str(e.get("actor_ids"))],
            })

    return actors_dict, new_events, recovery_log


def run_canonicalize(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    """Run canonicalization on extracted skill artifacts.

    Writes canonicalize_log.json. Overwrites actors_raw.json and events_raw.json in place.
    Returns 0 on success.
    """
    paths = build_skill_paths(deal_slug, project_root=project_root)

    if not paths.actors_raw_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.actors_raw_path}")
    if not paths.events_raw_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.events_raw_path}")

    actors = SkillActorsArtifact.model_validate(
        json.loads(paths.actors_raw_path.read_text(encoding="utf-8"))
    )
    events_artifact = SkillEventsArtifact.model_validate(
        json.loads(paths.events_raw_path.read_text(encoding="utf-8"))
    )

    events = events_artifact.model_dump(mode="json")["events"]
    log: dict = {"dedup_log": {}, "nda_gate_log": [], "recovery_log": []}

    events, dedup_log = _dedup_events(events)
    log["dedup_log"] = dedup_log

    events, nda_gate_log = _gate_drops_by_nda(events)
    log["nda_gate_log"] = nda_gate_log

    # Unnamed-party recovery from count_assertion gaps
    actors_dict = actors.model_dump(mode="json")
    actors_dict, new_events, recovery_log = _recover_unnamed_parties(actors_dict, events)
    events.extend(new_events)
    log["recovery_log"] = recovery_log

    # Write back actors (before events)
    paths.actors_raw_path.write_text(
        json.dumps(actors_dict, indent=2), encoding="utf-8"
    )

    # Write back events
    paths.events_raw_path.write_text(
        json.dumps({"events": events, "exclusions": [], "coverage_notes": []}, indent=2),
        encoding="utf-8",
    )

    ensure_output_directories(paths)
    paths.canonicalize_log_path.write_text(
        json.dumps(log, indent=2), encoding="utf-8"
    )
    return 0
