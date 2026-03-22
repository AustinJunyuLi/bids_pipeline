# Extraction Pipeline

---

## pipeline/cli.py
```python
from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from pipeline.config import (
    DEALS_DIR,
    RAW_DIR,
    STATE_DB_PATH,
    VALID_LLM_PROVIDERS,
    VALID_STRUCTURED_OUTPUT_MODES,
)
from pipeline.llm import build_backend
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
        _add_llm_args(subparser)

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


def _add_llm_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--provider",
        choices=VALID_LLM_PROVIDERS,
        default=None,
        help="LLM provider override (anthropic/openai).",
    )
    parser.add_argument("--model", dest="model_override", default=None, help="Override the LLM model id.")
    parser.add_argument(
        "--reasoning-effort",
        dest="reasoning_effort",
        default=None,
        help="Provider-specific reasoning/effort override (for example: minimal, low, medium, high, max).",
    )
    parser.add_argument(
        "--effort",
        dest="reasoning_effort",
        default=None,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--structured-mode",
        choices=VALID_STRUCTURED_OUTPUT_MODES,
        default=None,
        help="Structured output mode override (prompted_json/provider_native/auto).",
    )


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


def _resolve_stage_deals(deal_slugs: list[str], *, required_relative_path: str) -> list[str]:
    if deal_slugs:
        return list(dict.fromkeys(deal_slugs))
    resolved: list[str] = []
    for path in DEALS_DIR.iterdir():
        if not path.is_dir():
            continue
        if (path / required_relative_path).exists():
            resolved.append(path.name)
    return sorted(resolved)


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


def _record_usage_calls(
    orchestrator: PipelineOrchestrator,
    *,
    run_id: str,
    deal_slug: str,
    usage_path: Path,
    unit_name: str,
) -> None:
    if not usage_path.exists():
        return
    payload = json.loads(usage_path.read_text(encoding="utf-8"))
    call_rows = payload.get("calls") or [payload]
    for index, row in enumerate(call_rows, start=1):
        request_id = row.get("request_id") or f"{deal_slug}-{unit_name}-{index}"
        orchestrator.state_store.record_llm_call(
            call_id=f"{run_id}:{deal_slug}:{unit_name}:{index}:{request_id}",
            run_id=run_id,
            deal_slug=deal_slug,
            unit_name=unit_name,
            provider=row.get("provider") or "unknown",
            model=row.get("model") or "",
            prompt_version=row.get("prompt_version") or "",
            request_id=request_id,
            input_tokens=row.get("input_tokens"),
            cache_creation_input_tokens=row.get("cache_creation_input_tokens"),
            cache_read_input_tokens=row.get("cache_read_input_tokens"),
            output_tokens=row.get("output_tokens"),
            cost_usd=row.get("cost_usd"),
            latency_ms=row.get("latency_ms"),
            status="success",
        )
    recovery = payload.get("recovery")
    if recovery is not None:
        recovery_unit = f"{unit_name}_recovery_audit"
        request_id = recovery.get("request_id") or f"{deal_slug}-{recovery_unit}-1"
        orchestrator.state_store.record_llm_call(
            call_id=f"{run_id}:{deal_slug}:{recovery_unit}:1:{request_id}",
            run_id=run_id,
            deal_slug=deal_slug,
            unit_name=recovery_unit,
            provider=recovery.get("provider") or "unknown",
            model=recovery.get("model") or "",
            prompt_version=recovery.get("prompt_version") or "",
            request_id=request_id,
            input_tokens=recovery.get("input_tokens"),
            cache_creation_input_tokens=recovery.get("cache_creation_input_tokens"),
            cache_read_input_tokens=recovery.get("cache_read_input_tokens"),
            output_tokens=recovery.get("output_tokens"),
            cost_usd=recovery.get("cost_usd"),
            latency_ms=recovery.get("latency_ms"),
            status="success",
        )


def _build_backend(
    *,
    provider: str | None = None,
    model: str | None = None,
    reasoning_effort: str | None = None,
    structured_mode: str | None = None,
):
    return build_backend(
        provider=provider,
        model=model,
        reasoning_effort=reasoning_effort,
        structured_mode=structured_mode,
    )


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
        orchestrator.run_preprocess_source_batch(
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
                ("evidence_items", f"data/deals/{slug}/source/evidence_items.jsonl"),
                ("supplementary_snippets", f"data/deals/{slug}/source/supplementary_snippets.jsonl"),
            ):
                _record_artifact(
                    orchestrator,
                    run_id=run_id,
                    deal_slug=slug,
                    artifact_type=artifact_type,
                    relative_path=relative_path,
                )
        return 0

    if args.command == "source":
        # The raw/preprocess subcommands perform the actual work; keep source/* as plan aliases.
        orchestrator.plan_stage_invocation(
            command_name=f"source_{args.source_command}",
            deal_slugs=args.deal,
            mode=args.mode,
        )
        return 0

    if args.command == "extract":
        run_id = _ensure_run(
            orchestrator,
            run_id=args.run_id,
            mode=args.mode,
            resume=args.resume,
        )
        deal_slugs = _resolve_stage_deals(args.deal, required_relative_path="source/chronology_selection.json")
        backend = _build_backend(
            provider=args.provider,
            model=args.model_override,
            reasoning_effort=args.reasoning_effort,
            structured_mode=args.structured_mode,
        )
        if args.extract_command == "actors":
            orchestrator.run_actor_extraction_batch(run_id=run_id, deal_slugs=deal_slugs, backend=backend)
            for slug in deal_slugs:
                orchestrator.state_store.record_stage_attempt(run_id=run_id, deal_slug=slug, stage_name="extract_actors", status="success")
                for artifact_type, relative_path in (
                    ("actors_raw", f"data/deals/{slug}/extract/actors_raw.json"),
                    ("actor_usage", f"data/deals/{slug}/extract/actor_usage.json"),
                ):
                    _record_artifact(orchestrator, run_id=run_id, deal_slug=slug, artifact_type=artifact_type, relative_path=relative_path)
                _record_usage_calls(
                    orchestrator,
                    run_id=run_id,
                    deal_slug=slug,
                    usage_path=DEALS_DIR / slug / "extract" / "actor_usage.json",
                    unit_name="actor_extraction",
                )
            return 0
        if args.extract_command == "events":
            orchestrator.run_event_extraction_batch(run_id=run_id, deal_slugs=deal_slugs, backend=backend)
            for slug in deal_slugs:
                orchestrator.state_store.record_stage_attempt(run_id=run_id, deal_slug=slug, stage_name="extract_events", status="success")
                for artifact_type, relative_path in (
                    ("events_raw", f"data/deals/{slug}/extract/events_raw.json"),
                    ("event_chunks", f"data/deals/{slug}/extract/event_chunks.jsonl"),
                    ("event_usage", f"data/deals/{slug}/extract/event_usage.json"),
                    ("recovery_raw", f"data/deals/{slug}/extract/recovery_raw.json"),
                    ("recovery_usage", f"data/deals/{slug}/extract/recovery_usage.json"),
                ):
                    _record_artifact(orchestrator, run_id=run_id, deal_slug=slug, artifact_type=artifact_type, relative_path=relative_path)
                _record_usage_calls(
                    orchestrator,
                    run_id=run_id,
                    deal_slug=slug,
                    usage_path=DEALS_DIR / slug / "extract" / "event_usage.json",
                    unit_name="event_extraction",
                )
            return 0

    if args.command == "qa":
        run_id = _ensure_run(orchestrator, run_id=args.run_id, mode=args.mode, resume=args.resume)
        deal_slugs = _resolve_stage_deals(args.deal, required_relative_path="extract/events_raw.json")
        orchestrator.run_qa_batch(run_id=run_id, deal_slugs=deal_slugs)
        for slug in deal_slugs:
            orchestrator.state_store.record_stage_attempt(run_id=run_id, deal_slug=slug, stage_name="qa", status="success")
            for artifact_type, relative_path in (
                ("canonical_extraction", f"data/deals/{slug}/qa/extraction_canonical.json"),
                ("qa_report", f"data/deals/{slug}/qa/report.json"),
                ("span_registry", f"data/deals/{slug}/qa/span_registry.jsonl"),
            ):
                _record_artifact(orchestrator, run_id=run_id, deal_slug=slug, artifact_type=artifact_type, relative_path=relative_path)
        return 0

    if args.command == "enrich":
        run_id = _ensure_run(orchestrator, run_id=args.run_id, mode=args.mode, resume=args.resume)
        deal_slugs = _resolve_stage_deals(args.deal, required_relative_path="qa/extraction_canonical.json")
        orchestrator.run_enrichment_batch(run_id=run_id, deal_slugs=deal_slugs)
        for slug in deal_slugs:
            orchestrator.state_store.record_stage_attempt(run_id=run_id, deal_slug=slug, stage_name="enrich", status="success")
            _record_artifact(orchestrator, run_id=run_id, deal_slug=slug, artifact_type="deal_enrichment", relative_path=f"data/deals/{slug}/enrich/deal_enrichment.json")
        return 0

    if args.command == "export":
        run_id = _ensure_run(orchestrator, run_id=args.run_id, mode=args.mode, resume=args.resume)
        deal_slugs = _resolve_stage_deals(args.deal, required_relative_path="enrich/deal_enrichment.json")
        orchestrator.run_export_batch(run_id=run_id, deal_slugs=deal_slugs)
        for slug in deal_slugs:
            orchestrator.state_store.record_stage_attempt(run_id=run_id, deal_slug=slug, stage_name="export", status="success")
            for artifact_type, relative_path in (
                ("events_long_csv", f"data/deals/{slug}/export/events_long.csv"),
                ("alex_compat_csv", f"data/deals/{slug}/export/alex_compat.csv"),
                ("canonical_export", f"data/deals/{slug}/export/canonical_export.json"),
                ("reference_metrics", f"data/deals/{slug}/export/reference_metrics.json"),
            ):
                _record_artifact(orchestrator, run_id=run_id, deal_slug=slug, artifact_type=artifact_type, relative_path=relative_path)
        return 0

    if args.command == "validate":
        run_id = _ensure_run(orchestrator, run_id=args.run_id, mode=args.mode, resume=args.resume)
        deal_slugs = _resolve_stage_deals(args.deal, required_relative_path="export/reference_metrics.json")
        orchestrator.run_reference_validation(run_id=run_id, deal_slugs=deal_slugs)
        orchestrator.state_store.record_stage_attempt(run_id=run_id, deal_slug="__reference_summary__", stage_name="validate_references", status="success")
        _record_artifact(orchestrator, run_id=run_id, deal_slug="__reference_summary__", artifact_type="reference_summary", relative_path="data/validate/reference_summary.json")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

---

## pipeline/seeds.py
```python
import csv
import re
from collections.abc import Iterable, Mapping
from datetime import date, datetime
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from pipeline.config import PROJECT_ROOT, SEEDS_PATH
from pipeline.models.common import PIPELINE_VERSION
from pipeline.models.seed import SeedEvidence, SeedRegistryEntry
from pipeline.models.source import SeedDeal


