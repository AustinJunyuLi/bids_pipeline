from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from skill_pipeline.canonicalize import run_canonicalize
from skill_pipeline.check import run_check
from skill_pipeline.config import PROJECT_ROOT, SKILL_PIPELINE_VERSION
from skill_pipeline.deal_agent import run_deal_agent
from skill_pipeline.enrich_core import run_enrich_core
from skill_pipeline.verify import run_verify


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

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "deal-agent":
        summary = run_deal_agent(args.deal, project_root=args.project_root)
        print(summary.model_dump_json(indent=2))
        return 0
    if args.command == "check":
        return run_check(args.deal, project_root=args.project_root)
    if args.command == "verify":
        return run_verify(args.deal, project_root=args.project_root)
    if args.command == "enrich-core":
        return run_enrich_core(args.deal, project_root=args.project_root)
    if args.command == "canonicalize":
        return run_canonicalize(args.deal, project_root=args.project_root)
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
