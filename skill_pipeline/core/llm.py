"""Thin LLM wrapper for structured output via an OpenAI-compatible API."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

_DEFAULT_MODEL = "gpt-5.4"
_DEFAULT_BASE_URL = "https://www.linkflow.run/v1"
_REPO_ROOT = Path(__file__).resolve().parents[2]


_env_loaded = False


def _load_local_env() -> None:
    global _env_loaded
    if _env_loaded:
        return
    for path in (_REPO_ROOT / ".env.local", _REPO_ROOT / ".env"):
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)
    _env_loaded = True


def _openai_client_class():
    from openai import OpenAI

    return OpenAI


def _env_value(name: str) -> str | None:
    value = os.environ.get(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _get_client():
    _load_local_env()
    api_key = _env_value("NEWAPI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "NEWAPI_API_KEY is not configured. Set it in the environment or in "
            f"{_REPO_ROOT / '.env.local'}."
        )

    return _openai_client_class()(
        api_key=api_key,
        base_url=_env_value("NEWAPI_BASE_URL") or _DEFAULT_BASE_URL,
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


def _build_messages(
    system_prompt: str, user_message: str, schema_text: str
) -> list[dict[str, str]]:
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


def _check_truncation(response) -> None:
    """Raise immediately if the API truncated the response."""
    finish_reason = response.choices[0].finish_reason
    if finish_reason == "length":
        raise ValueError(
            "LLM response was truncated (finish_reason='length'). "
            "The API cut the output short before the model finished. "
            "This is not a validation error — retrying will not help."
        )


def _create_completion(
    client,
    messages: list[dict[str, str]],
    *,
    model: str,
    max_output_tokens: int | None,
    temperature: float,
    reasoning_effort: str | None,
    service_tier: str | None,
):
    kwargs: dict[str, object] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if max_output_tokens is not None:
        kwargs["max_completion_tokens"] = max_output_tokens
    if reasoning_effort and reasoning_effort != "none":
        kwargs["reasoning_effort"] = reasoning_effort
    if service_tier:
        kwargs["service_tier"] = service_tier
    return client.chat.completions.create(**kwargs)


def invoke_structured(
    system_prompt: str,
    user_message: str,
    output_model: type[T],
    *,
    model: str | None = None,
    max_output_tokens: int | None = None,
    temperature: float = 0.0,
    reasoning_effort: str | None = None,
    service_tier: str | None = None,
) -> T:
    """Send a prompt, parse JSON output, and validate it against a Pydantic model."""
    client = _get_client()
    effective_model = model or _env_value("NEWAPI_MODEL") or _DEFAULT_MODEL
    effective_reasoning_effort = (
        reasoning_effort
        if reasoning_effort is not None
        else (_env_value("NEWAPI_REASONING_EFFORT") or "none")
    )
    effective_service_tier = (
        service_tier if service_tier is not None else _env_value("NEWAPI_SERVICE_TIER")
    )
    schema_text = _schema_outline(output_model)
    messages = _build_messages(system_prompt, user_message, schema_text)

    response = _create_completion(
        client,
        messages,
        model=effective_model,
        max_output_tokens=max_output_tokens,
        temperature=temperature,
        reasoning_effort=effective_reasoning_effort,
        service_tier=effective_service_tier,
    )
    _check_truncation(response)

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
        reasoning_effort=effective_reasoning_effort,
        service_tier=effective_service_tier,
    )
    _check_truncation(response)

    raw_text = response.choices[0].message.content
    if raw_text is None:
        raise ValueError("LLM response did not include message content.")

    try:
        return _parse_output(raw_text, output_model)
    except (json.JSONDecodeError, ValidationError) as second_error:
        raise ValueError(
            f"LLM output failed validation after retry: {second_error}"
        ) from second_error
