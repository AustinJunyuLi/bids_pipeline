from __future__ import annotations

import json
from pathlib import Path

import pytest

from skill_pipeline.preprocess.source import preprocess_source_deal


def _write_seed_only_raw_fixture(
    tmp_path: Path,
    *,
    primary_candidates: list[dict] | None = None,
    supplementary_candidates: list[dict] | None = None,
    extra_documents: list[dict] | None = None,
) -> tuple[Path, Path]:
    raw_deal_dir = tmp_path / "raw" / "imprivata"
    filings_dir = raw_deal_dir / "filings"
    deals_dir = tmp_path / "data" / "deals"
    source_dir = deals_dir / "imprivata" / "source"
    filings_dir.mkdir(parents=True, exist_ok=True)
    source_dir.mkdir(parents=True, exist_ok=True)

    primary_candidate = {
        "document_id": "0001193125-16-677939",
        "accession_number": "0001193125-16-677939",
        "filing_type": "UNKNOWN",
        "sec_url": (
            "https://www.sec.gov/Archives/edgar/data/1328015/"
            "0001193125-16-677939-index.htm"
        ),
        "source_origin": "seed_accession",
        "ranking_features": {},
    }
    registry_document = {
        "document_id": "0001193125-16-677939",
        "accession_number": "0001193125-16-677939",
        "filing_type": "UNKNOWN",
        "txt_path": "raw/imprivata/filings/0001193125-16-677939.txt",
        "sha256_txt": "x",
        "byte_count_txt": 1,
        "fetched_at": "2026-03-20T00:00:00Z",
    }

    discovery = {
        "artifact_type": "raw_discovery_manifest",
        "run_id": "run-1",
        "deal_slug": "imprivata",
        "seed": {
            "artifact_type": "seed_deal",
            "run_id": "run-1",
            "deal_slug": "imprivata",
            "target_name": "IMPRIVATA INC",
            "primary_url_seed": primary_candidate["sec_url"],
            "is_reference": False,
        },
        "cik": "1328015",
        "primary_candidates": primary_candidates if primary_candidates is not None else [primary_candidate],
        "supplementary_candidates": supplementary_candidates or [],
        "fetch_scope": "seed_only",
    }
    registry = {
        "artifact_type": "raw_document_registry",
        "run_id": "run-1",
        "deal_slug": "imprivata",
        "documents": [registry_document, *(extra_documents or [])],
    }

    (raw_deal_dir / "discovery.json").write_text(json.dumps(discovery), encoding="utf-8")
    (raw_deal_dir / "document_registry.json").write_text(json.dumps(registry), encoding="utf-8")
    (filings_dir / "0001193125-16-677939.txt").write_text(
        "\n".join(
            [
                "Background of the Merger",
                "",
                "On July 1, 2016, Party A signed a confidentiality agreement.",
                "",
                "On July 5, 2016, Party A submitted an indication of interest.",
                "",
                "Opinion of Financial Advisor",
            ]
        ),
        encoding="utf-8",
    )

    return raw_deal_dir, deals_dir


