"""Deterministic coverage audit over source evidence and extract artifacts."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.extract_artifacts import LoadedExtractArtifacts, load_extract_artifacts
from skill_pipeline.models import CoverageFinding, CoverageFindingsArtifact, CoverageSummary
from skill_pipeline.paths import build_skill_paths, ensure_output_directories
from skill_pipeline.pipeline_models.source import ChronologyBlock, EvidenceItem, EvidenceType


CRITICAL_CUE_FAMILIES = frozenset(
    {
        "proposal",
        "nda",
        "withdrawal_or_drop",
        "process_initiation",
    }
)

NDA_TERMS = (
    "confidentiality agreement",
    "non-disclosure",
    "nondisclosure",
    "standstill",
)
NDA_EXECUTION_TERMS = ("entered into", "executed", "signed", "addendum")
PROPOSAL_PRIMARY_TERMS = ("indication of interest", "offer", "bid", "submitted")
PROPOSAL_ACTION_TERMS = (
    "submitted",
    "received",
    "sent",
    "delivered",
    "requested",
    "verbally indicated",
    "written",
)
WITHDRAWAL_TERMS = (
    "declined",
    "dropped",
    "withdrew",
    "withdrawn",
    "did not submit",
    "no longer interested",
)
ADVISOR_TERMS = ("financial advisor", "legal advisor", "advisor", "adviser", "retained", "engaged")
ADVISOR_CONTEXT_TERMS = ("advisor", "advisors", "counsel", "financial advisor", "legal advisor", "law firm")
BIDDER_INTEREST_TERMS = (
    "expressed interest",
    "indicated interest",
    "approached",
    "contacted",
    "interested in acquiring",
)
PROCESS_INITIATION_TERMS = (
    "sale process",
    "strategic alternatives",
    "explore strategic alternatives",
)
EXCLUSION_CUE_FAMILIES: dict[str, frozenset[str] | None] = {
    "partial_company_bid": frozenset({"proposal", "bidder_interest"}),
    "unsigned_nda": frozenset({"nda"}),
    "stale_process_reference": frozenset({"process_initiation"}),
    "duplicate_mention": None,
    "non_event_context": None,
    "other": None,
}


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
        overlapping_block_ids = _block_ids_for_evidence(
            item,
            blocks_by_document.get(item.document_id, []),
        )
        # extract-deal only consumes evidence_items scoped to chronology chunks, so
        # coverage should audit the same chronology-overlapping surface.
        if not overlapping_block_ids:
            continue
        cue_family = _classify_cue_family(item)
        if cue_family is None or item.confidence == "low":
            continue
        cues.append(
            CoverageCue(
                cue_family=cue_family,
                block_ids=overlapping_block_ids,
                evidence_ids=[item.evidence_id],
                matched_terms=item.matched_terms,
                confidence=item.confidence,
                suggested_event_types=_suggested_event_types(cue_family),
            )
        )
    return cues


def _classify_cue_family(item: EvidenceItem) -> str | None:
    text = f"{item.raw_text} {' '.join(item.matched_terms)}".lower()
    if _contains_any(text, NDA_TERMS):
        # Generic confidentiality language in proxy boilerplate is not an NDA event.
        if _contains_any(text, NDA_EXECUTION_TERMS):
            return "nda"
        return None

    if item.evidence_type in {EvidenceType.DATED_ACTION, EvidenceType.FINANCIAL_TERM}:
        if _contains_any(text, PROPOSAL_PRIMARY_TERMS):
            return "proposal"
        if "proposal" in text and (
            item.actor_hint
            or item.value_hint
            or _contains_any(text, PROPOSAL_ACTION_TERMS)
        ):
            return "proposal"

    if item.evidence_type == EvidenceType.DATED_ACTION and _contains_any(text, WITHDRAWAL_TERMS):
        if not _contains_any(text, ADVISOR_CONTEXT_TERMS):
            return "withdrawal_or_drop"

    if _contains_any(text, ADVISOR_TERMS):
        return "advisor"
    if _contains_any(text, BIDDER_INTEREST_TERMS):
        return "bidder_interest"
    if _contains_any(text, PROCESS_INITIATION_TERMS):
        return "process_initiation"
    return None


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


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
    if artifacts.mode == "legacy":
        return _cue_is_covered_legacy(cue, artifacts)
    return _cue_is_covered_canonical(cue, artifacts)


def _cue_is_excluded(cue: CoverageCue, artifacts: LoadedExtractArtifacts) -> bool:
    cue_block_ids = set(cue.block_ids)
    if not cue_block_ids:
        return False

    if artifacts.mode == "legacy" and artifacts.raw_events is not None:
        exclusions = artifacts.raw_events.exclusions
    elif artifacts.events is not None:
        exclusions = artifacts.events.exclusions
    else:
        exclusions = []

    for exclusion in exclusions:
        allowed_families = EXCLUSION_CUE_FAMILIES.get(exclusion.category)
        if allowed_families is not None and cue.cue_family not in allowed_families:
            continue
        if cue_block_ids.intersection(exclusion.block_ids):
            return True
    return False


def _cue_is_covered_legacy(cue: CoverageCue, artifacts: LoadedExtractArtifacts) -> bool:
    if cue.cue_family == "advisor":
        for actor in artifacts.raw_actors.actors:
            if actor.role != "advisor":
                continue
            if _refs_overlap(cue, actor.evidence_refs):
                return True

    for event in artifacts.raw_events.events:
        if cue.suggested_event_types and event.event_type not in cue.suggested_event_types:
            continue
        if _refs_overlap(cue, event.evidence_refs):
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


def _refs_overlap(cue: CoverageCue, refs: list) -> bool:
    cue_block_ids = set(cue.block_ids)
    cue_evidence_ids = set(cue.evidence_ids)
    for ref in refs:
        if cue_evidence_ids and ref.evidence_id:
            if ref.evidence_id in cue_evidence_ids:
                return True
            continue
        if ref.block_id and ref.block_id in cue_block_ids:
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
    if cue.cue_family == "bidder_interest" and cue.confidence == "high":
        return "warning"
    if cue.cue_family in CRITICAL_CUE_FAMILIES and cue.confidence == "high":
        return "error"
    if cue.confidence == "medium":
        return "warning"
    return None


def _build_findings(cues: list[CoverageCue], artifacts: LoadedExtractArtifacts) -> list[CoverageFinding]:
    findings: list[CoverageFinding] = []
    for cue in cues:
        if _cue_is_excluded(cue, artifacts):
            continue
        if _cue_is_covered(cue, artifacts):
            continue
        severity = _severity_for_cue(cue)
        if severity is None:
            continue
        findings.append(
            CoverageFinding(
                cue_family=cue.cue_family,
                severity=severity,
                repairability="repairable",
                description=f"{cue.confidence.capitalize()}-confidence {cue.cue_family} cue was not covered by extracted artifacts.",
                block_ids=cue.block_ids,
                evidence_ids=cue.evidence_ids,
                matched_terms=cue.matched_terms,
                confidence=cue.confidence,
                suggested_event_types=cue.suggested_event_types,
            )
        )
    return findings


def _build_summary(findings: list[CoverageFinding]) -> CoverageSummary:
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
