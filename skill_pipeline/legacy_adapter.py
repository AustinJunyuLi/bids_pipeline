from __future__ import annotations

import csv
import io
from typing import Any

from skill_pipeline.db_export import _build_event_rows, _format_seed_date
from skill_pipeline.models_v2 import AnalystRowRecord, CohortRecord, PartyRecord


DROP_LABEL_BY_REASON = {
    "reason:not_invited": "DropTarget",
    "reason:lost_to_winner": "DropTarget",
}


def build_legacy_event_rows(
    parties: list[PartyRecord],
    cohorts: list[CohortRecord],
    analyst_rows: list[AnalystRowRecord],
) -> list[list[str]]:
    actors = [_legacy_actor_from_party(party) for party in parties]
    actors.extend(_legacy_actor_from_cohort(cohort) for cohort in cohorts)
    events = [_legacy_event_from_row(row) for row in analyst_rows]
    enrichment = {
        row.row_id: _legacy_enrichment_from_row(row)
        for row in analyst_rows
    }
    return _build_event_rows(actors, events, enrichment, [], [])


def serialize_legacy_deal_events(seed, event_rows: list[list[str]]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
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
    return buffer.getvalue()


def _legacy_actor_from_party(party: PartyRecord) -> dict[str, Any]:
    return {
        "actor_id": party.party_id,
        "display_name": party.display_name,
        "role": party.role,
        "bidder_kind": party.bidder_kind,
        "listing_status": party.listing_status,
        "geography": party.geography,
        "is_grouped": False,
        "group_size": None,
        "group_label": None,
    }


def _legacy_actor_from_cohort(cohort: CohortRecord) -> dict[str, Any]:
    return {
        "actor_id": cohort.cohort_id,
        "display_name": cohort.label,
        "role": "bidder",
        "bidder_kind": None,
        "listing_status": None,
        "geography": None,
        "is_grouped": True,
        "group_size": cohort.exact_count,
        "group_label": cohort.label,
    }


def _legacy_event_from_row(row: AnalystRowRecord) -> dict[str, Any]:
    event_date = row.date_recorded or row.date_public
    return {
        "event_id": row.row_id,
        "event_type": row.analyst_event_type,
        "date_sort": event_date,
        "date_precision": "exact_day" if event_date is not None else "unknown",
        "actor_ids": [row.subject_ref] if row.subject_ref else [],
        "summary": row.basis.explanation,
        "terms_per_share": row.value,
        "terms_range_low": row.range_low,
        "terms_range_high": row.range_high,
        "terms_consideration_type": "cash" if row.all_cash is True else None,
        "executed_with_actor_id": (
            row.subject_ref if row.analyst_event_type == "executed" and row.subject_ref else None
        ),
    }


def _legacy_enrichment_from_row(row: AnalystRowRecord) -> dict[str, Any]:
    dropout_label = next(
        (
            mapped
            for review_flag, mapped in DROP_LABEL_BY_REASON.items()
            if review_flag in row.review_flags
        ),
        None,
    )
    return {
        "event_id": row.row_id,
        "dropout_label": dropout_label,
        "dropout_basis": row.basis.explanation if dropout_label else None,
        "bid_label": row.bid_type,
        "bid_rule_applied": None,
        "bid_basis": row.basis.explanation if row.bid_type else None,
        "all_cash_override": row.all_cash if row.all_cash is True else None,
        "c1": None,
        "c2": None,
        "c3": None,
        "review_flags": None,
    }
