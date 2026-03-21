from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from skill_pipeline.models import (
    RawSkillActorsArtifact,
    RawSkillEventsArtifact,
    SkillActorsArtifact,
    SkillEventsArtifact,
    SkillPathSet,
    SpanRecord,
    SpanRegistryArtifact,
)


@dataclass
class LoadedExtractArtifacts:
    mode: Literal["legacy", "canonical"]
    raw_actors: RawSkillActorsArtifact | None
    raw_events: RawSkillEventsArtifact | None
    actors: SkillActorsArtifact | None
    events: SkillEventsArtifact | None
    spans: SpanRegistryArtifact | None

    @property
    def span_index(self) -> dict[str, SpanRecord]:
        if not self.spans:
            return {}
        return {span.span_id: span for span in self.spans.spans}


def load_extract_artifacts(paths: SkillPathSet) -> LoadedExtractArtifacts:
    actors_payload = _read_json(paths.actors_raw_path)
    events_payload = _read_json(paths.events_raw_path)
    canonical = (
        paths.spans_path.exists()
        or _payload_has_span_ids(actors_payload, "actors")
        or _payload_has_span_ids(actors_payload, "count_assertions")
        or _payload_has_span_ids(events_payload, "events")
    )

    if canonical:
        spans_payload = _read_json(paths.spans_path) if paths.spans_path.exists() else {"spans": []}
        return LoadedExtractArtifacts(
            mode="canonical",
            raw_actors=None,
            raw_events=None,
            actors=SkillActorsArtifact.model_validate(actors_payload),
            events=SkillEventsArtifact.model_validate(events_payload),
            spans=SpanRegistryArtifact.model_validate(spans_payload),
        )

    return LoadedExtractArtifacts(
        mode="legacy",
        raw_actors=RawSkillActorsArtifact.model_validate(actors_payload),
        raw_events=RawSkillEventsArtifact.model_validate(events_payload),
        actors=None,
        events=None,
        spans=None,
    )


def _payload_has_span_ids(payload: dict, key: str) -> bool:
    for item in payload.get(key, []):
        if "evidence_span_ids" in item:
            return True
    return False


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