RAW_SEEDS_XLSX = PROJECT_ROOT / "raw" / "deal_details_Alex_2026.xlsx"
REQUIRED_SEED_COLUMNS = (
    "deal_slug",
    "target_name",
    "acquirer",
    "date_announced",
    "primary_url",
    "is_reference",
)
SEED_COLUMNS = REQUIRED_SEED_COLUMNS

CANONICAL_SLUG_OVERRIDES = {
    "imprivata-inc": "imprivata",
    "medivation-inc": "medivation",
    "zep-inc": "zep",
    "penford-corp": "penford",
    "mac-gray-corp": "mac-gray",
    "saks-inc": "saks",
    "providence-worcester-rr-co": "providence-worcester",
    "stec-inc": "stec",
    "s-tec-inc": "stec",
    "s-t-e-c-inc": "stec",
}
REFERENCE_SLUGS = {
    "imprivata",
    "medivation",
    "zep",
    "petsmart-inc",
    "penford",
    "mac-gray",
    "saks",
    "providence-worcester",
    "stec",
}
XLSX_COLUMN_MAP = {
    "TargetName": "target_name",
    "Acquirer": "acquirer",
    "DateAnnounced": "date_announced",
    "URL": "primary_url",
}


def make_slug(name: str) -> str:
    """Lowercase, strip punctuation, collapse to hyphens."""

    slug = re.sub(r"[^a-z0-9]+", "-", name.lower())
    slug = re.sub(r"-{2,}", "-", slug)
    return slug.strip("-")


