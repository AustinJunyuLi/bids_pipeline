from __future__ import annotations

from datetime import date
from decimal import Decimal

from pipeline.models.enrichment import DealEnrichment
from pipeline.models.extraction import DealExtraction, NDAEvent, ProposalEvent
from pipeline.models.qa import QAReport


ALEX_COMPAT_COLUMNS = [
    "TargetName",
    "Acquirer",
    "DateAnnounced",
    "DateEffective",
    "URL",
    "bidderID",
    "cycle_id",
    "event_id",
    "EventType",
    "Bidder",
    "bidder_type_note",
    "actor_role",
    "advisor_kind",
    "bid_type",
    "bid_note",
    "bid_date_raw",
    "bid_date_rough",
    "bid_date_precise",
    "bid_value",
    "bid_value_pershare",
    "bid_value_lower",
    "bid_value_upper",
    "consideration_type",
    "all_cash",
    "whole_company_scope",
    "whole_company_scope_note",
    "classification_rule",
    "formal_boundary_in_cycle",
    "nda_signed",
    "source_document_id",
    "source_accession_number",
    "source_filing_type",
    "source_start_line",
    "source_end_line",
    "source_lines",
    "source_text",
    "grouped_actor",
    "group_size",
    "group_label",
    "bidder_kind",
    "listing_status",
    "geography",
    "comments_1",
    "comments_2",
    "comments_3",
    "qa_flags",
    "review_required",
]


def build_alex_compat_rows(
    extraction: DealExtraction,
    enrichment: DealEnrichment,
    qa_report: QAReport,
) -> list[dict[str, str]]:
    actor_lookup = {actor.actor_id: actor for actor in extraction.actors}
    span_lookup = {span.span_id: span for span in extraction.spans}
    event_flags = _event_flags(qa_report)
    rows: list[dict[str, str]] = []

    ordered_events = sorted(
        extraction.events,
        key=lambda event: enrichment.event_sequence.get(event.event_id, 10**9),
    )
    for event in ordered_events:
        classification = enrichment.classifications.get(event.event_id)
        cycle_id = enrichment.event_cycle_map.get(event.event_id)
        formal_boundary = bool(cycle_id and enrichment.formal_boundary_event_ids.get(cycle_id) == event.event_id)
        span = _primary_span(event.primary_span_ids, span_lookup)
        actor_ids = event.actor_ids or [None]
        for actor_id in actor_ids:
            actor = actor_lookup.get(actor_id) if actor_id else None
            rows.append(
                {
                    "TargetName": extraction.seed.target_name,
                    "Acquirer": extraction.seed.acquirer_seed or "",
                    "DateAnnounced": _fmt_date(extraction.seed.date_announced_seed),
                    "DateEffective": "",
                    "URL": extraction.seed.primary_url_seed or "",
                    "bidderID": str(enrichment.event_sequence.get(event.event_id, "")),
                    "cycle_id": cycle_id or "",
                    "event_id": event.event_id,
                    "EventType": event.event_type.value,
                    "Bidder": actor.display_name if actor else "",
                    "bidder_type_note": _bidder_type_note(actor),
                    "actor_role": actor.role.value if actor else "",
                    "advisor_kind": actor.advisor_kind.value if actor and actor.advisor_kind else "",
                    "bid_type": classification.label.value if classification else "",
                    "bid_note": _bid_note(event, classification),
                    "bid_date_raw": event.date.raw_text,
                    "bid_date_rough": _fmt_date(event.date.sort_date or event.date.normalized_start),
                    "bid_date_precise": _fmt_date(event.date.normalized_start if _is_precise_date(event) else None),
                    "bid_value": _decimal_text(_bid_value(event)),
                    "bid_value_pershare": _decimal_text(event.terms.value_per_share) if isinstance(event, ProposalEvent) else "",
                    "bid_value_lower": _decimal_text(event.terms.lower_per_share) if isinstance(event, ProposalEvent) else "",
                    "bid_value_upper": _decimal_text(event.terms.upper_per_share) if isinstance(event, ProposalEvent) else "",
                    "consideration_type": event.consideration_type.value if isinstance(event, ProposalEvent) else "",
                    "all_cash": "1" if isinstance(event, ProposalEvent) and event.consideration_type.value == "cash" else "",
                    "whole_company_scope": "1" if isinstance(event, ProposalEvent) and event.whole_company_scope is True else ("0" if isinstance(event, ProposalEvent) and event.whole_company_scope is False else ""),
                    "whole_company_scope_note": event.whole_company_scope_note if isinstance(event, ProposalEvent) and event.whole_company_scope_note else "",
                    "classification_rule": classification.rule_id if classification and classification.rule_id else "",
                    "formal_boundary_in_cycle": "1" if formal_boundary else "",
                    "nda_signed": "1" if isinstance(event, NDAEvent) and event.nda_signed else "",
                    "source_document_id": span.document_id if span else "",
                    "source_accession_number": span.accession_number if span and span.accession_number else "",
                    "source_filing_type": span.filing_type if span else "",
                    "source_start_line": str(span.start_line) if span else "",
                    "source_end_line": str(span.end_line) if span else "",
                    "source_lines": _source_lines(span),
                    "source_text": span.quote_text if span else "",
                    "grouped_actor": "1" if actor and actor.is_grouped else "",
                    "group_size": str(actor.group_size) if actor and actor.group_size is not None else "",
                    "group_label": actor.group_label if actor and actor.group_label else "",
                    "bidder_kind": actor.bidder_kind.value if actor and actor.bidder_kind else "",
                    "listing_status": actor.listing_status.value if actor and actor.listing_status else "",
                    "geography": actor.geography.value if actor and actor.geography else "",
                    "comments_1": "; ".join(actor.notes) if actor and actor.notes else "; ".join(event.notes),
                    "comments_2": "; ".join(event.notes),
                    "comments_3": "; ".join(extraction.extraction_notes),
                    "qa_flags": "; ".join(event_flags.get(event.event_id, [])),
                    "review_required": "1" if any(f.review_required and event.event_id in f.related_event_ids for f in qa_report.findings) else "",
                }
            )
    return rows


