"""Structured coverage audit for canonical v2 observation artifacts."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.coverage_cues import (
    CoverageCue,
    build_coverage_cues,
    load_chronology_blocks,
    load_evidence_items,
    severity_for_cue,
)
from skill_pipeline.extract_artifacts_v2 import (
    LoadedObservationArtifacts,
    load_observation_artifacts,
)
from skill_pipeline.models import CoverageSummary
from skill_pipeline.models_v2 import (
    AgreementObservation,
    CoverageCheckRecordV2,
    CoverageFindingsArtifactV2,
    ProcessObservation,
    ProposalObservation,
    StatusObservation,
)
from skill_pipeline.paths import build_skill_paths, ensure_output_directories

DROP_STATUS_KINDS = frozenset(
    {
        "withdrew",
        "not_interested",
        "cannot_improve",
        "cannot_proceed",
        "limited_assets_only",
        "excluded",
    }
)
PROCESS_CUE_KINDS = frozenset({"sale_launch", "public_announcement", "press_release"})


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.model_dump_json(indent=2), encoding="utf-8")


def _span_ids_overlap(
    cue: CoverageCue,
    span_ids: list[str],
    span_index,
) -> bool:
    cue_block_ids = set(cue.block_ids)
    cue_evidence_ids = set(cue.evidence_ids)
    for span_id in span_ids:
        span = span_index.get(span_id)
        if span is None:
            continue
        if cue_evidence_ids and span.evidence_ids and cue_evidence_ids.intersection(span.evidence_ids):
            return True
        if cue_block_ids.intersection(span.block_ids):
            return True
    return False


def _matching_candidates(
    cue: CoverageCue,
    artifacts: LoadedObservationArtifacts,
) -> tuple[list[str], list[str], list[str], list[str]]:
    observation_ids: list[str] = []
    party_ids: list[str] = []
    cohort_ids: list[str] = []
    span_ids: set[str] = set()

    observations = artifacts.observations
    if observations is None:
        return observation_ids, party_ids, cohort_ids, []

    for observation in observations.observations:
        if not _observation_matches_cue_family(observation, cue.cue_family):
            continue
        if _span_ids_overlap(cue, observation.evidence_span_ids, artifacts.span_index):
            observation_ids.append(observation.observation_id)
            span_ids.update(observation.evidence_span_ids)

    if cue.cue_family == "advisor":
        for party in observations.parties:
            if party.role != "advisor":
                continue
            if _span_ids_overlap(cue, party.evidence_span_ids, artifacts.span_index):
                party_ids.append(party.party_id)
                span_ids.update(party.evidence_span_ids)

    return (
        sorted(set(observation_ids)),
        sorted(set(party_ids)),
        sorted(set(cohort_ids)),
        sorted(span_ids),
    )


def _observation_matches_cue_family(observation, cue_family: str) -> bool:
    if cue_family == "proposal":
        return isinstance(observation, ProposalObservation)
    if cue_family == "nda":
        return isinstance(observation, AgreementObservation) and observation.agreement_kind == "nda"
    if cue_family == "withdrawal_or_drop":
        return isinstance(observation, StatusObservation) and observation.status_kind in DROP_STATUS_KINDS
    if cue_family == "bidder_interest":
        return isinstance(observation, StatusObservation) and observation.status_kind == "expressed_interest"
    if cue_family == "process_initiation":
        return isinstance(observation, ProcessObservation) and (
            observation.process_kind in PROCESS_CUE_KINDS
            or observation.process_kind == "advisor_retention"
        )
    if cue_family == "advisor":
        return isinstance(observation, ProcessObservation) and observation.process_kind == "advisor_retention"
    return False


def _build_record(
    cue: CoverageCue,
    artifacts: LoadedObservationArtifacts,
) -> CoverageCheckRecordV2:
    issue_severity = severity_for_cue(cue)
    if issue_severity is None:
        raise ValueError(f"Unsupported cue severity for v2 coverage cue {cue.cue_family!r}")

    observation_ids, party_ids, cohort_ids, span_ids = _matching_candidates(cue, artifacts)
    total_matches = len(observation_ids) + len(party_ids) + len(cohort_ids)

    if total_matches == 0:
        status = "not_found"
        repairability = "repairable"
        description = (
            f"{cue.confidence.capitalize()}-confidence {cue.cue_family} cue was not covered "
            "by canonical v2 artifacts."
        )
        reason_code = f"uncovered_{cue.cue_family}_cue"
    elif total_matches == 1:
        status = "observed"
        repairability = None
        description = (
            f"{cue.confidence.capitalize()}-confidence {cue.cue_family} cue is covered by "
            "canonical v2 artifacts."
        )
        if observation_ids:
            reason_code = "matched_observation"
        elif party_ids:
            reason_code = "matched_party"
        else:
            reason_code = "matched_cohort"
    elif cue.cue_family == "nda" and observation_ids and not party_ids and not cohort_ids:
        status = "observed"
        repairability = None
        description = (
            f"{cue.confidence.capitalize()}-confidence {cue.cue_family} cue is covered by "
            "multiple canonical v2 observations."
        )
        reason_code = "matched_multiple_observations"
    else:
        status = "ambiguous"
        repairability = "repairable"
        description = (
            f"{cue.confidence.capitalize()}-confidence {cue.cue_family} cue matched multiple "
            "canonical v2 candidates."
        )
        reason_code = "multiple_matching_candidates"

    severity = "info" if status in {"observed", "derived"} else issue_severity

    return CoverageCheckRecordV2(
        cue_family=cue.cue_family,
        status=status,
        severity=severity,
        repairability=repairability,
        description=description,
        reason_code=reason_code,
        block_ids=cue.block_ids,
        evidence_ids=cue.evidence_ids,
        matched_terms=cue.matched_terms,
        confidence=cue.confidence,
        suggested_event_types=cue.suggested_event_types,
        supporting_span_ids=span_ids,
        supporting_observation_ids=observation_ids,
        supporting_party_ids=party_ids,
        supporting_cohort_ids=cohort_ids,
    )


def _build_summary(records: list[CoverageCheckRecordV2]) -> CoverageSummary:
    issue_records = [record for record in records if record.severity != "info"]
    counter = Counter(record.cue_family for record in issue_records)
    error_count = sum(1 for record in issue_records if record.severity == "error")
    warning_count = sum(1 for record in issue_records if record.severity == "warning")
    return CoverageSummary(
        status="fail" if error_count > 0 else "pass",
        finding_count=len(issue_records),
        error_count=error_count,
        warning_count=warning_count,
        counts_by_cue_family=dict(counter),
    )


def run_coverage_v2(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    """Run deterministic source coverage against canonical v2 observation artifacts."""
    paths = build_skill_paths(deal_slug, project_root=project_root)
    artifacts = load_observation_artifacts(paths, mode="canonical")
    blocks = load_chronology_blocks(paths.chronology_blocks_path)
    evidence_items = load_evidence_items(paths.evidence_items_path)
    cues = build_coverage_cues(evidence_items, blocks)
    records = [
        _build_record(cue, artifacts)
        for cue in cues
        if severity_for_cue(cue) is not None
    ]
    summary = _build_summary(records)

    ensure_output_directories(paths)
    _write_json(paths.coverage_v2_findings_path, CoverageFindingsArtifactV2(findings=records))
    _write_json(paths.coverage_v2_summary_path, summary)
    return 1 if summary.status == "fail" else 0
