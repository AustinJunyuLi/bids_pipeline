"""Tests for the NewAPI/OpenAI structured LLM wrapper."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from skill_pipeline.core.llm import _REPO_ROOT, _get_client, invoke_structured


class SampleOutput(BaseModel):
    name: str
    value: int


def _mock_chat_response(content: str, finish_reason: str = "stop") -> MagicMock:
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    choice.finish_reason = finish_reason
    response = MagicMock()
    response.choices = [choice]
    return response


def test_invoke_structured_returns_validated_model() -> None:
    with patch("skill_pipeline.core.llm._get_client") as mock_client_fn:
        client = MagicMock()
        mock_client_fn.return_value = client
        client.chat.completions.create.return_value = _mock_chat_response(
            '{"name": "test", "value": 42}'
        )

        result = invoke_structured(
            system_prompt="You are a test.",
            user_message="Return a sample.",
            output_model=SampleOutput,
        )

        assert isinstance(result, SampleOutput)
        assert result.name == "test"
        assert result.value == 42
        assert client.chat.completions.create.call_count == 1


def test_invoke_structured_retries_on_validation_error_then_returns_model() -> None:
    with patch("skill_pipeline.core.llm._get_client") as mock_client_fn:
        client = MagicMock()
        mock_client_fn.return_value = client
        client.chat.completions.create.side_effect = [
            _mock_chat_response('{"name": "test"}'),
            _mock_chat_response('{"name": "test", "value": 42}'),
        ]

        result = invoke_structured(
            system_prompt="You are a test.",
            user_message="Return a sample.",
            output_model=SampleOutput,
        )

        assert isinstance(result, SampleOutput)
        assert result.name == "test"
        assert result.value == 42
        assert client.chat.completions.create.call_count == 2


def test_invoke_structured_retries_once_then_raises() -> None:
    with patch("skill_pipeline.core.llm._get_client") as mock_client_fn:
        client = MagicMock()
        mock_client_fn.return_value = client
        client.chat.completions.create.side_effect = [
            _mock_chat_response('{"name": "test"}'),
            _mock_chat_response('{"name": "test"}'),
        ]

        with pytest.raises(ValueError) as excinfo:
            invoke_structured(
                system_prompt="You are a test.",
                user_message="Return a sample.",
                output_model=SampleOutput,
            )

        assert "validation" in str(excinfo.value).lower()
        assert client.chat.completions.create.call_count == 2


def test_get_client_loads_repo_local_env_file(tmp_path, monkeypatch) -> None:
    from skill_pipeline.core import llm

    env_path = tmp_path / ".env.local"
    env_path.write_text(
        (
            "NEWAPI_API_KEY=test-key\n"
            "NEWAPI_BASE_URL=https://www.linkflow.run/v1\n"
            "NEWAPI_MODEL=gpt-5.4\n"
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("NEWAPI_API_KEY", raising=False)
    monkeypatch.delenv("NEWAPI_BASE_URL", raising=False)
    monkeypatch.delenv("NEWAPI_MODEL", raising=False)

    llm._env_loaded = False
    with (
        patch("skill_pipeline.core.llm._REPO_ROOT", tmp_path),
        patch("skill_pipeline.core.llm._openai_client_class") as mock_openai_class,
    ):
        _get_client()

    mock_openai_class.assert_called_once_with()
    mock_openai_class.return_value.assert_called_once_with(
        api_key="test-key",
        base_url="https://www.linkflow.run/v1",
    )
    llm._env_loaded = False


def test_llm_repo_root_defaults_to_repo_root() -> None:
    assert _REPO_ROOT == Path(__file__).resolve().parents[1]


def test_get_client_uses_linkflow_default_base_url(monkeypatch) -> None:
    monkeypatch.setenv("NEWAPI_API_KEY", "test-key")
    monkeypatch.delenv("NEWAPI_BASE_URL", raising=False)

    with patch("skill_pipeline.core.llm._openai_client_class") as mock_openai_class:
        _get_client()

    mock_openai_class.assert_called_once_with()
    mock_openai_class.return_value.assert_called_once_with(
        api_key="test-key",
        base_url="https://www.linkflow.run/v1",
    )


def test_invoke_structured_uses_env_reasoning_and_priority_service_tier() -> None:
    with (
        patch("skill_pipeline.core.llm._get_client") as mock_client_fn,
        patch.dict(
            "os.environ",
            {
                "NEWAPI_MODEL": "gpt-5.4",
                "NEWAPI_REASONING_EFFORT": "xhigh",
                "NEWAPI_SERVICE_TIER": "priority",
            },
            clear=False,
        ),
    ):
        client = MagicMock()
        mock_client_fn.return_value = client
        client.chat.completions.create.return_value = _mock_chat_response(
            '{"name": "test", "value": 42}'
        )

        result = invoke_structured(
            system_prompt="You are a test.",
            user_message="Return a sample.",
            output_model=SampleOutput,
        )

        assert result.value == 42
        kwargs = client.chat.completions.create.call_args.kwargs
        assert kwargs["reasoning_effort"] == "xhigh"
        assert kwargs["service_tier"] == "priority"
        assert "max_completion_tokens" not in kwargs


def test_invoke_structured_raises_on_truncation() -> None:
    with patch("skill_pipeline.core.llm._get_client") as mock_client_fn:
        client = MagicMock()
        mock_client_fn.return_value = client
        client.chat.completions.create.return_value = _mock_chat_response(
            '{"name": "test", "val', "length"
        )

        with pytest.raises(ValueError, match="truncated"):
            invoke_structured(
                system_prompt="You are a test.",
                user_message="Return a sample.",
                output_model=SampleOutput,
            )

        # Should NOT retry — truncation is not a validation error
        assert client.chat.completions.create.call_count == 1


def test_invoke_structured_allows_explicit_token_cap_override() -> None:
    with patch("skill_pipeline.core.llm._get_client") as mock_client_fn:
        client = MagicMock()
        mock_client_fn.return_value = client
        client.chat.completions.create.return_value = _mock_chat_response(
            '{"name": "test", "value": 42}'
        )

        result = invoke_structured(
            system_prompt="You are a test.",
            user_message="Return a sample.",
            output_model=SampleOutput,
            max_output_tokens=2048,
        )

        assert result.value == 42
        kwargs = client.chat.completions.create.call_args.kwargs
        assert kwargs["max_completion_tokens"] == 2048


def test_load_local_env_reads_file_only_once(tmp_path, monkeypatch) -> None:
    from skill_pipeline.core import llm

    # Create a single .env file; .env.local intentionally absent
    env_path = tmp_path / ".env"
    env_path.write_text("TEST_SENTINEL_VAR=sentinel-value\n", encoding="utf-8")
    monkeypatch.delenv("TEST_SENTINEL_VAR", raising=False)

    read_count = 0
    original_read_text = Path.read_text

    def counting_read_text(self, *args, **kwargs):
        nonlocal read_count
        read_count += 1
        return original_read_text(self, *args, **kwargs)

    llm._env_loaded = False

    with (
        patch("skill_pipeline.core.llm._REPO_ROOT", tmp_path),
        patch.object(Path, "read_text", counting_read_text),
    ):
        llm._load_local_env()
        first_count = read_count

        llm._load_local_env()
        llm._load_local_env()

        # Calls 2 and 3 should not have read any files
        assert read_count == first_count

    # Reset for other tests
    llm._env_loaded = False
