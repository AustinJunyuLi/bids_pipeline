"""Deterministic coverage audit over source evidence and extract artifacts."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.extract_artifacts import LoadedExtractArtifacts, load_extract_artifacts
from skill_pipeline.models import (
    CoverageCheckRecord,
    CoverageFindingsArtifact,
    CoverageSummary,
)
from skill_pipeline.paths import build_skill_paths, ensure_output_directories
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


def _load_chronology_blocks(path: Path) -> list[ChronologyBlock]:
    blocks: list[ChronologyBlock] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        blocks.append(ChronologyBlock.model_validate_json(line))
    return blocks


def _load_evidence_items(path: Path) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        items.append(EvidenceItem.model_validate_json(line))
    return items


def _build_coverage_cues(
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


def _normalize_coverage_text(text: str) -> str:
    return " ".join(text.lower().split())


def _has_non_sale_nda_marker(text: str) -> bool:
    normalized = _normalize_coverage_text(text)
    return any(marker in normalized for marker in NON_SALE_NDA_MARKERS)


def _classify_cue_family(item: EvidenceItem) -> str | None:
    text = item.raw_text.lower()
    text_compact = _normalize_coverage_text(item.raw_text)
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
    has_non_sale_nda_language = _has_non_sale_nda_marker(text_compact)
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
        # Some blocks mention a bidder's reluctance to proceed unless terms improve,
        # but then immediately state that negotiations continued. Those are not drops.
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


def _cue_is_covered(cue: CoverageCue, artifacts: LoadedExtractArtifacts) -> bool:
    if artifacts.mode == "quote_first":
        return _cue_is_covered_quote_first(cue, artifacts)
    return _cue_is_covered_canonical(cue, artifacts)


def _cue_is_covered_quote_first(cue: CoverageCue, artifacts: LoadedExtractArtifacts) -> bool:
    cue_block_ids = set(cue.block_ids)
    quote_index: dict[str, str] = {}
    for quote in artifacts.raw_actors.quotes:
        quote_index[quote.quote_id] = quote.block_id
    for quote in artifacts.raw_events.quotes:
        quote_index[quote.quote_id] = quote.block_id

    if cue.cue_family == "advisor":
        for actor in artifacts.raw_actors.actors:
            if actor.role != "advisor":
                continue
            if _quote_ids_overlap(cue_block_ids, actor.quote_ids, quote_index):
                return True

    for event in artifacts.raw_events.events:
        if cue.suggested_event_types and event.event_type not in cue.suggested_event_types:
            continue
        if _quote_ids_overlap(cue_block_ids, event.quote_ids, quote_index):
            return True
    return False


def _cue_is_covered_canonical(cue: CoverageCue, artifacts: LoadedExtractArtifacts) -> bool:
    span_index = artifacts.span_index
    if cue.cue_family == "advisor":
        for actor in artifacts.actors.actors:
            if actor.role != "advisor":
                continue
            if _span_ids_overlap(cue, actor.evidence_span_ids, span_index):
                return True

    for event in artifacts.events.events:
        if cue.suggested_event_types and event.event_type not in cue.suggested_event_types:
            continue
        if _span_ids_overlap(cue, event.evidence_span_ids, span_index):
            return True
    return False


def _quote_ids_overlap(
    cue_block_ids: set[str],
    quote_ids: list[str],
    quote_index: dict[str, str],
) -> bool:
    for quote_id in quote_ids:
        block_id = quote_index.get(quote_id)
        if block_id and block_id in cue_block_ids:
            return True
    return False


def _span_ids_overlap(cue: CoverageCue, span_ids: list[str], span_index: dict) -> bool:
    cue_block_ids = set(cue.block_ids)
    cue_evidence_ids = set(cue.evidence_ids)
    for span_id in span_ids:
        span = span_index.get(span_id)
        if span is None:
            continue
        if cue_evidence_ids and span.evidence_ids:
            if cue_evidence_ids.intersection(span.evidence_ids):
                return True
            continue
        if cue_block_ids.intersection(span.block_ids):
            return True
    return False


def _severity_for_cue(cue: CoverageCue) -> str | None:
    if cue.cue_family == "advisor":
        return "warning" if cue.confidence in {"high", "medium"} else None
    if cue.cue_family in CRITICAL_CUE_FAMILIES and cue.confidence == "high":
        return "error"
    if cue.confidence == "medium":
        return "warning"
    return None


def _build_findings(
    cues: list[CoverageCue],
    artifacts: LoadedExtractArtifacts,
) -> list[CoverageCheckRecord]:
    findings: list[CoverageCheckRecord] = []
    for cue in cues:
        if _cue_is_covered(cue, artifacts):
            continue
        severity = _severity_for_cue(cue)
        if severity is None:
            continue
        findings.append(
            CoverageCheckRecord(
                cue_family=cue.cue_family,
                status="not_found",
                severity=severity,
                repairability="repairable",
                description=f"{cue.confidence.capitalize()}-confidence {cue.cue_family} cue was not covered by extracted artifacts.",
                reason_code=f"uncovered_{cue.cue_family}_cue",
                block_ids=cue.block_ids,
                evidence_ids=cue.evidence_ids,
                matched_terms=cue.matched_terms,
                confidence=cue.confidence,
                suggested_event_types=cue.suggested_event_types,
            )
        )
    return findings


def _build_summary(findings: list[CoverageCheckRecord]) -> CoverageSummary:
    counter = Counter(finding.cue_family for finding in findings)
    error_count = sum(1 for finding in findings if finding.severity == "error")
    warning_count = sum(1 for finding in findings if finding.severity == "warning")
    return CoverageSummary(
        status="fail" if error_count > 0 else "pass",
        finding_count=len(findings),
        error_count=error_count,
        warning_count=warning_count,
        counts_by_cue_family=dict(counter),
    )


def run_coverage(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    paths = build_skill_paths(deal_slug, project_root=project_root)

    if not paths.actors_raw_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.actors_raw_path}")
    if not paths.events_raw_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.events_raw_path}")
    if not paths.chronology_blocks_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.chronology_blocks_path}")
    if not paths.evidence_items_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.evidence_items_path}")

    blocks = _load_chronology_blocks(paths.chronology_blocks_path)
    evidence_items = _load_evidence_items(paths.evidence_items_path)
    artifacts = load_extract_artifacts(paths)
    cues = _build_coverage_cues(evidence_items, blocks)
    findings = _build_findings(cues, artifacts)
    findings_artifact = CoverageFindingsArtifact(findings=findings)
    summary = _build_summary(findings)

    ensure_output_directories(paths)
    paths.coverage_findings_path.write_text(
        findings_artifact.model_dump_json(indent=2),
        encoding="utf-8",
    )
    paths.coverage_summary_path.write_text(
        summary.model_dump_json(indent=2),
        encoding="utf-8",
    )

    return 1 if summary.status == "fail" else 0
