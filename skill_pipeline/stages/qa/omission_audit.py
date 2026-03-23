"""LLM omission audit over uncovered chronology blocks."""

from __future__ import annotations

import json
from pathlib import Path

from skill_pipeline.core.artifacts import load_artifacts
from skill_pipeline.core.config import PROJECT_ROOT
from skill_pipeline.core.llm import invoke_structured
from skill_pipeline.schemas.runtime import CoverageFindingsArtifact
from skill_pipeline.core.loaders import load_chronology_blocks
from skill_pipeline.core.paths import build_skill_paths, ensure_output_directories
from skill_pipeline.schemas.source import ChronologyBlock
from skill_pipeline.core.prompts import build_omission_audit_prompt


def _load_coverage_findings(path: Path) -> CoverageFindingsArtifact:
    return CoverageFindingsArtifact.model_validate(
        json.loads(path.read_text(encoding="utf-8"))
    )


def _covered_block_ids(paths) -> set[str]:
    artifacts = load_artifacts(paths)
    covered: set[str] = set()
    for span in artifacts.spans.spans:
        covered.update(span.block_ids)
    return covered


def _render_blocks(blocks: list[ChronologyBlock]) -> str:
    return "\n".join(
        f"{block.block_id} [L{block.start_line}-L{block.end_line}]: "
        f"{(block.clean_text or block.raw_text).strip()}"
        for block in blocks
    )


def run_omission_audit(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    paths = build_skill_paths(deal_slug, project_root=project_root)

    if not paths.materialized_actors_path.exists():
        raise FileNotFoundError(
            f"Missing required input: {paths.materialized_actors_path}"
        )
    if not paths.materialized_events_path.exists():
        raise FileNotFoundError(
            f"Missing required input: {paths.materialized_events_path}"
        )
    if not paths.chronology_blocks_path.exists():
        raise FileNotFoundError(
            f"Missing required input: {paths.chronology_blocks_path}"
        )
    if not paths.coverage_findings_path.exists():
        raise FileNotFoundError(
            f"Missing required input: {paths.coverage_findings_path}"
        )

    blocks = load_chronology_blocks(paths.chronology_blocks_path)
    covered_block_ids = _covered_block_ids(paths)
    uncovered_blocks = [
        block for block in blocks if block.block_id not in covered_block_ids
    ]

    ensure_output_directories(paths)
    if not uncovered_blocks:
        empty = CoverageFindingsArtifact(findings=[])
        paths.omission_findings_path.write_text(
            empty.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return 0

    coverage_findings = _load_coverage_findings(paths.coverage_findings_path)
    system_prompt, user_message = build_omission_audit_prompt(
        uncovered_blocks=_render_blocks(uncovered_blocks),
        coverage_findings=json.dumps(
            coverage_findings.model_dump(mode="json"),
            indent=2,
        ),
    )
    omission_findings = invoke_structured(
        system_prompt=system_prompt,
        user_message=user_message,
        output_model=CoverageFindingsArtifact,
    )
    paths.omission_findings_path.write_text(
        omission_findings.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return 1 if any(f.severity == "error" for f in omission_findings.findings) else 0
