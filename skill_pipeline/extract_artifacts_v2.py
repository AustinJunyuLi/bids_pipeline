from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, model_validator

from skill_pipeline.models import (
    CoverageCheckRecord,
    MoneyTerms,
    QuoteEntry,
    ResolvedDate,
    SkillExclusionRecord,
    SkillModel,
    SkillPathSet,
    SpanRecord,
    SpanRegistryArtifact,
)
from skill_pipeline.models_v2 import DerivedArtifactV2, ObservationArtifactV2
from skill_pipeline.normalize import normalize_raw_extraction


class RawPartyRecordV2(SkillModel):
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
    quote_ids: list[str] = Field(default_factory=list)


class RawCohortRecordV2(SkillModel):
    cohort_id: str
    label: str
    parent_cohort_id: str | None = None
    exact_count: int
    known_member_party_ids: list[str] = Field(default_factory=list)
    unknown_member_count: int
    membership_basis: str
    created_by_observation_id: str
    quote_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_counts(self) -> "RawCohortRecordV2":
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


class RawObservationBaseV2(SkillModel):
    observation_id: str
    obs_type: str
    date: ResolvedDate | None = None
    subject_refs: list[str] = Field(default_factory=list)
    counterparty_refs: list[str] = Field(default_factory=list)
    summary: str
    quote_ids: list[str] = Field(default_factory=list)


class RawProcessObservationV2(RawObservationBaseV2):
    obs_type: Literal["process"]
    process_kind: Literal[
        "sale_launch",
        "public_announcement",
        "advisor_retention",
        "press_release",
        "other",
    ]
    process_scope: Literal["target", "bidder", "activist", "other"] | None = None
    other_detail: str | None = None


class RawAgreementObservationV2(RawObservationBaseV2):
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


class RawSolicitationObservationV2(RawObservationBaseV2):
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


class RawProposalObservationV2(RawObservationBaseV2):
    obs_type: Literal["proposal"]
    requested_by_observation_id: str | None = None
    revises_observation_id: str | None = None
    delivery_mode: Literal["oral", "written", "email", "phone", "other"] | None = None
    terms: MoneyTerms | None = None
    mentions_non_binding: bool | None = None
    includes_draft_merger_agreement: bool | None = None
    includes_markup: bool | None = None
    other_detail: str | None = None


class RawStatusObservationV2(RawObservationBaseV2):
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


class RawOutcomeObservationV2(RawObservationBaseV2):
    obs_type: Literal["outcome"]
    outcome_kind: Literal["executed", "terminated", "restarted", "other"]
    related_observation_id: str | None = None
    other_detail: str | None = None


RawObservationV2 = Annotated[
    (
        RawProcessObservationV2
        | RawAgreementObservationV2
        | RawSolicitationObservationV2
        | RawProposalObservationV2
        | RawStatusObservationV2
        | RawOutcomeObservationV2
    ),
    Field(discriminator="obs_type"),
]


class RawObservationArtifactV2(SkillModel):
    quotes: list[QuoteEntry] = Field(default_factory=list)
    parties: list[RawPartyRecordV2] = Field(default_factory=list)
    cohorts: list[RawCohortRecordV2] = Field(default_factory=list)
    observations: list[RawObservationV2] = Field(default_factory=list)
    exclusions: list[SkillExclusionRecord] = Field(default_factory=list)
    coverage: list[CoverageCheckRecord] = Field(default_factory=list)


@dataclass
class LoadedObservationArtifacts:
    mode: Literal["quote_first", "canonical"]
    raw_artifact: RawObservationArtifactV2 | None
    observations: ObservationArtifactV2 | None
    spans: SpanRegistryArtifact | None
    derivations: DerivedArtifactV2 | None

    @property
    def span_index(self) -> dict[str, SpanRecord]:
        if not self.spans:
            return {}
        return {span.span_id: span for span in self.spans.spans}

    @property
    def party_index(self) -> dict[str, object]:
        if self.observations is None:
            return {}
        return {party.party_id: party for party in self.observations.parties}

    @property
    def cohort_index(self) -> dict[str, object]:
        if self.observations is None:
            return {}
        return {cohort.cohort_id: cohort for cohort in self.observations.cohorts}

    @property
    def observation_index(self) -> dict[str, object]:
        if self.observations is None:
            return {}
        return {
            observation.observation_id: observation
            for observation in self.observations.observations
    }


def load_observation_artifacts(
    paths: SkillPathSet,
    *,
    mode: Literal["auto", "quote_first", "canonical"] = "auto",
) -> LoadedObservationArtifacts:
    raw_exists = paths.observations_raw_path.exists()
    canonical_exists = paths.observations_path.exists()
    derivations = _load_optional_derivations(paths.derivations_path)

    if mode == "auto":
        if canonical_exists:
            mode = "canonical"
        elif raw_exists:
            mode = "quote_first"
        else:
            raise FileNotFoundError(
                f"Missing v2 observation artifact: {paths.observations_path} or {paths.observations_raw_path}"
            )

    if mode == "quote_first":
        if not raw_exists:
            raise FileNotFoundError(
                f"Missing required raw v2 artifact: {paths.observations_raw_path}"
            )
        raw_data = _read_json(paths.observations_raw_path)
        raw_data = normalize_raw_extraction(raw_data)
        return LoadedObservationArtifacts(
            mode="quote_first",
            raw_artifact=RawObservationArtifactV2.model_validate(raw_data),
            observations=None,
            spans=None,
            derivations=derivations,
        )

    if not canonical_exists:
        raise FileNotFoundError(
            f"Missing required canonical v2 artifact: {paths.observations_path}"
        )
    if not paths.spans_v2_path.exists():
        raise FileNotFoundError(
            f"Missing required canonical sidecar: {paths.spans_v2_path}"
        )
    return LoadedObservationArtifacts(
        mode="canonical",
        raw_artifact=None,
        observations=ObservationArtifactV2.model_validate(_read_json(paths.observations_path)),
        spans=SpanRegistryArtifact.model_validate(_read_json(paths.spans_v2_path)),
        derivations=derivations,
    )


def _load_optional_derivations(path: Path) -> DerivedArtifactV2 | None:
    if not path.exists():
        return None
    return DerivedArtifactV2.model_validate(_read_json(path))


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
