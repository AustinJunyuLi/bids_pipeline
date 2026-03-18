from __future__ import annotations

import asyncio
import math
import time
from typing import Any

from pydantic import BaseModel

from pipeline.config import (
    DEFAULT_CONCURRENCY_LIMIT,
    DEFAULT_STRUCTURED_OUTPUT_MODE,
    LLM_MAX_RETRIES,
    OPENAI_MODEL,
)
from pipeline.llm.backend import BaseLLMBackend, LLMUsage, SystemPromptParam
from pipeline.llm.schema_profile import openai_native_safe, profile_model_schema

try:  # pragma: no cover - exercised indirectly by import behavior in tests.
    import openai  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - dependency is optional in tests.
    openai = None


# Pricing intentionally omitted until the project pins the specific OpenAI model
# lineup it wants to use in production. Token accounting still works.
PRICING: dict[str, dict[str, float]] = {}
VALID_REASONING_EFFORTS = frozenset({"none", "minimal", "low", "medium", "high", "xhigh"})


class OpenAIBackend(BaseLLMBackend):
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        reasoning_effort: str | None = None,
        structured_mode: str = DEFAULT_STRUCTURED_OUTPUT_MODE,
        max_retries: int = LLM_MAX_RETRIES,
        concurrency_limit: int = DEFAULT_CONCURRENCY_LIMIT,
        max_validation_retries: int = 2,
        async_client: Any | None = None,
        client: Any | None = None,
    ) -> None:
        if reasoning_effort is not None and reasoning_effort not in VALID_REASONING_EFFORTS:
            raise ValueError(
                f"Invalid OpenAI reasoning effort {reasoning_effort!r}; expected one of {sorted(VALID_REASONING_EFFORTS)}"
            )
        super().__init__(
            provider="openai",
            model=model or OPENAI_MODEL,
            structured_mode=structured_mode,
            max_validation_retries=max_validation_retries,
        )
        self.reasoning_effort = reasoning_effort
        self.max_retries = max_retries
        self._async_client = async_client or self._build_async_client(api_key=api_key)
        self._client = client
        self._semaphore = asyncio.Semaphore(concurrency_limit)

    @staticmethod
    def _build_async_client(*, api_key: str | None) -> Any:
        if openai is None:
            raise ModuleNotFoundError(
                "openai is required to create a live OpenAIBackend client; "
                "pass async_client in tests or install the openai package."
            )
        return openai.AsyncOpenAI(api_key=api_key)

    async def _agenerate_text(
        self,
        *,
        messages: list[dict[str, Any]],
        system: str,
        max_tokens: int,
        model: str,
        cache: bool,
    ) -> tuple[str, LLMUsage]:
        params = self._build_text_request_params(
            messages=messages,
            system=system,
            max_tokens=max_tokens,
            model=model,
        )
        started = time.perf_counter()
        response = await self._call_with_retry(params)
        latency_ms = int((time.perf_counter() - started) * 1000)
        raw_text = self._extract_message_text(response)
        usage = self._usage_from_response(response, latency_ms=latency_ms, model=model)
        return raw_text, usage

    async def _ainvoke_provider_native(
        self,
        *,
        messages: list[dict[str, Any]],
        system: str,
        output_schema: type[BaseModel],
        max_tokens: int,
        model: str,
        cache: bool,
    ) -> tuple[str, LLMUsage]:
        params = self._build_text_request_params(
            messages=messages,
            system=system,
            max_tokens=max_tokens,
            model=model,
        )
        params["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": output_schema.__name__.lower(),
                "strict": True,
                "schema": output_schema.model_json_schema(mode="validation"),
            },
        }
        started = time.perf_counter()
        response = await self._call_with_retry(params)
        latency_ms = int((time.perf_counter() - started) * 1000)
        raw_text = self._extract_message_text(response)
        usage = self._usage_from_response(response, latency_ms=latency_ms, model=model)
        return raw_text, usage

    async def acount_tokens(
        self,
        *,
        messages: list[dict[str, Any]],
        system: SystemPromptParam,
        model: str | None = None,
    ) -> int:
        rendered_messages = self._build_messages(
            system=self._system_to_text(system),
            messages=messages,
        )
        return self._estimate_token_count(rendered_messages)

    def _supports_native_structured_output(self, output_schema: type[BaseModel]) -> bool:
        return openai_native_safe(profile_model_schema(output_schema))

    def _build_text_request_params(
        self,
        *,
        messages: list[dict[str, Any]],
        system: str,
        max_tokens: int,
        model: str,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "model": model,
            "messages": self._build_messages(system=system, messages=messages),
            "max_completion_tokens": max_tokens,
        }
        if self._supports_explicit_temperature(model):
            params["temperature"] = 0
        if self.reasoning_effort is not None:
            params["reasoning_effort"] = self.reasoning_effort
        return params

    def _build_messages(self, *, system: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rendered_messages: list[dict[str, Any]] = []
        if system:
            rendered_messages.append({"role": "developer", "content": system})
        for message in messages:
            rendered_messages.append(
                {
                    "role": message.get("role", "user"),
                    "content": self._normalize_message_content(message.get("content", "")),
                }
            )
        return rendered_messages

    @staticmethod
    def _normalize_message_content(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            rendered_parts: list[str] = []
            for part in content:
                if isinstance(part, dict):
                    rendered_parts.append(str(part.get("text") or part.get("content") or part))
                else:
                    rendered_parts.append(str(part))
            return "\n".join(rendered_parts)
        return str(content)

    @staticmethod
    def _supports_explicit_temperature(model: str) -> bool:
        normalized = model.strip().lower()
        return not normalized.startswith("gpt-5")

    async def _call_with_retry(self, params: dict[str, Any]):
        attempts = 0
        while True:
            try:
                async with self._semaphore:
                    return await self._async_client.chat.completions.create(**params)
            except Exception as exc:  # noqa: BLE001
                if attempts >= self.max_retries or not self._is_retryable_error(exc):
                    raise
                await asyncio.sleep(2**attempts)
                attempts += 1

    def _extract_message_text(self, response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text.strip():
            return output_text

        choices = getattr(response, "choices", None) or []
        if not choices:
            raise ValueError("OpenAI response did not include any choices.")
        message = getattr(choices[0], "message", None)
        if message is None:
            raise ValueError("OpenAI response choice did not include a message.")
        content = getattr(message, "content", None)
        if isinstance(content, str):
            if content.strip():
                return content
        if isinstance(content, list):
            parts: list[str] = []
            for part in content:
                part_type = getattr(part, "type", None) or (part.get("type") if isinstance(part, dict) else None)
                if part_type in {None, "text", "output_text"}:
                    text = getattr(part, "text", None)
                    if text is None and isinstance(part, dict):
                        text = part.get("text")
                    if text is None and hasattr(part, "content"):
                        text = getattr(part, "content")
                    if text is not None:
                        parts.append(str(text))
            if parts:
                joined = "\n".join(parts)
                if joined.strip():
                    return joined
        finish_reason = getattr(choices[0], "finish_reason", None)
        if finish_reason == "length":
            raise ValueError(
                "OpenAI response exhausted max_completion_tokens before emitting visible text. "
                "For GPT-5 structured extraction, increase max_completion_tokens and/or use reasoning_effort='none'."
            )
        raise ValueError("OpenAI response did not contain text content.")

    def _usage_from_response(self, response: Any, *, latency_ms: int, model: str) -> LLMUsage:
        usage = getattr(response, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        response_model = getattr(response, "model", None) or model
        request_id = getattr(response, "id", "")
        return LLMUsage(
            provider="openai",
            input_tokens=prompt_tokens,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
            output_tokens=completion_tokens,
            cost_usd=self._compute_cost(
                response_model,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
            ),
            latency_ms=latency_ms,
            request_id=request_id,
            model=response_model,
        )

    def _compute_cost(
        self,
        model: str,
        *,
        input_tokens: int,
        output_tokens: int,
    ) -> float | None:
        rates = PRICING.get(model) or PRICING.get(self.model)
        if rates is None:
            return None
        total = (input_tokens * rates["input"]) + (output_tokens * rates["output"])
        return total / 1_000_000

    @staticmethod
    def _estimate_token_count(messages: list[dict[str, Any]]) -> int:
        text = "\n".join(f"{message['role']}: {message['content']}" for message in messages)
        # Conservative heuristic: ~4 characters per token plus per-message framing.
        return max(1, math.ceil(len(text) / 4) + (8 * len(messages)))

    @staticmethod
    def _is_retryable_error(exc: Exception) -> bool:
        if openai is None:
            return False
        retryable_types = tuple(
            error_type
            for error_type in (
                getattr(openai, "APIConnectionError", None),
                getattr(openai, "APITimeoutError", None),
                getattr(openai, "InternalServerError", None),
                getattr(openai, "RateLimitError", None),
            )
            if error_type is not None
        )
        if retryable_types and isinstance(exc, retryable_types):
            return True
        api_status_error = getattr(openai, "APIStatusError", None)
        if api_status_error is not None and isinstance(exc, api_status_error):
            status_code = getattr(exc, "status_code", None)
            return isinstance(status_code, int) and status_code >= 500
        return False
