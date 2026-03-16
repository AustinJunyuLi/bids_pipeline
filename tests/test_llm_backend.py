from __future__ import annotations

import asyncio
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import BaseModel, ConfigDict

from pipeline.config import PROJECT_ROOT
from pipeline.models.source import ChronologyBlock

from pipeline.llm import AnthropicBackend, LLMBackend, LLMUsage, StructuredResult
from pipeline.llm.prompts import PromptPack
from pipeline.llm.schemas import ActorExtractionOutput, pydantic_to_anthropic_schema
from pipeline.llm.token_budget import (
    ComplexityClass,
    classify_complexity,
    count_chronology_tokens,
    estimate_max_output_tokens,
    plan_event_chunks,
)


PROMPT_SPEC_PATH = PROJECT_ROOT / "docs" / "plans" / "2026-03-16-prompt-engineering-spec.md"


class TinyOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str


class FakeAsyncMessages:
    def __init__(self, responses: list[SimpleNamespace] | None = None, *, token_count: int = 0) -> None:
        self.responses = list(responses or [])
        self.token_count = token_count
        self.create_calls: list[dict] = []
        self.count_calls: list[dict] = []

    async def create(self, **kwargs):
        self.create_calls.append(kwargs)
        if not self.responses:
            raise AssertionError("No fake responses queued for create().")
        return self.responses.pop(0)

    async def count_tokens(self, **kwargs):
        self.count_calls.append(kwargs)
        return SimpleNamespace(input_tokens=self.token_count)


class FakeAsyncClient:
    def __init__(self, responses: list[SimpleNamespace] | None = None, *, token_count: int = 0) -> None:
        self.messages = FakeAsyncMessages(responses=responses, token_count=token_count)


class RecordingTokenBackend:
    def __init__(self, token_count: int) -> None:
        self.token_count = token_count
        self.calls: list[dict] = []

    async def acount_tokens(self, *, messages, system, model=None):
        self.calls.append({"messages": messages, "system": system, "model": model})
        return self.token_count


class ConcurrencyMessages:
    def __init__(self, response_factory) -> None:
        self.response_factory = response_factory
        self.active = 0
        self.max_active = 0
        self.create_calls: list[dict] = []

    async def create(self, **kwargs):
        self.create_calls.append(kwargs)
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0.01)
        self.active -= 1
        return self.response_factory('{"value": "ok"}')

    async def count_tokens(self, **kwargs):
        return SimpleNamespace(input_tokens=123)


class ConcurrencyClient:
    def __init__(self, response_factory) -> None:
        self.messages = ConcurrencyMessages(response_factory)


def _contains_key(value, key: str) -> bool:
    if isinstance(value, dict):
        if key in value:
            return True
        return any(_contains_key(child, key) for child in value.values())
    if isinstance(value, list):
        return any(_contains_key(child, key) for child in value)
    return False


def _extract_fenced_block(markdown_text: str, heading: str) -> str:
    pattern = rf"## {re.escape(heading)}\n\n```(?:\w+)?\n(.*?)\n```"
    match = re.search(pattern, markdown_text, re.DOTALL)
    assert match is not None, f"Heading {heading!r} not found in prompt spec."
    return match.group(1).strip()


def _build_test_blocks() -> list[ChronologyBlock]:
    blocks: list[ChronologyBlock] = []
    for index in range(4):
        block_id = f"B{index + 1:03d}"
        blocks.append(
            ChronologyBlock(
                block_id=block_id,
                document_id="doc-1",
                ordinal=index + 1,
                start_line=100 + index,
                end_line=100 + index,
                raw_text="alpha beta gamma delta",
                clean_text="alpha beta gamma delta",
                is_heading=False,
            )
        )
    return blocks


def test_llm_exports_and_config_constants_exist():
    from pipeline.config import ANTHROPIC_API_KEY_ENV, DEFAULT_CONCURRENCY_LIMIT, LLM_MAX_RETRIES

    assert AnthropicBackend
    assert LLMBackend
    assert LLMUsage
    assert StructuredResult
    assert ANTHROPIC_API_KEY_ENV == "ANTHROPIC_API_KEY"
    assert DEFAULT_CONCURRENCY_LIMIT == 8
    assert LLM_MAX_RETRIES == 3


def test_prompt_pack_uses_verbatim_system_prompts_from_spec():
    spec_text = PROMPT_SPEC_PATH.read_text()

    assert PromptPack.ACTOR_SYSTEM_PROMPT == _extract_fenced_block(
        spec_text, "Actor Extraction System Prompt"
    )
    assert PromptPack.EVENT_SYSTEM_PROMPT == _extract_fenced_block(
        spec_text, "Event Extraction System Prompt"
    )
    assert PromptPack.RECOVERY_SYSTEM_PROMPT == _extract_fenced_block(
        spec_text, "Targeted Recovery Audit System Prompt"
    )
    assert PromptPack.REPAIR_SYSTEM_PROMPT == _extract_fenced_block(
        spec_text, "JSON Repair System Prompt"
    )


