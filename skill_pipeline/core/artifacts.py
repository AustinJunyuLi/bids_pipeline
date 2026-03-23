from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from skill_pipeline.core.loaders import read_json
from skill_pipeline.schemas.runtime import (
    SkillActorsArtifact,
    SkillEventsArtifact,
    SkillPathSet,
    SpanRecord,
    SpanRegistryArtifact,
)


@dataclass
class LoadedArtifacts:
    actors: SkillActorsArtifact
    events: SkillEventsArtifact
    spans: SpanRegistryArtifact

    @property
    def span_index(self) -> dict[str, SpanRecord]:
        return {span.span_id: span for span in self.spans.spans}


def load_artifacts(paths: SkillPathSet) -> LoadedArtifacts:
    if not paths.materialized_actors_path.exists():
        raise FileNotFoundError(
            f"Missing materialized artifacts: {paths.materialized_actors_path}. "
            "Run 'skill-pipeline materialize --deal <slug>' first."
        )

    actors_payload = read_json(paths.materialized_actors_path)
    events_payload = read_json(paths.materialized_events_path)
    spans_payload = (
        read_json(paths.materialized_spans_path)
        if paths.materialized_spans_path.exists()
        else {"spans": []}
    )
    return LoadedArtifacts(
        actors=SkillActorsArtifact.model_validate(actors_payload),
        events=SkillEventsArtifact.model_validate(events_payload),
        spans=SpanRegistryArtifact.model_validate(spans_payload),
    )
