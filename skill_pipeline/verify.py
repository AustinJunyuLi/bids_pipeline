"""Strict deterministic verify for extracted skill artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from skill_pipeline.extract_artifacts import LoadedExtractArtifacts, load_extract_artifacts
from skill_pipeline.pipeline_models.common import QuoteMatchType
from skill_pipeline.pipeline_models.source import ChronologyBlock
from skill_pipeline.normalize.quotes import find_anchor_in_segment

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.models import (
    QuoteEntry,
    SkillPathSet,
    SkillVerificationLog,
    VerificationFinding,
    VerificationLogSummary,
    VerificationRound,
    VerificationRoundTwo,
)
from skill_pipeline.paths import build_skill_paths, ensure_output_directories

SPAN_EXPANSION_LINES = 3
STRICT_QUOTE_MATCH_TYPES = frozenset({QuoteMatchType.EXACT, QuoteMatchType.NORMALIZED})


def _load_document_lines(filings_dir: Path) -> dict[str, list[str]]:
    """Load raw filing text keyed by document_id (path.stem).

    Raises FileNotFoundError if filings directory is missing — this means
    ``pipeline raw fetch`` was not run.
    """
    if not filings_dir.exists():
        raise FileNotFoundError(
            f"Raw filings directory not found: {filings_dir}. "
            "Run 'skill-pipeline raw-fetch --deal <slug>' first."
        )
    lines_by_document: dict[str, list[str]] = {}
    for path in filings_dir.glob("*.txt"):
        lines_by_document[path.stem] = path.read_text(encoding="utf-8").splitlines()
    return lines_by_document


def _load_chronology_blocks(path: Path) -> list[ChronologyBlock]:
    blocks: list[ChronologyBlock] = []
    for line in path.read_text(encoding="utf-8").strip().splitlines():
        if line.strip():
            blocks.append(ChronologyBlock.model_validate_json(line))
    return blocks


def _resolve_quote_match(
    raw_segment: str,
    anchor_text: str,
    raw_lines: list[str],
    start_line: int,
    end_line: int,
) -> QuoteMatchType:
    """Resolve anchor in segment; if unresolved, try +/-3 line expansion.

    Returns EXACT, NORMALIZED, FUZZY, or UNRESOLVED.
    """
    match_type, _, _ = find_anchor_in_segment(raw_segment, anchor_text)
    if match_type in STRICT_QUOTE_MATCH_TYPES:
        return match_type
    expanded_start = max(1, start_line - SPAN_EXPANSION_LINES)
    expanded_end = min(len(raw_lines), end_line + SPAN_EXPANSION_LINES)
    expanded_lines = raw_lines[expanded_start - 1 : expanded_end]
    expanded_segment = "\n".join(expanded_lines)
    expanded_match_type, _, _ = find_anchor_in_segment(expanded_segment, anchor_text)
    if expanded_match_type in STRICT_QUOTE_MATCH_TYPES:
        return expanded_match_type
    return match_type


def _check_quote_validation(
    artifacts: LoadedExtractArtifacts,
    blocks: list[ChronologyBlock],
    document_lines: dict[str, list[str]],
) -> tuple[list[VerificationFinding], int]:
    """Round 1: Validate each quote.text against filing text in the referenced block."""
    findings: list[VerificationFinding] = []
    total_checks = 0
    blocks_by_id: dict[str, ChronologyBlock] = {}
    for b in blocks:
        if b.block_id in blocks_by_id:
            raise ValueError(
                f"Duplicate block_id {b.block_id!r} across documents "
                f"{blocks_by_id[b.block_id].document_id!r} and {b.document_id!r}. "
                "Block IDs must be globally unique."
            )
        blocks_by_id[b.block_id] = b

    all_quotes: list[QuoteEntry] = []
    if artifacts.raw_actors:
        all_quotes.extend(artifacts.raw_actors.quotes)
    if artifacts.raw_events:
        all_quotes.extend(artifacts.raw_events.quotes)

    seen_ids: set[str] = set()
    for quote in all_quotes:
        if quote.quote_id in seen_ids:
            findings.append(
                VerificationFinding(
                    check_type="quote_validation",
                    severity="error",
                    repairability="repairable",
                    description=f"Duplicate quote_id {quote.quote_id!r} in quotes array",
                )
            )
        seen_ids.add(quote.quote_id)

    for quote in all_quotes:
        total_checks += 1
        block = blocks_by_id.get(quote.block_id)
        if block is None:
            findings.append(
                VerificationFinding(
                    check_type="quote_validation",
                    severity="error",
                    repairability="repairable",
                    description=f"Quote {quote.quote_id!r} references unknown block_id {quote.block_id!r}",
                    block_ids=[quote.block_id],
                    anchor_text=quote.text,
                )
            )
            continue

        raw_lines = document_lines.get(block.document_id, [])
        if not raw_lines:
            findings.append(
                VerificationFinding(
                    check_type="quote_validation",
                    severity="error",
                    repairability="repairable",
                    description=f"No document lines for quote {quote.quote_id!r} in block {quote.block_id}",
                    block_ids=[quote.block_id],
                    anchor_text=quote.text,
                )
            )
            continue

        segment_lines = raw_lines[block.start_line - 1 : block.end_line]
        raw_segment = "\n".join(segment_lines)
        match_type = _resolve_quote_match(
            raw_segment, quote.text, raw_lines, block.start_line, block.end_line
        )

        if match_type in {QuoteMatchType.FUZZY, QuoteMatchType.UNRESOLVED}:
            findings.append(
                VerificationFinding(
                    check_type="quote_validation",
                    severity="error",
                    repairability="repairable",
                    description=(
                        f"Quote {quote.quote_id!r} text not found at EXACT/NORMALIZED "
                        f"level in block {quote.block_id}"
                    ),
                    block_ids=[quote.block_id],
                    anchor_text=quote.text,
                )
            )

    return findings, total_checks


def _check_quote_id_integrity(
    artifacts: LoadedExtractArtifacts,
) -> tuple[list[VerificationFinding], int]:
    """Round 2: Check that every actor/event quote_id exists in the quotes array."""
    findings: list[VerificationFinding] = []
    total_checks = 0

    known_ids: set[str] = set()
    if artifacts.raw_actors:
        known_ids.update(quote.quote_id for quote in artifacts.raw_actors.quotes)
    if artifacts.raw_events:
        known_ids.update(quote.quote_id for quote in artifacts.raw_events.quotes)

    if artifacts.raw_actors:
        for actor in artifacts.raw_actors.actors:
            for quote_id in actor.quote_ids:
                total_checks += 1
                if quote_id not in known_ids:
                    findings.append(
                        VerificationFinding(
                            check_type="quote_id_integrity",
                            severity="error",
                            repairability="repairable",
                            description=f"Actor {actor.actor_id!r} references unknown quote_id {quote_id!r}",
                            actor_ids=[actor.actor_id],
                        )
                    )
        for assertion in artifacts.raw_actors.count_assertions:
            for quote_id in assertion.quote_ids:
                total_checks += 1
                if quote_id not in known_ids:
                    findings.append(
                        VerificationFinding(
                            check_type="quote_id_integrity",
                            severity="error",
                            repairability="repairable",
                            description=f"Count assertion {assertion.subject!r} references unknown quote_id {quote_id!r}",
                        )
                    )

    if artifacts.raw_events:
        for event in artifacts.raw_events.events:
            for quote_id in event.quote_ids:
                total_checks += 1
                if quote_id not in known_ids:
                    findings.append(
                        VerificationFinding(
                            check_type="quote_id_integrity",
                            severity="error",
                            repairability="repairable",
                            description=f"Event {event.event_id!r} references unknown quote_id {quote_id!r}",
                            event_ids=[event.event_id],
                        )
                    )

    return findings, total_checks


def _check_referential_integrity(
    actors,
    events,
) -> tuple[list[VerificationFinding], int]:
    """Event actor_ids, invited_actor_ids, and advised_actor_id must exist in actors."""
    findings: list[VerificationFinding] = []
    total_checks = 0
    actor_ids = {a.actor_id for a in actors.actors}

    for evt in events.events:
        for aid in evt.actor_ids:
            total_checks += 1
            if aid not in actor_ids:
                findings.append(
                    VerificationFinding(
                        check_type="referential_integrity",
                        severity="error",
                        repairability="repairable",
                        description=f"Event references actor {aid!r} which is absent from actors.",
                        event_ids=[evt.event_id],
                    )
                )
        if evt.executed_with_actor_id:
            total_checks += 1
            if evt.executed_with_actor_id not in actor_ids:
                findings.append(
                    VerificationFinding(
                        check_type="referential_integrity",
                        severity="error",
                        repairability="repairable",
                        description=(
                            f"Executed event references executed_with_actor_id "
                            f"{evt.executed_with_actor_id!r} which is absent from actors."
                        ),
                        event_ids=[evt.event_id],
                    )
                )
        for aid in evt.invited_actor_ids:
            total_checks += 1
            if aid not in actor_ids:
                findings.append(
                    VerificationFinding(
                        check_type="referential_integrity",
                        severity="error",
                        repairability="repairable",
                        description=f"Event references invited actor {aid!r} which is absent from actors.",
                        event_ids=[evt.event_id],
                    )
                )

    for actor in actors.actors:
        if actor.advised_actor_id and actor.advised_actor_id not in actor_ids:
            total_checks += 1
            findings.append(
                VerificationFinding(
                    check_type="referential_integrity",
                    severity="error",
                    repairability="repairable",
                    description=f"Advisor references advised_actor_id {actor.advised_actor_id!r} which is absent.",
                    actor_ids=[actor.actor_id],
                )
            )
        elif actor.advised_actor_id:
            total_checks += 1

    return findings, total_checks


def _check_structural_integrity(events) -> tuple[list[VerificationFinding], int]:
    """Minimal structural checks: initiation event, outcome event, proposal actor_ids."""
    findings: list[VerificationFinding] = []
    total_checks = 2
    initiation_types = {"target_sale", "target_sale_public", "bidder_sale", "bidder_interest", "activist_sale"}
    outcome_types = {"executed", "terminated", "restarted"}

    has_initiation = any(evt.event_type in initiation_types for evt in events.events)
    if not has_initiation:
        findings.append(
            VerificationFinding(
                check_type="structural_integrity",
                severity="error",
                repairability="repairable",
                description="At least one process initiation event (target_sale, bidder_sale, etc.) is required.",
            )
        )

    has_outcome = any(evt.event_type in outcome_types for evt in events.events)
    if not has_outcome:
        findings.append(
            VerificationFinding(
                check_type="structural_integrity",
                severity="error",
                repairability="repairable",
                description="At least one outcome event (executed, terminated, restarted) is required.",
            )
        )

    for evt in events.events:
        if evt.event_type == "proposal" and not evt.actor_ids:
            total_checks += 1
            findings.append(
                VerificationFinding(
                    check_type="structural_integrity",
                    severity="error",
                    repairability="repairable",
                    description="Proposal events must have non-empty actor_ids.",
                    event_ids=[evt.event_id],
                )
            )
        elif evt.event_type == "proposal":
            total_checks += 1
        if evt.event_type == "executed" and not evt.executed_with_actor_id and not evt.actor_ids:
            total_checks += 1
            findings.append(
                VerificationFinding(
                    check_type="structural_integrity",
                    severity="error",
                    repairability="repairable",
                    description="Executed event must have executed_with_actor_id or non-empty actor_ids.",
                    event_ids=[evt.event_id],
                )
            )
        elif evt.event_type == "executed":
            total_checks += 1

    return findings, total_checks


def _check_quote_verification_canonical(
    artifacts: LoadedExtractArtifacts,
    document_lines: dict[str, list[str]],
) -> tuple[list[VerificationFinding], int]:
    findings: list[VerificationFinding] = []
    total_checks = 0
    span_index = artifacts.span_index

    def _check_span_ids(span_ids: list[str], *, actor_ids: list[str], event_ids: list[str]) -> None:
        nonlocal total_checks
        for span_id in span_ids:
            total_checks += 1
            span = span_index.get(span_id)
            if span is None:
                findings.append(
                    VerificationFinding(
                        check_type="quote_verification",
                        severity="error",
                        repairability="repairable",
                        description=f"Unknown evidence span_id: {span_id!r}",
                        actor_ids=actor_ids,
                        event_ids=event_ids,
                        span_ids=[span_id],
                    )
                )
                continue
            if not span.anchor_text or not span.anchor_text.strip():
                continue
            raw_lines = document_lines.get(span.document_id, [])
            if not raw_lines:
                findings.append(
                    VerificationFinding(
                        check_type="quote_verification",
                        severity="error",
                        repairability="repairable",
                        description=f"No document lines for span {span_id!r}; cannot verify anchor.",
                        actor_ids=actor_ids,
                        event_ids=event_ids,
                        span_ids=[span_id],
                        block_ids=span.block_ids,
                        evidence_ids=span.evidence_ids,
                        anchor_text=span.anchor_text,
                    )
                )
                continue

            segment_lines = raw_lines[span.start_line - 1 : span.end_line]
            raw_segment = "\n".join(segment_lines)
            match_type = _resolve_quote_match(
                raw_segment,
                span.anchor_text,
                raw_lines,
                span.start_line,
                span.end_line,
            )
            if match_type in {QuoteMatchType.FUZZY, QuoteMatchType.UNRESOLVED}:
                findings.append(
                    VerificationFinding(
                        check_type="quote_verification",
                        severity="error",
                        repairability="repairable",
                        description=f"anchor_text not found at EXACT/NORMALIZED level within +/-{SPAN_EXPANSION_LINES} lines of span {span_id}",
                        actor_ids=actor_ids,
                        event_ids=event_ids,
                        span_ids=[span_id],
                        block_ids=span.block_ids,
                        evidence_ids=span.evidence_ids,
                        anchor_text=span.anchor_text,
                    )
                )
            elif span.match_type in {QuoteMatchType.FUZZY, QuoteMatchType.UNRESOLVED}:
                findings.append(
                    VerificationFinding(
                        check_type="quote_verification",
                        severity="error",
                        repairability="repairable",
                        description=f"Stored span {span_id} has non-verifiable match_type {span.match_type}.",
                        actor_ids=actor_ids,
                        event_ids=event_ids,
                        span_ids=[span_id],
                        block_ids=span.block_ids,
                        evidence_ids=span.evidence_ids,
                        anchor_text=span.anchor_text,
                    )
                )

    for actor in artifacts.actors.actors:
        _check_span_ids(actor.evidence_span_ids, actor_ids=[actor.actor_id], event_ids=[])

    for evt in artifacts.events.events:
        _check_span_ids(evt.evidence_span_ids, actor_ids=[], event_ids=[evt.event_id])

    return findings, total_checks


def _check_canonical_evidence_presence(artifacts: LoadedExtractArtifacts) -> tuple[list[VerificationFinding], int]:
    if artifacts.mode != "canonical":
        return [], 0

    findings: list[VerificationFinding] = []
    total_checks = 0
    actor_ids_affected: list[str] = []
    event_ids_affected: list[str] = []

    for actor in artifacts.actors.actors:
        total_checks += 1
        if not actor.evidence_span_ids:
            actor_ids_affected.append(actor.actor_id)

    for evt in artifacts.events.events:
        total_checks += 1
        if not evt.evidence_span_ids:
            event_ids_affected.append(evt.event_id)

    if actor_ids_affected or event_ids_affected:
        findings.append(
            VerificationFinding(
                check_type="canonical_evidence_required",
                severity="error",
                repairability="repairable",
                description="Canonical actors and events must carry at least one evidence span.",
                actor_ids=sorted(actor_ids_affected),
                event_ids=sorted(event_ids_affected),
            )
        )

    return findings, total_checks


def _collect_verification_findings(paths: SkillPathSet) -> tuple[list[VerificationFinding], int]:
    """Run all checks and return findings."""
    blocks = _load_chronology_blocks(paths.chronology_blocks_path)
    document_lines = _load_document_lines(paths.raw_root / paths.deal_slug / "filings")
    artifacts = load_extract_artifacts(paths)
    actors = artifacts.raw_actors if artifacts.mode == "quote_first" else artifacts.actors
    events = artifacts.raw_events if artifacts.mode == "quote_first" else artifacts.events

    findings: list[VerificationFinding] = []
    total_checks = 0
    if artifacts.mode == "quote_first":
        quote_findings, quote_checks = _check_quote_validation(
            artifacts,
            blocks,
            document_lines,
        )
        findings.extend(quote_findings)
        total_checks += quote_checks

        integrity_findings, integrity_checks = _check_quote_id_integrity(artifacts)
        findings.extend(integrity_findings)
        total_checks += integrity_checks
    else:
        quote_findings, quote_checks = _check_quote_verification_canonical(
            artifacts,
            document_lines,
        )
        findings.extend(quote_findings)
        total_checks += quote_checks
    evidence_findings, evidence_checks = _check_canonical_evidence_presence(artifacts)
    findings.extend(evidence_findings)
    total_checks += evidence_checks
    referential_findings, referential_checks = _check_referential_integrity(actors, events)
    findings.extend(referential_findings)
    total_checks += referential_checks
    structural_findings, structural_checks = _check_structural_integrity(events)
    findings.extend(structural_findings)
    total_checks += structural_checks

    return findings, total_checks


def _build_findings_artifact(findings: list[VerificationFinding]) -> dict:
    return {"findings": [f.model_dump(mode="json") for f in findings]}


def _build_compatible_log(
    findings: list[VerificationFinding],
    *,
    total_checks: int,
) -> SkillVerificationLog:
    """Build verification_log compatible with verify-extraction gate (no LLM repair)."""
    round_1_errors = sum(1 for f in findings if f.severity == "error")
    round_1_warnings = sum(1 for f in findings if f.severity == "warning")

    round_1 = VerificationRound(
        findings=findings,
        fixes_applied=[],
    )
    round_2 = VerificationRoundTwo(
        findings=[],
        status="pass" if round_1_errors == 0 else "fail",
    )
    summary = VerificationLogSummary(
        total_checks=total_checks,
        round_1_errors=round_1_errors,
        round_1_warnings=round_1_warnings,
        fixes_applied=0,
        round_2_errors=0,
        round_2_warnings=0,
        status="pass" if round_1_errors == 0 else "fail",
    )
    return SkillVerificationLog(round_1=round_1, round_2=round_2, summary=summary)


def run_verify(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    """Run strict deterministic verification on extracted skill artifacts.

    Writes verification_findings.json and verification_log.json.
    Returns 1 if any error-level finding exists, else 0.
    """
    paths = build_skill_paths(deal_slug, project_root=project_root)

    if not paths.actors_raw_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.actors_raw_path}")
    if not paths.events_raw_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.events_raw_path}")
    if not paths.chronology_blocks_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.chronology_blocks_path}")

    findings, total_checks = _collect_verification_findings(paths)

    ensure_output_directories(paths, include_legacy=True)
    paths.verification_findings_path.write_text(
        json.dumps(_build_findings_artifact(findings), indent=2),
        encoding="utf-8",
    )
    paths.verification_log_path.write_text(
        _build_compatible_log(findings, total_checks=total_checks).model_dump_json(indent=2),
        encoding="utf-8",
    )

    return 1 if any(f.severity == "error" for f in findings) else 0
