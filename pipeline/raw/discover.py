from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from pipeline.config import PRIMARY_FILING_TYPES, SUPPLEMENTARY_FILING_TYPES
from pipeline.models.raw import RawDiscoveryManifest
from pipeline.models.source import FilingCandidate, SeedDeal
from pipeline.source.discovery import FallbackLookupFn, SearchFn, search_candidates_with_fallback


def collect_filing_candidates(
    seed: SeedDeal,
    *,
    filing_types: Iterable[str],
    filing_family: str,
    search_fn: SearchFn,
    fallback_lookup_fn: FallbackLookupFn | None = None,
    top_k_per_form: int = 3,
) -> list[FilingCandidate]:
    candidates: list[FilingCandidate] = []
    for filing_type in filing_types:
        candidates.extend(
            search_candidates_with_fallback(
                seed,
                filing_type=filing_type,
                filing_family=filing_family,
                search_fn=search_fn,
                fallback_lookup_fn=fallback_lookup_fn,
                top_k=top_k_per_form,
            )
        )
    return _dedupe_candidates(candidates)


def build_raw_discovery_manifest(
    seed: SeedDeal,
    *,
    run_id: str,
    cik: str | None = None,
    primary_filing_types: Iterable[str] = PRIMARY_FILING_TYPES,
    supplementary_filing_types: Iterable[str] = SUPPLEMENTARY_FILING_TYPES,
    search_fn: SearchFn,
    fallback_lookup_fn: FallbackLookupFn | None = None,
    top_k_per_form: int = 3,
) -> RawDiscoveryManifest:
    primary_candidates = collect_filing_candidates(
        seed,
        filing_types=primary_filing_types,
        filing_family="primary",
        search_fn=search_fn,
        fallback_lookup_fn=fallback_lookup_fn,
        top_k_per_form=top_k_per_form,
    )
    supplementary_candidates = collect_filing_candidates(
        seed,
        filing_types=supplementary_filing_types,
        filing_family="supplementary",
        search_fn=search_fn,
        fallback_lookup_fn=fallback_lookup_fn,
        top_k_per_form=top_k_per_form,
    )
    return RawDiscoveryManifest(
        run_id=run_id,
        deal_slug=seed.deal_slug,
        seed=seed,
        cik=cik,
        primary_candidates=primary_candidates,
        supplementary_candidates=supplementary_candidates,
    )


def _dedupe_candidates(candidates: list[FilingCandidate]) -> list[FilingCandidate]:
    unique: dict[str, FilingCandidate] = {}
    for candidate in sorted(candidates, key=_candidate_sort_key):
        key = candidate.accession_number or candidate.document_id
        unique.setdefault(key, candidate)
    return list(unique.values())


def _candidate_sort_key(candidate: FilingCandidate) -> tuple[Any, ...]:
    ranking = candidate.ranking_features
    return (
        0 if ranking.get("seed_accession_match") else 1,
        ranking.get("form_preference", float("inf")),
        ranking.get("days_from_announcement", float("inf")),
        candidate.accession_number or candidate.document_id,
    )
