from __future__ import annotations

import csv
import json
import logging
import os
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from pipeline.schemas import (
    Actor,
    AuditFlags,
    Deal,
    Event,
    EventActorLink,
    FormalBoundary,
    Initiation,
    Judgment,
    MASTER_ROW_FIELDNAMES,
    OVERRIDES_CSV_HEADER,
    ProcessCycle,
    ReviewStatus,
)


logger = logging.getLogger(__name__)


_SOURCE_TEXT_MAX = 120
_JUDGMENT_ADAPTER = TypeAdapter(Judgment)

_EVENT_TYPE_TO_BID_NOTE: dict[str, str] = {
    "proposal": "",
    "nda": "NDA",
    "drop": "Drop",
    "drop_below_m": "DropBelowM",
    "drop_below_inf": "DropBelowInf",
    "drop_at_inf": "DropAtInf",
    "drop_target": "DropTarget",
    "ib_retention": "IB",
    "executed": "Executed",
    "terminated": "Terminated",
    "restarted": "Restarted",
    "final_round_inf_ann": "Final Round Inf Ann",
    "final_round_inf": "Final Round Inf",
    "final_round_ann": "Final Round Ann",
    "final_round": "Final Round",
    "final_round_ext_ann": "Final Round Ext Ann",
    "final_round_ext": "Final Round Ext",
    "activist_sale": "Activist Sale",
    "bidder_sale": "Bidder Sale",
    "bidder_interest": "Bidder Interest",
    "target_sale": "Target Sale",
    "target_sale_public": "Target Sale Public",
    "sale_press_release": "Sale Press Release",
    "bid_press_release": "Bid Press Release",
}

_EVENT_TYPE_SORT_PRIORITY: dict[str, int] = {
    "target_sale": 0,
    "target_sale_public": 1,
    "bidder_sale": 2,
    "bidder_interest": 3,
    "activist_sale": 4,
    "sale_press_release": 5,
    "bid_press_release": 6,
    "ib_retention": 10,
    "final_round_inf_ann": 20,
    "final_round_inf": 21,
    "final_round_ann": 22,
    "final_round": 23,
    "final_round_ext_ann": 24,
    "final_round_ext": 25,
    "nda": 30,
    "proposal": 40,
    "drop_target": 50,
    "drop": 51,
    "drop_below_m": 52,
    "drop_below_inf": 53,
    "drop_at_inf": 54,
    "executed": 60,
    "terminated": 61,
    "restarted": 62,
}

_DROP_EVENT_TYPES: set[str] = {
    "drop",
    "drop_below_m",
    "drop_below_inf",
    "drop_at_inf",
    "drop_target",
}


