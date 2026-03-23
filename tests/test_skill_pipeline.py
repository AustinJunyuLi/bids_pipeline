from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from skill_pipeline import cli
from skill_pipeline.core.config import PROJECT_ROOT
from skill_pipeline.core.paths import build_skill_paths, ensure_output_directories


@pytest.mark.parametrize("command", ["deal-agent", "source-discover", "canonicalize"])
def test_skill_cli_rejects_removed_non_production_commands(command: str) -> None:
    parser = cli.build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args([command, "--deal", "imprivata"])


def test_build_skill_paths_only_includes_live_materialize_and_repair_outputs(
    tmp_path: Path,
) -> None:
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    ensure_output_directories(paths)

    assert (
        paths.materialize_dir
        == tmp_path / "data" / "skill" / "imprivata" / "materialize"
    )
    assert paths.materialized_actors_path == paths.materialize_dir / "actors.json"
    assert paths.materialized_events_path == paths.materialize_dir / "events.json"
    assert paths.materialized_spans_path == paths.materialize_dir / "spans.json"
    assert paths.materialize_log_path == paths.materialize_dir / "materialize_log.json"
    assert paths.repair_dir == tmp_path / "data" / "skill" / "imprivata" / "repair"
    assert paths.repair_log_path == paths.repair_dir / "repair_log.json"
    assert (
        paths.omission_findings_path
        == tmp_path
        / "data"
        / "skill"
        / "imprivata"
        / "coverage"
        / "omission_findings.json"
    )
    assert paths.materialize_dir.is_dir()
    assert paths.repair_dir.is_dir()
    assert not hasattr(paths, "canonicalize_dir")
    assert not hasattr(paths, "canonicalize_log_path")
    assert not hasattr(paths, "spans_path")
    assert not (tmp_path / "data" / "skill" / "imprivata" / "canonicalize").exists()


def test_skill_pipeline_exports_only_live_artifact_loader_module() -> None:
    package_module = importlib.import_module("skill_pipeline")
    artifacts_module = importlib.import_module("skill_pipeline.core.artifacts")
    package_path = Path(next(iter(package_module.__path__)))

    assert hasattr(artifacts_module, "LoadedArtifacts")
    assert hasattr(artifacts_module, "load_artifacts")
    assert Path(artifacts_module.__file__) == package_path / "core" / "artifacts.py"
    assert not (package_path / "extract_artifacts.py").exists()


def test_default_project_root_points_at_repo_root() -> None:
    assert PROJECT_ROOT == Path(__file__).resolve().parents[1]
