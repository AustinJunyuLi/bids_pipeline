# LLM Infrastructure

---

## pipeline/llm/__init__.py
```python
from pipeline.llm.anthropic_backend import AnthropicBackend
from pipeline.llm.backend import LLMBackend, LLMUsage, StructuredResult
from pipeline.llm.factory import build_backend
from pipeline.llm.local_agent_backend import LocalAgentBackend
from pipeline.llm.openai_backend import OpenAIBackend

__all__ = [
    "AnthropicBackend",
    "LocalAgentBackend",
    "OpenAIBackend",
    "LLMBackend",
    "LLMUsage",
    "StructuredResult",
    "build_backend",
]
```

---

## pipeline/llm/backend.py
```python
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from pipeline.config import (
    DEFAULT_STRUCTURED_OUTPUT_MODE,
    LLM_JSON_REPAIR_ATTEMPTS,
    VALID_STRUCTURED_OUTPUT_MODES,
)
from pipeline.llm.json_utils import extract_json_candidate
from pipeline.llm.prompts import PromptPack


T = TypeVar("T", bound=BaseModel)
MessageParam = dict[str, Any]
SystemPromptParam = str | list[dict[str, Any]]


@dataclass(slots=True)
class LLMUsage:
    provider: str
    input_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int
    output_tokens: int
    cost_usd: float | None
    latency_ms: int
    request_id: str
    model: str


@dataclass(slots=True)
class StructuredResult(Generic[T]):
    output: T
    usage: LLMUsage
    raw_json: str
    prompt_version: str
    raw_text: str | None = None
    validation_errors: list[str] = field(default_factory=list)
    repair_count: int = 0
    structured_mode: str = DEFAULT_STRUCTURED_OUTPUT_MODE


class LLMBackend(Protocol):
    provider: str
    model: str
    structured_mode: str

    async def ainvoke_structured(
        self,
        *,
        messages: list[MessageParam],
        system: SystemPromptParam,
        output_schema: type[T],
        max_tokens: int,
        model: str | None = None,
        cache: bool = True,
    ) -> StructuredResult[T]: ...

    async def acount_tokens(
        self,
        *,
        messages: list[MessageParam],
        system: SystemPromptParam,
        model: str | None = None,
    ) -> int: ...

    async def arepair_structured(
        self,
        *,
        original_json: str,
        errors: list[str],
        output_schema: type[T],
        max_tokens: int,
        model: str | None = None,
    ) -> StructuredResult[T]: ...

    def invoke_structured(
        self,
        *,
        messages: list[MessageParam],
        system: SystemPromptParam,
        output_schema: type[T],
        max_tokens: int,
        model: str | None = None,
        cache: bool = True,
    ) -> StructuredResult[T]: ...

    def count_tokens(
        self,
        *,
        messages: list[MessageParam],
        system: SystemPromptParam,
        model: str | None = None,
    ) -> int: ...

    def repair_structured(
        self,
        *,
        original_json: str,
        errors: list[str],
        output_schema: type[T],
        max_tokens: int,
        model: str | None = None,
    ) -> StructuredResult[T]: ...


def run_coro_sync(coro):
    """Run a coroutine from sync code outside an active event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    raise RuntimeError("Cannot use sync LLM wrapper while an event loop is running.")


class StructuredOutputExhaustedError(ValueError):
    """Raised when text->JSON parsing and repair attempts cannot satisfy the target schema."""


def _augment_repair_validation_errors(
    output_schema_name: str,
    errors: list[str],
) -> list[str]:
    augmented = list(errors)
    if output_schema_name != "EventExtractionOutput":
        return augmented

    if any(
        "Proposal events require terms" in error or "Money terms require at least one amount" in error
        for error in errors
    ):
        augmented.append(
            "Repair rule: proposal events must include an explicit per-share price, range, or enterprise value. "
            "If the cited block only mentions draft agreements, mark-ups, financing commitments, or other bid "
            "package materials without explicit economics, remove that proposal event."
        )
    if any("Input should be a valid decimal" in error for error in errors):
        augmented.append(
            "Repair rule: numeric money fields must be plain numbers only, without currency symbols, commas, or "
            "words such as million or billion. Convert textual amounts to numeric form or remove the invalid field."
        )
    return augmented


class BaseLLMBackend(ABC):
    provider: str
    model: str
    structured_mode: str

    def __init__(
        self,
        *,
        provider: str,
        model: str,
        structured_mode: str = DEFAULT_STRUCTURED_OUTPUT_MODE,
        max_validation_retries: int = LLM_JSON_REPAIR_ATTEMPTS,
    ) -> None:
        if structured_mode not in VALID_STRUCTURED_OUTPUT_MODES:
            raise ValueError(
                f"Invalid structured output mode {structured_mode!r}; expected one of {sorted(VALID_STRUCTURED_OUTPUT_MODES)}"
            )
        self.provider = provider
        self.model = model
        self.structured_mode = structured_mode
        self.max_validation_retries = max_validation_retries

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
        base_system = self._system_to_text(system)
        resolved_mode = self._resolve_structured_mode(output_schema)

        if resolved_mode == "provider_native":
            raw_text, usage = await self._ainvoke_provider_native(
                messages=messages,
                system=base_system,
                output_schema=output_schema,
                max_tokens=max_tokens,
                model=effective_model,
                cache=cache,
            )
            prompt_version = PromptPack.prompt_version(base_system)
            try:
                return self._build_structured_result(
                    output_schema=output_schema,
                    raw_text=raw_text,
                    usage=usage,
                    prompt_version=prompt_version,
                    repair_count=0,
                    structured_mode=resolved_mode,
                )
            except ValidationError as exc:
                repaired = await self._repair_loop(
                    original_text=raw_text,
                    initial_usage=usage,
                    validation_errors=self._format_validation_errors(exc),
                    output_schema=output_schema,
                    max_tokens=max_tokens,
                    model=effective_model,
                    prompt_version=prompt_version,
                    structured_mode=resolved_mode,
                )
                return repaired

        contracted_system = PromptPack.render_structured_system_prompt(base_system, output_schema)
        prompt_version = PromptPack.prompt_version(contracted_system)
        raw_text, usage = await self._agenerate_text(
            messages=messages,
            system=contracted_system,
            max_tokens=max_tokens,
            model=effective_model,
            cache=cache,
        )
        try:
            return self._build_structured_result(
                output_schema=output_schema,
                raw_text=raw_text,
                usage=usage,
                prompt_version=prompt_version,
                repair_count=0,
                structured_mode="prompted_json",
            )
        except ValidationError as exc:
            return await self._repair_loop(
                original_text=raw_text,
                initial_usage=usage,
                validation_errors=self._format_validation_errors(exc),
                output_schema=output_schema,
                max_tokens=max_tokens,
                model=effective_model,
                prompt_version=prompt_version,
                structured_mode="prompted_json",
            )

    async def arepair_structured(
        self,
        *,
        original_json: str,
        errors: list[str],
        output_schema: type[T],
        max_tokens: int,
        model: str | None = None,
    ) -> StructuredResult[T]:
        effective_model = model or self.model
        repair_system = PromptPack.render_structured_system_prompt(
            PromptPack.REPAIR_SYSTEM_PROMPT,
            output_schema,
        )
        prompt_version = PromptPack.prompt_version(repair_system)
        raw_text, usage = await self._agenerate_text(
            messages=[
                {
                    "role": "user",
                    "content": PromptPack.render_repair_user_message(
                        original_text=original_json,
                        extracted_json=extract_json_candidate(original_json),
                        validation_errors=_augment_repair_validation_errors(
                            output_schema.__name__,
                            errors,
                        ),
                    ),
                }
            ],
            system=repair_system,
            max_tokens=max_tokens,
            model=effective_model,
            cache=False,
        )
        return self._build_structured_result(
            output_schema=output_schema,
            raw_text=raw_text,
            usage=usage,
            prompt_version=prompt_version,
            repair_count=1,
            structured_mode="prompted_json",
        )

    async def _repair_loop(
        self,
        *,
        original_text: str,
        initial_usage: LLMUsage,
        validation_errors: list[str],
        output_schema: type[T],
        max_tokens: int,
        model: str,
        prompt_version: str,
        structured_mode: str,
    ) -> StructuredResult[T]:
        combined_usage = initial_usage
        current_text = original_text
        current_errors = validation_errors
        last_candidate = extract_json_candidate(original_text)

        for attempt in range(1, self.max_validation_retries + 1):
            repair_system = PromptPack.render_structured_system_prompt(
                PromptPack.REPAIR_SYSTEM_PROMPT,
                output_schema,
            )
            repair_messages = [
                {
                    "role": "user",
                    "content": PromptPack.render_repair_user_message(
                        original_text=current_text,
                        extracted_json=last_candidate,
                        validation_errors=_augment_repair_validation_errors(
                            output_schema.__name__,
                            current_errors,
                        ),
                    ),
                }
            ]
            repair_text, repair_usage = await self._agenerate_text(
                messages=repair_messages,
                system=repair_system,
                max_tokens=max_tokens,
                model=model,
                cache=False,
            )
            combined_usage = self._combine_usage(combined_usage, repair_usage)
            try:
                return self._build_structured_result(
                    output_schema=output_schema,
                    raw_text=repair_text,
                    usage=combined_usage,
                    prompt_version=prompt_version,
                    repair_count=attempt,
                    structured_mode=structured_mode,
                )
            except ValidationError as exc:
                current_text = repair_text
                last_candidate = extract_json_candidate(repair_text)
                current_errors = self._format_validation_errors(exc)

        error_preview = "; ".join(current_errors[:5])
        raise StructuredOutputExhaustedError(
            f"Unable to validate {output_schema.__name__} after {self.max_validation_retries} repair attempt(s): {error_preview}"
        )

    def _build_structured_result(
        self,
        *,
        output_schema: type[T],
        raw_text: str,
        usage: LLMUsage,
        prompt_version: str,
        repair_count: int,
        structured_mode: str,
    ) -> StructuredResult[T]:
        candidate_json = extract_json_candidate(raw_text)
        parsed_output = output_schema.model_validate_json(candidate_json)
        return StructuredResult(
            output=parsed_output,
            usage=usage,
            raw_json=candidate_json,
            prompt_version=prompt_version,
            raw_text=raw_text,
            repair_count=repair_count,
            structured_mode=structured_mode,
        )

    def _resolve_structured_mode(self, output_schema: type[BaseModel]) -> str:
        if self.structured_mode == "prompted_json":
            return "prompted_json"
        if self.structured_mode == "provider_native":
            if not self._supports_native_structured_output(output_schema):
                raise ValueError(
                    f"{self.provider} provider-native structured output is disabled for {output_schema.__name__}; "
                    "use --structured-mode prompted_json instead."
                )
            return "provider_native"
        if self.structured_mode == "auto":
            return "provider_native" if self._supports_native_structured_output(output_schema) else "prompted_json"
        raise ValueError(f"Unsupported structured mode: {self.structured_mode}")

    @abstractmethod
    async def _agenerate_text(
        self,
        *,
        messages: list[dict[str, Any]],
        system: str,
        max_tokens: int,
        model: str,
        cache: bool,
    ) -> tuple[str, LLMUsage]:
        raise NotImplementedError

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
        raise NotImplementedError(
            f"{self.provider} backend does not implement provider-native structured output."
        )

    @abstractmethod
    def _supports_native_structured_output(self, output_schema: type[BaseModel]) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def acount_tokens(
        self,
        *,
        messages: list[MessageParam],
        system: SystemPromptParam,
        model: str | None = None,
    ) -> int:
        raise NotImplementedError

    @staticmethod
    def _format_validation_errors(error: ValidationError) -> list[str]:
        formatted = []
        for issue in error.errors():
            path = ".".join(str(part) for part in issue["loc"])
            path_text = path or "<root>"
            formatted.append(f"{path_text}: {issue['msg']}")
        return formatted

    @staticmethod
    def _combine_usage(primary: LLMUsage, secondary: LLMUsage) -> LLMUsage:
        cost_values = [value for value in (primary.cost_usd, secondary.cost_usd) if value is not None]
        return LLMUsage(
            provider=secondary.provider or primary.provider,
            input_tokens=primary.input_tokens + secondary.input_tokens,
            cache_creation_input_tokens=(
                primary.cache_creation_input_tokens + secondary.cache_creation_input_tokens
            ),
            cache_read_input_tokens=(
                primary.cache_read_input_tokens + secondary.cache_read_input_tokens
            ),
            output_tokens=primary.output_tokens + secondary.output_tokens,
            cost_usd=sum(cost_values) if cost_values else None,
            latency_ms=primary.latency_ms + secondary.latency_ms,
            request_id=secondary.request_id,
            model=secondary.model,
        )

    @staticmethod
    def _system_to_text(system: SystemPromptParam) -> str:
        if isinstance(system, str):
            return system
        return json.dumps(system, sort_keys=True, default=str)
```

