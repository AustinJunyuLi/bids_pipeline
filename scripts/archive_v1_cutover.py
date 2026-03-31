from __future__ import annotations

import argparse
import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.db_export_v2 import run_db_export_v2
from skill_pipeline.db_load_v2 import run_db_load_v2
from skill_pipeline.paths import (
    build_skill_paths,
    ensure_legacy_directories,
    legacy_v1_reconcile_archive_map,
    legacy_v1_skill_archive_map,
)


README_TEXT = """# Legacy v1 Archive

This directory stores the repository's pre-cutover v1 pipeline outputs.

- Live work now defaults to the v2 observation-graph surface under `data/skill/<slug>/`.
- Archived v1 skill artifacts live under `data/legacy/v1/skill/<slug>/`.
- The pre-cutover mixed DuckDB file is preserved as `pipeline_precutover.duckdb`.
- Use `/deal-agent-legacy` and `/reconcile-alex-legacy` when you need the v1 workflow.
"""


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _discover_cutover_slugs(project_root: Path) -> list[str]:
    skill_root = project_root / "data" / "skill"
    if skill_root.exists():
        discovered = sorted(path.name for path in skill_root.iterdir() if path.is_dir())
        if discovered:
            return discovered

    seeds_path = project_root / "data" / "seeds.csv"
    with seeds_path.open(newline="", encoding="utf-8") as handle:
        return [row["deal_slug"] for row in csv.DictReader(handle)]


def _move_tree_or_file(source: Path, destination: Path) -> bool:
    if source.exists():
        if destination.exists():
            raise FileExistsError(f"Archive destination already exists: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        return True
    return destination.exists()


def _archive_v1_skill_outputs(paths) -> tuple[list[str], list[str]]:
    ensure_legacy_directories(paths)
    archived_directories: list[str] = []
    archived_files: list[str] = []

    for source, destination in legacy_v1_skill_archive_map(paths).items():
        if _move_tree_or_file(source, destination):
            archived_directories.append(destination.relative_to(paths.legacy_v1_root).as_posix())

    for source, destination in legacy_v1_reconcile_archive_map(paths).items():
        if _move_tree_or_file(source, destination):
            archived_files.append(destination.relative_to(paths.legacy_v1_root).as_posix())

    live_reconcile_dir = paths.skill_root / "reconcile"
    if live_reconcile_dir.exists() and not any(live_reconcile_dir.iterdir()):
        live_reconcile_dir.rmdir()

    return archived_directories, archived_files


def _archive_precutover_database(database_path: Path, archive_path: Path) -> bool:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    if archive_path.exists():
        return True
    if not database_path.exists():
        return False
    shutil.copy2(database_path, archive_path)
    return True


def _write_legacy_readme(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text(README_TEXT, encoding="utf-8")


def rebuild_live_v2_database(
    deal_slugs: list[str],
    *,
    project_root: Path = PROJECT_ROOT,
    refresh_exports: bool = True,
) -> None:
    live_database_path = build_skill_paths(deal_slugs[0], project_root=project_root).database_path
    if live_database_path.exists():
        live_database_path.unlink()
    for deal_slug in deal_slugs:
        run_db_load_v2(deal_slug, project_root=project_root)
        if refresh_exports:
            run_db_export_v2(deal_slug, project_root=project_root)


def archive_v1_cutover(
    deal_slugs: list[str],
    *,
    project_root: Path = PROJECT_ROOT,
    rebuild_live_database: bool = True,
    refresh_exports: bool = True,
) -> dict:
    if not deal_slugs:
        raise ValueError("deal_slugs must not be empty")

    per_deal_records: list[dict[str, object]] = []
    archive_database_path = build_skill_paths(deal_slugs[0], project_root=project_root).legacy_v1_database_path
    live_database_path = build_skill_paths(deal_slugs[0], project_root=project_root).database_path
    database_archived = _archive_precutover_database(live_database_path, archive_database_path)

    for deal_slug in deal_slugs:
        paths = build_skill_paths(deal_slug, project_root=project_root)
        archived_directories, archived_files = _archive_v1_skill_outputs(paths)
        per_deal_records.append(
            {
                "deal_slug": deal_slug,
                "archived_directories": archived_directories,
                "archived_files": archived_files,
            }
        )

    if rebuild_live_database:
        rebuild_live_v2_database(
            deal_slugs,
            project_root=project_root,
            refresh_exports=refresh_exports,
        )

    legacy_root = build_skill_paths(deal_slugs[0], project_root=project_root).legacy_v1_root
    _write_legacy_readme(legacy_root)
    manifest = {
        "archive_version": 1,
        "created_at": _now_utc(),
        "project_root": str(project_root),
        "legacy_root": str(legacy_root),
        "database_archive_path": str(archive_database_path),
        "database_archived": database_archived,
        "live_database_rebuilt": rebuild_live_database,
        "live_exports_refreshed": refresh_exports if rebuild_live_database else False,
        "deals": per_deal_records,
    }
    build_skill_paths(deal_slugs[0], project_root=project_root).legacy_v1_manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Archive live v1 skill artifacts into data/legacy/v1 and rebuild the live v2 DuckDB surface.",
    )
    parser.add_argument(
        "--deal",
        action="append",
        dest="deals",
        help="Deal slug to archive. Repeat to scope the cutover; default is every live deal directory under data/skill/.",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--skip-rebuild-live-db",
        action="store_true",
        help="Archive v1 artifacts only; leave data/pipeline.duckdb untouched.",
    )
    parser.add_argument(
        "--skip-refresh-exports",
        action="store_true",
        help="Rebuild the live v2 DuckDB file without re-writing export_v2 CSVs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    deal_slugs = args.deals or _discover_cutover_slugs(args.project_root)
    manifest = archive_v1_cutover(
        deal_slugs,
        project_root=args.project_root,
        rebuild_live_database=not args.skip_rebuild_live_db,
        refresh_exports=not args.skip_refresh_exports,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
