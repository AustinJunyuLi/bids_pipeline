from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.db_schema import open_pipeline_db
from skill_pipeline.extract_artifacts import load_extract_artifacts
from skill_pipeline.models import SkillActorsArtifact, SkillEventsArtifact, SpanRegistryArtifact
from skill_pipeline.paths import build_skill_paths


def run_db_load(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    paths = build_skill_paths(deal_slug, project_root=project_root)
    required_paths = [
        paths.actors_raw_path,
        paths.events_raw_path,
        paths.spans_path,
        paths.deterministic_enrichment_path,
    ]
    for path in required_paths:
        if not path.exists():
            raise FileNotFoundError(f"Missing required input: {path}")

    artifacts = load_extract_artifacts(paths)
    if artifacts.mode != "canonical":
        raise ValueError("db-load requires canonical extract artifacts")
    if artifacts.actors is None or artifacts.events is None or artifacts.spans is None:
        raise ValueError("Canonical extract artifacts must include actors, events, and spans")

    con = open_pipeline_db(paths.database_path)
    in_transaction = False
    try:
        con.execute("BEGIN TRANSACTION")
        in_transaction = True
        _delete_deal(con, deal_slug)
        _load_actors(con, deal_slug, artifacts.actors)
        _load_events(con, deal_slug, artifacts.events)
        _load_spans(con, deal_slug, artifacts.spans)
        deterministic_data = _load_enrichment(con, deal_slug, paths)
        _load_cycles(con, deal_slug, deterministic_data)
        _load_rounds(con, deal_slug, deterministic_data)
        con.execute("COMMIT")
        in_transaction = False
    except Exception:
        if in_transaction:
            con.execute("ROLLBACK")
        raise
    finally:
        con.close()
    return 0


def _delete_deal(con, deal_slug: str) -> None:
    for table_name in ("actors", "events", "spans", "enrichment", "cycles", "rounds"):
        con.execute(f"DELETE FROM {table_name} WHERE deal_slug = ?", [deal_slug])


def _load_actors(con, deal_slug: str, artifact: SkillActorsArtifact) -> None:
    rows = [
        (
            deal_slug,
            actor.actor_id,
            actor.display_name,
            actor.canonical_name,
            actor.aliases,
            actor.role,
            actor.advisor_kind,
            actor.advised_actor_id,
            actor.bidder_kind,
            actor.listing_status,
            actor.geography,
            actor.is_grouped,
            actor.group_size,
            actor.group_label,
            actor.evidence_span_ids,
        )
        for actor in artifact.actors
    ]
    if rows:
        con.executemany(
            """
            INSERT INTO actors (
                deal_slug,
                actor_id,
                display_name,
                canonical_name,
                aliases,
                role,
                advisor_kind,
                advised_actor_id,
                bidder_kind,
                listing_status,
                geography,
                is_grouped,
                group_size,
                group_label,
                evidence_span_ids
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def _load_events(con, deal_slug: str, artifact: SkillEventsArtifact) -> None:
    rows = []
    for event in artifact.events:
        terms = event.terms
        rows.append(
            (
                deal_slug,
                event.event_id,
                event.event_type,
                event.date.raw_text,
                event.date.sort_date,
                event.date.precision.value,
                event.actor_ids,
                event.summary,
                event.evidence_span_ids,
                _decimal_to_float(terms.per_share if terms else None),
                _decimal_to_float(terms.range_low if terms else None),
                _decimal_to_float(terms.range_high if terms else None),
                terms.consideration_type if terms else None,
                event.whole_company_scope,
                event.drop_reason_text,
                event.round_scope,
                event.invited_actor_ids,
                event.executed_with_actor_id,
                event.nda_signed,
            )
        )
    if rows:
        con.executemany(
            """
            INSERT INTO events (
                deal_slug,
                event_id,
                event_type,
                date_raw_text,
                date_sort,
                date_precision,
                actor_ids,
                summary,
                evidence_span_ids,
                terms_per_share,
                terms_range_low,
                terms_range_high,
                terms_consideration_type,
                whole_company_scope,
                drop_reason_text,
                round_scope,
                invited_actor_ids,
                executed_with_actor_id,
                nda_signed
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def _load_spans(con, deal_slug: str, artifact: SpanRegistryArtifact) -> None:
    rows = [
        (
            deal_slug,
            span.span_id,
            span.document_id,
            span.filing_type,
            span.start_line,
            span.end_line,
            span.block_ids,
            span.quote_text,
            span.match_type.value,
        )
        for span in artifact.spans
    ]
    if rows:
        con.executemany(
            """
            INSERT INTO spans (
                deal_slug,
                span_id,
                document_id,
                filing_type,
                start_line,
                end_line,
                block_ids,
                quote_text,
                match_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def _load_enrichment(con, deal_slug: str, paths) -> dict[str, Any]:
    deterministic_data = _read_json(paths.deterministic_enrichment_path)
    rows_by_event_id: dict[str, dict[str, Any]] = {}

    for event_id, classification in deterministic_data.get("bid_classifications", {}).items():
        rows_by_event_id[event_id] = {
            "deal_slug": deal_slug,
            "event_id": event_id,
            "dropout_label": None,
            "dropout_basis": None,
            "bid_label": classification["label"],
            "bid_rule_applied": classification.get("rule_applied"),
            "bid_basis": classification.get("basis"),
        }

    if paths.enrichment_path.exists():
        interpretive_data = _read_json(paths.enrichment_path)
        for event_id, classification in interpretive_data.get("dropout_classifications", {}).items():
            row = rows_by_event_id.setdefault(
                event_id,
                {
                    "deal_slug": deal_slug,
                    "event_id": event_id,
                    "dropout_label": None,
                    "dropout_basis": None,
                    "bid_label": None,
                    "bid_rule_applied": None,
                    "bid_basis": None,
                },
            )
            row["dropout_label"] = classification["label"]
            row["dropout_basis"] = classification.get("basis")

    rows = [
        (
            row["deal_slug"],
            row["event_id"],
            row["dropout_label"],
            row["dropout_basis"],
            row["bid_label"],
            row["bid_rule_applied"],
            row["bid_basis"],
        )
        for row in rows_by_event_id.values()
    ]
    if rows:
        con.executemany(
            """
            INSERT INTO enrichment (
                deal_slug,
                event_id,
                dropout_label,
                dropout_basis,
                bid_label,
                bid_rule_applied,
                bid_basis
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
    return deterministic_data


def _load_cycles(con, deal_slug: str, data: dict[str, Any]) -> None:
    rows = [
        (
            deal_slug,
            cycle["cycle_id"],
            cycle["start_event_id"],
            cycle["end_event_id"],
            cycle["boundary_basis"],
        )
        for cycle in data.get("cycles", [])
    ]
    if rows:
        con.executemany(
            """
            INSERT INTO cycles (
                deal_slug,
                cycle_id,
                start_event_id,
                end_event_id,
                boundary_basis
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )


def _load_rounds(con, deal_slug: str, data: dict[str, Any]) -> None:
    rows = [
        (
            deal_slug,
            round_record["announcement_event_id"],
            round_record.get("deadline_event_id"),
            round_record["round_scope"],
            round_record.get("invited_actor_ids", []),
            round_record["active_bidders_at_time"],
            round_record["is_selective"],
        )
        for round_record in data.get("rounds", [])
    ]
    if rows:
        con.executemany(
            """
            INSERT INTO rounds (
                deal_slug,
                announcement_event_id,
                deadline_event_id,
                round_scope,
                invited_actor_ids,
                active_bidders_at_time,
                is_selective
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _decimal_to_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)