---

## pipeline/llm/anthropic_backend.py
```python
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
```

---

## pipeline/llm/openai_backend.py
```python
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
```

---

## pipeline/llm/factory.py
```python
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
from pipeline.llm.local_agent_backend import LocalAgentBackend
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
    if resolved_provider == "local_agent":
        return LocalAgentBackend(
            model=resolved_model,
            structured_mode=resolved_structured_mode,
        )
    raise AssertionError(f"Unhandled provider: {resolved_provider}")
```

---

## pipeline/llm/prompts.py
```python
from __future__ import annotations

import json
import re
from functools import lru_cache
from hashlib import sha256
from typing import Any

from pydantic import BaseModel

from pipeline.config import PROJECT_ROOT
from pipeline.llm.json_utils import schema_outline
from pipeline.models.source import ChronologyBlock, EvidenceItem


PROMPT_SPEC_PATH = PROJECT_ROOT / "docs" / "plans" / "2026-03-16-prompt-engineering-spec.md"


@lru_cache(maxsize=1)
def _prompt_spec_text() -> str:
    return PROMPT_SPEC_PATH.read_text(encoding="utf-8")


def _extract_fenced_block(heading: str) -> str:
    pattern = rf"## {re.escape(heading)}\n\n```(?:\w+)?\n(.*?)\n```"
    match = re.search(pattern, _prompt_spec_text(), re.DOTALL)
    if match is None:
        raise ValueError(f"Heading {heading!r} not found in prompt specification.")
    return match.group(1).strip()


def _serialize_for_prompt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, BaseModel):
        return json.dumps(value.model_dump(mode="json"), indent=2, sort_keys=True)
    if isinstance(value, list):
        normalized = [
            item.model_dump(mode="json") if isinstance(item, BaseModel) else item
            for item in value
        ]
        return json.dumps(normalized, indent=2, sort_keys=True, default=str)
    return str(value)


def _format_context_value(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


class PromptPack:
    ACTOR_SYSTEM_PROMPT = _extract_fenced_block("Actor Extraction System Prompt")
    EVENT_SYSTEM_PROMPT = _extract_fenced_block("Event Extraction System Prompt")
    RECOVERY_SYSTEM_PROMPT = _extract_fenced_block("Targeted Recovery Audit System Prompt")
    REPAIR_SYSTEM_PROMPT = _extract_fenced_block("JSON Repair System Prompt")

    @staticmethod
    def render_blocks(blocks: list[ChronologyBlock]) -> str:
        rendered_blocks = []
        for block in blocks:
            text = (block.clean_text or block.raw_text).strip().replace("\n", " ")
            rendered_blocks.append(
                f"{block.block_id} [L{block.start_line}-L{block.end_line}]: {text}"
            )
        return "\n".join(rendered_blocks)

    @staticmethod
    def render_evidence_items(evidence_items: list[EvidenceItem]) -> str:
        rendered_items = []
        for item in evidence_items:
            text = item.raw_text.strip().replace("\n", " ")
            rendered_items.append(
                f"{item.evidence_id} ({item.evidence_type.value}) [{item.document_id}:L{item.start_line}-L{item.end_line}]: {text}"
            )
        return "\n".join(rendered_items)

    @staticmethod
    def _render_evidence_section(evidence_items: list[EvidenceItem] | None) -> str:
        if not evidence_items:
            return ""
        return (
            "\n\n<cross_filing_evidence>\n"
            "Use evidence_id values from this appendix when a supporting fact comes from a non-chronology source.\n"
            f"{PromptPack.render_evidence_items(evidence_items)}\n"
            "</cross_filing_evidence>"
        )

    @staticmethod
    def render_actor_user_message(
        deal_context: dict[str, Any],
        blocks: list[ChronologyBlock],
        evidence_items: list[EvidenceItem] | None = None,
    ) -> str:
        return (
            "<deal_context>\n"
            f"deal_slug: {_format_context_value(deal_context.get('deal_slug'))}\n"
            f"target_name: {_format_context_value(deal_context.get('target_name'))}\n"
            f"seed_acquirer: {_format_context_value(deal_context.get('acquirer_seed'))}\n"
            "seed_announced_date: "
            f"{_format_context_value(deal_context.get('date_announced_seed'))}\n"
            "source_accession_number: "
            f"{_format_context_value(deal_context.get('accession_number'))}\n"
            f"source_form_type: {_format_context_value(deal_context.get('filing_type'))}\n"
            "</deal_context>\n\n"
            "<schema_notes>\n"
            "- first_mention_span will be resolved later from your evidence_refs\n"
            "- use block_id for chronology evidence and evidence_id for appendix evidence\n"
            "- return only the schema fields\n"
            "</schema_notes>\n\n"
            "<chronology_blocks>\n"
            f"{PromptPack.render_blocks(blocks)}\n"
            "</chronology_blocks>"
            f"{PromptPack._render_evidence_section(evidence_items)}"
        )

    @staticmethod
    def render_event_user_message(
        deal_context: dict[str, Any],
        actor_roster: list[BaseModel] | list[dict[str, Any]],
        blocks: list[ChronologyBlock],
        *,
        chunk_mode: str,
        chunk_id: str,
        prior_round_context: list[str] | str | None = None,
        evidence_items: list[EvidenceItem] | None = None,
    ) -> str:
        if isinstance(prior_round_context, list):
            prior_round_text = "\n".join(prior_round_context)
        else:
            prior_round_text = _serialize_for_prompt(prior_round_context)
        return (
            "<deal_context>\n"
            f"deal_slug: {_format_context_value(deal_context.get('deal_slug'))}\n"
            f"target_name: {_format_context_value(deal_context.get('target_name'))}\n"
            "source_accession_number: "
            f"{_format_context_value(deal_context.get('accession_number'))}\n"
            f"source_form_type: {_format_context_value(deal_context.get('filing_type'))}\n"
            f"chunk_mode: {chunk_mode}\n"
            f"chunk_id: {chunk_id}\n"
            "</deal_context>\n\n"
            "<actor_roster>\n"
            f"{_serialize_for_prompt(actor_roster)}\n"
            "</actor_roster>\n\n"
            "<prior_round_context>\n"
            f"{prior_round_text}\n"
            "</prior_round_context>\n\n"
            "<chronology_blocks>\n"
            f"{PromptPack.render_blocks(blocks)}\n"
            "</chronology_blocks>"
            f"{PromptPack._render_evidence_section(evidence_items)}"
        )

    @staticmethod
    def render_recovery_user_message(
        blocks: list[ChronologyBlock],
        extracted_events_summary: Any,
        evidence_items: list[EvidenceItem] | None = None,
    ) -> str:
        return (
            "<extracted_events_summary>\n"
            f"{_serialize_for_prompt(extracted_events_summary)}\n"
            "</extracted_events_summary>\n\n"
            "<chronology_blocks>\n"
            f"{PromptPack.render_blocks(blocks)}\n"
            "</chronology_blocks>"
            f"{PromptPack._render_evidence_section(evidence_items)}"
        )

    @staticmethod
    def render_structured_system_prompt(
        system_prompt: str,
        output_schema: type[BaseModel],
    ) -> str:
        return (
            f"{system_prompt}\n\n"
            "<json_output_contract>\n"
            "Return exactly one JSON object that matches the schema outline below.\n"
            "Do not wrap the JSON in markdown fences.\n"
            "Do not add prose before or after the JSON.\n"
            "If a fact is not supported by the provided filing text or evidence appendix, omit it rather than guessing.\n"
            "Use null only where the schema allows it.\n"
            "Schema outline:\n"
            f"{schema_outline(output_schema)}\n"
            "</json_output_contract>"
        )

    @staticmethod
    def render_repair_user_message(
        *,
        original_text: str,
        extracted_json: str,
        validation_errors: list[str],
    ) -> str:
        return (
            "<original_response>\n"
            f"{original_text}\n"
            "</original_response>\n\n"
            "<extracted_json_candidate>\n"
            f"{extracted_json}\n"
            "</extracted_json_candidate>\n\n"
            "<validation_errors>\n"
            f"{_serialize_for_prompt(validation_errors)}\n"
            "</validation_errors>\n\n"
            "Return corrected JSON only."
        )

    @staticmethod
    def prompt_version(prompt_text: str) -> str:
        return sha256(prompt_text.encode("utf-8")).hexdigest()
```

