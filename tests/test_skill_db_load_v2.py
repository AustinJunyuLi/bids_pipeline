from __future__ import annotations

import json
from pathlib import Path

from skill_pipeline import cli
from skill_pipeline.db_load_v2 import run_db_load_v2
from skill_pipeline.db_schema import open_pipeline_db
from skill_pipeline.derive import run_derive
from tests._v2_validation_fixtures import (
    canonical_observations_payload,
    clone_payload,
    write_v2_validation_fixture,
    write_v2_validation_reports,
)


def _write_v2_db_fixture(
    tmp_path: Path,
    *,
    slug: str = "stec",
    observations_payload: dict | None = None,
    coverage_findings: list[dict] | None = None,
) -> None:
    write_v2_validation_fixture(
        tmp_path,
        slug=slug,
        observations_payload=observations_payload,
    )
    write_v2_validation_reports(
        tmp_path,
        slug=slug,
        coverage_findings=coverage_findings,
    )
    run_derive(slug, project_root=tmp_path)


def test_run_db_load_v2_loads_additive_v2_tables(tmp_path: Path) -> None:
    _write_v2_db_fixture(
        tmp_path,
        coverage_findings=[
            {
                "cue_family": "sale_process",
                "status": "observed",
                "severity": "warning",
                "repairability": None,
                "description": "Sale process cue grounded by process observation.",
                "supporting_event_ids": [],
                "supporting_actor_ids": [],
                "supporting_span_ids": ["span_process"],
                "block_ids": [],
                "evidence_ids": [],
                "matched_terms": [],
                "confidence": "high",
                "suggested_event_types": [],
                "supporting_observation_ids": ["obs_process"],
                "supporting_party_ids": ["party_target"],
                "supporting_cohort_ids": [],
                "reason_code": None,
                "note": None,
            }
        ],
    )

    exit_code = run_db_load_v2("stec", project_root=tmp_path)

    con = open_pipeline_db(tmp_path / "data" / "pipeline.duckdb", read_only=True)
    try:
        counts = {
            table_name: con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            for table_name in (
                "v2_parties",
                "v2_cohorts",
                "v2_observations",
                "v2_derivations",
                "v2_coverage_checks",
            )
        }
        type_fields = con.execute(
            """
            SELECT type_fields
            FROM v2_observations
            WHERE deal_slug = ? AND observation_id = ?
            """,
            ["stec", "obs_solicit"],
        ).fetchone()[0]
        record_types = {
            row[0]
            for row in con.execute(
                "SELECT DISTINCT record_type FROM v2_derivations WHERE deal_slug = ?",
                ["stec"],
            ).fetchall()
        }
    finally:
        con.close()

    assert exit_code == 0
    assert counts == {
        "v2_parties": 3,
        "v2_cohorts": 1,
        "v2_observations": 5,
        "v2_derivations": 7,
        "v2_coverage_checks": 1,
    }
    assert json.loads(type_fields)["requested_submission"] == "ioi"
    assert record_types == {"analyst_row", "cash_regime", "phase"}


def test_run_db_load_v2_replaces_existing_rows_for_same_deal(tmp_path: Path) -> None:
    _write_v2_db_fixture(tmp_path)
    run_db_load_v2("stec", project_root=tmp_path)

    updated_payload = clone_payload(canonical_observations_payload())
    updated_payload["parties"].append(
        {
            "party_id": "party_bidder_b",
            "display_name": "Bidder B",
            "canonical_name": "BIDDER B",
            "aliases": [],
            "role": "bidder",
            "bidder_kind": "strategic",
            "advisor_kind": None,
            "advised_party_id": None,
            "listing_status": "public",
            "geography": "domestic",
            "evidence_span_ids": ["span_bidder"],
        }
    )
    _write_v2_db_fixture(tmp_path, observations_payload=updated_payload)

    run_db_load_v2("stec", project_root=tmp_path)

    con = open_pipeline_db(tmp_path / "data" / "pipeline.duckdb", read_only=True)
    try:
        party_count = con.execute(
            "SELECT COUNT(*) FROM v2_parties WHERE deal_slug = ?",
            ["stec"],
        ).fetchone()[0]
    finally:
        con.close()

    assert party_count == 4


def test_db_load_v2_cli_runs(tmp_path: Path) -> None:
    _write_v2_db_fixture(tmp_path)

    exit_code = cli.main(["db-load-v2", "--deal", "stec", "--project-root", str(tmp_path)])

    con = open_pipeline_db(tmp_path / "data" / "pipeline.duckdb", read_only=True)
    try:
        observation_count = con.execute(
            "SELECT COUNT(*) FROM v2_observations WHERE deal_slug = ?",
            ["stec"],
        ).fetchone()[0]
    finally:
        con.close()

    assert exit_code == 0
    assert observation_count == 5
