"""Structural validation for canonical v2 observation artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.extract_artifacts_v2 import (
    LoadedObservationArtifacts,
    load_observation_artifacts,
)
from skill_pipeline.models import CheckReportSummary
from skill_pipeline.models_v2 import (
    AgreementObservation,
    CheckFindingV2,
    ProposalObservation,
    SkillCheckReportV2,
    SolicitationObservation,
)
from skill_pipeline.paths import build_skill_paths, ensure_output_directories


def _write_json(path: Path, report: SkillCheckReportV2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")


def _span_ref_findings(artifacts: LoadedObservationArtifacts) -> list[CheckFindingV2]:
    findings: list[CheckFindingV2] = []
    span_ids = set(artifacts.span_index)
    observations = artifacts.observations
    if observations is None:
        return findings

    for party in observations.parties:
        missing = sorted(span_id for span_id in party.evidence_span_ids if span_id not in span_ids)
        if missing:
            findings.append(
                CheckFindingV2(
                    check_id="party_span_ref_missing",
                    severity="blocker",
                    description=(
                        f"Party {party.party_id!r} references unknown span IDs: "
                        f"{', '.join(missing)}."
                    ),
                    party_ids=[party.party_id],
                )
            )

    for cohort in observations.cohorts:
        missing = sorted(span_id for span_id in cohort.evidence_span_ids if span_id not in span_ids)
        if missing:
            findings.append(
                CheckFindingV2(
                    check_id="cohort_span_ref_missing",
                    severity="blocker",
                    description=(
                        f"Cohort {cohort.cohort_id!r} references unknown span IDs: "
                        f"{', '.join(missing)}."
                    ),
                    cohort_ids=[cohort.cohort_id],
                )
            )

    for observation in observations.observations:
        if not observation.evidence_span_ids:
            findings.append(
                CheckFindingV2(
                    check_id="observation_evidence_required",
                    severity="blocker",
                    description=(
                        f"Observation {observation.observation_id!r} must carry at least one "
                        "evidence span."
                    ),
                    observation_ids=[observation.observation_id],
                )
            )
            continue

        missing = sorted(
            span_id for span_id in observation.evidence_span_ids if span_id not in span_ids
        )
        if missing:
            findings.append(
                CheckFindingV2(
                    check_id="observation_span_ref_missing",
                    severity="blocker",
                    description=(
                        f"Observation {observation.observation_id!r} references unknown span IDs: "
                        f"{', '.join(missing)}."
                    ),
                    observation_ids=[observation.observation_id],
                )
            )

    return findings


def _reference_integrity_findings(artifacts: LoadedObservationArtifacts) -> list[CheckFindingV2]:
    findings: list[CheckFindingV2] = []
    observations = artifacts.observations
    if observations is None:
        return findings

    party_ids = set(artifacts.party_index)
    cohort_ids = set(artifacts.cohort_index)
    observation_ids = set(artifacts.observation_index)

    for party in observations.parties:
        if party.advised_party_id and party.advised_party_id not in party_ids:
            findings.append(
                CheckFindingV2(
                    check_id="advised_party_ref_missing",
                    severity="blocker",
                    description=(
                        f"Party {party.party_id!r} references missing advised_party_id "
                        f"{party.advised_party_id!r}."
                    ),
                    party_ids=[party.party_id, party.advised_party_id],
                )
            )

    for cohort in observations.cohorts:
        missing_members = sorted(
            party_id for party_id in cohort.known_member_party_ids if party_id not in party_ids
        )
        if missing_members:
            findings.append(
                CheckFindingV2(
                    check_id="cohort_member_ref_missing",
                    severity="blocker",
                    description=(
                        f"Cohort {cohort.cohort_id!r} references missing known members: "
                        f"{', '.join(missing_members)}."
                    ),
                    party_ids=missing_members,
                    cohort_ids=[cohort.cohort_id],
                )
            )
        if cohort.parent_cohort_id and cohort.parent_cohort_id not in cohort_ids:
            findings.append(
                CheckFindingV2(
                    check_id="cohort_parent_ref_missing",
                    severity="blocker",
                    description=(
                        f"Cohort {cohort.cohort_id!r} references missing parent cohort "
                        f"{cohort.parent_cohort_id!r}."
                    ),
                    cohort_ids=[cohort.cohort_id, cohort.parent_cohort_id],
                )
            )
        if cohort.created_by_observation_id not in observation_ids:
            findings.append(
                CheckFindingV2(
                    check_id="cohort_creator_ref_missing",
                    severity="blocker",
                    description=(
                        f"Cohort {cohort.cohort_id!r} references missing creator observation "
                        f"{cohort.created_by_observation_id!r}."
                    ),
                    cohort_ids=[cohort.cohort_id],
                    observation_ids=[cohort.created_by_observation_id],
                )
            )

    for observation in observations.observations:
        unresolved_entity_refs = sorted(
            ref
            for ref in _entity_refs_for_observation(observation)
            if ref not in party_ids and ref not in cohort_ids
        )
        if unresolved_entity_refs:
            findings.append(
                CheckFindingV2(
                    check_id="observation_entity_ref_missing",
                    severity="blocker",
                    description=(
                        f"Observation {observation.observation_id!r} references missing "
                        f"party/cohort IDs: {', '.join(unresolved_entity_refs)}."
                    ),
                    observation_ids=[observation.observation_id],
                    party_ids=[ref for ref in unresolved_entity_refs if ref in party_ids],
                    cohort_ids=[ref for ref in unresolved_entity_refs if ref in cohort_ids],
                )
            )

        unresolved_observation_refs = sorted(
            ref
            for ref in _observation_refs_for_observation(observation)
            if ref not in observation_ids
        )
        if unresolved_observation_refs:
            findings.append(
                CheckFindingV2(
                    check_id="observation_ref_missing",
                    severity="blocker",
                    description=(
                        f"Observation {observation.observation_id!r} references missing "
                        f"observation IDs: {', '.join(unresolved_observation_refs)}."
                    ),
                    observation_ids=[observation.observation_id] + unresolved_observation_refs,
                )
            )

    return findings


def _proposal_subject_findings(artifacts: LoadedObservationArtifacts) -> list[CheckFindingV2]:
    findings: list[CheckFindingV2] = []
    observations = artifacts.observations
    if observations is None:
        return findings

    for observation in observations.observations:
        if not isinstance(observation, ProposalObservation):
            continue
        bidder_subject_found = False
        for subject_ref in observation.subject_refs:
            party = artifacts.party_index.get(subject_ref)
            if party is not None and party.role == "bidder":
                bidder_subject_found = True
                break
            if subject_ref in artifacts.cohort_index:
                bidder_subject_found = True
                break
        if not bidder_subject_found:
            findings.append(
                CheckFindingV2(
                    check_id="proposal_bidder_subject_required",
                    severity="blocker",
                    description=(
                        f"Proposal {observation.observation_id!r} must have at least one "
                        "bidder or bidder-cohort subject."
                    ),
                    observation_ids=[observation.observation_id],
                )
            )

    return findings


def _agreement_supersession_findings(
    artifacts: LoadedObservationArtifacts,
) -> list[CheckFindingV2]:
    findings: list[CheckFindingV2] = []
    observations = artifacts.observations
    if observations is None:
        return findings

    for observation in observations.observations:
        if not isinstance(observation, AgreementObservation):
            continue
        if observation.supersedes_observation_id is None:
            continue
        target = artifacts.observation_index.get(observation.supersedes_observation_id)
        if target is None or isinstance(target, AgreementObservation):
            continue
        findings.append(
            CheckFindingV2(
                check_id="agreement_supersedes_non_agreement",
                severity="blocker",
                description=(
                    f"Agreement {observation.observation_id!r} supersedes "
                    f"{observation.supersedes_observation_id!r}, which is not an agreement."
                ),
                observation_ids=[
                    observation.observation_id,
                    observation.supersedes_observation_id,
                ],
            )
        )

    return findings


def _entity_refs_for_observation(observation) -> list[str]:
    refs = list(observation.subject_refs) + list(observation.counterparty_refs)
    if isinstance(observation, SolicitationObservation):
        refs.extend(observation.recipient_refs)
    return refs


def _observation_refs_for_observation(observation) -> list[str]:
    refs: list[str] = []
    for field_name in (
        "requested_by_observation_id",
        "revises_observation_id",
        "supersedes_observation_id",
        "related_observation_id",
    ):
        value = getattr(observation, field_name, None)
        if value:
            refs.append(value)
    return refs


def _build_report(findings: list[CheckFindingV2]) -> SkillCheckReportV2:
    blocker_count = sum(1 for finding in findings if finding.severity == "blocker")
    warning_count = sum(1 for finding in findings if finding.severity == "warning")
    status: Literal["pass", "fail"] = "fail" if blocker_count > 0 else "pass"
    return SkillCheckReportV2(
        findings=findings,
        summary=CheckReportSummary(
            blocker_count=blocker_count,
            warning_count=warning_count,
            status=status,
        ),
    )


def run_check_v2(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    """Run structural checks on canonical v2 observation artifacts."""
    paths = build_skill_paths(deal_slug, project_root=project_root)
    artifacts = load_observation_artifacts(paths, mode="canonical")

    findings: list[CheckFindingV2] = []
    findings.extend(_span_ref_findings(artifacts))
    findings.extend(_reference_integrity_findings(artifacts))
    findings.extend(_proposal_subject_findings(artifacts))
    findings.extend(_agreement_supersession_findings(artifacts))

    report = _build_report(findings)
    ensure_output_directories(paths)
    _write_json(paths.check_v2_report_path, report)
    return 1 if report.summary.status == "fail" else 0
