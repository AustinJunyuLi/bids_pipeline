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
