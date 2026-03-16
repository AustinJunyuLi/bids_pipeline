from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from pipeline.models.common import SCHEMA_VERSION
from pipeline.models.source import FilingCandidate, SeedDeal
from pipeline.raw.discover import build_raw_discovery_manifest
from pipeline.raw.fetch import freeze_raw_filing, write_immutable_text


def _seed() -> SeedDeal:
    return SeedDeal(
        schema_version=SCHEMA_VERSION,
        artifact_type="seed_deal",
        created_at=datetime(2026, 3, 16, tzinfo=UTC),
        pipeline_version="0.1.0",
        run_id="run-1",
        deal_slug="zep",
        target_name="ZEP INC",
        acquirer_seed="New Mountain Capital",
        date_announced_seed=date(2015, 4, 8),
        primary_url_seed="https://www.sec.gov/Archives/edgar/data/1408287/000104746915004456/a2224606zprem14a.htm",
        is_reference=True,
        seed_row_refs=[],
    )


def _raw_result(accession: str, filing_type: str, filing_date: str) -> dict[str, str]:
    return {
        "accession_number": accession,
        "filing_type": filing_type,
        "filing_date": filing_date,
        "url": f"https://www.sec.gov/Archives/edgar/data/1/{accession.replace('-', '')}/index.htm",
    }


def test_build_raw_discovery_manifest_collects_candidates():
    seed = _seed()
    search_results = {
        "PREM14A": [_raw_result("0001047469-15-004456", "PREM14A", "2015-05-06")],
        "DEFM14A": [_raw_result("0001047469-15-004989", "DEFM14A", "2015-05-26")],
        "DEFA14A": [_raw_result("0001104659-15-028402", "DEFA14A", "2015-04-08")],
    }

    def search_fn(filing_type: str) -> list[dict[str, str]]:
        return search_results.get(filing_type, [])

    manifest = build_raw_discovery_manifest(
        seed,
        run_id="run-raw-1",
        cik="1408287",
        primary_filing_types=("PREM14A", "DEFM14A"),
        supplementary_filing_types=("DEFA14A",),
        search_fn=search_fn,
        top_k_per_form=2,
    )

    assert [candidate.accession_number for candidate in manifest.primary_candidates] == [
        "0001047469-15-004456",
        "0001047469-15-004989",
    ]
    assert [candidate.accession_number for candidate in manifest.supplementary_candidates] == [
        "0001104659-15-028402"
    ]


def test_write_immutable_text_allows_idempotent_writes_only(tmp_path: Path):
    path = tmp_path / "raw" / "zep" / "filings" / "0001047469-15-004456.txt"

    write_immutable_text(path, "first version")
    write_immutable_text(path, "first version")

    with pytest.raises(FileExistsError):
        write_immutable_text(path, "different version")


def test_freeze_raw_filing_writes_under_raw_slug(tmp_path: Path):
    candidate = FilingCandidate(
        document_id="0001047469-15-004456",
        accession_number="0001047469-15-004456",
        filing_type="PREM14A",
        filing_date=date(2015, 5, 6),
        sec_url="https://www.sec.gov/Archives/edgar/data/1408287/000104746915004456/index.htm",
        source_origin="seed_accession",
    )

    frozen = freeze_raw_filing(
        candidate,
        deal_slug="zep",
        raw_dir=tmp_path / "raw",
        html_text="<html>zep</html>",
        txt_text="zep raw filing",
    )

    assert frozen.txt_path == "raw/zep/filings/0001047469-15-004456.txt"
    assert frozen.html_path == "raw/zep/filings/0001047469-15-004456.html"
    assert (tmp_path / frozen.txt_path).read_text(encoding="utf-8") == "zep raw filing"
