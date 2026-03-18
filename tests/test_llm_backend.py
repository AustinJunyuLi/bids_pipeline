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
from pipeline.llm.backend import StructuredOutputExhaustedError, _augment_repair_validation_errors
from pipeline.llm.prompts import PromptPack
from pipeline.llm.schemas import ActorExtractionOutput, EventExtractionOutput, pydantic_to_anthropic_schema
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


class FakeAnthropicAsyncMessages:
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


class FakeAnthropicAsyncClient:
    def __init__(self, responses: list[SimpleNamespace] | None = None, *, token_count: int = 0) -> None:
        self.messages = FakeAnthropicAsyncMessages(responses=responses, token_count=token_count)


class FakeOpenAICompletions:
    def __init__(self, responses: list[SimpleNamespace] | None = None) -> None:
        self.responses = list(responses or [])
        self.create_calls: list[dict] = []

    async def create(self, **kwargs):
        self.create_calls.append(kwargs)
        if not self.responses:
            raise AssertionError("No fake responses queued for create().")
        return self.responses.pop(0)


class FakeOpenAIAsyncClient:
    def __init__(self, responses: list[SimpleNamespace] | None = None) -> None:
        self.chat = SimpleNamespace(completions=FakeOpenAICompletions(responses=responses))


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


def _mock_openai_response(
    payload: str,
    *,
    prompt_tokens: int = 120,
    completion_tokens: int = 24,
    request_id: str = "resp_test_123",
    model: str = "gpt-4.1-mini",
    output_text: str | None = None,
    finish_reason: str = "stop",
) -> SimpleNamespace:
    usage = SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    message = SimpleNamespace(content=payload)
    choice = SimpleNamespace(message=message, finish_reason=finish_reason)
    return SimpleNamespace(
        id=request_id,
        model=model,
        choices=[choice],
        usage=usage,
        output_text=output_text,
    )


def test_llm_exports_and_config_constants_exist():
    from pipeline.config import (
        ANTHROPIC_API_KEY_ENV,
        DEFAULT_CONCURRENCY_LIMIT,
        DEFAULT_STRUCTURED_OUTPUT_MODE,
        LLM_JSON_REPAIR_ATTEMPTS,
        LLM_MAX_RETRIES,
        OPENAI_API_KEY_ENV,
    )

    assert AnthropicBackend
    assert LLMBackend
    assert LLMUsage
    assert StructuredResult
    assert ANTHROPIC_API_KEY_ENV == "ANTHROPIC_API_KEY"
    assert OPENAI_API_KEY_ENV == "OPENAI_API_KEY"
    assert DEFAULT_CONCURRENCY_LIMIT == 8
    assert LLM_MAX_RETRIES == 3
    assert LLM_JSON_REPAIR_ATTEMPTS == 2
    assert DEFAULT_STRUCTURED_OUTPUT_MODE == "prompted_json"


def test_build_backend_factory_supports_both_providers(monkeypatch: pytest.MonkeyPatch):
    from pipeline.llm import OpenAIBackend, build_backend

    monkeypatch.setenv("BIDS_LLM_PROVIDER", "openai")
    backend = build_backend(async_client=FakeOpenAIAsyncClient())
    assert isinstance(backend, OpenAIBackend)

    monkeypatch.setenv("BIDS_LLM_PROVIDER", "anthropic")
    backend = build_backend(async_client=FakeAnthropicAsyncClient())
    assert isinstance(backend, AnthropicBackend)


def test_build_backend_factory_rejects_invalid_provider(monkeypatch: pytest.MonkeyPatch):
    from pipeline.llm import build_backend

    monkeypatch.setenv("BIDS_LLM_PROVIDER", "invalid_provider")

    with pytest.raises(ValueError, match="Unsupported provider"):
        build_backend()


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


def test_prompt_pack_requires_explicit_proposal_economics_and_contiguous_anchors():
    assert "Proposal events require explicit economics." in PromptPack.EVENT_SYSTEM_PROMPT
    assert "anchor_text must be a contiguous verbatim substring" in PromptPack.EVENT_SYSTEM_PROMPT
    assert "anchor_text must be a contiguous verbatim substring" in PromptPack.ACTOR_SYSTEM_PROMPT


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


