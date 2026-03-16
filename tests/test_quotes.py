import json
from pathlib import Path

from pipeline.models.common import QuoteMatchType
from pipeline.models.source import ChronologyBlock
from pipeline.normalize.spans import resolve_anchor_span
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
