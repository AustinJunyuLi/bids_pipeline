"""Deterministic CSV export from materialized artifacts and enrichment."""

from __future__ import annotations

import csv
import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from skill_pipeline.core.artifacts import load_artifacts
from skill_pipeline.core.config import PROJECT_ROOT
from skill_pipeline.schemas.runtime import (
    SkillActorRecord,
    SkillEnrichmentArtifact,
    SkillEventRecord,
)
from skill_pipeline.core.paths import build_skill_paths, ensure_output_directories
from skill_pipeline.core.seeds import load_seed_entry

EVENT_COLUMNS = [
    "bidderID",
    "note",
    "bidder",
    "type",
    "bid_type",
    "val",
    "range",
    "date_r",
    "date_p",
    "cash",
    "c1",
    "c2",
    "c3",
    "review_flags",
]

HEADER_COLUMNS = ["TargetName", "Events", "Acquirer", "DateAnnounced", "URL"]

NOTE_MAP = {
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

TYPE_PRIORITY = {
    "target_sale": 0,
    "target_sale_public": 1,
    "bidder_sale": 2,
    "bidder_interest": 3,
    "activist_sale": 4,
    "sale_press_release": 5,
    "bid_press_release": 6,
    "ib_retention": 7,
    "nda": 8,
    "final_round_inf_ann": 9,
    "final_round_ann": 10,
    "final_round_ext_ann": 11,
    "drop": 12,
    "final_round_inf": 13,
    "final_round": 14,
    "final_round_ext": 15,
    "proposal": 16,
    "executed": 17,
    "terminated": 18,
    "restarted": 19,
}


def compose_bidder_type(actor: SkillActorRecord) -> str:
    if actor.role != "bidder":
        return "NA"
    if (
        actor.geography == "non_us"
        and actor.listing_status == "public"
        and actor.bidder_kind == "strategic"
    ):
        return "non-US public S"
    if (
        actor.geography == "non_us"
        and actor.listing_status == "public"
        and actor.bidder_kind == "financial"
    ):
        return "non-US public F"
    if actor.geography == "non_us" and actor.bidder_kind == "strategic":
        return "non-US S"
    if actor.geography == "non_us" and actor.bidder_kind == "financial":
        return "non-US F"
    if actor.listing_status == "public" and actor.bidder_kind == "strategic":
        return "public S"
    if actor.listing_status == "public" and actor.bidder_kind == "financial":
        return "public F"
    if actor.bidder_kind == "strategic":
        return "S"
    if actor.bidder_kind == "financial":
        return "F"
    if actor.is_grouped and actor.group_size is not None and actor.group_label:
        return f"{actor.group_size}{actor.group_label}"
    return "NA"


def run_export(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    paths = build_skill_paths(deal_slug, project_root=project_root)
    if not paths.enrichment_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.enrichment_path}")

    artifacts = load_artifacts(paths)
    enrichment = SkillEnrichmentArtifact.model_validate(
        json.loads(paths.enrichment_path.read_text(encoding="utf-8"))
    )
    seed = load_seed_entry(deal_slug, seeds_path=paths.seeds_path)

    actor_lookup = {actor.actor_id: actor for actor in artifacts.actors.actors}
    events = sorted(artifacts.events.events, key=_sort_key)
    event_ids = _assign_bidder_ids(events)
    seen_actor_ids: set[str] = set()

    ensure_output_directories(paths)
    with paths.deal_events_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER_COLUMNS)
        writer.writerow(
            [
                seed.target_name,
                str(len(events)),
                seed.acquirer or "",
                _format_seed_date(seed.date_announced),
                seed.primary_url or "",
            ]
        )
        writer.writerow([])
        writer.writerow(EVENT_COLUMNS)
        for bidder_id, event in zip(event_ids, events, strict=True):
            writer.writerow(
                _build_event_row(
                    event,
                    bidder_id=bidder_id,
                    actor_lookup=actor_lookup,
                    enrichment=enrichment,
                    seen_actor_ids=seen_actor_ids,
                )
            )
    return 0


def _sort_key(event: SkillEventRecord) -> tuple[date, int, str]:
    sort_date = event.date.sort_date or event.date.normalized_start or date.max
    return (
        sort_date,
        TYPE_PRIORITY.get(event.event_type, 999),
        event.event_id,
    )


def _assign_bidder_ids(events: list[SkillEventRecord]) -> list[str]:
    first_nda_index = next(
        (idx for idx, event in enumerate(events) if event.event_type == "nda"), None
    )
    if first_nda_index is None:
        return [str(index) for index in range(1, len(events) + 1)]

    ids: list[str] = []
    pre_nda_count = first_nda_index
    for index in range(pre_nda_count):
        step = round((index + 1) / (pre_nda_count + 1), 1)
        ids.append(f"{step:.1f}")
    for index in range(len(events) - pre_nda_count):
        ids.append(str(index + 1))
    return ids


