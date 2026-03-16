import json
from pathlib import Path

from pipeline.source.blocks import build_chronology_blocks
from pipeline.source.locate import select_chronology
from pipeline.source.supplementary import index_supplementary_snippets


DATA_DEALS = Path(__file__).resolve().parent.parent / "data" / "deals"
REFERENCE_DEALS = [
    "imprivata",
    "medivation",
    "zep",
    "petsmart-inc",
    "penford",
    "mac-gray",
    "saks",
    "providence-worcester",
    "stec",
]
ALTERNATE_FILINGS = {
    "mac-gray": "0001047469-13-010351",
    "medivation": "0001193125-16-696889",
    "zep": "0001047469-15-004989",
}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_selected_lines(deal_slug: str) -> tuple[list[str], dict]:
    bookmark = _load_json(DATA_DEALS / deal_slug / "source" / "chronology.json")
    accession = bookmark["accession_number"]
    txt_path = DATA_DEALS / deal_slug / "source" / "filings" / f"{accession}.txt"
    return txt_path.read_text(encoding="utf-8").splitlines(), bookmark


def test_reference_filings_localize_expected_chronology_section():
    for deal_slug in REFERENCE_DEALS:
        lines, bookmark = _load_selected_lines(deal_slug)
        selection = select_chronology(
            lines,
            document_id=bookmark["accession_number"],
            accession_number=bookmark["accession_number"],
            filing_type="UNKNOWN",
            run_id="test-run",
            deal_slug=deal_slug,
        )

        assert selection.selected_candidate is not None, deal_slug
        assert selection.selected_candidate.heading_text == bookmark["heading"], deal_slug
        assert selection.selected_candidate.start_line == bookmark["start_line"], deal_slug
        assert selection.selected_candidate.end_line == bookmark["end_line"], deal_slug
        assert selection.confidence == bookmark["confidence"], deal_slug


def test_alternate_reference_filings_still_produce_plausible_chronologies():
    for deal_slug, accession_number in ALTERNATE_FILINGS.items():
        txt_path = DATA_DEALS / deal_slug / "source" / "filings" / f"{accession_number}.txt"
        lines = txt_path.read_text(encoding="utf-8").splitlines()
        selection = select_chronology(
            lines,
            document_id=accession_number,
            accession_number=accession_number,
            filing_type="UNKNOWN",
            run_id="test-run",
            deal_slug=deal_slug,
        )

        if deal_slug == "medivation":
            assert selection.selected_candidate is None
            assert selection.confidence == "none"
            continue

        assert selection.selected_candidate is not None, deal_slug
        assert "Background" in selection.selected_candidate.heading_text, deal_slug
        assert selection.confidence in {"high", "medium", "low"}, deal_slug


def test_short_reference_confidences_are_review_aware():
    expectations = {
        "petsmart-inc": "low",
        "providence-worcester": "medium",
    }
    for deal_slug, confidence in expectations.items():
        lines, bookmark = _load_selected_lines(deal_slug)
        selection = select_chronology(
            lines,
            document_id=bookmark["accession_number"],
            accession_number=bookmark["accession_number"],
            filing_type="UNKNOWN",
            run_id="test-run",
            deal_slug=deal_slug,
        )

        assert selection.confidence == confidence
        assert selection.review_required is True


def test_block_builder_joins_wrapped_lines_and_preserves_spans():
    lines = [
        "BACKGROUND OF THE MERGER",
        "",
        "On January 15, 2015, the Board of Directors of the Company met to discuss",
        "strategic alternatives with Goldman Sachs.",
        "",
        "On February 1, 2015, Party A submitted an indication of interest.",
        "",
        "OPINION OF GOLDMAN SACHS & CO. LLC",
    ]
    selection = select_chronology(
        lines,
        document_id="doc-1",
        accession_number="0000000000-00-000001",
        filing_type="DEFM14A",
    )

    blocks = build_chronology_blocks(lines, selection=selection)

    assert [block.block_id for block in blocks] == ["B001", "B002", "B003"]
    assert blocks[0].is_heading is True
    assert blocks[1].start_line == 3
    assert blocks[1].end_line == 4
    assert "strategic alternatives with Goldman Sachs." in blocks[1].clean_text


def test_supplementary_indexer_labels_press_release_snippets():
    lines = [
        "The company issued a press release regarding strategic alternatives.",
        "A shareholder later pushed for a strategic review.",
        "The board announced the merger agreement in another press release.",
    ]

    snippets = index_supplementary_snippets(
        lines,
        document_id="doc-2",
        filing_type="8-K",
    )

    assert len(snippets) >= 2
    assert {snippet.event_hint for snippet in snippets} >= {
        "sale_press_release",
        "activist_sale",
    }
