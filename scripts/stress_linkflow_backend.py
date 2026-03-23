from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Literal

from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from skill_pipeline.core.llm import (  # noqa: E402
    _DEFAULT_BASE_URL,
    _DEFAULT_MODEL,
    _load_local_env,
    invoke_structured,
)


@dataclass(frozen=True)
class ScenarioConfig:
    name: str
    prompt_chars: int
    request_count: int
    concurrency: int


class ProbeResponse(BaseModel):
    scenario: str
    request_id: str
    digest: str
    payload_chars: int
    verdict: Literal["ok"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python scripts/stress_linkflow_backend.py",
        description="Standalone real-backend load test for Linkflow/GPT-5.4 via skill_pipeline.llm.",
    )
    parser.add_argument("--requests-per-scenario", type=int, default=4)
    parser.add_argument("--concurrency", type=int, default=2)
    parser.add_argument("--model", default=None)
    parser.add_argument("--output", type=Path, default=None)
    return parser


def build_scenarios(*, requests_per_scenario: int, concurrency: int) -> list[ScenarioConfig]:
    return [
        ScenarioConfig(
            name="small",
            prompt_chars=2_000,
            request_count=requests_per_scenario,
            concurrency=concurrency,
        ),
        ScenarioConfig(
            name="medium",
            prompt_chars=16_000,
            request_count=requests_per_scenario,
            concurrency=concurrency,
        ),
        ScenarioConfig(
            name="large",
            prompt_chars=64_000,
            request_count=requests_per_scenario,
            concurrency=concurrency,
        ),
    ]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = round((len(ordered) - 1) * percentile)
    return ordered[index]


def _payload_text(prompt_chars: int) -> str:
    base = (
        "Merger background chronology. Party A contacted the Company. "
        "The board considered strategic alternatives. "
        "Party A submitted an indication of interest. "
    )
    repeated = (base * ((prompt_chars // len(base)) + 1))[:prompt_chars]
    return repeated


def _run_request(
    scenario: ScenarioConfig,
    request_index: int,
    *,
    model: str | None,
) -> dict[str, object]:
    payload = _payload_text(scenario.prompt_chars)
    request_id = f"{scenario.name}-{request_index:03d}"
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    system_prompt = (
        "You are a backend load-test probe. "
        "Return the metadata exactly as provided. "
        "Do not summarize the payload."
    )
    user_message = (
        f"scenario={scenario.name}\n"
        f"request_id={request_id}\n"
        f"digest={digest}\n"
        f"payload_chars={len(payload)}\n"
        f"<payload>\n{payload}\n</payload>"
    )

    started = perf_counter()
    try:
        response = invoke_structured(
            system_prompt=system_prompt,
            user_message=user_message,
            output_model=ProbeResponse,
            model=model,
        )
        latency_ms = (perf_counter() - started) * 1000
        if response.scenario != scenario.name:
            raise ValueError(
                f"Scenario echo mismatch: expected {scenario.name}, got {response.scenario}"
            )
        if response.request_id != request_id:
            raise ValueError(
                f"Request id echo mismatch: expected {request_id}, got {response.request_id}"
            )
        if response.digest != digest:
            raise ValueError(f"Digest echo mismatch: expected {digest}, got {response.digest}")
        if response.payload_chars != len(payload):
            raise ValueError(
                f"Payload length mismatch: expected {len(payload)}, got {response.payload_chars}"
            )
        return {
            "scenario": scenario.name,
            "request_id": request_id,
            "status": "success",
            "latency_ms": round(latency_ms, 2),
            "error": None,
        }
    except Exception as exc:  # pragma: no cover - exercised by real backend runs
        latency_ms = (perf_counter() - started) * 1000
        return {
            "scenario": scenario.name,
            "request_id": request_id,
            "status": "failure",
            "latency_ms": round(latency_ms, 2),
            "error": str(exc),
        }


def _summarize_scenario(scenario: ScenarioConfig, records: list[dict[str, object]]) -> dict[str, object]:
    latencies = [
        float(record["latency_ms"])
        for record in records
        if record["status"] == "success"
    ]
    errors = [str(record["error"]) for record in records if record["error"]]
    success_count = sum(1 for record in records if record["status"] == "success")
    failure_count = sum(1 for record in records if record["status"] == "failure")
    return {
        "name": scenario.name,
        "prompt_chars": scenario.prompt_chars,
        "request_count": scenario.request_count,
        "success_count": success_count,
        "failure_count": failure_count,
        "latency_ms_p50": _percentile(latencies, 0.50),
        "latency_ms_p95": _percentile(latencies, 0.95),
        "errors": errors,
    }


def run_suite(
    *,
    requests_per_scenario: int,
    concurrency: int,
    model: str | None,
) -> dict[str, object]:
    _load_local_env()
    scenarios = build_scenarios(
        requests_per_scenario=requests_per_scenario,
        concurrency=concurrency,
    )
    scenario_reports: list[dict[str, object]] = []
    all_records: list[dict[str, object]] = []

    for scenario in scenarios:
        records: list[dict[str, object]] = []
        with ThreadPoolExecutor(max_workers=scenario.concurrency) as executor:
            futures = [
                executor.submit(_run_request, scenario, index, model=model)
                for index in range(1, scenario.request_count + 1)
            ]
            for future in as_completed(futures):
                record = future.result()
                records.append(record)
                all_records.append(record)
        records.sort(key=lambda item: str(item["request_id"]))
        scenario_reports.append(_summarize_scenario(scenario, records))

    success_count = sum(1 for record in all_records if record["status"] == "success")
    failure_count = sum(1 for record in all_records if record["status"] == "failure")
    all_latencies = [
        float(record["latency_ms"])
        for record in all_records
        if record["status"] == "success"
    ]
    return {
        "started_at": _now_iso(),
        "model": model or os.environ.get("NEWAPI_MODEL", _DEFAULT_MODEL),
        "base_url": os.environ.get("NEWAPI_BASE_URL", _DEFAULT_BASE_URL),
        "reasoning_effort": os.environ.get("NEWAPI_REASONING_EFFORT", "none"),
        "service_tier": os.environ.get("NEWAPI_SERVICE_TIER"),
        "overall": {
            "total_requests": len(all_records),
            "successes": success_count,
            "failures": failure_count,
            "latency_ms_p50": _percentile(all_latencies, 0.50),
            "latency_ms_p95": _percentile(all_latencies, 0.95),
        },
        "scenarios": scenario_reports,
        "records": all_records,
    }


def _default_output_path(project_root: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return project_root / "diagnosis" / "backend_load" / f"{timestamp}_linkflow_gpt54.json"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_suite(
        requests_per_scenario=args.requests_per_scenario,
        concurrency=args.concurrency,
        model=args.model,
    )
    output_path = args.output or _default_output_path(PROJECT_ROOT)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote backend load report to {output_path}")
    return 0 if report["overall"]["failures"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
