from __future__ import annotations

import json
from pathlib import Path

from skill_pipeline.gates_v2 import run_gates_v2
from skill_pipeline.paths import build_skill_paths
from tests._v2_validation_fixtures import (
    canonical_observations_payload,
    clone_payload,
    write_v2_validation_fixture,
)


def _report(tmp_path: Path, slug: str = "stec") -> dict:
    paths = build_skill_paths(slug, project_root=tmp_path)
    return json.loads(paths.gates_v2_report_path.read_text(encoding="utf-8"))


def test_gates_v2_passes_on_valid_fixture(tmp_path: Path) -> None:
    write_v2_validation_fixture(tmp_path)

    exit_code = run_gates_v2("stec", project_root=tmp_path)
    report = _report(tmp_path)

    assert exit_code == 0
    assert report["summary"]["status"] == "pass"
    assert report["findings"] == []


def test_gates_v2_blocks_proposal_revision_cycles(tmp_path: Path) -> None:
    observations = clone_payload(canonical_observations_payload())
    observations["observations"].append(
        {
            "observation_id": "obs_proposal_prev",
            "obs_type": "proposal",
            "date": observations["observations"][3]["date"],
            "subject_refs": ["party_bidder_a"],
            "counterparty_refs": ["party_target"],
            "summary": "Bidder A submitted an earlier proposal.",
            "evidence_span_ids": ["span_proposal"],
            "requested_by_observation_id": "obs_solicit",
            "revises_observation_id": "obs_proposal",
            "delivery_mode": "written",
            "terms": {
                "per_share": "20.50",
                "range_low": None,
                "range_high": None,
                "enterprise_value": None,
                "consideration_type": "cash",
            },
            "mentions_non_binding": True,
            "includes_draft_merger_agreement": False,
            "includes_markup": False,
            "other_detail": None,
        }
    )
    proposal = next(
        observation
        for observation in observations["observations"]
        if observation["observation_id"] == "obs_proposal"
    )
    proposal["revises_observation_id"] = "obs_proposal_prev"
    write_v2_validation_fixture(tmp_path, observations_payload=observations)

    exit_code = run_gates_v2("stec", project_root=tmp_path)
    report = _report(tmp_path)

    finding = next(
        finding
        for finding in report["findings"]
        if finding["gate_id"] == "proposal_revision_cycle"
    )
    assert exit_code == 1
    assert sorted(finding["observation_ids"]) == ["obs_proposal", "obs_proposal_prev"]


def test_gates_v2_blocks_child_cohort_counts_above_parent(tmp_path: Path) -> None:
    observations = clone_payload(canonical_observations_payload())
    observations["cohorts"] = [
        {
            "cohort_id": "cohort_parent",
            "label": "All bidders",
            "parent_cohort_id": None,
            "exact_count": 2,
            "known_member_party_ids": ["party_bidder_a"],
            "unknown_member_count": 1,
            "membership_basis": "contacted parties",
            "created_by_observation_id": "obs_solicit",
            "evidence_span_ids": ["span_cohort"],
        },
        {
            "cohort_id": "cohort_finalists",
            "label": "Finalists",
            "parent_cohort_id": "cohort_parent",
            "exact_count": 3,
            "known_member_party_ids": ["party_bidder_a"],
            "unknown_member_count": 2,
            "membership_basis": "advanced to the final round",
            "created_by_observation_id": "obs_solicit",
            "evidence_span_ids": ["span_cohort"],
        },
    ]
    write_v2_validation_fixture(tmp_path, observations_payload=observations)

    exit_code = run_gates_v2("stec", project_root=tmp_path)
    report = _report(tmp_path)

    finding = next(
        finding
        for finding in report["findings"]
        if finding["gate_id"] == "cohort_child_count_exceeds_parent"
    )
    assert exit_code == 1
    assert finding["cohort_ids"] == ["cohort_parent", "cohort_finalists"]


def test_gates_v2_blocks_due_dates_before_solicitations(tmp_path: Path) -> None:
    observations = clone_payload(canonical_observations_payload())
    solicitation = next(
        observation
        for observation in observations["observations"]
        if observation["observation_id"] == "obs_solicit"
    )
    solicitation["due_date"] = solicitation["date"] | {"sort_date": "2026-03-01", "normalized_start": "2026-03-01", "normalized_end": "2026-03-01", "raw_text": "2026-03-01"}
    write_v2_validation_fixture(tmp_path, observations_payload=observations)

    exit_code = run_gates_v2("stec", project_root=tmp_path)
    report = _report(tmp_path)

    finding = next(
        finding
        for finding in report["findings"]
        if finding["gate_id"] == "solicitation_deadline_precedes_request"
    )
    assert exit_code == 1
    assert finding["observation_ids"] == ["obs_solicit"]


def test_gates_v2_blocks_proposals_linking_to_non_solicitations(tmp_path: Path) -> None:
    observations = clone_payload(canonical_observations_payload())
    proposal = next(
        observation
        for observation in observations["observations"]
        if observation["observation_id"] == "obs_proposal"
    )
    proposal["requested_by_observation_id"] = "obs_process"
    write_v2_validation_fixture(tmp_path, observations_payload=observations)

    exit_code = run_gates_v2("stec", project_root=tmp_path)
    report = _report(tmp_path)

    finding = next(
        finding
        for finding in report["findings"]
        if finding["gate_id"] == "proposal_request_not_solicitation"
    )
    assert exit_code == 1
    assert finding["observation_ids"] == ["obs_proposal", "obs_process"]