def test_render_actor_user_message_includes_context_and_blocks(sample_blocks):
    rendered = PromptPack.render_actor_user_message(
        {
            "deal_slug": "imprivata",
            "target_name": "Imprivata, Inc.",
            "acquirer_seed": "Thoma Bravo",
            "date_announced_seed": "2016-07-11",
            "accession_number": "0001193125-16-677939",
            "filing_type": "DEFM14A",
        },
        sample_blocks,
    )

    assert "<deal_context>" in rendered
    assert "deal_slug: imprivata" in rendered
    assert "source_accession_number: 0001193125-16-677939" in rendered
    assert "B001 [L1200-L1202]:" in rendered
    assert "B002 [L1203-L1205]:" in rendered


def test_render_event_user_message_serializes_actor_roster_and_chunk_context(
    sample_blocks, sample_actor_roster
):
    rendered = PromptPack.render_event_user_message(
        {
            "deal_slug": "imprivata",
            "target_name": "Imprivata, Inc.",
            "accession_number": "0001193125-16-677939",
            "filing_type": "DEFM14A",
        },
        sample_actor_roster,
        sample_blocks,
        chunk_mode="chunked",
        chunk_id="chunk-2",
        prior_round_context=["final_round_ann on July 1, 2016"],
    )

    assert "chunk_mode: chunked" in rendered
    assert "chunk_id: chunk-2" in rendered
    assert '"actor_id": "party-a"' in rendered
    assert "final_round_ann on July 1, 2016" in rendered


def test_prompt_version_is_stable_for_same_text():
    version_one = PromptPack.prompt_version("hello world")
    version_two = PromptPack.prompt_version("hello world")
    version_three = PromptPack.prompt_version("different text")

    assert version_one == version_two
    assert version_one != version_three
    assert re.fullmatch(r"[0-9a-f]{64}", version_one)


def test_pydantic_to_anthropic_schema_inlines_nested_models():
    schema = pydantic_to_anthropic_schema(ActorExtractionOutput)

    assert "$defs" not in schema
    assert not _contains_key(schema, "$ref")
    assert schema["additionalProperties"] is False
    actor_schema = schema["properties"]["actors"]["items"]
    assert actor_schema["additionalProperties"] is False
    evidence_ref_schema = actor_schema["properties"]["evidence_refs"]["items"]
    block_id_schema = evidence_ref_schema["properties"]["block_id"]
    assert any(option.get("type") == "string" for option in block_id_schema.get("anyOf", [])) or block_id_schema.get("type") == "string"


def test_count_chronology_tokens_renders_blocks_for_backend(sample_blocks):
    backend = RecordingTokenBackend(token_count=321)

    count = asyncio.run(
        count_chronology_tokens(backend, sample_blocks, model="claude-sonnet-4-20250514")
    )

    assert count == 321
    assert backend.calls[0]["system"] == ""
    assert "B001 [L1200-L1202]:" in backend.calls[0]["messages"][0]["content"]


@pytest.mark.parametrize(
    ("token_count", "line_count", "actor_count", "expected"),
    [
        (7000, 250, 5, ComplexityClass.SIMPLE),
        (9000, 100, 5, ComplexityClass.SIMPLE),
        (9000, 250, 5, ComplexityClass.MODERATE),
        (16000, 100, 5, ComplexityClass.COMPLEX),
        (9000, 250, 16, ComplexityClass.COMPLEX),
    ],
)
def test_classify_complexity_respects_thresholds(token_count, line_count, actor_count, expected):
    assert classify_complexity(token_count, line_count, actor_count) == expected


def test_plan_event_chunks_uses_one_block_overlap():
    chunks = plan_event_chunks(_build_test_blocks(), token_budget_per_chunk=8, overlap_blocks=1)

    assert [[block.block_id for block in chunk] for chunk in chunks] == [
        ["B001", "B002"],
        ["B002", "B003"],
        ["B003", "B004"],
    ]


def test_estimate_max_output_tokens_scales_with_complexity():
    simple_actor = estimate_max_output_tokens(ComplexityClass.SIMPLE, "actor")
    simple_event = estimate_max_output_tokens(ComplexityClass.SIMPLE, "event")
    complex_event = estimate_max_output_tokens(ComplexityClass.COMPLEX, "event")

    assert simple_actor > 0
    assert simple_event >= simple_actor
    assert complex_event > simple_event


