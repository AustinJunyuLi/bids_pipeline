from __future__ import annotations

from pipeline.models.common import QuoteMatchType
from pipeline.models.extraction import SourceSpan
from pipeline.models.source import ChronologyBlock
from pipeline.normalize.quotes import (
    find_anchor_in_segment,
    normalize_for_matching,
    reconstruct_quote_text,
)


def resolve_anchor_span(
    blocks: list[ChronologyBlock],
    raw_lines: list[str],
    *,
    block_id: str,
    anchor_text: str,
    document_id: str,
    accession_number: str | None,
    filing_type: str,
    span_id: str,
) -> SourceSpan:
    block = next(block for block in blocks if block.block_id == block_id)
    block_lines = raw_lines[block.start_line - 1 : block.end_line]
    raw_segment = "\n".join(block_lines)
    match_type, start_idx, end_idx = find_anchor_in_segment(raw_segment, anchor_text)

    if match_type == QuoteMatchType.UNRESOLVED or start_idx is None or end_idx is None:
        quote_text = reconstruct_quote_text(block_lines)
        return SourceSpan(
            span_id=span_id,
            document_id=document_id,
            accession_number=accession_number,
            filing_type=filing_type,
            start_line=block.start_line,
            end_line=block.end_line,
            start_char=None,
            end_char=None,
            block_ids=[block_id],
            anchor_text=anchor_text,
            quote_text=quote_text,
            quote_text_normalized=normalize_for_matching(quote_text),
            match_type=QuoteMatchType.UNRESOLVED,
            resolution_note=f"Anchor text was not found in block {block_id}.",
        )

    start_line, start_char = _segment_offset_to_line_position(block_lines, block.start_line, start_idx)
    end_line, end_char_inclusive = _segment_offset_to_line_position(
        block_lines,
        block.start_line,
        end_idx - 1,
    )
    selected_lines = raw_lines[start_line - 1 : end_line]
    quote_text = reconstruct_quote_text(selected_lines)
    return SourceSpan(
        span_id=span_id,
        document_id=document_id,
        accession_number=accession_number,
        filing_type=filing_type,
        start_line=start_line,
        end_line=end_line,
        start_char=start_char,
        end_char=end_char_inclusive + 1,
        block_ids=[block_id],
        anchor_text=anchor_text,
        quote_text=quote_text,
        quote_text_normalized=normalize_for_matching(quote_text),
        match_type=match_type,
        resolution_note=None,
    )


def _segment_offset_to_line_position(
    block_lines: list[str],
    base_line_number: int,
    char_offset: int,
) -> tuple[int, int]:
    running = 0
    for offset, line in enumerate(block_lines):
        line_length = len(line)
        if char_offset < running + line_length:
            return base_line_number + offset, char_offset - running
        running += line_length
        if offset < len(block_lines) - 1:
            if char_offset == running:
                return base_line_number + offset, line_length
            running += 1
    return base_line_number + len(block_lines) - 1, len(block_lines[-1])
