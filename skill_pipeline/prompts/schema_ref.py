from __future__ import annotations

import json
import types
from datetime import date
from decimal import Decimal
from typing import Annotated, Any, Literal, Union, get_args, get_origin

from pydantic import BaseModel

from skill_pipeline.extract_artifacts_v2 import (
    RawAgreementObservationV2,
    RawCohortRecordV2,
    RawObservationArtifactV2,
    RawObservationBaseV2,
    RawOutcomeObservationV2,
    RawPartyRecordV2,
    RawProcessObservationV2,
    RawProposalObservationV2,
    RawSolicitationObservationV2,
    RawStatusObservationV2,
)
from skill_pipeline.models import MoneyTerms, ResolvedDate, SkillExclusionRecord
from skill_pipeline.pipeline_models.common import DatePrecision

_OBSERVATION_MODELS: tuple[type[BaseModel], ...] = (
    RawProcessObservationV2,
    RawAgreementObservationV2,
    RawSolicitationObservationV2,
    RawProposalObservationV2,
    RawStatusObservationV2,
    RawOutcomeObservationV2,
)


def generate_schema_reference() -> str:
    """Emit a compact JSON schema reference derived from the live models."""
    base_field_names = set(RawObservationBaseV2.model_fields)
    schema = {
        "top_level_keys": list(RawObservationArtifactV2.model_fields),
        "observation_record": {
            "discriminator": "obs_type",
            "obs_type_values": [_observation_type_value(model) for model in _OBSERVATION_MODELS],
            "common_fields": _field_specs(RawObservationBaseV2),
            "variant_fields": {
                _observation_type_value(model): {
                    name: _format_annotation(field.annotation)
                    for name, field in model.model_fields.items()
                    if name not in base_field_names
                }
                for model in _OBSERVATION_MODELS
            },
        },
        "ResolvedDate": {
            "fields": _field_specs(ResolvedDate),
            "precision_enum": [member.value for member in DatePrecision],
        },
        "MoneyTerms": {"fields": _field_specs(MoneyTerms)},
        "PartyRecord": {"fields": _field_specs(RawPartyRecordV2)},
        "CohortRecord": {"fields": _field_specs(RawCohortRecordV2)},
        "SkillExclusionRecord": {
            "fields": _field_specs(SkillExclusionRecord),
            "category_enum": _literal_values(
                SkillExclusionRecord.model_fields["category"].annotation
            ),
        },
    }
    return "<json_schema_reference>\n" + json.dumps(schema, indent=2) + "\n</json_schema_reference>"


def _field_specs(model: type[BaseModel]) -> dict[str, str]:
    return {
        field_name: _format_annotation(field.annotation)
        for field_name, field in model.model_fields.items()
    }


def _observation_type_value(model: type[BaseModel]) -> str:
    values = _literal_values(model.model_fields["obs_type"].annotation)
    if not values or len(values) != 1:
        raise ValueError(f"Unable to determine obs_type literal for {model.__name__}")
    return str(values[0])


def _format_annotation(annotation: Any) -> str:
    annotation = _unwrap_annotated(annotation)
    literal_values = _literal_values(annotation)
    if literal_values is not None:
        return "enum" + json.dumps(literal_values)

    origin = get_origin(annotation)
    if origin is list:
        (item_type,) = get_args(annotation)
        return f"array[{_format_annotation(item_type)}]"
    if origin is dict:
        return "object"
    if origin in (Union, types.UnionType):
        rendered = [
            _format_annotation(arg)
            for arg in get_args(annotation)
            if arg is not type(None)
        ]
        if len(rendered) == 1 and len(rendered) != len(get_args(annotation)):
            return f"{rendered[0]} | null"
        return " | ".join(rendered)

    if annotation is str:
        return "string"
    if annotation is int:
        return "integer"
    if annotation is bool:
        return "boolean"
    if annotation in (float, Decimal):
        return "number"
    if annotation is date:
        return "YYYY-MM-DD"
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation.__name__
    if isinstance(annotation, type) and hasattr(annotation, "__members__"):
        return annotation.__name__
    if annotation is Any:
        return "any"
    return str(annotation)


def _literal_values(annotation: Any) -> list[str] | None:
    annotation = _unwrap_annotated(annotation)
    origin = get_origin(annotation)
    if origin is Literal:
        return [str(value) for value in get_args(annotation)]
    if origin in (Union, types.UnionType):
        values: list[str] = []
        saw_literal = False
        for arg in get_args(annotation):
            if arg is type(None):
                continue
            nested = _literal_values(arg)
            if nested is None:
                return None
            values.extend(nested)
            saw_literal = True
        return values if saw_literal else None
    return None


def _unwrap_annotated(annotation: Any) -> Any:
    if get_origin(annotation) is Annotated:
        return get_args(annotation)[0]
    return annotation


__all__ = ["generate_schema_reference"]
