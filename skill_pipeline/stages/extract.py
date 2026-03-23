"""LLM-driven extraction of actors and events from preprocessed source artifacts."""

from __future__ import annotations

from pathlib import Path

from skill_pipeline.core.config import PROJECT_ROOT
from skill_pipeline.core.llm import invoke_structured
from skill_pipeline.schemas.runtime import (
    RawSkillActorsArtifact,
    RawSkillEventsArtifact,
)
from skill_pipeline.core.paths import build_skill_paths, ensure_output_directories
from skill_pipeline.schemas.source import ChronologyBlock, EvidenceItem
from skill_pipeline.core.loaders import load_chronology_blocks, load_evidence_items
from skill_pipeline.core.prompts import build_actor_prompt, build_event_prompt
from skill_pipeline.core.seeds import load_seed_entry


def run_extract(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    paths = build_skill_paths(deal_slug, project_root=project_root)
    if not paths.chronology_blocks_path.exists():
        raise FileNotFoundError(
            f"Missing required input: {paths.chronology_blocks_path}"
        )
    if not paths.evidence_items_path.exists():
        raise FileNotFoundError(f"Missing required input: {paths.evidence_items_path}")

    seed = load_seed_entry(deal_slug, seeds_path=paths.seeds_path)
    blocks = load_chronology_blocks(paths.chronology_blocks_path)
    evidence_items = load_evidence_items(paths.evidence_items_path)
    ensure_output_directories(paths)

    actor_system, actor_user = build_actor_prompt(seed, blocks, evidence_items)
    actors = invoke_structured(
        system_prompt=actor_system,
        user_message=actor_user,
        output_model=RawSkillActorsArtifact,
    )
    if (
        not actors.actors
        and not actors.count_assertions
        and not actors.unresolved_mentions
    ):
        raise ValueError("Actor extraction returned an empty structured payload.")

    event_system, event_user = build_event_prompt(seed, blocks, evidence_items, actors)
    events = invoke_structured(
        system_prompt=event_system,
        user_message=event_user,
        output_model=RawSkillEventsArtifact,
    )
    events = _sanitize_events_output(events)

    paths.actors_raw_path.write_text(actors.model_dump_json(indent=2), encoding="utf-8")
    paths.events_raw_path.write_text(events.model_dump_json(indent=2), encoding="utf-8")
    return 0


def _sanitize_events_output(events: RawSkillEventsArtifact) -> RawSkillEventsArtifact:
    kept_events = []
    exclusions = [exclusion.model_dump(mode="json") for exclusion in events.exclusions]
    for event in events.events:
        if event.event_type == "proposal" and event.whole_company_scope is False:
            exclusions.append(
                {
                    "category": "partial_company_bid",
                    "block_ids": [
                        ref.block_id for ref in event.evidence_refs if ref.block_id
                    ],
                    "explanation": event.summary,
                }
            )
            continue
        if event.event_type == "nda" and event.nda_signed is False:
            exclusions.append(
                {
                    "category": "unsigned_nda",
                    "block_ids": [
                        ref.block_id for ref in event.evidence_refs if ref.block_id
                    ],
                    "explanation": event.summary,
                }
            )
            continue
        kept_events.append(event.model_dump(mode="json"))

    return RawSkillEventsArtifact.model_validate(
        {
            "events": kept_events,
            "exclusions": exclusions,
            "coverage_notes": events.coverage_notes,
        }
    )


