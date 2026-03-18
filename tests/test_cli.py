import json
from types import SimpleNamespace

import pytest

from pipeline import cli


class RecordingStateStore:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def record_llm_call(self, **kwargs) -> None:
        self.calls.append(kwargs)


def test_cli_module_exposes_main():
    assert callable(cli.main)


def test_cli_supports_pipeline_stage_subcommands():
    parser = cli.build_parser()
    args = parser.parse_args(["source", "discover", "--deal", "imprivata"])

    assert args.command == "source"
    assert args.source_command == "discover"
    assert args.deal == ["imprivata"]


def test_cli_supports_raw_fetch_subcommand():
    parser = cli.build_parser()
    args = parser.parse_args(["raw", "fetch", "--deal", "imprivata", "--workers", "4"])

    assert args.command == "raw"
    assert args.raw_command == "fetch"
    assert args.deal == ["imprivata"]
    assert args.workers == 4


def test_cli_supports_preprocess_source_subcommand():
    parser = cli.build_parser()
    args = parser.parse_args(["preprocess", "source", "--deal", "zep", "--workers", "2"])

    assert args.command == "preprocess"
    assert args.preprocess_command == "source"
    assert args.deal == ["zep"]
    assert args.workers == 2


def test_cli_supports_validate_references_subcommand():
    parser = cli.build_parser()
    args = parser.parse_args(["validate", "references"])

    assert args.command == "validate"
    assert args.validate_command == "references"


def test_cli_extract_accepts_provider_model_effort_and_structured_mode():
    parser = cli.build_parser()
    args = parser.parse_args(
        [
            "extract",
            "actors",
            "--deal",
            "imprivata",
            "--provider",
            "openai",
            "--model",
            "gpt-4.1-mini",
            "--reasoning-effort",
            "minimal",
            "--structured-mode",
            "prompted_json",
        ]
    )

    assert args.command == "extract"
    assert args.extract_command == "actors"
    assert args.provider == "openai"
    assert args.model_override == "gpt-4.1-mini"
    assert args.reasoning_effort == "minimal"
    assert args.structured_mode == "prompted_json"


def test_cli_extract_effort_alias_maps_to_reasoning_effort():
    parser = cli.build_parser()
    args = parser.parse_args(
        [
            "extract",
            "events",
            "--deal",
            "imprivata",
            "--provider",
            "anthropic",
            "--effort",
            "medium",
        ]
    )

    assert args.provider == "anthropic"
    assert args.reasoning_effort == "medium"
    assert args.structured_mode is None


def test_cli_extract_rejects_invalid_provider():
    parser = cli.build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "extract",
                "actors",
                "--deal",
                "imprivata",
                "--provider",
                "invalid_provider",
            ]
        )


def test_record_usage_calls_records_nested_recovery_usage(tmp_path):
    usage_path = tmp_path / "event_usage.json"
    usage_path.write_text(
        json.dumps(
            {
                "calls": [
                    {
                        "provider": "openai",
                        "request_id": "req-main",
                        "model": "gpt-4.1-mini",
                        "prompt_version": "prompt-main",
                        "input_tokens": 10,
                        "cache_creation_input_tokens": 0,
                        "cache_read_input_tokens": 0,
                        "output_tokens": 5,
                        "cost_usd": 0.01,
                        "latency_ms": 20,
                    }
                ],
                "recovery": {
                    "provider": "openai",
                    "request_id": "req-recovery",
                    "model": "gpt-4.1-mini",
                    "prompt_version": "prompt-recovery",
                    "input_tokens": 6,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 0,
                    "output_tokens": 3,
                    "cost_usd": 0.02,
                    "latency_ms": 30,
                },
            }
        ),
        encoding="utf-8",
    )
    orchestrator = SimpleNamespace(state_store=RecordingStateStore())

    cli._record_usage_calls(
        orchestrator,
        run_id="run-1",
        deal_slug="imprivata",
        usage_path=usage_path,
        unit_name="event_extraction",
    )

    assert len(orchestrator.state_store.calls) == 2
    assert [call["unit_name"] for call in orchestrator.state_store.calls] == [
        "event_extraction",
        "event_extraction_recovery_audit",
    ]
    assert [call["provider"] for call in orchestrator.state_store.calls] == [
        "openai",
        "openai",
    ]
    assert [call["prompt_version"] for call in orchestrator.state_store.calls] == [
        "prompt-main",
        "prompt-recovery",
    ]


def test_record_usage_calls_defaults_missing_provider_to_unknown(tmp_path):
    usage_path = tmp_path / "actor_usage.json"
    usage_path.write_text(
        json.dumps(
            {
                "request_id": "req-actor",
                "model": "claude-sonnet-4-6",
                "prompt_version": "prompt-actor",
                "input_tokens": 8,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "output_tokens": 4,
                "cost_usd": 0.01,
                "latency_ms": 12,
            }
        ),
        encoding="utf-8",
    )
    orchestrator = SimpleNamespace(state_store=RecordingStateStore())

    cli._record_usage_calls(
        orchestrator,
        run_id="run-1",
        deal_slug="imprivata",
        usage_path=usage_path,
        unit_name="actor_extraction",
    )

    assert len(orchestrator.state_store.calls) == 1
    assert orchestrator.state_store.calls[0]["provider"] == "unknown"
