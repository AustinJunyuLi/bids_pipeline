from __future__ import annotations

import os
from typing import Any

from pipeline.config import (
    ANTHROPIC_API_KEY_ENV,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_STRUCTURED_OUTPUT_MODE,
    LLM_MODEL_ENV,
    LLM_PROVIDER_ENV,
    LLM_REASONING_EFFORT_ENV,
    LLM_STRUCTURED_MODE_ENV,
    OPENAI_API_KEY_ENV,
    VALID_LLM_PROVIDERS,
)
from pipeline.llm.anthropic_backend import AnthropicBackend
from pipeline.llm.openai_backend import OpenAIBackend


def build_backend(
    *,
    provider: str | None = None,
    model: str | None = None,
    reasoning_effort: str | None = None,
    structured_mode: str | None = None,
    api_key: str | None = None,
    async_client: Any | None = None,
    client: Any | None = None,
):
    resolved_provider = (provider or os.environ.get(LLM_PROVIDER_ENV) or DEFAULT_LLM_PROVIDER).strip().lower()
    if resolved_provider not in VALID_LLM_PROVIDERS:
        raise ValueError(
            f"Unsupported provider {resolved_provider!r}; expected one of {sorted(VALID_LLM_PROVIDERS)}"
        )
    resolved_model = model or os.environ.get(LLM_MODEL_ENV)
    resolved_effort = reasoning_effort or os.environ.get(LLM_REASONING_EFFORT_ENV)
    resolved_structured_mode = structured_mode or os.environ.get(LLM_STRUCTURED_MODE_ENV) or DEFAULT_STRUCTURED_OUTPUT_MODE

    if resolved_provider == "anthropic":
        return AnthropicBackend(
            api_key=api_key or os.environ.get(ANTHROPIC_API_KEY_ENV),
            model=resolved_model,
            reasoning_effort=resolved_effort,
            structured_mode=resolved_structured_mode,
            async_client=async_client,
            client=client,
        )
    if resolved_provider == "openai":
        return OpenAIBackend(
            api_key=api_key or os.environ.get(OPENAI_API_KEY_ENV),
            model=resolved_model,
            reasoning_effort=resolved_effort,
            structured_mode=resolved_structured_mode,
            async_client=async_client,
            client=client,
        )
    raise AssertionError(f"Unhandled provider: {resolved_provider}")
