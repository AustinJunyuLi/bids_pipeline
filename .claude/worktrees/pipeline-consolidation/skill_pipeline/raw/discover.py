from __future__ import annotations

import re
from urllib.parse import urlparse

from skill_pipeline.pipeline_models.raw import RawDiscoveryManifest
from skill_pipeline.pipeline_models.source import FilingCandidate, SeedDeal
from skill_pipeline.source.ranking import extract_cik_from_url


def build_raw_discovery_manifest(
    seed: SeedDeal,
    *,
    run_id: str,
    cik: str | None = None,
) -> RawDiscoveryManifest:
    candidate = _candidate_from_seed_url(seed)
    return RawDiscoveryManifest(
        run_id=run_id,
        deal_slug=seed.deal_slug,
        seed=seed,
        cik=cik if cik is not None else extract_cik_from_url(seed.primary_url_seed),
        primary_candidates=[candidate],
        supplementary_candidates=[],
        fetch_scope="seed_only",
    )


def _candidate_from_seed_url(seed: SeedDeal) -> FilingCandidate:
    sec_url = seed.primary_url_seed
    accession_number = _extract_unambiguous_accession(sec_url)
    return FilingCandidate(
        document_id=accession_number,
        accession_number=accession_number,
        filing_type="UNKNOWN",
        sec_url=sec_url,
        source_origin="seed_accession",
        ranking_features={
            "seed_accession_match": True,
            "filing_family": "primary",
        },
    )


def _extract_unambiguous_accession(url: str | None) -> str:
    if not url:
        raise ValueError("primary_url is required and must be a standard SEC Archives filing URL")
    if not _is_standard_sec_archives_url(url):
        raise ValueError("primary_url must be a standard SEC Archives filing URL")

    matches = re.findall(r"\d{10}-\d{2}-\d{6}|\d{18}", url)
    normalized_matches = {_normalize_accession(match) for match in matches}
    if len(normalized_matches) > 1:
        raise ValueError("primary_url contains an ambiguous accession")
    if not normalized_matches:
        raise ValueError("primary_url must contain an unambiguous SEC accession")
    return normalized_matches.pop()


def _normalize_accession(value: str) -> str:
    if re.fullmatch(r"\d{10}-\d{2}-\d{6}", value):
        return value
    if re.fullmatch(r"\d{18}", value):
        return f"{value[:10]}-{value[10:12]}-{value[12:]}"
    raise ValueError(f"Invalid accession format: {value}")


def _is_standard_sec_archives_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    if parsed.netloc not in {"sec.gov", "www.sec.gov"}:
        return False
    return parsed.path.startswith("/Archives/edgar/data/")
