from __future__ import annotations

from collections import Counter

from pipeline.extract.utils import appendix_evidence_items, select_prompt_evidence_items
from pipeline.models.source import ChronologyBlock, EvidenceItem, EvidenceType
from pipeline.source.evidence import group_evidence_by_type, scan_document_evidence
from pipeline.source.supplementary import evidence_items_to_snippets


def _build_evidence_item(
    *,
    evidence_type: EvidenceType,
    confidence: str,
    evidence_id: str,
    document_id: str = "supplementary-doc",
    start_line: int = 1,
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        document_id=document_id,
        accession_number=None,
        filing_type="DEFM14A",
        start_line=start_line,
        end_line=start_line,
        raw_text=f"{evidence_type.value} evidence {evidence_id}",
        evidence_type=evidence_type,
        confidence=confidence,
        matched_terms=[evidence_type.value],
    )


def _build_starved_prompt_evidence() -> list[EvidenceItem]:
    evidence_items: list[EvidenceItem] = []
    for evidence_type in (
        EvidenceType.ACTOR_IDENTIFICATION,
        EvidenceType.DATED_ACTION,
        EvidenceType.FINANCIAL_TERM,
        EvidenceType.OUTCOME_FACT,
    ):
        evidence_items.extend(
            _build_evidence_item(
                evidence_type=evidence_type,
                confidence="high",
                evidence_id=f"{evidence_type.value}-{index}",
                start_line=index,
            )
            for index in range(10)
        )
    evidence_items.extend(
        _build_evidence_item(
            evidence_type=EvidenceType.PROCESS_SIGNAL,
            confidence="low",
            evidence_id=f"process-signal-{index}",
            start_line=index,
        )
        for index in range(3)
    )
    return evidence_items


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


def test_evidence_ids_are_globally_unique_across_filings():
    lines_a = ["", "On March 9, 2016, Thoma Bravo sent an indication of interest at $18.00 per share.", ""]
    lines_b = ["", "On July 12, 2016, Barclays Capital Inc. delivered its fairness opinion.", ""]

    items_a = scan_document_evidence(
        lines_a,
        document_id="filing-a",
        filing_type="DEFM14A",
        accession_number="0001-a",
    )
    items_b = scan_document_evidence(
        lines_b,
        document_id="filing-b",
        filing_type="PREM14A",
        accession_number="0001-b",
    )

    all_ids = [item.evidence_id for item in items_a + items_b]
    assert len(all_ids) == len(set(all_ids)), f"Duplicate evidence IDs: {all_ids}"
    for item in items_a:
        assert "0001-a" in item.evidence_id
    for item in items_b:
        assert "0001-b" in item.evidence_id


def test_process_signal_confidence_bonus_for_high_value_terms():
    lines = [
        "The parties signed a confidentiality agreement.",
    ]

    evidence = scan_document_evidence(lines, document_id="doc-3", filing_type="DEFM14A")
    process_items = [item for item in evidence if item.evidence_type == EvidenceType.PROCESS_SIGNAL]

    assert len(process_items) == 1
    assert process_items[0].matched_terms == ["confidentiality agreement"]
    assert process_items[0].confidence == "medium"


def test_scan_document_evidence_detects_additional_process_terms():
    lines = [
        "Bidders were asked in a written instruction letter to submit best and final offers before the final bid deadline.",
    ]

    evidence = scan_document_evidence(lines, document_id="doc-4", filing_type="DEFM14A")
    process_items = [item for item in evidence if item.evidence_type == EvidenceType.PROCESS_SIGNAL]

    assert len(process_items) == 1
    assert set(process_items[0].matched_terms) >= {
        "best and final",
        "bid deadline",
        "final bid",
        "instruction letter",
        "written instruction",
    }


def test_select_prompt_evidence_items_guarantees_process_signal():
    selected = select_prompt_evidence_items(_build_starved_prompt_evidence())

    counts = Counter(item.evidence_type for item in selected)
    assert len(selected) == 40
    assert counts[EvidenceType.PROCESS_SIGNAL] == 3


