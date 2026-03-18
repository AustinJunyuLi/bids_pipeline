from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from pydantic import BaseModel


def inline_json_refs(schema: dict[str, Any]) -> dict[str, Any]:
    definitions = deepcopy(schema.get("$defs", {}))
    payload = deepcopy(schema)
    payload.pop("$defs", None)
    return _inline_refs(payload, definitions)


def _inline_refs(value: Any, definitions: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        if "$ref" in value:
            ref = value["$ref"]
            if not ref.startswith("#/$defs/"):
                raise ValueError(f"Unsupported schema reference: {ref}")
            name = ref.removeprefix("#/$defs/")
            return _inline_refs(deepcopy(definitions[name]), definitions)
        return {key: _inline_refs(child, definitions) for key, child in value.items()}
    if isinstance(value, list):
        return [_inline_refs(child, definitions) for child in value]
    return value


def extract_json_candidate(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return stripped
    if _is_valid_json(stripped):
        return stripped

    fenced_candidates = re.findall(r"```(?:json)?\s*(.*?)```", stripped, flags=re.DOTALL | re.IGNORECASE)
    for candidate in fenced_candidates:
        normalized = candidate.strip()
        if _is_valid_json(normalized):
            return normalized

    leading_balanced = _extract_balanced_json(stripped, start_index=0)
    if leading_balanced is not None:
        return leading_balanced
    if stripped[0] in "{[":
        # Preserve malformed top-level JSON for repair instead of dropping into a
        # nested child object/array that happens to be valid on its own.
        return stripped

    balanced = _extract_balanced_json(stripped)
    if balanced is not None:
        return balanced
    return stripped


def _is_valid_json(text: str) -> bool:
    try:
        json.loads(text)
    except json.JSONDecodeError:
        return False
    return True


def _extract_balanced_json(text: str, *, start_index: int | None = None) -> str | None:
    if start_index is not None:
        opening = text[start_index] if 0 <= start_index < len(text) else None
        candidate_indices = [(start_index, opening)] if opening in "[{" else []
    else:
        candidate_indices = list(enumerate(text))

    for start_index, opening in candidate_indices:
        if opening not in "[{":
            continue
        closing = "}" if opening == "{" else "]"
        depth = 0
        in_string = False
        escaped = False
        for end_index in range(start_index, len(text)):
            char = text[end_index]
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == opening:
                depth += 1
            elif char == closing:
                depth -= 1
                if depth == 0:
                    candidate = text[start_index : end_index + 1]
                    if _is_valid_json(candidate):
                        return candidate
                    break
        # Keep scanning from later opening characters if the first object failed.
    return None


def json_canonical_string(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)


def schema_outline(model_cls: type[BaseModel], *, max_chars: int = 12_000) -> str:
    schema = inline_json_refs(model_cls.model_json_schema(mode="validation"))
    rendered = _render_schema_node(schema, level=0, required=True)
    if len(rendered) <= max_chars:
        return rendered
    return rendered[: max_chars - 24] + "\n...\n<truncated schema>"


def _render_schema_node(node: Any, *, level: int, required: bool) -> str:
    indent = "  " * level
    if not isinstance(node, dict):
        return indent + repr(node)

    if "enum" in node:
        values = " | ".join(json.dumps(value, ensure_ascii=False) for value in node["enum"])
        return f"enum[{values}]"

    if "anyOf" in node or "oneOf" in node:
        options = node.get("anyOf") or node.get("oneOf") or []
        non_null = [option for option in options if option.get("type") != "null"]
        rendered = " | ".join(_render_schema_node(option, level=level, required=True).strip() for option in non_null)
        return rendered or "null"

    node_type = node.get("type")
    if node_type == "array":
        rendered_items = _render_schema_node(node.get("items", {}), level=level + 1, required=True).strip()
        return f"[{rendered_items}]"

    if node_type == "object" or "properties" in node:
        properties = node.get("properties", {})
        required_fields = set(node.get("required", []))
        lines = ["{"]
        for key, value in properties.items():
            field_required = key in required_fields
            suffix = "" if field_required else "?"
            rendered = _render_schema_node(value, level=level + 1, required=field_required).strip()
            lines.append(f"{indent}  {key}{suffix}: {rendered}")
        lines.append(f"{indent}}}")
        return "\n".join(lines)

    if node_type is not None:
        return node_type

    if "items" in node:
        return f"[{_render_schema_node(node['items'], level=level + 1, required=True).strip()}]"

    return node.get("title") or "value"
