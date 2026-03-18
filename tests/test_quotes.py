import json
from pathlib import Path

from pipeline.models.common import QuoteMatchType
from pipeline.models.source import ChronologyBlock
from pipeline.normalize.quotes import find_anchor_in_segment
from pipeline.normalize.spans import resolve_anchor_span, resolve_text_span
from pipeline.source.blocks import build_chronology_blocks
from pipeline.source.locate import select_chronology


RAW_DIR = Path(__file__).resolve().parent.parent / "raw"
DATA_DEALS = Path(__file__).resolve().parent.parent / "data" / "deals"


def test_exact_quote_match_resolves_single_line_span():
    lines = [
        "BACKGROUND OF THE MERGER",
        "",
        "On March 9, 2016, Thoma Bravo sent an unsolicited, non-binding indication of interest letter.",
        "",
        "OPINION OF FINANCIAL ADVISOR",
    ]
    blocks = [
        ChronologyBlock(
            block_id="B002",
            document_id="doc-1",
            ordinal=2,
            start_line=3,
            end_line=3,
            raw_text=lines[2],
            clean_text=lines[2],
            is_heading=False,
        )
    ]

    span = resolve_anchor_span(
        blocks,
        lines,
        block_id="B002",
        anchor_text="Thoma Bravo sent an unsolicited",
        document_id="doc-1",
        accession_number="0000000000-00-000001",
        filing_type="DEFM14A",
        span_id="span-1",
    )

    assert span.match_type == QuoteMatchType.EXACT
    assert span.start_line == 3
    assert span.end_line == 3
    assert span.quote_text == lines[2]


def test_normalized_quote_match_handles_curly_quotes_and_dashes():
    lines = [
        "BACKGROUND OF THE MERGER",
        "",
        "Party A’s “non-binding” indication—of interest remained under review.",
        "",
        "OTHER HEADING",
    ]
    blocks = [
        ChronologyBlock(
            block_id="B002",
            document_id="doc-2",
            ordinal=2,
            start_line=3,
            end_line=3,
            raw_text=lines[2],
            clean_text=lines[2],
            is_heading=False,
        )
    ]

    span = resolve_anchor_span(
        blocks,
        lines,
        block_id="B002",
        anchor_text='Party A\'s "non-binding" indication-of interest',
        document_id="doc-2",
        accession_number="0000000000-00-000002",
        filing_type="DEFM14A",
        span_id="span-2",
    )

    assert span.match_type == QuoteMatchType.NORMALIZED
    assert span.start_line == 3
    assert span.end_line == 3
    assert span.quote_text == lines[2]


def test_unresolved_quote_path_returns_unresolved_span():
    lines = [
        "BACKGROUND OF THE MERGER",
        "",
        "On March 9, 2016, Thoma Bravo sent an unsolicited, non-binding indication of interest letter.",
        "",
        "OPINION OF FINANCIAL ADVISOR",
    ]
    blocks = [
        ChronologyBlock(
            block_id="B002",
            document_id="doc-3",
            ordinal=2,
            start_line=3,
            end_line=3,
            raw_text=lines[2],
            clean_text=lines[2],
            is_heading=False,
        )
    ]

    span = resolve_anchor_span(
        blocks,
        lines,
        block_id="B002",
        anchor_text="anchor text that is not present",
        document_id="doc-3",
        accession_number="0000000000-00-000003",
        filing_type="DEFM14A",
        span_id="span-3",
    )

    assert span.match_type == QuoteMatchType.UNRESOLVED
    assert span.resolution_note is not None
    assert span.start_line == 3
    assert span.end_line == 3


def test_apostrophe_stripped_matching_returns_fuzzy():
    match_type, start, end = find_anchor_in_segment(
        "the Company\x92s financial advisor, Barclays Capital Inc.",
        "the Companys financial advisor, Barclays Capital Inc.",
    )

    assert match_type == QuoteMatchType.FUZZY
    assert start is not None
    assert end is not None


def test_inline_quote_stripped_matching_returns_fuzzy():
    match_type, start, end = find_anchor_in_segment(
        'Goodwin Procter LLP (\x93Goodwin\x94) were in attendance.',
        "Goodwin Procter LLP (Goodwin) were in attendance.",
    )

    assert match_type == QuoteMatchType.FUZZY
    assert start is not None
    assert end is not None