def test_gates_v2_blocks_proposals_linking_forward_in_time(tmp_path: Path) -> None:
    observations = clone_payload(canonical_observations_payload())
    observations["observations"].append(
        {
            "observation_id": "obs_solicit_final",
            "obs_type": "solicitation",
            "date": {
                **observations["observations"][1]["date"],
                "raw_text": "2026-03-12",
                "normalized_start": "2026-03-12",
                "normalized_end": "2026-03-12",
                "sort_date": "2026-03-12",
            },
            "subject_refs": ["party_advisor"],
            "counterparty_refs": ["party_target"],
            "summary": "Advisor Bank requested binding offers.",
            "evidence_span_ids": ["span_solicit"],
            "requested_submission": "binding_offer",
            "binding_level": "binding",
            "due_date": {
                **observations["observations"][1]["due_date"],
                "raw_text": "2026-03-14",
                "normalized_start": "2026-03-14",
                "normalized_end": "2026-03-14",
                "sort_date": "2026-03-14",
            },
            "recipient_refs": ["cohort_finalists"],
            "attachments": ["draft merger agreement"],
            "other_detail": None,
        }
    )
    proposal = next(
        observation
        for observation in observations["observations"]
        if observation["observation_id"] == "obs_proposal"
    )
    proposal["requested_by_observation_id"] = "obs_solicit_final"
    write_v2_validation_fixture(tmp_path, observations_payload=observations)

    exit_code = run_gates_v2("stec", project_root=tmp_path)
    report = _report(tmp_path)

    finding = next(
        finding
        for finding in report["findings"]
        if finding["gate_id"] == "proposal_request_points_forward"
    )
    assert exit_code == 1
    assert finding["observation_ids"] == ["obs_proposal", "obs_solicit_final"]


def test_gates_v2_warns_on_named_solicitation_without_recipient_refs(tmp_path: Path) -> None:
    observations = clone_payload(canonical_observations_payload())
    solicitation = next(
        observation
        for observation in observations["observations"]
        if observation["observation_id"] == "obs_solicit"
    )
    solicitation["recipient_refs"] = []
    solicitation["summary"] = "Advisor Bank requested indications of interest from Bidder A."
    write_v2_validation_fixture(tmp_path, observations_payload=observations)

    exit_code = run_gates_v2("stec", project_root=tmp_path)
    report = _report(tmp_path)

    finding = next(
        finding
        for finding in report["findings"]
        if finding["gate_id"] == "solicitation_missing_named_recipients"
    )
    assert exit_code == 0
    assert finding["observation_ids"] == ["obs_solicit"]
    assert finding["party_ids"] == ["party_bidder_a"]


def test_gates_v2_blocks_under_specified_executed_outcomes(tmp_path: Path) -> None:
    observations = clone_payload(canonical_observations_payload())
    observations["observations"].append(
        {
            "observation_id": "obs_executed",
            "obs_type": "outcome",
            "date": None,
            "subject_refs": ["party_target"],
            "counterparty_refs": [],
            "summary": "The merger agreement was executed.",
            "evidence_span_ids": ["span_status"],
            "outcome_kind": "executed",
            "related_observation_id": None,
            "other_detail": None,
        }
    )
    write_v2_validation_fixture(tmp_path, observations_payload=observations)

    exit_code = run_gates_v2("stec", project_root=tmp_path)
    report = _report(tmp_path)

    gate_ids = {finding["gate_id"] for finding in report["findings"]}
    assert exit_code == 1
    assert "substantive_outcome_missing_bidder_actor" in gate_ids
    assert "substantive_outcome_missing_date" in gate_ids


def test_gates_v2_warns_on_proxy_dates_for_export_surface(tmp_path: Path) -> None:
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
    write_v2_validation_fixture(tmp_path, observations_payload=observations)

    exit_code = run_gates_v2("stec", project_root=tmp_path)
    report = _report(tmp_path)

    finding = next(
        finding
        for finding in report["findings"]
        if finding["gate_id"] == "proxy_date_export_warning"
    )
    assert exit_code == 0
    assert finding["observation_ids"] == ["obs_proposal"]


def test_gates_v2_warns_on_lossy_agreement_kind_surface(tmp_path: Path) -> None:
    observations = clone_payload(canonical_observations_payload())
    agreement = next(
        observation
        for observation in observations["observations"]
        if observation["observation_id"] == "obs_nda"
    )
    agreement["agreement_kind"] = "other"
    agreement["summary"] = "Bidder A signed a 30-day exclusivity agreement."
    write_v2_validation_fixture(tmp_path, observations_payload=observations)

    exit_code = run_gates_v2("stec", project_root=tmp_path)
    report = _report(tmp_path)

    finding = next(
        finding
        for finding in report["findings"]
        if finding["gate_id"] == "agreement_kind_surface_warning"
    )
    assert exit_code == 0
    assert finding["observation_ids"] == ["obs_nda"]
