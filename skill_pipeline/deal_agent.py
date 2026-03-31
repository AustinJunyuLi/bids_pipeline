from __future__ import annotations

import csv
import json
from pathlib import Path

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.db_schema import open_pipeline_db
from skill_pipeline.extract_artifacts_v2 import load_observation_artifacts
from skill_pipeline.models import (
    CheckStageSummary,
    CoverageStageSummary,
    CoverageSummary,
    DealAgentSummary,
    DbExportStageSummary,
    DbLoadStageSummary,
    DeriveStageSummary,
    ExportStageSummary,
    ExtractStageSummary,
    GatesStageSummary,
    PromptStageSummary,
    StageStatus,
)
from skill_pipeline.paths import build_skill_paths, ensure_output_directories, missing_required_inputs
from skill_pipeline.pipeline_models.prompt import PromptPacketManifest
from skill_pipeline.seeds import load_seed_entry
from skill_pipeline.models_v2 import DerivedArtifactV2, GateReportV2, SkillCheckReportV2


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
        prompt=_summarize_prompt(paths),
        extract=_summarize_extract(paths),
        check=_summarize_check(paths),
        coverage=_summarize_coverage(paths),
        gates=_summarize_gates(paths),
        derive=_summarize_derive(paths),
        db_load=_summarize_db_load(paths),
        db_export=_summarize_db_export(paths),
        export=_summarize_export(paths),
    )


def _summarize_prompt(paths) -> PromptStageSummary:
    if not paths.prompt_v2_manifest_path.exists():
        return PromptStageSummary(status=StageStatus.MISSING)

    try:
        manifest = PromptPacketManifest.model_validate(_read_json(paths.prompt_v2_manifest_path))
    except Exception:
        return PromptStageSummary(status=StageStatus.FAIL)

    packet_count = len(manifest.packets)
    observation_packet_count = sum(
        1 for packet in manifest.packets if packet.packet_family == "observations_v2"
    )
    status = StageStatus.PASS if packet_count > 0 else StageStatus.FAIL
    return PromptStageSummary(
        status=status,
        packet_count=packet_count,
        observation_packet_count=observation_packet_count,
    )


def _summarize_extract(paths) -> ExtractStageSummary:
    if not paths.observations_raw_path.exists() and not paths.observations_path.exists():
        return ExtractStageSummary(status=StageStatus.MISSING)

    try:
        artifacts = load_observation_artifacts(paths)
    except Exception:
        return ExtractStageSummary(status=StageStatus.FAIL)

    if artifacts.mode == "quote_first":
        raw_artifact = artifacts.raw_artifact
        parties = raw_artifact.parties
        cohorts = raw_artifact.cohorts
        observations = raw_artifact.observations
    else:
        canonical = artifacts.observations
        parties = canonical.parties
        cohorts = canonical.cohorts
        observations = canonical.observations
    party_count = len(parties)
    cohort_count = len(cohorts)
    observation_count = len(observations)
    proposal_count = sum(observation.obs_type == "proposal" for observation in observations)
    status = StageStatus.PASS if party_count > 0 and observation_count > 0 else StageStatus.FAIL
    return ExtractStageSummary(
        status=status,
        party_count=party_count,
        cohort_count=cohort_count,
        observation_count=observation_count,
        proposal_count=proposal_count,
    )


def _summarize_check(paths) -> CheckStageSummary:
    if not paths.check_v2_report_path.exists():
        return CheckStageSummary(status=StageStatus.MISSING)

    try:
        report = SkillCheckReportV2.model_validate(_read_json(paths.check_v2_report_path))
    except Exception:
        return CheckStageSummary(status=StageStatus.FAIL)

    status = StageStatus.PASS if report.summary.status == "pass" else StageStatus.FAIL
    return CheckStageSummary(
        status=status,
        blocker_count=report.summary.blocker_count,
        warning_count=report.summary.warning_count,
    )


def _summarize_coverage(paths) -> CoverageStageSummary:
    if not paths.coverage_v2_summary_path.exists():
        return CoverageStageSummary(status=StageStatus.MISSING)

    try:
        summary = CoverageSummary.model_validate(_read_json(paths.coverage_v2_summary_path))
    except Exception:
        return CoverageStageSummary(status=StageStatus.FAIL)

    status = StageStatus.PASS if summary.status == "pass" else StageStatus.FAIL
    return CoverageStageSummary(
        status=status,
        error_count=summary.error_count,
        warning_count=summary.warning_count,
    )


def _summarize_gates(paths) -> GatesStageSummary:
    if not paths.gates_v2_report_path.exists():
        return GatesStageSummary(status=StageStatus.MISSING)

    try:
        report = GateReportV2.model_validate(_read_json(paths.gates_v2_report_path))
    except Exception:
        return GatesStageSummary(status=StageStatus.FAIL)

    status = StageStatus.PASS if report.summary.status == "pass" else StageStatus.FAIL
    return GatesStageSummary(
        status=status,
        blocker_count=report.summary.blocker_count,
        warning_count=report.summary.warning_count,
    )


