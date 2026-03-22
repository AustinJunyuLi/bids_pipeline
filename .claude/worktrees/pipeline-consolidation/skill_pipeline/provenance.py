from __future__ import annotations

from skill_pipeline.models import SpanRecord
from skill_pipeline.normalize.quotes import (
    find_anchor_in_segment,
    normalize_for_matching,
    reconstruct_quote_text,
)
from skill_pipeline.pipeline_models.common import QuoteMatchType


SPAN_EXPANSION_LINES = 3


def resolve_text_span(
    raw_lines: list[str],
    *,
    start_line: int,
    end_line: int,
    block_ids: list[str],
    evidence_ids: list[str],
    anchor_text: str,
    document_id: str,
    accession_number: str | None,
    filing_type: str,
    span_id: str,
) -> SpanRecord:
    block_lines = raw_lines[start_line - 1 : end_line]
    raw_segment = "\n".join(block_lines)
    match_type, start_idx, end_idx = find_anchor_in_segment(raw_segment, anchor_text)

    window_start_line = start_line
    resolved_lines = block_lines
    if match_type == QuoteMatchType.UNRESOLVED:
        expanded_start_line = max(1, start_line - SPAN_EXPANSION_LINES)
        expanded_end_line = min(len(raw_lines), end_line + SPAN_EXPANSION_LINES)
        if expanded_start_line != start_line or expanded_end_line != end_line:
            expanded_lines = raw_lines[expanded_start_line - 1 : expanded_end_line]
            expanded_segment = "\n".join(expanded_lines)
            expanded_match_type, expanded_start_idx, expanded_end_idx = find_anchor_in_segment(
                expanded_segment,
                anchor_text,
            )
            if expanded_match_type != QuoteMatchType.UNRESOLVED:
                match_type = expanded_match_type
                start_idx = expanded_start_idx
                end_idx = expanded_end_idx
                window_start_line = expanded_start_line
                resolved_lines = expanded_lines

    if match_type == QuoteMatchType.UNRESOLVED or start_idx is None or end_idx is None:
        quote_text = reconstruct_quote_text(block_lines)
        return SpanRecord(
            span_id=span_id,
            document_id=document_id,
            accession_number=accession_number,
            filing_type=filing_type,
            start_line=start_line,
            end_line=end_line,
            start_char=None,
            end_char=None,
            block_ids=block_ids,
            evidence_ids=evidence_ids,
            anchor_text=anchor_text,
            quote_text=quote_text,
            quote_text_normalized=normalize_for_matching(quote_text),
            match_type=QuoteMatchType.UNRESOLVED,
            resolution_note=f"Anchor text was not found between lines {start_line}-{end_line}.",
        )

    resolved_start_line, start_char = _segment_offset_to_line_position(
        resolved_lines,
        window_start_line,
        start_idx,
    )
    resolved_end_line, end_char_inclusive = _segment_offset_to_line_position(
        resolved_lines,
        window_start_line,
        end_idx - 1,
    )
    selected_lines = raw_lines[resolved_start_line - 1 : resolved_end_line]
    quote_text = reconstruct_quote_text(selected_lines)
    return SpanRecord(
        span_id=span_id,
        document_id=document_id,
        accession_number=accession_number,
        filing_type=filing_type,
        start_line=resolved_start_line,
        end_line=resolved_end_line,
        start_char=start_char,
        end_char=end_char_inclusive + 1,
        block_ids=block_ids,
        evidence_ids=evidence_ids,
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
    return base_line_number + len(block_lines) - 1, len(block_lines[-1]) if block_lines else 0
