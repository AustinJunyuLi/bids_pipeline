from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field, model_validator

from skill_pipeline.models import (
    CheckReportSummary,
    CoverageCheckRecord,
    CoverageSummary,
    GateReportSummary,
    MoneyTerms,
    ResolvedDate,
    SkillExclusionRecord,
    SkillModel,
)


class PartyRecord(SkillModel):
    party_id: str
    display_name: str
    canonical_name: str | None = None
    aliases: list[str] = Field(default_factory=list)
    role: Literal["bidder", "advisor", "activist", "target_board", "other"]
    bidder_kind: Literal["strategic", "financial", "unknown"] | None = None
    advisor_kind: Literal["financial", "legal", "other"] | None = None
    advised_party_id: str | None = None
    listing_status: Literal["public", "private"] | None = None
    geography: Literal["domestic", "non_us"] | None = None
    evidence_span_ids: list[str] = Field(default_factory=list)


class CohortRecord(SkillModel):
    cohort_id: str
    label: str
    parent_cohort_id: str | None = None
    exact_count: int
    known_member_party_ids: list[str] = Field(default_factory=list)
    unknown_member_count: int
    membership_basis: str
    created_by_observation_id: str
    evidence_span_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_counts(self) -> "CohortRecord":
        expected_unknown = self.exact_count - len(self.known_member_party_ids)
        if self.exact_count < 0:
            raise ValueError("exact_count must be non-negative")
        if self.unknown_member_count != expected_unknown:
            raise ValueError(
                "unknown_member_count must equal exact_count - len(known_member_party_ids)"
            )
        if self.unknown_member_count < 0:
            raise ValueError("unknown_member_count must be non-negative")
        return self


class ObservationBase(SkillModel):
    observation_id: str
    obs_type: str
    date: ResolvedDate | None = None
    subject_refs: list[str] = Field(default_factory=list)
    counterparty_refs: list[str] = Field(default_factory=list)
    summary: str
    evidence_span_ids: list[str] = Field(default_factory=list)


class ProcessObservation(ObservationBase):
    obs_type: Literal["process"]
    process_kind: Literal[
        "sale_launch",
        "public_announcement",
        "advisor_retention",
        "advisor_termination",
        "press_release",
        "other",
    ]
    process_scope: Literal["target", "bidder", "activist", "other"] | None = None
    other_detail: str | None = None


class AgreementObservation(ObservationBase):
    obs_type: Literal["agreement"]
    agreement_kind: Literal[
        "nda",
        "amendment",
        "standstill",
        "exclusivity",
        "merger_agreement",
        "clean_team",
        "other",
    ]
    signed: bool | None = None
    grants_diligence_access: bool | None = None
    includes_standstill: bool | None = None
    consideration_type: Literal["cash", "stock", "mixed", "other"] | None = None
    supersedes_observation_id: str | None = None
    other_detail: str | None = None


class SolicitationObservation(ObservationBase):
    obs_type: Literal["solicitation"]
    requested_submission: Literal[
        "ioi",
        "loi",
        "binding_offer",
        "best_and_final",
        "other",
    ]
    binding_level: Literal["non_binding", "binding", "mixed", "other"] | None = None
    due_date: ResolvedDate | None = None
    recipient_refs: list[str] = Field(default_factory=list)
    attachments: list[str] = Field(default_factory=list)
    other_detail: str | None = None


class ProposalObservation(ObservationBase):
    obs_type: Literal["proposal"]
    requested_by_observation_id: str | None = None
    revises_observation_id: str | None = None
    delivery_mode: Literal["oral", "written", "email", "phone", "other"] | None = None
    terms: MoneyTerms | None = None
    mentions_non_binding: bool | None = None
    includes_draft_merger_agreement: bool | None = None
    includes_markup: bool | None = None
    other_detail: str | None = None


class StatusObservation(ObservationBase):
    obs_type: Literal["status"]
    status_kind: Literal[
        "expressed_interest",
        "withdrew",
        "not_interested",
        "cannot_improve",
        "cannot_proceed",
        "limited_assets_only",
        "excluded",
        "selected_to_advance",
        "other",
    ]
    related_observation_id: str | None = None
    other_detail: str | None = None


class OutcomeObservation(ObservationBase):
    obs_type: Literal["outcome"]
    outcome_kind: Literal["executed", "terminated", "restarted", "other"]
    related_observation_id: str | None = None
    other_detail: str | None = None


Observation = Annotated[
    (
        ProcessObservation
        | AgreementObservation
        | SolicitationObservation
        | ProposalObservation
        | StatusObservation
        | OutcomeObservation
    ),
    Field(discriminator="obs_type"),
]


class DerivationBasis(SkillModel):
    rule_id: str
    source_observation_ids: list[str] = Field(default_factory=list)
    source_span_ids: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"]
    explanation: str


class ProcessPhaseRecord(SkillModel):
    phase_id: str
    phase_kind: Literal["informal", "formal", "extension", "endgame", "other"]
    start_observation_id: str
    end_observation_id: str | None = None
    participant_refs: list[str] = Field(default_factory=list)
    basis: DerivationBasis


