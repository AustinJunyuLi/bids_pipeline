from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Generic, Protocol, TypeVar

from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)
MessageParam = dict[str, Any]
SystemPromptParam = str | list[dict[str, Any]]


@dataclass(slots=True)
class LLMUsage:
    input_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int
    request_id: str
    model: str


@dataclass(slots=True)
class StructuredResult(Generic[T]):
    output: T
    usage: LLMUsage
    raw_json: str
    prompt_version: str


class LLMBackend(Protocol):
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
