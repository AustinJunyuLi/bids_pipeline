from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from pipeline.llm.json_utils import inline_json_refs


@dataclass(slots=True)
class SchemaProfile:
    schema_bytes: int
    optional_param_count: int
    union_param_count: int
    pattern_count: int
    object_count: int
    array_count: int
    max_depth: int


def profile_model_schema(model_cls: type[BaseModel]) -> SchemaProfile:
    schema = inline_json_refs(model_cls.model_json_schema(mode="validation"))
    counters = {
        "optional_param_count": 0,
        "union_param_count": 0,
        "pattern_count": 0,
        "object_count": 0,
        "array_count": 0,
        "max_depth": 0,
    }
    _walk_schema(schema, counters, depth=1)
    return SchemaProfile(
        schema_bytes=len(json.dumps(schema, sort_keys=True)),
        optional_param_count=counters["optional_param_count"],
        union_param_count=counters["union_param_count"],
        pattern_count=counters["pattern_count"],
        object_count=counters["object_count"],
        array_count=counters["array_count"],
        max_depth=counters["max_depth"],
    )


def _walk_schema(node: Any, counters: dict[str, int], *, depth: int) -> None:
    if isinstance(node, dict):
        counters["max_depth"] = max(counters["max_depth"], depth)
        if "pattern" in node:
            counters["pattern_count"] += 1
        if "anyOf" in node or "oneOf" in node:
            counters["union_param_count"] += 1
        if node.get("type") == "object" or "properties" in node:
            counters["object_count"] += 1
            required = set(node.get("required", []))
            for key, child in node.get("properties", {}).items():
                if key not in required:
                    counters["optional_param_count"] += 1
                _walk_schema(child, counters, depth=depth + 1)
        if node.get("type") == "array" or "items" in node:
            counters["array_count"] += 1
            _walk_schema(node.get("items"), counters, depth=depth + 1)
        for key, child in node.items():
            if key in {"properties", "items"}:
                continue
            _walk_schema(child, counters, depth=depth + 1)
        return
    if isinstance(node, list):
        for child in node:
            _walk_schema(child, counters, depth=depth + 1)


# These gates are intentionally conservative. The pipeline's production schemas
# should take the provider-neutral prompted-JSON path by default.
ANTHROPIC_NATIVE_MAX_OPTIONAL_PARAMS = 12
ANTHROPIC_NATIVE_MAX_UNION_PARAMS = 8
ANTHROPIC_NATIVE_MAX_SCHEMA_BYTES = 3_000

OPENAI_NATIVE_MAX_OPTIONAL_PARAMS = 20
OPENAI_NATIVE_MAX_UNION_PARAMS = 12
OPENAI_NATIVE_MAX_SCHEMA_BYTES = 4_500


def anthropic_native_safe(profile: SchemaProfile) -> bool:
    return (
        profile.optional_param_count <= ANTHROPIC_NATIVE_MAX_OPTIONAL_PARAMS
        and profile.union_param_count <= ANTHROPIC_NATIVE_MAX_UNION_PARAMS
        and profile.pattern_count == 0
        and profile.schema_bytes <= ANTHROPIC_NATIVE_MAX_SCHEMA_BYTES
        and profile.max_depth <= 8
    )


def openai_native_safe(profile: SchemaProfile) -> bool:
    return (
        profile.optional_param_count <= OPENAI_NATIVE_MAX_OPTIONAL_PARAMS
        and profile.union_param_count <= OPENAI_NATIVE_MAX_UNION_PARAMS
        and profile.pattern_count <= 1
        and profile.schema_bytes <= OPENAI_NATIVE_MAX_SCHEMA_BYTES
        and profile.max_depth <= 10
    )
