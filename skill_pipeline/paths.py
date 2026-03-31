from __future__ import annotations

from pathlib import Path

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.db_schema import DEFAULT_DB_NAME
from skill_pipeline.models import SkillPathSet

V1_SKILL_ARCHIVE_DIR_NAMES = (
    "canonicalize",
    "check",
    "coverage",
    "enrich",
    "export",
    "extract",
    "gates",
    "prompt",
    "verify",
)

V1_RECONCILE_ARCHIVE_FILE_NAMES = (
    "alex_rows_codex_blind_round2.json",
    "reconciliation_report_codex_blind_round2.json",
)


def build_skill_paths(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> SkillPathSet:
    data_dir = project_root / "data"
    legacy_root = data_dir / "legacy"
    legacy_v1_root = legacy_root / "v1"
    legacy_v1_skill_root = legacy_v1_root / "skill"
    legacy_v1_skill_deal_root = legacy_v1_skill_root / deal_slug
    deals_root = data_dir / "deals"
    skill_data_root = data_dir / "skill"
    raw_root = project_root / "raw"
    source_dir = deals_root / deal_slug / "source"
    skill_root = skill_data_root / deal_slug
    extract_dir = skill_root / "extract"
    check_dir = skill_root / "check"
    verify_dir = skill_root / "verify"
    coverage_dir = skill_root / "coverage"
    gates_dir = skill_root / "gates"
    enrich_dir = skill_root / "enrich"
    export_dir = skill_root / "export"
    extract_v2_dir = skill_root / "extract_v2"
    check_v2_dir = skill_root / "check_v2"
    coverage_v2_dir = skill_root / "coverage_v2"
    gates_v2_dir = skill_root / "gates_v2"
    derive_dir = skill_root / "derive"
    export_v2_dir = skill_root / "export_v2"
    canonicalize_dir = skill_root / "canonicalize"
    prompt_dir = skill_root / "prompt"
    prompt_v2_dir = skill_root / "prompt_v2"
    return SkillPathSet(
        project_root=project_root,
        data_dir=data_dir,
        legacy_root=legacy_root,
        legacy_v1_root=legacy_v1_root,
        legacy_v1_skill_root=legacy_v1_skill_root,
        legacy_v1_skill_deal_root=legacy_v1_skill_deal_root,
        legacy_v1_manifest_path=legacy_v1_root / "archive_manifest.json",
        legacy_v1_database_path=legacy_v1_root / "pipeline_precutover.duckdb",
        database_path=data_dir / DEFAULT_DB_NAME,
        deals_root=deals_root,
        skill_data_root=skill_data_root,
        raw_root=raw_root,
        seeds_path=data_dir / "seeds.csv",
        deal_slug=deal_slug,
        source_dir=source_dir,
        chronology_blocks_path=source_dir / "chronology_blocks.jsonl",
        evidence_items_path=source_dir / "evidence_items.jsonl",
        document_registry_path=raw_root / deal_slug / "document_registry.json",
        skill_root=skill_root,
        extract_dir=extract_dir,
        check_dir=check_dir,
        verify_dir=verify_dir,
        coverage_dir=coverage_dir,
        enrich_dir=enrich_dir,
        export_dir=export_dir,
        extract_v2_dir=extract_v2_dir,
        check_v2_dir=check_v2_dir,
        coverage_v2_dir=coverage_v2_dir,
        gates_v2_dir=gates_v2_dir,
        derive_dir=derive_dir,
        export_v2_dir=export_v2_dir,
        prompt_v2_dir=prompt_v2_dir,
        actors_raw_path=extract_dir / "actors_raw.json",
        events_raw_path=extract_dir / "events_raw.json",
        spans_path=extract_dir / "spans.json",
        observations_raw_path=extract_v2_dir / "observations_raw.json",
        observations_path=extract_v2_dir / "observations.json",
        spans_v2_path=extract_v2_dir / "spans.json",
        check_report_path=check_dir / "check_report.json",
        check_v2_report_path=check_v2_dir / "check_report.json",
        verification_log_path=verify_dir / "verification_log.json",
        verification_findings_path=verify_dir / "verification_findings.json",
        coverage_findings_path=coverage_dir / "coverage_findings.json",
        coverage_summary_path=coverage_dir / "coverage_summary.json",
        coverage_v2_findings_path=coverage_v2_dir / "coverage_findings.json",
        coverage_v2_summary_path=coverage_v2_dir / "coverage_summary.json",
        gates_dir=gates_dir,
        gates_report_path=gates_dir / "gates_report.json",
        gates_v2_report_path=gates_v2_dir / "gates_report.json",
        enrichment_path=enrich_dir / "enrichment.json",
        deterministic_enrichment_path=enrich_dir / "deterministic_enrichment.json",
        derivations_path=derive_dir / "derivations.json",
        derive_log_path=derive_dir / "derive_log.json",
        deal_events_path=export_dir / "deal_events.csv",
        literal_observations_path=export_v2_dir / "literal_observations.csv",
        analyst_rows_path=export_v2_dir / "analyst_rows.csv",
        benchmark_rows_expanded_path=export_v2_dir / "benchmark_rows_expanded.csv",
        canonicalize_dir=canonicalize_dir,
        canonicalize_log_path=canonicalize_dir / "canonicalize_log.json",
        prompt_dir=prompt_dir,
        prompt_packets_dir=prompt_dir / "packets",
        prompt_manifest_path=prompt_dir / "manifest.json",
        prompt_v2_packets_dir=prompt_v2_dir / "packets",
        prompt_v2_manifest_path=prompt_v2_dir / "manifest.json",
    )


def ensure_output_directories(paths: SkillPathSet, *, include_legacy: bool = False) -> None:
    if include_legacy:
        paths.extract_dir.mkdir(parents=True, exist_ok=True)
        paths.check_dir.mkdir(parents=True, exist_ok=True)
        paths.verify_dir.mkdir(parents=True, exist_ok=True)
        paths.coverage_dir.mkdir(parents=True, exist_ok=True)
        paths.gates_dir.mkdir(parents=True, exist_ok=True)
        paths.enrich_dir.mkdir(parents=True, exist_ok=True)
        paths.export_dir.mkdir(parents=True, exist_ok=True)
        paths.canonicalize_dir.mkdir(parents=True, exist_ok=True)
        paths.prompt_dir.mkdir(parents=True, exist_ok=True)
        paths.prompt_packets_dir.mkdir(parents=True, exist_ok=True)
    paths.extract_v2_dir.mkdir(parents=True, exist_ok=True)
    paths.check_v2_dir.mkdir(parents=True, exist_ok=True)
    paths.coverage_v2_dir.mkdir(parents=True, exist_ok=True)
    paths.gates_v2_dir.mkdir(parents=True, exist_ok=True)
    paths.derive_dir.mkdir(parents=True, exist_ok=True)
    paths.export_v2_dir.mkdir(parents=True, exist_ok=True)
    paths.prompt_v2_dir.mkdir(parents=True, exist_ok=True)
    paths.prompt_v2_packets_dir.mkdir(parents=True, exist_ok=True)


def ensure_legacy_directories(paths: SkillPathSet) -> None:
    paths.legacy_v1_root.mkdir(parents=True, exist_ok=True)
    paths.legacy_v1_skill_root.mkdir(parents=True, exist_ok=True)
    paths.legacy_v1_skill_deal_root.mkdir(parents=True, exist_ok=True)


def legacy_v1_skill_archive_map(paths: SkillPathSet) -> dict[Path, Path]:
    return {
        paths.skill_root / dir_name: paths.legacy_v1_skill_deal_root / dir_name
        for dir_name in V1_SKILL_ARCHIVE_DIR_NAMES
    }


def legacy_v1_reconcile_archive_map(paths: SkillPathSet) -> dict[Path, Path]:
    reconcile_dir = paths.skill_root / "reconcile"
    legacy_reconcile_dir = paths.legacy_v1_skill_deal_root / "reconcile"
    return {
        reconcile_dir / file_name: legacy_reconcile_dir / file_name
        for file_name in V1_RECONCILE_ARCHIVE_FILE_NAMES
    }


def missing_required_inputs(paths: SkillPathSet) -> list[Path]:
    required = [
        paths.chronology_blocks_path,
        paths.evidence_items_path,
        paths.document_registry_path,
    ]
    return [path for path in required if not path.exists()]