def _read_json(path: Path) -> Any:
    """Read and deserialize a JSON file."""

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_json_model(path: Path, model_type: type[Any]) -> Any:
    """Read a JSON file and validate it against a Pydantic model."""

    return model_type.model_validate(_read_json(path))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL file into a list of dictionaries."""

    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line: str = raw_line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _read_jsonl_models(path: Path, model_type: type[Any] | TypeAdapter) -> list[Any]:
    """Read JSONL rows and validate them as Pydantic models."""

    models: list[Any] = []
    for payload in _read_jsonl(path):
        if isinstance(model_type, TypeAdapter):
            models.append(model_type.validate_python(payload))
        else:
            models.append(model_type.model_validate(payload))
    return models


def _truncate(text: str | None, max_len: int = _SOURCE_TEXT_MAX) -> str:
    """Truncate text for reviewer-facing CSV columns."""

    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


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


def _event_type_to_bid_note(event_type: str) -> str:
    """Map an event type to the reviewer-facing bid note label."""

    return _EVENT_TYPE_TO_BID_NOTE.get(event_type, event_type)


def _load_linkage(reference_dir: Path) -> dict[str, dict[str, Any]]:
    """Load auxiliary linkage data, such as cshoc, from reference files when present."""

    linkage: dict[str, dict[str, Any]] = {}
    if not reference_dir.exists():
        return linkage

    for csv_path in sorted(reference_dir.rglob("*.csv")):
        try:
            with csv_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                if reader.fieldnames is None:
                    continue
                fieldnames_lower: set[str] = {field.lower() for field in reader.fieldnames}
                if "deal_slug" not in fieldnames_lower and "slug" not in fieldnames_lower:
                    continue
                for row in reader:
                    normalized: dict[str, Any] = {key.lower(): value for key, value in row.items() if key is not None}
                    slug: str = str(normalized.get("deal_slug") or normalized.get("slug") or "").strip()
                    if not slug:
                        continue
                    existing: dict[str, Any] = linkage.setdefault(slug, {})
                    for key, value in normalized.items():
                        if key in {"deal_slug", "slug"}:
                            continue
                        if value not in (None, ""):
                            existing[key] = value
        except Exception as exc:  # pragma: no cover - defensive path
            logger.warning("failed to load linkage csv=%s error=%s", csv_path, exc)

    for json_path in sorted(reference_dir.rglob("*.json")):
        try:
            payload: Any = _read_json(json_path)
        except Exception as exc:  # pragma: no cover - defensive path
            logger.warning("failed to load linkage json=%s error=%s", json_path, exc)
            continue
        if isinstance(payload, list):
            for item in payload:
                if not isinstance(item, dict):
                    continue
                slug_value: str = str(item.get("deal_slug") or item.get("slug") or "").strip()
                if not slug_value:
                    continue
                existing = linkage.setdefault(slug_value, {})
                for key, value in item.items():
                    if key in {"deal_slug", "slug"}:
                        continue
                    if value not in (None, ""):
                        existing[key.lower()] = value
        elif isinstance(payload, dict):
            for slug_value, values in payload.items():
                if not isinstance(values, dict):
                    continue
                existing = linkage.setdefault(str(slug_value), {})
                for key, value in values.items():
                    if value not in (None, ""):
                        existing[key.lower()] = value
    return linkage


def _sort_events(events: list[Event]) -> list[Event]:
    """Return a stable chronology ordering for events."""

    return sorted(
        events,
        key=lambda event: (event.date, _EVENT_TYPE_SORT_PRIORITY.get(event.event_type, 999), event.source_line_start, event.event_id),
    )


def _event_index_map(events: list[Event]) -> dict[str, int]:
    """Return an index map for sorted events."""

    return {event.event_id: index for index, event in enumerate(events)}


def _map_event_to_cycle(events: list[Event], cycles: list[ProcessCycle]) -> dict[str, str]:
    """Map each event identifier to its containing cycle identifier."""

    if not cycles:
        return {}
    ordered_events: list[Event] = _sort_events(events)
    index_map: dict[str, int] = _event_index_map(ordered_events)
    mapping: dict[str, str] = {}
    for cycle in cycles:
        if cycle.start_event_id not in index_map or cycle.end_event_id not in index_map:
            continue
        start_index: int = index_map[cycle.start_event_id]
        end_index: int = index_map[cycle.end_event_id]
        for event in ordered_events[start_index : end_index + 1]:
            mapping[event.event_id] = cycle.cycle_id
    return mapping


def _map_event_to_round(events: list[Event], cycles: list[ProcessCycle]) -> dict[str, str]:
    """Map round-boundary and within-round events to round identifiers."""

    ordered_events: list[Event] = _sort_events(events)
    index_map: dict[str, int] = _event_index_map(ordered_events)
    mapping: dict[str, str] = {}
    for cycle in cycles:
        for round_row in cycle.rounds:
            if round_row.announcement_event_id not in index_map or round_row.deadline_event_id not in index_map:
                continue
            start_index: int = index_map[round_row.announcement_event_id]
            end_index: int = index_map[round_row.deadline_event_id]
            if end_index < start_index:
                continue
            for event in ordered_events[start_index : end_index + 1]:
                mapping[event.event_id] = round_row.round_id
    return mapping


def _nda_actor_ids(events: list[Event], links: list[EventActorLink]) -> set[str]:
    """Return the set of actor IDs participating in NDA events."""

    nda_event_ids: set[str] = {event.event_id for event in events if event.event_type == "nda"}
    return {link.actor_id for link in links if link.event_id in nda_event_ids and link.actor_id}


def _build_reviewer_note(
    date_precision: str,
    flag_missing_nda: bool,
    flag_unresolved_lifecycle: bool,
    flag_anonymous_mapping: bool,
) -> str:
    """Generate the reviewer note text for a row from row-level flags."""

    parts: list[str] = []
    if date_precision in {"approximate", "month_only"}:
        parts.append(f"Date is {date_precision}")
    if flag_missing_nda:
        parts.append("Bidder has no NDA event")
    if flag_unresolved_lifecycle:
        parts.append("Actor lifecycle unresolved")
    if flag_anonymous_mapping:
        parts.append("Anonymous actor, cannot map to named entity")
    return ". ".join(parts) + ("." if parts else "")


def build_deal_rows(deal_dir: Path, linkage: dict[str, dict]) -> list[dict[str, str]]:
    """Build the 47-column reviewer rows for a single deal directory."""

    deal_path: Path = deal_dir / "extraction" / "deal.json"
    if not deal_path.exists():
        return []

    deal: Deal = _read_json_model(deal_path, Deal)
    actors: list[Actor] = _read_jsonl_models(deal_dir / "extraction" / "actors.jsonl", Actor)
    events: list[Event] = _read_jsonl_models(deal_dir / "extraction" / "events.jsonl", Event)
    links: list[EventActorLink] = _read_jsonl_models(deal_dir / "extraction" / "event_actor_links.jsonl", EventActorLink)
    judgments: list[Judgment] = _read_jsonl_models(deal_dir / "enrichment" / "judgments.jsonl", _JUDGMENT_ADAPTER)
    cycles: list[ProcessCycle] = _read_jsonl_models(deal_dir / "enrichment" / "process_cycles.jsonl", ProcessCycle)
    audit_flags_path: Path = deal_dir / "extraction" / "audit_flags.json"
    audit_flags: AuditFlags | None = _read_json_model(audit_flags_path, AuditFlags) if audit_flags_path.exists() else None

    actors_by_id: dict[str, Actor] = {actor.actor_id: actor for actor in actors}
    events_by_id: dict[str, Event] = {event.event_id: event for event in events}
    links_by_event: dict[str, list[EventActorLink]] = {}
    for link in links:
        links_by_event.setdefault(link.event_id, []).append(link)

    bid_classifications: dict[str, Any] = {}
    initiation_judgment: Initiation | None = None
    formal_boundary_judgment: FormalBoundary | None = None
    for judgment in judgments:
        if isinstance(judgment, dict):
            continue
        if getattr(judgment, "judgment_type", "") == "bid_classification":
            bid_classifications[judgment.scope_id] = judgment
        elif getattr(judgment, "judgment_type", "") == "initiation":
            initiation_judgment = judgment
        elif getattr(judgment, "judgment_type", "") == "formal_boundary":
            formal_boundary_judgment = judgment

    ordered_events: list[Event] = _sort_events(events)
    event_to_cycle: dict[str, str] = _map_event_to_cycle(ordered_events, cycles)
    event_to_round: dict[str, str] = _map_event_to_round(ordered_events, cycles)
    nda_actor_ids: set[str] = _nda_actor_ids(events, links)
    unresolved_actor_ids: set[str] = set(audit_flags.unresolved_actors) if audit_flags is not None else set()

    slug: str = deal.deal_slug
    deal_linkage: dict[str, Any] = linkage.get(slug, {})
    cshoc_value: str = str(deal_linkage.get("cshoc", "")) if deal_linkage.get("cshoc") not in (None, "") else ""

    winning_acquirer_display: str = deal.winning_acquirer
    if deal.winning_acquirer in actors_by_id:
        winning_acquirer_display = actors_by_id[deal.winning_acquirer].actor_alias

    deal_header: dict[str, str] = {
        "deal_slug": slug,
        "target_name": deal.target_name,
        "cik": str(deal.cik),
        "winning_acquirer": winning_acquirer_display,
        "deal_outcome": deal.deal_outcome,
        "consideration_type": deal.consideration_type,
        "DateAnnounced": deal.date_announced,
        "DateEffective": deal.date_effective or "",
        "filing_type": deal.filing_type,
        "URL": deal.filing_url,
    }

    raw_rows: list[dict[str, str]] = []
    any_row_flag: bool = False

    for event in ordered_events:
        event_links: list[EventActorLink] = links_by_event.get(event.event_id, [])
        if not event_links:
            event_links = []
        link_rows: list[EventActorLink | None] = event_links if event_links else [None]
        for link in link_rows:
            actor: Actor | None = actors_by_id.get(link.actor_id) if link is not None else None
            actor_id: str = actor.actor_id if actor is not None else ""
            actor_alias: str = actor.actor_alias if actor is not None else ""
            actor_type: str = actor.actor_type if actor is not None else ""
            bidder_subtype: str = actor.bidder_subtype or "" if actor is not None else ""
            lifecycle_status: str = actor.lifecycle_status if actor is not None else ""
            participation_role: str = link.participation_role if link is not None else ""
            actor_notes: str = actor.actor_notes or "" if actor is not None else ""

            flag_approximate_date: bool = event.date_precision in {"approximate", "month_only"}
            flag_missing_nda: bool = bool(actor and actor.actor_type == "bidder" and actor.actor_id not in nda_actor_ids)
            flag_unresolved_lifecycle: bool = bool(
                actor and (actor.lifecycle_status == "unresolved" or actor.actor_id in unresolved_actor_ids)
            )
            actor_alias_lower: str = actor_alias.lower()
            flag_anonymous_mapping: bool = bool(
                actor
                and (
                    actor_alias_lower.startswith("unnamed")
                    or "/unnamed_" in actor.actor_id.lower()
                    or actor.actor_id.lower().startswith("unnamed_")
                )
            )
            reviewer_note: str = _build_reviewer_note(
                event.date_precision or "",
                flag_missing_nda,
                flag_unresolved_lifecycle,
                flag_anonymous_mapping,
            )
            row_has_flag: bool = any(
                [flag_approximate_date, flag_missing_nda, flag_unresolved_lifecycle, flag_anonymous_mapping]
            )
            any_row_flag = any_row_flag or row_has_flag

            classification = bid_classifications.get(event.event_id)
            bid_note: str
            if event.event_type == "proposal":
                bid_note = ""  # Spec: blank for proposal rows
            else:
                bid_note = _event_type_to_bid_note(event.event_type)

            row: dict[str, str] = {
                **deal_header,
                "row_seq": "",
                "event_id": event.event_id,
                "event_type": event.event_type,
                "bid_note": bid_note,
                "cycle_id": event_to_cycle.get(event.event_id, ""),
                "actor_id": actor_id,
                "BidderName": actor_alias,
                "actor_type": actor_type,
                "bidder_subtype": bidder_subtype,
                "lifecycle_status": lifecycle_status,
                "participation_role": participation_role,
                "actor_notes": actor_notes,
                "event_date": event.date,
                "date_precision": event.date_precision or "",
                "round_id": event_to_round.get(event.event_id, ""),
                "bid_value_pershare": "" if event.value is None else str(event.value),
                "bid_value_lower": "" if event.value_lower is None else str(event.value_lower),
                "bid_value_upper": "" if event.value_upper is None else str(event.value_upper),
                "all_cash": "1" if event.consideration_type == "cash" else "",
                "event_consideration_type": event.consideration_type or "",
                "cshoc": cshoc_value,
                "bid_type": classification.value.capitalize() if classification is not None else "",
                "bid_classification_rule": classification.classification_rule if classification is not None else "",
                "bid_classification_confidence": classification.confidence if classification is not None else "",
                "initiation": initiation_judgment.value if initiation_judgment is not None else "",
                "formal_boundary_event": (
                    formal_boundary_judgment.value or "" if formal_boundary_judgment is not None else ""
                ),
                "source_text_short": _truncate(event.source_text),
                "raw_note": event.raw_note or "",
                "deal_notes": deal.deal_notes or "",
                "reviewer_note": reviewer_note,
                "needs_review": "false",
                "flag_approximate_date": "true" if flag_approximate_date else "false",
                "flag_missing_nda": "true" if flag_missing_nda else "false",
                "flag_unresolved_lifecycle": "true" if flag_unresolved_lifecycle else "false",
                "flag_anonymous_mapping": "true" if flag_anonymous_mapping else "false",
                "comments_1": "",
                "comments_2": "",
            }
            raw_rows.append(row)

    raw_rows.sort(
        key=lambda row: (
            row["event_date"],
            _EVENT_TYPE_SORT_PRIORITY.get(row["event_type"], 999),
            row["BidderName"].lower(),
            row["actor_id"].lower(),
            row["event_id"].lower(),
        )
    )

    deal_needs_review: bool = any_row_flag or bool(audit_flags is not None and audit_flags.flags)
    for row_sequence, row in enumerate(raw_rows, start=1):
        row["row_seq"] = str(row_sequence)
        row["needs_review"] = "true" if deal_needs_review else "false"

    return raw_rows


def write_review_status(deal_dir: Path, flags: list[str]) -> None:
    """Write review_status.json while preserving reviewer metadata when present."""

    review_dir: Path = deal_dir / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    review_path: Path = review_dir / "review_status.json"

    existing_reviewer: str | None = None
    existing_review_date: str | None = None
    if review_path.exists():
        existing_payload: Any = _read_json(review_path)
        if isinstance(existing_payload, dict):
            existing_reviewer = existing_payload.get("reviewer")
            existing_review_date = existing_payload.get("review_date")

    normalized_flags: list[str] = sorted(dict.fromkeys(flags))
    status: str = "needs_review" if normalized_flags else "pending_review"
    review_status: ReviewStatus = ReviewStatus(
        status=status,
        flags=normalized_flags,
        last_extraction_date=date.today().isoformat(),
        reviewer=existing_reviewer,
        review_date=existing_review_date,
    )
    _atomic_write_text(review_path, json.dumps(review_status.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def write_overrides_header(deal_dir: Path) -> None:
    """Create review/overrides.csv with the canonical header, preserving existing data."""

    review_dir: Path = deal_dir / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    overrides_path: Path = review_dir / "overrides.csv"

    if overrides_path.exists():
        with overrides_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            try:
                existing_header: list[str] = next(reader)
            except StopIteration:
                existing_header = []
        if existing_header:
            if tuple(existing_header) != OVERRIDES_CSV_HEADER:
                raise ValueError(f"Existing overrides header mismatch for {overrides_path}")
            return

    output_lines: list[str] = []
    output_lines.append(",".join(OVERRIDES_CSV_HEADER))
    _atomic_write_text(overrides_path, "\n".join(output_lines) + "\n")


def _row_flag_names(rows: list[dict[str, str]]) -> set[str]:
    """Return review-status flags implied by row-level reviewer flags."""

    flags: set[str] = set()
    if any(row.get("flag_approximate_date") == "true" for row in rows):
        flags.add("approximate_date")
    if any(row.get("flag_missing_nda") == "true" for row in rows):
        flags.add("missing_nda")
    if any(row.get("flag_unresolved_lifecycle") == "true" for row in rows):
        flags.add("unresolved_lifecycle")
    if any(row.get("flag_anonymous_mapping") == "true" for row in rows):
        flags.add("anonymous_mapping")
    return flags


def _write_rows_csv(path: Path, rows: list[dict[str, str]]) -> None:
    """Write a CSV file atomically using the canonical master-row field order."""

    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor: int
    tmp_path_str: str
    file_descriptor, tmp_path_str = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp_path: Path = Path(tmp_path_str)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(MASTER_ROW_FIELDNAMES))
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def rebuild_master_csv(deals_dir: Path, views_dir: Path, reference_dir: Path) -> Path:
    """Rebuild per-deal master_rows.csv files and the merged global master.csv."""

    linkage: dict[str, dict] = _load_linkage(reference_dir)
    all_rows: list[dict[str, str]] = []
    discovered_deal_dirs: list[Path] = [
        deal_dir for deal_dir in sorted(deals_dir.iterdir()) if deal_dir.is_dir() and (deal_dir / "extraction" / "deal.json").exists()
    ] if deals_dir.exists() else []

    for deal_dir in discovered_deal_dirs:
        rows: list[dict[str, str]] = build_deal_rows(deal_dir, linkage)
        audit_flags_path: Path = deal_dir / "extraction" / "audit_flags.json"
        audit_flags: AuditFlags | None = _read_json_model(audit_flags_path, AuditFlags) if audit_flags_path.exists() else None
        combined_flags: set[str] = set(audit_flags.flags if audit_flags is not None else [])
        combined_flags.update(_row_flag_names(rows))
        write_review_status(deal_dir, sorted(combined_flags))
        write_overrides_header(deal_dir)
        _write_rows_csv(deal_dir / "master_rows.csv", rows)
        all_rows.extend(rows)

    all_rows.sort(key=lambda row: (row["deal_slug"].lower(), int(row["row_seq"]) if row["row_seq"].isdigit() else 0))
    views_dir.mkdir(parents=True, exist_ok=True)
    master_csv_path: Path = views_dir / "master.csv"
    _write_rows_csv(master_csv_path, all_rows)
    logger.info("rebuild_master_csv wrote deals=%s rows=%s path=%s", len(discovered_deal_dirs), len(all_rows), master_csv_path)
    return master_csv_path
