from pipeline.schemas import ChronologyBookmark, FilingManifest, FilingRecord


def test_filing_record_supports_selected_document_metadata():
    record = FilingRecord(
        filing_type="DEFM14A",
        accession_number="0001193125-16-677939",
        filing_date="2016-07-11",
        url="https://www.sec.gov/Archives/edgar/data/1285550/000119312516677939/d208987ddefm14a.htm",
        disposition="selected",
        html_path="source/filings/0001193125-16-677939.html",
        txt_path="source/filings/0001193125-16-677939.txt",
    )

    assert record.disposition == "selected"
    assert record.txt_path.endswith(".txt")


def test_filing_manifest_embeds_records():
    manifest = FilingManifest(
        deal_slug="imprivata",
        cik="1285550",
        target_name="Imprivata, Inc.",
        filings=[
            FilingRecord(
                filing_type="DEFM14A",
                accession_number="0001193125-16-677939",
                filing_date="2016-07-11",
                url=None,
                disposition="found",
            )
        ],
    )

    assert manifest.deal_slug == "imprivata"
    assert manifest.filings[0].filing_type == "DEFM14A"


def test_chronology_bookmark_supports_audit_metadata():
    bookmark = ChronologyBookmark(
        accession_number="0001193125-16-677939",
        heading="Background of the Merger",
        start_line=1148,
        end_line=2376,
        confidence="high",
        selection_basis="Selected the standalone heading over TOC and cross-reference matches.",
    )
    assert bookmark.confidence == "high"
    assert (
        bookmark.selection_basis
        == "Selected the standalone heading over TOC and cross-reference matches."
    )
