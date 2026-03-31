from __future__ import annotations

import csv
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.db_export import EVENT_TYPE_PRIORITY
from skill_pipeline.db_schema import open_pipeline_db
from skill_pipeline.models_v2 import AnalystRowRecord
from skill_pipeline.paths import build_skill_paths, ensure_output_directories


LITERAL_FIELDNAMES = [
    "observation_id",
    "obs_type",
    "date_raw_text",
    "date_sort",
    "date_precision",
    "subject_refs",
    "subject_names",
    "counterparty_refs",
    "counterparty_names",
    "summary",
    "evidence_span_ids",
    "type_fields",
]

ANALYST_FIELDNAMES = [
    "row_id",
    "origin",
    "analyst_event_type",
    "subject_ref",
    "subject_name",
    "row_count",
    "bidder_name",
    "bidder_type",
    "bid_type",
    "value",
    "range_low",
    "range_high",
    "date_recorded",
    "date_public",
    "all_cash",
    "rule_id",
    "source_observation_ids",
    "source_span_ids",
    "confidence",
    "review_flags",
    "explanation",
]

BENCHMARK_FIELDNAMES = ANALYST_FIELDNAMES + ["expansion_slot", "expanded_from_row_id"]


def run_db_export_v2(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    paths = build_skill_paths(deal_slug, project_root=project_root)
    if not paths.database_path.exists():
        raise FileNotFoundError(f"Pipeline database not found: {paths.database_path}")

    con = open_pipeline_db(paths.database_path, read_only=True)
    try:
        observation_count = con.execute(
            "SELECT COUNT(*) FROM v2_observations WHERE deal_slug = ?",
            [deal_slug],
        ).fetchone()[0]
        if observation_count == 0:
            raise ValueError(f"No v2 observations found for deal '{deal_slug}' in database")

        parties = _query_parties(con, deal_slug)
        cohorts = _query_cohorts(con, deal_slug)
        observations = _query_observations(con, deal_slug)
        analyst_rows = _query_analyst_rows(con, deal_slug)
    finally:
        con.close()

    literal_rows = _build_literal_rows(parties, cohorts, observations)
    analyst_export_rows = _build_analyst_export_rows(parties, cohorts, analyst_rows)
    benchmark_rows = _build_benchmark_rows(parties, cohorts, analyst_rows)

    ensure_output_directories(paths)
    _write_dict_rows(paths.literal_observations_path, LITERAL_FIELDNAMES, literal_rows)
    _write_dict_rows(paths.analyst_rows_path, ANALYST_FIELDNAMES, analyst_export_rows)
    _write_dict_rows(paths.benchmark_rows_expanded_path, BENCHMARK_FIELDNAMES, benchmark_rows)
    return 0


def _query_parties(con, deal_slug: str) -> dict[str, dict[str, Any]]:
    rows = _fetch_dicts(
        con,
        """
        SELECT
            party_id,
            display_name,
            role,
            bidder_kind,
            listing_status,
            geography
        FROM v2_parties
        WHERE deal_slug = ?
        """,
        [deal_slug],
    )
    return {row["party_id"]: row for row in rows}


def _query_cohorts(con, deal_slug: str) -> dict[str, dict[str, Any]]:
    rows = _fetch_dicts(
        con,
        """
        SELECT
            cohort_id,
            label,
            exact_count
        FROM v2_cohorts
        WHERE deal_slug = ?
        """,
        [deal_slug],
    )
    return {row["cohort_id"]: row for row in rows}


def _query_observations(con, deal_slug: str) -> list[dict[str, Any]]:
    rows = _fetch_dicts(
        con,
        """
        SELECT
            observation_id,
            obs_type,
            date_raw_text,
            date_sort,
            date_precision,
            subject_refs,
            counterparty_refs,
            summary,
            evidence_span_ids,
            type_fields
        FROM v2_observations
        WHERE deal_slug = ?
        """,
        [deal_slug],
    )
    return sorted(
        rows,
        key=lambda row: (
            row["date_sort"] is None,
            row["date_sort"] or date.max,
            row["observation_id"],
        ),
    )


def _query_analyst_rows(con, deal_slug: str) -> list[AnalystRowRecord]:
    rows = _fetch_dicts(
        con,
        """
        SELECT record_id, record_fields
        FROM v2_derivations
        WHERE deal_slug = ? AND record_type = 'analyst_row'
        """,
        [deal_slug],
    )
    analyst_rows = [
        AnalystRowRecord.model_validate(_json_field(row["record_fields"]))
        for row in rows
    ]
    return sorted(
        analyst_rows,
        key=lambda row: (
            row.date_recorded is None and row.date_public is None,
            row.date_recorded or row.date_public or date.max,
            EVENT_TYPE_PRIORITY.get(row.analyst_event_type, 99),
            row.row_id,
        ),
    )


def _build_literal_rows(
    parties: dict[str, dict[str, Any]],
    cohorts: dict[str, dict[str, Any]],
    observations: list[dict[str, Any]],
) -> list[dict[str, str]]:
    return [
        {
            "observation_id": row["observation_id"],
            "obs_type": row["obs_type"],
            "date_raw_text": row["date_raw_text"] or "NA",
            "date_sort": _format_date(row["date_sort"]),
            "date_precision": row["date_precision"] or "NA",
            "subject_refs": _join_values(row["subject_refs"]),
            "subject_names": _join_values(
                _display_name(ref, parties, cohorts) for ref in row["subject_refs"] or []
            ),
            "counterparty_refs": _join_values(row["counterparty_refs"]),
            "counterparty_names": _join_values(
                _display_name(ref, parties, cohorts)
                for ref in row["counterparty_refs"] or []
            ),
            "summary": row["summary"],
            "evidence_span_ids": _join_values(row["evidence_span_ids"]),
            "type_fields": json.dumps(_json_field(row["type_fields"]), sort_keys=True),
        }
        for row in observations
    ]


def _build_analyst_export_rows(
    parties: dict[str, dict[str, Any]],
    cohorts: dict[str, dict[str, Any]],
    analyst_rows: list[AnalystRowRecord],
) -> list[dict[str, str]]:
    return [
        _analyst_row_to_export_dict(
            row,
            parties,
            cohorts,
        )
        for row in analyst_rows
    ]


def _build_benchmark_rows(
    parties: dict[str, dict[str, Any]],
    cohorts: dict[str, dict[str, Any]],
    analyst_rows: list[AnalystRowRecord],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for analyst_row in analyst_rows:
        if analyst_row.origin == "synthetic_anonymous" and analyst_row.row_count > 1:
            base_name = analyst_row.bidder_name or _display_name(analyst_row.subject_ref, parties, cohorts)
            for index in range(1, analyst_row.row_count + 1):
                slot = f"anon_slot_{index:03d}"
                expanded = analyst_row.model_copy(
                    update={
                        "row_id": f"{analyst_row.row_id}:{slot}",
                        "subject_ref": (
                            f"{analyst_row.subject_ref}:{slot}"
                            if analyst_row.subject_ref
                            else slot
                        ),
                        "row_count": 1,
                        "bidder_name": f"{base_name} {slot}" if base_name else slot,
                        "review_flags": list(analyst_row.review_flags)
                        + [f"expanded_from:{analyst_row.row_id}"],
                    }
                )
                row_dict = _analyst_row_to_export_dict(expanded, parties, cohorts)
                row_dict["expansion_slot"] = slot
                row_dict["expanded_from_row_id"] = analyst_row.row_id
                rows.append(row_dict)
            continue
        row_dict = _analyst_row_to_export_dict(analyst_row, parties, cohorts)
        row_dict["expansion_slot"] = "NA"
        row_dict["expanded_from_row_id"] = "NA"
        rows.append(row_dict)
    return rows


def _analyst_row_to_export_dict(
    row: AnalystRowRecord,
    parties: dict[str, dict[str, Any]],
    cohorts: dict[str, dict[str, Any]],
) -> dict[str, str]:
    return {
        "row_id": row.row_id,
        "origin": row.origin,
        "analyst_event_type": row.analyst_event_type,
        "subject_ref": row.subject_ref or "NA",
        "subject_name": _display_name(row.subject_ref, parties, cohorts),
        "row_count": str(row.row_count),
        "bidder_name": row.bidder_name or "NA",
        "bidder_type": row.bidder_type or "NA",
        "bid_type": row.bid_type or "NA",
        "value": _format_decimal(row.value),
        "range_low": _format_decimal(row.range_low),
        "range_high": _format_decimal(row.range_high),
        "date_recorded": _format_date(row.date_recorded),
        "date_public": _format_date(row.date_public),
        "all_cash": _format_bool(row.all_cash),
        "rule_id": row.basis.rule_id,
        "source_observation_ids": _join_values(row.basis.source_observation_ids),
        "source_span_ids": _join_values(row.basis.source_span_ids),
        "confidence": row.basis.confidence,
        "review_flags": _join_values(row.review_flags),
        "explanation": row.basis.explanation,
    }


def _display_name(
    ref: str | None,
    parties: dict[str, dict[str, Any]],
    cohorts: dict[str, dict[str, Any]],
) -> str:
    if ref is None:
        return "NA"
    party = parties.get(ref)
    if party is not None:
        return party["display_name"]
    cohort = cohorts.get(ref)
    if cohort is not None:
        return cohort["label"]
    if ":anon_slot_" in ref:
        return ref.split(":", maxsplit=1)[1]
    return ref


def _fetch_dicts(con, query: str, params: list[Any]) -> list[dict[str, Any]]:
    result = con.execute(query, params)
    columns = [description[0] for description in result.description]
    return [dict(zip(columns, row)) for row in result.fetchall()]


def _write_dict_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _format_date(value: date | None) -> str:
    if value is None:
        return "NA"
    return f"{value.isoformat()} 00:00:00"


def _format_decimal(value: Decimal | None) -> str:
    if value is None:
        return "NA"
    numeric_value = float(value)
    if numeric_value.is_integer():
        return str(int(numeric_value))
    return f"{numeric_value:.2f}".rstrip("0").rstrip(".")


def _format_bool(value: bool | None) -> str:
    if value is None:
        return "NA"
    return "1" if value else "0"


def _join_values(values) -> str:
    normalized = [str(value) for value in values if value not in (None, "", [])]
    return "|".join(normalized) if normalized else "NA"


def _json_field(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value in (None, ""):
        return {}
    return json.loads(value)
