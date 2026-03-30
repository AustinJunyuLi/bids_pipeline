from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Any

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.db_schema import open_pipeline_db
from skill_pipeline.paths import build_skill_paths, ensure_output_directories
from skill_pipeline.seeds import load_seed_entry


EVENT_TYPE_PRIORITY = {
    "target_sale": 0,
    "target_sale_public": 0,
    "bidder_sale": 0,
    "bidder_interest": 0,
    "activist_sale": 0,
    "sale_press_release": 0,
    "bid_press_release": 0,
    "ib_retention": 0,
    "nda": 1,
    "proposal": 2,
    "drop": 3,
    "final_round_inf_ann": 4,
    "final_round_inf": 4,
    "final_round_ann": 4,
    "final_round": 4,
    "final_round_ext_ann": 4,
    "final_round_ext": 4,
    "executed": 5,
    "terminated": 5,
    "restarted": 5,
}

NOTE_BY_EVENT_TYPE = {
    "target_sale": "Target Sale",
    "target_sale_public": "Target Sale Public",
    "bidder_sale": "Bidder Sale",
    "bidder_interest": "Bidder Interest",
    "activist_sale": "Activist Sale",
    "sale_press_release": "Sale Press Release",
    "bid_press_release": "Bid Press Release",
    "ib_retention": "IB",
    "nda": "NDA",
    "proposal": "NA",
    "final_round_inf_ann": "Final Round Inf Ann",
    "final_round_inf": "Final Round Inf",
    "final_round_ann": "Final Round Ann",
    "final_round": "Final Round",
    "final_round_ext_ann": "Final Round Ext Ann",
    "final_round_ext": "Final Round Ext",
    "executed": "Executed",
    "terminated": "Terminated",
    "restarted": "Restarted",
}

BIDDERLESS_EVENT_TYPES = {
    "target_sale",
    "target_sale_public",
    "sale_press_release",
    "final_round_inf_ann",
    "final_round_inf",
    "final_round_ann",
    "final_round",
    "final_round_ext_ann",
    "final_round_ext",
    "terminated",
}


def run_db_export(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    paths = build_skill_paths(deal_slug, project_root=project_root)
    db_path = paths.database_path
    if not db_path.exists():
        raise FileNotFoundError(f"Pipeline database not found: {db_path}")

    con = open_pipeline_db(db_path, read_only=True)
    try:
        event_count = con.execute(
            "SELECT COUNT(*) FROM events WHERE deal_slug = ?",
            [deal_slug],
        ).fetchone()[0]
        if event_count == 0:
            raise ValueError(f"No events found for deal '{deal_slug}' in database")

        actors = _query_actors(con, deal_slug)
        events = _query_events(con, deal_slug)
        enrichment = _query_enrichment(con, deal_slug)
        cycles = _query_cycles(con, deal_slug)
        rounds = _query_rounds(con, deal_slug)
        seed = load_seed_entry(deal_slug, seeds_path=paths.seeds_path)
        event_rows = _build_event_rows(actors, events, enrichment, cycles, rounds)
    finally:
        con.close()

    ensure_output_directories(paths)
    with paths.deal_events_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["TargetName", "Events", "Acquirer", "DateAnnounced", "URL"])
        writer.writerow(
            [
                seed.target_name,
                str(len(event_rows)),
                seed.acquirer or "NA",
                _format_seed_date(seed.date_announced),
                seed.primary_url or "NA",
            ]
        )
        writer.writerows(event_rows)
    return 0


def _query_actors(con, deal_slug: str) -> list[dict[str, Any]]:
    return _fetch_dicts(
        con,
        """
        SELECT
            actor_id,
            display_name,
            role,
            bidder_kind,
            listing_status,
            geography,
            is_grouped,
            group_size,
            group_label
        FROM actors
        WHERE deal_slug = ?
        """,
        [deal_slug],
    )


def _query_events(con, deal_slug: str) -> list[dict[str, Any]]:
    return _fetch_dicts(
        con,
        """
        SELECT
            event_id,
            event_type,
            date_raw_text,
            date_sort,
            date_precision,
            actor_ids,
            summary,
            terms_per_share,
            terms_range_low,
            terms_range_high,
            terms_consideration_type,
            drop_reason_text,
            executed_with_actor_id
        FROM events
        WHERE deal_slug = ?
        """,
        [deal_slug],
    )


