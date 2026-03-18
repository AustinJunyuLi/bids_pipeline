from __future__ import annotations

import asyncio
import time
from typing import Any

from pydantic import BaseModel

from pipeline.config import (
    ANTHROPIC_MODEL,
    DEFAULT_CONCURRENCY_LIMIT,
    DEFAULT_STRUCTURED_OUTPUT_MODE,
    LLM_MAX_RETRIES,
)
from pipeline.llm.backend import BaseLLMBackend, LLMUsage, SystemPromptParam
from pipeline.llm.schema_profile import anthropic_native_safe, profile_model_schema
from pipeline.llm.schemas import pydantic_to_anthropic_schema

try:  # pragma: no cover - exercised indirectly by import behavior in tests.
    import anthropic  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - dependency is optional in tests.
    anthropic = None


PRICING = {
    "claude-sonnet-4-20250514": {
        "input": 3.0,
        "cache_write": 3.75,
        "cache_read": 0.30,
        "output": 15.0,
    },
    "claude-sonnet-4-6": {
        "input": 3.0,
        "cache_write": 3.75,
        "cache_read": 0.30,
        "output": 15.0,
    },
}

VALID_EFFORT_LEVELS = frozenset({"low", "medium", "high", "max"})


class AnthropicBackend(BaseLLMBackend):
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        effort: str | None = None,
        reasoning_effort: str | None = None,
        structured_mode: str = DEFAULT_STRUCTURED_OUTPUT_MODE,
        max_retries: int = LLM_MAX_RETRIES,
        concurrency_limit: int = DEFAULT_CONCURRENCY_LIMIT,
        max_validation_retries: int = 2,
        async_client: Any | None = None,
        client: Any | None = None,
    ) -> None:
        effective_effort = reasoning_effort or effort
        if effective_effort is not None and effective_effort not in VALID_EFFORT_LEVELS:
            raise ValueError(
                f"Invalid effort level {effective_effort!r}; expected one of {sorted(VALID_EFFORT_LEVELS)}"
            )
        super().__init__(
            provider="anthropic",
            model=model or ANTHROPIC_MODEL,
            structured_mode=structured_mode,
            max_validation_retries=max_validation_retries,
        )
        self.effort = effective_effort
        self.max_retries = max_retries
        self._async_client = async_client or self._build_async_client(api_key=api_key)
        self._client = client
        self._semaphore = asyncio.Semaphore(concurrency_limit)

    @staticmethod
    def _build_async_client(*, api_key: str | None) -> Any:
        if anthropic is None:
            raise ModuleNotFoundError(
                "anthropic is required to create a live AnthropicBackend client; "
                "pass async_client in tests or install the anthropic package."
            )
        return anthropic.AsyncAnthropic(api_key=api_key)

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
            cache=cache,
        )
        started = time.perf_counter()
        response = await self._call_with_retry("create", params)
        latency_ms = int((time.perf_counter() - started) * 1000)
        raw_text = self._extract_text_block(response)
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
        params = self._build_native_request_params(
            messages=messages,
            system=system,
            output_schema=output_schema,
            max_tokens=max_tokens,
            model=model,
            cache=cache,
        )
        started = time.perf_counter()
        response = await self._call_with_retry("create", params)
        latency_ms = int((time.perf_counter() - started) * 1000)
        raw_text = self._extract_text_block(response)
        usage = self._usage_from_response(response, latency_ms=latency_ms, model=model)
        return raw_text, usage

    async def acount_tokens(
        self,
        *,
        messages: list[dict[str, Any]],
        system: SystemPromptParam,
        model: str | None = None,
    ) -> int:
        params: dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "system": system,
        }
        if self.effort is not None:
            params["output_config"] = {"effort": self.effort}
        response = await self._call_with_retry("count_tokens", params)
        return int(getattr(response, "input_tokens", 0) or 0)

    def _supports_native_structured_output(self, output_schema: type[BaseModel]) -> bool:
        return anthropic_native_safe(profile_model_schema(output_schema))

    def _build_text_request_params(
        self,
        *,
        messages: list[dict[str, Any]],
        system: str,
        max_tokens: int,
        model: str,
        cache: bool,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
            "system": system,
            "temperature": 0,
        }
        if self.effort is not None:
            params["output_config"] = {"effort": self.effort}
        if cache:
            params["cache_control"] = {"type": "ephemeral"}
        return params

    def _build_native_request_params(
        self,
        *,
        messages: list[dict[str, Any]],
        system: str,
        output_schema: type[BaseModel],
        max_tokens: int,
        model: str,
        cache: bool,
    ) -> dict[str, Any]:
        output_config: dict[str, Any] = {
            "format": {
                "type": "json_schema",
                "schema": pydantic_to_anthropic_schema(output_schema),
            }
        }
        if self.effort is not None:
            output_config["effort"] = self.effort
        params: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
            "system": system,
            "temperature": 0,
            "output_config": output_config,
        }
        if cache:
            params["cache_control"] = {"type": "ephemeral"}
        return params

    async def _call_with_retry(self, method_name: str, params: dict[str, Any]):
        attempts = 0
        while True:
            try:
                async with self._semaphore:
                    method = getattr(self._async_client.messages, method_name)
                    return await method(**params)
            except Exception as exc:  # noqa: BLE001
                if attempts >= self.max_retries or not self._is_retryable_error(exc):
                    raise
                await asyncio.sleep(2**attempts)
                attempts += 1

    def _extract_text_block(self, response: Any) -> str:
        content_blocks = list(getattr(response, "content", []))
        for block in content_blocks:
            if getattr(block, "type", None) == "text":
                return getattr(block, "text")
        raise ValueError("Anthropic response did not contain a text block.")

    def _usage_from_response(self, response: Any, *, latency_ms: int, model: str) -> LLMUsage:
        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        cache_creation_input_tokens = int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
        cache_read_input_tokens = int(getattr(usage, "cache_read_input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        response_model = getattr(response, "model", None) or model
        request_id = getattr(response, "id", "")
        return LLMUsage(
            provider="anthropic",
            input_tokens=input_tokens,
            cache_creation_input_tokens=cache_creation_input_tokens,
            cache_read_input_tokens=cache_read_input_tokens,
            output_tokens=output_tokens,
            cost_usd=self._compute_cost(
                response_model,
                input_tokens=input_tokens,
                cache_creation_input_tokens=cache_creation_input_tokens,
                cache_read_input_tokens=cache_read_input_tokens,
                output_tokens=output_tokens,
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
        cache_creation_input_tokens: int,
        cache_read_input_tokens: int,
        output_tokens: int,
    ) -> float | None:
        rates = PRICING.get(model) or PRICING.get(self.model) or PRICING.get(ANTHROPIC_MODEL)
        if rates is None:
            return None
        total = (
            (input_tokens * rates["input"])
            + (cache_creation_input_tokens * rates["cache_write"])
            + (cache_read_input_tokens * rates["cache_read"])
            + (output_tokens * rates["output"])
        )
        return total / 1_000_000

    @staticmethod
    def _is_retryable_error(exc: Exception) -> bool:
        if anthropic is None:
            return False
        if isinstance(exc, (anthropic.APIConnectionError, anthropic.InternalServerError, anthropic.RateLimitError)):
            return True
        if isinstance(exc, anthropic.APIStatusError):
            status_code = getattr(exc, "status_code", None)
            return isinstance(status_code, int) and status_code >= 500
        return False