def test_ainvoke_structured_sends_output_config_and_cache_control(mock_anthropic_response):
    client = FakeAsyncClient(responses=[mock_anthropic_response('{"value": "ok"}')])
    backend = AnthropicBackend(async_client=client, model="claude-sonnet-4-20250514")

    result = asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=256,
        )
    )

    create_call = client.messages.create_calls[0]
    assert result.output.value == "ok"
    assert re.fullmatch(r"[0-9a-f]{64}", result.prompt_version)
    assert create_call["cache_control"] == {"type": "ephemeral"}
    assert create_call["output_config"]["format"]["type"] == "json_schema"
    assert create_call["output_config"]["format"]["schema"]["additionalProperties"] is False


def test_ainvoke_structured_omits_cache_control_when_cache_disabled(mock_anthropic_response):
    client = FakeAsyncClient(responses=[mock_anthropic_response('{"value": "ok"}')])
    backend = AnthropicBackend(async_client=client, model="claude-sonnet-4-20250514")

    asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=256,
            cache=False,
        )
    )

    create_call = client.messages.create_calls[0]
    assert "cache_control" not in create_call


def test_ainvoke_structured_parses_usage_and_cost(mock_anthropic_response):
    response = mock_anthropic_response(
        '{"value": "ok"}',
        input_tokens=1_000,
        cache_creation_input_tokens=500,
        cache_read_input_tokens=100,
        output_tokens=200,
    )
    client = FakeAsyncClient(responses=[response])
    backend = AnthropicBackend(async_client=client, model="claude-sonnet-4-20250514")

    result = asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=256,
        )
    )

    expected_cost = (
        (1_000 * 3.0) + (500 * 3.75) + (100 * 0.30) + (200 * 15.0)
    ) / 1_000_000
    assert result.usage.input_tokens == 1_000
    assert result.usage.cache_creation_input_tokens == 500
    assert result.usage.cache_read_input_tokens == 100
    assert result.usage.output_tokens == 200
    assert result.usage.cost_usd == pytest.approx(expected_cost)


def test_unknown_model_cost_falls_back_to_default_pricing(mock_anthropic_response):
    response = mock_anthropic_response(
        '{"value": "ok"}',
        input_tokens=1_000,
        output_tokens=200,
        model="claude-custom-test-model",
    )
    client = FakeAsyncClient(responses=[response])
    backend = AnthropicBackend(async_client=client, model="claude-custom-test-model")

    result = asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=256,
        )
    )

    expected_cost = ((1_000 * 3.0) + (200 * 15.0)) / 1_000_000
    assert result.usage.cost_usd == pytest.approx(expected_cost)


def test_ainvoke_structured_repairs_after_validation_error(mock_anthropic_response):
    client = FakeAsyncClient(
        responses=[
            mock_anthropic_response("{}"),
            mock_anthropic_response('{"value": "ok"}', request_id="msg_repair_456"),
        ]
    )
    backend = AnthropicBackend(async_client=client, model="claude-sonnet-4-20250514")

    result = asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=256,
        )
    )

    assert result.output.value == "ok"
    assert len(client.messages.create_calls) == 2
    assert client.messages.create_calls[1]["system"] == PromptPack.REPAIR_SYSTEM_PROMPT


def test_acount_tokens_uses_count_endpoint():
    client = FakeAsyncClient(token_count=456)
    backend = AnthropicBackend(async_client=client, model="claude-sonnet-4-20250514")

    count = asyncio.run(
        backend.acount_tokens(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
        )
    )

    assert count == 456
    assert client.messages.count_calls[0]["model"] == "claude-sonnet-4-20250514"


def test_sync_wrapper_invokes_structured_without_event_loop(mock_anthropic_response):
    client = FakeAsyncClient(responses=[mock_anthropic_response('{"value": "ok"}')])
    backend = AnthropicBackend(async_client=client, model="claude-sonnet-4-20250514")

    result = backend.invoke_structured(
        messages=[{"role": "user", "content": "hello"}],
        system="You are a tester.",
        output_schema=TinyOutput,
        max_tokens=256,
    )

    assert result.output.value == "ok"


def test_concurrency_limit_caps_parallel_requests(mock_anthropic_response):
    client = ConcurrencyClient(mock_anthropic_response)
    backend = AnthropicBackend(
        async_client=client,
        model="claude-sonnet-4-20250514",
        concurrency_limit=2,
    )

    async def invoke_many() -> None:
        await asyncio.gather(
            *[
                backend.ainvoke_structured(
                    messages=[{"role": "user", "content": f"hello-{idx}"}],
                    system="You are a tester.",
                    output_schema=TinyOutput,
                    max_tokens=128,
                )
                for idx in range(5)
            ]
        )

    asyncio.run(invoke_many())

    assert client.messages.max_active <= 2
