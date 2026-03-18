from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pipeline.models.common import (
    ActorRole,
    AdvisorKind,
    BidderKind,
    ConsiderationType,
    EventType,
    GeographyFlag,
    ListingStatus,
)


class LLMOutputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RawEvidenceRef(LLMOutputModel):
    block_id: str | None = None
    evidence_id: str | None = None
    anchor_text: str

    @model_validator(mode="after")
    def validate_location(self) -> "RawEvidenceRef":
        if not self.block_id and not self.evidence_id:
            raise ValueError("RawEvidenceRef requires block_id or evidence_id")
        return self


class RawActorRecord(LLMOutputModel):
    actor_id: str
    display_name: str
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)
    role: ActorRole
    advised_actor_id: str | None = None
    advisor_kind: AdvisorKind | None = None
    bidder_kind: BidderKind | None = None
    listing_status: ListingStatus | None = None
    geography: GeographyFlag | None = None
    is_grouped: bool
    group_size: int | None = None
    group_label: str | None = None
    evidence_refs: list[RawEvidenceRef] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_group_metadata(self) -> "RawActorRecord":
        if self.is_grouped and self.group_size is None and not self.group_label:
            raise ValueError("Grouped actors require group_size or group_label")
        return self


class RawCountAssertion(LLMOutputModel):
    count: int
    subject: Literal[
        "interested_parties",
        "nda_signed_bidders",
        "nda_signed_financial_buyers",
        "nda_signed_strategic_buyers",
        "final_round_invitees",
        "other",
    ]
    qualifier_text: str | None = None
    evidence_refs: list[RawEvidenceRef] = Field(default_factory=list)


class ActorExtractionOutput(LLMOutputModel):
    actors: list[RawActorRecord] = Field(default_factory=list)
    count_assertions: list[RawCountAssertion] = Field(default_factory=list)
    unresolved_mentions: list[str] = Field(default_factory=list)


class RawDateHint(LLMOutputModel):
    raw_text: str
    normalized_hint: str | None = None
    relative_to: str | None = None


class RawMoneyTerms(LLMOutputModel):
    raw_text: str | None = None
    currency: str = "USD"
    value_per_share: Decimal | None = None
    lower_per_share: Decimal | None = None
    upper_per_share: Decimal | None = None
    total_enterprise_value: Decimal | None = None
    is_range: bool = False

    @model_validator(mode="after")
    def validate_amounts(self) -> "RawMoneyTerms":
        if not any(
            value is not None
            for value in (
                self.value_per_share,
                self.lower_per_share,
                self.upper_per_share,
                self.total_enterprise_value,
            )
        ):
            raise ValueError("Money terms require at least one amount")
        if self.is_range and self.lower_per_share is None and self.upper_per_share is None:
            raise ValueError("Range money terms require lower_per_share or upper_per_share")
        return self


class RawFormalitySignals(LLMOutputModel):
    contains_range: bool = False
    mentions_indication_of_interest: bool = False
    mentions_preliminary: bool = False
    mentions_non_binding: bool = False
    mentions_binding_offer: bool = False
    includes_draft_merger_agreement: bool = False
    includes_marked_up_agreement: bool = False
    requested_binding_offer_via_process_letter: bool = False
    after_final_round_announcement: bool = False
    after_final_round_deadline: bool = False
    is_subject_to_financing: bool | None = None


class RawEventRecord(LLMOutputModel):
    event_type: EventType
    date: RawDateHint
    actor_ids: list[str] = Field(default_factory=list)
    summary: str
    evidence_refs: list[RawEvidenceRef] = Field(default_factory=list)
    terms: RawMoneyTerms | None = None
    consideration_type: ConsiderationType | None = None
    whole_company_scope: bool | None = None
    whole_company_scope_note: str | None = None
    formality_signals: RawFormalitySignals | None = None
    drop_reason_text: str | None = None
    round_scope: Literal["informal", "formal", "extension"] | None = None
    invited_actor_ids: list[str] = Field(default_factory=list)
    deadline_date: RawDateHint | None = None
    executed_with_actor_id: str | None = None
    boundary_note: str | None = None
    nda_signed: bool = True
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_event_shape(self) -> "RawEventRecord":
        if self.event_type == EventType.PROPOSAL:
            if self.terms is None:
                raise ValueError("Proposal events require terms")
            if self.formality_signals is None:
                raise ValueError("Proposal events require formality_signals")
        if self.event_type in {
            EventType.FINAL_ROUND_INF_ANN,
            EventType.FINAL_ROUND_INF,
            EventType.FINAL_ROUND_ANN,
            EventType.FINAL_ROUND,
            EventType.FINAL_ROUND_EXT_ANN,
            EventType.FINAL_ROUND_EXT,
        } and self.round_scope is None:
            raise ValueError("Round events require round_scope")
        return self


class RawExclusion(LLMOutputModel):
    category: Literal[
        "partial_company_bid",
        "unsigned_nda",
        "stale_process_reference",
        "duplicate_mention",
        "non_event_context",
        "other",
    ]
    block_ids: list[str] = Field(default_factory=list)
    explanation: str


class EventExtractionOutput(LLMOutputModel):
    events: list[RawEventRecord] = Field(default_factory=list)
    exclusions: list[RawExclusion] = Field(default_factory=list)
    unresolved_mentions: list[str] = Field(default_factory=list)
    coverage_notes: list[str] = Field(default_factory=list)


class RecoveryTarget(LLMOutputModel):
    target_type: str
    block_ids: list[str] = Field(default_factory=list)
    reason: str
    anchor_text: str
    suggested_event_types: list[EventType] = Field(default_factory=list)


class RecoveryAuditOutput(LLMOutputModel):
    recovery_targets: list[RecoveryTarget] = Field(default_factory=list)


def pydantic_to_anthropic_schema(model_cls: type[BaseModel]) -> dict[str, Any]:
    schema = model_cls.model_json_schema(mode="validation")
    definitions = deepcopy(schema.pop("$defs", {}))
    return _inline_refs(schema, definitions)


def _inline_refs(value: Any, definitions: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        if "$ref" in value:
            ref = value["$ref"]
            if not ref.startswith("#/$defs/"):
                raise ValueError(f"Unsupported schema reference: {ref}")
            definition_name = ref.removeprefix("#/$defs/")
            resolved = deepcopy(definitions[definition_name])
            return _inline_refs(resolved, definitions)
        return {key: _inline_refs(child, definitions) for key, child in value.items()}
    if isinstance(value, list):
        return [_inline_refs(child, definitions) for child in value]
    return value
