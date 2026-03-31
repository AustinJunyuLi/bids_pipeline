from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.extract_artifacts import LoadedExtractArtifacts
from skill_pipeline.extract_artifacts_v2 import RawObservationArtifactV2
from skill_pipeline.models import QuoteEntry
from skill_pipeline.paths import build_skill_paths, ensure_output_directories
from skill_pipeline.extract_artifacts import load_extract_artifacts


ROUND_ANNOUNCEMENT_TYPES = {
    "final_round_inf_ann": {
        "deadline_type": "final_round_inf",
        "requested_submission": "ioi",
        "binding_level": "non_binding",
        "phase_kind": "informal",
    },
    "final_round_ann": {
        "deadline_type": "final_round",
        "requested_submission": "best_and_final",
        "binding_level": "binding",
        "phase_kind": "formal",
    },
    "final_round_ext_ann": {
        "deadline_type": "final_round_ext",
        "requested_submission": "best_and_final",
        "binding_level": "binding",
        "phase_kind": "extension",
    },
}
ROUND_DEADLINE_TYPES = {
    "final_round_inf": {
        "requested_submission": "ioi",
        "binding_level": "non_binding",
        "phase_kind": "informal",
    },
    "final_round": {
        "requested_submission": "best_and_final",
        "binding_level": "binding",
        "phase_kind": "formal",
    },
    "final_round_ext": {
        "requested_submission": "best_and_final",
        "binding_level": "binding",
        "phase_kind": "extension",
    },
}
PROCESS_EVENT_MAP = {
    "target_sale": ("sale_launch", "target"),
    "target_sale_public": ("public_announcement", "target"),
    "bidder_sale": ("sale_launch", "bidder"),
    "activist_sale": ("sale_launch", "activist"),
    "sale_press_release": ("press_release", "target"),
    "bid_press_release": ("press_release", "bidder"),
    "ib_retention": ("advisor_retention", "target"),
}


@dataclass
class _MigrationContext:
    artifacts: LoadedExtractArtifacts
    quotes: list[QuoteEntry]
    quote_ids_by_span_id: dict[str, str]
    grouped_actor_ids: set[str]
    actor_index: dict[str, object]
    observations: list[dict]
    observation_ids_by_event_id: dict[str, str]


def _quote_ids_for_span_ids(context: _MigrationContext, span_ids: list[str]) -> list[str]:
    quote_ids: list[str] = []
    seen: set[str] = set()
    for span_id in span_ids:
        if span_id in seen:
            continue
        seen.add(span_id)
        quote_id = context.quote_ids_by_span_id.get(span_id)
        if quote_id is None:
            span = context.artifacts.span_index.get(span_id)
            if span is None:
                raise ValueError(f"Unknown v1 span reference during migration: {span_id}")
            if not span.block_ids:
                raise ValueError(f"Span {span_id!r} has no block_ids; cannot create quote-first v2 artifact.")
            quote_id = f"Q{len(context.quotes) + 1:04d}"
            context.quotes.append(
                QuoteEntry(
                    quote_id=quote_id,
                    block_id=span.block_ids[0],
                    text=span.quote_text,
                )
            )
            context.quote_ids_by_span_id[span_id] = quote_id
        quote_ids.append(quote_id)
    return quote_ids


def _map_actor_ref(context: _MigrationContext, actor_id: str) -> str:
    return actor_id if actor_id in context.actor_index else actor_id


def _actor_role(context: _MigrationContext, actor_id: str) -> str | None:
    actor = context.actor_index.get(actor_id)
    return getattr(actor, "role", None)


def _filter_actor_refs(
    context: _MigrationContext,
    actor_ids: list[str],
    *,
    roles: set[str] | None = None,
    include_grouped_bidders: bool = False,
) -> list[str]:
    refs: list[str] = []
    seen: set[str] = set()
    for actor_id in actor_ids:
        role = _actor_role(context, actor_id)
        grouped_bidder = actor_id in context.grouped_actor_ids
        if roles is not None and role not in roles and not (include_grouped_bidders and grouped_bidder):
            continue
        ref = _map_actor_ref(context, actor_id)
        if ref in seen:
            continue
        seen.add(ref)
        refs.append(ref)
    return refs


