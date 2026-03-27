from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = REPO_ROOT / ".claude" / "skills"
TARGET_DIRS = (
    REPO_ROOT / ".codex" / "skills",
    REPO_ROOT / ".cursor" / "skills",
)


def _collect_source_files(source_dir: Path) -> dict[Path, bytes]:
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Canonical skill source directory does not exist: {source_dir}")

    files: dict[Path, bytes] = {}
    for path in sorted(source_dir.rglob("*")):
        if path.is_dir() or "__pycache__" in path.parts:
            continue
        relative_path = path.relative_to(source_dir)
        files[relative_path] = path.read_bytes()

    if not files:
        raise ValueError(f"Canonical skill source directory is empty: {source_dir}")
    return files


def _parse_skill_descriptions(source_dir: Path) -> list[tuple[str, str]]:
    skills: list[tuple[str, str]] = []
    for skill_dir in sorted(path for path in source_dir.iterdir() if path.is_dir()):
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            raise FileNotFoundError(f"Missing SKILL.md in canonical skill directory: {skill_dir}")
        description = _extract_front_matter_field(skill_file.read_text(encoding="utf-8"), "description")
        skills.append((skill_dir.name, description or "No description provided."))
    return skills


def _extract_front_matter_field(text: str, field_name: str) -> str | None:
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return None

    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            return None
        prefix = f"{field_name}:"
        if stripped.startswith(prefix):
            return stripped[len(prefix) :].strip()
    return None


def _render_readme(skills: list[tuple[str, str]]) -> bytes:
    lines = [
        "# Skills",
        "",
        "Derived mirror of `.claude/skills/` for Codex.",
        "",
        "| Skill | Description |",
        "|---|---|",
    ]
    for name, description in skills:
        lines.append(f"| `{name}` | {description} |")
    lines.extend(
        [
            "",
            "Refresh this mirror with `python scripts/sync_skill_mirrors.py`.",
            "",
        ]
    )
    return "\n".join(lines).encode("utf-8")


def build_expected_tree(source_dir: Path, target_dir: Path) -> dict[Path, bytes]:
    expected_files = _collect_source_files(source_dir)
    if target_dir.parent.name == ".codex" and target_dir.name == "skills":
        expected_files[Path("README.md")] = _render_readme(_parse_skill_descriptions(source_dir))
    return expected_files


def check_target(source_dir: Path, target_dir: Path) -> list[str]:
    expected_files = build_expected_tree(source_dir, target_dir)
    actual_files: dict[Path, bytes] = {}

    if target_dir.exists():
        for path in sorted(target_dir.rglob("*")):
            if path.is_dir() or "__pycache__" in path.parts:
                continue
            actual_files[path.relative_to(target_dir)] = path.read_bytes()

    issues: list[str] = []
    for relative_path in sorted(expected_files):
        if relative_path not in actual_files:
            issues.append(f"{target_dir}: missing {relative_path.as_posix()}")
            continue
        if actual_files[relative_path] != expected_files[relative_path]:
            issues.append(f"{target_dir}: content drift in {relative_path.as_posix()}")

    for relative_path in sorted(actual_files):
        if relative_path not in expected_files:
            issues.append(f"{target_dir}: unexpected file {relative_path.as_posix()}")

    return issues


def sync_target(source_dir: Path, target_dir: Path) -> None:
    expected_files = build_expected_tree(source_dir, target_dir)
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    for relative_path, content in expected_files.items():
        destination = target_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync `.codex/skills` and `.cursor/skills` from `.claude/skills`."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify mirrors are already in sync without modifying files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    issues: list[str] = []

    if args.check:
        for target_dir in TARGET_DIRS:
            issues.extend(check_target(SOURCE_DIR, target_dir))
        if issues:
            for issue in issues:
                print(issue, file=sys.stderr)
            return 1
        print("Skill mirrors are in sync.")
        return 0

    for target_dir in TARGET_DIRS:
        sync_target(SOURCE_DIR, target_dir)
    print("Synced skill mirrors from .claude/skills.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