def test_render_structured_system_prompt_adds_json_contract():
    rendered = PromptPack.render_structured_system_prompt("You are a tester.", TinyOutput)

    assert rendered.startswith("You are a tester.")
    assert "<json_output_contract>" in rendered
    assert "Return exactly one JSON object" in rendered
    assert "value: string" in rendered


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


def test_extract_json_candidate_handles_fenced_json():
    from pipeline.llm.json_utils import extract_json_candidate

    raw = "Here you go:\n```json\n{\n  \"value\": \"ok\"\n}\n```"
    assert extract_json_candidate(raw) == '{\n  "value": "ok"\n}'


def test_augment_repair_validation_errors_adds_event_schema_guidance():
    errors = [
        "events.21: Value error, Proposal events require terms",
        "events.22.terms.total_enterprise_value: Input should be a valid decimal",
    ]

    augmented = _augment_repair_validation_errors("EventExtractionOutput", errors)

    assert augmented[:2] == errors
    assert any("remove that proposal event" in message for message in augmented)
    assert any("numeric money fields must be plain numbers only" in message for message in augmented)


def test_extract_json_candidate_does_not_drop_to_nested_array_when_top_level_object_is_malformed():
    from pipeline.llm.json_utils import extract_json_candidate

    raw = '{\n  "events": [\n    {"value": "ok"}\n  ],\n  "exclusions":\n'
    assert extract_json_candidate(raw) == raw.strip()


def test_schema_profile_keeps_pipeline_schemas_off_anthropic_native_path():
    from pipeline.llm.schema_profile import anthropic_native_safe, profile_model_schema

    tiny_profile = profile_model_schema(TinyOutput)
    actor_profile = profile_model_schema(ActorExtractionOutput)
    event_profile = profile_model_schema(EventExtractionOutput)

    assert anthropic_native_safe(tiny_profile) is True
    assert anthropic_native_safe(actor_profile) is False
    assert anthropic_native_safe(event_profile) is False
    assert event_profile.optional_param_count > actor_profile.optional_param_count


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
        (7000, 250, 5, ComplexityClass.MODERATE),
        (9000, 100, 5, ComplexityClass.MODERATE),
        (9000, 250, 5, ComplexityClass.MODERATE),
        (16000, 100, 5, ComplexityClass.COMPLEX),
        (9000, 250, 16, ComplexityClass.COMPLEX),
    ],
)
def test_classify_complexity_respects_thresholds(token_count, line_count, actor_count, expected):
    assert classify_complexity(token_count, line_count, actor_count) == expected


def test_plan_event_chunks_uses_one_block_overlap():
    chunks = plan_event_chunks(_build_test_blocks(), token_budget_per_chunk=10, overlap_blocks=1)

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


def test_anthropic_prompted_json_mode_adds_contract_and_cache_control(mock_anthropic_response):
    client = FakeAnthropicAsyncClient(responses=[mock_anthropic_response('{"value": "ok"}')])
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
    assert "output_config" not in create_call or "format" not in create_call.get("output_config", {})
    assert "<json_output_contract>" in create_call["system"]
    assert result.structured_mode == "prompted_json"


def test_anthropic_auto_mode_uses_native_schema_for_tiny_output(mock_anthropic_response):
    client = FakeAnthropicAsyncClient(responses=[mock_anthropic_response('{"value": "ok"}')])
    backend = AnthropicBackend(
        async_client=client, model="claude-sonnet-4-20250514", structured_mode="auto"
    )

    asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=256,
        )
    )

    create_call = client.messages.create_calls[0]
    assert create_call["output_config"]["format"]["type"] == "json_schema"
    assert create_call["output_config"]["format"]["schema"]["additionalProperties"] is False


def test_anthropic_provider_native_mode_uses_native_schema_for_tiny_output(
    mock_anthropic_response,
):
    client = FakeAnthropicAsyncClient(responses=[mock_anthropic_response('{"value": "ok"}')])
    backend = AnthropicBackend(
        async_client=client,
        model="claude-sonnet-4-20250514",
        structured_mode="provider_native",
    )

    asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=256,
        )
    )

    create_call = client.messages.create_calls[0]
    assert create_call["output_config"]["format"]["type"] == "json_schema"
    assert create_call["output_config"]["format"]["schema"]["additionalProperties"] is False


