"""LLM interpretive enrichment layered on deterministic enrich-core output."""

from __future__ import annotations

import json
from pathlib import Path

from skill_pipeline.core.artifacts import load_artifacts
from skill_pipeline.core.config import PROJECT_ROOT
from skill_pipeline.core.llm import invoke_structured
from skill_pipeline.schemas.runtime import (
    AdvisoryVerificationRecord,
    CountReconciliationRecord,
    DropoutClassification,
    InitiationJudgment,
    SkillEnrichmentArtifact,
    SkillModel,
)
from skill_pipeline.core.loaders import read_json
from skill_pipeline.core.paths import build_skill_paths, ensure_output_directories
from skill_pipeline.core.prompts import build_enrich_interpret_prompt


class DropoutClassificationsOutput(SkillModel):
    dropout_classifications: dict[str, DropoutClassification]


class AdvisoryVerificationOutput(SkillModel):
    advisory_verification: dict[str, AdvisoryVerificationRecord]


class CountReconciliationOutput(SkillModel):
    count_reconciliation: list[CountReconciliationRecord]


def _load_context(paths) -> str:
    artifacts = load_artifacts(paths)
    source_text = paths.chronology_blocks_path.read_text(encoding="utf-8").strip()
    deterministic = read_json(paths.deterministic_enrichment_path)
    return (
        "<materialized_actors>\n"
        f"{artifacts.actors.model_dump_json(indent=2)}\n"
        "</materialized_actors>\n\n"
        "<materialized_events>\n"
        f"{artifacts.events.model_dump_json(indent=2)}\n"
        "</materialized_events>\n\n"
        "<deterministic_enrichment>\n"
        f"{json.dumps(deterministic, indent=2)}\n"
        "</deterministic_enrichment>\n\n"
        "<chronology_blocks>\n"
        f"{source_text}\n"
        "</chronology_blocks>"
    )


def _build_review_flags(
    advisory_verification: dict[str, AdvisoryVerificationRecord],
    count_reconciliation: list[CountReconciliationRecord],
) -> list[str]:
    flags: list[str] = []
    for actor_id, record in advisory_verification.items():
        if record.verified:
            continue
        if record.advised_actor_id is None:
            flags.append(f"advisory_missing_link:{actor_id}")
        else:
            flags.append(f"advisory_mismatch:{actor_id}")

    for index, record in enumerate(count_reconciliation):
        if record.classification == "unresolved":
            flags.append(f"count_reconciliation_unresolved:{index}")

    return flags


def run_enrich_interpret(
    deal_slug: str,
    *,
    project_root: Path = PROJECT_ROOT,
) -> int:
    paths = build_skill_paths(deal_slug, project_root=project_root)
    if not paths.materialized_actors_path.exists():
        raise FileNotFoundError(
            f"Missing required input: {paths.materialized_actors_path}"
        )
    if not paths.materialized_events_path.exists():
        raise FileNotFoundError(
            f"Missing required input: {paths.materialized_events_path}"
        )
    if not paths.deterministic_enrichment_path.exists():
        raise FileNotFoundError(
            f"Missing required input: {paths.deterministic_enrichment_path}"
        )
    if not paths.chronology_blocks_path.exists():
        raise FileNotFoundError(
            f"Missing required input: {paths.chronology_blocks_path}"
        )

    context = _load_context(paths)
    deterministic = read_json(paths.deterministic_enrichment_path)

    dropout_system, dropout_user = build_enrich_interpret_prompt(
        "dropout classification",
        context,
    )
    dropout_output = invoke_structured(
        system_prompt=dropout_system,
        user_message=dropout_user,
        output_model=DropoutClassificationsOutput,
    )

    initiation_system, initiation_user = build_enrich_interpret_prompt(
        "initiation judgment",
        context,
    )
    initiation_output = invoke_structured(
        system_prompt=initiation_system,
        user_message=initiation_user,
        output_model=InitiationJudgment,
    )

    advisory_system, advisory_user = build_enrich_interpret_prompt(
        "advisory verification",
        context,
    )
    advisory_output = invoke_structured(
        system_prompt=advisory_system,
        user_message=advisory_user,
        output_model=AdvisoryVerificationOutput,
    )

    count_system, count_user = build_enrich_interpret_prompt(
        "count reconciliation",
        context,
    )
    count_output = invoke_structured(
        system_prompt=count_system,
        user_message=count_user,
        output_model=CountReconciliationOutput,
    )

    review_flags = _build_review_flags(
        advisory_output.advisory_verification,
        count_output.count_reconciliation,
    )
    final_payload = {
        **deterministic,
        "dropout_classifications": dropout_output.dropout_classifications,
        "initiation_judgment": initiation_output,
        "advisory_verification": advisory_output.advisory_verification,
        "count_reconciliation": count_output.count_reconciliation,
        "review_flags": review_flags,
    }
    artifact = SkillEnrichmentArtifact.model_validate(final_payload)

    ensure_output_directories(paths)
    paths.enrichment_path.write_text(
        artifact.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return 0
