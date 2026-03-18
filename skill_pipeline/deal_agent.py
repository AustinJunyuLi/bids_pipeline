from __future__ import annotations

import json
from pathlib import Path

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.models import (
    DealAgentSummary,
    EnrichStageSummary,
    ExportStageSummary,
    ExtractStageSummary,
    SkillActorsArtifact,
    SkillEnrichmentArtifact,
    SkillEventsArtifact,
    SkillVerificationLog,
    StageStatus,
    VerifyStageSummary,
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

    ensure_output_directories(paths)

    return DealAgentSummary(
        deal_slug=deal_slug,
        seed=seed,
        paths=paths,
        extract=_summarize_extract(paths),
        verify=_summarize_verify(paths),
        enrich=_summarize_enrich(paths),
        export=_summarize_export(paths),
    )


def _summarize_extract(paths) -> ExtractStageSummary:
    if not paths.actors_raw_path.exists() or not paths.events_raw_path.exists():
        return ExtractStageSummary(status=StageStatus.MISSING)

    actors = SkillActorsArtifact.model_validate(_read_json(paths.actors_raw_path))
    events = SkillEventsArtifact.model_validate(_read_json(paths.events_raw_path))
    actor_count = len(actors.actors)
    event_count = len(events.events)
    proposal_count = sum(event.event_type == "proposal" for event in events.events)
    status = StageStatus.PASS if actor_count > 0 and event_count > 0 else StageStatus.FAIL
    return ExtractStageSummary(
        status=status,
        actor_count=actor_count,
        event_count=event_count,
        proposal_count=proposal_count,
    )


def _summarize_verify(paths) -> VerifyStageSummary:
    if not paths.verification_log_path.exists():
        return VerifyStageSummary(status=StageStatus.MISSING)

    log = SkillVerificationLog.model_validate(_read_json(paths.verification_log_path))
    status = StageStatus.PASS if log.summary.status == "pass" else StageStatus.FAIL
    return VerifyStageSummary(
        status=status,
        round_1_errors=log.summary.round_1_errors,
        fixes_applied=log.summary.fixes_applied,
        round_2_status=log.round_2.status,
    )


def _summarize_enrich(paths) -> EnrichStageSummary:
    if not paths.enrichment_path.exists():
        return EnrichStageSummary(status=StageStatus.MISSING)

    enrichment = SkillEnrichmentArtifact.model_validate(_read_json(paths.enrichment_path))
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


def _summarize_export(paths) -> ExportStageSummary:
    if not paths.deal_events_path.exists():
        return ExportStageSummary(status=StageStatus.MISSING, output_path=paths.deal_events_path)
    if paths.deal_events_path.stat().st_size == 0:
        return ExportStageSummary(status=StageStatus.FAIL, output_path=paths.deal_events_path)
    return ExportStageSummary(status=StageStatus.PASS, output_path=paths.deal_events_path)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