def test_anthropic_auto_mode_falls_back_to_prompted_json_for_pipeline_schema(mock_anthropic_response):
    client = FakeAnthropicAsyncClient(
        responses=[
            mock_anthropic_response(
                '{"actors": [], "count_assertions": [], "unresolved_mentions": []}'
            )
        ]
    )
    backend = AnthropicBackend(
        async_client=client, model="claude-sonnet-4-20250514", structured_mode="auto"
    )

    asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=ActorExtractionOutput,
            max_tokens=256,
        )
    )

    create_call = client.messages.create_calls[0]
    assert "output_config" not in create_call or "format" not in create_call.get("output_config", {})
    assert "<json_output_contract>" in create_call["system"]


def test_anthropic_repairs_after_validation_error_without_native_schema(mock_anthropic_response):
    client = FakeAnthropicAsyncClient(
        responses=[
            mock_anthropic_response("{}"),
            mock_anthropic_response('```json\n{"value": "ok"}\n```', request_id="msg_repair_456"),
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
    assert result.repair_count == 1
    assert len(client.messages.create_calls) == 2
    assert PromptPack.REPAIR_SYSTEM_PROMPT in client.messages.create_calls[1]["system"]
    assert "format" not in client.messages.create_calls[1].get("output_config", {})


def test_anthropic_raises_structured_output_exhausted_error_after_repair_limit(
    mock_anthropic_response,
):
    client = FakeAnthropicAsyncClient(
        responses=[
            mock_anthropic_response("{}"),
            mock_anthropic_response("still not valid json"),
        ]
    )
    backend = AnthropicBackend(
        async_client=client,
        model="claude-sonnet-4-20250514",
        max_validation_retries=1,
    )

    with pytest.raises(StructuredOutputExhaustedError, match="Unable to validate TinyOutput"):
        asyncio.run(
            backend.ainvoke_structured(
                messages=[{"role": "user", "content": "hello"}],
                system="You are a tester.",
                output_schema=TinyOutput,
                max_tokens=256,
            )
        )


def test_anthropic_acount_tokens_uses_count_endpoint():
    client = FakeAnthropicAsyncClient(token_count=456)
    backend = AnthropicBackend(async_client=client, model="claude-sonnet-4-20250514")

    count = asyncio.run(
        backend.acount_tokens(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
        )
    )

    assert count == 456
    assert client.messages.count_calls[0]["model"] == "claude-sonnet-4-20250514"


def test_anthropic_sync_wrapper_invokes_structured_without_event_loop(mock_anthropic_response):
    client = FakeAnthropicAsyncClient(responses=[mock_anthropic_response('{"value": "ok"}')])
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


def test_effort_medium_is_sent_without_native_format(mock_anthropic_response):
    client = FakeAnthropicAsyncClient(responses=[mock_anthropic_response('{"value": "ok"}')])
    backend = AnthropicBackend(
        async_client=client, model="claude-sonnet-4-6", reasoning_effort="medium"
    )

    asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=256,
        )
    )

    create_call = client.messages.create_calls[0]
    assert create_call["output_config"]["effort"] == "medium"
    assert "format" not in create_call["output_config"]


def test_sonnet_46_pricing_is_registered():
    from pipeline.llm.anthropic_backend import PRICING

    assert "claude-sonnet-4-6" in PRICING


def test_openai_prompted_json_mode_uses_developer_message_and_reasoning_effort():
    from pipeline.llm import OpenAIBackend

    client = FakeOpenAIAsyncClient(responses=[_mock_openai_response('{"value": "ok"}')])
    backend = OpenAIBackend(
        async_client=client, model="gpt-4.1-mini", reasoning_effort="minimal"
    )

    result = asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=128,
        )
    )

    create_call = client.chat.completions.create_calls[0]
    assert result.output.value == "ok"
    assert create_call["messages"][0]["role"] == "developer"
    assert "<json_output_contract>" in create_call["messages"][0]["content"]
    assert create_call["reasoning_effort"] == "minimal"
    assert "response_format" not in create_call
    assert result.usage.provider == "openai"


def test_openai_prompted_json_mode_prefers_output_text():
    from pipeline.llm import OpenAIBackend

    client = FakeOpenAIAsyncClient(
        responses=[_mock_openai_response("ignored", output_text='{"value": "ok"}')]
    )
    backend = OpenAIBackend(async_client=client, model="gpt-4.1-mini")

    result = asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=128,
        )
    )

    assert result.output.value == "ok"


