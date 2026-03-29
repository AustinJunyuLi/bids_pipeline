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
    mode: Literal["quote_first", "canonical"]
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


class MixedSchemaError(ValueError):
    pass


def load_extract_artifacts(paths: SkillPathSet) -> LoadedExtractArtifacts:
    actors_payload = _read_json(paths.actors_raw_path)
    events_payload = _read_json(paths.events_raw_path)
    actors_canonical = _payload_has_span_ids(actors_payload, "actors") or _payload_has_span_ids(
        actors_payload,
        "count_assertions",
    )
    events_canonical = _payload_has_span_ids(events_payload, "events")

    if actors_canonical != events_canonical:
        actors_mode = "canonical" if actors_canonical else "quote_first"
        events_mode = "canonical" if events_canonical else "quote_first"
        raise MixedSchemaError(
            f"Mixed extract schema modes: actors are {actors_mode} but events are {events_mode}"
        )

    if actors_canonical or events_canonical:
        if not paths.spans_path.exists():
            raise FileNotFoundError(
                f"Missing required canonical sidecar: {paths.spans_path}"
            )
        return LoadedExtractArtifacts(
            mode="canonical",
            raw_actors=None,
            raw_events=None,
            actors=SkillActorsArtifact.model_validate(actors_payload),
            events=SkillEventsArtifact.model_validate(events_payload),
            spans=SpanRegistryArtifact.model_validate(_read_json(paths.spans_path)),
        )

    if "quotes" in actors_payload or "quotes" in events_payload:
        return LoadedExtractArtifacts(
            mode="quote_first",
            raw_actors=RawSkillActorsArtifact.model_validate(actors_payload),
            raw_events=RawSkillEventsArtifact.model_validate(events_payload),
            actors=None,
            events=None,
            spans=None,
        )

    raise ValueError(
        "Unrecognized extract artifact format. "
        "Expected quote-first format (top-level 'quotes' key) or canonical format "
        "(evidence_span_ids). Legacy evidence_refs format is no longer supported."
    )


def _payload_has_span_ids(payload: dict, key: str) -> bool:
    for item in payload.get(key, []):
        if "evidence_span_ids" in item:
            return True
    return False


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
