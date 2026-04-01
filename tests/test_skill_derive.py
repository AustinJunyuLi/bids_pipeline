from __future__ import annotations

import json
from pathlib import Path

import pytest

from skill_pipeline import cli
from skill_pipeline.derive import run_derive
from skill_pipeline.paths import build_skill_paths
from tests._v2_validation_fixtures import (
    canonical_observations_payload,
    clone_payload,
    write_v2_validation_fixture,
    write_v2_validation_reports,
)


def _load_derivations(tmp_path: Path, slug: str = "stec") -> dict:
    paths = build_skill_paths(slug, project_root=tmp_path)
    return json.loads(paths.derivations_path.read_text(encoding="utf-8"))


def _load_derive_log(tmp_path: Path, slug: str = "stec") -> dict:
    paths = build_skill_paths(slug, project_root=tmp_path)
    return json.loads(paths.derive_log_path.read_text(encoding="utf-8"))


def _write_derive_fixture(tmp_path: Path, *, observations_payload: dict | None = None) -> None:
    write_v2_validation_fixture(tmp_path, observations_payload=observations_payload)
    write_v2_validation_reports(tmp_path)


def test_derive_requires_passing_v2_validation_artifacts(tmp_path: Path) -> None:
    write_v2_validation_fixture(tmp_path)
    write_v2_validation_reports(tmp_path, check_status="fail")

    with pytest.raises(ValueError, match="check-v2"):
        run_derive("stec", project_root=tmp_path)


def test_derive_informal_phase_and_cash_regime_from_validated_fixture(tmp_path: Path) -> None:
    _write_derive_fixture(tmp_path)

    exit_code = run_derive("stec", project_root=tmp_path)
    derivations = _load_derivations(tmp_path)

    phase = derivations["phases"][0]
    cash_regime = derivations["cash_regimes"][0]
    proposal_row = next(
        row for row in derivations["analyst_rows"] if row["analyst_event_type"] == "proposal"
    )
    round_rows = [
        row["analyst_event_type"]
        for row in derivations["analyst_rows"]
        if row["analyst_event_type"] in {"final_round_inf_ann", "final_round_inf"}
    ]

    assert exit_code == 0
    assert phase["phase_kind"] == "informal"
    assert phase["basis"]["rule_id"] == "ROUND-01"
    assert cash_regime["regime"] == "all_cash"
    assert cash_regime["basis"]["rule_id"] == "CASH-01"
    assert proposal_row["subject_ref"] == "party_bidder_a"
    assert proposal_row["bid_type"] == "Informal"
    assert proposal_row["all_cash"] is True
    assert round_rows == ["final_round_inf_ann", "final_round_inf"]


def test_derive_formal_phase_rows_from_binding_solicitation(tmp_path: Path) -> None:
    observations = clone_payload(canonical_observations_payload())
    solicitation = next(
        observation
        for observation in observations["observations"]
        if observation["observation_id"] == "obs_solicit"
    )
    solicitation["requested_submission"] = "binding_offer"
    solicitation["binding_level"] = "binding"
    _write_derive_fixture(tmp_path, observations_payload=observations)

    run_derive("stec", project_root=tmp_path)
    derivations = _load_derivations(tmp_path)

    phase = derivations["phases"][0]
    round_rows = [
        row["analyst_event_type"]
        for row in derivations["analyst_rows"]
        if row["analyst_event_type"] in {"final_round_ann", "final_round"}
    ]
    assert phase["phase_kind"] == "formal"
    assert phase["basis"]["rule_id"] == "ROUND-02"
    assert round_rows == ["final_round_ann", "final_round"]


def test_derive_falls_back_to_prior_solicitation_when_requested_link_points_forward(
    tmp_path: Path,
) -> None:
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
    proposal["summary"] = "Bidder A submitted a written proposal."
    proposal["mentions_non_binding"] = False
    _write_derive_fixture(tmp_path, observations_payload=observations)

    run_derive("stec", project_root=tmp_path)
    derivations = _load_derivations(tmp_path)
    proposal_row = next(
        row for row in derivations["analyst_rows"] if row["analyst_event_type"] == "proposal"
    )

    assert proposal_row["bid_type"] == "Informal"


def test_derive_uses_proposal_local_formality_cues_without_valid_phase_link(
    tmp_path: Path,
) -> None:
    observations = clone_payload(canonical_observations_payload())
    proposal = next(
        observation
        for observation in observations["observations"]
        if observation["observation_id"] == "obs_proposal"
    )
    proposal["requested_by_observation_id"] = "obs_process"
    proposal["summary"] = "Bidder A submitted a revised proposal."
    proposal["mentions_non_binding"] = True
    proposal["includes_markup"] = True
    _write_derive_fixture(tmp_path, observations_payload=observations)

    run_derive("stec", project_root=tmp_path)
    derivations = _load_derivations(tmp_path)
    proposal_row = next(
        row for row in derivations["analyst_rows"] if row["analyst_event_type"] == "proposal"
    )

    assert proposal_row["bid_type"] == "Formal"


