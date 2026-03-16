from datetime import UTC, date, datetime

from pipeline.config import EXAMPLE_DIR, RAW_DIR
from pipeline.models.common import SCHEMA_VERSION
from pipeline.models.raw import RawDiscoveryManifest, RawDocumentRegistry
from pipeline.models.source import FilingCandidate, FrozenDocument, SeedDeal


def _seed() -> SeedDeal:
    return SeedDeal(
        schema_version=SCHEMA_VERSION,
        artifact_type="seed_deal",
        created_at=datetime(2026, 3, 16, tzinfo=UTC),
        pipeline_version="0.1.0",
        run_id="run-1",
        deal_slug="imprivata",
        target_name="Imprivata, Inc.",
        acquirer_seed="Thoma Bravo",
        date_announced_seed=date(2016, 7, 11),
        primary_url_seed="https://www.sec.gov/Archives/edgar/data/1328015/000119312516677939/index.htm",
        is_reference=True,
        seed_row_refs=["csv:280"],
    )


def test_config_exposes_raw_and_example_directories():
    assert RAW_DIR.name == "raw"
    assert EXAMPLE_DIR.name == "example"
    assert RAW_DIR.parent == EXAMPLE_DIR.parent


def test_raw_discovery_manifest_round_trip():
    manifest = RawDiscoveryManifest(
        schema_version=SCHEMA_VERSION,
        artifact_type="raw_discovery_manifest",
        created_at=datetime(2026, 3, 16, tzinfo=UTC),
        pipeline_version="0.1.0",
        run_id="run-1",
        deal_slug="imprivata",
        seed=_seed(),
        cik="1328015",
        primary_candidates=[
            FilingCandidate(
                document_id="0001193125-16-677939",
                accession_number="0001193125-16-677939",
                filing_type="DEFM14A",
                filing_date=date(2016, 7, 11),
                sec_url="https://www.sec.gov/Archives/edgar/data/1328015/000119312516677939/index.htm",
                source_origin="seed_accession",
                ranking_features={"seed_accession_match": True},
            )
        ],
        supplementary_candidates=[],
        fetch_scope="all_candidates",
    )

    restored = RawDiscoveryManifest.model_validate_json(manifest.model_dump_json())

    assert restored.seed.deal_slug == "imprivata"
    assert restored.fetch_scope == "all_candidates"
    assert restored.primary_candidates[0].accession_number == "0001193125-16-677939"


def test_raw_document_registry_round_trip():
    registry = RawDocumentRegistry(
        schema_version=SCHEMA_VERSION,
        artifact_type="raw_document_registry",
        created_at=datetime(2026, 3, 16, tzinfo=UTC),
        pipeline_version="0.1.0",
        run_id="run-1",
        deal_slug="imprivata",
        documents=[
            FrozenDocument(
                document_id="0001193125-16-677939",
                accession_number="0001193125-16-677939",
                filing_type="DEFM14A",
                filing_date=date(2016, 7, 11),
                html_path="raw/imprivata/filings/0001193125-16-677939.html",
                txt_path="raw/imprivata/filings/0001193125-16-677939.txt",
                md_path=None,
                sha256_txt="deadbeef",
                sha256_html="beadfeed",
                byte_count_txt=123,
                fetched_at=datetime(2026, 3, 16, tzinfo=UTC),
            )
        ],
    )

    restored = RawDocumentRegistry.model_validate_json(registry.model_dump_json())

    assert restored.documents[0].txt_path.endswith(".txt")
    assert restored.documents[0].html_path.endswith(".html")