def test_parenthetical_inserted_matching_returns_fuzzy():
    match_type, start, end = find_anchor_in_segment(
        'On December 14, 2014, PetSmart, Inc. (the "Company") entered into an Agreement and Plan of Merger.',
        "On December 14, 2014, PetSmart, Inc. entered into an Agreement and Plan of Merger",
    )

    assert match_type == QuoteMatchType.FUZZY
    assert start is not None
    assert end is not None


def test_compact_alnum_matching_returns_fuzzy_for_spacing_artifacts():
    match_type, start, end = find_anchor_in_segment(
        "G& W submitted a revised LOI together withmark-upsof the merger agreement and the voting agreement.",
        "together with mark-ups of the merger agreement",
    )

    assert match_type == QuoteMatchType.FUZZY
    assert start is not None
    assert end is not None


def test_paraphrase_anchor_stays_unresolved():
    match_type, start, end = find_anchor_in_segment(
        "it did not believe that the Board would be interested in a transaction",
        "the Board would not be interested",
    )

    assert match_type == QuoteMatchType.UNRESOLVED
    assert start is None
    assert end is None


def test_resolve_text_span_expands_one_line_for_split_date_prefix():
    raw_lines = [
        "On",
        "March 13, 2015, New Mountain Capital communicated that the $20.05 per share offer price was best and final.",
    ]

    span = resolve_text_span(
        raw_lines,
        start_line=2,
        end_line=2,
        block_ids=["B001"],
        anchor_text="On March 13, 2015",
        document_id="doc-1",
        accession_number="0000000000-00-000004",
        filing_type="DEFM14A",
        span_id="span-4",
    )

    assert span.match_type == QuoteMatchType.NORMALIZED
    assert span.start_line == 1
    assert span.end_line == 2


def test_resolve_text_span_expands_three_lines_for_late_line_continuation():
    raw_lines = [
        "From April 1 through April 17, 2013, sTec negotiated non-disclosure agreements and scheduled management",
        "presentations with interested parties. On April 4, 2013, sTec entered into a non-disclosure agreement with Company E, on April 10, it entered into a non-disclosure agreement with Company D, on",
        "April 11, it entered into a non-disclosure agreement with Company F, another",
        "27",
        "participant in the storage industry, and on April 17, it entered into a non-disclosure agreement with Company G.",
    ]

    span = resolve_text_span(
        raw_lines,
        start_line=1,
        end_line=3,
        block_ids=["B001"],
        anchor_text="it entered into a non-disclosure agreement with Company G",
        document_id="doc-1",
        accession_number="0000000000-00-000005",
        filing_type="DEFM14A",
        span_id="span-5",
    )

    assert span.match_type == QuoteMatchType.EXACT
    assert span.start_line == 5
    assert span.end_line == 5


def test_real_focus_filing_block_generates_canonical_quote_span():
    bookmark = json.loads((DATA_DEALS / "petsmart-inc" / "source" / "chronology.json").read_text(encoding="utf-8"))
    accession = bookmark["accession_number"]
    lines = (RAW_DIR / "petsmart-inc" / "filings" / f"{accession}.txt").read_text(encoding="utf-8").splitlines()
    selection = select_chronology(
        lines,
        document_id=accession,
        accession_number=accession,
        filing_type="DEFM14A",
    )
    blocks = build_chronology_blocks(lines, selection=selection)
    target_block = next(
        block
        for block in blocks
        if "JANA Partners filed a Schedule 13D" in block.clean_text
    )

    span = resolve_anchor_span(
        blocks,
        lines,
        block_id=target_block.block_id,
        anchor_text="JANA Partners filed a Schedule 13D",
        document_id=accession,
        accession_number=accession,
        filing_type="DEFM14A",
        span_id="span-real-1",
    )

    assert span.match_type == QuoteMatchType.EXACT
    assert span.start_line == 1119
    assert span.end_line == 1119
    assert "JANA Partners filed a Schedule 13D" in span.quote_text
