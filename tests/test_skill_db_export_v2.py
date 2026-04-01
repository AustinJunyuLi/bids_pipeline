from __future__ import annotations

import csv
from pathlib import Path

from skill_pipeline import cli
from skill_pipeline.db_export_v2 import (
    ANALYST_FIELDNAMES,
    BENCHMARK_FIELDNAMES,
    LITERAL_FIELDNAMES,
    run_db_export_v2,
)
from skill_pipeline.db_load_v2 import run_db_load_v2
from skill_pipeline.derive import run_derive
from skill_pipeline.extract_artifacts_v2 import load_observation_artifacts
from skill_pipeline.paths import build_skill_paths
from tests._v2_validation_fixtures import (
    canonical_observations_payload,
    clone_payload,
    write_v2_validation_fixture,
    write_v2_validation_reports,
)


def _prepare_v2_export_fixture(
    tmp_path: Path,
    *,
    slug: str = "stec",
    observations_payload: dict | None = None,
) -> Path:
    write_v2_validation_fixture(
        tmp_path,
        slug=slug,
        observations_payload=observations_payload,
    )
    write_v2_validation_reports(tmp_path, slug=slug)
    run_derive(slug, project_root=tmp_path)
    run_db_load_v2(slug, project_root=tmp_path)
    return build_skill_paths(slug, project_root=tmp_path)


def _read_dict_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def test_run_db_export_v2_writes_triple_csv_surface(tmp_path: Path) -> None:
    paths = _prepare_v2_export_fixture(tmp_path)

    exit_code = run_db_export_v2("stec", project_root=tmp_path)
    literal_fieldnames, literal_rows = _read_dict_rows(paths.literal_observations_path)
    analyst_fieldnames, analyst_rows = _read_dict_rows(paths.analyst_rows_path)
    benchmark_fieldnames, benchmark_rows = _read_dict_rows(paths.benchmark_rows_expanded_path)

    assert exit_code == 0
    assert literal_fieldnames == LITERAL_FIELDNAMES
    assert analyst_fieldnames == ANALYST_FIELDNAMES
    assert benchmark_fieldnames == BENCHMARK_FIELDNAMES
    assert len(literal_rows) == 5
    assert len(analyst_rows) == 5
    assert len(benchmark_rows) == 9
    assert literal_rows[1]["observation_id"] == "obs_solicit"
    assert "requested_submission" in literal_rows[1]["type_fields"]


def test_run_db_export_v2_expands_anonymous_rows_only_in_benchmark_surface(tmp_path: Path) -> None:
    observations = clone_payload(canonical_observations_payload())
    proposal = next(
        observation
        for observation in observations["observations"]
        if observation["observation_id"] == "obs_proposal"
    )
    proposal["subject_refs"] = ["cohort_finalists"]
    paths = _prepare_v2_export_fixture(tmp_path, observations_payload=observations)

    run_db_export_v2("stec", project_root=tmp_path)
    _, analyst_rows = _read_dict_rows(paths.analyst_rows_path)
    _, benchmark_rows = _read_dict_rows(paths.benchmark_rows_expanded_path)

    analyst_proposal_rows = [
        row
        for row in analyst_rows
        if row["analyst_event_type"] == "proposal" and row["subject_ref"] == "cohort_finalists"
    ]
    expanded_rows = [
        row
        for row in benchmark_rows
        if row["analyst_event_type"] == "proposal"
        and row["expanded_from_row_id"] == analyst_proposal_rows[0]["row_id"]
    ]

    assert len(analyst_proposal_rows) == 1
    assert analyst_proposal_rows[0]["row_count"] == "3"
    assert len(expanded_rows) == 3
    assert [row["expansion_slot"] for row in expanded_rows] == [
        "anon_slot_001",
        "anon_slot_002",
        "anon_slot_003",
    ]
    assert all(row["row_count"] == "1" for row in expanded_rows)


def test_run_db_export_v2_preserves_enterprise_value_and_proxy_date_fields(tmp_path: Path) -> None:
    observations = clone_payload(canonical_observations_payload())
    proposal = next(
        observation
        for observation in observations["observations"]
        if observation["observation_id"] == "obs_proposal"
    )
    proposal["date"] = {
        **proposal["date"],
        "raw_text": "late July 2026",
        "normalized_start": "2026-07-01",
        "normalized_end": "2026-07-31",
        "sort_date": "2026-07-25",
        "precision": "month_late",
        "is_inferred": True,
    }
    proposal["terms"] = {
        "per_share": None,
        "range_low": None,
        "range_high": None,
        "enterprise_value": "2600000000",
        "consideration_type": "cash",
    }
    paths = _prepare_v2_export_fixture(tmp_path, observations_payload=observations)

    run_db_export_v2("stec", project_root=tmp_path)
    _, analyst_rows = _read_dict_rows(paths.analyst_rows_path)
    proposal_row = next(
        row for row in analyst_rows if row["analyst_event_type"] == "proposal"
    )

    assert proposal_row["enterprise_value"] == "2600000000"
    assert proposal_row["value"] == "NA"
    assert proposal_row["range_low"] == "NA"
    assert proposal_row["range_high"] == "NA"
    assert proposal_row["date_precision"] == "month_late"
    assert proposal_row["date_recorded"] == "NA"
    assert proposal_row["date_sort_proxy"] == "2026-07-25 00:00:00"


def test_db_export_v2_cli_runs(tmp_path: Path) -> None:
    paths = _prepare_v2_export_fixture(tmp_path)

    exit_code = cli.main(["db-export-v2", "--deal", "stec", "--project-root", str(tmp_path)])
    _, analyst_rows = _read_dict_rows(paths.analyst_rows_path)

    assert exit_code == 0
    assert len(analyst_rows) == 5
