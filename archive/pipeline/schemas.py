from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ACTOR_TYPES = (
    "bidder",
    "advisor",
    "activist",
    "target_board",
)

BIDDER_SUBTYPES = (
    "strategic",
    "financial",
    "non_us",
    "mixed",
)

LIFECYCLE_STATUSES = (
    "bid",
    "dropped",
    "dropped_by_target",
    "winner",
    "stale",
    "advisor",
    "unresolved",
)

DECISION_TYPES = (
    "alias_merge",
    "approximate_date",
    "implicit_dropout",
    "event_type_choice",
    "actor_type_classification",
    "count_interpretation",
    "cycle_boundary",
    "filing_selection",
    "scope_exclusion",
)

EVENT_TYPES = (
    "target_sale",
    "target_sale_public",
    "bidder_sale",
    "bidder_interest",
    "activist_sale",
    "sale_press_release",
    "bid_press_release",
    "ib_retention",
    "nda",
    "proposal",
    "drop",
    "drop_below_m",
    "drop_below_inf",
    "drop_at_inf",
    "drop_target",
    "final_round_inf_ann",
    "final_round_inf",
    "final_round_ann",
    "final_round",
    "final_round_ext_ann",
    "final_round_ext",
    "executed",
    "terminated",
    "restarted",
)

PARTICIPATION_ROLES = (
    "bidder",
    "advisor",
    "counterparty",
    "decision_maker",
    "initiator",
)

RECONCILIATION_TYPES = (
    "advisor_exclusion",
    "stale_process",
    "unnamed_aggregate",
    "filing_approximation",
    "consortium_counted_once",
    "partial_bidder_excluded",
    "unresolved",
)

AUDIT_FLAG_VALUES = (
    "unresolved_actors",
    "unverified_quotes",
    "count_mismatch",
    "missing_nda",
    "missing_round_pair",
    "missing_initiation",
    "lifecycle_inconsistency",
    "proposal_completeness",
)

AUDIT_CHECK_NAMES = (
    "nda_coverage",
    "round_pairs",
    "process_initiation",
    "lifecycle_consistency",
    "proposal_completeness",
)

PRIMARY_FILING_TYPES = (
    "DEFM14A",
    "PREM14A",
    "SC 14D-9",
    "SC 13E-3",
    "S-4",
    "SC TO-T",
)

SUPPLEMENTARY_FILING_TYPES = (
    "SC 13D",
    "DEFA14A",
    "8-K",
)

OVERRIDES_CSV_HEADER: tuple[str, ...] = (
    "override_id",
    "target_type",
    "target_id",
    "field",
    "original_value",
    "corrected_value",
    "reviewer",
    "date",
    "basis",
)

MASTER_ROW_FIELDNAMES: tuple[str, ...] = (
    "deal_slug",
    "target_name",
    "cik",
    "winning_acquirer",
    "deal_outcome",
    "consideration_type",
    "DateAnnounced",
    "DateEffective",
    "filing_type",
    "URL",
    "row_seq",
    "event_id",
    "event_type",
    "bid_note",
    "cycle_id",
    "actor_id",
    "BidderName",
    "actor_type",
    "bidder_subtype",
    "lifecycle_status",
    "participation_role",
    "actor_notes",
    "event_date",
    "date_precision",
    "round_id",
    "bid_value_pershare",
    "bid_value_lower",
    "bid_value_upper",
    "all_cash",
    "event_consideration_type",
    "cshoc",
    "bid_type",
    "bid_classification_rule",
    "bid_classification_confidence",
    "initiation",
    "formal_boundary_event",
    "source_text_short",
    "raw_note",
    "deal_notes",
    "reviewer_note",
    "needs_review",
    "flag_approximate_date",
    "flag_missing_nda",
    "flag_unresolved_lifecycle",
    "flag_anonymous_mapping",
    "comments_1",
    "comments_2",
)


