from __future__ import annotations

import csv
import hashlib
import json
import logging
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from pipeline.providers import Provider, ProviderResult
from pipeline.schemas import (
    Actor,
    AuditFlags,
    ChronologyBookmark,
    CorpusManifestEntry,
    CountAssertion,
    Deal,
    DealState,
    Decision,
    Event,
    EventActorLink,
    FormalBoundary,
    Initiation,
    Judgment,
    PipelineResult,
    ProcessCycle,
    Reconciliation,
    ReviewStatus,
    SeedDeal,
    SourceSelection,
    Stage2Result,
)
from pipeline.stage1_sourcing import run_stage1
from pipeline.stage3_audit import run_stage3_audit
from pipeline.stage3_enrichment import run_stage3
from pipeline.stage4_assembly import rebuild_master_csv


logger = logging.getLogger(__name__)


DEFAULT_STAGE_ORDER: tuple[str, ...] = ("stage1", "stage2", "stage3", "stage3_audit", "stage4")
_JUDGMENT_ADAPTER = TypeAdapter(Judgment)


def _utc_now_iso() -> str:
    """Return the current UTC timestamp in ISO 8601 form."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _atomic_write_text(path: Path, text: str) -> None:
    """Write text atomically to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor: int
    tmp_path_str: str
    file_descriptor, tmp_path_str = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp_path: Path = Path(tmp_path_str)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def _read_json(path: Path) -> Any:
    """Read a JSON file and deserialize its payload."""

    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_json_model(path: Path, model_type: type[Any]) -> Any:
    """Read a JSON file and validate it against a model class."""

    return model_type.model_validate(_read_json(path))


def _read_jsonl_models(path: Path, model_type: type[Any] | TypeAdapter) -> list[Any]:
    """Read JSONL records and validate them against a model or type adapter."""

    rows: list[Any] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line: str = raw_line.strip()
            if not line:
                continue
            payload: dict[str, Any] = json.loads(line)
            if isinstance(model_type, TypeAdapter):
                rows.append(model_type.validate_python(payload))
            else:
                rows.append(model_type.model_validate(payload))
    return rows


