"""Tests for the NewAPI/OpenAI structured LLM wrapper."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from skill_pipeline.llm import invoke_structured


class SampleOutput(BaseModel):
    name: str
    value: int


def _mock_chat_response(content: str) -> MagicMock:
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


def test_invoke_structured_returns_validated_model() -> None:
    with patch("skill_pipeline.llm._get_client") as mock_client_fn:
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
    with patch("skill_pipeline.llm._get_client") as mock_client_fn:
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
    with patch("skill_pipeline.llm._get_client") as mock_client_fn:
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
