"""Shared coverage-cue helpers for the live v2 coverage audit."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from skill_pipeline.pipeline_models.source import ChronologyBlock, EvidenceItem


CRITICAL_CUE_FAMILIES = frozenset(
    {
        "proposal",
        "nda",
        "withdrawal_or_drop",
        "process_initiation",
    }
)

NON_SALE_NDA_MARKERS = (
    "management rollover",
    "rollover equity",
    "rolled over",
    "continuing equity",
    "joint bid",
    "consortium",
    "teaming",
    "partnered with",
    "due diligence with respect to",
    "engage in due diligence with respect to",
)


@dataclass
class CoverageCue:
    cue_family: str
    block_ids: list[str]
    evidence_ids: list[str]
    matched_terms: list[str]
    confidence: str
    suggested_event_types: list[str]


def load_chronology_blocks(path: Path) -> list[ChronologyBlock]:
    blocks: list[ChronologyBlock] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        blocks.append(ChronologyBlock.model_validate_json(line))
    return blocks


def load_evidence_items(path: Path) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        items.append(EvidenceItem.model_validate_json(line))
    return items


def build_coverage_cues(
    evidence_items: list[EvidenceItem],
    blocks: list[ChronologyBlock],
) -> list[CoverageCue]:
    blocks_by_document: dict[str, list[ChronologyBlock]] = {}
    for block in blocks:
        blocks_by_document.setdefault(block.document_id, []).append(block)

    cues: list[CoverageCue] = []
    for item in evidence_items:
        cue_family = _classify_cue_family(item)
        if cue_family is None or item.confidence == "low":
            continue
        block_ids = _block_ids_for_evidence(item, blocks_by_document.get(item.document_id, []))
        if not block_ids:
            continue
        cues.append(
            CoverageCue(
                cue_family=cue_family,
                block_ids=block_ids,
                evidence_ids=[item.evidence_id],
                matched_terms=item.matched_terms,
                confidence=item.confidence,
                suggested_event_types=_suggested_event_types(cue_family),
            )
        )
    return cues


def normalize_coverage_text(text: str) -> str:
    return " ".join(text.lower().split())


def has_non_sale_nda_marker(text: str) -> bool:
    normalized = normalize_coverage_text(text)
    return any(marker in normalized for marker in NON_SALE_NDA_MARKERS)


def severity_for_cue(cue: CoverageCue) -> str | None:
    if cue.cue_family == "advisor":
        return "warning" if cue.confidence in {"high", "medium"} else None
    if cue.cue_family in CRITICAL_CUE_FAMILIES and cue.confidence == "high":
        return "error"
    if cue.confidence == "medium":
        return "warning"
    return None


def _classify_cue_family(item: EvidenceItem) -> str | None:
    text = item.raw_text.lower()
    text_compact = normalize_coverage_text(item.raw_text)
    evidence_type = item.evidence_type.value

    has_nda_language = any(
        token in text
        for token in (
            "non-disclosure agreement",
            "nondisclosure agreement",
            "confidentiality agreement",
            "confidentiality and standstill",
            "standstill agreement",
        )
    )
    has_executed_nda_language = any(
        phrase in text
        for phrase in (
            "entered into a non-disclosure agreement",
            "entered into an addendum to its existing non-disclosure agreement",
            "executed six non-disclosure agreements",
            "executed a non-disclosure agreement",
            "signed a non-disclosure agreement",
            "entered into a confidentiality agreement",
            "executed a confidentiality agreement",
            "signed a confidentiality agreement",
        )
    )
    references_prior_executed_nda = any(
        phrase in text or phrase in text_compact
        for phrase in (
            "which had executed a confidentiality agreement",
            "who had executed a confidentiality agreement",
            "that had executed a confidentiality agreement",
        )
    )
    has_non_sale_nda_language = has_non_sale_nda_marker(text_compact)
    has_proposal_language = any(
        phrase in text
        for phrase in (
            "submitted an indication of interest",
            "provided a verbal indication of its interest to pursue a transaction",
            "submitted a written indication of interest",
            "submitted a written non-binding indication of interest",
            "submitted a written second-round indication of interest",
            "submitted a revised written indication of interest",
            "submitted a written indication of interest of $",
        )
    )
    has_drop_language = any(
        token in text
        for token in (
            "would not continue in the process",
            "disengaging from the process",
            "not prepared to move forward",
            "reevaluating its interest",
            "withdrew",
            "withdrawn",
            "no longer interested",
        )
    )
    has_continue_negotiation_language = any(
        phrase in text
        for phrase in (
            "move forward with negotiations",
            "moved forward with negotiations",
            "continue negotiations",
            "continued negotiations",
        )
    )
    has_advisor_language = any(
        token in text
        for token in (
            "financial advisor",
            "legal advisor",
            "outside corporate counsel",
            "counsel to",
            "law firm",
            "engagement letter",
            "retaining ",
            "retained ",
        )
    )
    has_bidder_interest_language = any(
        token in text
        for token in (
            "express the interest of",
            "expressed an interest",
            "interest in exploring a potential acquisition",
            "request a preliminary meeting",
            "possible acquisition target",
            "interested in a potential transaction",
        )
    )
    has_process_initiation_language = any(
        phrase in text
        for phrase in (
            "exploring a potential sale",
            "possible sale of the company",
            "explore strategic alternatives",
            "confidentially approach strategic buyers",
        )
    )

    if evidence_type == "process_signal":
        if has_nda_language and has_executed_nda_language and not (
            references_prior_executed_nda or has_non_sale_nda_language
        ):
            return "nda"
        if has_process_initiation_language:
            return "process_initiation"
        return None

    if evidence_type == "dated_action":
        if has_nda_language and has_executed_nda_language and not (
            references_prior_executed_nda or has_non_sale_nda_language
        ):
            return "nda"
        if has_drop_language and not has_continue_negotiation_language:
            return "withdrawal_or_drop"
        if has_proposal_language:
            return "proposal"
        if has_bidder_interest_language:
            return "bidder_interest"
        if has_process_initiation_language:
            return "process_initiation"
        if has_advisor_language:
            return "advisor"
        return None

    if evidence_type == "actor_identification":
        if has_advisor_language:
            return "advisor"
        return None

    return None


def _suggested_event_types(cue_family: str) -> list[str]:
    return {
        "proposal": ["proposal"],
        "nda": ["nda"],
        "withdrawal_or_drop": ["drop"],
        "bidder_interest": ["bidder_interest", "bidder_sale"],
        "process_initiation": [
            "target_sale",
            "target_sale_public",
            "bidder_sale",
            "activist_sale",
            "sale_press_release",
            "bid_press_release",
        ],
        "advisor": ["ib_retention"],
    }.get(cue_family, [])


def _block_ids_for_evidence(item: EvidenceItem, blocks: list[ChronologyBlock]) -> list[str]:
    block_ids: list[str] = []
    for block in blocks:
        overlaps = not (block.end_line < item.start_line or block.start_line > item.end_line)
        if overlaps and block.block_id not in block_ids:
            block_ids.append(block.block_id)
    return block_ids
