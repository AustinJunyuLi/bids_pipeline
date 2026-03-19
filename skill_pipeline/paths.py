from __future__ import annotations

from pathlib import Path

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.models import SkillPathSet


def build_skill_paths(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> SkillPathSet:
    data_dir = project_root / "data"
    deals_root = data_dir / "deals"
    skill_data_root = data_dir / "skill"
    raw_root = project_root / "raw"
    source_dir = deals_root / deal_slug / "source"
    skill_root = skill_data_root / deal_slug
    extract_dir = skill_root / "extract"
    check_dir = skill_root / "check"
    verify_dir = skill_root / "verify"
    enrich_dir = skill_root / "enrich"
    export_dir = skill_root / "export"
    canonicalize_dir = skill_root / "canonicalize"
    return SkillPathSet(
        project_root=project_root,
        data_dir=data_dir,
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
        enrich_dir=enrich_dir,
        export_dir=export_dir,
        actors_raw_path=extract_dir / "actors_raw.json",
        events_raw_path=extract_dir / "events_raw.json",
        check_report_path=check_dir / "check_report.json",
        verification_log_path=verify_dir / "verification_log.json",
        verification_findings_path=verify_dir / "verification_findings.json",
        enrichment_path=enrich_dir / "enrichment.json",
        deterministic_enrichment_path=enrich_dir / "deterministic_enrichment.json",
        deal_events_path=export_dir / "deal_events.csv",
        canonicalize_dir=canonicalize_dir,
        canonicalize_log_path=canonicalize_dir / "canonicalize_log.json",
    )


def ensure_output_directories(paths: SkillPathSet) -> None:
    paths.extract_dir.mkdir(parents=True, exist_ok=True)
    paths.check_dir.mkdir(parents=True, exist_ok=True)
    paths.verify_dir.mkdir(parents=True, exist_ok=True)
    paths.enrich_dir.mkdir(parents=True, exist_ok=True)
    paths.export_dir.mkdir(parents=True, exist_ok=True)
    paths.canonicalize_dir.mkdir(parents=True, exist_ok=True)


def missing_required_inputs(paths: SkillPathSet) -> list[Path]:
    required = [
        paths.chronology_blocks_path,
        paths.evidence_items_path,
        paths.document_registry_path,
    ]
    return [path for path in required if not path.exists()]