class FrozenModel(BaseModel):
    """Base model with immutable instances and strict field handling."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class Actor(FrozenModel):
    """One row from actors.jsonl representing an identified party in the deal."""

    actor_id: str = Field(description="Stable actor identifier in the form <deal_slug>/<label>.")
    actor_alias: str = Field(description="Human-readable alias from the filing or resolved entity name.")
    actor_type: Literal["bidder", "advisor", "activist", "target_board"] = Field(
        description="Top-level actor type classification."
    )
    bidder_subtype: Literal["strategic", "financial", "non_us", "mixed"] | None = Field(
        default=None,
        description="Optional bidder subtype, only populated when actor_type is bidder.",
    )
    is_grouped: bool | None = Field(
        default=None,
        description="True when the actor is an explicitly grouped consortium or aggregate bidder.",
    )
    group_size: int | None = Field(
        default=None,
        description="Number of constituent parties when is_grouped is true.",
        ge=1,
    )
    lifecycle_status: Literal[
        "bid",
        "dropped",
        "dropped_by_target",
        "winner",
        "stale",
        "advisor",
        "unresolved",
    ] = Field(description="Lifecycle status assigned to the actor within the extracted process.")
    actor_notes: str | None = Field(default=None, description="Free-form notes about the actor.")
    first_evidence_accession_number: str = Field(
        description="Accession number of the filing line range first establishing this actor."
    )
    first_evidence_line_start: int = Field(
        description="One-indexed starting line of the first identity-establishing quote.",
        ge=1,
    )
    first_evidence_line_end: int = Field(
        description="One-indexed ending line of the first identity-establishing quote.",
        ge=1,
    )
    first_evidence_text: str = Field(
        description="Verbatim text establishing the actor identity or label in the filing."
    )

    @model_validator(mode="after")
    def validate_actor(self) -> Actor:
        """Enforce internal schema consistency for actor records."""

        if self.first_evidence_line_end < self.first_evidence_line_start:
            raise ValueError("first_evidence_line_end must be greater than or equal to first_evidence_line_start")
        if self.actor_type != "bidder" and self.bidder_subtype is not None:
            raise ValueError("bidder_subtype may only be populated for bidder actors")
        if self.actor_type == "advisor" and self.lifecycle_status != "advisor":
            raise ValueError("advisor actors must have lifecycle_status='advisor'")
        if self.is_grouped is True and (self.group_size is None or self.group_size < 2):
            raise ValueError("group_size must be at least 2 when is_grouped is true")
        if self.is_grouped is False and self.group_size not in (None, 1):
            raise ValueError("group_size must be omitted or 1 when is_grouped is false")
        return self


class CountAssertion(FrozenModel):
    """One numeric assertion from count_assertions.json."""

    assertion_id: str = Field(description="Unique assertion identifier within the deal.")
    assertion_text: str = Field(description="Full sentence or clause containing the numeric assertion.")
    metric: str = Field(description="Metric being counted, such as nda_signed or parties_contacted.")
    expected_count: int = Field(description="Integer count claimed by the filing.", ge=0)
    time_scope: str = Field(description="Normalized textual description of the timing scope of the assertion.")
    cycle_scope: str = Field(description="Normalized textual description of the process cycle covered.")
    source_accession_number: str = Field(description="Accession number for the filing source of the assertion.")
    source_line_start: int = Field(description="One-indexed line at which the assertion begins.", ge=1)
    source_line_end: int = Field(description="One-indexed line at which the assertion ends.", ge=1)
    source_text: str = Field(description="Verbatim source text supporting the assertion.")

    @model_validator(mode="after")
    def validate_count_assertion(self) -> CountAssertion:
        """Validate line order on count assertions."""

        if self.source_line_end < self.source_line_start:
            raise ValueError("source_line_end must be greater than or equal to source_line_start")
        return self


class Decision(FrozenModel):
    """One append-only decision record written to decisions.jsonl."""

    skill: str = Field(description="Pipeline skill or stage that produced the decision.")
    decision_type: Literal[
        "alias_merge",
        "approximate_date",
        "implicit_dropout",
        "event_type_choice",
        "actor_type_classification",
        "count_interpretation",
        "cycle_boundary",
        "filing_selection",
        "scope_exclusion",
    ] = Field(description="Controlled vocabulary label for the decision type.")
    detail: str = Field(description="Human-readable explanation of the decision.")
    artifact_affected: str = Field(description="Artifact filename or path affected by the decision.")
    target_id: str = Field(description="Primary identifier of the object affected by the decision.")
    confidence: Literal["high", "medium", "low"] = Field(description="Confidence assigned to the decision.")


class EvidenceAttributes(FrozenModel):
    """Proposal-only auxiliary evidence features used for later bid classification."""

    preceded_by_process_letter: bool | None = Field(
        default=None,
        description="Whether a process letter preceded the proposal.",
    )
    accompanied_by_merger_agreement: bool | None = Field(
        default=None,
        description="Whether the proposal was accompanied by a merger agreement draft or markup.",
    )
    post_final_round_announcement: bool | None = Field(
        default=None,
        description="Whether the proposal followed a final-round announcement.",
    )
    filing_language: str | None = Field(
        default=None,
        description="The filing's own verbal characterization of the proposal.",
    )


class Event(FrozenModel):
    """One row from events.jsonl representing a dated event in the M&A chronology."""

    event_id: str = Field(description="Stable event identifier unique within the deal.")
    event_type: Literal[
        "target_sale",
        "target_sale_public",
        "bidder_sale",
        "bidder_interest",
        "activist_sale",
        "sale_press_release",
        "bid_press_release",
        "ib_retention",
        "nda",
        "proposal",
        "drop",
        "drop_below_m",
        "drop_below_inf",
        "drop_at_inf",
        "drop_target",
        "final_round_inf_ann",
        "final_round_inf",
        "final_round_ann",
        "final_round",
        "final_round_ext_ann",
        "final_round_ext",
        "executed",
        "terminated",
        "restarted",
    ] = Field(description="Controlled event taxonomy label.")
    date: str = Field(description="Calendar date in ISO YYYY-MM-DD form.")
    date_precision: Literal["exact", "approximate", "month_only"] | None = Field(
        default=None,
        description="Precision of the populated event date.",
    )
    value: float | None = Field(default=None, description="Bid value, usually a per-share midpoint for proposals.")
    value_lower: float | None = Field(default=None, description="Lower bound for a bid value range.")
    value_upper: float | None = Field(default=None, description="Upper bound for a bid value range.")
    value_unit: Literal["per_share", "total"] | None = Field(
        default=None,
        description="Unit attached to the bid value fields.",
    )
    consideration_type: Literal["cash", "stock", "mixed", "cash_plus_cvr"] | None = Field(
        default=None,
        description="Consideration form specific to the event, when applicable.",
    )
    evidence_attributes: EvidenceAttributes | None = Field(
        default=None,
        description="Proposal-only auxiliary evidence attributes used for later classification.",
    )
    source_accession_number: str = Field(description="Accession number for the source filing.")
    source_line_start: int = Field(description="One-indexed starting line of the supporting quote.", ge=1)
    source_line_end: int = Field(description="One-indexed ending line of the supporting quote.", ge=1)
    source_text: str = Field(description="Verbatim quote supporting the event row.")
    raw_note: str | None = Field(default=None, description="Free-form context note or inference explanation.")

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        """Require an ISO date string with day precision present."""

        parts: list[str] = value.split("-")
        if len(parts) != 3 or any(not part.isdigit() for part in parts):
            raise ValueError("date must be in ISO YYYY-MM-DD format")
        if len(parts[0]) != 4 or len(parts[1]) != 2 or len(parts[2]) != 2:
            raise ValueError("date must be in ISO YYYY-MM-DD format")
        return value

    @model_validator(mode="after")
    def validate_event(self) -> Event:
        """Validate internal event field relationships."""

        if self.source_line_end < self.source_line_start:
            raise ValueError("source_line_end must be greater than or equal to source_line_start")
        if (self.value_lower is None) ^ (self.value_upper is None):
            raise ValueError("value_lower and value_upper must either both be populated or both be null")
        if self.event_type != "proposal" and self.evidence_attributes is not None:
            raise ValueError("evidence_attributes may only be present on proposal events")
        return self


class EventActorLink(FrozenModel):
    """One row from event_actor_links.jsonl linking an event to an actor role."""

    event_id: str = Field(description="Referenced event identifier from events.jsonl.")
    actor_id: str = Field(description="Referenced actor identifier from actors.jsonl.")
    participation_role: Literal["bidder", "advisor", "counterparty", "decision_maker", "initiator"] = Field(
        description="Role the actor plays in the linked event."
    )


class SourceReference(FrozenModel):
    """A direct line-level source reference used inside deal-level provenance."""

    source_accession_number: str = Field(description="Accession number for the supporting filing.")
    source_line_start: int = Field(description="One-indexed starting line of the support quote.", ge=1)
    source_line_end: int = Field(description="One-indexed ending line of the support quote.", ge=1)
    source_text: str = Field(description="Verbatim supporting quote text.")

    @model_validator(mode="after")
    def validate_source_reference(self) -> SourceReference:
        """Validate source reference line ordering."""

        if self.source_line_end < self.source_line_start:
            raise ValueError("source_line_end must be greater than or equal to source_line_start")
        return self


class DirectQuoteProvenance(FrozenModel):
    """Provenance mode indicating the value is quoted directly from source text."""

    mode: Literal["direct_quote"] = Field(description="Direct-quote provenance discriminator.")
    source_refs: list[SourceReference] = Field(
        description="One or more direct source references supporting the value.",
        min_length=1,
    )


class DerivedFromRowsProvenance(FrozenModel):
    """Provenance mode indicating the value is derived from extracted event rows."""

    mode: Literal["derived_from_rows"] = Field(description="Derived-from-rows provenance discriminator.")
    basis: str = Field(description="Deterministic derivation basis applied to extracted rows.")
    supporting_event_ids: list[str] = Field(
        description="Event identifiers supporting the derived value.",
        min_length=1,
    )


ProvenanceValue = Annotated[
    DirectQuoteProvenance | DerivedFromRowsProvenance,
    Field(discriminator="mode"),
]


class Deal(FrozenModel):
    """Deal-level metadata stored in deal.json with field-level provenance."""

    deal_slug: str = Field(description="Stable deal slug used throughout the pipeline.")
    target_name: str = Field(description="Target company name.")
    cik: str = Field(description="SEC Central Index Key for the target.")
    primary_accession_number: str = Field(description="Accession number of the anchor filing.")
    filing_type: str = Field(description="Filing type of the anchor filing.")
    filing_url: str = Field(description="Direct SEC URL for the anchor filing document.")
    filing_date: str = Field(description="Anchor filing date in ISO YYYY-MM-DD form.")
    winning_acquirer: str = Field(description="Actor identifier for the winning acquirer.")
    deal_outcome: Literal["completed", "terminated", "withdrawn"] = Field(
        description="Top-level outcome of the deal."
    )
    date_announced: str = Field(description="Public announcement date in ISO YYYY-MM-DD form.")
    date_effective: str | None = Field(
        default=None,
        description="Effective closing date in ISO YYYY-MM-DD form when the deal completed.",
    )
    consideration_type: Literal["all_cash", "stock", "mixed"] = Field(
        description="Overall consideration type for the deal."
    )
    deal_notes: str | None = Field(default=None, description="Deal-level narrative notes.")
    provenance: dict[str, ProvenanceValue] = Field(
        description="Per-field provenance map for deal-level values."
    )

    @field_validator("filing_date", "date_announced", "date_effective")
    @classmethod
    def validate_optional_iso_date(cls, value: str | None) -> str | None:
        """Validate ISO date strings on deal-level date fields."""

        if value is None:
            return value
        parts: list[str] = value.split("-")
        if len(parts) != 3 or any(not part.isdigit() for part in parts):
            raise ValueError("date values must be in ISO YYYY-MM-DD format")
        if len(parts[0]) != 4 or len(parts[1]) != 2 or len(parts[2]) != 2:
            raise ValueError("date values must be in ISO YYYY-MM-DD format")
        return value


class CensusPartyRosterEntry(FrozenModel):
    """Roster entry embedded inside census.json."""

    actor_id: str = Field(description="Actor identifier copied from actors.jsonl.")
    actor_alias: str = Field(description="Human-readable actor alias.")
    actor_type: Literal["bidder", "advisor", "activist", "target_board"] = Field(
        description="Actor type copied from actors.jsonl."
    )
    bidder_subtype: Literal["strategic", "financial", "non_us", "mixed"] | None = Field(
        default=None,
        description="Optional bidder subtype copied from actors.jsonl.",
    )
    lifecycle_status: Literal[
        "bid",
        "dropped",
        "dropped_by_target",
        "winner",
        "stale",
        "advisor",
        "unresolved",
    ] = Field(description="Lifecycle status copied from actors.jsonl.")
    source: Literal["actors.jsonl", "actors_extended.jsonl"] = Field(
        description="Source actor artifact contributing the roster entry."
    )
    first_evidence_accession_number: str = Field(
        description="Accession number for the actor's first evidence citation."
    )
    first_evidence_line_start: int = Field(
        description="One-indexed starting line for the actor's first evidence quote.",
        ge=1,
    )
    first_evidence_line_end: int = Field(
        description="One-indexed ending line for the actor's first evidence quote.",
        ge=1,
    )
    first_evidence_text: str = Field(
        description="Verbatim actor-identifying quote copied from actors.jsonl."
    )

    @model_validator(mode="after")
    def validate_party_roster_entry(self) -> CensusPartyRosterEntry:
        """Validate embedded roster entry line ordering."""

        if self.first_evidence_line_end < self.first_evidence_line_start:
            raise ValueError("first_evidence_line_end must be greater than or equal to first_evidence_line_start")
        return self


class ReconciliationExplanation(FrozenModel):
    """One structured explanation item contributing to count reconciliation."""

    type: Literal[
        "advisor_exclusion",
        "stale_process",
        "unnamed_aggregate",
        "filing_approximation",
        "consortium_counted_once",
        "partial_bidder_excluded",
        "unresolved",
    ] = Field(description="Controlled reconciliation explanation category.")
    related_actor_ids: list[str] = Field(
        default_factory=list,
        description="Actor identifiers implicated by the reconciliation explanation.",
    )
    related_event_ids: list[str] = Field(
        default_factory=list,
        description="Event identifiers implicated by the reconciliation explanation.",
    )
    count_adjustment: int = Field(
        default=0,
        description="Signed count adjustment contributed by the explanation.",
    )


class Reconciliation(FrozenModel):
    """One reconciled comparison between a filing count assertion and extracted data."""

    assertion_id: str = Field(description="Referenced count assertion identifier.")
    expected: int = Field(description="Expected count stated in the filing.")
    extracted: int = Field(description="Observed count from extracted structured data.")
    explained: int = Field(description="Portion of the gap explained by structured reconciliation items.")
    residual: int = Field(description="Remaining unexplained residual after explanations are applied.")
    status: Literal["pass", "fail"] = Field(description="Pass when residual is zero, fail otherwise.")
    explanations: list[ReconciliationExplanation] = Field(
        default_factory=list,
        description="Structured typed explanations for the gap.",
    )

    @model_validator(mode="after")
    def validate_reconciliation(self) -> Reconciliation:
        """Ensure reconciliation status and arithmetic remain internally consistent."""

        implied_residual: int = self.expected - self.extracted - self.explained
        if implied_residual != self.residual:
            raise ValueError("reconciliation residual must equal expected - extracted - explained")
        expected_status: str = "pass" if self.residual == 0 else "fail"
        if self.status != expected_status:
            raise ValueError("reconciliation status must be 'pass' when residual is zero and 'fail' otherwise")
        return self


class AuditFailure(FrozenModel):
    """One structural audit failure entry embedded in census.json and audit_flags.json."""

    check: Literal[
        "nda_coverage",
        "round_pairs",
        "process_initiation",
        "lifecycle_consistency",
        "proposal_completeness",
    ] = Field(description="Audit check that failed or needs review.")
    detail: str = Field(description="Human-readable description of the failure.")
    actor_id: str | None = Field(
        default=None,
        description="Actor identifier implicated by the failure, when applicable.",
    )


class StructuralAudit(FrozenModel):
    """Five-point structural audit summary embedded in census.json."""

    nda_coverage: Literal["pass", "needs_review"] = Field(description="Outcome of the NDA coverage check.")
    round_pairs: Literal["pass", "needs_review"] = Field(description="Outcome of the round pairing check.")
    process_initiation: Literal["pass", "needs_review"] = Field(
        description="Outcome of the process initiation presence check."
    )
    lifecycle_consistency: Literal["pass", "needs_review"] = Field(
        description="Outcome of the lifecycle-to-event consistency check."
    )
    proposal_completeness: Literal["pass", "needs_review"] = Field(
        description="Outcome of the invited-bidder proposal completeness check."
    )
    failures: list[AuditFailure] = Field(
        default_factory=list,
        description="All structural failures across the five deterministic checks.",
    )


class LifecycleAudit(FrozenModel):
    """Lifecycle closure summary embedded in census.json."""

    total_actors: int = Field(description="Count of non-advisor actors included in the lifecycle audit.", ge=0)
    closed_actors: int = Field(
        description="Count of non-advisor actors whose lifecycle status is not unresolved.",
        ge=0,
    )
    unresolved_actors: list[str] = Field(
        default_factory=list,
        description="Actor identifiers that remain unresolved after extraction and audit.",
    )


class SelfCheck(FrozenModel):
    """Self-check block embedded in census.json."""

    reconciliations: list[Reconciliation] = Field(
        default_factory=list,
        description="Reconciliation results for all extracted count assertions.",
    )
    structural_audit: StructuralAudit = Field(description="Summary of the five-point structural audit.")
    lifecycle_audit: LifecycleAudit = Field(description="Lifecycle closure summary.")


class Census(FrozenModel):
    """Top-level census.json artifact."""

    party_roster: list[CensusPartyRosterEntry] = Field(
        default_factory=list,
        description="Actor roster snapshot used for downstream reconciliation and review.",
    )
    count_assertions: list[CountAssertion] = Field(
        default_factory=list,
        description="All numeric filing assertions collected during actor extraction.",
    )
    self_check: SelfCheck = Field(description="Deterministic self-check and reconciliation summary.")


class AuditFlags(FrozenModel):
    """Top-level audit_flags.json artifact used to route review work."""

    deal_slug: str = Field(description="Deal slug for the audited deal.")
    flags: list[
        Literal[
            "unresolved_actors",
            "unverified_quotes",
            "count_mismatch",
            "missing_nda",
            "missing_round_pair",
            "missing_initiation",
            "lifecycle_inconsistency",
            "proposal_completeness",
        ]
    ] = Field(default_factory=list, description="Distinct deal-level flags raised by the audit stage.")
    unresolved_actors: list[str] = Field(
        default_factory=list,
        description="Actor identifiers whose lifecycle remains unresolved.",
    )
    unresolved_counts: list[str] = Field(
        default_factory=list,
        description="Assertion identifiers that remain count-mismatched after reconciliation.",
    )
    unverified_quotes: list[str] = Field(
        default_factory=list,
        description="Object identifiers with source quotes that could not be verified deterministically.",
    )
    structural_failures: list[AuditFailure] = Field(
        default_factory=list,
        description="Structural audit failures copied through for reviewer visibility.",
    )


class Round(FrozenModel):
    """One nested round object embedded in process_cycles.jsonl."""

    round_id: str = Field(description="Round identifier unique within the deal.")
    announcement_event_id: str = Field(description="Event identifier for the round announcement event.")
    deadline_event_id: str = Field(description="Event identifier for the matching round deadline event.")
    invited_set: list[str] = Field(
        default_factory=list,
        description="Actor identifiers invited to participate in the round.",
    )
    source_text: str = Field(description="Verbatim announcement text describing the round invitation.")


class ProcessCycle(FrozenModel):
    """One process cycle row written to process_cycles.jsonl."""

    cycle_id: str = Field(description="Cycle identifier in the form <slug>_c<N>.")
    cycle_sequence: int = Field(description="One-indexed cycle sequence within the deal.", ge=1)
    start_event_id: str = Field(description="First event identifier assigned to the cycle.")
    end_event_id: str = Field(description="Last event identifier assigned to the cycle.")
    status: Literal["completed", "terminated", "withdrawn"] = Field(
        description="Terminal status of the cycle."
    )
    segmentation_basis: str = Field(description="Brief explanation for the cycle boundary choice.")
    rounds: list[Round] = Field(default_factory=list, description="Nested rounds identified within the cycle.")


class BidClassification(FrozenModel):
    """One bid classification judgment row written to judgments.jsonl."""

    judgment_type: Literal["bid_classification"] = Field(description="Judgment discriminator.")
    scope: Literal["event"] = Field(description="Scope discriminator for proposal-level judgments.")
    scope_id: str = Field(description="Proposal event identifier being classified.")
    value: Literal["formal", "informal"] = Field(description="Bid formality classification.")
    classification_rule: str = Field(description="Deterministic rule label producing the classification.")
    confidence: Literal["high", "medium", "low"] = Field(description="Confidence in the classification.")


class Initiation(FrozenModel):
    """One deal-level initiation judgment row written to judgments.jsonl."""

    judgment_type: Literal["initiation"] = Field(description="Judgment discriminator.")
    scope: Literal["deal"] = Field(description="Scope discriminator for deal-level judgments.")
    scope_id: str = Field(description="Deal slug for the judged deal.")
    value: Literal["target_driven", "bidder_driven", "activist_driven", "mixed"] = Field(
        description="Initiation classification assigned to the deal."
    )
    basis: str = Field(description="Factual basis supporting the initiation classification.")
    source_text: str = Field(description="Verbatim quote supporting the initiation judgment.")
    confidence: Literal["high", "medium", "low"] = Field(description="Confidence in the initiation judgment.")
    alternative_value: Literal["target_driven", "bidder_driven", "activist_driven", "mixed"] | None = Field(
        default=None,
        description="Next-best alternative interpretation, when applicable.",
    )
    alternative_basis: str | None = Field(
        default=None,
        description="Reason supporting the alternative interpretation, when applicable.",
    )


class FormalBoundary(FrozenModel):
    """One deal-level formal-boundary judgment row written to judgments.jsonl."""

    judgment_type: Literal["formal_boundary"] = Field(description="Judgment discriminator.")
    scope: Literal["deal"] = Field(description="Scope discriminator for deal-level judgments.")
    scope_id: str = Field(description="Deal slug for the judged deal.")
    value: str | None = Field(description="Boundary event identifier or null when no formal boundary exists.")
    basis: str = Field(description="Factual basis supporting the chosen boundary placement.")
    source_text: str = Field(description="Verbatim quote supporting the boundary placement.")
    confidence: Literal["high", "medium", "low"] = Field(description="Confidence in the boundary judgment.")
    alternative_value: str | None = Field(
        default=None,
        description="Alternative plausible boundary event identifier, when applicable.",
    )
    alternative_basis: str | None = Field(
        default=None,
        description="Reason supporting the alternative boundary placement, when applicable.",
    )


Judgment = Annotated[BidClassification | Initiation | FormalBoundary, Field(discriminator="judgment_type")]


class FilingSearchRecord(FrozenModel):
    """One filing-search summary row embedded in source_selection.json."""

    filing_type: str = Field(description="Filing type searched, such as DEFM14A or SC 14D-9.")
    results_count: int = Field(description="Number of search results found for the filing type.", ge=0)
    disposition: Literal["selected", "searched_not_used", "not_applicable", "not_found", "uncertain"] = Field(
        description="How the filing search outcome was used during anchor selection."
    )
    selected_accession_number: str | None = Field(
        default=None,
        description="Selected accession number when this filing type supplied the anchor filing.",
    )
    reason: str | None = Field(default=None, description="Optional rationale for the disposition.")


class DocumentListEntry(FrozenModel):
    """One document row listed on the SEC filing index page."""

    filename: str = Field(description="Filename listed on the SEC filing index page.")
    description: str = Field(description="Document description listed on the filing index page.")
    size: str = Field(description="Size value shown on the filing index page.")


class DocumentSelection(FrozenModel):
    """Selected-document metadata embedded in source_selection.json."""

    index_url: str = Field(description="SEC filing index URL used to inspect the document table.")
    documents_listed: list[DocumentListEntry] = Field(
        default_factory=list,
        description="All listed documents extracted from the SEC filing index page.",
    )
    selected_document: str = Field(description="Filename selected as the main HTML document to freeze.")
    selection_rationale: str = Field(description="Deterministic explanation for why the document was selected.")


class SourceSelection(FrozenModel):
    """Top-level source_selection.json artifact."""

    deal_slug: str = Field(description="Deal slug for the sourced deal.")
    cik: str = Field(description="Resolved SEC CIK for the target company.")
    target_name: str = Field(description="Target company name supplied to sourcing.")
    primary_searches: list[FilingSearchRecord] = Field(
        default_factory=list,
        description="Search results and dispositions for primary filing types.",
    )
    supplementary_searches: list[FilingSearchRecord] = Field(
        default_factory=list,
        description="Search results and dispositions for supplementary filing types.",
    )
    document_selection: DocumentSelection = Field(description="Document-table inspection details for the anchor filing.")


class CorpusManifestEntry(FrozenModel):
    """One filing row embedded in corpus_manifest.json."""

    accession_number: str = Field(description="SEC accession number.")
    filing_type: str = Field(description="Filing type for the archived filing.")
    role: Literal["primary", "supplementary"] = Field(description="Role of the filing in the deal bundle.")
    url: str = Field(description="Full SEC URL for the selected filing document.")
    html_filename: str = Field(description="Relative path to the archived HTML file.")
    txt_filename: str = Field(description="Relative path to the frozen text snapshot.")
    filing_date: str = Field(description="Filing date in ISO YYYY-MM-DD form.")
    fetch_status: Literal["success", "failed"] = Field(description="Outcome of fetching and freezing the filing.")
    fetch_error: str | None = Field(default=None, description="Error message when fetch_status is failed.")

    @field_validator("filing_date")
    @classmethod
    def validate_manifest_date(cls, value: str) -> str:
        """Validate manifest ISO date strings."""

        parts: list[str] = value.split("-")
        if len(parts) != 3 or any(not part.isdigit() for part in parts):
            raise ValueError("filing_date must be in ISO YYYY-MM-DD format")
        if len(parts[0]) != 4 or len(parts[1]) != 2 or len(parts[2]) != 2:
            raise ValueError("filing_date must be in ISO YYYY-MM-DD format")
        return value


class ChronologyBookmark(FrozenModel):
    """Top-level chronology_bookmark.json artifact."""

    accession_number: str = Field(description="Primary filing accession number containing the chronology section.")
    section_heading: str = Field(description="Exact heading text found in the frozen text snapshot.")
    start_line: int = Field(description="One-indexed line number of the chronology heading.", ge=1)
    end_line: int = Field(description="One-indexed line number of the last chronology line.", ge=1)
    confidence: Literal["high", "medium", "low"] = Field(description="Confidence in the selected chronology span.")
    selection_basis: str = Field(description="Deterministic explanation for distinguishing the chosen section.")

    @model_validator(mode="after")
    def validate_bookmark(self) -> ChronologyBookmark:
        """Validate chronology bookmark line ordering."""

        if self.end_line < self.start_line:
            raise ValueError("end_line must be greater than or equal to start_line")
        return self


class ReviewStatus(FrozenModel):
    """Top-level review_status.json artifact."""

    status: Literal["needs_review", "pending_review"] = Field(
        description="Deal review status derived from audit and row-level flags."
    )
    flags: list[str] = Field(default_factory=list, description="Deal-level flags currently attached to the deal.")
    last_extraction_date: str = Field(description="Date of the most recent extraction run in ISO YYYY-MM-DD form.")
    reviewer: str | None = Field(default=None, description="Reviewer identifier or name, populated during human review.")
    review_date: str | None = Field(
        default=None,
        description="Date human review was completed in ISO YYYY-MM-DD form.",
    )

    @field_validator("last_extraction_date", "review_date")
    @classmethod
    def validate_review_dates(cls, value: str | None) -> str | None:
        """Validate ISO date strings used in review-status metadata."""

        if value is None:
            return value
        parts: list[str] = value.split("-")
        if len(parts) != 3 or any(not part.isdigit() for part in parts):
            raise ValueError("review status dates must be in ISO YYYY-MM-DD format")
        if len(parts[0]) != 4 or len(parts[1]) != 2 or len(parts[2]) != 2:
            raise ValueError("review status dates must be in ISO YYYY-MM-DD format")
        return value


class QuoteVerifyResult(FrozenModel):
    """Result of deterministic quote verification against the frozen text snapshot."""

    object_type: Literal["event", "actor"] | None = Field(
        default=None,
        description="Type of object whose quote was verified.",
    )
    object_id: str | None = Field(default=None, description="Identifier of the object whose quote was verified.")
    verified: bool = Field(description="Whether the quote was verified in the frozen text snapshot.")
    strategy: Literal["primary", "retry_context", "full_file_search", "unverified"] = Field(
        description="Search strategy that succeeded or the final unverified state."
    )
    original_line_start: int = Field(description="Original claimed starting line for the quote.", ge=1)
    original_line_end: int = Field(description="Original claimed ending line for the quote.", ge=1)
    matched_line_start: int | None = Field(
        default=None,
        description="Matched starting line in the frozen text snapshot when verification succeeded.",
    )
    matched_line_end: int | None = Field(
        default=None,
        description="Matched ending line in the frozen text snapshot when verification succeeded.",
    )
    distinctive_phrase: str | None = Field(
        default=None,
        description="Distinctive phrase used for full-file fallback matching when applicable.",
    )
    detail: str = Field(description="Explanation of the verification outcome.")

    @model_validator(mode="after")
    def validate_quote_result(self) -> QuoteVerifyResult:
        """Validate line ordering and match presence for quote verification output."""

        if self.original_line_end < self.original_line_start:
            raise ValueError("original_line_end must be greater than or equal to original_line_start")
        if self.verified:
            if self.matched_line_start is None or self.matched_line_end is None:
                raise ValueError("verified quote results must include matched line bounds")
            if self.matched_line_end < self.matched_line_start:
                raise ValueError("matched_line_end must be greater than or equal to matched_line_start")
        return self


class AuditCheckResult(FrozenModel):
    """Structured result of one deterministic structural audit check."""

    check: Literal[
        "nda_coverage",
        "round_pairs",
        "process_initiation",
        "lifecycle_consistency",
        "proposal_completeness",
    ] = Field(description="Deterministic audit check name.")
    status: Literal["pass", "needs_review"] = Field(description="Outcome of the audit check.")
    failures: list[AuditFailure] = Field(
        default_factory=list,
        description="Specific failure items generated by the check.",
    )


@dataclass(slots=True, frozen=True)
class SeedDeal:
    """One input seed row used to drive pipeline execution."""

    deal_slug: str
    target_name: str
    filing_url: str | None


@dataclass(slots=True)
class DealState:
    """Mutable in-memory representation of a deal bundle while the pipeline is running."""

    deal_slug: str
    target_name: str
    filing_url: str | None
    deal_dir: Path
    cik: str | None = None
    source_selection: SourceSelection | None = None
    corpus_manifest: list[CorpusManifestEntry] = field(default_factory=list)
    chronology_bookmark: ChronologyBookmark | None = None
    actors: list[Actor] = field(default_factory=list)
    count_assertions: list[CountAssertion] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    event_actor_links: list[EventActorLink] = field(default_factory=list)
    reconciliations: list[Reconciliation] = field(default_factory=list)
    deal: Deal | None = None
    process_cycles: list[ProcessCycle] = field(default_factory=list)
    judgments: list[Judgment] = field(default_factory=list)
    census: Census | None = None
    audit_flags: AuditFlags | None = None


@dataclass(slots=True, frozen=True)
class Stage1Result:
    """Return value for deterministic stage 1 sourcing and chronology localization."""

    deal_slug: str
    cik: str
    source_selection: SourceSelection
    corpus_manifest: list[CorpusManifestEntry]
    chronology_bookmark: ChronologyBookmark
    html_path: Path
    txt_path: Path
    primary_accession_number: str
    filing_type: str
    filing_url: str


@dataclass(slots=True, frozen=True)
class Stage2Result:
    """Return value for stage 2 provider-backed extraction and validation."""

    actors: list[Actor]
    count_assertions: list[CountAssertion]
    events: list[Event]
    event_actor_links: list[EventActorLink]
    decisions: list[Decision]
    reconciliations: list[Reconciliation]
    deal: Deal


@dataclass(slots=True, frozen=True)
class Stage3Result:
    """Return value for deterministic enrichment stage output."""

    process_cycles: list[ProcessCycle]
    judgments: list[Judgment]
    decisions: list[Decision]


@dataclass(slots=True, frozen=True)
class Stage3AuditResult:
    """Return value for deterministic audit stage output."""

    quote_results: list[QuoteVerifyResult]
    census: Census
    audit_flags: AuditFlags


@dataclass(slots=True, frozen=True)
class PipelineResult:
    """Aggregate summary returned by the top-level orchestrator."""

    total_registered_deals: int
    completed_deals: list[str]
    failed_deals: dict[str, str]
    skipped_deals: list[str]
    total_cost_usd: float
    stage_counts: dict[str, int]
    master_csv_path: Path | None = None


__all__ = [
    "ACTOR_TYPES",
    "AUDIT_CHECK_NAMES",
    "AUDIT_FLAG_VALUES",
    "Actor",
    "AuditCheckResult",
    "AuditFailure",
    "AuditFlags",
    "BidClassification",
    "BIDDER_SUBTYPES",
    "ChronologyBookmark",
    "CorpusManifestEntry",
    "CountAssertion",
    "Census",
    "CensusPartyRosterEntry",
    "DECISION_TYPES",
    "Decision",
    "Deal",
    "DealState",
    "DerivedFromRowsProvenance",
    "DirectQuoteProvenance",
    "DocumentListEntry",
    "DocumentSelection",
    "EVENT_TYPES",
    "EvidenceAttributes",
    "Event",
    "EventActorLink",
    "FilingSearchRecord",
    "FormalBoundary",
    "FrozenModel",
    "Initiation",
    "Judgment",
    "LifecycleAudit",
    "LIFECYCLE_STATUSES",
    "MASTER_ROW_FIELDNAMES",
    "OVERRIDES_CSV_HEADER",
    "PARTICIPATION_ROLES",
    "PRIMARY_FILING_TYPES",
    "ProcessCycle",
    "ProvenanceValue",
    "QuoteVerifyResult",
    "RECONCILIATION_TYPES",
    "Reconciliation",
    "ReconciliationExplanation",
    "ReviewStatus",
    "Round",
    "SeedDeal",
    "SelfCheck",
    "SourceReference",
    "SourceSelection",
    "Stage1Result",
    "Stage2Result",
    "Stage3AuditResult",
    "Stage3Result",
    "StructuralAudit",
    "SUPPLEMENTARY_FILING_TYPES",
    "PipelineResult",
]
