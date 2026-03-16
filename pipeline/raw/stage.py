from __future__ import annotations

import os
from collections.abc import Iterable
from typing import Any

from edgar import Company, find_company, get_by_accession_number, set_identity

from pipeline.config import PRIMARY_FILING_TYPES, RAW_DIR, SUPPLEMENTARY_FILING_TYPES
from pipeline.models.raw import RawDocumentRegistry
from pipeline.models.source import SeedDeal
from pipeline.raw.discover import build_raw_discovery_manifest
from pipeline.raw.fetch import atomic_write_json, fetch_filing_contents, freeze_raw_filing
from pipeline.source.ranking import extract_cik_from_url, search_terms_for_form

DEFAULT_IDENTITY = "Austin Li austin@example.com"


def fetch_raw_deal(
    seed: SeedDeal,
    *,
    run_id: str,
    raw_dir: Any = RAW_DIR,
    primary_filing_types: Iterable[str] = PRIMARY_FILING_TYPES,
    supplementary_filing_types: Iterable[str] = SUPPLEMENTARY_FILING_TYPES,
    search_fn: Any | None = None,
    fallback_lookup_fn: Any | None = get_by_accession_number,
    fetch_contents_fn: Any = fetch_filing_contents,
    identity: str | None = None,
    search_limit: int = 25,
) -> dict[str, Any]:
    raw_dir = RAW_DIR if raw_dir is None else raw_dir
    if search_fn is None:
        search_fn = build_edgar_search_fn(
            seed,
            identity=identity,
            search_limit=search_limit,
        )

    discovery = build_raw_discovery_manifest(
        seed,
        run_id=run_id,
        cik=extract_cik_from_url(seed.primary_url_seed),
        primary_filing_types=primary_filing_types,
        supplementary_filing_types=supplementary_filing_types,
        search_fn=search_fn,
        fallback_lookup_fn=fallback_lookup_fn,
    )
    raw_deal_dir = raw_dir / seed.deal_slug
    raw_deal_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(
        raw_deal_dir / "discovery.json",
        discovery.model_dump(mode="json"),
    )

    documents = []
    seen_keys: set[str] = set()
    for candidate in [*discovery.primary_candidates, *discovery.supplementary_candidates]:
        key = candidate.accession_number or candidate.document_id
        if key in seen_keys:
            continue
        seen_keys.add(key)
        accession = candidate.accession_number or candidate.document_id
        html_text, txt_text = fetch_contents_fn(accession, sec_url=candidate.sec_url)
        documents.append(
            freeze_raw_filing(
                candidate,
                deal_slug=seed.deal_slug,
                raw_dir=raw_dir,
                html_text=html_text,
                txt_text=txt_text,
            )
        )

    registry = RawDocumentRegistry(
        run_id=run_id,
        deal_slug=seed.deal_slug,
        documents=documents,
    )
    atomic_write_json(
        raw_deal_dir / "document_registry.json",
        registry.model_dump(mode="json"),
    )
    return {
        "deal_slug": seed.deal_slug,
        "cik": discovery.cik,
        "primary_candidate_count": len(discovery.primary_candidates),
        "supplementary_candidate_count": len(discovery.supplementary_candidates),
        "frozen_count": len(documents),
        "discovery_path": str((raw_deal_dir / "discovery.json").relative_to(raw_dir.parent)),
        "document_registry_path": str(
            (raw_deal_dir / "document_registry.json").relative_to(raw_dir.parent)
        ),
    }


def build_edgar_search_fn(
    seed: SeedDeal,
    *,
    identity: str | None = None,
    search_limit: int = 25,
) -> Any:
    company = _resolve_company(seed, identity=identity)

    def search_fn(filing_type: str) -> list[dict[str, Any]]:
        forms = list(search_terms_for_form(filing_type))
        filings = company.get_filings(
            form=forms if len(forms) > 1 else forms[0],
            amendments=True,
            trigger_full_load=False,
        )
        if filings.empty:
            return []
        return [
            {
                "accession_number": filing.accession_number,
                "filing_type": filing.form,
                "filing_date": filing.filing_date,
                "url": filing.url,
            }
            for filing in filings.head(search_limit)
        ]

    return search_fn


def _resolve_company(seed: SeedDeal, *, identity: str | None = None) -> Company:
    _set_identity(identity)
    cik = extract_cik_from_url(seed.primary_url_seed)
    if cik:
        return Company(cik)

    results = find_company(seed.target_name)
    if results.empty:
        raise ValueError(f"Unable to resolve company for seed target {seed.target_name!r}")
    return results[0]


def _set_identity(identity: str | None = None) -> None:
    selected = identity
    if selected is None:
        for env_name in ("PIPELINE_SEC_IDENTITY", "SEC_IDENTITY", "EDGAR_IDENTITY"):
            selected = os.getenv(env_name)
            if selected:
                break
    set_identity(selected or DEFAULT_IDENTITY)