class LifecycleTransitionRecord(SkillModel):
    transition_id: str
    subject_ref: str
    subject_count: int = 1
    event_date: ResolvedDate | None = None
    from_state: Literal[
        "unknown",
        "identified",
        "under_nda",
        "active",
        "submitted",
        "finalist",
        "inactive",
        "winner",
    ]
    to_state: Literal[
        "unknown",
        "identified",
        "under_nda",
        "active",
        "submitted",
        "finalist",
        "inactive",
        "winner",
    ]
    reason_kind: Literal["literal", "not_invited", "cannot_improve", "lost_to_winner", "other"]
    basis: DerivationBasis


class CashRegimeRecord(SkillModel):
    cash_regime_id: str
    scope_kind: Literal["cycle", "phase"]
    scope_ref: str
    regime: Literal["all_cash", "mixed", "unknown"]
    basis: DerivationBasis


class JudgmentRecord(SkillModel):
    judgment_id: str
    judgment_kind: Literal["initiation", "advisory_link", "ambiguous_exit", "ambiguous_phase"]
    subject_ref: str | None = None
    human_review_required: bool = True
    note: str | None = None
    basis: DerivationBasis


AnalystEventType = Literal[
    "target_sale",
    "target_sale_public",
    "bidder_sale",
    "bidder_interest",
    "activist_sale",
    "sale_press_release",
    "bid_press_release",
    "ib_retention",
    "ib_terminated",
    "nda",
    "nda_amendment",
    "standstill",
    "exclusivity",
    "clean_team",
    "proposal",
    "drop",
    "final_round_inf_ann",
    "final_round_inf",
    "final_round_ann",
    "final_round",
    "final_round_ext_ann",
    "final_round_ext",
    "executed",
    "terminated",
    "restarted",
]


class AnalystRowRecord(SkillModel):
    row_id: str
    origin: Literal["literal", "derived", "synthetic_anonymous"]
    analyst_event_type: AnalystEventType
    subject_ref: str | None = None
    row_count: int = 1
    bidder_name: str | None = None
    bidder_type: str | None = None
    bid_type: Literal["Informal", "Formal", "Uncertain"] | None = None
    value: Decimal | None = None
    range_low: Decimal | None = None
    range_high: Decimal | None = None
    enterprise_value: Decimal | None = None
    date_precision: str | None = None
    date_recorded: date | None = None
    date_public: date | None = None
    date_sort_proxy: date | None = None
    all_cash: bool | None = None
    review_flags: list[str] = Field(default_factory=list)
    basis: DerivationBasis


class CoverageCheckRecordV2(CoverageCheckRecord):
    supporting_observation_ids: list[str] = Field(default_factory=list)
    supporting_party_ids: list[str] = Field(default_factory=list)
    supporting_cohort_ids: list[str] = Field(default_factory=list)


class CoverageFindingsArtifactV2(SkillModel):
    findings: list[CoverageCheckRecordV2] = Field(default_factory=list)


class CheckFindingV2(SkillModel):
    check_id: str
    severity: Literal["blocker", "warning"]
    description: str
    party_ids: list[str] = Field(default_factory=list)
    cohort_ids: list[str] = Field(default_factory=list)
    observation_ids: list[str] = Field(default_factory=list)


class SkillCheckReportV2(SkillModel):
    findings: list[CheckFindingV2] = Field(default_factory=list)
    summary: CheckReportSummary


class GateFindingV2(SkillModel):
    gate_id: str
    rule_id: str
    severity: Literal["blocker", "warning"]
    description: str
    party_ids: list[str] = Field(default_factory=list)
    cohort_ids: list[str] = Field(default_factory=list)
    observation_ids: list[str] = Field(default_factory=list)


class GateReportV2(SkillModel):
    findings: list[GateFindingV2] = Field(default_factory=list)
    summary: GateReportSummary


class ObservationArtifactV2(SkillModel):
    parties: list[PartyRecord] = Field(default_factory=list)
    cohorts: list[CohortRecord] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)
    exclusions: list[SkillExclusionRecord] = Field(default_factory=list)
    coverage: list[CoverageCheckRecord] = Field(default_factory=list)


class DerivedArtifactV2(SkillModel):
    phases: list[ProcessPhaseRecord] = Field(default_factory=list)
    transitions: list[LifecycleTransitionRecord] = Field(default_factory=list)
    cash_regimes: list[CashRegimeRecord] = Field(default_factory=list)
    judgments: list[JudgmentRecord] = Field(default_factory=list)
    analyst_rows: list[AnalystRowRecord] = Field(default_factory=list)


__all__ = [
    "AgreementObservation",
    "AnalystEventType",
    "AnalystRowRecord",
    "CashRegimeRecord",
    "CheckFindingV2",
    "CohortRecord",
    "CoverageCheckRecord",
    "CoverageCheckRecordV2",
    "CoverageFindingsArtifactV2",
    "CoverageSummary",
    "DerivationBasis",
    "DerivedArtifactV2",
    "GateFindingV2",
    "GateReportV2",
    "JudgmentRecord",
    "LifecycleTransitionRecord",
    "Observation",
    "ObservationArtifactV2",
    "ObservationBase",
    "OutcomeObservation",
    "PartyRecord",
    "ProcessObservation",
    "ProcessPhaseRecord",
    "ProposalObservation",
    "SolicitationObservation",
    "SkillCheckReportV2",
    "StatusObservation",
]
