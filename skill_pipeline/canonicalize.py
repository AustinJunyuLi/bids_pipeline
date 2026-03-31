"""Deterministic canonicalization: schema upgrade, dedup, NDA-gate, count-gap audit."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.extract_artifacts import load_extract_artifacts
from skill_pipeline.extract_artifacts_v2 import (
    RawObservationArtifactV2,
    load_observation_artifacts,
)
from skill_pipeline.models import (
    QuoteEntry,
    RawSkillActorsArtifact,
    RawSkillEventsArtifact,
    ResolvedDate,
    SkillActorsArtifact,
    SkillEventsArtifact,
    SpanRegistryArtifact,
)
from skill_pipeline.models_v2 import ObservationArtifactV2
from skill_pipeline.normalize.dates import parse_resolved_date
from skill_pipeline.paths import build_skill_paths, ensure_output_directories
from skill_pipeline.pipeline_models.source import ChronologyBlock
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


def _resolve_quotes_to_spans(
    quotes: list[QuoteEntry],
    *,
    blocks_by_id: dict[str, ChronologyBlock],
    document_lines: dict[str, list[str]],
    document_meta: dict[str, dict],
) -> tuple[list[dict], dict[str, str]]:
    """Resolve quotes to spans and return the span payload plus quote-to-span index."""
    spans: list[dict] = []
    quote_to_span: dict[str, str] = {}
    span_id_by_key: dict[tuple[str, str], str] = {}
    seen_ids: set[str] = set()

    for quote in quotes:
        if quote.quote_id in seen_ids:
            raise ValueError(f"Duplicate quote_id {quote.quote_id!r} in quotes array")
        seen_ids.add(quote.quote_id)

    for quote in quotes:
        existing_span_id = span_id_by_key.get((quote.block_id, quote.text))
        if existing_span_id is not None:
            quote_to_span[quote.quote_id] = existing_span_id
            continue

        block = blocks_by_id.get(quote.block_id)
        if block is None:
            raise ValueError(
                f"Quote {quote.quote_id!r} references unknown block_id {quote.block_id!r}"
            )

        meta = document_meta.get(block.document_id, {})
        raw_lines = document_lines.get(block.document_id)
        if raw_lines is None:
            raise FileNotFoundError(
                f"Missing filing text for document_id {block.document_id!r}"
            )

        span_id = f"span_{len(spans) + 1:04d}"
        span = resolve_text_span(
            raw_lines,
            start_line=block.start_line,
            end_line=block.end_line,
            block_ids=[block.block_id],
            evidence_ids=[],
            anchor_text=quote.text,
            document_id=block.document_id,
            accession_number=meta.get("accession_number"),
            filing_type=meta.get("filing_type", "UNKNOWN"),
            span_id=span_id,
        )
        spans.append(span.model_dump(mode="json"))
        quote_to_span[quote.quote_id] = span_id
        span_id_by_key[(quote.block_id, quote.text)] = span_id

    return spans, quote_to_span


def _validate_unique_quote_ids(quotes: list[QuoteEntry]) -> None:
    seen_ids: set[str] = set()
    for quote in quotes:
        if quote.quote_id in seen_ids:
            raise ValueError(f"Duplicate quote_id {quote.quote_id!r} in quotes array")
        seen_ids.add(quote.quote_id)


def _build_quote_id_remap(
    quotes: list[QuoteEntry],
    *,
    prefix: str,
) -> dict[str, str]:
    return {
        quote.quote_id: f"{prefix}_{index:03d}"
        for index, quote in enumerate(quotes, start=1)
    }


def _rewrite_quote_ids(quote_ids: list[str], remap: dict[str, str]) -> list[str]:
    return [remap[quote_id] for quote_id in quote_ids if quote_id in remap]


def _remap_quote_entries(
    quotes: list[QuoteEntry],
    remap: dict[str, str],
) -> list[dict]:
    return [
        {
            "quote_id": remap[quote.quote_id],
            "block_id": quote.block_id,
            "text": quote.text,
        }
        for quote in quotes
    ]


def _renumber_quote_first_artifacts(
    raw_actors: RawSkillActorsArtifact,
    raw_events: RawSkillEventsArtifact,
) -> tuple[RawSkillActorsArtifact, RawSkillEventsArtifact, dict[str, dict[str, str]]]:
    _validate_unique_quote_ids(list(raw_actors.quotes))
    _validate_unique_quote_ids(list(raw_events.quotes))

    actor_quote_remap = _build_quote_id_remap(list(raw_actors.quotes), prefix="qa")
    event_quote_remap = _build_quote_id_remap(list(raw_events.quotes), prefix="qe")

    actors_payload = raw_actors.model_dump(mode="json")
    actors_payload["quotes"] = _remap_quote_entries(list(raw_actors.quotes), actor_quote_remap)
    for actor in actors_payload["actors"]:
        actor["quote_ids"] = _rewrite_quote_ids(actor.get("quote_ids", []), actor_quote_remap)
    for assertion in actors_payload.get("count_assertions", []):
        assertion["quote_ids"] = _rewrite_quote_ids(
            assertion.get("quote_ids", []),
            actor_quote_remap,
        )

    events_payload = raw_events.model_dump(mode="json")
    events_payload["quotes"] = _remap_quote_entries(list(raw_events.quotes), event_quote_remap)
    for event in events_payload["events"]:
        event["quote_ids"] = _rewrite_quote_ids(event.get("quote_ids", []), event_quote_remap)

    quote_id_renumber_log = {
        "actor_quotes": actor_quote_remap,
        "event_quotes": event_quote_remap,
    }
    return (
        RawSkillActorsArtifact.model_validate(actors_payload),
        RawSkillEventsArtifact.model_validate(events_payload),
        quote_id_renumber_log,
    )


def _upgrade_raw_actors(
    actors_artifact: RawSkillActorsArtifact,
    *,
    quote_to_span: dict[str, str],
) -> dict:
    """Convert raw actors with quote_ids to canonical actors with evidence_span_ids."""
    actors_payload = actors_artifact.model_dump(mode="json")
    actors_payload.pop("quotes", None)
    for actor in actors_payload["actors"]:
        actor["evidence_span_ids"] = [
            quote_to_span[qid]
            for qid in actor.pop("quote_ids", [])
            if qid in quote_to_span
        ]

    for assertion in actors_payload.get("count_assertions", []):
        assertion["evidence_span_ids"] = [
            quote_to_span[qid]
            for qid in assertion.pop("quote_ids", [])
            if qid in quote_to_span
        ]

    return actors_payload


def _upgrade_raw_events(
    events_artifact: RawSkillEventsArtifact,
    *,
    quote_to_span: dict[str, str],
) -> dict:
    """Convert raw events with quote_ids to canonical events with evidence_span_ids."""
    events_payload = events_artifact.model_dump(mode="json")
    events_payload.pop("quotes", None)
    previous_resolved_date: ResolvedDate | None = None
    previous_event_id: str | None = None

    for event in events_payload["events"]:
        event["evidence_span_ids"] = [
            quote_to_span[qid]
            for qid in event.pop("quote_ids", [])
            if qid in quote_to_span
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
    kept: list[dict] = []
    gate_log: list[dict] = []
    bidder_states: dict[str, str] = {}
    for event in events:
        if event["event_type"] == "restarted":
            bidder_states.clear()
            kept.append(event)
            continue
        if event["event_type"] == "nda":
            for actor_id in event.get("actor_ids", []):
                bidder_states[actor_id] = "nda"
            kept.append(event)
            continue
        if event["event_type"] == "drop":
            drop_actors = set(event.get("actor_ids", []))
            invalid = {
                actor_id for actor_id in drop_actors if bidder_states.get(actor_id) != "nda"
            }
            if not drop_actors or invalid:
                missing = invalid if drop_actors else {"(empty)"}
                gate_log.append(
                    {
                        "removed_event_id": event["event_id"],
                        "reason": f"Drop actor(s) {missing} have no prior NDA in the current cycle.",
                    }
                )
                continue
            for actor_id in drop_actors:
                bidder_states[actor_id] = "drop"
        kept.append(event)
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

    nda_actor_ids: set[str] = set()
    for event in events:
        if event["event_type"] == "nda" and event.get("evidence_span_ids"):
            nda_actors = event.get("actor_ids", [])
            nda_actor_ids.update(nda_actors)

    for kind, subject in _KIND_SUBJECTS.items():
        assertions = [
            assertion for assertion in actors_dict.get("count_assertions", []) if assertion["subject"] == subject
        ]
        if not assertions:
            continue
        # Use the strongest filing-backed count when the same subject is asserted multiple times.
        asserted_count = max(assertion["count"] for assertion in assertions)
        actual_count = sum(
            1
            for actor in actors_dict["actors"]
            if actor.get("bidder_kind") == kind
            and actor["role"] == "bidder"
            and actor.get("evidence_span_ids")
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
        recovery_log.append(
            {
                "kind": kind,
                "subject": subject,
                "asserted_count": asserted_count,
                "grounded_count": actual_count,
                "gap": gap,
                "status": "blocked_unresolved_gap",
                "candidate_mentions": matching_mentions,
            }
        )

    return actors_dict, [], recovery_log


def _upgrade_raw_observation_artifact_v2(
    raw_artifact: RawObservationArtifactV2,
    *,
    quote_to_span: dict[str, str],
) -> dict:
    payload = raw_artifact.model_dump(mode="json")
    payload.pop("quotes", None)

    for party in payload["parties"]:
        party["evidence_span_ids"] = [
            quote_to_span[qid]
            for qid in party.pop("quote_ids", [])
            if qid in quote_to_span
        ]

    for cohort in payload["cohorts"]:
        cohort["evidence_span_ids"] = [
            quote_to_span[qid]
            for qid in cohort.pop("quote_ids", [])
            if qid in quote_to_span
        ]

    for observation in payload["observations"]:
        observation["evidence_span_ids"] = [
            quote_to_span[qid]
            for qid in observation.pop("quote_ids", [])
            if qid in quote_to_span
        ]

    return payload


def run_canonicalize(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    """Upgrade quote-first extract artifacts to canonical provenance, then normalize events."""
    paths = build_skill_paths(deal_slug, project_root=project_root)

    if not paths.actors_raw_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.actors_raw_path}")
    if not paths.events_raw_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.events_raw_path}")
    if not paths.chronology_blocks_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.chronology_blocks_path}")
    if not paths.document_registry_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.document_registry_path}")

    loaded = load_extract_artifacts(paths)
    if loaded.mode == "quote_first":
        raw_actors, raw_events, quote_id_renumber_log = _renumber_quote_first_artifacts(
            loaded.raw_actors,
            loaded.raw_events,
        )
        blocks = _load_chronology_blocks(paths.chronology_blocks_path)
        document_lines = _load_document_lines(paths.raw_root / deal_slug / "filings")
        document_meta = _load_document_registry(paths.document_registry_path)
        blocks_by_id = {block.block_id: block for block in blocks}
        all_quotes = list(raw_actors.quotes) + list(raw_events.quotes)
        spans, quote_to_span = _resolve_quotes_to_spans(
            all_quotes,
            blocks_by_id=blocks_by_id,
            document_lines=document_lines,
            document_meta=document_meta,
        )

        referenced_ids: set[str] = set()
        for actor in raw_actors.actors:
            referenced_ids.update(actor.quote_ids)
        for assertion in raw_actors.count_assertions:
            referenced_ids.update(assertion.quote_ids)
        for event in raw_events.events:
            referenced_ids.update(event.quote_ids)
        orphaned = [quote.quote_id for quote in all_quotes if quote.quote_id not in referenced_ids]

        actors_dict = _upgrade_raw_actors(
            raw_actors,
            quote_to_span=quote_to_span,
        )
        events_dict = _upgrade_raw_events(
            raw_events,
            quote_to_span=quote_to_span,
        )
    else:
        actors_dict = loaded.actors.model_dump(mode="json")
        events_dict = loaded.events.model_dump(mode="json")
        spans = loaded.spans.model_dump(mode="json")["spans"]
        orphaned = []
        quote_id_renumber_log = {
            "actor_quotes": {},
            "event_quotes": {},
        }

    events = events_dict["events"]
    log: dict = {
        "dedup_log": {},
        "nda_gate_log": [],
        "recovery_log": [],
        "orphaned_quotes": orphaned,
        "quote_id_renumber_log": quote_id_renumber_log,
    }

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

    ensure_output_directories(paths, include_legacy=True)
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


def run_canonicalize_v2(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    """Upgrade quote-first v2 observation artifacts to canonical span-backed form."""
    paths = build_skill_paths(deal_slug, project_root=project_root)

    prefer_raw = paths.observations_raw_path.exists()
    loaded = load_observation_artifacts(
        paths,
        mode="quote_first" if prefer_raw else "canonical",
    )

    if loaded.mode == "quote_first":
        if not paths.chronology_blocks_path.exists():
            raise FileNotFoundError(f"Missing required input: {paths.chronology_blocks_path}")
        if not paths.document_registry_path.exists():
            raise FileNotFoundError(f"Missing required input: {paths.document_registry_path}")

        blocks = _load_chronology_blocks(paths.chronology_blocks_path)
        document_lines = _load_document_lines(paths.raw_root / deal_slug / "filings")
        document_meta = _load_document_registry(paths.document_registry_path)
        blocks_by_id = {block.block_id: block for block in blocks}
        spans, quote_to_span = _resolve_quotes_to_spans(
            list(loaded.raw_artifact.quotes),
            blocks_by_id=blocks_by_id,
            document_lines=document_lines,
            document_meta=document_meta,
        )
        observations_dict = _upgrade_raw_observation_artifact_v2(
            loaded.raw_artifact,
            quote_to_span=quote_to_span,
        )
    else:
        observations_dict = loaded.observations.model_dump(mode="json")
        spans = loaded.spans.model_dump(mode="json")["spans"]

    canonical_observations = ObservationArtifactV2.model_validate(observations_dict)
    span_registry = SpanRegistryArtifact.model_validate({"spans": spans})

    ensure_output_directories(paths)
    paths.observations_path.write_text(
        canonical_observations.model_dump_json(indent=2),
        encoding="utf-8",
    )
    paths.spans_v2_path.write_text(
        span_registry.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return 0
