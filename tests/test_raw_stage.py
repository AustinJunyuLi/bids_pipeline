import json
from datetime import UTC, date, datetime
from pathlib import Path

from pipeline.models.common import SCHEMA_VERSION
from pipeline.models.source import SeedDeal
from pipeline.raw.stage import fetch_raw_deal


def _seed() -> SeedDeal:
    return SeedDeal(
        schema_version=SCHEMA_VERSION,
        artifact_type="seed_deal",
        created_at=datetime(2026, 3, 16, tzinfo=UTC),
        pipeline_version="0.1.0",
        run_id="run-1",
        deal_slug="sample-deal",
        target_name="Sample Target",
        acquirer_seed="Sample Buyer",
        date_announced_seed=date(2016, 7, 11),
        primary_url_seed="https://www.sec.gov/Archives/edgar/data/1234567/000000000016000001/index.htm",
        is_reference=False,
        seed_row_refs=[],
    )


def test_fetch_raw_deal_writes_archive_contract(tmp_path: Path):
    seed = _seed()
    raw_dir = tmp_path / "raw"
    search_results = {
        "DEFM14A": [
            {
                "accession_number": "0000000000-16-000001",
                "filing_type": "DEFM14A",
                "filing_date": "2016-07-11",
                "url": "https://example.test/defm14a",
            }
        ],
        "8-K": [
            {
                "accession_number": "0000000000-16-000002",
                "filing_type": "8-K",
                "filing_date": "2016-07-10",
                "url": "https://example.test/8k",
            }
        ],
    }

    def search_fn(filing_type: str) -> list[dict[str, str]]:
        return search_results.get(filing_type, [])

    def fetch_contents_fn(accession_number: str, *, sec_url: str | None = None) -> tuple[str | None, str]:
        return f"<html>{accession_number}</html>", f"text for {accession_number} from {sec_url}"

    summary = fetch_raw_deal(
        seed,
        run_id="run-raw",
        raw_dir=raw_dir,
        primary_filing_types=("DEFM14A",),
        supplementary_filing_types=("8-K",),
        search_fn=search_fn,
        fetch_contents_fn=fetch_contents_fn,
    )

    raw_deal_dir = raw_dir / seed.deal_slug
    discovery = json.loads((raw_deal_dir / "discovery.json").read_text(encoding="utf-8"))
    registry = json.loads((raw_deal_dir / "document_registry.json").read_text(encoding="utf-8"))

    assert summary["deal_slug"] == "sample-deal"
    assert summary["frozen_count"] == 2
    assert discovery["primary_candidates"][0]["accession_number"] == "0000000000-16-000001"
    assert registry["documents"][0]["txt_path"].startswith("raw/sample-deal/filings/")
    assert (raw_deal_dir / "filings" / "0000000000-16-000001.txt").exists()
