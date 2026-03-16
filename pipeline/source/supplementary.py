from __future__ import annotations

from pipeline.models.source import SupplementarySnippet


KEYWORD_HINTS = {
    "sale_press_release": ("strategic alternatives", "sale process", "review of alternatives"),
    "bid_press_release": ("press release", "merger agreement", "announced"),
    "activist_sale": ("activist", "shareholder", "strategic review"),
}


def index_supplementary_snippets(
    lines: list[str],
    *,
    document_id: str,
    filing_type: str,
) -> list[SupplementarySnippet]:
    snippets: list[SupplementarySnippet] = []
    ordinal = 1
    for idx, line in enumerate(lines):
        lower = line.lower()
        for hint, keywords in KEYWORD_HINTS.items():
            hits = [keyword for keyword in keywords if keyword in lower]
            if not hits:
                continue
            start_line = max(1, idx)
            end_line = min(len(lines), idx + 3)
            raw_text = "\n".join(lines[start_line - 1 : end_line])
            snippets.append(
                SupplementarySnippet(
                    snippet_id=f"S{ordinal:03d}",
                    document_id=document_id,
                    filing_type=filing_type,
                    event_hint=hint,
                    start_line=start_line,
                    end_line=end_line,
                    raw_text=raw_text,
                    keyword_hits=hits,
                    confidence="medium" if len(hits) > 1 else "low",
                )
            )
            ordinal += 1
            break
    return snippets