def _build_event_row(
    event: SkillEventRecord,
    *,
    bidder_id: str,
    actor_lookup: dict[str, SkillActorRecord],
    enrichment: SkillEnrichmentArtifact,
    seen_actor_ids: set[str],
) -> list[str]:
    actor_ids = [actor_id for actor_id in event.actor_ids if actor_id in actor_lookup]
    actors = [actor_lookup[actor_id] for actor_id in actor_ids]
    bidder = "/".join(actor.display_name for actor in actors) if actors else "NA"

    row_type = "NA"
    actor_types = [compose_bidder_type(actor) for actor in actors]
    should_populate_type = event.event_type != "bidder_interest"
    if (
        should_populate_type
        and actors
        and any(actor_id not in seen_actor_ids for actor_id in actor_ids)
    ):
        joined_type = "/".join(
            actor_type for actor_type in actor_types if actor_type != "NA"
        )
        row_type = joined_type or "NA"
        seen_actor_ids.update(actor_ids)

    note = _note_for_event(event, enrichment)
    bid_type, extra_flags = _bid_type_and_flags(event, enrichment)
    value_text = _proposal_value(event)
    range_text = _proposal_range(event)
    date_r, date_p = _format_event_dates(event)
    cash = "1" if event.terms and event.terms.consideration_type == "cash" else "NA"
    c1 = _c1_for_event(event)
    c2 = ""
    c3 = ""
    review_flags = _row_review_flags(event, enrichment, extra_flags)
    if (
        event.terms
        and event.terms.per_share is None
        and event.terms.enterprise_value is not None
    ):
        c1 = f"Enterprise value only: {_format_decimal(event.terms.enterprise_value)}"

    return [
        bidder_id,
        note,
        bidder,
        row_type,
        bid_type,
        value_text,
        range_text,
        date_r,
        date_p,
        cash,
        c1,
        c2,
        c3,
        review_flags,
    ]


def _note_for_event(
    event: SkillEventRecord, enrichment: SkillEnrichmentArtifact
) -> str:
    if event.event_type == "drop":
        classification = enrichment.dropout_classifications.get(event.event_id)
        return classification.label if classification else "Drop"
    return NOTE_MAP.get(event.event_type, event.event_type)


def _bid_type_and_flags(
    event: SkillEventRecord,
    enrichment: SkillEnrichmentArtifact,
) -> tuple[str, list[str]]:
    if event.event_type != "proposal":
        return "NA", []
    classification = enrichment.bid_classifications.get(event.event_id)
    if classification is None:
        return "NA", []
    if classification.label == "Uncertain":
        return "NA", [f"bid_classification_uncertain:{event.event_id}"]
    return classification.label, []


def _proposal_value(event: SkillEventRecord) -> str:
    if (
        event.event_type != "proposal"
        or event.terms is None
        or event.terms.per_share is None
    ):
        return "NA"
    return _format_decimal(event.terms.per_share)


def _proposal_range(event: SkillEventRecord) -> str:
    if event.event_type != "proposal" or event.terms is None:
        return "NA"
    if event.terms.range_low is not None and event.terms.range_high is not None:
        return f"{_format_decimal(event.terms.range_low)}-{_format_decimal(event.terms.range_high)}"
    if event.terms.per_share is not None:
        val = _format_decimal(event.terms.per_share)
        return f"{val}-{val}"
    return "NA"


def _format_event_dates(event: SkillEventRecord) -> tuple[str, str]:
    if event.date.sort_date is None and event.date.normalized_start is None:
        return "NA", "NA"
    rough = event.date.sort_date or event.date.normalized_start
    rough_text = rough.strftime("%m/%d/%Y") if rough else "NA"
    if event.date.precision == "exact_day" and event.date.normalized_start is not None:
        return rough_text, event.date.normalized_start.strftime("%m/%d/%Y")
    return rough_text, "NA"


def _c1_for_event(event: SkillEventRecord) -> str:
    if event.event_type == "drop" and event.drop_reason_text:
        return event.drop_reason_text
    return ""


def _row_review_flags(
    event: SkillEventRecord,
    enrichment: SkillEnrichmentArtifact,
    extra_flags: list[str],
) -> str:
    flags = [
        flag
        for flag in enrichment.review_flags
        if f":{event.event_id}" in flag or flag.endswith(event.event_id)
    ]
    flags.extend(extra_flags)
    if (
        event.terms
        and event.terms.per_share is None
        and event.terms.enterprise_value is not None
    ):
        flags.append(f"enterprise_value_only:{event.event_id}")
    return "|".join(_unique(flags))


def _format_seed_date(value: str | None) -> str:
    if not value:
        return ""
    try:
        return date.fromisoformat(value).strftime("%m/%d/%Y")
    except ValueError:
        return value


def _format_decimal(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
