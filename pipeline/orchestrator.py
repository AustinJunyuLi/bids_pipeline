from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pipeline.config import DEALS_DIR, RAW_DIR
from pipeline.models.common import PIPELINE_VERSION
from pipeline.preprocess.source import preprocess_source_deal
from pipeline.raw.stage import fetch_raw_deal
from pipeline.state import PipelineStateStore


STAGE_SEQUENCE = [
    "raw_discover",
    "raw_freeze",
    "preprocess_source",
    "extract_actors",
    "extract_events",
    "qa",
    "enrich",
    "export",
    "validate_references",
]


def stage_names_from(stage_name: str) -> list[str]:
    if stage_name not in STAGE_SEQUENCE:
        raise ValueError(f"Unknown stage: {stage_name}")
    start_idx = STAGE_SEQUENCE.index(stage_name)
    return STAGE_SEQUENCE[start_idx:]


@dataclass
class PipelineOrchestrator:
    state_store: PipelineStateStore

    @classmethod
    def from_db_path(cls, db_path: Path) -> "PipelineOrchestrator":
        return cls(state_store=PipelineStateStore(db_path))

    def start_run(
        self,
        *,
        run_id: str,
        mode: str,
        config_hash: str,
        resume: bool = False,
    ) -> dict[str, Any]:
        return self.state_store.start_run(
            run_id=run_id,
            code_version=PIPELINE_VERSION,
            config_hash=config_hash,
            mode=mode,
            resume=resume,
        )

    def summarize_run(self, run_id: str) -> dict[str, Any]:
        return self.state_store.summarize_run(run_id)

    def plan_stage_invocation(
        self,
        *,
        command_name: str,
        deal_slugs: list[str] | None = None,
        mode: str = "strict",
        from_stage: str | None = None,
    ) -> dict[str, Any]:
        stages = stage_names_from(from_stage) if from_stage else [command_name]
        return {
            "command": command_name,
            "deal_slugs": deal_slugs or [],
            "mode": mode,
            "stages": stages,
        }

    def run_preprocess_source_batch(
        self,
        *,
        run_id: str,
        deal_slugs: list[str],
        workers: int = 1,
        raw_dir: Path = RAW_DIR,
        deals_dir: Path = DEALS_DIR,
        preprocess_fn: Any = preprocess_source_deal,
        executor_cls: Any = ProcessPoolExecutor,
    ) -> dict[str, Any]:
        unique_slugs = list(dict.fromkeys(deal_slugs))
        if workers <= 1 or len(unique_slugs) <= 1:
            return {
                slug: preprocess_fn(
                    slug,
                    run_id=run_id,
                    raw_dir=raw_dir,
                    deals_dir=deals_dir,
                )
                for slug in unique_slugs
            }

        results: dict[str, Any] = {}
        with executor_cls(max_workers=workers) as executor:
            future_map = {
                executor.submit(
                    preprocess_fn,
                    slug,
                    run_id=run_id,
                    raw_dir=raw_dir,
                    deals_dir=deals_dir,
                ): slug
                for slug in unique_slugs
            }
            for future in as_completed(future_map):
                results[future_map[future]] = future.result()
        return results

    def run_raw_fetch_batch(
        self,
        *,
        run_id: str,
        seeds: list[Any],
        workers: int = 1,
        raw_dir: Path = RAW_DIR,
        fetch_fn: Any = fetch_raw_deal,
        executor_cls: Any = ThreadPoolExecutor,
    ) -> dict[str, Any]:
        seed_by_slug = {seed.deal_slug: seed for seed in seeds}
        unique_slugs = list(seed_by_slug)
        if workers <= 1 or len(unique_slugs) <= 1:
            return {
                slug: fetch_fn(
                    seed_by_slug[slug],
                    run_id=run_id,
                    raw_dir=raw_dir,
                )
                for slug in unique_slugs
            }

        results: dict[str, Any] = {}
        with executor_cls(max_workers=workers) as executor:
            future_map = {
                executor.submit(
                    fetch_fn,
                    seed_by_slug[slug],
                    run_id=run_id,
                    raw_dir=raw_dir,
                ): slug
                for slug in unique_slugs
            }
            for future in as_completed(future_map):
                results[future_map[future]] = future.result()
        return results
