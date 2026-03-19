from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from skill_pipeline.pipeline_models.source import FilingCandidate, SeedDeal
from skill_pipeline.source.ranking import extract_accession_from_url, rank_filing_candidates


SearchFn = Callable[[str], list[Any]]
FallbackLookupFn = Callable[[str], Any | None]


def search_candidates_with_fallback(
    seed: SeedDeal,
    *,
    filing_type: str,
    filing_family: str,
    search_fn: SearchFn,
    fallback_lookup_fn: FallbackLookupFn | None = None,
    top_k: int = 3,
) -> list[FilingCandidate]:
    try:
        search_results = list(search_fn(filing_type))
    except Exception:
        search_results = []

    if not search_results and fallback_lookup_fn is not None:
        seed_accession = extract_accession_from_url(seed.primary_url_seed)
        if seed_accession:
            fallback_result = fallback_lookup_fn(seed_accession)
            if fallback_result is not None:
                search_results = [dict(_coerce_result(fallback_result), source_origin="seed_accession")]

    return rank_filing_candidates(
        seed,
        search_results,
        filing_family=filing_family,
        top_k=top_k,
    )


def load_filing_overrides(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}

    import yaml

    with path.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError("filing_override.yaml must contain a mapping")
    return payload


def _coerce_result(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        return dict(result)
    return {
        "accession_number": getattr(result, "accession_number", None),
        "filing_type": getattr(result, "filing_type", None) or getattr(result, "form", None),
        "filing_date": getattr(result, "filing_date", None),
        "url": getattr(result, "url", None),
    }
