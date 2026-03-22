from __future__ import annotations

import os
from typing import Any

from skill_pipeline.config import RAW_DIR
from skill_pipeline.pipeline_models.raw import RawDocumentRegistry
from skill_pipeline.pipeline_models.source import SeedDeal
from skill_pipeline.raw.discover import build_raw_discovery_manifest
from skill_pipeline.raw.fetch import atomic_write_json, fetch_filing_contents, freeze_raw_filing
from skill_pipeline.source.ranking import extract_cik_from_url

try:  # pragma: no cover - optional dependency in tests.
    from edgar import set_identity
except ModuleNotFoundError:  # pragma: no cover
    set_identity = None


def fetch_raw_deal(
    seed: SeedDeal,
    *,
    run_id: str,
    raw_dir: Any = RAW_DIR,
    fetch_contents_fn: Any = fetch_filing_contents,
    identity: str | None = None,
) -> dict[str, Any]:
    raw_dir = RAW_DIR if raw_dir is None else raw_dir

    discovery = build_raw_discovery_manifest(
        seed,
        run_id=run_id,
        cik=extract_cik_from_url(seed.primary_url_seed),
    )
    if fetch_contents_fn is fetch_filing_contents:
        _set_identity(identity)
    raw_deal_dir = raw_dir / seed.deal_slug
    raw_deal_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(raw_deal_dir / "discovery.json", discovery.model_dump(mode="json"))

    candidate = discovery.primary_candidates[0]
    accession = candidate.accession_number or candidate.document_id
    html_text, txt_text = fetch_contents_fn(accession, sec_url=candidate.sec_url)
    document = freeze_raw_filing(
        candidate,
        deal_slug=seed.deal_slug,
        raw_dir=raw_dir,
        html_text=html_text,
        txt_text=txt_text,
    )

    registry = RawDocumentRegistry(run_id=run_id, deal_slug=seed.deal_slug, documents=[document])
    atomic_write_json(raw_deal_dir / "document_registry.json", registry.model_dump(mode="json"))
    return {
        "deal_slug": seed.deal_slug,
        "cik": discovery.cik,
        "primary_candidate_count": len(discovery.primary_candidates),
        "supplementary_candidate_count": len(discovery.supplementary_candidates),
        "frozen_count": 1,
        "discovery_path": str((raw_deal_dir / "discovery.json").relative_to(raw_dir.parent)),
        "document_registry_path": str((raw_deal_dir / "document_registry.json").relative_to(raw_dir.parent)),
    }


def _set_identity(identity: str | None = None) -> None:
    if set_identity is None:
        raise ModuleNotFoundError(
            "edgar is required for live SEC access; pass fetch_contents_fn in tests or install edgartools."
        )
    selected = identity
    if selected is None:
        for env_name in ("PIPELINE_SEC_IDENTITY", "SEC_IDENTITY", "EDGAR_IDENTITY"):
            selected = os.getenv(env_name)
            if selected:
                break
    if not selected:
        raise ValueError(
            "EDGAR_IDENTITY is required for live SEC access. "
            "Set EDGAR_IDENTITY (or pass identity=...) before running raw-fetch."
        )
    set_identity(selected)
