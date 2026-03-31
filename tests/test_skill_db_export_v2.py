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
from skill_pipeline.db_export import run_db_export
from skill_pipeline.db_load import run_db_load
from skill_pipeline.db_load_v2 import run_db_load_v2
from skill_pipeline.derive import run_derive
from skill_pipeline.extract_artifacts_v2 import load_observation_artifacts
from skill_pipeline.legacy_adapter import build_legacy_event_rows, serialize_legacy_deal_events
from skill_pipeline.paths import build_skill_paths
from skill_pipeline.seeds import load_seed_entry
from tests._v2_validation_fixtures import (
    canonical_observations_payload,
    clone_payload,
    write_v2_validation_fixture,
    write_v2_validation_reports,
)
from tests.test_skill_db_load import _span, _write_canonical_fixture


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


def test_legacy_adapter_matches_v1_csv_for_equivalent_rows(tmp_path: Path) -> None:
    v1_tmp = tmp_path / "v1"
    v2_tmp = tmp_path / "v2"

    _write_canonical_fixture(
        v1_tmp,
        slug="imprivata",
        actors=[
            {
                "actor_id": "bidder_a",
                "display_name": "Bidder A",
                "canonical_name": "BIDDER A",
                "aliases": [],
                "role": "bidder",
                "advisor_kind": None,
                "advised_actor_id": None,
                "bidder_kind": "financial",
                "listing_status": "private",
                "geography": "domestic",
                "is_grouped": False,
                "group_size": None,
                "group_label": None,
                "evidence_span_ids": ["span_actor_bidder"],
                "notes": [],
            }
        ],
        events=[
            {
                "event_id": "row_0001",
                "event_type": "target_sale",
                "date": {
                    "raw_text": "2026-03-01",
                    "normalized_start": "2026-03-01",
                    "normalized_end": "2026-03-01",
                    "sort_date": "2026-03-01",
                    "precision": "exact_day",
                    "anchor_event_id": None,
                    "anchor_span_id": None,
                    "resolution_note": None,
                    "is_inferred": False,
                },
                "actor_ids": [],
                "summary": "The Company began exploring a potential sale.",
                "evidence_span_ids": ["span_evt_001"],
                "terms": None,
                "formality_signals": None,
                "whole_company_scope": True,
                "drop_reason_text": None,
                "round_scope": None,
                "invited_actor_ids": [],
                "deadline_date": None,
                "executed_with_actor_id": None,
                "boundary_note": None,
                "nda_signed": None,
                "notes": [],
            },
            {
                "event_id": "row_0002",
                "event_type": "nda",
                "date": {
                    "raw_text": "2026-03-03",
                    "normalized_start": "2026-03-03",
                    "normalized_end": "2026-03-03",
                    "sort_date": "2026-03-03",
                    "precision": "exact_day",
                    "anchor_event_id": None,
                    "anchor_span_id": None,
                    "resolution_note": None,
                    "is_inferred": False,
                },
                "actor_ids": ["bidder_a"],
                "summary": "Bidder A entered into a confidentiality agreement.",
                "evidence_span_ids": ["span_evt_002"],
                "terms": None,
                "formality_signals": None,
                "whole_company_scope": True,
                "drop_reason_text": None,
                "round_scope": None,
                "invited_actor_ids": [],
                "deadline_date": None,
                "executed_with_actor_id": None,
                "boundary_note": None,
                "nda_signed": True,
                "notes": [],
            },
            {
                "event_id": "row_0003",
                "event_type": "proposal",
                "date": {
                    "raw_text": "2026-03-08",
                    "normalized_start": "2026-03-08",
                    "normalized_end": "2026-03-08",
                    "sort_date": "2026-03-08",
                    "precision": "exact_day",
                    "anchor_event_id": None,
                    "anchor_span_id": None,
                    "resolution_note": None,
                    "is_inferred": False,
                },
                "actor_ids": ["bidder_a"],
                "summary": "Bidder A submitted a written indication of interest.",
                "evidence_span_ids": ["span_evt_003"],
                "terms": {
                    "per_share": 21.5,
                    "range_low": None,
                    "range_high": None,
                    "enterprise_value": None,
                    "consideration_type": "cash",
                },
                "formality_signals": None,
                "whole_company_scope": True,
                "drop_reason_text": None,
                "round_scope": None,
                "invited_actor_ids": [],
                "deadline_date": None,
                "executed_with_actor_id": None,
                "boundary_note": None,
                "nda_signed": None,
                "notes": [],
            },
            {
                "event_id": "row_0004",
                "event_type": "final_round_inf_ann",
                "date": {
                    "raw_text": "2026-03-02",
                    "normalized_start": "2026-03-02",
                    "normalized_end": "2026-03-02",
                    "sort_date": "2026-03-02",
                    "precision": "exact_day",
                    "anchor_event_id": None,
                    "anchor_span_id": None,
                    "resolution_note": None,
                    "is_inferred": False,
                },
                "actor_ids": [],
                "summary": "Advisor Bank requested indications of interest.",
                "evidence_span_ids": ["span_evt_004"],
                "terms": None,
                "formality_signals": None,
                "whole_company_scope": True,
                "drop_reason_text": None,
                "round_scope": "informal",
                "invited_actor_ids": [],
                "deadline_date": None,
                "executed_with_actor_id": None,
                "boundary_note": None,
                "nda_signed": None,
                "notes": [],
            },
            {
                "event_id": "row_0005",
                "event_type": "final_round_inf",
                "date": {
                    "raw_text": "2026-03-10",
                    "normalized_start": "2026-03-10",
                    "normalized_end": "2026-03-10",
                    "sort_date": "2026-03-10",
                    "precision": "exact_day",
                    "anchor_event_id": None,
                    "anchor_span_id": None,
                    "resolution_note": None,
                    "is_inferred": False,
                },
                "actor_ids": [],
                "summary": "Advisor Bank requested indications of interest.",
                "evidence_span_ids": ["span_evt_005"],
                "terms": None,
                "formality_signals": None,
                "whole_company_scope": True,
                "drop_reason_text": None,
                "round_scope": "informal",
                "invited_actor_ids": [],
                "deadline_date": None,
                "executed_with_actor_id": None,
                "boundary_note": None,
                "nda_signed": None,
                "notes": [],
            },
        ],
        spans=[
            _span("span_evt_001", "B001", 1, "The Company began exploring a potential sale."),
            _span("span_evt_002", "B002", 2, "Bidder A entered into a confidentiality agreement."),
            _span("span_evt_003", "B003", 3, "Bidder A submitted a written indication of interest."),
            _span("span_evt_004", "B004", 4, "Advisor Bank requested indications of interest."),
            _span("span_evt_005", "B005", 5, "Final indications of interest were due."),
        ],
        deterministic_enrichment={
            "rounds": [],
            "bid_classifications": {
                "row_0003": {
                    "label": "Informal",
                    "rule_applied": 1.0,
                    "basis": "Informal indication of interest",
                },
                "row_0004": {
                    "label": "Informal",
                    "rule_applied": 1.0,
                    "basis": "Informal round announcement",
                },
                "row_0005": {
                    "label": "Informal",
                    "rule_applied": 1.0,
                    "basis": "Informal round deadline",
                },
            },
            "cycles": [
                {
                    "cycle_id": "cycle_1",
                    "start_event_id": "row_0001",
                    "end_event_id": "row_0005",
                    "boundary_basis": "Single synthetic cycle",
                }
            ],
            "formal_boundary": {"cycle_1": {"event_id": None, "basis": "No formal phase"}},
            "dropout_classifications": {},
            "all_cash_overrides": {
                "row_0003": True,
                "row_0004": True,
                "row_0005": True,
            },
        },
    )
    run_db_load("imprivata", project_root=v1_tmp)
    run_db_export("imprivata", project_root=v1_tmp)
    expected_text = (build_skill_paths("imprivata", project_root=v1_tmp).deal_events_path).read_text(
        encoding="utf-8"
    )

    v2_paths = _prepare_v2_export_fixture(v2_tmp, slug="imprivata")
    (v2_tmp / "data" / "seeds.csv").write_text(
        (
            "deal_slug,target_name,acquirer,date_announced,primary_url,is_reference\n"
            "imprivata,IMPRIVATA INC,THOMA BRAVO LLC,2016-07-13,https://example.com/imprivata,false\n"
        ),
        encoding="utf-8",
    )
    artifacts = load_observation_artifacts(v2_paths, mode="canonical")
    seed = load_seed_entry("imprivata", seeds_path=v2_paths.seeds_path)
    legacy_rows = build_legacy_event_rows(
        artifacts.observations.parties,
        artifacts.observations.cohorts,
        artifacts.derivations.analyst_rows,
    )
    actual_text = serialize_legacy_deal_events(seed, legacy_rows)

    assert actual_text == expected_text


def test_db_export_v2_cli_runs(tmp_path: Path) -> None:
    paths = _prepare_v2_export_fixture(tmp_path)

    exit_code = cli.main(["db-export-v2", "--deal", "stec", "--project-root", str(tmp_path)])
    _, analyst_rows = _read_dict_rows(paths.analyst_rows_path)

    assert exit_code == 0
    assert len(analyst_rows) == 5