---

## pipeline/llm/token_budget.py
```python
from __future__ import annotations

from enum import StrEnum

from pipeline.llm.prompts import PromptPack
from pipeline.models.source import ChronologyBlock


class ComplexityClass(StrEnum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


async def count_chronology_tokens(backend, blocks: list[ChronologyBlock], model: str) -> int:
    return await backend.acount_tokens(
        messages=[{"role": "user", "content": PromptPack.render_blocks(blocks)}],
        system="",
        model=model,
    )


def classify_complexity(
    token_count: int,
    line_count: int,
    actor_count: int,
) -> ComplexityClass:
    if actor_count > 15 or token_count > 15_000 or line_count > 400:
        return ComplexityClass.COMPLEX
    if token_count <= 8_000 and line_count <= 150:
        return ComplexityClass.SIMPLE
    return ComplexityClass.MODERATE


def plan_event_chunks(
    blocks: list[ChronologyBlock],
    *,
    token_budget_per_chunk: int = 5_000,
    overlap_blocks: int = 1,
) -> list[list[ChronologyBlock]]:
    if not blocks:
        return []

    overlap_blocks = max(0, overlap_blocks)
    estimated_tokens = [_estimate_block_tokens(block) for block in blocks]
    chunks: list[list[ChronologyBlock]] = []
    start = 0

    while start < len(blocks):
        total = 0
        end = start
        while end < len(blocks):
            block_tokens = estimated_tokens[end]
            if end > start and total + block_tokens > token_budget_per_chunk:
                break
            total += block_tokens
            end += 1
        chunks.append(blocks[start:end])
        if end >= len(blocks):
            break
        start = max(end - overlap_blocks, start + 1)

    return chunks


def estimate_max_output_tokens(complexity: ComplexityClass, call_type: str) -> int:
    budgets = {
        "actor": {
            ComplexityClass.SIMPLE: 1_200,
            ComplexityClass.MODERATE: 1_800,
            ComplexityClass.COMPLEX: 2_400,
        },
        "event": {
            ComplexityClass.SIMPLE: 3_000,
            ComplexityClass.MODERATE: 5_000,
            ComplexityClass.COMPLEX: 7_000,
        },
        "recovery": {
            ComplexityClass.SIMPLE: 1_000,
            ComplexityClass.MODERATE: 1_500,
            ComplexityClass.COMPLEX: 2_000,
        },
        "repair": {
            ComplexityClass.SIMPLE: 1_000,
            ComplexityClass.MODERATE: 1_000,
            ComplexityClass.COMPLEX: 1_000,
        },
    }
    if call_type not in budgets:
        raise ValueError(f"Unsupported call_type: {call_type}")
    return budgets[call_type][complexity]


def _estimate_block_tokens(block: ChronologyBlock) -> int:
    text = (block.clean_text or block.raw_text).strip()
    return max(1, len(text) // 4)
```

---

## pipeline/llm/json_utils.py
```python
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
```
