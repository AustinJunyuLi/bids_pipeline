from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from pydantic import BaseModel, ValidationError

from pipeline.config import ANTHROPIC_MODEL, DEFAULT_CONCURRENCY_LIMIT, LLM_MAX_RETRIES
from pipeline.llm.backend import LLMUsage, StructuredResult, SystemPromptParam, T, run_coro_sync
from pipeline.llm.prompts import PromptPack
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
    }
}


class AnthropicBackend:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        max_retries: int = LLM_MAX_RETRIES,
        concurrency_limit: int = DEFAULT_CONCURRENCY_LIMIT,
        async_client: Any | None = None,
        client: Any | None = None,
    ) -> None:
        self.model = model or ANTHROPIC_MODEL
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

    def invoke_structured(
        self,
        *,
        messages: list[dict[str, Any]],
        system: SystemPromptParam,
        output_schema: type[T],
        max_tokens: int,
        model: str | None = None,
        cache: bool = True,
    ) -> StructuredResult[T]:
        return run_coro_sync(
            self.ainvoke_structured(
                messages=messages,
                system=system,
                output_schema=output_schema,
                max_tokens=max_tokens,
                model=model,
                cache=cache,
            )
        )

    def count_tokens(
        self,
        *,
        messages: list[dict[str, Any]],
        system: SystemPromptParam,
        model: str | None = None,
    ) -> int:
        return run_coro_sync(self.acount_tokens(messages=messages, system=system, model=model))

    def repair_structured(
        self,
        *,
        original_json: str,
        errors: list[str],
        output_schema: type[T],
        max_tokens: int,
        model: str | None = None,
    ) -> StructuredResult[T]:
        return run_coro_sync(
            self.arepair_structured(
                original_json=original_json,
                errors=errors,
                output_schema=output_schema,
                max_tokens=max_tokens,
                model=model,
            )
        )

    async def ainvoke_structured(
        self,
        *,
        messages: list[dict[str, Any]],
        system: SystemPromptParam,
        output_schema: type[T],
        max_tokens: int,
        model: str | None = None,
        cache: bool = True,
    ) -> StructuredResult[T]:
        effective_model = model or self.model
        prompt_version = PromptPack.prompt_version(self._system_to_text(system))
        raw_json, usage = await self._ainvoke_once(
            messages=messages,
            system=system,
            output_schema=output_schema,
            max_tokens=max_tokens,
            model=effective_model,
            cache=cache,
        )
        try:
            parsed_output = output_schema.model_validate_json(raw_json)
            return StructuredResult(
                output=parsed_output,
                usage=usage,
                raw_json=raw_json,
                prompt_version=prompt_version,
            )
        except ValidationError as exc:
            repaired = await self.arepair_structured(
                original_json=raw_json,
                errors=self._format_validation_errors(exc),
                output_schema=output_schema,
                max_tokens=max_tokens,
                model=effective_model,
            )
            return StructuredResult(
                output=repaired.output,
                usage=self._combine_usage(usage, repaired.usage),
                raw_json=repaired.raw_json,
                prompt_version=repaired.prompt_version,
            )

    async def acount_tokens(
        self,
        *,
        messages: list[dict[str, Any]],
        system: SystemPromptParam,
        model: str | None = None,
    ) -> int:
        params = {"model": model or self.model, "messages": messages, "system": system}
        response = await self._call_with_retry("count_tokens", params)
        return int(getattr(response, "input_tokens", 0) or 0)

    async def arepair_structured(
        self,
        *,
        original_json: str,
        errors: list[str],
        output_schema: type[T],
        max_tokens: int,
        model: str | None = None,
    ) -> StructuredResult[T]:
        repair_messages = [
            {
                "role": "user",
                "content": PromptPack.render_repair_user_message(original_json, errors),
            }
        ]
        raw_json, usage = await self._ainvoke_once(
            messages=repair_messages,
            system=PromptPack.REPAIR_SYSTEM_PROMPT,
            output_schema=output_schema,
            max_tokens=max_tokens,
            model=model or self.model,
            cache=False,
        )
        parsed_output = output_schema.model_validate_json(raw_json)
        return StructuredResult(
            output=parsed_output,
            usage=usage,
            raw_json=raw_json,
            prompt_version=PromptPack.prompt_version(PromptPack.REPAIR_SYSTEM_PROMPT),
        )

    async def _ainvoke_once(
        self,
        *,
        messages: list[dict[str, Any]],
        system: SystemPromptParam,
        output_schema: type[BaseModel],
        max_tokens: int,
        model: str,
        cache: bool,
    ) -> tuple[str, LLMUsage]:
        params = self._build_request_params(
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
        raw_json = self._extract_text_block(response)
        usage = self._usage_from_response(response, latency_ms=latency_ms, model=model)
        return raw_json, usage

    def _build_request_params(
        self,
        *,
        messages: list[dict[str, Any]],
        system: SystemPromptParam,
        output_schema: type[BaseModel],
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
            "output_config": {
                "format": {
                    "type": "json_schema",
                    "schema": pydantic_to_anthropic_schema(output_schema),
                }
            },
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
        for block in getattr(response, "content", []):
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
    ) -> float:
        rates = PRICING.get(model) or PRICING.get(self.model) or PRICING.get(ANTHROPIC_MODEL)
        if rates is None:
            raise KeyError(f"No pricing configured for {model!r} or fallback models.")
        total = (
            (input_tokens * rates["input"])
            + (cache_creation_input_tokens * rates["cache_write"])
            + (cache_read_input_tokens * rates["cache_read"])
            + (output_tokens * rates["output"])
        )
        return total / 1_000_000

    @staticmethod
    def _format_validation_errors(error: ValidationError) -> list[str]:
        formatted = []
        for issue in error.errors():
            path = ".".join(str(part) for part in issue["loc"])
            formatted.append(f"{path}: {issue['msg']}")
        return formatted

    @staticmethod
    def _combine_usage(primary: LLMUsage, secondary: LLMUsage) -> LLMUsage:
        return LLMUsage(
            input_tokens=primary.input_tokens + secondary.input_tokens,
            cache_creation_input_tokens=(
                primary.cache_creation_input_tokens + secondary.cache_creation_input_tokens
            ),
            cache_read_input_tokens=(
                primary.cache_read_input_tokens + secondary.cache_read_input_tokens
            ),
            output_tokens=primary.output_tokens + secondary.output_tokens,
            cost_usd=primary.cost_usd + secondary.cost_usd,
            latency_ms=primary.latency_ms + secondary.latency_ms,
            request_id=secondary.request_id,
            model=secondary.model,
        )

    @staticmethod
    def _system_to_text(system: SystemPromptParam) -> str:
        if isinstance(system, str):
            return system
        return json.dumps(system, sort_keys=True, default=str)

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
