"""Tiny deterministic structural gate for extracted skill artifacts."""

from __future__ import annotations

import json
from collections import defaultdict
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


def _check_proposal_terms(artifacts: LoadedExtractArtifacts) -> list[CheckFinding]:
    findings: list[CheckFinding] = []
    events = artifacts.raw_events.events if artifacts.mode == "legacy" else artifacts.events.events
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
    actors = artifacts.raw_actors.actors if artifacts.mode == "legacy" else artifacts.actors.actors
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

    if artifacts.mode == "legacy":
        for actor in artifacts.raw_actors.actors:
            for ref in actor.evidence_refs:
                if not ref.anchor_text or not ref.anchor_text.strip():
                    actor_ids_affected.add(actor.actor_id)
                    break

        for evt in artifacts.raw_events.events:
            for ref in evt.evidence_refs:
                if not ref.anchor_text or not ref.anchor_text.strip():
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


def _check_missing_canonical_provenance(artifacts: LoadedExtractArtifacts) -> list[CheckFinding]:
    if artifacts.mode != "canonical":
        return []

    actor_ids_missing = sorted(
        actor.actor_id
        for actor in artifacts.actors.actors
        if not actor.evidence_span_ids
    )
    event_ids_missing = sorted(
        event.event_id
        for event in artifacts.events.events
        if not event.evidence_span_ids
    )
    if not actor_ids_missing and not event_ids_missing:
        return []

    return [
        CheckFinding(
            check_id="missing_canonical_provenance",
            severity="blocker",
            description="Canonical actors and events must have non-empty evidence_span_ids.",
            actor_ids=actor_ids_missing,
            event_ids=event_ids_missing,
        )
    ]


def _check_actor_audit(artifacts: LoadedExtractArtifacts) -> list[CheckFinding]:
    """Audit actor roster for residual issues from chunked extraction."""
    findings: list[CheckFinding] = []
    actors_artifact = artifacts.raw_actors if artifacts.mode == "legacy" else artifacts.actors
    events_artifact = artifacts.raw_events if artifacts.mode == "legacy" else artifacts.events
    if actors_artifact is None or events_artifact is None:
        raise ValueError(f"Unexpected extract artifact mode: {artifacts.mode}")

    actors = actors_artifact.actors
    events = events_artifact.events
    count_assertions = actors_artifact.count_assertions

    by_canonical_name: dict[str, list] = defaultdict(list)
    for actor in actors:
        by_canonical_name[actor.canonical_name.strip().upper()].append(actor)
    for canonical_name, group in by_canonical_name.items():
        if len(group) <= 1:
            continue
        actor_ids = [actor.actor_id for actor in group]
        findings.append(
            CheckFinding(
                check_id="duplicate_canonical_name",
                severity="warning",
                description=f"Actors {actor_ids} share canonical_name '{canonical_name}'.",
                actor_ids=actor_ids,
            )
        )

    nda_actor_ids: set[str] = set()
    nda_event_count = 0
    for event in events:
        if event.event_type != "nda":
            continue
        nda_event_count += 1
        nda_actor_ids.update(event.actor_ids)

    for actor in actors:
        if actor.role == "bidder" and not actor.is_grouped and actor.actor_id not in nda_actor_ids:
            findings.append(
                CheckFinding(
                    check_id="bidder_no_nda",
                    severity="warning",
                    description=f"Bidder '{actor.actor_id}' has no NDA event.",
                    actor_ids=[actor.actor_id],
                )
            )

    for assertion in count_assertions:
        subject_lower = assertion.subject.lower()
        if "nda" not in subject_lower and "confidentiality" not in subject_lower:
            continue
        if nda_event_count != assertion.count:
            findings.append(
                CheckFinding(
                    check_id="count_assertion_gap",
                    severity="warning",
                    description=(
                        f"Count assertion '{assertion.subject}' expects {assertion.count}, "
                        f"found {nda_event_count}."
                    ),
                )
            )

    for actor in actors:
        if actor.role == "advisor" and actor.advised_actor_id is None:
            findings.append(
                CheckFinding(
                    check_id="advisor_missing_advised",
                    severity="warning",
                    description=f"Advisor '{actor.actor_id}' has no advised_actor_id.",
                    actor_ids=[actor.actor_id],
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
    findings.extend(_check_empty_anchor_text(artifacts))
    findings.extend(_check_missing_canonical_provenance(artifacts))
    findings.extend(_check_actor_audit(artifacts))

    report = _build_report(findings)
    ensure_output_directories(paths)
    _write_json(paths.check_report_path, report)

    return 1 if report.summary.status == "fail" else 0
