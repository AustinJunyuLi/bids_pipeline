"""LLM-driven repair loop for raw extraction artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from skill_pipeline.stages.qa.check import run_check
from skill_pipeline.core.config import PROJECT_ROOT
from skill_pipeline.stages.qa.coverage import run_coverage
from skill_pipeline.core.llm import invoke_structured
from skill_pipeline.stages.materialize import run_materialize
from skill_pipeline.schemas.runtime import (
    RawSkillActorsArtifact,
    RawSkillEventsArtifact,
    SkillModel,
)
from skill_pipeline.core.loaders import read_json
from skill_pipeline.core.paths import build_skill_paths, ensure_output_directories
from skill_pipeline.core.prompts import build_repair_prompt, render_blocks
from skill_pipeline.schemas.source import ChronologyBlock
from skill_pipeline.stages.qa.verify import run_verify
from pydantic import Field


class RepairPatchArtifact(SkillModel):
    actors_raw: RawSkillActorsArtifact | None = None
    events_raw: RawSkillEventsArtifact | None = None
    repair_notes: list[str] = Field(default_factory=list)


def _load_findings(path: Path, *, source: str) -> list[dict]:
    if not path.exists():
        return []
    payload = read_json(path)
    findings = payload.get("findings", [])
    result: list[dict] = []
    for finding in findings:
        enriched = dict(finding)
        enriched["finding_source"] = source
        result.append(enriched)
    return result


def _load_all_findings(paths) -> list[dict]:
    findings: list[dict] = []
    findings.extend(
        _load_findings(paths.verification_findings_path, source="verification")
    )
    findings.extend(_load_findings(paths.coverage_findings_path, source="coverage"))
    findings.extend(_load_findings(paths.omission_findings_path, source="omission"))
    return findings


def _load_raw_artifacts(
    paths,
) -> tuple[RawSkillActorsArtifact, RawSkillEventsArtifact]:
    if not paths.actors_raw_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.actors_raw_path}")
    if not paths.events_raw_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.events_raw_path}")
    return (
        RawSkillActorsArtifact.model_validate(read_json(paths.actors_raw_path)),
        RawSkillEventsArtifact.model_validate(read_json(paths.events_raw_path)),
    )


def _load_rendered_blocks(path: Path) -> str:
    """Load chronology blocks and render as human-readable text."""
    blocks = [
        ChronologyBlock.model_validate(json.loads(line))
        for line in path.read_text(encoding="utf-8").strip().splitlines()
        if line.strip()
    ]
    return render_blocks(blocks)


def _apply_patches(paths, patches: RepairPatchArtifact) -> None:
    if patches.actors_raw is not None:
        original = RawSkillActorsArtifact.model_validate_json(
            paths.actors_raw_path.read_text(encoding="utf-8")
        )
        if len(patches.actors_raw.actors) < len(original.actors):
            raise ValueError(
                f"Repair dropped actors: {len(original.actors)} → "
                f"{len(patches.actors_raw.actors)}"
            )
        paths.actors_raw_path.write_text(
            patches.actors_raw.model_dump_json(indent=2),
            encoding="utf-8",
        )
    if patches.events_raw is not None:
        original = RawSkillEventsArtifact.model_validate_json(
            paths.events_raw_path.read_text(encoding="utf-8")
        )
        if len(patches.events_raw.events) < len(original.events):
            raise ValueError(
                f"Repair dropped events: {len(original.events)} → "
                f"{len(patches.events_raw.events)}"
            )
        paths.events_raw_path.write_text(
            patches.events_raw.model_dump_json(indent=2),
            encoding="utf-8",
        )


def _write_repair_log(paths, log: dict) -> None:
    ensure_output_directories(paths)
    paths.repair_log_path.write_text(
        json.dumps(log, indent=2),
        encoding="utf-8",
    )


def run_repair(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    """Run the LLM repair loop for at most two rounds."""
    paths = build_skill_paths(deal_slug, project_root=project_root)
    if not paths.chronology_blocks_path.exists():
        raise FileNotFoundError(
            f"Missing required input: {paths.chronology_blocks_path}"
        )

    rounds: list[dict] = []
    filing_context = _load_rendered_blocks(paths.chronology_blocks_path)

    for round_num in range(1, 3):
        findings = _load_all_findings(paths)
        errors = [finding for finding in findings if finding.get("severity") == "error"]
        warnings = [
            finding for finding in findings if finding.get("severity") == "warning"
        ]

        if not errors:
            _write_repair_log(
                paths,
                {
                    "rounds": rounds,
                    "status": "pass",
                    "final_error_count": 0,
                    "final_warning_count": len(warnings),
                },
            )
            return 0

        non_repairable = [
            finding
            for finding in errors
            if finding.get("repairability") == "non_repairable"
        ]
        if non_repairable:
            _write_repair_log(
                paths,
                {
                    "rounds": rounds,
                    "status": "fail",
                    "final_error_count": len(errors),
                    "failure_reason": "non_repairable_errors",
                },
            )
            raise RuntimeError(
                f"Round {round_num}: {len(non_repairable)} non-repairable errors. "
                "Pipeline cannot continue."
            )

        actors_raw, events_raw = _load_raw_artifacts(paths)
        system_prompt, user_message = build_repair_prompt(
            findings=json.dumps(errors, indent=2),
            filing_context=filing_context,
            actors_json=actors_raw.model_dump_json(indent=2),
            events_json=events_raw.model_dump_json(indent=2),
        )
        patches = invoke_structured(
            system_prompt=system_prompt,
            user_message=user_message,
            output_model=RepairPatchArtifact,
        )
        _apply_patches(paths, patches)

        rc = run_materialize(deal_slug, project_root=project_root)
        if rc != 0:
            raise RuntimeError(f"Materialize failed after repair round {round_num}")
        run_check(deal_slug, project_root=project_root)
        run_verify(deal_slug, project_root=project_root)
        run_coverage(deal_slug, project_root=project_root)

        rounds.append(
            {
                "round": round_num,
                "error_count": len(errors),
                "warning_count": len(warnings),
                "repair_notes": list(patches.repair_notes),
            }
        )

    final_findings = _load_all_findings(paths)
    final_errors = [
        finding for finding in final_findings if finding.get("severity") == "error"
    ]
    final_warnings = [
        finding for finding in final_findings if finding.get("severity") == "warning"
    ]
    _write_repair_log(
        paths,
        {
            "rounds": rounds,
            "status": "fail",
            "final_error_count": len(final_errors),
            "final_warning_count": len(final_warnings),
        },
    )
    if final_errors:
        raise RuntimeError(
            f"Repair failed: {len(final_errors)} errors remain after 2 rounds."
        )
    return 0
