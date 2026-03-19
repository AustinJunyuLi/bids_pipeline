from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from skill_pipeline.config import PRIMARY_PREFERENCE
from skill_pipeline.pipeline_models.source import FilingCandidate, SeedDeal


FORM_SEARCH_ALIASES: dict[str, tuple[str, ...]] = {
    "SC 14D-9": ("SC 14D-9", "SC 14D9"),
    "SC 13E-3": ("SC 13E-3", "SC 13E3"),
}
FORM_CANONICAL_NAMES: dict[str, str] = {
    "SC 14D9": "SC 14D-9",
    "SC14D9": "SC 14D-9",
    "SC 13E3": "SC 13E-3",
    "SC13E3": "SC 13E-3",
}
SUPPLEMENTARY_PREFERENCE = {
    "DEFA14A": 0,
    "8-K": 1,
    "SC 13D": 2,
}


def search_terms_for_form(filing_type: str) -> tuple[str, ...]:
    return FORM_SEARCH_ALIASES.get(filing_type, (filing_type,))


def canonical_form_name(filing_type: str) -> str:
    normalized = re.sub(r"\s+", " ", filing_type.strip().upper())
    return FORM_CANONICAL_NAMES.get(normalized, normalized)


def extract_accession_from_url(url: str | None) -> str | None:
    if not url:
        return None
    dashed = re.search(r"(\d{10}-\d{2}-\d{6})", url)
    if dashed:
        return dashed.group(1)

    compact = re.search(r"(\d{18})", url)
    if compact:
        value = compact.group(1)
        return f"{value[:10]}-{value[10:12]}-{value[12:]}"
    return None


def extract_cik_from_url(url: str | None) -> str | None:
    if not url:
        return None
    match = re.search(r"/data/(\d+)/", url)
    return match.group(1) if match else None


def parse_filing_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def filing_window_days(filing_family: str) -> int:
    if filing_family == "primary":
        return 365
    if filing_family == "supplementary":
        return 180
    raise ValueError(f"Unknown filing family: {filing_family}")


def rank_filing_candidates(
    seed: SeedDeal,
    search_results: list[Any],
    *,
    filing_family: str,
    top_k: int,
) -> list[FilingCandidate]:
    announcement_date = seed.date_announced_seed
    window_days = filing_window_days(filing_family)
    seed_accession = extract_accession_from_url(seed.primary_url_seed)

    candidates: list[FilingCandidate] = []
    for index, result in enumerate(search_results, start=1):
        accession_number = _result_value(result, "accession_number")
        filing_type = canonical_form_name(
            _result_value(result, "filing_type")
            or _result_value(result, "form")
            or ""
        )
        filing_date = parse_filing_date(_result_value(result, "filing_date"))
        sec_url = _result_value(result, "url") or _result_value(result, "sec_url")
        source_origin = _result_value(result, "source_origin") or "edgartools_search"

        days_from_announcement = None
        in_window = True
        if announcement_date and filing_date:
            days_from_announcement = abs((filing_date - announcement_date).days)
            in_window = days_from_announcement <= window_days

        seed_accession_match = accession_number == seed_accession
        if not in_window and not seed_accession_match:
            continue

        document_id = accession_number or f"{filing_type.lower()}-{index:03d}"
        form_preference = _form_preference(filing_type, filing_family)
        candidates.append(
            FilingCandidate(
                document_id=document_id,
                accession_number=accession_number,
                filing_type=filing_type,
                filing_date=filing_date,
                sec_url=sec_url,
                source_origin=source_origin,
                ranking_features={
                    "seed_accession_match": seed_accession_match,
                    "days_from_announcement": days_from_announcement,
                    "within_window": in_window,
                    "form_preference": form_preference,
                    "filing_family": filing_family,
                },
            )
        )

    candidates.sort(
        key=lambda candidate: (
            0 if candidate.ranking_features["seed_accession_match"] else 1,
            candidate.ranking_features["form_preference"],
            candidate.ranking_features["days_from_announcement"]
            if candidate.ranking_features["days_from_announcement"] is not None
            else float("inf"),
            candidate.accession_number or candidate.document_id,
        )
    )
    return candidates[:top_k]


def _form_preference(filing_type: str, filing_family: str) -> int:
    if filing_family == "primary":
        return PRIMARY_PREFERENCE.get(filing_type, len(PRIMARY_PREFERENCE))
    return SUPPLEMENTARY_PREFERENCE.get(filing_type, len(SUPPLEMENTARY_PREFERENCE))


def _result_value(result: Any, field_name: str) -> Any:
    if isinstance(result, dict):
        return result.get(field_name)
    return getattr(result, field_name, None)