def test_preprocess_source_scans_only_the_single_seed_document_and_cleans_stale_artifacts(
    tmp_path: Path,
) -> None:
    raw_deal_dir, deals_dir = _write_seed_only_raw_fixture(tmp_path)
    source_dir = deals_dir / "imprivata" / "source"
    source_filings_dir = source_dir / "filings"
    source_filings_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "supplementary_snippets.jsonl").write_text("stale\n", encoding="utf-8")
    (source_filings_dir / "stale-doc.txt").write_text("stale\n", encoding="utf-8")

    result = preprocess_source_deal(
        "imprivata",
        run_id="run-1",
        raw_dir=raw_deal_dir.parent,
        deals_dir=deals_dir,
    )

    evidence_path = source_dir / "evidence_items.jsonl"
    evidence = [
        json.loads(line)
        for line in evidence_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert result["candidate_count"] == 1
    assert result["scanned_document_count"] == 1
    assert all(item["document_id"] == "0001193125-16-677939" for item in evidence)
    assert not (source_dir / "supplementary_snippets.jsonl").exists()
    assert not (source_filings_dir / "stale-doc.txt").exists()
    assert (source_filings_dir / "0001193125-16-677939.txt").exists()


def test_preprocess_source_fails_when_supplementary_candidates_are_present(
    tmp_path: Path,
) -> None:
    raw_deal_dir, deals_dir = _write_seed_only_raw_fixture(
        tmp_path,
        supplementary_candidates=[
            {
                "document_id": "0001193125-16-662313",
                "accession_number": "0001193125-16-662313",
                "filing_type": "PREM14A",
                "sec_url": (
                    "https://www.sec.gov/Archives/edgar/data/1328015/"
                    "0001193125-16-662313-index.htm"
                ),
                "source_origin": "seed_accession",
                "ranking_features": {},
            }
        ],
    )

    with pytest.raises(ValueError, match="supplementary_candidates"):
        preprocess_source_deal(
            "imprivata",
            run_id="run-1",
            raw_dir=raw_deal_dir.parent,
            deals_dir=deals_dir,
        )


def test_preprocess_source_fails_when_registry_has_multiple_documents(tmp_path: Path) -> None:
    raw_deal_dir, deals_dir = _write_seed_only_raw_fixture(
        tmp_path,
        extra_documents=[
            {
                "document_id": "0001193125-16-662313",
                "accession_number": "0001193125-16-662313",
                "filing_type": "PREM14A",
                "txt_path": "raw/imprivata/filings/0001193125-16-662313.txt",
                "sha256_txt": "y",
                "byte_count_txt": 1,
                "fetched_at": "2026-03-20T00:00:00Z",
            }
        ],
    )

    with pytest.raises(ValueError, match="document_registry"):
        preprocess_source_deal(
            "imprivata",
            run_id="run-1",
            raw_dir=raw_deal_dir.parent,
            deals_dir=deals_dir,
        )


@pytest.mark.parametrize(
    "primary_candidates",
    [
        [],
        [
            {
                "document_id": "0001193125-16-677939",
                "accession_number": "0001193125-16-677939",
                "filing_type": "UNKNOWN",
                "sec_url": (
                    "https://www.sec.gov/Archives/edgar/data/1328015/"
                    "0001193125-16-677939-index.htm"
                ),
                "source_origin": "seed_accession",
                "ranking_features": {},
            },
            {
                "document_id": "0001193125-16-662313",
                "accession_number": "0001193125-16-662313",
                "filing_type": "UNKNOWN",
                "sec_url": (
                    "https://www.sec.gov/Archives/edgar/data/1328015/"
                    "0001193125-16-662313-index.htm"
                ),
                "source_origin": "seed_accession",
                "ranking_features": {},
            },
        ],
    ],
)
def test_preprocess_source_fails_when_primary_candidate_count_is_not_one(
    tmp_path: Path,
    primary_candidates: list[dict],
) -> None:
    raw_deal_dir, deals_dir = _write_seed_only_raw_fixture(
        tmp_path,
        primary_candidates=primary_candidates,
    )

    with pytest.raises(ValueError, match="exactly one primary candidate"):
        preprocess_source_deal(
            "imprivata",
            run_id="run-1",
            raw_dir=raw_deal_dir.parent,
            deals_dir=deals_dir,
        )


def test_preprocess_source_fails_when_primary_candidate_is_missing_from_registry(
    tmp_path: Path,
) -> None:
    raw_deal_dir, deals_dir = _write_seed_only_raw_fixture(tmp_path)
    discovery_path = raw_deal_dir / "discovery.json"
    discovery = json.loads(discovery_path.read_text(encoding="utf-8"))
    discovery["primary_candidates"][0]["document_id"] = "missing-doc"
    discovery["primary_candidates"][0]["accession_number"] = "0001193125-16-600000"
    discovery_path.write_text(json.dumps(discovery), encoding="utf-8")

    with pytest.raises(ValueError, match="missing from document_registry"):
        preprocess_source_deal(
            "imprivata",
            run_id="run-1",
            raw_dir=raw_deal_dir.parent,
            deals_dir=deals_dir,
        )
