from __future__ import annotations

import json
from pathlib import Path

from scripts.archive_v1_cutover import archive_v1_cutover
from skill_pipeline.derive import run_derive
from skill_pipeline.paths import build_skill_paths
from tests._v2_validation_fixtures import (
    canonical_observations_payload,
    spans_payload,
    write_v2_validation_reports,
)


def _write_shared_inputs(tmp_path: Path, *, slug: str = "imprivata") -> None:
    data_dir = tmp_path / "data"
    deals_source_dir = data_dir / "deals" / slug / "source"
    raw_dir = tmp_path / "raw" / slug
    deals_source_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    (data_dir / "seeds.csv").write_text(
        (
            "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
            f"{slug},IMPRIVATA INC,THOMA BRAVO LLC,2016-07-13,https://example.com,false\n"
        ),
        encoding="utf-8",
    )
    (deals_source_dir / "chronology_blocks.jsonl").write_text(
        json.dumps(
            {
                "block_id": "B001",
                "document_id": "DOC001",
                "ordinal": 1,
                "start_line": 1,
                "end_line": 1,
                "raw_text": "x",
                "clean_text": "x",
                "is_heading": False,
                "page_break_before": False,
                "page_break_after": False,
                "date_mentions": [],
                "entity_mentions": [],
                "evidence_density": 0,
                "temporal_phase": "other",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (deals_source_dir / "evidence_items.jsonl").write_text("", encoding="utf-8")
    (raw_dir / "document_registry.json").write_text("{}", encoding="utf-8")


def _write_v2_artifacts(tmp_path: Path, *, slug: str = "imprivata") -> Path:
    paths = build_skill_paths(slug, project_root=tmp_path)
    paths.extract_v2_dir.mkdir(parents=True, exist_ok=True)
    paths.observations_path.write_text(
        json.dumps(canonical_observations_payload()),
        encoding="utf-8",
    )
    paths.spans_v2_path.write_text(
        json.dumps(spans_payload()),
        encoding="utf-8",
    )
    write_v2_validation_reports(tmp_path, slug=slug)
    run_derive(slug, project_root=tmp_path)
    return paths.skill_root


def test_archive_v1_cutover_moves_live_v1_outputs_into_legacy_root(tmp_path: Path) -> None:
    _write_shared_inputs(tmp_path)
    skill_root = _write_v2_artifacts(tmp_path)

    for directory in ("extract", "coverage", "export"):
        live_dir = skill_root / directory
        live_dir.mkdir(parents=True, exist_ok=True)
        (live_dir / f"{directory}.txt").write_text(directory, encoding="utf-8")

    reconcile_dir = skill_root / "reconcile"
    reconcile_dir.mkdir(parents=True, exist_ok=True)
    (reconcile_dir / "alex_rows_codex_blind_round2.json").write_text("[]", encoding="utf-8")
    (reconcile_dir / "reconciliation_report_codex_blind_round2.json").write_text(
        "{}",
        encoding="utf-8",
    )
    (reconcile_dir / "reconciliation_report.json").write_text("{}", encoding="utf-8")

    manifest = archive_v1_cutover(
        ["imprivata"],
        project_root=tmp_path,
        rebuild_live_database=False,
        refresh_exports=False,
    )

    legacy_root = tmp_path / "data" / "legacy" / "v1"
    assert (legacy_root / "skill" / "imprivata" / "extract" / "extract.txt").read_text(
        encoding="utf-8"
    ) == "extract"
    assert (legacy_root / "skill" / "imprivata" / "coverage" / "coverage.txt").read_text(
        encoding="utf-8"
    ) == "coverage"
    assert (legacy_root / "skill" / "imprivata" / "export" / "export.txt").read_text(
        encoding="utf-8"
    ) == "export"
    assert not (skill_root / "extract").exists()
    assert not (skill_root / "coverage").exists()
    assert not (skill_root / "export").exists()
    assert not (reconcile_dir / "alex_rows_codex_blind_round2.json").exists()
    assert not (reconcile_dir / "reconciliation_report_codex_blind_round2.json").exists()
    assert (reconcile_dir / "reconciliation_report.json").exists()
    assert (legacy_root / "README.md").exists()
    assert manifest["deals"][0]["deal_slug"] == "imprivata"
    assert (legacy_root / "archive_manifest.json").exists()


def test_archive_v1_cutover_rebuilds_live_v2_database_and_exports(tmp_path: Path) -> None:
    _write_shared_inputs(tmp_path)
    skill_root = _write_v2_artifacts(tmp_path)
    live_database_path = tmp_path / "data" / "pipeline.duckdb"
    live_database_path.parent.mkdir(parents=True, exist_ok=True)
    live_database_path.write_bytes(b"legacy-db-snapshot")

    manifest = archive_v1_cutover(["imprivata"], project_root=tmp_path)

    paths = build_skill_paths("imprivata", project_root=tmp_path)
    archived_database = tmp_path / "data" / "legacy" / "v1" / "pipeline_precutover.duckdb"
    assert archived_database.read_bytes() == b"legacy-db-snapshot"
    assert paths.database_path.exists()
    assert paths.analyst_rows_path.exists()
    assert paths.literal_observations_path.exists()
    assert paths.benchmark_rows_expanded_path.exists()
    assert manifest["database_archived"] is True
    assert manifest["live_database_rebuilt"] is True
    assert manifest["live_exports_refreshed"] is True
