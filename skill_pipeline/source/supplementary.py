from __future__ import annotations

from skill_pipeline.pipeline_models.source import EvidenceItem, EvidenceType, SupplementarySnippet
from skill_pipeline.source.evidence import scan_document_evidence


PRESS_TERMS = {"press release", "announced", "announcement"}
ACTIVIST_TERMS = {"activist", "shareholder", "stockholder", "jana", "gamco", "gabelli"}
SALE_TERMS = {"strategic alternatives", "sale process", "review of alternatives", "review of strategic alternatives"}


def index_supplementary_snippets(
    lines: list[str],
    *,
    document_id: str,
    filing_type: str,
    accession_number: str | None = None,
) -> list[SupplementarySnippet]:
    evidence_items = scan_document_evidence(
        lines,
        document_id=document_id,
        filing_type=filing_type,
        accession_number=accession_number,
    )
    snippets: list[SupplementarySnippet] = []
    ordinal = 1
    for item in evidence_items:
        event_hint = _hint_for_item(item)
        if event_hint is None:
            continue
        snippets.append(
            SupplementarySnippet(
                snippet_id=f"S{ordinal:03d}",
                document_id=item.document_id,
                filing_type=item.filing_type,
                event_hint=event_hint,
                start_line=item.start_line,
                end_line=item.end_line,
                raw_text=item.raw_text,
                keyword_hits=item.matched_terms,
                confidence=item.confidence,
                evidence_id=item.evidence_id,
            )
        )
        ordinal += 1
    return snippets


def evidence_items_to_snippets(items: list[EvidenceItem]) -> list[SupplementarySnippet]:
    snippets: list[SupplementarySnippet] = []
    ordinal = 1
    for item in items:
        event_hint = _hint_for_item(item)
        if event_hint is None:
            continue
        snippets.append(
            SupplementarySnippet(
                snippet_id=f"S{ordinal:03d}",
                document_id=item.document_id,
                filing_type=item.filing_type,
                event_hint=event_hint,
                start_line=item.start_line,
                end_line=item.end_line,
                raw_text=item.raw_text,
                keyword_hits=item.matched_terms,
                confidence=item.confidence,
                evidence_id=item.evidence_id,
            )
        )
        ordinal += 1
    return snippets


def _hint_for_item(item: EvidenceItem) -> str | None:
    lowered = item.raw_text.lower()
    if any(term in lowered for term in ACTIVIST_TERMS):
        return "activist_sale"
    if any(term in lowered for term in PRESS_TERMS) and any(term in lowered for term in SALE_TERMS):
        return "sale_press_release"
    if any(term in lowered for term in PRESS_TERMS) or (
        item.evidence_type == EvidenceType.OUTCOME_FACT and "merger agreement" in lowered
    ):
        return "bid_press_release"
    if item.evidence_type == EvidenceType.PROCESS_SIGNAL and any(term in lowered for term in SALE_TERMS):
        return "sale_press_release"
    if item.evidence_type in {EvidenceType.OUTCOME_FACT, EvidenceType.PROCESS_SIGNAL}:
        return "other"
    return None