def canonical_deal_slug(target_name: str) -> str:
    """Apply stable overrides for known reference/example deals."""

    base_slug = make_slug(target_name)
    return CANONICAL_SLUG_OVERRIDES.get(base_slug, base_slug)


def validate_seed_headers(headers: Iterable[str]) -> None:
    header_set = {header for header in headers if header}
    missing = [column for column in REQUIRED_SEED_COLUMNS if column not in header_set]
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"Seed input is missing required columns: {missing_text}")


def load_seed_registry(path: Path = SEEDS_PATH) -> list[SeedRegistryEntry]:
    rows = _load_rows(path)
    return build_seed_registry(rows)


def build_seed_registry(rows: Iterable[Mapping[str, Any]]) -> list[SeedRegistryEntry]:
    entries_by_slug: dict[str, SeedRegistryEntry] = {}
    ordered_slugs: list[str] = []

    for row in rows:
        target_name = _clean_optional_text(row.get("target_name"))
        if not target_name:
            continue

        deal_slug = canonical_deal_slug(target_name)
        entry = entries_by_slug.get(deal_slug)
        is_reference = _parse_bool(row.get("is_reference")) or deal_slug in REFERENCE_SLUGS
        acquirer = _clean_optional_text(row.get("acquirer"))
        date_announced = _parse_seed_date(row.get("date_announced"))
        primary_url = _clean_optional_text(row.get("primary_url"))

        if entry is None:
            entry = SeedRegistryEntry(
                deal_slug=deal_slug,
                target_name=target_name,
                acquirer=acquirer,
                date_announced=date_announced,
                primary_url=primary_url,
                is_reference=is_reference,
            )
            entries_by_slug[deal_slug] = entry
            ordered_slugs.append(deal_slug)
        else:
            entry.is_reference = entry.is_reference or is_reference
            if entry.acquirer is None and acquirer is not None:
                entry.acquirer = acquirer
            if entry.date_announced is None and date_announced is not None:
                entry.date_announced = date_announced
            if entry.primary_url is None and primary_url is not None:
                entry.primary_url = primary_url

        entry.evidence.append(
            SeedEvidence(
                row_ref=_clean_optional_text(row.get("_row_ref")),
                provided_deal_slug=_clean_optional_text(row.get("deal_slug")),
                target_name_raw=target_name,
                acquirer_raw=acquirer,
                date_announced_raw=_clean_optional_text(row.get("date_announced")),
                primary_url_raw=primary_url,
                is_reference_raw=_parse_bool(row.get("is_reference")),
            )
        )
        _record_conflict(entry, "target_name", target_name)
        _record_conflict(entry, "acquirer", acquirer)
        _record_conflict(entry, "date_announced", _clean_optional_text(row.get("date_announced")))
        _record_conflict(entry, "primary_url", primary_url)

    return [entries_by_slug[slug] for slug in ordered_slugs]


def entry_to_seed_artifact(
    entry: SeedRegistryEntry,
    *,
    run_id: str,
    pipeline_version: str = PIPELINE_VERSION,
) -> SeedDeal:
    row_refs = [evidence.row_ref for evidence in entry.evidence if evidence.row_ref]
    notes = [
        f"conflict:{field}=" + " | ".join(values)
        for field, values in sorted(entry.conflicting_evidence.items())
    ]
    return SeedDeal(
        run_id=run_id,
        pipeline_version=pipeline_version,
        deal_slug=entry.deal_slug,
        target_name=entry.target_name,
        acquirer_seed=entry.acquirer,
        date_announced_seed=entry.date_announced,
        primary_url_seed=entry.primary_url,
        is_reference=entry.is_reference,
        seed_row_refs=row_refs,
        notes=notes,
    )


def extract_seeds(xlsx_path: Path) -> list[dict[str, str]]:
    """Read deal_details xlsx and return normalized seed rows."""

    return [_entry_to_output_row(entry) for entry in load_seed_registry(xlsx_path)]


