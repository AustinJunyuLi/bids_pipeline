import argparse
from collections.abc import Sequence
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from pipeline.config import DEALS_DIR, RAW_DIR, STATE_DB_PATH
from pipeline.models.common import SCHEMA_VERSION
from pipeline.orchestrator import PipelineOrchestrator
from pipeline.seeds import entry_to_seed_artifact, load_seed_registry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pipeline",
        description="M&A deal extraction pipeline CLI.",
    )
    parser.add_argument(
        "--state-db",
        type=Path,
        default=STATE_DB_PATH,
        help="Path to the SQLite state database.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="bids-data-pipeline 0.1.0",
    )

    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Create or resume a pipeline run.")
    run_parser.add_argument("--run-id")
    run_parser.add_argument(
        "--mode",
        choices=("strict", "exploratory"),
        default="strict",
    )
    run_parser.add_argument("--resume", action="store_true")

    source_parser = subparsers.add_parser("source", help="Source stage commands.")
    source_subparsers = source_parser.add_subparsers(dest="source_command")
    for subcommand in ("discover", "locate"):
        subparser = source_subparsers.add_parser(subcommand)
        _add_stage_execution_args(subparser)

    raw_parser = subparsers.add_parser("raw", help="Networked raw archive commands.")
    raw_subparsers = raw_parser.add_subparsers(dest="raw_command")
    raw_fetch_parser = raw_subparsers.add_parser("fetch")
    _add_stage_execution_args(raw_fetch_parser, include_workers=True)

    preprocess_parser = subparsers.add_parser("preprocess", help="Local preprocess commands.")
    preprocess_subparsers = preprocess_parser.add_subparsers(dest="preprocess_command")
    preprocess_source_parser = preprocess_subparsers.add_parser("source")
    _add_stage_execution_args(preprocess_source_parser, include_workers=True)

    extract_parser = subparsers.add_parser("extract", help="Extraction stage commands.")
    extract_subparsers = extract_parser.add_subparsers(dest="extract_command")
    for subcommand in ("actors", "events"):
        subparser = extract_subparsers.add_parser(subcommand)
        _add_stage_execution_args(subparser)

    qa_parser = subparsers.add_parser("qa", help="Run QA stage.")
    _add_stage_execution_args(qa_parser)

    enrich_parser = subparsers.add_parser("enrich", help="Run enrichment stage.")
    _add_stage_execution_args(enrich_parser)

    export_parser = subparsers.add_parser("export", help="Run export stage.")
    _add_stage_execution_args(export_parser)

    validate_parser = subparsers.add_parser("validate", help="Validation commands.")
    validate_subparsers = validate_parser.add_subparsers(dest="validate_command")
    references_parser = validate_subparsers.add_parser(
        "references", help="Validate reference deals."
    )
    _add_stage_execution_args(references_parser)

    return parser


def _add_stage_execution_args(
    parser: argparse.ArgumentParser,
    *,
    include_workers: bool = False,
) -> None:
    parser.add_argument("--deal", nargs="+", default=[])
    parser.add_argument(
        "--mode",
        choices=("strict", "exploratory"),
        default="strict",
    )
    parser.add_argument("--run-id")
    parser.add_argument("--resume", action="store_true")
    if include_workers:
        parser.add_argument("--workers", type=int, default=1)


def _ensure_run(
    orchestrator: PipelineOrchestrator,
    *,
    run_id: str | None,
    mode: str,
    resume: bool,
) -> str:
    resolved_run_id = run_id or f"run-{uuid4().hex[:8]}"
    config_hash = sha256(f"{mode}:{resolved_run_id}".encode("utf-8")).hexdigest()[:12]
    orchestrator.start_run(
        run_id=resolved_run_id,
        mode=mode,
        config_hash=config_hash,
        resume=resume,
    )
    return resolved_run_id


def _load_seed_artifacts(run_id: str, deal_slugs: list[str]) -> list:
    entries = load_seed_registry()
    seeds = [entry_to_seed_artifact(entry, run_id=run_id) for entry in entries]
    if not deal_slugs:
        return seeds

    allowed = set(deal_slugs)
    selected = [seed for seed in seeds if seed.deal_slug in allowed]
    missing = sorted(allowed - {seed.deal_slug for seed in selected})
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(f"Unknown deal slug(s): {missing_text}")
    return selected


def _resolve_preprocess_deals(deal_slugs: list[str]) -> list[str]:
    if deal_slugs:
        return list(dict.fromkeys(deal_slugs))
    if not RAW_DIR.exists():
        raise ValueError("raw/ does not exist yet; run `pipeline raw fetch` first.")
    return sorted(path.name for path in RAW_DIR.iterdir() if path.is_dir())


