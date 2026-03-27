"""Unit tests for deterministic chronology block annotation helpers."""

from __future__ import annotations

from skill_pipeline.models import SeedEntry
from skill_pipeline.pipeline_models.common import DatePrecision
from skill_pipeline.pipeline_models.source import (
    ChronologyBlock,
    EvidenceItem,
    EvidenceType,
)
from skill_pipeline.source.annotate import (
    _assign_temporal_phase,
    _extract_date_mentions,
    _extract_entity_mentions,
    _overlapping_evidence,
    annotate_chronology_blocks,
)


def _seed(
    target_name: str = "IMPRIVATA INC",
    acquirer: str | None = "THOMA BRAVO LLC",
) -> SeedEntry:
    return SeedEntry(
        deal_slug="imprivata",
        target_name=target_name,
        acquirer=acquirer,
        date_announced="2016-07-13",
        primary_url="https://example.com",
        is_reference=False,
    )


def _block(
    block_id: str = "B001",
    ordinal: int = 1,
    start_line: int = 1,
    end_line: int = 1,
    clean_text: str = "placeholder",
) -> ChronologyBlock:
    return ChronologyBlock(
        block_id=block_id,
        document_id="DOC001",
        ordinal=ordinal,
        start_line=start_line,
        end_line=end_line,
        raw_text=clean_text,
        clean_text=clean_text,
        is_heading=False,
        date_mentions=[],
        entity_mentions=[],
        evidence_density=0,
        temporal_phase="other",
    )


def _evidence(
    evidence_type: EvidenceType = EvidenceType.DATED_ACTION,
    start_line: int = 1,
    end_line: int = 1,
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id="DOC001:E0001",
        document_id="DOC001",
        filing_type="DEFM14A",
        start_line=start_line,
        end_line=end_line,
        raw_text="placeholder",
        evidence_type=evidence_type,
        confidence="high",
    )


# ── Date extraction tests ──


def test_extract_exact_date_mention() -> None:
    mentions = _extract_date_mentions("On July 1, 2016, Party A signed an NDA.")
    assert len(mentions) == 1
    assert mentions[0].raw_text == "July 1, 2016"
    assert mentions[0].normalized == "2016-07-01"
    assert mentions[0].precision == DatePrecision.EXACT_DAY


def test_extract_multiple_date_mentions() -> None:
    text = "On July 1, 2016, Party A met with Party B. On July 5, 2016, they signed."
    mentions = _extract_date_mentions(text)
    assert len(mentions) == 2
    raw_texts = {m.raw_text for m in mentions}
    assert "July 1, 2016" in raw_texts
    assert "July 5, 2016" in raw_texts


def test_extract_month_only_date_mention() -> None:
    mentions = _extract_date_mentions("In June 2016, the Board retained advisors.")
    assert len(mentions) == 1
    assert mentions[0].raw_text == "June 2016"
    assert mentions[0].precision == DatePrecision.MONTH


def test_extract_no_dates() -> None:
    mentions = _extract_date_mentions("The Board met to discuss the transaction.")
    assert mentions == []


def test_deduplicates_repeated_date_fragments() -> None:
    text = "On July 1, 2016, Party A called. On July 1, 2016, Party B responded."
    mentions = _extract_date_mentions(text)
    assert len(mentions) == 1


# ── Entity extraction tests ──


def test_extract_target_entity() -> None:
    seed = _seed(target_name="IMPRIVATA INC")
    mentions = _extract_entity_mentions("IMPRIVATA INC retained Goldman Sachs.", seed)
    assert any(m.entity_type == "target" and m.raw_text == "IMPRIVATA INC" for m in mentions)


def test_extract_acquirer_entity() -> None:
    seed = _seed(acquirer="THOMA BRAVO LLC")
    mentions = _extract_entity_mentions("THOMA BRAVO LLC submitted a proposal.", seed)
    assert any(m.entity_type == "acquirer" and m.raw_text == "THOMA BRAVO LLC" for m in mentions)


def test_extract_party_alias() -> None:
    seed = _seed()
    mentions = _extract_entity_mentions("Party A signed a confidentiality agreement.", seed)
    assert any(m.entity_type == "party_alias" and m.raw_text == "Party A" for m in mentions)


def test_extract_company_and_board() -> None:
    seed = _seed()
    mentions = _extract_entity_mentions(
        "the Company retained advisors and the Board met to discuss.",
        seed,
    )
    types = {m.entity_type for m in mentions}
    assert "party_alias" in types


