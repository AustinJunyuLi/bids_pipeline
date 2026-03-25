from __future__ import annotations

from pathlib import Path
import subprocess
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "sync_skill_mirrors.py"


def _run(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--project-root", str(repo_root), *args],
        capture_output=True,
        check=False,
        cwd=PROJECT_ROOT,
        text=True,
    )


def _write(path: Path, text: str, *, newline: str = "\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline=newline)


def _relative_files(root: Path) -> set[str]:
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_sync_skill_mirrors_copies_canonical_tree_and_prunes_stale_files(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    source_root = repo_root / ".claude" / "skills"
    codex_root = repo_root / ".codex" / "skills"
    cursor_root = repo_root / ".cursor" / "skills"

    _write(source_root / "README.md", "# Canonical\n")
    _write(source_root / "deal-agent" / "SKILL.md", "deal-agent\n")
    _write(codex_root / "README.md", "# Old\r\n", newline="\r\n")
    _write(codex_root / "stale.md", "remove me\n")

    result = _run(repo_root)

    assert result.returncode == 0, result.stderr or result.stdout
    expected_files = _relative_files(source_root)
    assert _relative_files(codex_root) == expected_files
    assert _relative_files(cursor_root) == expected_files
    assert b"\r\n" not in (codex_root / "README.md").read_bytes()
    assert b"\r\n" not in (cursor_root / "README.md").read_bytes()
    assert not (codex_root / "stale.md").exists()


def test_check_skill_mirrors_reports_direct_edits(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    source_root = repo_root / ".claude" / "skills"
    codex_root = repo_root / ".codex" / "skills"

    _write(source_root / "README.md", "# Canonical\n")
    _write(source_root / "deal-agent" / "SKILL.md", "deal-agent\n")
    sync_result = _run(repo_root)
    assert sync_result.returncode == 0, sync_result.stderr or sync_result.stdout

    _write(codex_root / "deal-agent" / "SKILL.md", "local drift\n")
    check_result = _run(repo_root, "--check")

    assert check_result.returncode == 1
    assert "content drift in deal-agent/SKILL.md" in check_result.stdout


def test_repo_skill_mirrors_match_canonical_tree() -> None:
    result = _run(PROJECT_ROOT, "--check")

    assert result.returncode == 0, result.stderr or result.stdout
