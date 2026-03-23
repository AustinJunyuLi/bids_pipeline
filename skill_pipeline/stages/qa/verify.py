"""Strict deterministic verify for materialized skill artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from skill_pipeline.core.artifacts import LoadedArtifacts, load_artifacts
from skill_pipeline.schemas.common import QuoteMatchType
from skill_pipeline.normalize.quotes import find_anchor_in_segment

from skill_pipeline.core.config import PROJECT_ROOT
from skill_pipeline.schemas.runtime import (
    SkillPathSet,
    SkillVerificationLog,
    VerificationFinding,
    VerificationLogSummary,
    VerificationRound,
    VerificationRoundTwo,
)
from skill_pipeline.core.loaders import load_document_lines
from skill_pipeline.core.paths import build_skill_paths, ensure_output_directories

SPAN_EXPANSION_LINES = 3


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
    if match_type != QuoteMatchType.UNRESOLVED:
        return match_type
    expanded_start = max(1, start_line - SPAN_EXPANSION_LINES)
    expanded_end = min(len(raw_lines), end_line + SPAN_EXPANSION_LINES)
    expanded_lines = raw_lines[expanded_start - 1 : expanded_end]
    expanded_segment = "\n".join(expanded_lines)
    match_type, _, _ = find_anchor_in_segment(expanded_segment, anchor_text)
    return match_type


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
    initiation_types = {
        "target_sale",
        "target_sale_public",
        "bidder_sale",
        "bidder_interest",
        "activist_sale",
    }
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
        if (
            evt.event_type == "executed"
            and not evt.executed_with_actor_id
            and not evt.actor_ids
        ):
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
    artifacts: LoadedArtifacts,
    document_lines: dict[str, list[str]],
) -> tuple[list[VerificationFinding], int]:
    findings: list[VerificationFinding] = []
    total_checks = 0
    span_index = artifacts.span_index

    def _check_span_ids(
        span_ids: list[str], *, actor_ids: list[str], event_ids: list[str]
    ) -> None:
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
        _check_span_ids(
            actor.evidence_span_ids, actor_ids=[actor.actor_id], event_ids=[]
        )

    for evt in artifacts.events.events:
        _check_span_ids(evt.evidence_span_ids, actor_ids=[], event_ids=[evt.event_id])

    return findings, total_checks


def _collect_verification_findings(
    paths: SkillPathSet,
) -> tuple[list[VerificationFinding], int]:
    """Run all checks and return findings."""
    document_lines = load_document_lines(paths.raw_root / paths.deal_slug / "filings")
    artifacts = load_artifacts(paths)
    actors = artifacts.actors
    events = artifacts.events

    findings: list[VerificationFinding] = []
    total_checks = 0
    quote_findings, quote_checks = _check_quote_verification_canonical(
        artifacts,
        document_lines,
    )
    findings.extend(quote_findings)
    total_checks += quote_checks
    referential_findings, referential_checks = _check_referential_integrity(
        actors, events
    )
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
    """Run strict deterministic verification on materialized skill artifacts.

    Writes verification_findings.json and verification_log.json.
    Returns 1 if any error-level finding exists, else 0.
    """
    paths = build_skill_paths(deal_slug, project_root=project_root)

    if not paths.materialized_actors_path.exists():
        raise FileNotFoundError(
            f"Missing required input: {paths.materialized_actors_path}"
        )
    if not paths.materialized_events_path.exists():
        raise FileNotFoundError(
            f"Missing required input: {paths.materialized_events_path}"
        )

    findings, total_checks = _collect_verification_findings(paths)

    ensure_output_directories(paths)
    paths.verification_findings_path.write_text(
        json.dumps(_build_findings_artifact(findings), indent=2),
        encoding="utf-8",
    )
    paths.verification_log_path.write_text(
        _build_compatible_log(findings, total_checks=total_checks).model_dump_json(
            indent=2
        ),
        encoding="utf-8",
    )

    return 1 if any(f.severity == "error" for f in findings) else 0