def _event_date_payload(event) -> dict | None:
    if event.date is None:
        return None
    return event.date.model_dump(mode="json")


def _due_date_payload(event, paired_deadline) -> dict | None:
    if paired_deadline is not None:
        return paired_deadline.date.model_dump(mode="json")
    if getattr(event, "deadline_date", None) is not None:
        return event.deadline_date.model_dump(mode="json")
    return None


def _latest_solicitation_id_before(context: _MigrationContext, index: int) -> str | None:
    for observation in reversed(context.observations[:index]):
        if observation["obs_type"] == "solicitation":
            return observation["observation_id"]
    return None


def _infer_delivery_mode(summary: str, notes: list[str]) -> str | None:
    text = f"{summary} {' '.join(notes)}".lower()
    if "oral" in text or "verbally" in text or "verbal" in text:
        return "oral"
    if " email" in text or text.startswith("email") or "e-mail" in text:
        return "email"
    if "telephone" in text or "phone" in text or "telephonic" in text:
        return "phone"
    if "written" in text or "letter" in text:
        return "written"
    return None


def _infer_status_kind(drop_reason_text: str | None, summary: str) -> str:
    text = f"{drop_reason_text or ''} {summary}".lower()
    if "limited, select assets" in text or "limited assets only" in text:
        return "limited_assets_only"
    if "not meaningfully higher" in text or "significantly below" in text or "could not improve" in text:
        return "cannot_improve"
    if "did not submit" in text or "declined the invitation" in text:
        return "excluded"
    if "not proceed" in text or "move forward" in text or "disengaging" in text:
        return "cannot_proceed"
    if "no longer interested" in text or "not interested" in text or "declined interest" in text:
        return "not_interested"
    return "withdrew"


def _build_round_observations(context: _MigrationContext) -> set[str]:
    used_event_ids: set[str] = set()
    events = list(context.artifacts.events.events)

    for index, event in enumerate(events):
        if event.event_type not in ROUND_ANNOUNCEMENT_TYPES:
            continue
        config = ROUND_ANNOUNCEMENT_TYPES[event.event_type]
        paired_deadline = next(
            (
                candidate
                for candidate in events[index + 1 :]
                if candidate.event_id not in used_event_ids
                and candidate.event_type == config["deadline_type"]
            ),
            None,
        )
        used_event_ids.add(event.event_id)
        if paired_deadline is not None:
            used_event_ids.add(paired_deadline.event_id)

        observation_id = f"obs_{event.event_id}"
        quote_ids = _quote_ids_for_span_ids(
            context,
            list(event.evidence_span_ids)
            + list(getattr(paired_deadline, "evidence_span_ids", []) or []),
        )
        other_detail = "extension round" if config["phase_kind"] == "extension" else None
        context.observations.append(
            {
                "observation_id": observation_id,
                "obs_type": "solicitation",
                "date": _event_date_payload(event),
                "subject_refs": [],
                "counterparty_refs": [],
                "summary": event.summary,
                "quote_ids": quote_ids,
                "requested_submission": config["requested_submission"],
                "binding_level": config["binding_level"],
                "due_date": _due_date_payload(event, paired_deadline),
                "recipient_refs": [],
                "attachments": [],
                "other_detail": other_detail,
            }
        )
        context.observation_ids_by_event_id[event.event_id] = observation_id
        if paired_deadline is not None:
            context.observation_ids_by_event_id[paired_deadline.event_id] = observation_id

        invited_refs = _filter_actor_refs(
            context,
            list(event.invited_actor_ids),
            roles={"bidder"},
            include_grouped_bidders=True,
        )
        if invited_refs:
            context.observations.append(
                {
                    "observation_id": f"{observation_id}_selected",
                    "obs_type": "status",
                    "date": _event_date_payload(event),
                    "subject_refs": invited_refs,
                    "counterparty_refs": [],
                    "summary": event.summary,
                    "quote_ids": _quote_ids_for_span_ids(context, list(event.evidence_span_ids)),
                    "status_kind": "selected_to_advance",
                    "related_observation_id": observation_id,
                    "other_detail": None,
                }
            )

    for event in events:
        if event.event_id in used_event_ids or event.event_type not in ROUND_DEADLINE_TYPES:
            continue
        config = ROUND_DEADLINE_TYPES[event.event_type]
        observation_id = f"obs_{event.event_id}"
        context.observations.append(
            {
                "observation_id": observation_id,
                "obs_type": "solicitation",
                "date": _event_date_payload(event),
                "subject_refs": [],
                "counterparty_refs": [],
                "summary": event.summary,
                "quote_ids": _quote_ids_for_span_ids(context, list(event.evidence_span_ids)),
                "requested_submission": config["requested_submission"],
                "binding_level": config["binding_level"],
                "due_date": _event_date_payload(event),
                "recipient_refs": [],
                "attachments": [],
                "other_detail": "extension round" if config["phase_kind"] == "extension" else None,
            }
        )
        context.observation_ids_by_event_id[event.event_id] = observation_id
        used_event_ids.add(event.event_id)

    return used_event_ids


