from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import TypeAdapter, ValidationError

from skill_pipeline.models_v2 import (
    AgreementObservation,
    AnalystRowRecord,
    CashRegimeRecord,
    CohortRecord,
    DerivationBasis,
    JudgmentRecord,
    LifecycleTransitionRecord,
    Observation,
    ObservationArtifactV2,
    OutcomeObservation,
    PartyRecord,
    ProcessObservation,
    ProcessPhaseRecord,
    ProposalObservation,
    SolicitationObservation,
    StatusObservation,
)


def _resolved_date_payload(day: str = "2026-03-31") -> dict:
    return {
        "raw_text": day,
        "normalized_start": day,
        "normalized_end": day,
        "sort_date": day,
        "precision": "exact_day",
        "anchor_event_id": None,
        "anchor_span_id": None,
        "resolution_note": None,
        "is_inferred": False,
    }


def _basis() -> DerivationBasis:
    return DerivationBasis(
        rule_id="ROUND-01",
        source_observation_ids=["obs_001"],
        source_span_ids=["span_001"],
        confidence="high",
        explanation="Synthetic test basis",
    )


def test_party_record_round_trip_preserves_core_fields() -> None:
    record = PartyRecord(
        party_id="party_bidder_a",
        display_name="Bidder A",
        canonical_name="BIDDER A",
        aliases=["Company A"],
        role="bidder",
        bidder_kind="financial",
        advisor_kind=None,
        advised_party_id=None,
        evidence_span_ids=["span_001"],
    )

    payload = record.model_dump(mode="json")
    restored = PartyRecord.model_validate(payload)

    assert restored == record


def test_party_record_round_trip_preserves_optional_linkage_fields() -> None:
    record = PartyRecord(
        party_id="party_advisor_a",
        display_name="Advisor A",
        canonical_name="ADVISOR A",
        aliases=["Advisor Alpha"],
        role="advisor",
        bidder_kind="unknown",
        advisor_kind="financial",
        advised_party_id="party_target",
        evidence_span_ids=["span_010"],
    )

    payload = record.model_dump(mode="json")
    restored = PartyRecord.model_validate(payload)

    assert restored.role == "advisor"
    assert restored.bidder_kind == "unknown"
    assert restored.advisor_kind == "financial"
    assert restored.advised_party_id == "party_target"
    assert restored.evidence_span_ids == ["span_010"]


def test_cohort_record_enforces_unknown_member_count_invariant() -> None:
    with pytest.raises(
        ValidationError,
        match="unknown_member_count must equal exact_count - len\\(known_member_party_ids\\)",
    ):
        CohortRecord(
            cohort_id="cohort_001",
            label="Unnamed bidders",
            exact_count=5,
            known_member_party_ids=["party_a", "party_b"],
            unknown_member_count=1,
            membership_basis="signed NDA",
            created_by_observation_id="obs_001",
        )


def test_cohort_record_supports_nested_parent_lineage() -> None:
    cohort = CohortRecord(
        cohort_id="cohort_finalists",
        label="Final-round bidders",
        parent_cohort_id="cohort_nda_signers",
        exact_count=3,
        known_member_party_ids=["party_bidder_a"],
        unknown_member_count=2,
        membership_basis="selected to advance to the final round",
        created_by_observation_id="obs_status",
        evidence_span_ids=["span_011"],
    )

    payload = cohort.model_dump(mode="json")
    restored = CohortRecord.model_validate(payload)

    assert restored.parent_cohort_id == "cohort_nda_signers"
    assert restored.known_member_party_ids == ["party_bidder_a"]
    assert restored.unknown_member_count == 2


@pytest.mark.parametrize(
    ("payload", "expected_type"),
    [
        (
            {
                "observation_id": "obs_process",
                "obs_type": "process",
                "date": _resolved_date_payload(),
                "summary": "Target launched a sale process.",
                "subject_refs": ["party_target"],
                "evidence_span_ids": ["span_001"],
                "process_kind": "sale_launch",
            },
            ProcessObservation,
        ),
        (
            {
                "observation_id": "obs_agreement",
                "obs_type": "agreement",
                "date": _resolved_date_payload(),
                "summary": "Bidder A signed an NDA.",
                "subject_refs": ["party_bidder_a"],
                "counterparty_refs": ["party_target"],
                "evidence_span_ids": ["span_002"],
                "agreement_kind": "nda",
                "signed": True,
                "supersedes_observation_id": "obs_prev_nda",
            },
            AgreementObservation,
        ),
        (
            {
                "observation_id": "obs_solicit",
                "obs_type": "solicitation",
                "date": _resolved_date_payload(),
                "summary": "Advisor sent process letters requesting IOIs.",
                "subject_refs": ["party_advisor"],
                "evidence_span_ids": ["span_003"],
                "requested_submission": "ioi",
                "binding_level": "non_binding",
                "due_date": _resolved_date_payload("2026-04-07"),
                "recipient_refs": ["party_bidder_a", "cohort_001"],
            },
            SolicitationObservation,
        ),
        (
            {
                "observation_id": "obs_proposal",
                "obs_type": "proposal",
                "date": _resolved_date_payload(),
                "summary": "Bidder A submitted a revised proposal.",
                "subject_refs": ["party_bidder_a"],
                "evidence_span_ids": ["span_004"],
                "requested_by_observation_id": "obs_solicit",
                "revises_observation_id": "obs_old_proposal",
                "delivery_mode": "written",
                "terms": {
                    "per_share": "21.50",
                    "range_low": None,
                    "range_high": None,
                    "enterprise_value": None,
                    "consideration_type": "cash",
                },
                "mentions_non_binding": True,
                "includes_markup": True,
            },
            ProposalObservation,
        ),
        (
            {
                "observation_id": "obs_status",
                "obs_type": "status",
                "date": _resolved_date_payload(),
                "summary": "Bidder A said it could not improve.",
                "subject_refs": ["party_bidder_a"],
                "evidence_span_ids": ["span_005"],
                "status_kind": "cannot_improve",
                "related_observation_id": "obs_proposal",
            },
            StatusObservation,
        ),
        (
            {
                "observation_id": "obs_outcome",
                "obs_type": "outcome",
                "date": _resolved_date_payload(),
                "summary": "Target and Bidder A executed the merger agreement.",
                "subject_refs": ["party_target"],
                "counterparty_refs": ["party_bidder_a"],
                "evidence_span_ids": ["span_006"],
                "outcome_kind": "executed",
                "related_observation_id": "obs_agreement",
            },
            OutcomeObservation,
        ),
    ],
)
def test_observation_union_dispatches_all_subtypes(payload: dict, expected_type: type) -> None:
    adapter = TypeAdapter(Observation)
    observation = adapter.validate_python(payload)

    assert isinstance(observation, expected_type)
    assert observation.model_dump(mode="json")["obs_type"] == payload["obs_type"]


