from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Sequence
from uuid import uuid4

from skill_pipeline.stages.qa.check import run_check
from skill_pipeline.core.config import PROJECT_ROOT, SKILL_PIPELINE_VERSION
from skill_pipeline.stages.qa.coverage import run_coverage
from skill_pipeline.stages.enrich.core import run_enrich_core
from skill_pipeline.stages.enrich.interpret import run_enrich_interpret
from skill_pipeline.stages.export import run_export
from skill_pipeline.stages.extract import run_extract
from skill_pipeline.stages.materialize import run_materialize
from skill_pipeline.stages.qa.omission_audit import run_omission_audit
from skill_pipeline.schemas.common import PIPELINE_VERSION
from skill_pipeline.schemas.source import SeedDeal
from skill_pipeline.stages.qa.repair import run_repair
from skill_pipeline.stages.run import run_deal
from skill_pipeline.core.seeds import load_seed_entry
from skill_pipeline.stages.qa.verify import run_verify


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

    check_parser = subparsers.add_parser(
        "check",
        help="Run structural checks on materialized skill artifacts.",
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
        help="Run strict deterministic verification on materialized skill artifacts.",
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
        help="Run deterministic source-coverage audit on materialized skill artifacts.",
    )
    coverage_parser.add_argument("--deal", required=True)
    coverage_parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help=argparse.SUPPRESS,
    )

    omission_audit_parser = subparsers.add_parser(
        "omission-audit",
        help="Run LLM omission audit over uncovered chronology blocks.",
    )
    omission_audit_parser.add_argument("--deal", required=True)
    omission_audit_parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help=argparse.SUPPRESS,
    )

    repair_parser = subparsers.add_parser(
        "repair",
        help="Run the LLM repair loop over raw extraction artifacts.",
    )
    repair_parser.add_argument("--deal", required=True)
    repair_parser.add_argument(
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

    enrich_interpret_parser = subparsers.add_parser(
        "enrich-interpret",
        help="Run LLM interpretive enrichment and merge final enrichment.json.",
    )
    enrich_interpret_parser.add_argument("--deal", required=True)
    enrich_interpret_parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help=argparse.SUPPRESS,
    )

    export_parser = subparsers.add_parser(
        "export",
        help="Write the deterministic repo review CSV from materialized artifacts and enrichment.",
    )
    export_parser.add_argument("--deal", required=True)
    export_parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help=argparse.SUPPRESS,
    )

    run_parser = subparsers.add_parser(
        "run",
        help="Run the production skill pipeline through export; reconcile remains standalone.",
    )
    run_parser.add_argument("--deal", required=True)
    run_parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help=argparse.SUPPRESS,
    )

    extract_parser = subparsers.add_parser(
        "extract",
        help="Run LLM actor and event extraction from preprocessed source artifacts.",
    )
    extract_parser.add_argument("--deal", required=True)
    extract_parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help=argparse.SUPPRESS,
    )

    materialize_parser = subparsers.add_parser(
        "materialize",
        help="Resolve spans, normalize dates, deduplicate events, gate drops, and recover unnamed parties.",
    )
    materialize_parser.add_argument("--deal", required=True)
    materialize_parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
        help=argparse.SUPPRESS,
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "raw-fetch":
        from skill_pipeline.stages.raw.stage import fetch_raw_deal

        run_id = f"skill-{uuid4().hex[:8]}"
        seeds_path = args.project_root / "data" / "seeds.csv"
        entry = load_seed_entry(args.deal, seeds_path=seeds_path)
        seed = _seed_entry_to_seed_deal(entry, run_id=run_id)
        raw_dir = args.project_root / "raw"
        result = fetch_raw_deal(seed, run_id=run_id, raw_dir=raw_dir)
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "preprocess-source":
        from skill_pipeline.stages.preprocess.source import preprocess_source_deal

        run_id = f"skill-{uuid4().hex[:8]}"
        raw_dir = args.project_root / "raw"
        deals_dir = args.project_root / "data" / "deals"
        result = preprocess_source_deal(
            args.deal, run_id=run_id, raw_dir=raw_dir, deals_dir=deals_dir
        )
        print(json.dumps(result, indent=2))
        return 0
    if args.command == "check":
        return run_check(args.deal, project_root=args.project_root)
    if args.command == "verify":
        return run_verify(args.deal, project_root=args.project_root)
    if args.command == "coverage":
        return run_coverage(args.deal, project_root=args.project_root)
    if args.command == "omission-audit":
        return run_omission_audit(args.deal, project_root=args.project_root)
    if args.command == "repair":
        return run_repair(args.deal, project_root=args.project_root)
    if args.command == "run":
        return run_deal(args.deal, project_root=args.project_root)
    if args.command == "enrich-core":
        return run_enrich_core(args.deal, project_root=args.project_root)
    if args.command == "enrich-interpret":
        return run_enrich_interpret(args.deal, project_root=args.project_root)
    if args.command == "export":
        return run_export(args.deal, project_root=args.project_root)
    if args.command == "extract":
        return run_extract(args.deal, project_root=args.project_root)
    if args.command == "materialize":
        return run_materialize(args.deal, project_root=args.project_root)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