def _record_artifact(
    orchestrator: PipelineOrchestrator,
    *,
    run_id: str,
    deal_slug: str,
    artifact_type: str,
    relative_path: str,
) -> None:
    path = RAW_DIR.parent / relative_path
    if not path.exists():
        return
    orchestrator.state_store.record_artifact(
        run_id=run_id,
        deal_slug=deal_slug,
        artifact_type=artifact_type,
        path=relative_path,
        sha256=_file_sha256(path),
        schema_version=SCHEMA_VERSION,
    )


def _file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    orchestrator = PipelineOrchestrator.from_db_path(args.state_db)
    if args.command == "run":
        _ensure_run(
            orchestrator,
            run_id=args.run_id,
            mode=args.mode,
            resume=args.resume,
        )
        return 0

    if args.command == "raw":
        run_id = _ensure_run(
            orchestrator,
            run_id=args.run_id,
            mode=args.mode,
            resume=args.resume,
        )
        seeds = _load_seed_artifacts(run_id, args.deal)
        results = orchestrator.run_raw_fetch_batch(
            run_id=run_id,
            seeds=seeds,
            workers=args.workers,
            raw_dir=RAW_DIR,
        )
        for seed in seeds:
            slug = seed.deal_slug
            summary = results[slug]
            orchestrator.state_store.record_stage_attempt(
                run_id=run_id,
                deal_slug=slug,
                stage_name="raw_discover",
                status="success",
            )
            orchestrator.state_store.record_stage_attempt(
                run_id=run_id,
                deal_slug=slug,
                stage_name="raw_freeze",
                status="success",
            )
            _record_artifact(
                orchestrator,
                run_id=run_id,
                deal_slug=slug,
                artifact_type="raw_discovery_manifest",
                relative_path=summary["discovery_path"],
            )
            _record_artifact(
                orchestrator,
                run_id=run_id,
                deal_slug=slug,
                artifact_type="raw_document_registry",
                relative_path=summary["document_registry_path"],
            )
        return 0

    if args.command == "preprocess":
        run_id = _ensure_run(
            orchestrator,
            run_id=args.run_id,
            mode=args.mode,
            resume=args.resume,
        )
        deal_slugs = _resolve_preprocess_deals(args.deal)
        results = orchestrator.run_preprocess_source_batch(
            run_id=run_id,
            deal_slugs=deal_slugs,
            workers=args.workers,
            raw_dir=RAW_DIR,
            deals_dir=DEALS_DIR,
        )
        for slug in deal_slugs:
            orchestrator.state_store.record_stage_attempt(
                run_id=run_id,
                deal_slug=slug,
                stage_name="preprocess_source",
                status="success",
            )
            for artifact_type, relative_path in (
                ("chronology_selection", f"data/deals/{slug}/source/chronology_selection.json"),
                ("chronology_blocks", f"data/deals/{slug}/source/chronology_blocks.jsonl"),
                ("supplementary_snippets", f"data/deals/{slug}/source/supplementary_snippets.jsonl"),
            ):
                _record_artifact(
                    orchestrator,
                    run_id=run_id,
                    deal_slug=slug,
                    artifact_type=artifact_type,
                    relative_path=relative_path,
                )
            _ = results[slug]
        return 0

    if args.command == "source":
        orchestrator.plan_stage_invocation(
            command_name=f"source_{args.source_command}",
            deal_slugs=args.deal,
            mode=args.mode,
        )
        return 0

    if args.command == "extract":
        orchestrator.plan_stage_invocation(
            command_name=f"extract_{args.extract_command}",
            deal_slugs=args.deal,
            mode=args.mode,
        )
        return 0

    if args.command == "qa":
        orchestrator.plan_stage_invocation(
            command_name="qa",
            deal_slugs=args.deal,
            mode=args.mode,
        )
        return 0

    if args.command == "enrich":
        orchestrator.plan_stage_invocation(
            command_name="enrich",
            deal_slugs=args.deal,
            mode=args.mode,
        )
        return 0

    if args.command == "export":
        orchestrator.plan_stage_invocation(
            command_name="export",
            deal_slugs=args.deal,
            mode=args.mode,
        )
        return 0

    if args.command == "validate":
        orchestrator.plan_stage_invocation(
            command_name="validate_references",
            deal_slugs=args.deal,
            mode=args.mode,
        )
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
