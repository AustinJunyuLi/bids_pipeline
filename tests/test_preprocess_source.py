import json
from datetime import UTC, date, datetime
from pathlib import Path

from pipeline.models.common import SCHEMA_VERSION
from pipeline.models.raw import RawDiscoveryManifest, RawDocumentRegistry
from pipeline.models.source import FilingCandidate, FrozenDocument, SeedDeal
from pipeline.preprocess.source import preprocess_source_deal


def _seed(slug: str) -> SeedDeal:
    return SeedDeal(
        schema_version=SCHEMA_VERSION,
        artifact_type="seed_deal",
        created_at=datetime(2026, 3, 16, tzinfo=UTC),
        pipeline_version="0.1.0",
        run_id="run-1",
        deal_slug=slug,
        target_name="Sample Target",
        acquirer_seed="Sample Buyer",
        date_announced_seed=date(2016, 7, 11),
        primary_url_seed=None,
        is_reference=False,
        seed_row_refs=[],
    )


def test_preprocess_source_consumes_raw_archive_and_writes_derived_outputs(tmp_path: Path):
    raw_dir = tmp_path / "raw"
    deals_dir = tmp_path / "data" / "deals"
    slug = "sample-deal"
    seed = _seed(slug)

    primary_candidate = FilingCandidate(
        document_id="0000000000-16-000001",
        accession_number="0000000000-16-000001",
        filing_type="DEFM14A",
        filing_date=date(2016, 7, 11),
        sec_url="https://example.test/primary",
        source_origin="manual_override",
        ranking_features={"seed_accession_match": True, "form_preference": 0},
    )
    supplementary_candidate = FilingCandidate(
        document_id="0000000000-16-000002",
        accession_number="0000000000-16-000002",
        filing_type="8-K",
        filing_date=date(2016, 7, 10),
        sec_url="https://example.test/supplementary",
        source_origin="manual_override",
        ranking_features={"seed_accession_match": False, "form_preference": 1},
    )

    discovery = RawDiscoveryManifest(
        run_id="run-local",
        deal_slug=slug,
        seed=seed,
        cik="1234567",
        primary_candidates=[primary_candidate],
        supplementary_candidates=[supplementary_candidate],
    )
    registry = RawDocumentRegistry(
        run_id="run-local",
        deal_slug=slug,
        documents=[
            FrozenDocument(
                document_id=primary_candidate.document_id,
                accession_number=primary_candidate.accession_number,
                filing_type=primary_candidate.filing_type,
                filing_date=primary_candidate.filing_date,
                html_path=None,
                txt_path=f"raw/{slug}/filings/{primary_candidate.document_id}.txt",
                md_path=None,
                sha256_txt="abc",
                sha256_html=None,
                byte_count_txt=10,
                fetched_at=datetime(2026, 3, 16, tzinfo=UTC),
            ),
            FrozenDocument(
                document_id=supplementary_candidate.document_id,
                accession_number=supplementary_candidate.accession_number,
                filing_type=supplementary_candidate.filing_type,
                filing_date=supplementary_candidate.filing_date,
                html_path=None,
                txt_path=f"raw/{slug}/filings/{supplementary_candidate.document_id}.txt",
                md_path=None,
                sha256_txt="def",
                sha256_html=None,
                byte_count_txt=20,
                fetched_at=datetime(2026, 3, 16, tzinfo=UTC),
            ),
        ],
    )

    raw_deal_dir = raw_dir / slug
    raw_deal_dir.mkdir(parents=True)
    (raw_deal_dir / "discovery.json").write_text(discovery.model_dump_json(indent=2), encoding="utf-8")
    (raw_deal_dir / "document_registry.json").write_text(
        registry.model_dump_json(indent=2),
        encoding="utf-8",
    )
    filings_dir = raw_deal_dir / "filings"
    filings_dir.mkdir()
    (filings_dir / f"{primary_candidate.document_id}.txt").write_text(
        "\n".join(
            [
                "BACKGROUND OF THE MERGER",
                "",
                "On July 1, 2016, the board met to discuss a merger proposal.",
                "On July 5, 2016, the company received a revised offer.",
                "",
                "On July 7, 2016, management met with the buyer and its advisors.",
                "On July 9, 2016, the board authorized continued negotiations.",
                "",
                "On July 10, 2016, the company and the buyer exchanged drafts of the merger agreement.",
                "",
                "OPINION OF FINANCIAL ADVISOR",
            ]
        ),
        encoding="utf-8",
    )
    (filings_dir / f"{supplementary_candidate.document_id}.txt").write_text(
        "The company issued a press release regarding strategic alternatives.",
        encoding="utf-8",
    )

    result = preprocess_source_deal(
        slug,
        run_id="run-local",
        raw_dir=raw_dir,
        deals_dir=deals_dir,
    )

    source_dir = deals_dir / slug / "source"
    selection = json.loads((source_dir / "chronology_selection.json").read_text(encoding="utf-8"))
    blocks = [json.loads(line) for line in (source_dir / "chronology_blocks.jsonl").read_text(encoding="utf-8").splitlines()]
    snippets = [
        json.loads(line)
        for line in (source_dir / "supplementary_snippets.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    evidence_items = [
        json.loads(line)
        for line in (source_dir / "evidence_items.jsonl").read_text(encoding="utf-8").splitlines()
    ]

    assert result["selected_document_id"] == "0000000000-16-000001"
    assert selection["document_id"] == "0000000000-16-000001"
    assert blocks[0]["is_heading"] is True
    assert snippets[0]["document_id"] == "0000000000-16-000002"
    assert len(evidence_items) >= 2
    assert (source_dir / "filings" / "0000000000-16-000001.txt").exists()
    assert (source_dir / "filings" / "0000000000-16-000002.txt").exists()
