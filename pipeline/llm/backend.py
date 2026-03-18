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