def _query_enrichment(con, deal_slug: str) -> dict[str, dict[str, Any]]:
    columns = {row[1] for row in con.execute("PRAGMA table_info('enrichment')").fetchall()}
    selected_columns = [
        "event_id",
        "dropout_label",
        "dropout_basis",
        "bid_label",
        "bid_rule_applied",
        "bid_basis",
    ]
    for optional_column in ("all_cash_override", "c1", "c2", "c3", "review_flags"):
        if optional_column in columns:
            selected_columns.append(optional_column)
    rows = _fetch_dicts(
        con,
        f"SELECT {', '.join(selected_columns)} FROM enrichment WHERE deal_slug = ?",
        [deal_slug],
    )
    return {row["event_id"]: row for row in rows}


def _query_cycles(con, deal_slug: str) -> list[dict[str, Any]]:
    return _fetch_dicts(
        con,
        """
        SELECT cycle_id, start_event_id, end_event_id, boundary_basis
        FROM cycles
        WHERE deal_slug = ?
        ORDER BY cycle_id
        """,
        [deal_slug],
    )


def _query_rounds(con, deal_slug: str) -> list[dict[str, Any]]:
    return _fetch_dicts(
        con,
        """
        SELECT
            announcement_event_id,
            deadline_event_id,
            round_scope,
            invited_actor_ids,
            active_bidders_at_time,
            is_selective
        FROM rounds
        WHERE deal_slug = ?
        ORDER BY announcement_event_id
        """,
        [deal_slug],
    )


def _fetch_dicts(con, query: str, params: list[Any]) -> list[dict[str, Any]]:
    result = con.execute(query, params)
    columns = [description[0] for description in result.description]
    return [dict(zip(columns, row)) for row in result.fetchall()]


def _build_event_rows(
    actors: list[dict[str, Any]],
    events: list[dict[str, Any]],
    enrichment: dict[str, dict[str, Any]],
    cycles: list[dict[str, Any]],
    rounds: list[dict[str, Any]],
) -> list[list[str]]:
    del cycles
    del rounds
    actors_by_id = {actor["actor_id"]: actor for actor in actors}
    sorted_events = _sort_events(events)
    bidder_ids = _assign_bidder_ids(sorted_events)
    seen_actor_types: set[tuple[str, ...]] = set()
    rows = []
    for event in sorted_events:
        rows.append(
            _format_event_row(
                event,
                actors_by_id,
                enrichment.get(event["event_id"]),
                bidder_ids[event["event_id"]],
                seen_actor_types,
            )
        )
    return rows


def _sort_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        events,
        key=lambda event: (
            event["date_sort"] is None,
            event["date_sort"] or date.max,
            EVENT_TYPE_PRIORITY.get(event["event_type"], 99),
            event["event_id"],
        ),
    )


def _assign_bidder_ids(events: list[dict[str, Any]]) -> dict[str, str]:
    bidder_ids: dict[str, str] = {}
    first_nda_index = next(
        (index for index, event in enumerate(events) if event["event_type"] == "nda"),
        None,
    )
    if first_nda_index is None:
        for index, event in enumerate(events, start=1):
            bidder_ids[event["event_id"]] = _format_bidder_id(float(index))
        return bidder_ids

    pre_nda_events = events[:first_nda_index]
    pre_count = len(pre_nda_events)
    for index, event in enumerate(pre_nda_events, start=1):
        bidder_ids[event["event_id"]] = _format_bidder_id(round(index / (pre_count + 1), 1))
    for index, event in enumerate(events[first_nda_index:], start=1):
        bidder_ids[event["event_id"]] = _format_bidder_id(float(index))
    return bidder_ids


def _format_bidder_id(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.1f}"


def _format_event_row(
    event: dict[str, Any],
    actors_by_id: dict[str, dict[str, Any]],
    enrichment_row: dict[str, Any] | None,
    bidder_id: str,
    seen_actor_types: set[tuple[str, ...]],
) -> list[str]:
    actor_ids = _event_actor_ids(event)
    actor_key = tuple(sorted(actor_ids))
    bidder_name = _event_bidder_name(event, actors_by_id, actor_ids)
    type_value = "NA"
    if actor_key and bidder_name != "NA" and actor_key not in seen_actor_types:
        type_value = _bidder_type(actor_ids, actors_by_id)
        seen_actor_types.add(actor_key)
    bid_type = _bid_type(enrichment_row)
    value = _format_number(event.get("terms_per_share"))
    range_value = _range_value(event)
    date_r, date_p = _format_dates(event)
    all_cash_override = enrichment_row.get("all_cash_override") if enrichment_row else None
    if all_cash_override is True:
        cash_value = "1"
    elif event.get("terms_consideration_type") == "cash":
        cash_value = "1"
    else:
        cash_value = "NA"
    review_flags = _optional_enrichment_value(enrichment_row, "review_flags")
    return [
        bidder_id,
        _note_value(event, enrichment_row),
        bidder_name,
        type_value,
        bid_type,
        value,
        range_value,
        date_r,
        date_p,
        cash_value,
        _optional_enrichment_value(enrichment_row, "c1"),
        _optional_enrichment_value(enrichment_row, "c2"),
        _optional_enrichment_value(enrichment_row, "c3"),
        review_flags,
    ]


