from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.extract_artifacts import load_extract_artifacts
from skill_pipeline.models import (
    CheckStageSummary,
    CoverageStageSummary,
    CoverageSummary,
    DealAgentSummary,
    DeterministicEnrichmentArtifact,
    EnrichStageSummary,
    ExportStageSummary,
    ExtractStageSummary,
    SkillCheckReport,
    SkillEnrichmentArtifact,
    SkillVerificationLog,
    StageStatus,
    VerifyStageSummary,
)
from skill_pipeline.source_validation import (
    load_chronology_blocks,
    load_document_registry,
    load_evidence_items,
    validate_frozen_document,
)
from skill_pipeline.paths import build_skill_paths, ensure_output_directories, missing_required_inputs
from skill_pipeline.seeds import load_seed_entry


def run_deal_agent(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> DealAgentSummary:
    paths = build_skill_paths(deal_slug, project_root=project_root)
    seed = load_seed_entry(deal_slug, seeds_path=paths.seeds_path)

    missing_inputs = missing_required_inputs(paths)
    if missing_inputs:
        missing_text = ", ".join(str(path) for path in missing_inputs)
        raise FileNotFoundError(f"Missing required skill inputs: {missing_text}")
    _validate_shared_inputs(paths)

    ensure_output_directories(paths)

    return DealAgentSummary(
        deal_slug=deal_slug,
        seed=seed,
        paths=paths,
        extract=_summarize_extract(paths),
        check=_summarize_check(paths),
        coverage=_summarize_coverage(paths),
        verify=_summarize_verify(paths),
        enrich=_summarize_enrich(paths),
        export=_summarize_export(paths),
    )


def _summarize_extract(paths) -> ExtractStageSummary:
    if not paths.actors_raw_path.exists() or not paths.events_raw_path.exists():
        return ExtractStageSummary(status=StageStatus.MISSING)

    try:
        artifacts = load_extract_artifacts(paths)
    except (FileNotFoundError, ValidationError, ValueError, json.JSONDecodeError):
        return ExtractStageSummary(status=StageStatus.FAIL)
    actors = artifacts.raw_actors.actors if artifacts.mode == "legacy" else artifacts.actors.actors
    events = artifacts.raw_events.events if artifacts.mode == "legacy" else artifacts.events.events
    actor_count = len(actors)
    event_count = len(events)
    proposal_count = sum(event.event_type == "proposal" for event in events)
    status = StageStatus.PASS if actor_count > 0 and event_count > 0 else StageStatus.FAIL
    return ExtractStageSummary(
        status=status,
        actor_count=actor_count,
        event_count=event_count,
        proposal_count=proposal_count,
    )


def _summarize_check(paths) -> CheckStageSummary:
    if not paths.check_report_path.exists():
        return CheckStageSummary(status=StageStatus.MISSING)

    try:
        report = SkillCheckReport.model_validate(_read_json(paths.check_report_path))
    except (ValidationError, json.JSONDecodeError):
        return CheckStageSummary(status=StageStatus.FAIL)
    status = StageStatus.PASS if report.summary.status == "pass" else StageStatus.FAIL
    return CheckStageSummary(
        status=status,
        blocker_count=report.summary.blocker_count,
        warning_count=report.summary.warning_count,
    )


def _summarize_coverage(paths) -> CoverageStageSummary:
    if not paths.coverage_summary_path.exists():
        return CoverageStageSummary(status=StageStatus.MISSING)

    try:
        summary = CoverageSummary.model_validate(_read_json(paths.coverage_summary_path))
    except (ValidationError, json.JSONDecodeError):
        return CoverageStageSummary(status=StageStatus.FAIL)
    status = StageStatus.PASS if summary.status == "pass" else StageStatus.FAIL
    return CoverageStageSummary(
        status=status,
        error_count=summary.error_count,
        warning_count=summary.warning_count,
    )


def _summarize_verify(paths) -> VerifyStageSummary:
    if not paths.verification_log_path.exists():
        return VerifyStageSummary(status=StageStatus.MISSING)

    try:
        log = SkillVerificationLog.model_validate(_read_json(paths.verification_log_path))
    except (ValidationError, json.JSONDecodeError):
        return VerifyStageSummary(status=StageStatus.FAIL)
    status = StageStatus.PASS if log.summary.status == "pass" else StageStatus.FAIL
    return VerifyStageSummary(
        status=status,
        round_1_errors=log.summary.round_1_errors,
        fixes_applied=log.summary.fixes_applied,
        round_2_status=log.round_2.status,
    )


def _summarize_enrich(paths) -> EnrichStageSummary:
    if paths.enrichment_path.exists():
        try:
            enrichment = SkillEnrichmentArtifact.model_validate(_read_json(paths.enrichment_path))
        except (ValidationError, json.JSONDecodeError):
            return EnrichStageSummary(status=StageStatus.FAIL)
        formal_bid_count = sum(
            classification.label == "Formal"
            for classification in enrichment.bid_classifications.values()
        )
        informal_bid_count = sum(
            classification.label == "Informal"
            for classification in enrichment.bid_classifications.values()
        )
        return EnrichStageSummary(
            status=StageStatus.PASS,
            cycle_count=len(enrichment.cycles),
            formal_bid_count=formal_bid_count,
            informal_bid_count=informal_bid_count,
            initiation_judgment_type=enrichment.initiation_judgment.type,
            review_flags_count=len(enrichment.review_flags),
        )

    if paths.deterministic_enrichment_path.exists():
        try:
            enrichment = DeterministicEnrichmentArtifact.model_validate(
                _read_json(paths.deterministic_enrichment_path)
            )
        except (ValidationError, json.JSONDecodeError):
            return EnrichStageSummary(status=StageStatus.FAIL)
        formal_bid_count = sum(
            classification.label == "Formal"
            for classification in enrichment.bid_classifications.values()
        )
        informal_bid_count = sum(
            classification.label == "Informal"
            for classification in enrichment.bid_classifications.values()
        )
        return EnrichStageSummary(
            status=StageStatus.PASS,
            cycle_count=len(enrichment.cycles),
            formal_bid_count=formal_bid_count,
            informal_bid_count=informal_bid_count,
            initiation_judgment_type=None,
            review_flags_count=0,
        )

    return EnrichStageSummary(status=StageStatus.MISSING)


def _summarize_export(paths) -> ExportStageSummary:
    if not paths.deal_events_path.exists():
        return ExportStageSummary(status=StageStatus.MISSING, output_path=paths.deal_events_path)
    lines = [
        line
        for line in paths.deal_events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(lines) <= 1:
        return ExportStageSummary(status=StageStatus.FAIL, output_path=paths.deal_events_path)
    return ExportStageSummary(status=StageStatus.PASS, output_path=paths.deal_events_path)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_shared_inputs(paths) -> None:
    load_chronology_blocks(paths.chronology_blocks_path)
    load_evidence_items(paths.evidence_items_path)
    registry = load_document_registry(paths.document_registry_path)
    for document in registry.documents:
        validate_frozen_document(
            document,
            project_root=paths.project_root,
            deal_slug=paths.deal_slug,
        )
