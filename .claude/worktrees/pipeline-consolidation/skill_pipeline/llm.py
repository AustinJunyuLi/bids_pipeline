"""Thin LLM wrapper for structured output via an OpenAI-compatible API."""

from __future__ import annotations

import json
import os
from typing import TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

_DEFAULT_MODEL = "gpt-5.4"
_DEFAULT_BASE_URL = "https://api.newapi.pro/v1"


def _get_client():
    from openai import OpenAI

    return OpenAI(
        api_key=os.environ["NEWAPI_API_KEY"],
        base_url=os.environ.get("NEWAPI_BASE_URL", _DEFAULT_BASE_URL),
    )


def _schema_outline(model: type[BaseModel]) -> str:
    return json.dumps(model.model_json_schema(), indent=2)


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if len(lines) == 1:
        return stripped.strip("`").strip()
    if lines[-1].strip().startswith("```"):
        return "\n".join(lines[1:-1]).strip()
    return "\n".join(lines[1:]).strip()


def _parse_output(raw_text: str, output_model: type[T]) -> T:
    data = json.loads(_strip_code_fences(raw_text))
    return output_model.model_validate(data)


def _build_messages(system_prompt: str, user_message: str, schema_text: str) -> list[dict[str, str]]:
    full_system = (
        f"{system_prompt}\n\n"
        "You MUST respond with exactly one JSON object matching this schema:\n"
        f"```json\n{schema_text}\n```\n"
        "Return ONLY the JSON object, no other text."
    )
    return [
        {"role": "system", "content": full_system},
        {"role": "user", "content": user_message},
    ]


def _create_completion(
    client,
    messages: list[dict[str, str]],
    *,
    model: str,
    max_output_tokens: int,
    temperature: float,
    reasoning_effort: str,
):
    kwargs: dict[str, object] = {
        "model": model,
        "messages": messages,
        "max_completion_tokens": max_output_tokens,
        "temperature": temperature,
    }
    if reasoning_effort != "none":
        kwargs["reasoning_effort"] = reasoning_effort
    return client.chat.completions.create(**kwargs)


def invoke_structured(
    system_prompt: str,
    user_message: str,
    output_model: type[T],
    *,
    model: str | None = None,
    max_output_tokens: int = 16_000,
    temperature: float = 0.0,
    reasoning_effort: str = "none",
) -> T:
    """Send a prompt, parse JSON output, and validate it against a Pydantic model."""
    client = _get_client()
    effective_model = model or os.environ.get("NEWAPI_MODEL", _DEFAULT_MODEL)
    schema_text = _schema_outline(output_model)
    messages = _build_messages(system_prompt, user_message, schema_text)

    response = _create_completion(
        client,
        messages,
        model=effective_model,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
        reasoning_effort=reasoning_effort,
    )

    raw_text = response.choices[0].message.content
    if raw_text is None:
        raise ValueError("LLM response did not include message content.")

    try:
        return _parse_output(raw_text, output_model)
    except (json.JSONDecodeError, ValidationError) as first_error:
        retry_messages = messages + [
            {"role": "assistant", "content": raw_text},
            {
                "role": "user",
                "content": (
                    "Your response failed validation:\n"
                    f"{first_error}\n\n"
                    "Fix the JSON and return only the corrected JSON object."
                ),
            },
        ]

    response = _create_completion(
        client,
        retry_messages,
        model=effective_model,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
        reasoning_effort=reasoning_effort,
    )

    raw_text = response.choices[0].message.content
    if raw_text is None:
        raise ValueError("LLM response did not include message content.")

    try:
        return _parse_output(raw_text, output_model)
    except (json.JSONDecodeError, ValidationError) as second_error:
        raise ValueError(
            f"LLM output failed validation after retry: {second_error}"
        ) from second_error