def test_select_prompt_evidence_items_min_per_type_zero_restores_old_behavior():
    selected = select_prompt_evidence_items(_build_starved_prompt_evidence(), min_per_type=0)

    counts = Counter(item.evidence_type for item in selected)
    assert len(selected) == 40
    assert counts[EvidenceType.PROCESS_SIGNAL] == 0


def test_select_prompt_evidence_items_preserves_priority_order_after_floor_selection():
    selected = select_prompt_evidence_items(_build_starved_prompt_evidence())

    assert [item.evidence_type for item in selected[:3]] == [
        EvidenceType.ACTOR_IDENTIFICATION,
        EvidenceType.ACTOR_IDENTIFICATION,
        EvidenceType.ACTOR_IDENTIFICATION,
    ]
    assert [item.evidence_type for item in selected[-3:]] == [
        EvidenceType.PROCESS_SIGNAL,
        EvidenceType.PROCESS_SIGNAL,
        EvidenceType.PROCESS_SIGNAL,
    ]


def test_nda_substring_does_not_create_false_process_signal():
    lines = [
        "Glass, Lewis & Co., LLC recommended that stockholders vote in favor of the Recommendation.",
    ]

    evidence = scan_document_evidence(lines, document_id="doc-5", filing_type="DEFM14A")
    process_items = [item for item in evidence if item.evidence_type == EvidenceType.PROCESS_SIGNAL]

    assert len(process_items) == 0


def test_non_disclosure_still_detects_process_signal():
    lines = [
        "Party A entered into a non-disclosure agreement with the Company.",
    ]

    evidence = scan_document_evidence(lines, document_id="doc-6", filing_type="DEFM14A")
    process_items = [item for item in evidence if item.evidence_type == EvidenceType.PROCESS_SIGNAL]

    assert len(process_items) == 1
    assert "non-disclosure" in process_items[0].matched_terms


def test_closed_substring_does_not_create_false_outcome_fact():
    lines = [
        "The Company disclosed certain information regarding the proposed transaction in its proxy statement.",
    ]

    evidence = scan_document_evidence(lines, document_id="doc-7", filing_type="DEFM14A")
    outcome_items = [item for item in evidence if item.evidence_type == EvidenceType.OUTCOME_FACT]

    assert len(outcome_items) == 0


def test_closing_still_detects_outcome_fact():
    lines = [
        "The closing of the transaction occurred on March 30, 2016.",
    ]

    evidence = scan_document_evidence(lines, document_id="doc-8", filing_type="DEFM14A")
    outcome_items = [item for item in evidence if item.evidence_type == EvidenceType.OUTCOME_FACT]

    assert len(outcome_items) == 1
    assert "closing" in outcome_items[0].matched_terms


def test_appendix_evidence_items_excludes_only_items_inside_chronology_span():
    chronology_blocks = [
        ChronologyBlock(
            block_id="B001",
            document_id="primary-doc",
            ordinal=1,
            start_line=10,
            end_line=20,
            raw_text="Primary chronology block.",
            clean_text="Primary chronology block.",
            is_heading=False,
        )
    ]
    evidence_items = [
        _build_evidence_item(
            evidence_type=EvidenceType.PROCESS_SIGNAL,
            confidence="medium",
            evidence_id="primary-inside",
            document_id="primary-doc",
            start_line=12,
        ),
        _build_evidence_item(
            evidence_type=EvidenceType.PROCESS_SIGNAL,
            confidence="medium",
            evidence_id="primary-outside",
            document_id="primary-doc",
            start_line=25,
        ),
        _build_evidence_item(
            evidence_type=EvidenceType.PROCESS_SIGNAL,
            confidence="medium",
            evidence_id="supp-item",
            document_id="supp-doc",
        ),
    ]

    filtered = appendix_evidence_items(evidence_items, chronology_blocks=chronology_blocks)

    assert [item.evidence_id for item in filtered] == ["primary-outside", "supp-item"]
