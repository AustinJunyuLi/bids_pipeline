"""Deterministic derivation engine for canonical v2 observation artifacts."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.extract_artifacts_v2 import load_observation_artifacts
from skill_pipeline.models import CoverageSummary
from skill_pipeline.models_v2 import (
    AgreementObservation,
    AnalystRowRecord,
    CashRegimeRecord,
    DerivationBasis,
    DerivedArtifactV2,
    GateReportV2,
    JudgmentRecord,
    LifecycleTransitionRecord,
    OutcomeObservation,
    PartyRecord,
    ProcessObservation,
    ProcessPhaseRecord,
    ProposalObservation,
    SkillCheckReportV2,
    SolicitationObservation,
    StatusObservation,
)
from skill_pipeline.paths import build_skill_paths, ensure_output_directories

PROCESS_EVENT_TYPES = {
    "sale_launch": {
        "target": "target_sale",
        "bidder": "bidder_sale",
        "activist": "activist_sale",
        "other": "target_sale",
    },
    "public_announcement": {
        "target": "target_sale_public",
        "bidder": "bid_press_release",
        "activist": "bid_press_release",
        "other": "target_sale_public",
    },
    "press_release": {
        "target": "sale_press_release",
        "bidder": "bid_press_release",
        "activist": "bid_press_release",
        "other": "sale_press_release",
    },
}
ROUND_EVENT_TYPES = {
    "informal": ("final_round_inf_ann", "final_round_inf"),
    "formal": ("final_round_ann", "final_round"),
    "extension": ("final_round_ext_ann", "final_round_ext"),
}
LITERAL_EXIT_KINDS = frozenset({"withdrew", "not_interested", "cannot_proceed"})


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(payload, "model_dump_json"):
        path.write_text(payload.model_dump_json(indent=2), encoding="utf-8")
        return
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _invalidate_outputs(paths) -> None:
    for path in (paths.derivations_path, paths.derive_log_path):
        if path.exists():
            path.unlink()


def _require_v2_gate_artifacts(paths) -> None:
    required = {
        "check-v2": paths.check_v2_report_path,
        "coverage-v2": paths.coverage_v2_summary_path,
        "gates-v2": paths.gates_v2_report_path,
    }
    for stage_name, path in required.items():
        if not path.exists():
            raise FileNotFoundError(f"Missing required input for derive: {path} ({stage_name})")

    check_report = SkillCheckReportV2.model_validate(_read_json(paths.check_v2_report_path))
    if check_report.summary.status != "pass":
        raise ValueError(f"Cannot run derive before check-v2 passes: {paths.check_v2_report_path}")

    coverage_summary = CoverageSummary.model_validate(_read_json(paths.coverage_v2_summary_path))
    if coverage_summary.status != "pass":
        raise ValueError(
            f"Cannot run derive before coverage-v2 passes: {paths.coverage_v2_summary_path}"
        )

    gates_report = GateReportV2.model_validate(_read_json(paths.gates_v2_report_path))
    if gates_report.summary.status != "pass":
        raise ValueError(f"Cannot run derive before gates-v2 passes: {paths.gates_v2_report_path}")


def _date_value(value) -> date | None:
    if value is None:
        return None
    sort_date = getattr(value, "sort_date", None)
    if sort_date is not None:
        return sort_date
    normalized_start = getattr(value, "normalized_start", None)
    if normalized_start is None:
        return None
    try:
        return date.fromisoformat(normalized_start)
    except ValueError:
        return None


def _date_fields(value) -> tuple[date | None, date | None]:
    if value is None:
        return None, None
    recorded = _date_value(value)
    if recorded is None:
        return None, None
    if getattr(value, "precision", None) == "exact_day":
        return recorded, recorded
    return recorded, None


def _basis(
    *,
    rule_id: str,
    source_observation_ids: list[str],
    source_span_ids: list[str],
    explanation: str,
    confidence: str = "high",
) -> DerivationBasis:
    return DerivationBasis(
        rule_id=rule_id,
        source_observation_ids=source_observation_ids,
        source_span_ids=source_span_ids,
        confidence=confidence,
        explanation=explanation,
    )


def _observation_sort_key(observation) -> tuple[date, str]:
    return (_date_value(observation.date) or date.max, observation.observation_id)


def _sorted_observations(observations: list) -> list:
    return sorted(observations, key=_observation_sort_key)


def _phase_kind_for_solicitation(observation: SolicitationObservation) -> str | None:
    attachments_text = " ".join(observation.attachments).lower()
    if observation.requested_submission == "ioi" or observation.binding_level == "non_binding":
        return "informal"
    if observation.requested_submission in {"loi", "binding_offer", "best_and_final"}:
        return "formal"
    if observation.binding_level in {"binding", "mixed"}:
        return "formal"
    if "merger agreement" in attachments_text or "markup" in attachments_text:
        return "formal"
    if observation.requested_submission == "other" or observation.binding_level == "other":
        return None
    return None


def _next_phase_boundary_observation_id(current, ordered_observations: list) -> str | None:
    seen_current = False
    for candidate in ordered_observations:
        if candidate.observation_id == current.observation_id:
            seen_current = True
            continue
        if not seen_current:
            continue
        if isinstance(candidate, (SolicitationObservation, OutcomeObservation)):
            return candidate.observation_id
    return None


def _derive_phases_and_judgments(artifacts) -> tuple[list[ProcessPhaseRecord], list[JudgmentRecord]]:
    observations = artifacts.observations
    if observations is None:
        return [], []

    ordered = _sorted_observations(observations.observations)
    phases: list[ProcessPhaseRecord] = []
    judgments: list[JudgmentRecord] = []
    for index, observation in enumerate(ordered, start=1):
        if not isinstance(observation, SolicitationObservation):
            continue
        phase_kind = _phase_kind_for_solicitation(observation)
        if phase_kind is None:
            judgments.append(
                JudgmentRecord(
                    judgment_id=f"judgment_{len(judgments) + 1:03d}",
                    judgment_kind="ambiguous_phase",
                    subject_ref=observation.observation_id,
                    note=(
                        "Solicitation could not be classified as informal or formal from "
                        "structured fields alone."
                    ),
                    basis=_basis(
                        rule_id="ROUND-UNRESOLVED",
                        source_observation_ids=[observation.observation_id],
                        source_span_ids=list(observation.evidence_span_ids),
                        explanation="Solicitation lacked deterministic round-classification fields.",
                        confidence="medium",
                    ),
                )
            )
            continue
        participant_refs = list(observation.recipient_refs or observation.subject_refs)
        phases.append(
            ProcessPhaseRecord(
                phase_id=f"phase_{index:03d}",
                phase_kind=phase_kind,
                start_observation_id=observation.observation_id,
                end_observation_id=_next_phase_boundary_observation_id(observation, ordered),
                participant_refs=participant_refs,
                basis=_basis(
                    rule_id="ROUND-01" if phase_kind == "informal" else "ROUND-02",
                    source_observation_ids=[observation.observation_id],
                    source_span_ids=list(observation.evidence_span_ids),
                    explanation=(
                        "Solicitation requested non-binding IOIs."
                        if phase_kind == "informal"
                        else "Solicitation requested LOIs/binding offers or carried formal attachments."
                    ),
                ),
            )
        )

    if not any(
        isinstance(observation, ProcessObservation)
        and observation.process_kind in {"sale_launch", "public_announcement"}
        for observation in observations.observations
    ):
        if any(
            isinstance(observation, (SolicitationObservation, ProposalObservation))
            for observation in observations.observations
        ):
            first_observation = ordered[0]
            judgments.append(
                JudgmentRecord(
                    judgment_id=f"judgment_{len(judgments) + 1:03d}",
                    judgment_kind="initiation",
                    subject_ref=None,
                    note="No explicit process-launch observation exists before bidding activity.",
                    basis=_basis(
                        rule_id="INITIATION-AMBIGUOUS",
                        source_observation_ids=[first_observation.observation_id],
                        source_span_ids=list(first_observation.evidence_span_ids),
                        explanation="Bidding activity appears without an explicit process-initiation observation.",
                        confidence="medium",
                    ),
                )
            )

    for party in observations.parties:
        if party.role == "advisor" and party.advised_party_id is None:
            judgments.append(
                JudgmentRecord(
                    judgment_id=f"judgment_{len(judgments) + 1:03d}",
                    judgment_kind="advisory_link",
                    subject_ref=party.party_id,
                    note="Advisor party lacks advised_party_id linkage.",
                    basis=_basis(
                        rule_id="ADVISORY-LINK-AMBIGUOUS",
                        source_observation_ids=[],
                        source_span_ids=list(party.evidence_span_ids),
                        explanation="Advisor linkage is missing from the literal party record.",
                        confidence="medium",
                    ),
                )
            )

    return phases, judgments


def _build_phase_index(phases: list[ProcessPhaseRecord]) -> dict[str, ProcessPhaseRecord]:
    return {phase.start_observation_id: phase for phase in phases}


def _latest_phase_for_observation(observation, phases: list[ProcessPhaseRecord], artifacts) -> ProcessPhaseRecord | None:
    if isinstance(observation, ProposalObservation) and observation.requested_by_observation_id:
        phase = _build_phase_index(phases).get(observation.requested_by_observation_id)
        if phase is not None:
            return phase

    observation_date = _date_value(observation.date)
    candidates: list[tuple[date, ProcessPhaseRecord]] = []
    observation_index = artifacts.observation_index
    for phase in phases:
        source = observation_index.get(phase.start_observation_id)
        if source is None:
            continue
        phase_date = _date_value(source.date)
        if phase_date is None:
            continue
        if observation_date is None or phase_date <= observation_date:
            candidates.append((phase_date, phase))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[-1][1]


def _derive_cash_regimes(artifacts, phases: list[ProcessPhaseRecord]) -> list[CashRegimeRecord]:
    observations = artifacts.observations
    if observations is None:
        return []

    cash_regimes: list[CashRegimeRecord] = []
    phase_lookup = {phase.phase_id: phase for phase in phases}
    proposals_by_phase: dict[str, list[ProposalObservation]] = {phase.phase_id: [] for phase in phases}
    merger_agreements_by_phase: dict[str, list[AgreementObservation]] = {phase.phase_id: [] for phase in phases}

    for observation in observations.observations:
        if isinstance(observation, ProposalObservation):
            phase = _latest_phase_for_observation(observation, phases, artifacts)
            if phase is not None:
                proposals_by_phase[phase.phase_id].append(observation)
        elif isinstance(observation, AgreementObservation) and observation.agreement_kind == "merger_agreement":
            phase = _latest_phase_for_observation(observation, phases, artifacts)
            if phase is not None:
                merger_agreements_by_phase[phase.phase_id].append(observation)

    for phase_id, phase in phase_lookup.items():
        proposals = proposals_by_phase.get(phase_id, [])
        agreements = merger_agreements_by_phase.get(phase_id, [])
        if not proposals and not agreements:
            continue

        typed_types = [
            proposal.terms.consideration_type
            for proposal in proposals
            if proposal.terms is not None and proposal.terms.consideration_type is not None
        ]
        untyped_proposals = [
            proposal for proposal in proposals if proposal.terms is None or proposal.terms.consideration_type is None
        ]
        agreement_cash = next(
            (
                agreement
                for agreement in agreements
                if agreement.consideration_type == "cash"
                or (agreement.consideration_type is None and "cash" in agreement.summary.lower())
            ),
            None,
        )

        rule_id = None
        regime = None
        source_observation_ids: list[str] = []
        source_span_ids: list[str] = []

        if agreement_cash is not None:
            rule_id = "CASH-02"
            regime = "all_cash"
            source_observation_ids = [agreement_cash.observation_id]
            source_span_ids = list(agreement_cash.evidence_span_ids)
        elif typed_types:
            if any(consideration_type != "cash" for consideration_type in typed_types):
                rule_id = "CASH-01"
                regime = "mixed"
            else:
                rule_id = "CASH-01"
                regime = "all_cash"
            source_observation_ids = [proposal.observation_id for proposal in proposals if proposal.terms is not None]
            source_span_ids = sorted(
                {
                    span_id
                    for proposal in proposals
                    for span_id in proposal.evidence_span_ids
                }
            )
        elif untyped_proposals:
            rule_id = "CASH-03"
            regime = "unknown"
            source_observation_ids = [proposal.observation_id for proposal in untyped_proposals]
            source_span_ids = sorted(
                {
                    span_id
                    for proposal in untyped_proposals
                    for span_id in proposal.evidence_span_ids
                }
            )

        if regime == "unknown" and agreement_cash is None and typed_types and all(
            consideration_type == "cash" for consideration_type in typed_types
        ):
            rule_id = "CASH-03"
            regime = "all_cash"

        if regime == "unknown" and typed_types and all(
            consideration_type == "cash" for consideration_type in typed_types
        ):
            regime = "all_cash"

        if regime is None:
            continue

        if regime == "unknown" and typed_types:
            regime = "mixed"

        if regime == "unknown" and not typed_types and not agreement_cash:
            continue

        if regime == "unknown":
            continue

        cash_regimes.append(
            CashRegimeRecord(
                cash_regime_id=f"cash_{len(cash_regimes) + 1:03d}",
                scope_kind="phase",
                scope_ref=phase.phase_id,
                regime=regime,
                basis=_basis(
                    rule_id=rule_id or "CASH-03",
                    source_observation_ids=source_observation_ids,
                    source_span_ids=source_span_ids,
                    explanation=(
                        "Cash merger agreement established an all-cash regime."
                        if rule_id == "CASH-02"
                        else (
                            "Explicit proposal consideration types set the phase cash regime."
                            if rule_id == "CASH-01"
                            else "Phase-level proposal evidence implied the cash regime."
                        )
                    ),
                ),
            )
        )

    return cash_regimes


def _subject_count(subject_ref: str, artifacts, *, default: int = 1) -> int:
    party = artifacts.party_index.get(subject_ref)
    if party is not None:
        return 1
    cohort = artifacts.cohort_index.get(subject_ref)
    if cohort is not None:
        return cohort.exact_count
    return default


def _from_state(subject_ref: str, prior_proposals: set[str], active_refs: set[str]) -> str:
    if subject_ref in prior_proposals:
        return "submitted"
    if subject_ref in active_refs:
        return "active"
    return "unknown"


def _build_transition(
    *,
    rule_id: str,
    reason_kind: str,
    subject_ref: str,
    subject_count: int,
    from_state: str,
    source_observation_ids: list[str],
    source_span_ids: list[str],
    explanation: str,
) -> LifecycleTransitionRecord:
    source_key = "-".join(source_observation_ids) if source_observation_ids else "no-source"
    return LifecycleTransitionRecord(
        transition_id=f"{rule_id.lower()}_{subject_ref}_{source_key}",
        subject_ref=subject_ref,
        subject_count=subject_count,
        from_state=from_state,
        to_state="inactive",
        reason_kind=reason_kind,
        basis=_basis(
            rule_id=rule_id,
            source_observation_ids=source_observation_ids,
            source_span_ids=source_span_ids,
            explanation=explanation,
        ),
    )


def _derive_transitions(
    artifacts,
    phases: list[ProcessPhaseRecord],
    judgments: list[JudgmentRecord],
) -> tuple[list[LifecycleTransitionRecord], list[JudgmentRecord]]:
    observations = artifacts.observations
    if observations is None:
        return [], judgments

    ordered = _sorted_observations(observations.observations)
    phase_by_start = _build_phase_index(phases)
    active_refs: set[str] = set()
    prior_proposals: set[str] = set()
    terminal_exit_refs: set[str] = set()
    transitions: list[LifecycleTransitionRecord] = []
    judgment_list = list(judgments)

    for observation in ordered:
        if isinstance(observation, SolicitationObservation):
            active_refs.update(observation.recipient_refs)
            continue

        if isinstance(observation, ProposalObservation):
            active_refs.update(observation.subject_refs)
            prior_proposals.update(observation.subject_refs)
            continue

        if isinstance(observation, AgreementObservation) and observation.agreement_kind == "nda":
            active_refs.update(observation.subject_refs)
            continue

        if isinstance(observation, StatusObservation):
            if observation.status_kind in LITERAL_EXIT_KINDS:
                for subject_ref in observation.subject_refs:
                    transitions.append(
                        _build_transition(
                            rule_id="EXIT-01",
                            reason_kind="literal",
                            subject_ref=subject_ref,
                            subject_count=_subject_count(subject_ref, artifacts),
                            from_state=_from_state(subject_ref, prior_proposals, active_refs),
                            source_observation_ids=[observation.observation_id],
                            source_span_ids=list(observation.evidence_span_ids),
                            explanation="Literal status observation recorded bidder withdrawal or non-participation.",
                        )
                    )
                    active_refs.discard(subject_ref)
                    terminal_exit_refs.add(subject_ref)
                continue

            if observation.status_kind == "cannot_improve":
                for subject_ref in observation.subject_refs:
                    if subject_ref not in prior_proposals:
                        judgment_list.append(
                            JudgmentRecord(
                                judgment_id=f"judgment_{len(judgment_list) + 1:03d}",
                                judgment_kind="ambiguous_exit",
                                subject_ref=subject_ref,
                                note="cannot_improve status lacks a prior proposal to ground the exit state.",
                                basis=_basis(
                                    rule_id="EXIT-02-UNRESOLVED",
                                    source_observation_ids=[observation.observation_id],
                                    source_span_ids=list(observation.evidence_span_ids),
                                    explanation="Cannot-improve status appeared without prior proposal evidence.",
                                    confidence="medium",
                                ),
                            )
                        )
                        continue
                    transitions.append(
                        _build_transition(
                            rule_id="EXIT-02",
                            reason_kind="cannot_improve",
                            subject_ref=subject_ref,
                            subject_count=_subject_count(subject_ref, artifacts),
                            from_state=_from_state(subject_ref, prior_proposals, active_refs),
                            source_observation_ids=[observation.observation_id],
                            source_span_ids=list(observation.evidence_span_ids),
                            explanation="Status observation explicitly said the bidder could not improve.",
                        )
                    )
                    active_refs.discard(subject_ref)
                    terminal_exit_refs.add(subject_ref)
                continue

            if observation.status_kind == "selected_to_advance":
                pool_refs = set(active_refs)
                if observation.related_observation_id:
                    related_phase = phase_by_start.get(observation.related_observation_id)
                    if related_phase is not None:
                        pool_refs.update(related_phase.participant_refs)
                    related_observation = artifacts.observation_index.get(observation.related_observation_id)
                    if isinstance(related_observation, SolicitationObservation):
                        pool_refs.update(related_observation.recipient_refs)
                selected_refs = set(observation.subject_refs)
                for subject_ref in sorted(ref for ref in pool_refs if ref not in selected_refs):
                    transitions.append(
                        _build_transition(
                            rule_id="EXIT-03",
                            reason_kind="not_invited",
                            subject_ref=subject_ref,
                            subject_count=_subject_count(subject_ref, artifacts),
                            from_state=_from_state(subject_ref, prior_proposals, active_refs),
                            source_observation_ids=[observation.observation_id],
                            source_span_ids=list(observation.evidence_span_ids),
                            explanation="Selected-to-advance observation omitted an otherwise active subject.",
                        )
                    )
                    active_refs.discard(subject_ref)
                active_refs.update(selected_refs)
                continue

        if isinstance(observation, OutcomeObservation):
            if observation.outcome_kind == "restarted":
                active_refs.clear()
                prior_proposals.clear()
                continue

            if observation.outcome_kind == "executed":
                winner_ref = next(
                    (
                        ref
                        for ref in observation.counterparty_refs + observation.subject_refs
                        if ref in artifacts.party_index and artifacts.party_index[ref].role == "bidder"
                    ),
                    None,
                )
                if winner_ref is None:
                    winner_ref = next(
                        (
                            ref
                            for ref in observation.counterparty_refs + observation.subject_refs
                            if ref in artifacts.cohort_index
                        ),
                        None,
                    )
                if winner_ref is not None:
                    losing_refs = (active_refs | prior_proposals) - {winner_ref} - terminal_exit_refs
                    for subject_ref in sorted(losing_refs):
                        transitions.append(
                            _build_transition(
                                rule_id="EXIT-04",
                                reason_kind="lost_to_winner",
                                subject_ref=subject_ref,
                                subject_count=_subject_count(subject_ref, artifacts),
                                from_state=_from_state(subject_ref, prior_proposals, active_refs),
                                source_observation_ids=[observation.observation_id],
                                source_span_ids=list(observation.evidence_span_ids),
                                explanation="Execution outcome closed out remaining active bidders in favor of the winner.",
                            )
                        )
                    active_refs = {winner_ref}
                continue

            if observation.outcome_kind == "terminated":
                active_refs.clear()

    return transitions, judgment_list


def _subject_name(subject_ref: str | None, artifacts) -> str | None:
    if subject_ref is None:
        return None
    party = artifacts.party_index.get(subject_ref)
    if party is not None:
        return party.display_name
    cohort = artifacts.cohort_index.get(subject_ref)
    if cohort is not None:
        return cohort.label
    return None


def _single_bidder_type(party: PartyRecord | None) -> str | None:
    if party is None or party.role != "bidder":
        return None
    if party.geography == "non_us" and party.listing_status == "public" and party.bidder_kind == "strategic":
        return "non-US public S"
    if party.geography == "non_us" and party.listing_status == "public" and party.bidder_kind == "financial":
        return "non-US public F"
    if party.geography == "non_us" and party.bidder_kind == "strategic":
        return "non-US S"
    if party.geography == "non_us" and party.bidder_kind == "financial":
        return "non-US F"
    if party.listing_status == "public" and party.bidder_kind == "strategic":
        return "public S"
    if party.listing_status == "public" and party.bidder_kind == "financial":
        return "public F"
    if party.bidder_kind == "strategic":
        return "S"
    if party.bidder_kind == "financial":
        return "F"
    return None


def _subject_bidder_type(subject_ref: str | None, artifacts) -> str | None:
    if subject_ref is None:
        return None
    party = artifacts.party_index.get(subject_ref)
    if party is not None:
        return _single_bidder_type(party)
    return None


def _origin(subject_ref: str | None, *, derived: bool, artifacts) -> str:
    if subject_ref is not None and subject_ref in artifacts.cohort_index:
        return "synthetic_anonymous"
    return "derived" if derived else "literal"


def _append_row(rows: list[AnalystRowRecord], **kwargs) -> None:
    rows.append(
        AnalystRowRecord(
            row_id=f"row_{len(rows) + 1:04d}",
            **kwargs,
        )
    )


def _phase_bid_type(phase_kind: str) -> str | None:
    if phase_kind == "formal":
        return "Formal"
    if phase_kind in {"informal", "extension"}:
        return "Informal"
    return "Uncertain"


def _phase_cash_map(cash_regimes: list[CashRegimeRecord]) -> dict[str, bool | None]:
    result: dict[str, bool | None] = {}
    for regime in cash_regimes:
        if regime.scope_kind != "phase":
            continue
        if regime.regime == "all_cash":
            result[regime.scope_ref] = True
        elif regime.regime == "mixed":
            result[regime.scope_ref] = False
        else:
            result[regime.scope_ref] = None
    return result


def _compile_literal_rows(artifacts, phases: list[ProcessPhaseRecord], cash_regimes: list[CashRegimeRecord]) -> list[AnalystRowRecord]:
    observations = artifacts.observations
    if observations is None:
        return []
    rows: list[AnalystRowRecord] = []
    phase_cash = _phase_cash_map(cash_regimes)
    phase_by_start = _build_phase_index(phases)

    for observation in _sorted_observations(observations.observations):
        if isinstance(observation, ProcessObservation):
            if observation.process_kind == "advisor_retention":
                event_type = "ib_retention"
            else:
                scope = observation.process_scope or "other"
                event_type = PROCESS_EVENT_TYPES.get(observation.process_kind, {}).get(scope)
            if event_type is None:
                continue
            subjects = observation.subject_refs or [None]
            for subject_ref in subjects:
                recorded, public = _date_fields(observation.date)
                _append_row(
                    rows,
                    origin=_origin(subject_ref, derived=False, artifacts=artifacts),
                    analyst_event_type=event_type,
                    subject_ref=subject_ref,
                    row_count=_subject_count(subject_ref, artifacts),
                    bidder_name=_subject_name(subject_ref, artifacts),
                    bidder_type=_subject_bidder_type(subject_ref, artifacts),
                    date_recorded=recorded,
                    date_public=public,
                    basis=_basis(
                        rule_id="LITERAL-PROCESS",
                        source_observation_ids=[observation.observation_id],
                        source_span_ids=list(observation.evidence_span_ids),
                        explanation="Literal process observation compiled directly into analyst row.",
                    ),
                )
            continue

        if isinstance(observation, AgreementObservation):
            if observation.agreement_kind not in {"nda", "amendment", "standstill", "exclusivity", "clean_team"}:
                continue
            subjects = observation.subject_refs or [None]
            for subject_ref in subjects:
                recorded, public = _date_fields(observation.date)
                review_flags = []
                if observation.supersedes_observation_id:
                    review_flags.append(f"supersedes:{observation.supersedes_observation_id}")
                _append_row(
                    rows,
                    origin=_origin(subject_ref, derived=False, artifacts=artifacts),
                    analyst_event_type="nda",
                    subject_ref=subject_ref,
                    row_count=_subject_count(subject_ref, artifacts),
                    bidder_name=_subject_name(subject_ref, artifacts),
                    bidder_type=_subject_bidder_type(subject_ref, artifacts),
                    date_recorded=recorded,
                    date_public=public,
                    review_flags=review_flags,
                    basis=_basis(
                        rule_id="AGREEMENT-01" if observation.supersedes_observation_id else "LITERAL-AGREEMENT",
                        source_observation_ids=[observation.observation_id],
                        source_span_ids=list(observation.evidence_span_ids),
                        explanation="Literal agreement observation compiled into NDA-family analyst row.",
                    ),
                )
            continue

        if isinstance(observation, ProposalObservation):
            phase = phase_by_start.get(observation.requested_by_observation_id or "")
            if phase is None:
                phase = _latest_phase_for_observation(observation, phases, artifacts)
            proposal_cash = None
            if observation.terms is not None and observation.terms.consideration_type is not None:
                proposal_cash = observation.terms.consideration_type == "cash"
            elif phase is not None:
                proposal_cash = phase_cash.get(phase.phase_id)
            bid_type = _phase_bid_type(phase.phase_kind) if phase is not None else "Uncertain"
            subjects = observation.subject_refs or [None]
            for subject_ref in subjects:
                recorded, public = _date_fields(observation.date)
                _append_row(
                    rows,
                    origin=_origin(subject_ref, derived=False, artifacts=artifacts),
                    analyst_event_type="proposal",
                    subject_ref=subject_ref,
                    row_count=_subject_count(subject_ref, artifacts),
                    bidder_name=_subject_name(subject_ref, artifacts),
                    bidder_type=_subject_bidder_type(subject_ref, artifacts),
                    bid_type=bid_type,
                    value=observation.terms.per_share if observation.terms else None,
                    range_low=observation.terms.range_low if observation.terms else None,
                    range_high=observation.terms.range_high if observation.terms else None,
                    date_recorded=recorded,
                    date_public=public,
                    all_cash=proposal_cash,
                    basis=_basis(
                        rule_id="LITERAL-PROPOSAL",
                        source_observation_ids=[observation.observation_id],
                        source_span_ids=list(observation.evidence_span_ids),
                        explanation="Literal proposal observation compiled directly into analyst row.",
                    ),
                )
            continue

        if isinstance(observation, OutcomeObservation):
            if observation.outcome_kind not in {"executed", "terminated", "restarted"}:
                continue
            subject_ref = next(
                (
                    ref
                    for ref in observation.counterparty_refs + observation.subject_refs
                    if ref in artifacts.party_index or ref in artifacts.cohort_index
                ),
                None,
            )
            recorded, public = _date_fields(observation.date)
            _append_row(
                rows,
                origin=_origin(subject_ref, derived=False, artifacts=artifacts),
                analyst_event_type=observation.outcome_kind,
                subject_ref=subject_ref,
                row_count=_subject_count(subject_ref, artifacts),
                bidder_name=_subject_name(subject_ref, artifacts),
                bidder_type=_subject_bidder_type(subject_ref, artifacts),
                date_recorded=recorded,
                date_public=public,
                basis=_basis(
                    rule_id="LITERAL-OUTCOME",
                    source_observation_ids=[observation.observation_id],
                    source_span_ids=list(observation.evidence_span_ids),
                    explanation="Literal outcome observation compiled directly into analyst row.",
                ),
            )

    return rows


def _compile_phase_rows(artifacts, phases: list[ProcessPhaseRecord], cash_regimes: list[CashRegimeRecord]) -> list[AnalystRowRecord]:
    rows: list[AnalystRowRecord] = []
    phase_cash = _phase_cash_map(cash_regimes)
    observation_index = artifacts.observation_index
    for phase in phases:
        event_types = ROUND_EVENT_TYPES.get(phase.phase_kind)
        source = observation_index.get(phase.start_observation_id)
        if event_types is None or not isinstance(source, SolicitationObservation):
            continue
        announcement_type, deadline_type = event_types
        participants = phase.participant_refs or [None]
        for subject_ref in participants:
            recorded, public = _date_fields(source.date)
            _append_row(
                rows,
                origin=_origin(subject_ref, derived=True, artifacts=artifacts),
                analyst_event_type=announcement_type,
                subject_ref=subject_ref,
                row_count=_subject_count(subject_ref, artifacts),
                bidder_name=_subject_name(subject_ref, artifacts),
                bidder_type=_subject_bidder_type(subject_ref, artifacts),
                bid_type=_phase_bid_type(phase.phase_kind),
                date_recorded=recorded,
                date_public=public,
                all_cash=phase_cash.get(phase.phase_id),
                basis=phase.basis,
            )
            due_recorded, due_public = _date_fields(source.due_date)
            if due_recorded is None:
                continue
            _append_row(
                rows,
                origin=_origin(subject_ref, derived=True, artifacts=artifacts),
                analyst_event_type=deadline_type,
                subject_ref=subject_ref,
                row_count=_subject_count(subject_ref, artifacts),
                bidder_name=_subject_name(subject_ref, artifacts),
                bidder_type=_subject_bidder_type(subject_ref, artifacts),
                bid_type=_phase_bid_type(phase.phase_kind),
                date_recorded=due_recorded,
                date_public=due_public,
                all_cash=phase_cash.get(phase.phase_id),
                basis=phase.basis,
            )
    return rows


def _compile_transition_rows(artifacts, transitions: list[LifecycleTransitionRecord]) -> list[AnalystRowRecord]:
    rows: list[AnalystRowRecord] = []
    observation_index = artifacts.observation_index
    for transition in transitions:
        source_observation = next(
            (
                observation_index.get(observation_id)
                for observation_id in transition.basis.source_observation_ids
                if observation_index.get(observation_id) is not None
            ),
            None,
        )
        recorded, public = _date_fields(getattr(source_observation, "date", None))
        review_flags = []
        if transition.reason_kind != "literal":
            review_flags.append(f"reason:{transition.reason_kind}")
        _append_row(
            rows,
            origin=(
                "literal"
                if transition.basis.rule_id == "EXIT-01" and transition.subject_ref not in artifacts.cohort_index
                else _origin(transition.subject_ref, derived=True, artifacts=artifacts)
            ),
            analyst_event_type="drop",
            subject_ref=transition.subject_ref,
            row_count=transition.subject_count,
            bidder_name=_subject_name(transition.subject_ref, artifacts),
            bidder_type=_subject_bidder_type(transition.subject_ref, artifacts),
            date_recorded=recorded,
            date_public=public,
            review_flags=review_flags,
            basis=transition.basis,
        )
    return rows


def run_derive(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    """Run deterministic v2 derivation and write derive artifacts."""
    paths = build_skill_paths(deal_slug, project_root=project_root)
    _invalidate_outputs(paths)
    _require_v2_gate_artifacts(paths)

    artifacts = load_observation_artifacts(paths, mode="canonical")
    phases, judgments = _derive_phases_and_judgments(artifacts)
    cash_regimes = _derive_cash_regimes(artifacts, phases)
    transitions, judgments = _derive_transitions(artifacts, phases, judgments)

    analyst_rows: list[AnalystRowRecord] = []
    analyst_rows.extend(_compile_literal_rows(artifacts, phases, cash_regimes))
    analyst_rows.extend(_compile_phase_rows(artifacts, phases, cash_regimes))
    analyst_rows.extend(_compile_transition_rows(artifacts, transitions))

    artifact = DerivedArtifactV2(
        phases=phases,
        transitions=transitions,
        cash_regimes=cash_regimes,
        judgments=judgments,
        analyst_rows=analyst_rows,
    )

    log_payload = {
        "rule_order": [
            "ROUND-01",
            "ROUND-02",
            "EXIT-01",
            "EXIT-02",
            "EXIT-03",
            "EXIT-04",
            "AGREEMENT-01",
            "CASH-01",
            "CASH-02",
            "CASH-03",
        ],
        "validation_gate": {
            "check_v2": str(paths.check_v2_report_path),
            "coverage_v2": str(paths.coverage_v2_summary_path),
            "gates_v2": str(paths.gates_v2_report_path),
            "verify_policy": "not_required_until_shared_v2_verify_exists",
        },
        "output_counts": {
            "phases": len(phases),
            "transitions": len(transitions),
            "cash_regimes": len(cash_regimes),
            "judgments": len(judgments),
            "analyst_rows": len(analyst_rows),
        },
    }

    ensure_output_directories(paths)
    _write_json(paths.derivations_path, artifact)
    _write_json(paths.derive_log_path, log_payload)
    return 0
