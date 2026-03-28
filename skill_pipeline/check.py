"""Tiny deterministic structural gate for extracted skill artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.extract_artifacts import LoadedExtractArtifacts, load_extract_artifacts
from skill_pipeline.models import (
    CheckFinding,
    CheckReportSummary,
    SkillCheckReport,
)
from skill_pipeline.paths import build_skill_paths, ensure_output_directories


def _read_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing required input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, report: SkillCheckReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")


def _get_actor_event_records(artifacts: LoadedExtractArtifacts) -> tuple[list, list]:
    if artifacts.mode == "quote_first":
        return artifacts.raw_actors.actors, artifacts.raw_events.events
    return artifacts.actors.actors, artifacts.events.events


def _actor_has_evidence(artifacts: LoadedExtractArtifacts, actor) -> bool:
    if artifacts.mode == "quote_first":
        return bool(actor.quote_ids)
    return bool(actor.evidence_span_ids)


def _event_has_evidence(artifacts: LoadedExtractArtifacts, event) -> bool:
    if artifacts.mode == "quote_first":
        return bool(event.quote_ids)
    return bool(event.evidence_span_ids)


def _check_proposal_terms(artifacts: LoadedExtractArtifacts) -> list[CheckFinding]:
    findings: list[CheckFinding] = []
    _, events = _get_actor_event_records(artifacts)
    for evt in events:
        if evt.event_type != "proposal":
            continue
        if evt.terms is None or evt.formality_signals is None:
            findings.append(
                CheckFinding(
                    check_id="proposal_terms_required",
                    severity="blocker",
                    description="Proposal events must have both terms and formality_signals.",
                    event_ids=[evt.event_id],
                )
            )
    return findings


def _check_bidder_kind(artifacts: LoadedExtractArtifacts) -> list[CheckFinding]:
    findings: list[CheckFinding] = []
    actors, _ = _get_actor_event_records(artifacts)
    for actor in actors:
        if actor.role == "bidder" and actor.bidder_kind is None:
            findings.append(
                CheckFinding(
                    check_id="bidder_kind_missing",
                    severity="warning",
                    description="Bidder actors should have bidder_kind.",
                    actor_ids=[actor.actor_id],
                )
            )
    return findings


def _check_empty_anchor_text(artifacts: LoadedExtractArtifacts) -> list[CheckFinding]:
    findings: list[CheckFinding] = []
    actor_ids_affected: set[str] = set()
    event_ids_affected: set[str] = set()

    if artifacts.mode == "quote_first":
        quotes_by_id: dict[str, object] = {}
        if artifacts.raw_actors:
            for quote in artifacts.raw_actors.quotes:
                quotes_by_id[quote.quote_id] = quote
        if artifacts.raw_events:
            for quote in artifacts.raw_events.quotes:
                quotes_by_id[quote.quote_id] = quote

        for actor in artifacts.raw_actors.actors:
            for quote_id in actor.quote_ids:
                quote = quotes_by_id.get(quote_id)
                if quote is None or not quote.text or not quote.text.strip():
                    actor_ids_affected.add(actor.actor_id)
                    break

        for evt in artifacts.raw_events.events:
            for quote_id in evt.quote_ids:
                quote = quotes_by_id.get(quote_id)
                if quote is None or not quote.text or not quote.text.strip():
                    event_ids_affected.add(evt.event_id)
                    break
    else:
        span_index = artifacts.span_index
        for actor in artifacts.actors.actors:
            for span_id in actor.evidence_span_ids:
                span = span_index.get(span_id)
                if span is None or not span.anchor_text or not span.anchor_text.strip():
                    actor_ids_affected.add(actor.actor_id)
                    break

        for evt in artifacts.events.events:
            for span_id in evt.evidence_span_ids:
                span = span_index.get(span_id)
                if span is None or not span.anchor_text or not span.anchor_text.strip():
                    event_ids_affected.add(evt.event_id)
                    break

    if actor_ids_affected or event_ids_affected:
        findings.append(
            CheckFinding(
                check_id="empty_anchor_text",
                severity="blocker",
                description="Evidence references must have non-empty anchor_text.",
                actor_ids=sorted(actor_ids_affected),
                event_ids=sorted(event_ids_affected),
            )
        )

    return findings


def _check_canonical_evidence_presence(artifacts: LoadedExtractArtifacts) -> list[CheckFinding]:
    if artifacts.mode != "canonical":
        return []

    actor_ids_affected: list[str] = []
    event_ids_affected: list[str] = []

    for actor in artifacts.actors.actors:
        if not actor.evidence_span_ids:
            actor_ids_affected.append(actor.actor_id)

    for evt in artifacts.events.events:
        if not evt.evidence_span_ids:
            event_ids_affected.append(evt.event_id)

    if not actor_ids_affected and not event_ids_affected:
        return []

    return [
        CheckFinding(
            check_id="canonical_evidence_required",
            severity="blocker",
            description="Canonical actors and events must carry at least one evidence span.",
            actor_ids=sorted(actor_ids_affected),
            event_ids=sorted(event_ids_affected),
        )
    ]


def _check_nda_count_gaps(artifacts: LoadedExtractArtifacts) -> list[CheckFinding]:
    findings: list[CheckFinding] = []
    actor_records, event_records = _get_actor_event_records(artifacts)
    actor_artifact = artifacts.raw_actors if artifacts.mode == "quote_first" else artifacts.actors

    nda_actor_ids: set[str] = set()
    for evt in event_records:
        if evt.event_type == "nda" and _event_has_evidence(artifacts, evt):
            nda_actor_ids.update(evt.actor_ids)

    subject_to_kind = {
        "nda_signed_financial_buyers": "financial",
        "nda_signed_strategic_buyers": "strategic",
    }
    for subject, kind in subject_to_kind.items():
        assertions = [assertion for assertion in actor_artifact.count_assertions if assertion.subject == subject]
        if not assertions:
            continue
        # Use the strongest filing-backed count when the same subject is asserted multiple times.
        asserted_count = max(assertion.count for assertion in assertions)
        grounded_actor_ids = sorted(
            actor.actor_id
            for actor in actor_records
            if actor.role == "bidder"
            and actor.bidder_kind == kind
            and _actor_has_evidence(artifacts, actor)
            and actor.actor_id in nda_actor_ids
        )
        if asserted_count <= len(grounded_actor_ids):
            continue

        findings.append(
            CheckFinding(
                check_id="nda_count_assertion_gap",
                severity="blocker",
                description=(
                    f"Count assertion {subject}={asserted_count} exceeds grounded bidder actors "
                    f"with NDA evidence ({len(grounded_actor_ids)})."
                ),
                actor_ids=grounded_actor_ids,
            )
        )

    return findings


def _build_report(findings: list[CheckFinding]) -> SkillCheckReport:
    blocker_count = sum(1 for f in findings if f.severity == "blocker")
    warning_count = sum(1 for f in findings if f.severity == "warning")
    status: Literal["pass", "fail"] = "fail" if blocker_count > 0 else "pass"
    return SkillCheckReport(
        findings=findings,
        summary=CheckReportSummary(
            blocker_count=blocker_count,
            warning_count=warning_count,
            status=status,
        ),
    )


def run_check(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    """Run structural checks on extracted skill artifacts.

    Reads actors_raw.json and events_raw.json, writes check_report.json.
    Returns 1 if any blocker exists, else 0.
    """
    paths = build_skill_paths(deal_slug, project_root=project_root)
    artifacts = load_extract_artifacts(paths)

    findings: list[CheckFinding] = []
    findings.extend(_check_proposal_terms(artifacts))
    findings.extend(_check_bidder_kind(artifacts))
    findings.extend(_check_canonical_evidence_presence(artifacts))
    findings.extend(_check_nda_count_gaps(artifacts))
    findings.extend(_check_empty_anchor_text(artifacts))

    report = _build_report(findings)
    ensure_output_directories(paths)
    _write_json(paths.check_report_path, report)

    return 1 if report.summary.status == "fail" else 0