def test_extract_committee_mentions() -> None:
    seed = _seed()
    mentions = _extract_entity_mentions(
        "The Special Committee and Transaction Committee met.",
        seed,
    )
    assert any(m.entity_type == "committee" for m in mentions)
    assert len([m for m in mentions if m.entity_type == "committee"]) == 2


def test_no_entities_in_plain_text() -> None:
    seed = _seed()
    mentions = _extract_entity_mentions("The weather was nice.", seed)
    assert mentions == []


def test_entity_deduplication() -> None:
    seed = _seed()
    mentions = _extract_entity_mentions("Party A met Party A again.", seed)
    party_a_count = sum(1 for m in mentions if m.raw_text == "Party A")
    assert party_a_count == 1


# ── Evidence density tests ──


def test_overlapping_evidence_single_overlap() -> None:
    block = _block(start_line=5, end_line=10)
    items = [
        _evidence(start_line=7, end_line=8),
        _evidence(start_line=20, end_line=25),
    ]
    overlapping = _overlapping_evidence(block, items)
    assert len(overlapping) == 1


def test_overlapping_evidence_no_overlap() -> None:
    block = _block(start_line=5, end_line=10)
    items = [_evidence(start_line=11, end_line=15)]
    overlapping = _overlapping_evidence(block, items)
    assert len(overlapping) == 0


def test_overlapping_evidence_boundary_overlap() -> None:
    block = _block(start_line=5, end_line=10)
    items = [_evidence(start_line=10, end_line=15)]
    overlapping = _overlapping_evidence(block, items)
    assert len(overlapping) == 1


# ── Temporal phase tests ──


def test_phase_outcome_from_evidence() -> None:
    block = _block(ordinal=5)
    overlapping = [_evidence(evidence_type=EvidenceType.OUTCOME_FACT)]
    phase = _assign_temporal_phase(block, overlapping, 10)
    assert phase == "outcome"


def test_phase_bidding_from_evidence() -> None:
    block = _block(ordinal=5)
    overlapping = [_evidence(evidence_type=EvidenceType.DATED_ACTION)]
    phase = _assign_temporal_phase(block, overlapping, 10)
    assert phase == "bidding"


def test_phase_initiation_from_evidence() -> None:
    block = _block(ordinal=5)
    overlapping = [_evidence(evidence_type=EvidenceType.ACTOR_IDENTIFICATION)]
    phase = _assign_temporal_phase(block, overlapping, 10)
    assert phase == "initiation"


def test_phase_ordinal_fallback_early() -> None:
    block = _block(ordinal=1)
    phase = _assign_temporal_phase(block, [], 10)
    assert phase == "initiation"


def test_phase_ordinal_fallback_late() -> None:
    block = _block(ordinal=10)
    phase = _assign_temporal_phase(block, [], 10)
    assert phase == "outcome"


def test_phase_ordinal_fallback_middle() -> None:
    block = _block(ordinal=5)
    phase = _assign_temporal_phase(block, [], 10)
    assert phase == "other"


def test_outcome_overrides_bidding() -> None:
    block = _block(ordinal=5)
    overlapping = [
        _evidence(evidence_type=EvidenceType.DATED_ACTION),
        _evidence(evidence_type=EvidenceType.OUTCOME_FACT),
    ]
    phase = _assign_temporal_phase(block, overlapping, 10)
    assert phase == "outcome"


# ── Integration: annotate_chronology_blocks ──


def test_annotate_chronology_blocks_end_to_end() -> None:
    seed = _seed()
    blocks = [
        _block(
            block_id="B001",
            ordinal=1,
            start_line=1,
            end_line=2,
            clean_text="On July 1, 2016, Party A signed a confidentiality agreement.",
        ),
    ]
    evidence = [
        EvidenceItem(
            evidence_id="DOC001:E0001",
            document_id="DOC001",
            filing_type="DEFM14A",
            start_line=1,
            end_line=2,
            raw_text="Party A signed a confidentiality agreement.",
            evidence_type=EvidenceType.PROCESS_SIGNAL,
            confidence="high",
            matched_terms=["confidentiality agreement"],
        ),
    ]
    annotated = annotate_chronology_blocks(blocks, evidence, seed)
    assert len(annotated) == 1
    b = annotated[0]
    assert b.block_id == "B001"
    assert len(b.date_mentions) == 1
    assert b.date_mentions[0].raw_text == "July 1, 2016"
    assert any(m.raw_text == "Party A" for m in b.entity_mentions)
    assert b.evidence_density == 1
    assert b.temporal_phase == "bidding"
