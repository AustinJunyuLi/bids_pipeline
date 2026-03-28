from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Sequence
from uuid import uuid4

from skill_pipeline.canonicalize import run_canonicalize
from skill_pipeline.compose_prompts import run_compose_prompts
from skill_pipeline.check import run_check
from skill_pipeline.config import PROJECT_ROOT, RAW_DIR, SKILL_PIPELINE_VERSION
from skill_pipeline.coverage import run_coverage
from skill_pipeline.deal_agent import run_deal_agent
from skill_pipeline.enrich_core import run_enrich_core
from skill_pipeline.gates import run_gates
from skill_pipeline.pipeline_models.common import PIPELINE_VERSION
from skill_pipeline.pipeline_models.source import SeedDeal
from skill_pipeline.seeds import load_seed_entry
from skill_pipeline.verify import run_verify


def _seed_entry_to_seed_deal(entry, *, run_id: str) -> SeedDeal:
    """Bridge a SeedEntry to a SeedDeal for use by raw/preprocess stages."""
    date_announced = None
    if entry.date_announced:
        try:
            date_announced = date.fromisoformat(entry.date_announced)
        except ValueError:
            pass
    return SeedDeal(
        run_id=run_id,
        pipeline_version=PIPELINE_VERSION,
        deal_slug=entry.deal_slug,
        target_name=entry.target_name,
        acquirer_seed=entry.acquirer,
        date_announced_seed=date_announced,
        primary_url_seed=entry.primary_url,
        is_reference=entry.is_reference,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skill-pipeline",
        description="Isolated skill-framework runtime CLI.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"skill-pipeline {SKILL_PIPELINE_VERSION}",
    )
    subparsers = parser.add_subparsers(dest="command")

    deal_agent_parser = subparsers.add_parser(
        "deal-agent",
        help="Verify shared inputs, create isolated skill directories, and summarize skill artifacts.",
    )
    deal_agent_parser.add_argument("--deal", required=True)
    deal_agent_parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help=argparse.SUPPRESS,
    )

    raw_fetch_parser = subparsers.add_parser(
        "raw-fetch",
        help="Discover and fetch raw SEC filings for a deal.",
    )
    raw_fetch_parser.add_argument("--deal", required=True)
    raw_fetch_parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help=argparse.SUPPRESS,
    )

    preprocess_source_parser = subparsers.add_parser(
        "preprocess-source",
        help="Preprocess raw filings into chronology blocks and evidence items.",
    )
    preprocess_source_parser.add_argument("--deal", required=True)
    preprocess_source_parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help=argparse.SUPPRESS,
    )

    source_discover_parser = subparsers.add_parser(
        "source-discover",
        help="Discover source filing candidates for a deal (no fetch).",
    )
    source_discover_parser.add_argument("--deal", required=True)
    source_discover_parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help=argparse.SUPPRESS,
    )

    check_parser = subparsers.add_parser(
        "check",
        help="Run structural checks on extracted skill artifacts.",
    )
    check_parser.add_argument("--deal", required=True)
    check_parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help=argparse.SUPPRESS,
    )

    verify_parser = subparsers.add_parser(
        "verify",
        help="Run strict deterministic verification on extracted skill artifacts.",
    )
    verify_parser.add_argument("--deal", required=True)
    verify_parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help=argparse.SUPPRESS,
    )

    coverage_parser = subparsers.add_parser(
        "coverage",
        help="Run deterministic source-coverage audit on extracted skill artifacts.",
    )
    coverage_parser.add_argument("--deal", required=True)
    coverage_parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help=argparse.SUPPRESS,
    )

    enrich_core_parser = subparsers.add_parser(
        "enrich-core",
        help="Run deterministic enrich-core: rounds, bid classification, cycles, formal boundary.",
    )
    enrich_core_parser.add_argument("--deal", required=True)
    enrich_core_parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help=argparse.SUPPRESS,
    )

    canonicalize_parser = subparsers.add_parser(
        "canonicalize",
        help="Deduplicate events, gate drops by NDA, recover unnamed parties.",
    )
    canonicalize_parser.add_argument("--deal", required=True)
    canonicalize_parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help=argparse.SUPPRESS,
    )

    compose_prompts_parser = subparsers.add_parser(
        "compose-prompts",
        help="Compose deterministic prompt packets from source artifacts.",
    )
    compose_prompts_parser.add_argument("--deal", required=True)
    compose_prompts_parser.add_argument(
        "--mode",
        choices=["actors", "events", "all"],
        default="all",
        help="Which packet families to compose (default: all).",
    )
    compose_prompts_parser.add_argument(
        "--chunk-budget",
        type=int,
        default=6000,
        help="Target token budget per chunk window (default: 6000).",
    )
    compose_prompts_parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help=argparse.SUPPRESS,
    )

    gates_parser = subparsers.add_parser(
        "gates",
        help="Run semantic gates on extracted skill artifacts.",
    )
    gates_parser.add_argument("--deal", required=True)
    gates_parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help=argparse.SUPPRESS,
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "deal-agent":
        summary = run_deal_agent(args.deal, project_root=args.project_root)
        print(summary.model_dump_json(indent=2))
        return 0
    if args.command == "raw-fetch":
        from skill_pipeline.raw.stage import fetch_raw_deal

        run_id = f"skill-{uuid4().hex[:8]}"
        seeds_path = args.project_root / "data" / "seeds.csv"
        entry = load_seed_entry(args.deal, seeds_path=seeds_path)
        seed = _seed_entry_to_seed_deal(entry, run_id=run_id)
        raw_dir = args.project_root / "raw"
        result = fetch_raw_deal(seed, run_id=run_id, raw_dir=raw_dir)
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "preprocess-source":
        from skill_pipeline.preprocess.source import preprocess_source_deal

        run_id = f"skill-{uuid4().hex[:8]}"
        raw_dir = args.project_root / "raw"
        deals_dir = args.project_root / "data" / "deals"
        result = preprocess_source_deal(
            args.deal, run_id=run_id, raw_dir=raw_dir, deals_dir=deals_dir
        )
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "source-discover":
        from skill_pipeline.raw.discover import build_raw_discovery_manifest
        from skill_pipeline.source.ranking import extract_cik_from_url

        run_id = f"skill-{uuid4().hex[:8]}"
        seeds_path = args.project_root / "data" / "seeds.csv"
        entry = load_seed_entry(args.deal, seeds_path=seeds_path)
        seed = _seed_entry_to_seed_deal(entry, run_id=run_id)
        discovery = build_raw_discovery_manifest(
            seed,
            run_id=run_id,
            cik=extract_cik_from_url(seed.primary_url_seed),
        )
        print(discovery.model_dump_json(indent=2))
        return 0
    if args.command == "check":
        return run_check(args.deal, project_root=args.project_root)
    if args.command == "verify":
        return run_verify(args.deal, project_root=args.project_root)
    if args.command == "coverage":
        return run_coverage(args.deal, project_root=args.project_root)
    if args.command == "gates":
        return run_gates(args.deal, project_root=args.project_root)
    if args.command == "enrich-core":
        return run_enrich_core(args.deal, project_root=args.project_root)
    if args.command == "canonicalize":
        return run_canonicalize(args.deal, project_root=args.project_root)
    if args.command == "compose-prompts":
        manifest = run_compose_prompts(
            args.deal,
            project_root=args.project_root,
            mode=args.mode,
            chunk_budget=args.chunk_budget,
        )
        print(manifest.model_dump_json(indent=2))
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