def test_derive_emits_judgments_for_ambiguous_phase_and_missing_advisory_link(tmp_path: Path) -> None:
    observations = clone_payload(canonical_observations_payload())
    solicitation = next(
        observation
        for observation in observations["observations"]
        if observation["observation_id"] == "obs_solicit"
    )
    solicitation["requested_submission"] = "other"
    solicitation["binding_level"] = "other"
    advisor = next(
        party for party in observations["parties"] if party["party_id"] == "party_advisor"
    )
    advisor["advised_party_id"] = None
    _write_derive_fixture(tmp_path, observations_payload=observations)

    run_derive("stec", project_root=tmp_path)
    derivations = _load_derivations(tmp_path)
    judgment_kinds = sorted(judgment["judgment_kind"] for judgment in derivations["judgments"])

    assert "advisory_link" in judgment_kinds
    assert "ambiguous_phase" in judgment_kinds


def test_derive_exit_rules_cover_not_invited_without_duplicate_execution_drop(tmp_path: Path) -> None:
    observations = clone_payload(canonical_observations_payload())
    observations["parties"].append(
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
    solicitation = next(
        observation
        for observation in observations["observations"]
        if observation["observation_id"] == "obs_solicit"
    )
    solicitation["recipient_refs"] = ["party_bidder_a", "party_bidder_b"]
    status = next(
        observation
        for observation in observations["observations"]
        if observation["observation_id"] == "obs_status"
    )
    status["subject_refs"] = ["party_bidder_a"]
    status["related_observation_id"] = "obs_solicit"
    observations["observations"].append(
        {
            "observation_id": "obs_proposal_b",
            "obs_type": "proposal",
            "date": observations["observations"][3]["date"],
            "subject_refs": ["party_bidder_b"],
            "counterparty_refs": ["party_target"],
            "summary": "Bidder B submitted a written indication of interest.",
            "evidence_span_ids": ["span_proposal"],
            "requested_by_observation_id": "obs_solicit",
            "revises_observation_id": None,
            "delivery_mode": "written",
            "terms": {
                "per_share": "20.75",
                "range_low": None,
                "range_high": None,
                "enterprise_value": None,
                "consideration_type": "stock",
            },
            "mentions_non_binding": True,
            "includes_draft_merger_agreement": False,
            "includes_markup": False,
            "other_detail": None,
        }
    )
    observations["observations"].append(
        {
            "observation_id": "obs_executed",
            "obs_type": "outcome",
            "date": {
                **observations["observations"][3]["date"],
                "raw_text": "2026-03-12",
                "normalized_start": "2026-03-12",
                "normalized_end": "2026-03-12",
                "sort_date": "2026-03-12",
            },
            "subject_refs": ["party_target"],
            "counterparty_refs": ["party_bidder_a"],
            "summary": "The Company executed a merger agreement with Bidder A.",
            "evidence_span_ids": ["span_status"],
            "outcome_kind": "executed",
            "related_observation_id": "obs_nda",
            "other_detail": None,
        }
    )
    _write_derive_fixture(tmp_path, observations_payload=observations)

    run_derive("stec", project_root=tmp_path)
    derivations = _load_derivations(tmp_path)
    reasons = sorted(transition["reason_kind"] for transition in derivations["transitions"])

    assert reasons == ["not_invited"]
    drop_rows = [
        row
        for row in derivations["analyst_rows"]
        if row["analyst_event_type"] == "drop" and row["subject_ref"] == "party_bidder_b"
    ]
    assert len(drop_rows) == 1


def test_derive_not_invited_drop_prefers_related_solicitation_deadline(tmp_path: Path) -> None:
    observations = clone_payload(canonical_observations_payload())
    observations["parties"].append(
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
    solicitation = next(
        observation
        for observation in observations["observations"]
        if observation["observation_id"] == "obs_solicit"
    )
    solicitation["recipient_refs"] = ["party_bidder_a", "party_bidder_b"]
    solicitation["due_date"] = {
        **solicitation["due_date"],
        "raw_text": "2026-03-08",
        "normalized_start": "2026-03-08",
        "normalized_end": "2026-03-08",
        "sort_date": "2026-03-08",
    }
    status = next(
        observation
        for observation in observations["observations"]
        if observation["observation_id"] == "obs_status"
    )
    status["date"] = {
        **status["date"],
        "raw_text": "2026-03-09",
        "normalized_start": "2026-03-09",
        "normalized_end": "2026-03-09",
        "sort_date": "2026-03-09",
    }
    status["subject_refs"] = ["party_bidder_a"]
    status["related_observation_id"] = "obs_solicit"
    _write_derive_fixture(tmp_path, observations_payload=observations)

    run_derive("stec", project_root=tmp_path)
    derivations = _load_derivations(tmp_path)
    drop_row = next(
        row
        for row in derivations["analyst_rows"]
        if row["analyst_event_type"] == "drop"
        and row["subject_ref"] == "party_bidder_b"
        and "reason:not_invited" in row["review_flags"]
    )

    assert drop_row["date_recorded"] == "2026-03-08"


def test_derive_lost_to_winner_drop_prefers_last_round_deadline(tmp_path: Path) -> None:
    observations = clone_payload(canonical_observations_payload())
    observations["parties"].append(
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
    solicitation = next(
        observation
        for observation in observations["observations"]
        if observation["observation_id"] == "obs_solicit"
    )
    solicitation["recipient_refs"] = ["party_bidder_a", "party_bidder_b"]
    solicitation["due_date"] = {
        **solicitation["due_date"],
        "raw_text": "2026-03-08",
        "normalized_start": "2026-03-08",
        "normalized_end": "2026-03-08",
        "sort_date": "2026-03-08",
    }
    status = next(
        observation
        for observation in observations["observations"]
        if observation["observation_id"] == "obs_status"
    )
    status["status_kind"] = "expressed_interest"
    status["related_observation_id"] = None
    observations["observations"].append(
        {
            "observation_id": "obs_proposal_b",
            "obs_type": "proposal",
            "date": {
                **observations["observations"][3]["date"],
                "raw_text": "2026-03-07",
                "normalized_start": "2026-03-07",
                "normalized_end": "2026-03-07",
                "sort_date": "2026-03-07",
            },
            "subject_refs": ["party_bidder_b"],
            "counterparty_refs": ["party_target"],
            "summary": "Bidder B submitted a written proposal.",
            "evidence_span_ids": ["span_proposal"],
            "requested_by_observation_id": "obs_solicit",
            "revises_observation_id": None,
            "delivery_mode": "written",
            "terms": {
                "per_share": "20.75",
                "range_low": None,
                "range_high": None,
                "enterprise_value": None,
                "consideration_type": "cash",
            },
            "mentions_non_binding": False,
            "includes_draft_merger_agreement": False,
            "includes_markup": False,
            "other_detail": None,
        }
    )
    observations["observations"].append(
        {
            "observation_id": "obs_executed",
            "obs_type": "outcome",
            "date": {
                **observations["observations"][3]["date"],
                "raw_text": "2026-03-12",
                "normalized_start": "2026-03-12",
                "normalized_end": "2026-03-12",
                "sort_date": "2026-03-12",
            },
            "subject_refs": ["party_target"],
            "counterparty_refs": ["party_bidder_a"],
            "summary": "The Company executed a merger agreement with Bidder A.",
            "evidence_span_ids": ["span_status"],
            "outcome_kind": "executed",
            "related_observation_id": None,
            "other_detail": None,
        }
    )
    _write_derive_fixture(tmp_path, observations_payload=observations)

    run_derive("stec", project_root=tmp_path)
    derivations = _load_derivations(tmp_path)
    drop_row = next(
        row
        for row in derivations["analyst_rows"]
        if row["analyst_event_type"] == "drop"
        and row["subject_ref"] == "party_bidder_b"
        and "reason:lost_to_winner" in row["review_flags"]
    )

    assert drop_row["date_recorded"] == "2026-03-08"


def test_derive_executed_row_prefers_bidder_actor_and_related_merger_agreement_date(
    tmp_path: Path,
) -> None:
    observations = clone_payload(canonical_observations_payload())
    observations["observations"].append(
        {
            "observation_id": "obs_merger_agreement",
            "obs_type": "agreement",
            "date": {
                **observations["observations"][2]["date"],
                "raw_text": "2026-03-12",
                "normalized_start": "2026-03-12",
                "normalized_end": "2026-03-12",
                "sort_date": "2026-03-12",
            },
            "subject_refs": ["party_bidder_a"],
            "counterparty_refs": ["party_target"],
            "summary": "Bidder A signed a merger agreement with the Company.",
            "evidence_span_ids": ["span_nda"],
            "agreement_kind": "merger_agreement",
            "signed": True,
            "grants_diligence_access": None,
            "includes_standstill": None,
            "consideration_type": "cash",
            "supersedes_observation_id": None,
            "other_detail": None,
        }
    )
    observations["observations"].append(
        {
            "observation_id": "obs_executed",
            "obs_type": "outcome",
            "date": None,
            "subject_refs": ["party_target"],
            "counterparty_refs": ["party_bidder_a"],
            "summary": "The Company executed a merger agreement with Bidder A.",
            "evidence_span_ids": ["span_status"],
            "outcome_kind": "executed",
            "related_observation_id": "obs_merger_agreement",
            "other_detail": None,
        }
    )
    _write_derive_fixture(tmp_path, observations_payload=observations)

    run_derive("stec", project_root=tmp_path)
    derivations = _load_derivations(tmp_path)
    executed_row = next(
        row for row in derivations["analyst_rows"] if row["analyst_event_type"] == "executed"
    )

    assert executed_row["subject_ref"] == "party_bidder_a"
    assert executed_row["date_recorded"] == "2026-03-12"


def test_derive_preserves_cohort_rows_as_synthetic_anonymous_without_slot_expansion(
    tmp_path: Path,
) -> None:
    observations = clone_payload(canonical_observations_payload())
    proposal = next(
        observation
        for observation in observations["observations"]
        if observation["observation_id"] == "obs_proposal"
    )
    proposal["subject_refs"] = ["cohort_finalists"]
    _write_derive_fixture(tmp_path, observations_payload=observations)

    run_derive("stec", project_root=tmp_path)
    derivations = _load_derivations(tmp_path)

    proposal_rows = [
        row for row in derivations["analyst_rows"] if row["analyst_event_type"] == "proposal"
    ]
    assert len(proposal_rows) == 1
    assert proposal_rows[0]["origin"] == "synthetic_anonymous"
    assert proposal_rows[0]["subject_ref"] == "cohort_finalists"
    assert proposal_rows[0]["row_count"] == 3


def test_derive_emits_distinct_agreement_family_row_for_superseding_agreement(
    tmp_path: Path,
) -> None:
    observations = clone_payload(canonical_observations_payload())
    observations["observations"].append(
        {
            "observation_id": "obs_nda_amendment",
            "obs_type": "agreement",
            "date": {
                **observations["observations"][2]["date"],
                "raw_text": "2026-03-04",
                "normalized_start": "2026-03-04",
                "normalized_end": "2026-03-04",
                "sort_date": "2026-03-04",
            },
            "subject_refs": ["party_bidder_a"],
            "counterparty_refs": ["party_target"],
            "summary": "Bidder A signed an amendment to the confidentiality agreement.",
            "evidence_span_ids": ["span_nda"],
            "agreement_kind": "amendment",
            "signed": True,
            "grants_diligence_access": True,
            "includes_standstill": False,
            "consideration_type": None,
            "supersedes_observation_id": "obs_nda",
            "other_detail": None,
        }
    )
    _write_derive_fixture(tmp_path, observations_payload=observations)

    run_derive("stec", project_root=tmp_path)
    derivations = _load_derivations(tmp_path)

    amendment_rows = [
        row
        for row in derivations["analyst_rows"]
        if row["analyst_event_type"] == "nda_amendment"
        and row["subject_ref"] == "party_bidder_a"
    ]
    assert any("supersedes:obs_nda" in row["review_flags"] for row in amendment_rows)


def test_derive_emits_ib_terminated_for_advisor_termination_process(tmp_path: Path) -> None:
    observations = clone_payload(canonical_observations_payload())
    observations["observations"].append(
        {
            "observation_id": "obs_advisor_termination",
            "obs_type": "process",
            "date": {
                **observations["observations"][0]["date"],
                "raw_text": "2026-03-15",
                "normalized_start": "2026-03-15",
                "normalized_end": "2026-03-15",
                "sort_date": "2026-03-15",
            },
            "subject_refs": ["party_advisor"],
            "counterparty_refs": ["party_target"],
            "summary": "The Company terminated Advisor Bank.",
            "evidence_span_ids": ["span_process"],
            "process_kind": "advisor_termination",
            "process_scope": "target",
            "other_detail": None,
        }
    )
    _write_derive_fixture(tmp_path, observations_payload=observations)

    run_derive("stec", project_root=tmp_path)
    derivations = _load_derivations(tmp_path)
    process_row = next(
        row
        for row in derivations["analyst_rows"]
        if row["analyst_event_type"] == "ib_terminated"
    )

    assert process_row["subject_ref"] == "party_advisor"


def test_derive_cli_runs_and_writes_artifacts(tmp_path: Path) -> None:
    _write_derive_fixture(tmp_path)

    exit_code = cli.main(["derive", "--deal", "stec", "--project-root", str(tmp_path)])
    log_payload = _load_derive_log(tmp_path)

    assert exit_code == 0
    assert log_payload["validation_gate"]["verify_policy"] == "not_required_until_shared_v2_verify_exists"