def _summarize_derive(paths) -> DeriveStageSummary:
    if not paths.derivations_path.exists():
        return DeriveStageSummary(status=StageStatus.MISSING)

    try:
        derivations = DerivedArtifactV2.model_validate(_read_json(paths.derivations_path))
    except Exception:
        return DeriveStageSummary(status=StageStatus.FAIL)

    phase_count = len(derivations.phases)
    transition_count = len(derivations.transitions)
    analyst_row_count = len(derivations.analyst_rows)
    judgment_count = len(derivations.judgments)
    status = StageStatus.PASS if any(
        count > 0 for count in (phase_count, transition_count, analyst_row_count, judgment_count)
    ) else StageStatus.FAIL
    return DeriveStageSummary(
        status=status,
        phase_count=phase_count,
        transition_count=transition_count,
        analyst_row_count=analyst_row_count,
        judgment_count=judgment_count,
    )


def _summarize_db_load(paths) -> DbLoadStageSummary:
    if not paths.database_path.exists():
        return DbLoadStageSummary(status=StageStatus.MISSING)

    try:
        con = open_pipeline_db(paths.database_path, read_only=True)
    except Exception:
        return DbLoadStageSummary(status=StageStatus.FAIL)

    try:
        try:
            party_rows = _count_deal_rows(con, "v2_parties", paths.deal_slug)
            cohort_rows = _count_deal_rows(con, "v2_cohorts", paths.deal_slug)
            observation_rows = _count_deal_rows(con, "v2_observations", paths.deal_slug)
            derivation_rows = _count_deal_rows(con, "v2_derivations", paths.deal_slug)
            coverage_rows = _count_deal_rows(con, "v2_coverage_checks", paths.deal_slug)
        except Exception:
            return DbLoadStageSummary(status=StageStatus.FAIL)
    finally:
        con.close()

    if all(count == 0 for count in (party_rows, cohort_rows, observation_rows, derivation_rows, coverage_rows)):
        return DbLoadStageSummary(status=StageStatus.MISSING)
    if party_rows == 0 or observation_rows == 0 or derivation_rows == 0:
        return DbLoadStageSummary(
            status=StageStatus.FAIL,
            party_rows=party_rows,
            cohort_rows=cohort_rows,
            observation_rows=observation_rows,
            derivation_rows=derivation_rows,
            coverage_rows=coverage_rows,
        )
    return DbLoadStageSummary(
        status=StageStatus.PASS,
        party_rows=party_rows,
        cohort_rows=cohort_rows,
        observation_rows=observation_rows,
        derivation_rows=derivation_rows,
        coverage_rows=coverage_rows,
    )


def _summarize_db_export(paths) -> DbExportStageSummary:
    if not paths.analyst_rows_path.exists():
        return DbExportStageSummary(
            status=StageStatus.MISSING,
            output_path=paths.analyst_rows_path,
            literal_output_path=paths.literal_observations_path,
            benchmark_output_path=paths.benchmark_rows_expanded_path,
        )

    with paths.analyst_rows_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    if len(rows) < 2:
        return DbExportStageSummary(
            status=StageStatus.FAIL,
            row_count=0,
            output_path=paths.analyst_rows_path,
            literal_output_path=paths.literal_observations_path,
            benchmark_output_path=paths.benchmark_rows_expanded_path,
        )

    row_count = len(rows) - 1
    status = StageStatus.PASS if row_count > 0 else StageStatus.FAIL
    return DbExportStageSummary(
        status=status,
        row_count=row_count,
        output_path=paths.analyst_rows_path,
        literal_output_path=paths.literal_observations_path,
        benchmark_output_path=paths.benchmark_rows_expanded_path,
    )


def _summarize_export(paths) -> ExportStageSummary:
    required_paths = (
        paths.literal_observations_path,
        paths.analyst_rows_path,
        paths.benchmark_rows_expanded_path,
    )
    if any(not path.exists() for path in required_paths):
        return ExportStageSummary(
            status=StageStatus.MISSING,
            output_path=paths.analyst_rows_path,
            literal_output_path=paths.literal_observations_path,
            benchmark_output_path=paths.benchmark_rows_expanded_path,
        )
    if any(path.stat().st_size == 0 for path in required_paths):
        return ExportStageSummary(
            status=StageStatus.FAIL,
            output_path=paths.analyst_rows_path,
            literal_output_path=paths.literal_observations_path,
            benchmark_output_path=paths.benchmark_rows_expanded_path,
        )
    return ExportStageSummary(
        status=StageStatus.PASS,
        output_path=paths.analyst_rows_path,
        literal_output_path=paths.literal_observations_path,
        benchmark_output_path=paths.benchmark_rows_expanded_path,
    )


def _count_deal_rows(con, table_name: str, deal_slug: str) -> int:
    return con.execute(
        f"SELECT COUNT(*) FROM {table_name} WHERE deal_slug = ?",
        [deal_slug],
    ).fetchone()[0]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
