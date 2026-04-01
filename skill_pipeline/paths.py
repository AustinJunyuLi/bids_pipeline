from __future__ import annotations

from pathlib import Path

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.db_schema import DEFAULT_DB_NAME
from skill_pipeline.models import SkillPathSet


def build_skill_paths(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> SkillPathSet:
    data_dir = project_root / "data"
    deals_root = data_dir / "deals"
    skill_data_root = data_dir / "skill"
    raw_root = project_root / "raw"
    source_dir = deals_root / deal_slug / "source"
    skill_root = skill_data_root / deal_slug
    extract_v2_dir = skill_root / "extract_v2"
    check_v2_dir = skill_root / "check_v2"
    coverage_v2_dir = skill_root / "coverage_v2"
    gates_v2_dir = skill_root / "gates_v2"
    derive_dir = skill_root / "derive"
    export_v2_dir = skill_root / "export_v2"
    prompt_v2_dir = skill_root / "prompt_v2"
    return SkillPathSet(
        project_root=project_root,
        data_dir=data_dir,
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
        extract_v2_dir=extract_v2_dir,
        check_v2_dir=check_v2_dir,
        coverage_v2_dir=coverage_v2_dir,
        gates_v2_dir=gates_v2_dir,
        derive_dir=derive_dir,
        export_v2_dir=export_v2_dir,
        prompt_v2_dir=prompt_v2_dir,
        observations_raw_path=extract_v2_dir / "observations_raw.json",
        observations_path=extract_v2_dir / "observations.json",
        spans_v2_path=extract_v2_dir / "spans.json",
        check_v2_report_path=check_v2_dir / "check_report.json",
        coverage_v2_findings_path=coverage_v2_dir / "coverage_findings.json",
        coverage_v2_summary_path=coverage_v2_dir / "coverage_summary.json",
        gates_v2_report_path=gates_v2_dir / "gates_report.json",
        derivations_path=derive_dir / "derivations.json",
        derive_log_path=derive_dir / "derive_log.json",
        literal_observations_path=export_v2_dir / "literal_observations.csv",
        analyst_rows_path=export_v2_dir / "analyst_rows.csv",
        benchmark_rows_expanded_path=export_v2_dir / "benchmark_rows_expanded.csv",
        prompt_v2_packets_dir=prompt_v2_dir / "packets",
        prompt_v2_manifest_path=prompt_v2_dir / "manifest.json",
    )


def ensure_output_directories(paths: SkillPathSet) -> None:
    paths.extract_v2_dir.mkdir(parents=True, exist_ok=True)
    paths.check_v2_dir.mkdir(parents=True, exist_ok=True)
    paths.coverage_v2_dir.mkdir(parents=True, exist_ok=True)
    paths.gates_v2_dir.mkdir(parents=True, exist_ok=True)
    paths.derive_dir.mkdir(parents=True, exist_ok=True)
    paths.export_v2_dir.mkdir(parents=True, exist_ok=True)
    paths.prompt_v2_dir.mkdir(parents=True, exist_ok=True)
    paths.prompt_v2_packets_dir.mkdir(parents=True, exist_ok=True)


def missing_required_inputs(paths: SkillPathSet) -> list[Path]:
    required = [
        paths.chronology_blocks_path,
        paths.evidence_items_path,
        paths.document_registry_path,
    ]
    return [path for path in required if not path.exists()]