def _write_json(path: Path, payload: object) -> None:
    """Write JSON atomically with stable formatting."""

    _atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _write_jsonl(path: Path, rows: list[Any]) -> None:
    """Write JSONL atomically from validated models."""

    serialized_lines: list[str] = []
    for row in rows:
        if hasattr(row, "model_dump"):
            payload: object = row.model_dump(mode="json")
        else:
            payload = row
        serialized_lines.append(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    _atomic_write_text(path, "\n".join(serialized_lines) + ("\n" if serialized_lines else ""))


def _sha256_bytes(data: bytes) -> str:
    """Return the SHA-256 hex digest for raw bytes."""

    return hashlib.sha256(data).hexdigest()


def _json_hash(payload: object) -> str:
    """Return a stable SHA-256 hash for a JSON-serializable payload."""

    return _sha256_bytes(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8"))


def _file_hash(path: Path) -> str:
    """Return the SHA-256 hash of a file's bytes."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk: bytes = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _hash_paths(paths: list[Path]) -> str:
    """Compute a SHA-256 hash across multiple existing files."""

    digest = hashlib.sha256()
    for path in sorted({candidate.resolve() for candidate in paths if candidate.exists()}):
        relative_marker: str = str(path)
        digest.update(relative_marker.encode("utf-8"))
        with path.open("rb") as handle:
            while True:
                chunk: bytes = handle.read(65536)
                if not chunk:
                    break
                digest.update(chunk)
    return digest.hexdigest()


def init_database(db_path: Path) -> sqlite3.Connection:
    """Initialize the SQLite pipeline state database and return an open connection."""

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn: sqlite3.Connection = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS deals (
            deal_slug TEXT PRIMARY KEY,
            target_name TEXT NOT NULL,
            cik TEXT,
            filing_url TEXT,
            status TEXT NOT NULL,
            current_stage TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS stage_runs (
            deal_slug TEXT NOT NULL,
            stage_name TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            error_message TEXT,
            input_hash TEXT,
            output_hash TEXT,
            model_id TEXT,
            prompt_version TEXT,
            cost_usd REAL NOT NULL DEFAULT 0,
            PRIMARY KEY (deal_slug, stage_name),
            FOREIGN KEY (deal_slug) REFERENCES deals(deal_slug)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cost_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deal_slug TEXT NOT NULL,
            stage_name TEXT NOT NULL,
            provider TEXT NOT NULL,
            model_id TEXT NOT NULL,
            input_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            cost_usd REAL NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (deal_slug) REFERENCES deals(deal_slug)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_stage_runs_stage_status ON stage_runs(stage_name, status)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_cost_tracking_deal_stage ON cost_tracking(deal_slug, stage_name)"
    )
    conn.commit()
    return conn


def load_seed_csv(csv_path: Path) -> list[SeedDeal]:
    """Load seed deals from a CSV with deal_slug, target_name, and filing_url columns."""

    seeds: list[SeedDeal] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            deal_slug: str = str(row.get("deal_slug", "")).strip()
            target_name: str = str(row.get("target_name", "")).strip()
            filing_url_value: str = str(row.get("filing_url", "")).strip()
            filing_url: str | None = filing_url_value or None
            if not deal_slug or not target_name:
                continue
            seeds.append(SeedDeal(deal_slug=deal_slug, target_name=target_name, filing_url=filing_url))
    return seeds


def register_deals(conn: sqlite3.Connection, seeds: list[SeedDeal]) -> int:
    """Register seed deals in the database, skipping rows already present."""

    now: str = _utc_now_iso()
    inserted_count: int = 0
    deduped: dict[str, SeedDeal] = {}
    for seed in seeds:
        deduped.setdefault(seed.deal_slug, seed)
    for seed in deduped.values():
        existing = conn.execute("SELECT deal_slug FROM deals WHERE deal_slug = ?", (seed.deal_slug,)).fetchone()
        if existing is not None:
            continue
        conn.execute(
            """
            INSERT INTO deals (
                deal_slug,
                target_name,
                cik,
                filing_url,
                status,
                current_stage,
                error_message,
                created_at,
                updated_at
            ) VALUES (?, ?, NULL, ?, 'pending', NULL, NULL, ?, ?)
            """,
            (seed.deal_slug, seed.target_name, seed.filing_url, now, now),
        )
        inserted_count += 1
    conn.commit()
    return inserted_count


def get_pending_deals(conn: sqlite3.Connection, stage: str | None = None) -> list[str]:
    """Return deal slugs pending overall execution or a specific stage."""

    if stage is None:
        rows = conn.execute(
            "SELECT deal_slug FROM deals WHERE status != 'complete' ORDER BY deal_slug"
        ).fetchall()
        return [str(row["deal_slug"]) for row in rows]
    rows = conn.execute(
        """
        SELECT d.deal_slug
        FROM deals AS d
        LEFT JOIN stage_runs AS s
          ON d.deal_slug = s.deal_slug
         AND s.stage_name = ?
         AND s.status = 'complete'
        WHERE s.deal_slug IS NULL
        ORDER BY d.deal_slug
        """,
        (stage,),
    ).fetchall()
    return [str(row["deal_slug"]) for row in rows]


def mark_stage_start(conn: sqlite3.Connection, deal_slug: str, stage: str) -> None:
    """Record the start of a stage run for a deal."""

    now: str = _utc_now_iso()
    conn.execute(
        """
        INSERT INTO stage_runs (
            deal_slug, stage_name, status, started_at, completed_at, error_message,
            input_hash, output_hash, model_id, prompt_version, cost_usd
        ) VALUES (?, ?, 'running', ?, NULL, NULL, NULL, NULL, NULL, NULL, 0)
        ON CONFLICT(deal_slug, stage_name) DO UPDATE SET
            status='running',
            started_at=excluded.started_at,
            completed_at=NULL,
            error_message=NULL,
            input_hash=NULL,
            output_hash=NULL,
            model_id=NULL,
            prompt_version=NULL,
            cost_usd=0
        """,
        (deal_slug, stage, now),
    )
    conn.execute(
        """
        UPDATE deals
           SET status = ?, current_stage = ?, error_message = NULL, updated_at = ?
         WHERE deal_slug = ?
        """,
        (stage, stage, now, deal_slug),
    )
    conn.commit()


def mark_stage_complete(conn: sqlite3.Connection, deal_slug: str, stage: str, output_hash: str) -> None:
    """Record successful completion of a stage for a deal."""

    now: str = _utc_now_iso()
    conn.execute(
        """
        UPDATE stage_runs
           SET status = 'complete', completed_at = ?, error_message = NULL, output_hash = ?
         WHERE deal_slug = ? AND stage_name = ?
        """,
        (now, output_hash, deal_slug, stage),
    )
    status_value: str = "complete" if stage == "stage4" else stage
    conn.execute(
        """
        UPDATE deals
           SET status = ?, current_stage = ?, error_message = NULL, updated_at = ?
         WHERE deal_slug = ?
        """,
        (status_value, stage, now, deal_slug),
    )
    conn.commit()


def mark_stage_failed(conn: sqlite3.Connection, deal_slug: str, stage: str, error: str) -> None:
    """Record a failed stage run for a deal."""

    now: str = _utc_now_iso()
    conn.execute(
        """
        UPDATE stage_runs
           SET status = 'failed', completed_at = ?, error_message = ?
         WHERE deal_slug = ? AND stage_name = ?
        """,
        (now, error, deal_slug, stage),
    )
    conn.execute(
        """
        UPDATE deals
           SET status = 'failed', current_stage = ?, error_message = ?, updated_at = ?
         WHERE deal_slug = ?
        """,
        (stage, error, now, deal_slug),
    )
    conn.commit()


def record_cost(
    conn: sqlite3.Connection,
    deal_slug: str,
    stage: str,
    provider: str,
    model_id: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
) -> None:
    """Record token usage and cost for a stage."""

    timestamp: str = _utc_now_iso()
    conn.execute(
        """
        INSERT INTO cost_tracking (
            deal_slug, stage_name, provider, model_id, input_tokens, output_tokens, cost_usd, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (deal_slug, stage, provider, model_id, input_tokens, output_tokens, cost_usd, timestamp),
    )
    conn.execute(
        """
        UPDATE stage_runs
           SET cost_usd = COALESCE(cost_usd, 0) + ?, model_id = ?
         WHERE deal_slug = ? AND stage_name = ?
        """,
        (cost_usd, model_id, deal_slug, stage),
    )
    conn.commit()


def compute_artifact_hash(deal_dir: Path, stage: str) -> str:
    """Compute a deterministic SHA-256 hash over the artifacts produced by a stage."""

    stage_files: list[Path]
    if stage == "stage1":
        stage_files = [
            deal_dir / "source" / "source_selection.json",
            deal_dir / "source" / "corpus_manifest.json",
            deal_dir / "source" / "chronology_bookmark.json",
            *sorted((deal_dir / "source" / "filings").glob("*")),
        ]
    elif stage == "stage2":
        stage_files = [
            deal_dir / "extraction" / "actors.jsonl",
            deal_dir / "extraction" / "count_assertions.json",
            deal_dir / "extraction" / "events.jsonl",
            deal_dir / "extraction" / "event_actor_links.jsonl",
            deal_dir / "extraction" / "reconciliations.json",
            deal_dir / "extraction" / "deal.json",
        ]
    elif stage == "stage3":
        stage_files = [
            deal_dir / "enrichment" / "process_cycles.jsonl",
            deal_dir / "enrichment" / "judgments.jsonl",
        ]
    elif stage == "stage3_audit":
        stage_files = [
            deal_dir / "extraction" / "census.json",
            deal_dir / "extraction" / "audit_flags.json",
        ]
    elif stage == "stage4":
        stage_files = [
            deal_dir / "master_rows.csv",
            deal_dir / "review" / "review_status.json",
            deal_dir / "review" / "overrides.csv",
        ]
    else:
        raise ValueError(f"Unknown stage for artifact hashing: {stage}")
    return _hash_paths(stage_files)


def _set_stage_input_hash(conn: sqlite3.Connection, deal_slug: str, stage: str, input_hash: str) -> None:
    """Persist the computed input hash for a stage run."""

    conn.execute(
        "UPDATE stage_runs SET input_hash = ? WHERE deal_slug = ? AND stage_name = ?",
        (input_hash, deal_slug, stage),
    )
    conn.commit()


def _set_stage_prompt_metadata(conn: sqlite3.Connection, deal_slug: str, stage: str, model_id: str, prompt_version: str) -> None:
    """Persist model and prompt metadata for a stage run."""

    conn.execute(
        "UPDATE stage_runs SET model_id = ?, prompt_version = ? WHERE deal_slug = ? AND stage_name = ?",
        (model_id, prompt_version, deal_slug, stage),
    )
    conn.commit()


def _get_stage_run(conn: sqlite3.Connection, deal_slug: str, stage: str) -> sqlite3.Row | None:
    """Fetch the persisted stage run row for a deal and stage."""

    return conn.execute(
        "SELECT * FROM stage_runs WHERE deal_slug = ? AND stage_name = ?",
        (deal_slug, stage),
    ).fetchone()


def _stage_complete_and_current(
    conn: sqlite3.Connection,
    deal_slug: str,
    stage: str,
    expected_input_hash: str,
    deal_dir: Path,
) -> bool:
    """Return whether a stage can be safely skipped under resume mode."""

    stage_run = _get_stage_run(conn, deal_slug, stage)
    if stage_run is None:
        return False
    if stage_run["status"] != "complete":
        return False
    if stage_run["input_hash"] != expected_input_hash:
        return False
    try:
        current_output_hash: str = compute_artifact_hash(deal_dir, stage)
    except Exception:
        return False
    return current_output_hash == stage_run["output_hash"]


def _hash_reference_dir(reference_dir: Path) -> str:
    """Hash reference files that can affect stage 4 assembly."""

    if not reference_dir.exists():
        return _sha256_bytes(b"")
    return _hash_paths([path for path in reference_dir.rglob("*") if path.is_file()])


def _seed_hash(seed: SeedDeal) -> str:
    """Hash a seed row for stage 1 idempotency checks."""

    return _json_hash(
        {
            "deal_slug": seed.deal_slug,
            "target_name": seed.target_name,
            "filing_url": seed.filing_url,
        }
    )


def _stage_input_hash(stage: str, deal_dir: Path, provider: Provider | None, reference_dir: Path) -> str:
    """Compute the expected input hash for a stage."""

    if stage == "stage1":
        raise ValueError("stage1 input hash must be computed from the seed row")
    if stage == "stage2":
        stage1_hash: str = compute_artifact_hash(deal_dir, "stage1")
        provider_identity: dict[str, str] = {
            "provider_name": provider.config.provider_name if provider is not None else "",
            "model_id": provider.config.model_id if provider is not None else "",
        }
        return _json_hash({"stage1_hash": stage1_hash, **provider_identity})
    if stage == "stage3":
        return _json_hash({"stage2_hash": compute_artifact_hash(deal_dir, "stage2")})
    if stage == "stage3_audit":
        return _json_hash(
            {
                "stage2_hash": compute_artifact_hash(deal_dir, "stage2"),
                "stage3_hash": compute_artifact_hash(deal_dir, "stage3"),
            }
        )
    if stage == "stage4":
        return _json_hash(
            {
                "stage3_hash": compute_artifact_hash(deal_dir, "stage3"),
                "stage3_audit_hash": compute_artifact_hash(deal_dir, "stage3_audit"),
                "reference_hash": _hash_reference_dir(reference_dir),
            }
        )
    raise ValueError(f"Unknown stage: {stage}")


def _primary_txt_path(deal_state: DealState) -> Path:
    """Resolve the primary frozen text path from the loaded deal state."""

    for entry in deal_state.corpus_manifest:
        if entry.role == "primary":
            return deal_state.deal_dir / entry.txt_filename
    raise FileNotFoundError(f"No primary text file found for {deal_state.deal_slug}")


def _primary_manifest_entry(deal_state: DealState) -> CorpusManifestEntry:
    """Return the primary corpus manifest entry from the deal state."""

    for entry in deal_state.corpus_manifest:
        if entry.role == "primary":
            return entry
    raise FileNotFoundError(f"No primary manifest entry found for {deal_state.deal_slug}")


def _chronology_text(deal_state: DealState) -> str:
    """Extract the chronology slice text from the primary frozen text file."""

    if deal_state.chronology_bookmark is None:
        raise ValueError(f"Chronology bookmark is missing for {deal_state.deal_slug}")
    txt_path: Path = _primary_txt_path(deal_state)
    lines: list[str] = txt_path.read_text(encoding="utf-8").splitlines()
    start_index: int = max(deal_state.chronology_bookmark.start_line - 1, 0)
    end_index: int = min(deal_state.chronology_bookmark.end_line, len(lines))
    return "\n".join(lines[start_index:end_index]) + "\n"


def _sort_actors(actors: list[Actor]) -> list[Actor]:
    """Sort actors deterministically for stable artifact output."""

    return sorted(
        actors,
        key=lambda actor: (
            actor.first_evidence_accession_number,
            actor.first_evidence_line_start,
            actor.actor_id,
        ),
    )


def _sort_count_assertions(assertions: list[CountAssertion]) -> list[CountAssertion]:
    """Sort count assertions deterministically for stable artifact output."""

    return sorted(
        assertions,
        key=lambda assertion: (
            assertion.source_accession_number,
            assertion.source_line_start,
            assertion.assertion_id,
        ),
    )


def _sort_events(events: list[Event]) -> list[Event]:
    """Sort events deterministically for stable artifact output."""

    return sorted(
        events,
        key=lambda event: (event.date, event.source_line_start, event.event_id),
    )


def _sort_links(links: list[EventActorLink]) -> list[EventActorLink]:
    """Sort event-actor links deterministically for stable artifact output."""

    return sorted(links, key=lambda link: (link.event_id, link.actor_id, link.participation_role))


def _sort_reconciliations(reconciliations: list[Reconciliation]) -> list[Reconciliation]:
    """Sort reconciliations deterministically for stable artifact output."""

    return sorted(reconciliations, key=lambda item: item.assertion_id)


def _validate_actor_outputs(deal_slug: str, actors: list[Actor], assertions: list[CountAssertion]) -> None:
    """Validate provider actor and count assertion outputs for deterministic safety."""

    actor_ids: list[str] = [actor.actor_id for actor in actors]
    if len(actor_ids) != len(set(actor_ids)):
        raise ValueError(f"Duplicate actor IDs returned for {deal_slug}")
    for actor in actors:
        expected_prefix: str = f"{deal_slug}/"
        if not actor.actor_id.startswith(expected_prefix):
            raise ValueError(f"Actor ID {actor.actor_id} does not start with {expected_prefix}")
    assertion_ids: list[str] = [assertion.assertion_id for assertion in assertions]
    if len(assertion_ids) != len(set(assertion_ids)):
        raise ValueError(f"Duplicate assertion IDs returned for {deal_slug}")


def _validate_event_outputs(
    deal_slug: str,
    actors: list[Actor],
    events: list[Event],
    links: list[EventActorLink],
) -> None:
    """Validate provider event and link outputs for deterministic safety."""

    actor_id_set: set[str] = {actor.actor_id for actor in actors}
    event_ids: list[str] = [event.event_id for event in events]
    event_id_set: set[str] = set(event_ids)
    if len(event_ids) != len(event_id_set):
        raise ValueError(f"Duplicate event IDs returned for {deal_slug}")
    for link in links:
        if link.event_id not in event_id_set:
            raise ValueError(f"Event-actor link references unknown event_id {link.event_id}")
        if link.actor_id not in actor_id_set:
            raise ValueError(f"Event-actor link references unknown actor_id {link.actor_id}")


def _validate_reconciliations(assertions: list[CountAssertion], reconciliations: list[Reconciliation]) -> None:
    """Validate reconciliation outputs against known assertion identifiers."""

    assertion_id_set: set[str] = {assertion.assertion_id for assertion in assertions}
    for reconciliation in reconciliations:
        if reconciliation.assertion_id not in assertion_id_set:
            raise ValueError(f"Reconciliation references unknown assertion_id {reconciliation.assertion_id}")


def _merge_stage1_fields_into_deal(deal_state: DealState, extracted_deal: Deal) -> Deal:
    """Override provider-supplied deal fields with authoritative stage 1 metadata."""

    primary_manifest: CorpusManifestEntry = _primary_manifest_entry(deal_state)
    authoritative_updates: dict[str, Any] = {
        "deal_slug": deal_state.deal_slug,
        "target_name": deal_state.target_name,
        "cik": deal_state.cik or extracted_deal.cik,
        "primary_accession_number": primary_manifest.accession_number,
        "filing_type": primary_manifest.filing_type,
        "filing_url": primary_manifest.url,
        "filing_date": primary_manifest.filing_date,
    }
    merged: Deal = extracted_deal.model_copy(update=authoritative_updates)
    return merged


def _stage1_seed_decisions(decisions_path: Path) -> list[Decision]:
    """Load only stage 1 sourcing decisions from the shared decisions log."""

    decisions: list[Decision] = []
    if not decisions_path.exists():
        return decisions
    with decisions_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line: str = raw_line.strip()
            if not line:
                continue
            decision: Decision = Decision.model_validate_json(line)
            if decision.skill == "stage1_sourcing":
                decisions.append(decision)
    return decisions


def _record_provider_last_result(conn: sqlite3.Connection, deal_slug: str, stage: str, provider: Provider) -> None:
    """Persist token-cost metadata for the provider's most recent call, when available."""

    provider_result: ProviderResult[Any] | None = provider.last_result
    if provider_result is None:
        return
    record_cost(
        conn=conn,
        deal_slug=deal_slug,
        stage=stage,
        provider=provider.config.provider_name,
        model_id=provider_result.model_id,
        input_tokens=provider_result.cost.input_tokens,
        output_tokens=provider_result.cost.output_tokens,
        cost_usd=provider_result.cost.cost_usd,
    )
    _set_stage_prompt_metadata(
        conn,
        deal_slug,
        stage,
        provider_result.model_id,
        provider_result.prompt_version,
    )


def _run_stage2(deal_state: DealState, provider: Provider, conn: sqlite3.Connection) -> Stage2Result:
    """Run provider-backed extraction with deterministic validation and persistence."""

    chronology_text: str = _chronology_text(deal_state)
    primary_manifest: CorpusManifestEntry = _primary_manifest_entry(deal_state)
    extraction_dir: Path = deal_state.deal_dir / "extraction"
    extraction_dir.mkdir(parents=True, exist_ok=True)

    actors, count_assertions, actor_decisions = provider.extract_actors(
        chronology_text,
        deal_state.deal_slug,
        primary_manifest.accession_number,
    )
    _record_provider_last_result(conn, deal_state.deal_slug, "stage2", provider)
    actors = _sort_actors(actors)
    count_assertions = _sort_count_assertions(count_assertions)
    _validate_actor_outputs(deal_state.deal_slug, actors, count_assertions)

    events, event_links, event_decisions = provider.extract_events(
        chronology_text,
        deal_state.deal_slug,
        actors,
        primary_manifest.accession_number,
    )
    _record_provider_last_result(conn, deal_state.deal_slug, "stage2", provider)
    events = _sort_events(events)
    event_links = _sort_links(event_links)
    _validate_event_outputs(deal_state.deal_slug, actors, events, event_links)

    reconciliations: list[Reconciliation] = provider.reconcile_counts(count_assertions, actors, events, event_links)
    _record_provider_last_result(conn, deal_state.deal_slug, "stage2", provider)
    reconciliations = _sort_reconciliations(reconciliations)
    _validate_reconciliations(count_assertions, reconciliations)

    extracted_deal: Deal = provider.extract_deal_metadata(chronology_text, deal_state.deal_slug, events, actors)
    _record_provider_last_result(conn, deal_state.deal_slug, "stage2", provider)
    merged_deal: Deal = _merge_stage1_fields_into_deal(deal_state, extracted_deal)
    if merged_deal.winning_acquirer and merged_deal.winning_acquirer not in {actor.actor_id for actor in actors}:
        raise ValueError(
            f"Winning acquirer {merged_deal.winning_acquirer} is not present in the extracted actor roster for {deal_state.deal_slug}"
        )

    stage1_decisions: list[Decision] = _stage1_seed_decisions(extraction_dir / "decisions.jsonl")
    combined_decisions: list[Decision] = [*stage1_decisions, *actor_decisions, *event_decisions]

    _write_jsonl(extraction_dir / "actors.jsonl", actors)
    _write_json(extraction_dir / "count_assertions.json", [item.model_dump(mode="json") for item in count_assertions])
    _write_jsonl(extraction_dir / "events.jsonl", events)
    _write_jsonl(extraction_dir / "event_actor_links.jsonl", event_links)
    _write_json(extraction_dir / "reconciliations.json", [item.model_dump(mode="json") for item in reconciliations])
    _write_json(extraction_dir / "deal.json", merged_deal.model_dump(mode="json"))
    _write_jsonl(extraction_dir / "decisions.jsonl", combined_decisions)

    deal_state.actors = actors
    deal_state.count_assertions = count_assertions
    deal_state.events = events
    deal_state.event_actor_links = event_links
    deal_state.reconciliations = reconciliations
    deal_state.deal = merged_deal
    deal_state.decisions = combined_decisions

    return Stage2Result(
        actors=actors,
        count_assertions=count_assertions,
        events=events,
        event_actor_links=event_links,
        decisions=combined_decisions,
        reconciliations=reconciliations,
        deal=merged_deal,
    )


def _load_deal_state(seed: SeedDeal, deal_dir: Path) -> DealState:
    """Load all available persisted artifacts for a deal into memory."""

    state = DealState(
        deal_slug=seed.deal_slug,
        target_name=seed.target_name,
        filing_url=seed.filing_url,
        deal_dir=deal_dir,
    )
    source_dir: Path = deal_dir / "source"
    extraction_dir: Path = deal_dir / "extraction"
    enrichment_dir: Path = deal_dir / "enrichment"

    source_selection_path: Path = source_dir / "source_selection.json"
    if source_selection_path.exists():
        state.source_selection = _read_json_model(source_selection_path, SourceSelection)
        state.cik = state.source_selection.cik

    corpus_manifest_path: Path = source_dir / "corpus_manifest.json"
    if corpus_manifest_path.exists():
        payload = _read_json(corpus_manifest_path)
        if isinstance(payload, list):
            state.corpus_manifest = [CorpusManifestEntry.model_validate(item) for item in payload]

    chronology_bookmark_path: Path = source_dir / "chronology_bookmark.json"
    if chronology_bookmark_path.exists():
        state.chronology_bookmark = _read_json_model(chronology_bookmark_path, ChronologyBookmark)

    actors_path: Path = extraction_dir / "actors.jsonl"
    if actors_path.exists():
        state.actors = _read_jsonl_models(actors_path, Actor)

    count_assertions_path: Path = extraction_dir / "count_assertions.json"
    if count_assertions_path.exists():
        payload = _read_json(count_assertions_path)
        if isinstance(payload, list):
            state.count_assertions = [CountAssertion.model_validate(item) for item in payload]

    events_path: Path = extraction_dir / "events.jsonl"
    if events_path.exists():
        state.events = _read_jsonl_models(events_path, Event)

    event_links_path: Path = extraction_dir / "event_actor_links.jsonl"
    if event_links_path.exists():
        state.event_actor_links = _read_jsonl_models(event_links_path, EventActorLink)

    reconciliations_path: Path = extraction_dir / "reconciliations.json"
    if reconciliations_path.exists():
        payload = _read_json(reconciliations_path)
        if isinstance(payload, list):
            state.reconciliations = [Reconciliation.model_validate(item) for item in payload]

    decisions_path: Path = extraction_dir / "decisions.jsonl"
    if decisions_path.exists():
        state.decisions = _read_jsonl_models(decisions_path, Decision)

    deal_path: Path = extraction_dir / "deal.json"
    if deal_path.exists():
        state.deal = _read_json_model(deal_path, Deal)
        state.cik = state.deal.cik

    process_cycles_path: Path = enrichment_dir / "process_cycles.jsonl"
    if process_cycles_path.exists():
        state.process_cycles = _read_jsonl_models(process_cycles_path, ProcessCycle)

    judgments_path: Path = enrichment_dir / "judgments.jsonl"
    if judgments_path.exists():
        state.judgments = _read_jsonl_models(judgments_path, _JUDGMENT_ADAPTER)

    census_path: Path = extraction_dir / "census.json"
    if census_path.exists():
        from pipeline.schemas import Census

        state.census = _read_json_model(census_path, Census)

    audit_flags_path: Path = extraction_dir / "audit_flags.json"
    if audit_flags_path.exists():
        state.audit_flags = _read_json_model(audit_flags_path, AuditFlags)

    return state


def _write_review_bundle_input_state_marker(deal_dir: Path) -> None:
    """Ensure the review directory exists before stage 4 assembly."""

    (deal_dir / "review").mkdir(parents=True, exist_ok=True)


def _update_deal_cik(conn: sqlite3.Connection, deal_slug: str, cik: str) -> None:
    """Persist the resolved CIK on the deals table."""

    conn.execute(
        "UPDATE deals SET cik = ?, updated_at = ? WHERE deal_slug = ?",
        (cik, _utc_now_iso(), deal_slug),
    )
    conn.commit()


def _sum_stage_costs(conn: sqlite3.Connection, deal_slug: str, stage: str) -> float:
    """Return the cumulative cost recorded for a deal and stage."""

    row = conn.execute(
        "SELECT COALESCE(SUM(cost_usd), 0) AS total_cost FROM cost_tracking WHERE deal_slug = ? AND stage_name = ?",
        (deal_slug, stage),
    ).fetchone()
    return float(row["total_cost"] if row is not None else 0.0)


def run_pipeline(
    seed_csv: Path,
    data_dir: Path,
    db_path: Path,
    provider: Provider,
    stages: list[str] | None = None,
    resume: bool = True,
) -> PipelineResult:
    """Run the deal extraction pipeline with checkpointing, resume, and cost tracking."""

    selected_stages: list[str] = list(stages) if stages is not None else list(DEFAULT_STAGE_ORDER)
    invalid_stages: set[str] = set(selected_stages).difference(DEFAULT_STAGE_ORDER)
    if invalid_stages:
        raise ValueError(f"Unknown stages requested: {sorted(invalid_stages)}")

    data_dir.mkdir(parents=True, exist_ok=True)
    deals_dir: Path = data_dir / "deals"
    views_dir: Path = data_dir / "views"
    reference_dir: Path = data_dir / "reference"
    deals_dir.mkdir(parents=True, exist_ok=True)
    views_dir.mkdir(parents=True, exist_ok=True)

    conn: sqlite3.Connection = init_database(db_path)
    seeds: list[SeedDeal] = load_seed_csv(seed_csv)
    inserted_count: int = register_deals(conn, seeds)
    seed_map: dict[str, SeedDeal] = {}
    for seed in seeds:
        seed_map.setdefault(seed.deal_slug, seed)

    completed_deals: list[str] = []
    failed_deals: dict[str, str] = {}
    skipped_deals: list[str] = []
    stage_counts: dict[str, int] = {stage: 0 for stage in DEFAULT_STAGE_ORDER}
    master_csv_path: Path | None = None

    for deal_slug in sorted(seed_map):
        seed: SeedDeal = seed_map[deal_slug]
        deal_dir: Path = deals_dir / deal_slug
        deal_dir.mkdir(parents=True, exist_ok=True)
        deal_failed: bool = False

        for stage in selected_stages:
            try:
                if stage == "stage1":
                    expected_input_hash: str = _seed_hash(seed)
                else:
                    expected_input_hash = _stage_input_hash(stage, deal_dir, provider, reference_dir)
            except Exception as exc:
                failed_deals[deal_slug] = f"Unable to compute input hash for {stage}: {exc}"
                deal_failed = True
                break

            if resume and _stage_complete_and_current(conn, deal_slug, stage, expected_input_hash, deal_dir):
                logger.info("resume_skip deal_slug=%s stage=%s", deal_slug, stage)
                stage_counts[stage] += 1
                skipped_deals.append(f"{deal_slug}:{stage}")
                continue

            try:
                mark_stage_start(conn, deal_slug, stage)
                _set_stage_input_hash(conn, deal_slug, stage, expected_input_hash)

                if stage == "stage1":
                    stage1_result = run_stage1(seed.deal_slug, seed.target_name, seed.filing_url, deal_dir)
                    _update_deal_cik(conn, deal_slug, stage1_result.cik)
                elif stage == "stage2":
                    deal_state: DealState = _load_deal_state(seed, deal_dir)
                    _run_stage2(deal_state, provider, conn)
                elif stage == "stage3":
                    deal_state = _load_deal_state(seed, deal_dir)
                    run_stage3(deal_state)
                elif stage == "stage3_audit":
                    deal_state = _load_deal_state(seed, deal_dir)
                    run_stage3_audit(deal_state)
                elif stage == "stage4":
                    _write_review_bundle_input_state_marker(deal_dir)
                    master_csv_path = rebuild_master_csv(deals_dir, views_dir, reference_dir)
                else:
                    raise ValueError(f"Unsupported stage {stage}")

                output_hash: str = compute_artifact_hash(deal_dir, stage)
                mark_stage_complete(conn, deal_slug, stage, output_hash)
                stage_counts[stage] += 1
            except Exception as exc:
                error_text: str = f"{type(exc).__name__}: {exc}"
                logger.exception("stage_failed deal_slug=%s stage=%s", deal_slug, stage)
                mark_stage_failed(conn, deal_slug, stage, error_text)
                failed_deals[deal_slug] = error_text
                deal_failed = True
                break

        if not deal_failed:
            completed_deals.append(deal_slug)

    total_cost_row = conn.execute("SELECT COALESCE(SUM(cost_usd), 0) AS total_cost FROM cost_tracking").fetchone()
    total_cost_usd: float = float(total_cost_row["total_cost"] if total_cost_row is not None else 0.0)

    if "stage4" in selected_stages and master_csv_path is None:
        master_csv_path = rebuild_master_csv(deals_dir, views_dir, reference_dir)

    conn.close()
    return PipelineResult(
        total_registered_deals=len(seed_map),
        completed_deals=completed_deals,
        failed_deals=failed_deals,
        skipped_deals=skipped_deals,
        total_cost_usd=total_cost_usd,
        stage_counts=stage_counts,
        master_csv_path=master_csv_path,
    )
