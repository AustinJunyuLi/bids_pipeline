from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from skill_pipeline.config import PROJECT_ROOT, SKILL_PIPELINE_VERSION
from skill_pipeline.deal_agent import run_deal_agent


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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "deal-agent":
        summary = run_deal_agent(args.deal, project_root=args.project_root)
        print(summary.model_dump_json(indent=2))
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
