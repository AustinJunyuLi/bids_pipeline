from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from scripts import stress_linkflow_backend


def test_build_parser_defaults() -> None:
    parser = stress_linkflow_backend.build_parser()
    args = parser.parse_args([])

    assert args.requests_per_scenario == 4
    assert args.concurrency == 2
    assert args.output is None


def test_build_scenarios_contains_small_medium_large() -> None:
    scenarios = stress_linkflow_backend.build_scenarios(
        requests_per_scenario=5,
        concurrency=3,
    )

    assert [scenario.name for scenario in scenarios] == ["small", "medium", "large"]
    assert scenarios[0].request_count == 5
    assert scenarios[1].prompt_chars > scenarios[0].prompt_chars
    assert scenarios[2].prompt_chars > scenarios[1].prompt_chars
    assert scenarios[2].concurrency == 3


def test_main_writes_report_without_hitting_network(tmp_path: Path) -> None:
    report_path = tmp_path / "load_report.json"

    fake_report = {
        "model": "gpt-5.4",
        "base_url": "https://www.linkflow.run/v1",
        "overall": {"total_requests": 3, "successes": 3, "failures": 0},
        "scenarios": [
            {
                "name": "small",
                "request_count": 1,
                "success_count": 1,
                "failure_count": 0,
                "latency_ms_p50": 100.0,
                "latency_ms_p95": 100.0,
                "errors": [],
            }
        ],
    }

    with patch(
        "scripts.stress_linkflow_backend.run_suite",
        return_value=fake_report,
    ):
        result = stress_linkflow_backend.main(
            ["--output", str(report_path), "--requests-per-scenario", "1"]
        )

    assert result == 0
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["overall"]["total_requests"] == 3
    assert payload["scenarios"][0]["name"] == "small"


def test_run_request_uses_wrapper_backend_defaults() -> None:
    scenario = stress_linkflow_backend.build_scenarios(
        requests_per_scenario=1,
        concurrency=1,
    )[0]
    payload = stress_linkflow_backend._payload_text(scenario.prompt_chars)
    fake_response = stress_linkflow_backend.ProbeResponse(
        scenario=scenario.name,
        request_id="small-001",
        digest=hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12],
        payload_chars=len(payload),
        verdict="ok",
    )

    with patch(
        "scripts.stress_linkflow_backend.invoke_structured",
        return_value=fake_response,
    ) as mock_invoke:
        record = stress_linkflow_backend._run_request(
            scenario,
            1,
            model="gpt-5.4",
        )

    assert record["status"] == "success"
    kwargs = mock_invoke.call_args.kwargs
    assert "reasoning_effort" not in kwargs
    assert "max_output_tokens" not in kwargs


def test_script_runs_as_direct_file() -> None:
    script_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "stress_linkflow_backend.py"
    )
    result = subprocess.run(
        [sys.executable, str(script_path), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "requests-per-scenario" in result.stdout