def _build_non_round_observations(context: _MigrationContext, used_event_ids: set[str]) -> None:
    latest_proposal_by_subject: dict[tuple[str, ...], str] = {}

    for event in context.artifacts.events.events:
        if event.event_id in used_event_ids:
            continue

        observation_id = f"obs_{event.event_id}"
        quote_ids = _quote_ids_for_span_ids(context, list(event.evidence_span_ids))
        bidder_refs = _filter_actor_refs(
            context,
            list(event.actor_ids),
            roles={"bidder"},
            include_grouped_bidders=True,
        )
        advisor_refs = _filter_actor_refs(context, list(event.actor_ids), roles={"advisor"})
        activist_refs = _filter_actor_refs(context, list(event.actor_ids), roles={"activist"})
        target_refs = _filter_actor_refs(context, list(event.actor_ids), roles={"target_board"})

        if event.event_type in PROCESS_EVENT_MAP:
            process_kind, process_scope = PROCESS_EVENT_MAP[event.event_type]
            if event.event_type == "ib_retention":
                subject_refs = advisor_refs or [
                    _map_actor_ref(context, actor_id)
                    for actor_id in event.actor_ids
                ]
            elif event.event_type == "bid_press_release":
                subject_refs = bidder_refs
            elif event.event_type in {"bidder_sale", "activist_sale"}:
                subject_refs = bidder_refs or activist_refs
            else:
                subject_refs = []
            context.observations.append(
                {
                    "observation_id": observation_id,
                    "obs_type": "process",
                    "date": _event_date_payload(event),
                    "subject_refs": subject_refs,
                    "counterparty_refs": [],
                    "summary": event.summary,
                    "quote_ids": quote_ids,
                    "process_kind": process_kind,
                    "process_scope": process_scope,
                    "other_detail": None,
                }
            )
            context.observation_ids_by_event_id[event.event_id] = observation_id
            continue

        if event.event_type == "bidder_interest":
            context.observations.append(
                {
                    "observation_id": observation_id,
                    "obs_type": "status",
                    "date": _event_date_payload(event),
                    "subject_refs": bidder_refs,
                    "counterparty_refs": advisor_refs,
                    "summary": event.summary,
                    "quote_ids": quote_ids,
                    "status_kind": "expressed_interest",
                    "related_observation_id": None,
                    "other_detail": None,
                }
            )
            context.observation_ids_by_event_id[event.event_id] = observation_id
            continue

        if event.event_type == "nda":
            context.observations.append(
                {
                    "observation_id": observation_id,
                    "obs_type": "agreement",
                    "date": _event_date_payload(event),
                    "subject_refs": bidder_refs or advisor_refs or target_refs,
                    "counterparty_refs": [],
                    "summary": event.summary,
                    "quote_ids": quote_ids,
                    "agreement_kind": "nda",
                    "signed": True if event.nda_signed is None else event.nda_signed,
                    "grants_diligence_access": True,
                    "includes_standstill": None,
                    "consideration_type": None,
                    "supersedes_observation_id": None,
                    "other_detail": None,
                }
            )
            context.observation_ids_by_event_id[event.event_id] = observation_id
            continue

        if event.event_type == "proposal":
            subject_refs = bidder_refs or [
                _map_actor_ref(context, actor_id)
                for actor_id in event.actor_ids
            ]
            key = tuple(subject_refs)
            requested_by = _latest_solicitation_id_before(context, len(context.observations))
            context.observations.append(
                {
                    "observation_id": observation_id,
                    "obs_type": "proposal",
                    "date": _event_date_payload(event),
                    "subject_refs": subject_refs,
                    "counterparty_refs": [],
                    "summary": event.summary,
                    "quote_ids": quote_ids,
                    "requested_by_observation_id": requested_by,
                    "revises_observation_id": latest_proposal_by_subject.get(key),
                    "delivery_mode": _infer_delivery_mode(event.summary, list(event.notes)),
                    "terms": event.terms.model_dump(mode="json") if event.terms is not None else None,
                    "mentions_non_binding": (
                        event.formality_signals.mentions_non_binding
                        if event.formality_signals is not None
                        else None
                    ),
                    "includes_draft_merger_agreement": (
                        event.formality_signals.includes_draft_merger_agreement
                        if event.formality_signals is not None
                        else None
                    ),
                    "includes_markup": (
                        event.formality_signals.includes_marked_up_agreement
                        if event.formality_signals is not None
                        else None
                    ),
                    "other_detail": None,
                }
            )
            latest_proposal_by_subject[key] = observation_id
            context.observation_ids_by_event_id[event.event_id] = observation_id
            continue

        if event.event_type == "drop":
            context.observations.append(
                {
                    "observation_id": observation_id,
                    "obs_type": "status",
                    "date": _event_date_payload(event),
                    "subject_refs": bidder_refs,
                    "counterparty_refs": [],
                    "summary": event.summary,
                    "quote_ids": quote_ids,
                    "status_kind": _infer_status_kind(event.drop_reason_text, event.summary),
                    "related_observation_id": None,
                    "other_detail": event.drop_reason_text,
                }
            )
            context.observation_ids_by_event_id[event.event_id] = observation_id
            continue

        if event.event_type in {"executed", "terminated", "restarted"}:
            counterparty_refs = []
            if event.executed_with_actor_id:
                counterparty_refs.append(_map_actor_ref(context, event.executed_with_actor_id))
            subject_refs = bidder_refs if event.event_type == "executed" and not counterparty_refs else []
            context.observations.append(
                {
                    "observation_id": observation_id,
                    "obs_type": "outcome",
                    "date": _event_date_payload(event),
                    "subject_refs": subject_refs,
                    "counterparty_refs": counterparty_refs,
                    "summary": event.summary,
                    "quote_ids": quote_ids,
                    "outcome_kind": event.event_type,
                    "related_observation_id": None,
                    "other_detail": event.boundary_note,
                }
            )
            context.observation_ids_by_event_id[event.event_id] = observation_id
            if event.event_type == "executed":
                merger_agreement_id = f"{observation_id}_agreement"
                context.observations.append(
                    {
                        "observation_id": merger_agreement_id,
                        "obs_type": "agreement",
                        "date": _event_date_payload(event),
                        "subject_refs": counterparty_refs,
                        "counterparty_refs": [],
                        "summary": event.summary,
                        "quote_ids": quote_ids,
                        "agreement_kind": "merger_agreement",
                        "signed": True,
                        "grants_diligence_access": None,
                        "includes_standstill": None,
                        "consideration_type": None,
                        "supersedes_observation_id": None,
                        "other_detail": None,
                    }
                )
            continue


