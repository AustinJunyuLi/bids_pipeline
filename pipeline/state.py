from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


class PipelineStateStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def start_run(
        self,
        *,
        run_id: str,
        code_version: str,
        config_hash: str,
        mode: str,
        resume: bool = False,
    ) -> dict[str, Any]:
        with self._write_connection() as conn:
            existing = conn.execute(
                "SELECT * FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if existing is not None:
                if resume:
                    return dict(existing)
                raise ValueError(f"Run already exists: {run_id}")

            started_at = _utc_now()
            conn.execute(
                """
                INSERT INTO runs (
                    run_id, started_at, finished_at, code_version, config_hash, mode
                ) VALUES (?, ?, NULL, ?, ?, ?)
                """,
                (run_id, started_at, code_version, config_hash, mode),
            )
            return dict(
                conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            )

    def list_runs(self) -> list[str]:
        with self._read_connection() as conn:
            rows = conn.execute(
                "SELECT run_id FROM runs ORDER BY started_at"
            ).fetchall()
            return [row["run_id"] for row in rows]

    def record_stage_attempt(
        self,
        *,
        run_id: str,
        deal_slug: str,
        stage_name: str,
        status: str,
        attempt_no: int | None = None,
        started_at: str | None = None,
        finished_at: str | None = None,
        duration_ms: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        review_required: bool = False,
    ) -> dict[str, Any]:
        with self._write_connection() as conn:
            if attempt_no is None:
                attempt_no = (
                    conn.execute(
                        """
                        SELECT COALESCE(MAX(attempt_no), 0) + 1
                        FROM stage_attempts
                        WHERE run_id = ? AND deal_slug = ? AND stage_name = ?
                        """,
                        (run_id, deal_slug, stage_name),
                    ).fetchone()[0]
                )

            started_at = started_at or _utc_now()
            if finished_at is None and status in {"success", "failed", "blocked"}:
                finished_at = _utc_now()

            conn.execute(
                """
                INSERT INTO stage_attempts (
                    run_id, deal_slug, stage_name, attempt_no, status,
                    started_at, finished_at, duration_ms, error_code,
                    error_message, review_required
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    deal_slug,
                    stage_name,
                    attempt_no,
                    status,
                    started_at,
                    finished_at,
                    duration_ms,
                    error_code,
                    error_message,
                    int(review_required),
                ),
            )
            row = conn.execute(
                """
                SELECT * FROM stage_attempts
                WHERE run_id = ? AND deal_slug = ? AND stage_name = ? AND attempt_no = ?
                """,
                (run_id, deal_slug, stage_name, attempt_no),
            ).fetchone()
            return dict(row)

    def record_artifact(
        self,
        *,
        run_id: str,
        deal_slug: str,
        artifact_type: str,
        path: str,
        sha256: str,
        schema_version: str,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        with self._write_connection() as conn:
            created_at = created_at or _utc_now()
            conn.execute(
                """
                INSERT INTO artifacts (
                    run_id, deal_slug, artifact_type, path, sha256, schema_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, deal_slug, artifact_type, path, sha256, schema_version, created_at),
            )
            row = conn.execute(
                """
                SELECT * FROM artifacts
                WHERE rowid = last_insert_rowid()
                """
            ).fetchone()
            return dict(row)

    def record_llm_call(
        self,
        *,
        call_id: str,
        run_id: str,
        deal_slug: str,
        unit_name: str,
        provider: str,
        model: str,
        prompt_version: str,
        request_id: str | None = None,
        input_tokens: int | None = None,
        cache_creation_input_tokens: int | None = None,
        cache_read_input_tokens: int | None = None,
        output_tokens: int | None = None,
        cost_usd: float | None = None,
        latency_ms: int | None = None,
        status: str = "success",
    ) -> dict[str, Any]:
        with self._write_connection() as conn:
            conn.execute(
                """
                INSERT INTO llm_calls (
                    call_id, run_id, deal_slug, unit_name, provider, model, prompt_version,
                    request_id, input_tokens, cache_creation_input_tokens,
                    cache_read_input_tokens, output_tokens, cost_usd, latency_ms, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    call_id,
                    run_id,
                    deal_slug,
                    unit_name,
                    provider,
                    model,
                    prompt_version,
                    request_id,
                    input_tokens,
                    cache_creation_input_tokens,
                    cache_read_input_tokens,
                    output_tokens,
                    cost_usd,
                    latency_ms,
                    status,
                ),
            )
            row = conn.execute(
                "SELECT * FROM llm_calls WHERE call_id = ?",
                (call_id,),
            ).fetchone()
            return dict(row)

    def record_review_item(
        self,
        *,
        review_id: str,
        deal_slug: str,
        stage_name: str,
        severity: str,
        code: str,
        message: str,
        artifact_path: str | None = None,
        status: str = "open",
        resolved_at: str | None = None,
    ) -> dict[str, Any]:
        with self._write_connection() as conn:
            conn.execute(
                """
                INSERT INTO review_items (
                    review_id, deal_slug, stage_name, severity, code, message,
                    artifact_path, status, resolved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    review_id,
                    deal_slug,
                    stage_name,
                    severity,
                    code,
                    message,
                    artifact_path,
                    status,
                    resolved_at,
                ),
            )
            row = conn.execute(
                "SELECT * FROM review_items WHERE review_id = ?",
                (review_id,),
            ).fetchone()
            return dict(row)

    def summarize_run(self, run_id: str) -> dict[str, Any]:
        with self._read_connection() as conn:
            run = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if run is None:
                raise ValueError(f"Unknown run_id: {run_id}")

            def count_rows(table: str) -> int:
                if table == "review_items":
                    query = "SELECT COUNT(*) FROM review_items"
                    params: tuple[Any, ...] = ()
                else:
                    query = f"SELECT COUNT(*) FROM {table} WHERE run_id = ?"
                    params = (run_id,)
                return int(conn.execute(query, params).fetchone()[0])

            return {
                "run": dict(run),
                "counts": {
                    "stage_attempts": count_rows("stage_attempts"),
                    "artifacts": count_rows("artifacts"),
                    "llm_calls": count_rows("llm_calls"),
                    "review_items": count_rows("review_items"),
                },
            }

    def _initialize(self) -> None:
        with self._write_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    code_version TEXT NOT NULL,
                    config_hash TEXT NOT NULL,
                    mode TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS stage_attempts (
                    run_id TEXT NOT NULL,
                    deal_slug TEXT NOT NULL,
                    stage_name TEXT NOT NULL,
                    attempt_no INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    duration_ms INTEGER,
                    error_code TEXT,
                    error_message TEXT,
                    review_required INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (run_id, deal_slug, stage_name, attempt_no),
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS artifacts (
                    run_id TEXT NOT NULL,
                    deal_slug TEXT NOT NULL,
                    artifact_type TEXT NOT NULL,
                    path TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS llm_calls (
                    call_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    deal_slug TEXT NOT NULL,
                    unit_name TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    prompt_version TEXT NOT NULL,
                    request_id TEXT,
                    input_tokens INTEGER,
                    cache_creation_input_tokens INTEGER,
                    cache_read_input_tokens INTEGER,
                    output_tokens INTEGER,
                    cost_usd REAL,
                    latency_ms INTEGER,
                    status TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS review_items (
                    review_id TEXT PRIMARY KEY,
                    deal_slug TEXT NOT NULL,
                    stage_name TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    code TEXT NOT NULL,
                    message TEXT NOT NULL,
                    artifact_path TEXT,
                    status TEXT NOT NULL,
                    resolved_at TEXT
                )
                """
            )

    def _read_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.db_path,
            timeout=30,
            isolation_level=None,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 30000")
        return conn

    def _write_connection(self) -> sqlite3.Connection:
        conn = self._read_connection()
        conn.execute("PRAGMA journal_mode = WAL")
        return conn
