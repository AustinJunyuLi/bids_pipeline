from __future__ import annotations

from pipeline.models.source import EvidenceType
from pipeline.source.evidence import group_evidence_by_type, scan_document_evidence
from pipeline.source.supplementary import evidence_items_to_snippets


def test_scan_document_evidence_detects_key_evidence_types():
    lines = [
        "On March 9, 2016, Party A submitted a non-binding indication of interest of $25.00 to $27.00 per share.",
        "",
        "The Special Committee and its financial advisor discussed the draft merger agreement and due diligence process.",
        "",
        "The merger agreement was executed on March 30, 2016.",
    ]

    evidence = scan_document_evidence(lines, document_id="doc-1", filing_type="DEFM14A")
    evidence_types = {item.evidence_type for item in evidence}

    assert EvidenceType.DATED_ACTION in evidence_types
    assert EvidenceType.FINANCIAL_TERM in evidence_types
    assert EvidenceType.ACTOR_IDENTIFICATION in evidence_types
    assert EvidenceType.PROCESS_SIGNAL in evidence_types
    assert EvidenceType.OUTCOME_FACT in evidence_types

    grouped = group_evidence_by_type(evidence)
    assert grouped[EvidenceType.FINANCIAL_TERM][0].value_hint == "$25.00 to $27.00 per share"


def test_evidence_items_to_snippets_derives_press_release_and_activist_hints():
    lines = [
        "The company issued a press release regarding strategic alternatives.",
        "",
        "A shareholder later pushed for a strategic review.",
        "",
        "The board announced the merger agreement in another press release.",
    ]

    evidence = scan_document_evidence(lines, document_id="doc-2", filing_type="8-K")
    snippets = evidence_items_to_snippets(evidence)

    assert {snippet.event_hint for snippet in snippets} >= {
        "sale_press_release",
        "activist_sale",
        "bid_press_release",
    }
