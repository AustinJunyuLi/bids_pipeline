"""Deterministic prompt composition stage.

Loads source artifacts, validates their presence, creates prompt output
directories, and writes a schema-valid manifest stub. This stage stops
before any model invocation and must not import provider SDKs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal
from uuid import uuid4

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.paths import build_skill_paths, ensure_output_directories
from skill_pipeline.pipeline_models.common import PIPELINE_VERSION
from skill_pipeline.pipeline_models.prompt import PromptPacketManifest


def run_compose_prompts(
    deal_slug: str,
    project_root: Path = PROJECT_ROOT,
    *,
    mode: Literal["actors", "events", "all"] = "all",
    chunk_budget: int = 6000,
) -> PromptPacketManifest:
    """Build prompt packet artifacts for a deal.

    Loads chronology_blocks.jsonl and evidence_items.jsonl, validates their
    presence, creates prompt output directories, and writes a manifest stub.

    Args:
        deal_slug: Deal identifier.
        project_root: Repository root.
        mode: Which packet families to compose.
        chunk_budget: Target token budget per chunk window.

    Returns:
        The written PromptPacketManifest.

    Raises:
        FileNotFoundError: If required source artifacts are missing.
    """
    paths = build_skill_paths(deal_slug, project_root=project_root)

    # Validate required source inputs exist
    missing: list[Path] = []
    if not paths.chronology_blocks_path.exists():
        missing.append(paths.chronology_blocks_path)
    if not paths.evidence_items_path.exists():
        missing.append(paths.evidence_items_path)
    if missing:
        missing_names = ", ".join(str(p) for p in missing)
        raise FileNotFoundError(
            f"Missing required source artifacts for compose-prompts: {missing_names}"
        )

    # Ensure output directories exist
    ensure_output_directories(paths)

    # Load source artifacts to confirm they are readable
    blocks_text = paths.chronology_blocks_path.read_text(encoding="utf-8").strip()
    blocks_lines = [line for line in blocks_text.split("\n") if line.strip()] if blocks_text else []
    block_count = len(blocks_lines)

    evidence_text = paths.evidence_items_path.read_text(encoding="utf-8").strip()
    evidence_lines = [line for line in evidence_text.split("\n") if line.strip()] if evidence_text else []
    evidence_count = len(evidence_lines)

    run_id = f"compose-{uuid4().hex[:8]}"

    # Build manifest stub -- packet rendering will be filled in by later plans
    manifest = PromptPacketManifest(
        run_id=run_id,
        pipeline_version=PIPELINE_VERSION,
        deal_slug=deal_slug,
        packets=[],
        asset_files=[],
        notes=[
            f"mode={mode}",
            f"chunk_budget={chunk_budget}",
            f"source_blocks={block_count}",
            f"source_evidence_items={evidence_count}",
        ],
    )

    # Write manifest
    paths.prompt_manifest_path.write_text(
        manifest.model_dump_json(indent=2),
        encoding="utf-8",
    )

    return manifest