def _primary_span(primary_span_ids, span_lookup):
    for span_id in primary_span_ids:
        if span_id in span_lookup:
            return span_lookup[span_id]
    return None


def _event_flags(report: QAReport) -> dict[str, list[str]]:
    flags: dict[str, list[str]] = {}
    for finding in report.findings:
        for event_id in finding.related_event_ids:
            flags.setdefault(event_id, []).append(finding.code)
    return flags


def _bid_note(event, classification) -> str:
    mapping = {
        "target_sale": "Target Sale",
        "target_sale_public": "Target Sale Public",
        "bidder_sale": "Bidder Sale",
        "bidder_interest": "Bidder Interest",
        "activist_sale": "Activist Sale",
        "sale_press_release": "Sale Press Release",
        "bid_press_release": "Bid Press Release",
        "ib_retention": "IB",
        "nda": "NDA",
        "drop": "Drop",
        "drop_below_m": "DropBelowM",
        "drop_below_inf": "DropBelowInf",
        "drop_at_inf": "DropAtInf",
        "drop_target": "DropTarget",
        "final_round_inf_ann": "Final Round Inf Ann",
        "final_round_inf": "Final Round Inf",
        "final_round_ann": "Final Round Ann",
        "final_round": "Final Round",
        "final_round_ext_ann": "Final Round Ext Ann",
        "final_round_ext": "Final Round Ext",
        "executed": "Executed",
        "terminated": "Terminated",
        "restarted": "Restarted",
    }
    if event.event_type.value == "proposal":
        return ""
    return mapping.get(event.event_type.value, event.event_type.value)


def _fmt_date(value: date | None) -> str:
    if value is None:
        return ""
    return value.strftime("%m/%d/%Y")


def _is_precise_date(event) -> bool:
    return event.date.precision.value == "exact_day"


def _source_lines(span) -> str:
    if span is None:
        return ""
    if span.start_line == span.end_line:
        return f"L{span.start_line}"
    return f"L{span.start_line}-L{span.end_line}"


def _bid_value(event) -> Decimal | None:
    if not isinstance(event, ProposalEvent):
        return None
    return event.terms.total_enterprise_value or event.terms.value_per_share


def _decimal_text(value: Decimal | None) -> str:
    return "" if value is None else format(value, "f")


def _bidder_type_note(actor) -> str:
    if actor is None:
        return ""
    parts: list[str] = []
    if actor.geography and actor.geography.value == "non_us":
        parts.append("non-US")
    if actor.listing_status and actor.listing_status.value in {"public", "private"}:
        parts.append(actor.listing_status.value)
    if actor.bidder_kind and actor.bidder_kind.value == "strategic":
        parts.append("S")
    elif actor.bidder_kind and actor.bidder_kind.value == "financial":
        parts.append("F")
    return " ".join(parts)