def test_observation_artifact_round_trip_preserves_cross_observation_references() -> None:
    artifact = ObservationArtifactV2(
        parties=[
            PartyRecord(
                party_id="party_bidder_a",
                display_name="Bidder A",
                role="bidder",
                bidder_kind="financial",
            )
        ],
        cohorts=[
            CohortRecord(
                cohort_id="cohort_001",
                label="Unnamed bidders",
                exact_count=3,
                known_member_party_ids=["party_bidder_a"],
                unknown_member_count=2,
                membership_basis="submitted IOI",
                created_by_observation_id="obs_solicit",
            )
        ],
        observations=[
            SolicitationObservation(
                observation_id="obs_solicit",
                obs_type="solicitation",
                date=None,
                summary="Advisor requested IOIs.",
                requested_submission="ioi",
                recipient_refs=["cohort_001"],
            ),
            ProposalObservation(
                observation_id="obs_proposal",
                obs_type="proposal",
                date=None,
                summary="Bidder A submitted a proposal.",
                subject_refs=["party_bidder_a"],
                requested_by_observation_id="obs_solicit",
                revises_observation_id="obs_old",
            ),
            AgreementObservation(
                observation_id="obs_agreement",
                obs_type="agreement",
                date=None,
                summary="Bidder A signed an amended NDA.",
                agreement_kind="amendment",
                supersedes_observation_id="obs_old_nda",
            ),
            StatusObservation(
                observation_id="obs_status",
                obs_type="status",
                date=None,
                summary="Bidder A was selected to advance.",
                status_kind="selected_to_advance",
                related_observation_id="obs_proposal",
            ),
        ],
    )

    payload = artifact.model_dump(mode="json")
    restored = ObservationArtifactV2.model_validate(payload)

    proposal = next(obs for obs in restored.observations if obs.observation_id == "obs_proposal")
    agreement = next(obs for obs in restored.observations if obs.observation_id == "obs_agreement")
    status = next(obs for obs in restored.observations if obs.observation_id == "obs_status")

    assert isinstance(proposal, ProposalObservation)
    assert proposal.requested_by_observation_id == "obs_solicit"
    assert proposal.revises_observation_id == "obs_old"
    assert isinstance(agreement, AgreementObservation)
    assert agreement.supersedes_observation_id == "obs_old_nda"
    assert isinstance(status, StatusObservation)
    assert status.related_observation_id == "obs_proposal"


def test_derived_record_types_require_derivation_basis() -> None:
    phase = ProcessPhaseRecord(
        phase_id="phase_001",
        phase_kind="formal",
        start_observation_id="obs_001",
        basis=_basis(),
    )
    transition = LifecycleTransitionRecord(
        transition_id="transition_001",
        subject_ref="party_bidder_a",
        from_state="active",
        to_state="submitted",
        reason_kind="literal",
        basis=_basis(),
    )
    cash_regime = CashRegimeRecord(
        cash_regime_id="cash_001",
        scope_kind="cycle",
        scope_ref="cycle_001",
        regime="all_cash",
        basis=_basis(),
    )
    judgment = JudgmentRecord(
        judgment_id="judgment_001",
        judgment_kind="ambiguous_phase",
        basis=_basis(),
    )
    analyst_row = AnalystRowRecord(
        row_id="row_001",
        origin="derived",
        analyst_event_type="proposal",
        bidder_name="Bidder A",
        bid_type="Formal",
        value=Decimal("21.50"),
        all_cash=True,
        basis=_basis(),
    )

    assert phase.basis.rule_id == "ROUND-01"
    assert transition.basis.source_observation_ids == ["obs_001"]
    assert cash_regime.basis.confidence == "high"
    assert judgment.human_review_required is True
    assert analyst_row.model_dump(mode="json")["basis"]["rule_id"] == "ROUND-01"