def _build_parties_and_cohorts(context: _MigrationContext) -> tuple[list[dict], list[dict]]:
    parties: list[dict] = []
    cohorts: list[dict] = []
    fallback_observation_id = context.observations[0]["observation_id"] if context.observations else "obs_bootstrap"

    for actor in context.artifacts.actors.actors:
        quote_ids = _quote_ids_for_span_ids(context, list(actor.evidence_span_ids))
        if actor.is_grouped:
            created_by = next(
                (
                    observation["observation_id"]
                    for observation in context.observations
                    if actor.actor_id in observation.get("subject_refs", [])
                    or actor.actor_id in observation.get("counterparty_refs", [])
                    or actor.actor_id in observation.get("recipient_refs", [])
                ),
                fallback_observation_id,
            )
            exact_count = actor.group_size or 1
            cohorts.append(
                {
                    "cohort_id": actor.actor_id,
                    "label": actor.group_label or actor.display_name,
                    "parent_cohort_id": None,
                    "exact_count": exact_count,
                    "known_member_party_ids": [],
                    "unknown_member_count": exact_count,
                    "membership_basis": actor.group_label or actor.display_name,
                    "created_by_observation_id": created_by,
                    "quote_ids": quote_ids,
                }
            )
            continue
        parties.append(
            {
                "party_id": actor.actor_id,
                "display_name": actor.display_name,
                "canonical_name": actor.canonical_name,
                "aliases": list(actor.aliases),
                "role": actor.role,
                "bidder_kind": actor.bidder_kind or "unknown" if actor.role == "bidder" else None,
                "advisor_kind": actor.advisor_kind,
                "advised_party_id": actor.advised_actor_id,
                "listing_status": actor.listing_status,
                "geography": actor.geography,
                "quote_ids": quote_ids,
            }
        )
    return parties, cohorts


