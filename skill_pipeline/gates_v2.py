"""Semantic gates for canonical v2 observation artifacts."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.extract_artifacts_v2 import load_observation_artifacts
from skill_pipeline.models import GateReportSummary
from skill_pipeline.models_v2 import (
    AgreementObservation,
    GateFindingV2,
    GateReportV2,
    ProposalObservation,
    SolicitationObservation,
)
from skill_pipeline.paths import build_skill_paths, ensure_output_directories


def _write_json(path: Path, report: GateReportV2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")


def _parse_date(value) -> date | None:
    if value is None:
        return None
    sort_date = getattr(value, "sort_date", None)
    if sort_date is not None:
        return sort_date
    normalized_start = getattr(value, "normalized_start", None)
    if normalized_start is None:
        return None
    try:
        return date.fromisoformat(normalized_start)
    except ValueError:
        return None


def _find_linear_cycles(graph: dict[str, str]) -> list[list[str]]:
    cycles: list[list[str]] = []
    visited: set[str] = set()
    for start in graph:
        if start in visited:
            continue
        path: list[str] = []
        index_by_node: dict[str, int] = {}
        current = start
        while current in graph:
            if current in index_by_node:
                cycles.append(path[index_by_node[current] :])
                break
            if current in visited:
                break
            index_by_node[current] = len(path)
            path.append(current)
            current = graph[current]
        visited.update(path)
    return cycles


def _revision_chain_findings(artifacts) -> list[GateFindingV2]:
    observations = artifacts.observations
    if observations is None:
        return []

    proposal_graph = {
        observation.observation_id: observation.revises_observation_id
        for observation in observations.observations
        if isinstance(observation, ProposalObservation) and observation.revises_observation_id
    }
    agreement_graph = {
        observation.observation_id: observation.supersedes_observation_id
        for observation in observations.observations
        if isinstance(observation, AgreementObservation) and observation.supersedes_observation_id
    }

    findings: list[GateFindingV2] = []
    for cycle in _find_linear_cycles(proposal_graph):
        findings.append(
            GateFindingV2(
                gate_id="proposal_revision_cycle",
                rule_id="proposal_revision_acyclic",
                severity="blocker",
                description=(
                    "Proposal revision chain must be acyclic; cycle detected in "
                    f"{', '.join(cycle)}."
                ),
                observation_ids=cycle,
            )
        )
    for cycle in _find_linear_cycles(agreement_graph):
        findings.append(
            GateFindingV2(
                gate_id="agreement_supersession_cycle",
                rule_id="agreement_supersession_acyclic",
                severity="blocker",
                description=(
                    "Agreement supersession chain must be acyclic; cycle detected in "
                    f"{', '.join(cycle)}."
                ),
                observation_ids=cycle,
            )
        )
    return findings


def _cohort_count_findings(artifacts) -> list[GateFindingV2]:
    observations = artifacts.observations
    if observations is None:
        return []

    findings: list[GateFindingV2] = []
    for cohort in observations.cohorts:
        if cohort.parent_cohort_id is None:
            continue
        parent = artifacts.cohort_index.get(cohort.parent_cohort_id)
        if parent is None:
            continue
        if cohort.exact_count <= parent.exact_count:
            continue
        findings.append(
            GateFindingV2(
                gate_id="cohort_child_count_exceeds_parent",
                rule_id="cohort_parent_count_bound",
                severity="blocker",
                description=(
                    f"Cohort {cohort.cohort_id!r} has exact_count={cohort.exact_count}, "
                    f"which exceeds parent {parent.cohort_id!r} exact_count={parent.exact_count}."
                ),
                cohort_ids=[parent.cohort_id, cohort.cohort_id],
            )
        )
    return findings


def _deadline_findings(artifacts) -> list[GateFindingV2]:
    observations = artifacts.observations
    if observations is None:
        return []

    findings: list[GateFindingV2] = []
    for observation in observations.observations:
        if not isinstance(observation, SolicitationObservation):
            continue
        solicitation_date = _parse_date(observation.date)
        due_date = _parse_date(observation.due_date)
        if solicitation_date is None or due_date is None:
            continue
        if due_date >= solicitation_date:
            continue
        findings.append(
            GateFindingV2(
                gate_id="solicitation_deadline_precedes_request",
                rule_id="solicitation_deadline_ordering",
                severity="blocker",
                description=(
                    f"Solicitation {observation.observation_id!r} has due date "
                    f"{due_date.isoformat()} before solicitation date {solicitation_date.isoformat()}."
                ),
                observation_ids=[observation.observation_id],
            )
        )
    return findings


def _build_report(findings: list[GateFindingV2]) -> GateReportV2:
    blocker_count = sum(1 for finding in findings if finding.severity == "blocker")
    warning_count = sum(1 for finding in findings if finding.severity == "warning")
    status: Literal["pass", "fail"] = "fail" if blocker_count > 0 else "pass"
    return GateReportV2(
        findings=findings,
        summary=GateReportSummary(
            blocker_count=blocker_count,
            warning_count=warning_count,
            status=status,
        ),
    )


def run_gates_v2(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    """Run graph-level semantic gates on canonical v2 observation artifacts."""
    paths = build_skill_paths(deal_slug, project_root=project_root)
    artifacts = load_observation_artifacts(paths, mode="canonical")

    findings: list[GateFindingV2] = []
    findings.extend(_revision_chain_findings(artifacts))
    findings.extend(_cohort_count_findings(artifacts))
    findings.extend(_deadline_findings(artifacts))

    report = _build_report(findings)
    ensure_output_directories(paths)
    _write_json(paths.gates_v2_report_path, report)
    return 1 if report.summary.status == "fail" else 0
