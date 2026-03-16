from __future__ import annotations

from collections.abc import Iterable

from pipeline.models.common import ClassificationLabel, EventType
from pipeline.models.enrichment import ProposalClassification
from pipeline.models.extraction import DealExtraction, ProposalEvent, RoundEvent


RULE_VERSION = "2026-03-16-v1"


def classify_proposals(
    extraction: DealExtraction,
    *,
    ordered_events: Iterable | None = None,
) -> dict[str, ProposalClassification]:
    """Deterministically classify proposal events as formal/informal/uncertain.

    The cascade follows the v2/v3 design: explicit informal indicators and ranges
    dominate, then explicit binding-package indicators, then round context.
    """

    events = list(ordered_events) if ordered_events is not None else list(extraction.events)
    classifications: dict[str, ProposalClassification] = {}
    last_round_event: RoundEvent | None = None

    for event in events:
        if isinstance(event, RoundEvent):
            last_round_event = event
            continue
        if not isinstance(event, ProposalEvent):
            continue

        signals = event.formality_signals
        terms = event.terms

        if terms.is_range:
            classifications[event.event_id] = ProposalClassification(
                label=ClassificationLabel.INFORMAL,
                rule_id="I1_range_bid",
                rule_version=RULE_VERSION,
                note="Range bids are informal under Alex's instructions.",
            )
            continue

        if (
            signals.mentions_indication_of_interest
            or signals.mentions_preliminary
            or signals.mentions_non_binding
        ):
            classifications[event.event_id] = ProposalClassification(
                label=ClassificationLabel.INFORMAL,
                rule_id="I2_explicit_informal_language",
                rule_version=RULE_VERSION,
                note="Proposal carries explicit informal / non-binding language.",
            )
            continue

        if (
            signals.includes_draft_merger_agreement
            or signals.includes_marked_up_agreement
            or signals.mentions_binding_offer
        ):
            classifications[event.event_id] = ProposalClassification(
                label=ClassificationLabel.FORMAL,
                rule_id="F1_binding_package",
                rule_version=RULE_VERSION,
                note="Proposal includes explicit binding-package signals.",
            )
            continue

        if (
            signals.requested_binding_offer_via_process_letter
            or signals.after_final_round_deadline
            or signals.after_final_round_announcement
        ):
            classifications[event.event_id] = ProposalClassification(
                label=ClassificationLabel.FORMAL,
                rule_id="F2_formal_round_signal",
                rule_version=RULE_VERSION,
                note="Proposal occurs in explicit final binding round context.",
            )
            continue

        if last_round_event is not None:
            if last_round_event.event_type in {EventType.FINAL_ROUND_INF_ANN, EventType.FINAL_ROUND_INF}:
                classifications[event.event_id] = ProposalClassification(
                    label=ClassificationLabel.INFORMAL,
                    rule_id="I3_informal_round_context",
                    rule_version=RULE_VERSION,
                    note="Proposal follows an informal final-round event.",
                )
                continue
            if last_round_event.event_type in {
                EventType.FINAL_ROUND_ANN,
                EventType.FINAL_ROUND,
                EventType.FINAL_ROUND_EXT_ANN,
                EventType.FINAL_ROUND_EXT,
            }:
                classifications[event.event_id] = ProposalClassification(
                    label=ClassificationLabel.FORMAL,
                    rule_id="F3_formal_round_context",
                    rule_version=RULE_VERSION,
                    note="Proposal follows a formal-round announcement or deadline.",
                )
                continue

        classifications[event.event_id] = ProposalClassification(
            label=ClassificationLabel.UNCERTAIN,
            rule_id="U1_residual",
            rule_version=RULE_VERSION,
            note="No deterministic formality rule fired.",
        )

    return classifications