def migrate_canonical_v1_to_v2(artifacts: LoadedExtractArtifacts) -> RawObservationArtifactV2:
    if artifacts.mode != "canonical" or artifacts.actors is None or artifacts.events is None:
        raise ValueError("v1->v2 migration requires canonical v1 actors/events/spans artifacts.")

    actor_index = {actor.actor_id: actor for actor in artifacts.actors.actors}
    context = _MigrationContext(
        artifacts=artifacts,
        quotes=[],
        quote_ids_by_span_id={},
        grouped_actor_ids={actor.actor_id for actor in artifacts.actors.actors if actor.is_grouped},
        actor_index=actor_index,
        observations=[],
        observation_ids_by_event_id={},
    )

    used_round_event_ids = _build_round_observations(context)
    _build_non_round_observations(context, used_round_event_ids)
    parties, cohorts = _build_parties_and_cohorts(context)

    return RawObservationArtifactV2.model_validate(
        {
            "quotes": [quote.model_dump(mode="json") for quote in context.quotes],
            "parties": parties,
            "cohorts": cohorts,
            "observations": context.observations,
            "exclusions": [record.model_dump(mode="json") for record in artifacts.events.exclusions],
            "coverage": [],
        }
    )


def run_migrate_extract_v1_to_v2(
    deal_slug: str,
    *,
    project_root: Path = PROJECT_ROOT,
) -> int:
    """Write quote-first v2 observations by translating canonical v1 artifacts."""
    paths = build_skill_paths(deal_slug, project_root=project_root)
    loaded = load_extract_artifacts(paths)
    payload = migrate_canonical_v1_to_v2(loaded)

    ensure_output_directories(paths)
    paths.observations_raw_path.write_text(
        payload.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return 0
