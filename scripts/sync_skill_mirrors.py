from __future__ import annotations

import argparse
from pathlib import Path
import sys


CANONICAL_RELATIVE = Path(".claude/skills")
MIRROR_RELATIVES = (Path(".codex/skills"), Path(".cursor/skills"))


def _normalize_bytes(raw: bytes) -> bytes:
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def _iter_files(root: Path) -> list[Path]:
    if not root.exists():
        raise FileNotFoundError(f"Missing skills directory: {root}")
    return sorted(path.relative_to(root) for path in root.rglob("*") if path.is_file())


def _remove_empty_dirs(root: Path) -> None:
    if not root.exists():
        return
    for directory in sorted((path for path in root.rglob("*") if path.is_dir()), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            continue


def sync_mirror(source_root: Path, mirror_root: Path) -> list[Path]:
    source_files = _iter_files(source_root)
    source_set = set(source_files)
    mirror_files = set(_iter_files(mirror_root)) if mirror_root.exists() else set()
    changed_paths: list[Path] = []

    for relative_path in source_files:
        source_bytes = _normalize_bytes((source_root / relative_path).read_bytes())
        destination = mirror_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)

        if not destination.exists() or destination.read_bytes() != source_bytes:
            destination.write_bytes(source_bytes)
            changed_paths.append(destination)

    for relative_path in sorted(mirror_files - source_set):
        stale_path = mirror_root / relative_path
        stale_path.unlink()
        changed_paths.append(stale_path)

    _remove_empty_dirs(mirror_root)
    return changed_paths


def check_mirror(source_root: Path, mirror_root: Path) -> list[str]:
    source_files = set(_iter_files(source_root))
    mirror_files = set(_iter_files(mirror_root)) if mirror_root.exists() else set()
    issues: list[str] = []

    for relative_path in sorted(source_files - mirror_files):
        issues.append(f"{mirror_root}: missing {relative_path.as_posix()}")
    for relative_path in sorted(mirror_files - source_files):
        issues.append(f"{mirror_root}: unexpected {relative_path.as_posix()}")
    for relative_path in sorted(source_files & mirror_files):
        source_bytes = _normalize_bytes((source_root / relative_path).read_bytes())
        mirror_bytes = _normalize_bytes((mirror_root / relative_path).read_bytes())
        if source_bytes != mirror_bytes:
            issues.append(f"{mirror_root}: content drift in {relative_path.as_posix()}")

    return issues


def sync_all_mirrors(project_root: Path) -> list[Path]:
    source_root = project_root / CANONICAL_RELATIVE
    changed_paths: list[Path] = []
    for mirror_relative in MIRROR_RELATIVES:
        changed_paths.extend(sync_mirror(source_root, project_root / mirror_relative))
    return changed_paths


def check_all_mirrors(project_root: Path) -> list[str]:
    source_root = project_root / CANONICAL_RELATIVE
    issues: list[str] = []
    for mirror_relative in MIRROR_RELATIVES:
        issues.extend(check_mirror(source_root, project_root / mirror_relative))
    return issues


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync .codex/.cursor skill mirrors from .claude.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root containing .claude/.codex/.cursor skill trees.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if any mirror differs from the canonical .claude skill tree.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    project_root = args.project_root.resolve()

    if args.check:
        issues = check_all_mirrors(project_root)
        if issues:
            print("\n".join(issues))
            return 1
        print("Skill mirrors are in sync.")
        return 0

    changed_paths = sync_all_mirrors(project_root)
    if changed_paths:
        print("\n".join(path.relative_to(project_root).as_posix() for path in changed_paths))
    else:
        print("Skill mirrors already in sync.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