def test_openai_gpt5_omits_explicit_temperature():
    from pipeline.llm import OpenAIBackend

    client = FakeOpenAIAsyncClient(responses=[_mock_openai_response('{"value": "ok"}')])
    backend = OpenAIBackend(
        async_client=client,
        model="gpt-5.4",
        reasoning_effort="high",
    )

    asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=128,
        )
    )

    create_call = client.chat.completions.create_calls[0]
    assert create_call["reasoning_effort"] == "high"
    assert "temperature" not in create_call


def test_openai_raises_when_length_truncated_response_has_no_visible_text():
    from pipeline.llm import OpenAIBackend

    client = FakeOpenAIAsyncClient(
        responses=[
            _mock_openai_response(
                "",
                model="gpt-5.4-2026-03-05",
                completion_tokens=1800,
                finish_reason="length",
            )
        ]
    )
    backend = OpenAIBackend(
        async_client=client,
        model="gpt-5.4",
        reasoning_effort="high",
    )

    with pytest.raises(ValueError, match="exhausted max_completion_tokens"):
        asyncio.run(
            backend.ainvoke_structured(
                messages=[{"role": "user", "content": "hello"}],
                system="You are a tester.",
                output_schema=TinyOutput,
                max_tokens=1800,
            )
        )


def test_openai_auto_mode_uses_native_schema_for_tiny_output():
    from pipeline.llm import OpenAIBackend

    client = FakeOpenAIAsyncClient(responses=[_mock_openai_response('{"value": "ok"}')])
    backend = OpenAIBackend(async_client=client, model="gpt-4.1-mini", structured_mode="auto")

    asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=128,
        )
    )

    create_call = client.chat.completions.create_calls[0]
    assert create_call["response_format"]["type"] == "json_schema"
    assert create_call["response_format"]["json_schema"]["strict"] is True


def test_openai_repairs_after_validation_error():
    from pipeline.llm import OpenAIBackend

    client = FakeOpenAIAsyncClient(
        responses=[
            _mock_openai_response("{}"),
            _mock_openai_response('```json\n{"value": "ok"}\n```', request_id="resp_repair_456"),
        ]
    )
    backend = OpenAIBackend(async_client=client, model="gpt-4.1-mini")

    result = asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=128,
        )
    )

    assert result.output.value == "ok"
    assert result.repair_count == 1
    assert len(client.chat.completions.create_calls) == 2
    assert PromptPack.REPAIR_SYSTEM_PROMPT in client.chat.completions.create_calls[1]["messages"][0]["content"]


def test_openai_provider_native_mode_uses_native_schema_for_tiny_output():
    from pipeline.llm import OpenAIBackend

    client = FakeOpenAIAsyncClient(responses=[_mock_openai_response('{"value": "ok"}')])
    backend = OpenAIBackend(
        async_client=client,
        model="gpt-4.1-mini",
        structured_mode="provider_native",
    )

    asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=128,
        )
    )

    create_call = client.chat.completions.create_calls[0]
    assert create_call["response_format"]["type"] == "json_schema"
    assert create_call["response_format"]["json_schema"]["strict"] is True


def test_openai_count_tokens_uses_heuristic():
    from pipeline.llm import OpenAIBackend

    backend = OpenAIBackend(async_client=FakeOpenAIAsyncClient())

    count = asyncio.run(
        backend.acount_tokens(
            messages=[{"role": "user", "content": "hello world"}],
            system="You are a tester.",
        )
    )

    assert count > 0


def test_summarize_usage_includes_provider_and_repair_count():
    from pipeline.extract.utils import summarize_usage

    result = StructuredResult(
        output=TinyOutput(value="ok"),
        usage=LLMUsage(
            provider="anthropic",
            input_tokens=10,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
            output_tokens=5,
            cost_usd=0.01,
            latency_ms=123,
            request_id="req-1",
            model="claude-sonnet-4-20250514",
        ),
        raw_json='{"value": "ok"}',
        prompt_version="prompt-v1",
        repair_count=1,
        structured_mode="prompted_json",
    )

    summary = summarize_usage(result)
    assert summary["provider"] == "anthropic"
    assert summary["repair_count"] == 1
    assert summary["structured_mode"] == "prompted_json"
