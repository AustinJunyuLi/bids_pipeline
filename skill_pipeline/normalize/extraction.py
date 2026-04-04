from __future__ import annotations

import logging
from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

logger = logging.getLogger(__name__)

_INFO_MESSAGES: tuple[tuple[str, str], ...] = (
    ("obs_type_aliases", "normalize_raw_extraction.obs_type_aliases"),
    ("string_dates_wrapped", "normalize_raw_extraction.string_dates_wrapped"),
    ("day_precisions_mapped", "normalize_raw_extraction.day_precisions_mapped"),
    ("party_names_renamed", "normalize_raw_extraction.party_names_renamed"),
    ("cohort_descriptions_renamed", "normalize_raw_extraction.cohort_descriptions_renamed"),
    (
        "cohort_known_members_renamed",
        "normalize_raw_extraction.cohort_known_members_renamed",
    ),
    ("coverage_dicts_replaced", "normalize_raw_extraction.coverage_dicts_replaced"),
    ("exclusions_renamed", "normalize_raw_extraction.exclusions_renamed"),
    ("price_per_share_renamed", "normalize_raw_extraction.price_per_share_renamed"),
    ("per_share_values_normalized", "normalize_raw_extraction.per_share_values_normalized"),
)


def normalize_raw_extraction(data: dict) -> dict:
    """Normalize deterministic raw-extraction mismatches before validation."""
    normalized = deepcopy(data)
    counts = {key: 0 for key, _ in _INFO_MESSAGES}
    warning_counts = {
        "proposal_empty_subject_refs": 0,
        "cohort_missing_created_by_observation_id": 0,
    }

    parties = normalized.get("parties")
    if isinstance(parties, list):
        for party in parties:
            if isinstance(party, dict) and _rename_key(party, "name", "display_name"):
                counts["party_names_renamed"] += 1

    cohorts = normalized.get("cohorts")
    if isinstance(cohorts, list):
        for cohort in cohorts:
            if not isinstance(cohort, dict):
                continue
            if _rename_key(cohort, "description", "label"):
                counts["cohort_descriptions_renamed"] += 1
            if _rename_key(cohort, "known_members", "known_member_party_ids"):
                counts["cohort_known_members_renamed"] += 1
            if cohort.get("created_by_observation_id") in (None, ""):
                warning_counts["cohort_missing_created_by_observation_id"] += 1

    observations = normalized.get("observations")
    if isinstance(observations, list):
        for observation in observations:
            if not isinstance(observation, dict):
                continue
            if _normalize_obs_type(observation):
                counts["obs_type_aliases"] += 1

            for field_name in ("date", "due_date"):
                if field_name not in observation:
                    continue
                updated, wrapped_count, precision_count = _normalize_resolved_date(
                    observation[field_name]
                )
                observation[field_name] = updated
                counts["string_dates_wrapped"] += wrapped_count
                counts["day_precisions_mapped"] += precision_count

            terms = observation.get("terms")
            if isinstance(terms, dict):
                if _rename_key(terms, "price_per_share", "per_share"):
                    counts["price_per_share_renamed"] += 1
                if _normalize_per_share(terms):
                    counts["per_share_values_normalized"] += 1

            if observation.get("obs_type") == "proposal" and not observation.get("subject_refs"):
                warning_counts["proposal_empty_subject_refs"] += 1

    exclusions = normalized.get("exclusions")
    if isinstance(exclusions, list):
        for exclusion in exclusions:
            if not isinstance(exclusion, dict):
                continue
            changed = _rename_key(exclusion, "item", "category")
            changed = _rename_key(exclusion, "reason", "explanation") or changed
            if changed:
                counts["exclusions_renamed"] += 1

    if isinstance(normalized.get("coverage"), dict):
        normalized["coverage"] = []
        counts["coverage_dicts_replaced"] += 1

    for key, message in _INFO_MESSAGES:
        logger.info("%s count=%d", message, counts[key])

    if warning_counts["proposal_empty_subject_refs"]:
        logger.warning(
            "normalize_raw_extraction.proposal_empty_subject_refs count=%d",
            warning_counts["proposal_empty_subject_refs"],
        )
    if warning_counts["cohort_missing_created_by_observation_id"]:
        logger.warning(
            "normalize_raw_extraction.cohort_missing_created_by_observation_id count=%d",
            warning_counts["cohort_missing_created_by_observation_id"],
        )

    return normalized


def _rename_key(record: dict[str, Any], old_key: str, new_key: str) -> bool:
    if old_key not in record:
        return False
    if new_key not in record:
        record[new_key] = record[old_key]
    del record[old_key]
    return True


def _normalize_obs_type(record: dict[str, Any]) -> bool:
    changed = False
    for alias in ("observation_type", "type"):
        if alias not in record:
            continue
        if "obs_type" not in record:
            record["obs_type"] = record[alias]
        del record[alias]
        changed = True
    return changed


def _normalize_resolved_date(value: Any) -> tuple[Any, int, int]:
    if isinstance(value, str):
        return _wrap_resolved_date(value), 1, 0
    if not isinstance(value, dict):
        return value, 0, 0
    if value.get("precision") == "day":
        value["precision"] = "exact_day"
        return value, 0, 1
    return value, 0, 0


def _wrap_resolved_date(raw_value: str) -> dict[str, Any]:
    stripped = raw_value.strip()
    try:
        parsed = date.fromisoformat(stripped)
    except ValueError:
        return {
            "raw_text": raw_value,
            "normalized_start": None,
            "normalized_end": None,
            "sort_date": None,
            "precision": "unknown",
            "anchor_event_id": None,
            "anchor_span_id": None,
            "resolution_note": None,
            "is_inferred": False,
        }
    normalized_day = parsed.isoformat()
    return {
        "raw_text": raw_value,
        "normalized_start": normalized_day,
        "normalized_end": normalized_day,
        "sort_date": normalized_day,
        "precision": "exact_day",
        "anchor_event_id": None,
        "anchor_span_id": None,
        "resolution_note": None,
        "is_inferred": False,
    }


def _normalize_per_share(terms: dict[str, Any]) -> bool:
    value = terms.get("per_share")
    if not isinstance(value, str):
        return False
    if "$" not in value and "," not in value:
        return False
    cleaned = value.replace("$", "").replace(",", "").strip()
    try:
        terms["per_share"] = Decimal(cleaned)
    except InvalidOperation:
        return False
    return True


__all__ = ["normalize_raw_extraction"]
