"""Deterministic canonicalization: schema upgrade, dedup, NDA-gate, unnamed-party recovery."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.models import (
    RawSkillActorsArtifact,
    RawSkillEventsArtifact,
    ResolvedDate,
    SkillActorsArtifact,
    SkillEventsArtifact,
    SpanRegistryArtifact,
)
from skill_pipeline.normalize.dates import parse_resolved_date
from skill_pipeline.paths import build_skill_paths, ensure_output_directories
from skill_pipeline.pipeline_models.common import DatePrecision
from skill_pipeline.pipeline_models.source import ChronologyBlock, EvidenceItem
from skill_pipeline.provenance import resolve_text_span


def _load_document_lines(filings_dir: Path) -> dict[str, list[str]]:
    if not filings_dir.exists():
        raise FileNotFoundError(
            f"Raw filings directory not found: {filings_dir}. "
            "Run 'skill-pipeline raw-fetch --deal <slug>' first."
        )
    lines_by_document: dict[str, list[str]] = {}
    for path in filings_dir.glob("*.txt"):
        lines_by_document[path.stem] = path.read_text(encoding="utf-8").splitlines()
    return lines_by_document


def _load_chronology_blocks(path: Path) -> list[ChronologyBlock]:
    blocks: list[ChronologyBlock] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        blocks.append(ChronologyBlock.model_validate_json(line))
    return blocks


def _load_evidence_items(path: Path) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        items.append(EvidenceItem.model_validate_json(line))
    return items


def _load_document_registry(path: Path) -> dict[str, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    documents = payload.get("documents", [])
    return {
        document["document_id"]: {
            "accession_number": document.get("accession_number"),
            "filing_type": document.get("filing_type", "UNKNOWN"),
        }
        for document in documents
        if document.get("document_id")
    }


def _normalize_date(date_payload: dict) -> str:
    for key in ("sort_date", "normalized_start", "raw_text"):
        value = date_payload.get(key)
        if value:
            return str(value)
    return ""


def _canonical_unknown_date() -> dict:
    return ResolvedDate(
        raw_text="unknown",
        precision=DatePrecision.UNKNOWN,
    ).model_dump(mode="json")


def _convert_raw_date(
    date_payload: dict | None,
    *,
    anchor_date: ResolvedDate | None = None,
    anchor_event_id: str | None = None,
) -> dict | None:
    if date_payload is None:
        return None
    raw_text = date_payload.get("raw_text")
    normalized_hint = date_payload.get("normalized_hint")
    source_text = raw_text
    if not source_text or source_text == "unknown":
        source_text = normalized_hint or raw_text
    return parse_resolved_date(
        source_text,
        anchor_date=anchor_date,
        anchor_event_id=anchor_event_id,
    ).model_dump(mode="json")


def _resolve_ref_to_span_id(
    ref: dict,
    *,
    blocks_by_id: dict[str, ChronologyBlock],
    evidence_by_id: dict[str, EvidenceItem],
    document_lines: dict[str, list[str]],
    document_meta: dict[str, dict],
    span_id_by_key: dict[tuple[str | None, str | None, str], str],
    spans: list[dict],
) -> str:
    key = (ref.get("block_id"), ref.get("evidence_id"), ref["anchor_text"])
    existing = span_id_by_key.get(key)
    if existing is not None:
        return existing

    block_id = ref.get("block_id")
    evidence_id = ref.get("evidence_id")
    block_ids: list[str] = []
    evidence_ids: list[str] = []
    if evidence_id:
        evidence_item = evidence_by_id.get(evidence_id)
        if evidence_item is None:
            raise ValueError(f"Unknown evidence_id in evidence reference: {evidence_id!r}")

        document_id = evidence_item.document_id
        accession_number = evidence_item.accession_number
        filing_type = evidence_item.filing_type
        start_line = evidence_item.start_line
        end_line = evidence_item.end_line
        evidence_ids = [evidence_item.evidence_id]

        if block_id:
            block = blocks_by_id.get(block_id)
            if block is None:
                raise ValueError(
                    f"Mismatched evidence reference: block_id={block_id!r} evidence_id={evidence_id!r}"
                )
            if block.document_id != evidence_item.document_id or not (
                block.start_line <= evidence_item.start_line <= evidence_item.end_line <= block.end_line
            ):
                raise ValueError(
                    f"Mismatched evidence reference: block_id={block_id!r} evidence_id={evidence_id!r}"
                )
            block_ids = [block.block_id]
    elif block_id and block_id in blocks_by_id:
        block = blocks_by_id[block_id]
        document_id = block.document_id
        meta = document_meta.get(document_id, {})
        accession_number = meta.get("accession_number")
        filing_type = meta.get("filing_type", "UNKNOWN")
        start_line = block.start_line
        end_line = block.end_line
        block_ids = [block.block_id]
    else:
        raise ValueError(
            f"Unknown evidence reference: block_id={ref.get('block_id')!r} evidence_id={ref.get('evidence_id')!r}"
        )

    raw_lines = document_lines.get(document_id)
    if raw_lines is None:
        raise FileNotFoundError(f"Missing filing text for document_id {document_id!r}.")

    span_id = f"span_{len(spans) + 1:04d}"
    span = resolve_text_span(
        raw_lines,
        start_line=start_line,
        end_line=end_line,
        block_ids=block_ids,
        evidence_ids=evidence_ids,
        anchor_text=ref["anchor_text"],
        document_id=document_id,
        accession_number=accession_number,
        filing_type=filing_type,
        span_id=span_id,
    )
    spans.append(span.model_dump(mode="json"))
    span_id_by_key[key] = span_id
    return span_id


def _upgrade_raw_actors(
    actors_artifact: RawSkillActorsArtifact,
    *,
    blocks_by_id: dict[str, ChronologyBlock],
    evidence_by_id: dict[str, EvidenceItem],
    document_lines: dict[str, list[str]],
    document_meta: dict[str, dict],
    span_id_by_key: dict[tuple[str | None, str | None, str], str],
    spans: list[dict],
) -> dict:
    actors_payload = actors_artifact.model_dump(mode="json")
    for actor in actors_payload["actors"]:
        actor["evidence_span_ids"] = [
            _resolve_ref_to_span_id(
                ref,
                blocks_by_id=blocks_by_id,
                evidence_by_id=evidence_by_id,
                document_lines=document_lines,
                document_meta=document_meta,
                span_id_by_key=span_id_by_key,
                spans=spans,
            )
            for ref in actor.pop("evidence_refs", [])
        ]

    for assertion in actors_payload.get("count_assertions", []):
        assertion["evidence_span_ids"] = [
            _resolve_ref_to_span_id(
                ref,
                blocks_by_id=blocks_by_id,
                evidence_by_id=evidence_by_id,
                document_lines=document_lines,
                document_meta=document_meta,
                span_id_by_key=span_id_by_key,
                spans=spans,
            )
            for ref in assertion.pop("evidence_refs", [])
        ]

    return actors_payload


def _upgrade_raw_events(
    events_artifact: RawSkillEventsArtifact,
    *,
    blocks_by_id: dict[str, ChronologyBlock],
    evidence_by_id: dict[str, EvidenceItem],
    document_lines: dict[str, list[str]],
    document_meta: dict[str, dict],
    span_id_by_key: dict[tuple[str | None, str | None, str], str],
    spans: list[dict],
) -> dict:
    events_payload = events_artifact.model_dump(mode="json")
    previous_resolved_date: ResolvedDate | None = None
    previous_event_id: str | None = None

    for event in events_payload["events"]:
        event["evidence_span_ids"] = [
            _resolve_ref_to_span_id(
                ref,
                blocks_by_id=blocks_by_id,
                evidence_by_id=evidence_by_id,
                document_lines=document_lines,
                document_meta=document_meta,
                span_id_by_key=span_id_by_key,
                spans=spans,
            )
            for ref in event.pop("evidence_refs", [])
        ]
        event["date"] = _convert_raw_date(
            event.get("date"),
            anchor_date=previous_resolved_date,
            anchor_event_id=previous_event_id,
        )
        if event.get("deadline_date") is not None:
            event["deadline_date"] = _convert_raw_date(
                event["deadline_date"],
                anchor_date=ResolvedDate.model_validate(event["date"]) if event.get("date") else previous_resolved_date,
                anchor_event_id=event["event_id"],
            )
        if event.get("date"):
            resolved = ResolvedDate.model_validate(event["date"])
            if resolved.sort_date is not None:
                previous_resolved_date = resolved
                previous_event_id = event["event_id"]

    return events_payload


def _dedup_events(events: list[dict]) -> tuple[list[dict], dict[str, str]]:
    dedup_log: dict[str, str] = {}

    groups: dict[tuple, list[dict]] = defaultdict(list)
    for evt in events:
        key = (
            evt["event_type"],
            _normalize_date(evt["date"]),
            frozenset(evt.get("actor_ids", [])),
        )
        groups[key].append(evt)

    kept: list[dict] = []
    for group in groups.values():
        if len(group) == 1:
            kept.append(group[0])
            continue

        clusters: list[list[dict]] = []
        for evt in group:
            evt_spans = set(evt.get("evidence_span_ids", []))
            merged = False
            for cluster in clusters:
                cluster_spans: set[str] = set()
                for cluster_event in cluster:
                    cluster_spans.update(cluster_event.get("evidence_span_ids", []))
                if evt_spans & cluster_spans:
                    cluster.append(evt)
                    merged = True
                    break
            if not merged:
                clusters.append([evt])

        for cluster in clusters:
            if len(cluster) == 1:
                kept.append(cluster[0])
                continue

            by_semantics: dict[str, list[dict]] = defaultdict(list)
            for event in cluster:
                by_semantics[_event_semantics_key(event)].append(event)

            for semantic_group in by_semantics.values():
                if len(semantic_group) == 1:
                    kept.append(semantic_group[0])
                    continue

                survivor = max(semantic_group, key=lambda event: len(event.get("summary", "")))
                merged_span_ids: list[str] = []
                for event in semantic_group:
                    for span_id in event.get("evidence_span_ids", []):
                        if span_id not in merged_span_ids:
                            merged_span_ids.append(span_id)
                survivor["evidence_span_ids"] = merged_span_ids
                merged_notes: list[str] = []
                for event in semantic_group:
                    for note in event.get("notes", []):
                        if note not in merged_notes:
                            merged_notes.append(note)
                survivor["notes"] = merged_notes
                kept.append(survivor)
                for event in semantic_group:
                    if event["event_id"] != survivor["event_id"]:
                        dedup_log[event["event_id"]] = survivor["event_id"]

    id_order = {event["event_id"]: index for index, event in enumerate(events)}
    kept.sort(key=lambda event: id_order.get(event["event_id"], 0))
    return kept, dedup_log


def _event_semantics_key(event: dict) -> str:
    semantics = {
        "event_type": event.get("event_type"),
        "date": event.get("date"),
        "actor_ids": sorted(event.get("actor_ids", [])),
        "terms": event.get("terms"),
        "formality_signals": event.get("formality_signals"),
        "whole_company_scope": event.get("whole_company_scope"),
        "drop_reason_text": event.get("drop_reason_text"),
        "round_scope": event.get("round_scope"),
        "invited_actor_ids": sorted(event.get("invited_actor_ids", [])),
        "deadline_date": event.get("deadline_date"),
        "executed_with_actor_id": event.get("executed_with_actor_id"),
        "boundary_note": event.get("boundary_note"),
        "nda_signed": event.get("nda_signed"),
    }
    return json.dumps(semantics, sort_keys=True)


def _gate_drops_by_nda(events: list[dict]) -> tuple[list[dict], list[dict]]:
    nda_actors_seen: set[str] = set()
    kept: list[dict] = []
    gate_log: list[dict] = []
    for event in events:
        if event["event_type"] == "drop":
            drop_actors = set(event.get("actor_ids", []))
            if not drop_actors or not drop_actors.issubset(nda_actors_seen):
                missing = drop_actors - nda_actors_seen if drop_actors else {"(empty)"}
                gate_log.append(
                    {
                        "removed_event_id": event["event_id"],
                        "reason": f"Drop actor(s) {missing} have no prior NDA.",
                    }
                )
                continue
        kept.append(event)
        if event["event_type"] == "nda":
            nda_actors_seen.update(event.get("actor_ids", []))
    return kept, gate_log


_KIND_SUBJECTS = {
    "financial": "nda_signed_financial_buyers",
    "strategic": "nda_signed_strategic_buyers",
}


def _recover_unnamed_parties(
    actors_dict: dict,
    events: list[dict],
) -> tuple[dict, list[dict], list[dict]]:
    recovery_log: list[dict] = []
    new_events: list[dict] = []

    nda_actor_ids: set[str] = set()
    for event in events:
        if event["event_type"] == "nda":
            nda_actors = event.get("actor_ids", [])
            nda_actor_ids.update(nda_actors)

    for kind, subject in _KIND_SUBJECTS.items():
        assertions = [
            assertion for assertion in actors_dict.get("count_assertions", []) if assertion["subject"] == subject
        ]
        if not assertions:
            continue
        asserted_count = assertions[0]["count"]
        actual_count = sum(
            1
            for actor in actors_dict["actors"]
            if actor.get("bidder_kind") == kind
            and actor["role"] == "bidder"
            and actor["actor_id"] in nda_actor_ids
        )
        gap = asserted_count - actual_count
        if gap <= 0:
            continue

        matching_mentions = [
            mention
            for mention in actors_dict.get("unresolved_mentions", [])
            if kind in mention.lower()
            and ("sponsor" in mention.lower() or "buyer" in mention.lower() or "bidder" in mention.lower())
        ]
        if not matching_mentions:
            continue

        for index in range(min(gap, len(matching_mentions))):
            placeholder_id = f"placeholder_{kind}_{index + 1}"
            mention = matching_mentions[index]
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
                "evidence_span_ids": [],
                "notes": [f"Synthesized from unresolved_mention: {mention}"],
            }
            actors_dict["actors"].append(placeholder_actor)

            nda_event = {
                "event_id": f"{placeholder_id}_nda",
                "event_type": "nda",
                "date": _canonical_unknown_date(),
                "actor_ids": [placeholder_id],
                "summary": f"Placeholder NDA for {placeholder_id}.",
                "evidence_span_ids": [],
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

            created_event_ids = [nda_event["event_id"]]
            if has_drop:
                drop_event = {
                    "event_id": f"{placeholder_id}_drop",
                    "event_type": "drop",
                    "date": _canonical_unknown_date(),
                    "actor_ids": [placeholder_id],
                    "summary": f"Placeholder drop: {mention}",
                    "evidence_span_ids": [],
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
                created_event_ids.append(drop_event["event_id"])

            recovery_log.append(
                {
                    "placeholder_id": placeholder_id,
                    "kind": kind,
                    "source_mention": mention,
                    "events_created": created_event_ids,
                }
            )

    return actors_dict, new_events, recovery_log


def run_canonicalize(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    """Upgrade legacy extract artifacts to canonical provenance, then normalize events."""
    paths = build_skill_paths(deal_slug, project_root=project_root)

    if not paths.actors_raw_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.actors_raw_path}")
    if not paths.events_raw_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.events_raw_path}")
    if not paths.chronology_blocks_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.chronology_blocks_path}")
    if not paths.evidence_items_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.evidence_items_path}")
    if not paths.document_registry_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.document_registry_path}")

    raw_actors = RawSkillActorsArtifact.model_validate(
        json.loads(paths.actors_raw_path.read_text(encoding="utf-8"))
    )
    raw_events = RawSkillEventsArtifact.model_validate(
        json.loads(paths.events_raw_path.read_text(encoding="utf-8"))
    )

    blocks = _load_chronology_blocks(paths.chronology_blocks_path)
    evidence_items = _load_evidence_items(paths.evidence_items_path)
    document_lines = _load_document_lines(paths.raw_root / deal_slug / "filings")
    document_meta = _load_document_registry(paths.document_registry_path)
    blocks_by_id = {block.block_id: block for block in blocks}
    evidence_by_id = {item.evidence_id: item for item in evidence_items}

    spans: list[dict] = []
    span_id_by_key: dict[tuple[str | None, str | None, str], str] = {}
    actors_dict = _upgrade_raw_actors(
        raw_actors,
        blocks_by_id=blocks_by_id,
        evidence_by_id=evidence_by_id,
        document_lines=document_lines,
        document_meta=document_meta,
        span_id_by_key=span_id_by_key,
        spans=spans,
    )
    events_dict = _upgrade_raw_events(
        raw_events,
        blocks_by_id=blocks_by_id,
        evidence_by_id=evidence_by_id,
        document_lines=document_lines,
        document_meta=document_meta,
        span_id_by_key=span_id_by_key,
        spans=spans,
    )

    events = events_dict["events"]
    log: dict = {"dedup_log": {}, "nda_gate_log": [], "recovery_log": []}

    events, dedup_log = _dedup_events(events)
    log["dedup_log"] = dedup_log

    events, nda_gate_log = _gate_drops_by_nda(events)
    log["nda_gate_log"] = nda_gate_log

    actors_dict, new_events, recovery_log = _recover_unnamed_parties(actors_dict, events)
    events.extend(new_events)
    log["recovery_log"] = recovery_log

    canonical_actors = SkillActorsArtifact.model_validate(actors_dict)
    canonical_events = SkillEventsArtifact.model_validate(
        {
            "events": events,
            "exclusions": events_dict.get("exclusions", []),
            "coverage_notes": events_dict.get("coverage_notes", []),
        }
    )
    span_registry = SpanRegistryArtifact.model_validate({"spans": spans})

    ensure_output_directories(paths)
    paths.actors_raw_path.write_text(
        canonical_actors.model_dump_json(indent=2),
        encoding="utf-8",
    )
    paths.events_raw_path.write_text(
        canonical_events.model_dump_json(indent=2),
        encoding="utf-8",
    )
    paths.spans_path.write_text(
        span_registry.model_dump_json(indent=2),
        encoding="utf-8",
    )
    paths.canonicalize_log_path.write_text(
        json.dumps(log, indent=2),
        encoding="utf-8",
    )
    return 0