def _note_value(event: dict[str, Any], enrichment_row: dict[str, Any] | None) -> str:
    if event["event_type"] == "drop":
        if enrichment_row and enrichment_row.get("dropout_label"):
            return str(enrichment_row["dropout_label"])
        return "Drop"
    return NOTE_BY_EVENT_TYPE.get(event["event_type"], "NA")


def _event_actor_ids(event: dict[str, Any]) -> list[str]:
    actor_ids = list(event.get("actor_ids") or [])
    executed_with_actor_id = event.get("executed_with_actor_id")
    if executed_with_actor_id and executed_with_actor_id not in actor_ids:
        actor_ids.append(executed_with_actor_id)
    return actor_ids


def _event_bidder_name(
    event: dict[str, Any],
    actors_by_id: dict[str, dict[str, Any]],
    actor_ids: list[str],
) -> str:
    if event["event_type"] in BIDDERLESS_EVENT_TYPES:
        return "NA"
    names = [
        actor["display_name"]
        for actor_id in actor_ids
        if (actor := actors_by_id.get(actor_id)) is not None
    ]
    if not names:
        return "NA"
    return "/".join(names)


def _bidder_type(actor_ids: list[str], actors_by_id: dict[str, dict[str, Any]]) -> str:
    if not actor_ids:
        return "NA"
    if len(actor_ids) > 1:
        types = [_single_actor_type(actors_by_id.get(actor_id)) for actor_id in actor_ids]
        visible_types = [type_value for type_value in types if type_value != "NA"]
        return "/".join(visible_types) if visible_types else "NA"
    actor = actors_by_id.get(actor_ids[0])
    return _single_actor_type(actor)


def _single_actor_type(actor: dict[str, Any] | None) -> str:
    if actor is None or actor.get("role") != "bidder":
        return "NA"
    geography = actor.get("geography")
    listing_status = actor.get("listing_status")
    bidder_kind = actor.get("bidder_kind")
    if geography == "non_us" and listing_status == "public" and bidder_kind == "strategic":
        return "non-US public S"
    if geography == "non_us" and listing_status == "public" and bidder_kind == "financial":
        return "non-US public F"
    if geography == "non_us" and bidder_kind == "strategic":
        return "non-US S"
    if geography == "non_us" and bidder_kind == "financial":
        return "non-US F"
    if listing_status == "public" and bidder_kind == "strategic":
        return "public S"
    if listing_status == "public" and bidder_kind == "financial":
        return "public F"
    if bidder_kind == "strategic":
        return "S"
    if bidder_kind == "financial":
        return "F"
    if actor.get("is_grouped") and actor.get("group_size") and actor.get("group_label"):
        return f"{actor['group_size']}{actor['group_label']}"
    return "NA"


def _bid_type(enrichment_row: dict[str, Any] | None) -> str:
    if not enrichment_row:
        return "NA"
    label = enrichment_row.get("bid_label")
    if label in {"Formal", "Informal"}:
        return str(label)
    return "NA"


def _range_value(event: dict[str, Any]) -> str:
    range_low = event.get("terms_range_low")
    range_high = event.get("terms_range_high")
    per_share = event.get("terms_per_share")
    if range_low is not None and range_high is not None:
        return f"{_format_number(range_low)}-{_format_number(range_high)}"
    if per_share is not None:
        value = _format_number(per_share)
        return f"{value}-{value}"
    return "NA"


def _format_number(value: Any) -> str:
    if value is None:
        return "NA"
    numeric_value = float(value)
    if numeric_value.is_integer():
        return str(int(numeric_value))
    return f"{numeric_value:.2f}".rstrip("0").rstrip(".")


def _format_dates(event: dict[str, Any]) -> tuple[str, str]:
    if event.get("date_sort") is None or event.get("date_precision") == "unknown":
        return "NA", "NA"
    formatted = f"{event['date_sort'].isoformat()} 00:00:00"
    if event.get("date_precision") == "exact_day":
        return formatted, formatted
    return formatted, "NA"


def _optional_enrichment_value(enrichment_row: dict[str, Any] | None, key: str) -> str:
    if not enrichment_row:
        return "NA"
    value = enrichment_row.get(key)
    if value in (None, "", []):
        return "NA"
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    return str(value)


def _format_seed_date(value: str | None) -> str:
    if value is None:
        return "NA"
    try:
        return f"{date.fromisoformat(value).isoformat()} 00:00:00"
    except ValueError:
        return value