def write_seeds(
    seeds: Iterable[SeedRegistryEntry | SeedDeal | Mapping[str, Any]],
    output_path: Path,
) -> None:
    """Write seeds to CSV."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SEED_COLUMNS)
        writer.writeheader()
        for seed in seeds:
            writer.writerow(_coerce_output_row(seed))


def main() -> None:
    """Entry point: rebuild seeds.csv from workbook when available, else normalize the CSV."""

    input_path = RAW_SEEDS_XLSX if RAW_SEEDS_XLSX.exists() else SEEDS_PATH
    entries = load_seed_registry(input_path)
    write_seeds(entries, SEEDS_PATH)
    print(f"Wrote {len(entries)} seeds to {SEEDS_PATH}")


def _coerce_output_row(seed: SeedRegistryEntry | SeedDeal | Mapping[str, Any]) -> dict[str, str]:
    if isinstance(seed, SeedRegistryEntry):
        return _entry_to_output_row(seed)
    if isinstance(seed, SeedDeal):
        return {
            "deal_slug": seed.deal_slug,
            "target_name": seed.target_name,
            "acquirer": seed.acquirer_seed or "",
            "date_announced": seed.date_announced_seed.isoformat()
            if seed.date_announced_seed
            else "",
            "primary_url": seed.primary_url_seed or "",
            "is_reference": "true" if seed.is_reference else "false",
        }

    return {
        "deal_slug": _clean_optional_text(seed.get("deal_slug")) or "",
        "target_name": _clean_optional_text(seed.get("target_name")) or "",
        "acquirer": _clean_optional_text(seed.get("acquirer")) or "",
        "date_announced": _clean_optional_text(seed.get("date_announced")) or "",
        "primary_url": _clean_optional_text(seed.get("primary_url")) or "",
        "is_reference": "true" if _parse_bool(seed.get("is_reference")) else "false",
    }


def _entry_to_output_row(entry: SeedRegistryEntry) -> dict[str, str]:
    return {
        "deal_slug": entry.deal_slug,
        "target_name": entry.target_name,
        "acquirer": entry.acquirer or "",
        "date_announced": entry.date_announced.isoformat() if entry.date_announced else "",
        "primary_url": entry.primary_url or "",
        "is_reference": "true" if entry.is_reference else "false",
    }


def _load_rows(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _read_csv_rows(path)
    if suffix in {".xlsx", ".xlsm"}:
        return _read_xlsx_rows(path)
    raise ValueError(f"Unsupported seed input format: {path.suffix}")


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        validate_seed_headers(fieldnames)
        rows: list[dict[str, Any]] = []
        for line_no, row in enumerate(reader, start=2):
            enriched = {key: value for key, value in row.items()}
            enriched["_row_ref"] = f"csv:{line_no}"
            rows.append(enriched)
        return rows


def _read_xlsx_rows(path: Path) -> list[dict[str, Any]]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    worksheet = workbook[workbook.sheetnames[0]]
    raw_rows = worksheet.iter_rows(values_only=True)
    header = [str(value).strip() if value else "" for value in next(raw_rows)]
    indices = {name: idx for idx, name in enumerate(header) if name}
    missing = [name for name in XLSX_COLUMN_MAP if name not in indices]
    if missing:
        raise ValueError(
            "Seed workbook is missing required columns: " + ", ".join(sorted(missing))
        )

    rows: list[dict[str, Any]] = []
    for row_no, values in enumerate(raw_rows, start=2):
        target_name = _clean_optional_text(values[indices["TargetName"]])
        if not target_name:
            continue
        rows.append(
            {
                "deal_slug": canonical_deal_slug(target_name),
                "target_name": target_name,
                "acquirer": _clean_optional_text(values[indices["Acquirer"]]),
                "date_announced": _format_date(values[indices["DateAnnounced"]]),
                "primary_url": _clean_optional_text(values[indices["URL"]]),
                "is_reference": canonical_deal_slug(target_name) in REFERENCE_SLUGS,
                "_row_ref": f"xlsx:{row_no}",
            }
        )
    return rows


def _record_conflict(entry: SeedRegistryEntry, field_name: str, candidate: str | None) -> None:
    if not candidate:
        return

    existing_values = set(entry.conflicting_evidence.get(field_name, []))
    canonical_value = _canonical_field_text(entry, field_name)
    if canonical_value:
        existing_values.add(canonical_value)
    existing_values.add(candidate)

    if len(existing_values) > 1:
        entry.conflicting_evidence[field_name] = sorted(existing_values)


def _canonical_field_text(entry: SeedRegistryEntry, field_name: str) -> str | None:
    value = getattr(entry, field_name)
    if isinstance(value, date):
        return value.isoformat()
    return value


def _clean_optional_text(value: object) -> str | None:
    cleaned = _clean_text(value)
    return cleaned or None


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = _clean_text(value).lower()
    return text in {"1", "true", "t", "yes", "y"}


def _parse_seed_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = _clean_text(value)
    if not text:
        return None

    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _format_date(value: object) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return _clean_text(value)


if __name__ == "__main__":
    main()
```

---

## pipeline/extract/__init__.py
```python
from pipeline.extract.actors import run_actor_extraction
from pipeline.extract.events import run_event_extraction
from pipeline.extract.merge import merge_event_outputs
from pipeline.extract.recovery import build_recovery_block_subset, needs_recovery_audit, recover_missing_events, run_recovery_audit

__all__ = [
    "build_recovery_block_subset",
    "merge_event_outputs",
    "needs_recovery_audit",
    "recover_missing_events",
    "run_actor_extraction",
    "run_event_extraction",
    "run_recovery_audit",
]
```

---

## pipeline/extract/utils.py
```python
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from pipeline.config import DEALS_DIR
from pipeline.models.source import ChronologyBlock, ChronologySelection, EvidenceItem, SeedDeal
from pipeline.seeds import entry_to_seed_artifact, load_seed_registry


def _assert_evidence_ids_unique(evidence_items: list[EvidenceItem]) -> None:
    seen: set[str] = set()
    for item in evidence_items:
        if item.evidence_id in seen:
            raise ValueError(
                f"Duplicate evidence_id {item.evidence_id!r} across filings. "
                "Re-run preprocessing to generate globally unique IDs."
            )
        seen.add(item.evidence_id)


def load_source_inputs(
    deal_slug: str,
    *,
    run_id: str,
    deals_dir: Path = DEALS_DIR,
) -> tuple[SeedDeal, ChronologySelection, list[ChronologyBlock], list[EvidenceItem]]:
    seed = load_seed_artifact(deal_slug, run_id=run_id)
    source_dir = deals_dir / deal_slug / "source"
    selection = ChronologySelection.model_validate_json(
        (source_dir / "chronology_selection.json").read_text(encoding="utf-8")
    )
    blocks = load_jsonl(source_dir / "chronology_blocks.jsonl", ChronologyBlock)
    evidence_path = source_dir / "evidence_items.jsonl"
    evidence_items = load_jsonl(evidence_path, EvidenceItem) if evidence_path.exists() else []
    if evidence_items:
        _assert_evidence_ids_unique(evidence_items)
    return seed, selection, blocks, evidence_items


def load_seed_artifact(deal_slug: str, *, run_id: str) -> SeedDeal:
    for entry in load_seed_registry():
        if entry.deal_slug == deal_slug:
            return entry_to_seed_artifact(entry, run_id=run_id)
    raise ValueError(f"Unknown deal slug: {deal_slug}")


def load_jsonl(path: Path, model_cls):
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return []
    return [model_cls.model_validate_json(line) for line in text.splitlines()]


def atomic_write_json(path: Path, payload: Any) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2, default=str))


def atomic_write_jsonl(path: Path, payloads: list[dict[str, Any]]) -> None:
    atomic_write_text(path, "\n".join(json.dumps(payload, default=str) for payload in payloads))


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def summarize_usage(result) -> dict[str, Any]:
    usage = getattr(result, "usage", None)
    if usage is None:
        return {}
    return {
        "provider": getattr(usage, "provider", None),
        "input_tokens": usage.input_tokens,
        "cache_creation_input_tokens": usage.cache_creation_input_tokens,
        "cache_read_input_tokens": usage.cache_read_input_tokens,
        "output_tokens": usage.output_tokens,
        "cost_usd": usage.cost_usd,
        "latency_ms": usage.latency_ms,
        "request_id": usage.request_id,
        "model": usage.model,
        "prompt_version": result.prompt_version,
        "structured_mode": getattr(result, "structured_mode", None),
        "repair_count": getattr(result, "repair_count", 0),
    }


def select_prompt_evidence_items(
    evidence_items: list[EvidenceItem],
    *,
    max_total: int = 40,
    max_per_type: int = 10,
) -> list[EvidenceItem]:
    priority = {"high": 0, "medium": 1, "low": 2}
    per_type_counts: dict[str, int] = {}
    selected: list[EvidenceItem] = []
    for item in sorted(
        evidence_items,
        key=lambda value: (
            priority[value.confidence],
            value.evidence_type.value,
            value.start_line,
            value.evidence_id,
        ),
    ):
        type_key = item.evidence_type.value
        if per_type_counts.get(type_key, 0) >= max_per_type:
            continue
        selected.append(item)
        per_type_counts[type_key] = per_type_counts.get(type_key, 0) + 1
        if len(selected) >= max_total:
            break
    return selected
```

---

## pipeline/extract/actors.py
```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from pipeline.config import DEALS_DIR
from pipeline.llm.prompts import PromptPack
from pipeline.llm.schemas import ActorExtractionOutput
from pipeline.llm.token_budget import classify_complexity, estimate_max_output_tokens
from pipeline.extract.utils import (
    atomic_write_json,
    load_source_inputs,
    select_prompt_evidence_items,
    summarize_usage,
)


ACTOR_OUTPUT_FILENAME = "actors_raw.json"
ACTOR_USAGE_FILENAME = "actor_usage.json"


def run_actor_extraction(
    deal_slug: str,
    *,
    run_id: str,
    backend,
    deals_dir: Path = DEALS_DIR,
    model: str | None = None,
) -> dict[str, Any]:
    seed, selection, blocks, evidence_items = load_source_inputs(deal_slug, run_id=run_id, deals_dir=deals_dir)
    extract_dir = deals_dir / deal_slug / "extract"
    extract_dir.mkdir(parents=True, exist_ok=True)

    prompt_evidence = select_prompt_evidence_items(evidence_items)
    deal_context = {
        "deal_slug": deal_slug,
        "target_name": seed.target_name,
        "acquirer_seed": seed.acquirer_seed,
        "date_announced_seed": seed.date_announced_seed,
        "accession_number": selection.accession_number,
        "filing_type": selection.filing_type,
    }
    messages = [
        {
            "role": "user",
            "content": PromptPack.render_actor_user_message(
                deal_context,
                blocks,
                evidence_items=prompt_evidence,
            ),
        }
    ]
    token_count = backend.count_tokens(
        messages=messages,
        system=PromptPack.ACTOR_SYSTEM_PROMPT,
        model=model,
    )
    line_count = sum((block.end_line - block.start_line + 1) for block in blocks)
    complexity = classify_complexity(token_count, line_count, actor_count=0)
    max_tokens = estimate_max_output_tokens(complexity, "actor")
    effective_model = (model or getattr(backend, "model", "") or "").strip().lower()
    provider = (getattr(backend, "provider", "") or "").strip().lower()
    if provider == "openai" and effective_model.startswith("gpt-5"):
        gpt5_actor_floors = {
            "simple": 3_000,
            "moderate": 4_500,
            "complex": 6_500,
        }
        max_tokens = max(max_tokens, gpt5_actor_floors[complexity.value])
    result = backend.invoke_structured(
        messages=messages,
        system=PromptPack.ACTOR_SYSTEM_PROMPT,
        output_schema=ActorExtractionOutput,
        max_tokens=max_tokens,
        model=model,
    )
    if not result.output.actors and not result.output.count_assertions and not result.output.unresolved_mentions:
        raise ValueError(
            "Actor extraction returned an empty structured payload; "
            "this usually indicates a truncated or under-budget LLM response."
        )

    atomic_write_json(extract_dir / ACTOR_OUTPUT_FILENAME, result.output.model_dump(mode="json"))
    atomic_write_json(
        extract_dir / ACTOR_USAGE_FILENAME,
        {
            **summarize_usage(result),
            "deal_slug": deal_slug,
            "run_id": run_id,
            "token_count": token_count,
            "line_count": line_count,
            "complexity": complexity.value,
            "evidence_item_count": len(prompt_evidence),
            "block_count": len(blocks),
        },
    )
    return {
        "deal_slug": deal_slug,
        "actor_count": len(result.output.actors),
        "count_assertion_count": len(result.output.count_assertions),
        "unresolved_mention_count": len(result.output.unresolved_mentions),
        "complexity": complexity.value,
        **summarize_usage(result),
    }
```

---

## pipeline/extract/events.py
```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from pipeline.config import DEALS_DIR
from pipeline.llm.prompts import PromptPack
from pipeline.llm.schemas import ActorExtractionOutput, EventExtractionOutput
from pipeline.llm.token_budget import classify_complexity, estimate_max_output_tokens, plan_event_chunks
from pipeline.extract.merge import merge_event_outputs
from pipeline.extract.recovery import (
    build_recovery_block_subset,
    needs_recovery_audit,
    recover_missing_events,
    run_recovery_audit,
)
from pipeline.extract.utils import (
    atomic_write_json,
    atomic_write_jsonl,
    load_source_inputs,
    select_prompt_evidence_items,
    summarize_usage,
)
from pipeline.models.common import EventType


EVENT_OUTPUT_FILENAME = "events_raw.json"
EVENT_CHUNKS_FILENAME = "event_chunks.jsonl"
EVENT_USAGE_FILENAME = "event_usage.json"


def run_event_extraction(
    deal_slug: str,
    *,
    run_id: str,
    backend,
    deals_dir: Path = DEALS_DIR,
    model: str | None = None,
) -> dict[str, Any]:
    seed, selection, blocks, evidence_items = load_source_inputs(deal_slug, run_id=run_id, deals_dir=deals_dir)
    extract_dir = deals_dir / deal_slug / "extract"
    extract_dir.mkdir(parents=True, exist_ok=True)

    actor_output = ActorExtractionOutput.model_validate_json(
        (extract_dir / "actors_raw.json").read_text(encoding="utf-8")
    )
    actor_roster = actor_output.actors
    prompt_evidence = select_prompt_evidence_items(evidence_items)
    rendered_prompt = PromptPack.render_event_user_message(
        {
            "deal_slug": deal_slug,
            "target_name": seed.target_name,
            "accession_number": selection.accession_number,
            "filing_type": selection.filing_type,
        },
        actor_roster,
        blocks,
        chunk_mode="single_pass",
        chunk_id="all",
        prior_round_context=[],
        evidence_items=prompt_evidence,
    )
    token_count = backend.count_tokens(
        messages=[{"role": "user", "content": rendered_prompt}],
        system=PromptPack.EVENT_SYSTEM_PROMPT,
        model=model,
    )
    line_count = sum((block.end_line - block.start_line + 1) for block in blocks)
    complexity = classify_complexity(token_count, line_count, len(actor_roster))

    chunk_groups = [blocks]
    chunk_mode = "single_pass"
    if complexity != "simple":
        chunk_groups = plan_event_chunks(blocks)
        chunk_mode = "chunked"

    chunk_outputs: list[EventExtractionOutput] = []
    chunk_usage_records: list[dict[str, Any]] = []
    prior_round_context: list[str] = []

    for index, chunk in enumerate(chunk_groups, start=1):
        result = _invoke_event_call(
            backend,
            seed_context={
                "deal_slug": deal_slug,
                "target_name": seed.target_name,
                "accession_number": selection.accession_number,
                "filing_type": selection.filing_type,
            },
            actor_roster=actor_roster,
            blocks=chunk,
            chunk_mode=chunk_mode,
            chunk_id=f"chunk-{index}" if chunk_mode == "chunked" else "all",
            prior_round_context=prior_round_context,
            evidence_items=prompt_evidence,
            model=model,
            complexity=complexity,
        )
        chunk_outputs.append(result.output)
        chunk_usage_records.append({
            "chunk_id": f"chunk-{index}" if chunk_mode == "chunked" else "all",
            **summarize_usage(result),
        })
        prior_round_context.extend(_round_context_lines(result.output))

    merged_output = merge_event_outputs(chunk_outputs)

    recovery_usage: dict[str, Any] | None = None
    if needs_recovery_audit(merged_output, evidence_items=evidence_items):
        recovery_result = run_recovery_audit(
            blocks,
            deal_slug=deal_slug,
            run_id=run_id,
            backend=backend,
            extracted_events_summary=_event_summary_for_recovery(merged_output),
            evidence_items=evidence_items,
            deals_dir=deals_dir,
            model=model,
        )
        recovery_usage = {k: v for k, v in recovery_result.items() if k != "output"}
        subset = build_recovery_block_subset(recovery_result["output"], blocks)
        if subset:
            recovered = _invoke_event_call(
                backend,
                seed_context={
                    "deal_slug": deal_slug,
                    "target_name": seed.target_name,
                    "accession_number": selection.accession_number,
                    "filing_type": selection.filing_type,
                },
                actor_roster=actor_roster,
                blocks=subset,
                chunk_mode="recovery",
                chunk_id="recovery",
                prior_round_context=prior_round_context,
                evidence_items=prompt_evidence,
                model=model,
                complexity=complexity,
            )
            merged_output = recover_missing_events(merged_output, recovered.output)
            chunk_usage_records.append({"chunk_id": "recovery", **summarize_usage(recovered)})

    atomic_write_json(extract_dir / EVENT_OUTPUT_FILENAME, merged_output.model_dump(mode="json"))
    atomic_write_jsonl(
        extract_dir / EVENT_CHUNKS_FILENAME,
        [output.model_dump(mode="json") for output in chunk_outputs],
    )
    atomic_write_json(
        extract_dir / EVENT_USAGE_FILENAME,
        {
            "deal_slug": deal_slug,
            "run_id": run_id,
            "token_count": token_count,
            "line_count": line_count,
            "complexity": complexity.value,
            "chunk_mode": chunk_mode,
            "chunk_count": len(chunk_groups),
            "calls": chunk_usage_records,
            "recovery": recovery_usage,
        },
    )
    return {
        "deal_slug": deal_slug,
        "event_count": len(merged_output.events),
        "exclusion_count": len(merged_output.exclusions),
        "unresolved_mention_count": len(merged_output.unresolved_mentions),
        "complexity": complexity.value,
        "chunk_mode": chunk_mode,
        "chunk_count": len(chunk_groups),
    }


def _invoke_event_call(
    backend,
    *,
    seed_context: dict[str, Any],
    actor_roster,
    blocks,
    chunk_mode: str,
    chunk_id: str,
    prior_round_context: list[str] | str | None,
    evidence_items,
    model: str | None,
    complexity,
):
    effective_model = (model or getattr(backend, "model", "") or "").strip().lower()
    provider = (getattr(backend, "provider", "") or "").strip().lower()
    max_tokens = estimate_max_output_tokens(complexity, "event")
    if provider == "openai" and effective_model.startswith("gpt-5"):
        # GPT-5 event extraction can defer visible JSON until late in the
        # completion. Give it a larger output cap than the provider-neutral
        # defaults or moderately complex chunks can terminate with no text.
        gpt5_minimums = {
            "simple": 8_000,
            "moderate": 12_000,
            "complex": 16_000,
        }
        max_tokens = max(max_tokens, gpt5_minimums[complexity.value])
    if provider == "anthropic" and effective_model.startswith("claude-"):
        # Anthropic can also truncate long event chunks mid-object in prompted
        # JSON mode. Give moderate/complex chunks extra room so the first pass
        # can finish the top-level object instead of exhausting repairs.
        anthropic_minimums = {
            "simple": 3_000,
            "moderate": 10_000,
            "complex": 14_000,
        }
        max_tokens = max(max_tokens, anthropic_minimums[complexity.value])

    messages = [
        {
            "role": "user",
            "content": PromptPack.render_event_user_message(
                seed_context,
                actor_roster,
                blocks,
                chunk_mode=chunk_mode,
                chunk_id=chunk_id,
                prior_round_context=prior_round_context,
                evidence_items=evidence_items,
            ),
        }
    ]
    return backend.invoke_structured(
        messages=messages,
        system=PromptPack.EVENT_SYSTEM_PROMPT,
        output_schema=EventExtractionOutput,
        max_tokens=max_tokens,
        model=model,
    )


def _round_context_lines(output: EventExtractionOutput) -> list[str]:
    lines: list[str] = []
    for event in output.events:
        if event.event_type in {
            EventType.FINAL_ROUND_INF_ANN,
            EventType.FINAL_ROUND_INF,
            EventType.FINAL_ROUND_ANN,
            EventType.FINAL_ROUND,
            EventType.FINAL_ROUND_EXT_ANN,
            EventType.FINAL_ROUND_EXT,
        }:
            lines.append(f"{event.event_type.value} on {event.date.raw_text}")
    return lines


def _event_summary_for_recovery(output: EventExtractionOutput) -> list[dict[str, Any]]:
    summary = []
    for event in output.events:
        summary.append(
            {
                "event_type": event.event_type.value,
                "date": event.date.raw_text,
                "actor_ids": event.actor_ids,
                "summary": event.summary,
                "evidence_refs": [ref.model_dump(mode="json") for ref in event.evidence_refs],
            }
        )
    return summary
```

---

## pipeline/extract/merge.py
```python
from __future__ import annotations

from typing import Any

from pipeline.llm.schemas import EventExtractionOutput, RawEventRecord, RawExclusion


def merge_event_outputs(outputs: list[EventExtractionOutput]) -> EventExtractionOutput:
    merged_events: list[RawEventRecord] = []
    seen_event_keys: set[tuple[Any, ...]] = set()
    merged_exclusions: list[RawExclusion] = []
    seen_exclusion_keys: set[tuple[Any, ...]] = set()
    unresolved_mentions: list[str] = []
    coverage_notes: list[str] = []

    for output in outputs:
        for event in output.events:
            key = _event_key(event)
            if key in seen_event_keys:
                continue
            seen_event_keys.add(key)
            merged_events.append(event)
        for exclusion in output.exclusions:
            key = (exclusion.category, tuple(sorted(exclusion.block_ids)), exclusion.explanation.strip())
            if key in seen_exclusion_keys:
                continue
            seen_exclusion_keys.add(key)
            merged_exclusions.append(exclusion)
        for mention in output.unresolved_mentions:
            if mention not in unresolved_mentions:
                unresolved_mentions.append(mention)
        for note in output.coverage_notes:
            if note not in coverage_notes:
                coverage_notes.append(note)

    merged_events.sort(key=_event_sort_key)
    return EventExtractionOutput(
        events=merged_events,
        exclusions=merged_exclusions,
        unresolved_mentions=unresolved_mentions,
        coverage_notes=coverage_notes,
    )


def _event_key(event: RawEventRecord) -> tuple[Any, ...]:
    terms = event.terms
    terms_key = None
    if terms is not None:
        terms_key = (
            str(terms.value_per_share) if terms.value_per_share is not None else None,
            str(terms.lower_per_share) if terms.lower_per_share is not None else None,
            str(terms.upper_per_share) if terms.upper_per_share is not None else None,
            str(terms.total_enterprise_value) if terms.total_enterprise_value is not None else None,
            terms.is_range,
        )
    evidence_key = tuple(
        sorted(
            (
                ref.block_id or "",
                ref.evidence_id or "",
                " ".join(ref.anchor_text.lower().split()),
            )
            for ref in event.evidence_refs
        )
    )
    return (
        event.event_type.value,
        " ".join(event.date.raw_text.lower().split()),
        tuple(sorted(event.actor_ids)),
        terms_key,
        evidence_key,
    )


def _event_sort_key(event: RawEventRecord) -> tuple[Any, ...]:
    return (
        event.date.normalized_hint or "",
        event.date.raw_text,
        event.event_type.value,
        tuple(event.actor_ids),
        event.summary,
    )
```

---

## pipeline/extract/recovery.py
```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from pipeline.config import DEALS_DIR
from pipeline.llm.prompts import PromptPack
from pipeline.llm.schemas import EventExtractionOutput, RecoveryAuditOutput
from pipeline.extract.merge import merge_event_outputs
from pipeline.extract.utils import atomic_write_json, select_prompt_evidence_items, summarize_usage
from pipeline.models.common import EventType
from pipeline.models.source import ChronologyBlock, EvidenceItem


RECOVERY_OUTPUT_FILENAME = "recovery_raw.json"
RECOVERY_USAGE_FILENAME = "recovery_usage.json"


def needs_recovery_audit(
    event_output: EventExtractionOutput,
    *,
    evidence_items: list[EvidenceItem],
) -> bool:
    proposal_count = sum(1 for event in event_output.events if event.event_type == EventType.PROPOSAL)
    nda_count = sum(1 for event in event_output.events if event.event_type == EventType.NDA)
    outcome_count = sum(
        1
        for event in event_output.events
        if event.event_type in {EventType.EXECUTED, EventType.TERMINATED}
    )

    financial_items = [item for item in evidence_items if item.evidence_type.value == "financial_term"]
    process_items = [item for item in evidence_items if item.evidence_type.value == "process_signal"]
    outcome_items = [item for item in evidence_items if item.evidence_type.value == "outcome_fact"]

    if proposal_count == 0 and financial_items:
        return True
    if nda_count == 0 and any("confidentiality" in item.raw_text.lower() or "nda" in item.raw_text.lower() for item in process_items):
        return True
    if outcome_count == 0 and outcome_items:
        return True
    if len(event_output.events) < 3 and (financial_items or process_items):
        return True
    return False


def run_recovery_audit(
    blocks: list[ChronologyBlock],
    *,
    deal_slug: str,
    run_id: str,
    backend,
    extracted_events_summary: Any,
    evidence_items: list[EvidenceItem],
    deals_dir: Path = DEALS_DIR,
    model: str | None = None,
) -> dict[str, Any]:
    extract_dir = deals_dir / deal_slug / "extract"
    extract_dir.mkdir(parents=True, exist_ok=True)

    prompt_evidence = select_prompt_evidence_items(evidence_items, max_total=30, max_per_type=8)
    messages = [
        {
            "role": "user",
            "content": PromptPack.render_recovery_user_message(
                blocks,
                extracted_events_summary,
                evidence_items=prompt_evidence,
            ),
        }
    ]
    result = backend.invoke_structured(
        messages=messages,
        system=PromptPack.RECOVERY_SYSTEM_PROMPT,
        output_schema=RecoveryAuditOutput,
        max_tokens=1500,
        model=model,
    )
    atomic_write_json(extract_dir / RECOVERY_OUTPUT_FILENAME, result.output.model_dump(mode="json"))
    atomic_write_json(
        extract_dir / RECOVERY_USAGE_FILENAME,
        {
            **summarize_usage(result),
            "deal_slug": deal_slug,
            "run_id": run_id,
            "recovery_target_count": len(result.output.recovery_targets),
        },
    )
    return {
        "output": result.output,
        **summarize_usage(result),
    }


def build_recovery_block_subset(
    recovery_output: RecoveryAuditOutput,
    blocks: list[ChronologyBlock],
) -> list[ChronologyBlock]:
    by_id = {block.block_id: block for block in blocks}
    selected: list[ChronologyBlock] = []
    seen: set[str] = set()
    for target in recovery_output.recovery_targets:
        for block_id in target.block_ids:
            if block_id not in by_id or block_id in seen:
                continue
            seen.add(block_id)
            selected.append(by_id[block_id])
    selected.sort(key=lambda block: block.ordinal)
    return selected


def recover_missing_events(
    existing_output: EventExtractionOutput,
    recovered_output: EventExtractionOutput,
) -> EventExtractionOutput:
    return merge_event_outputs([existing_output, recovered_output])
```
