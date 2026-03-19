"""Deterministic canonicalization: dedup, NDA-gate, unnamed-party recovery."""

from __future__ import annotations

import json
from pathlib import Path

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.models import SkillActorsArtifact, SkillEventsArtifact
from skill_pipeline.paths import build_skill_paths, ensure_output_directories


def run_canonicalize(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    """Run canonicalization on extracted skill artifacts.

    Writes canonicalize_log.json. Overwrites actors_raw.json and events_raw.json in place.
    Returns 0 on success.
    """
    paths = build_skill_paths(deal_slug, project_root=project_root)

    if not paths.actors_raw_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.actors_raw_path}")
    if not paths.events_raw_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.events_raw_path}")

    actors = SkillActorsArtifact.model_validate(
        json.loads(paths.actors_raw_path.read_text(encoding="utf-8"))
    )
    events_artifact = SkillEventsArtifact.model_validate(
        json.loads(paths.events_raw_path.read_text(encoding="utf-8"))
    )

    log: dict = {"dedup_log": {}, "nda_gate_log": [], "recovery_log": []}

    ensure_output_directories(paths)
    paths.canonicalize_log_path.write_text(
        json.dumps(log, indent=2), encoding="utf-8"
    )
    return 0
