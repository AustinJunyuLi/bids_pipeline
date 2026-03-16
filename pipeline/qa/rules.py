from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pipeline.config import DEALS_DIR
from pipeline.extract.utils import atomic_write_json, atomic_write_jsonl, load_source_inputs
from pipeline.llm.schemas import ActorExtractionOutput, EventExtractionOutput, RawActorRecord, RawCountAssertion, RawEventRecord
from pipeline.models.common import ConsiderationType, EventType, QuoteMatchType, ReviewSeverity
from pipeline.models.extraction import (
    ActorRecord,
    CountAssertion,
    CycleBoundaryEvent,
    DateValue,
    DealExtraction,
    DropEvent,
    ExtractionExclusion,
    FormalitySignals,
    MoneyTerms,
    NDAEvent,
    OutcomeEvent,
    ProcessMarkerEvent,
    ProposalEvent,
    RoundEvent,
    SourceSpan,
)
from pipeline.models.qa import QAFinding, QAReport
from pipeline.models.source import ChronologyBlock, EvidenceItem
from pipeline.normalize.dates import parse_date_value
from pipeline.normalize.spans import resolve_anchor_span, resolve_evidence_item_span
from pipeline.qa.completeness import compute_completeness_metrics
from pipeline.qa.review import apply_review_overrides, load_review_overrides


CANONICAL_FILENAME = "extraction_canonical.json"
QA_REPORT_FILENAME = "report.json"
SPAN_REGISTRY_FILENAME = "span_registry.jsonl"


class SpanRegistry:
    def __init__(
        self,
        *,
        blocks: list[ChronologyBlock],
        evidence_items: list[EvidenceItem],
        document_lines: dict[str, list[str]],
        selection_document_id: str,
        selection_accession_number: str | None,
        selection_filing_type: str,
    ) -> None:
        self.blocks = {block.block_id: block for block in blocks}
        self.evidence_items = {item.evidence_id: item for item in evidence_items}
        self.document_lines = document_lines
        self.selection_document_id = selection_document_id
        self.selection_accession_number = selection_accession_number
        self.selection_filing_type = selection_filing_type
        self._spans_by_key: dict[tuple[Any, ...], SourceSpan] = {}
        self._counter = 1

    def resolve_many(self, evidence_refs) -> list[str]:
        span_ids: list[str] = []
        for ref in evidence_refs:
            span_ids.append(self.resolve(ref).span_id)
        return span_ids

    def resolve(self, evidence_ref) -> SourceSpan:
        key = (evidence_ref.block_id, evidence_ref.evidence_id, " ".join(evidence_ref.anchor_text.lower().split()))
        if key in self._spans_by_key:
            return self._spans_by_key[key]
        span_id = f"span-{self._counter:04d}"
        self._counter += 1
        if evidence_ref.block_id:
            block = self.blocks[evidence_ref.block_id]
            raw_lines = self.document_lines.get(block.document_id, [])
            span = resolve_anchor_span(
                list(self.blocks.values()),
                raw_lines,
                block_id=evidence_ref.block_id,
                anchor_text=evidence_ref.anchor_text,
                document_id=block.document_id,
                accession_number=self.selection_accession_number,
                filing_type=self.selection_filing_type,
                span_id=span_id,
            )
        else:
            item = self.evidence_items[evidence_ref.evidence_id]
            raw_lines = self.document_lines.get(item.document_id, _fallback_lines(item))
            span = resolve_evidence_item_span(item, raw_lines, anchor_text=evidence_ref.anchor_text, span_id=span_id)
        self._spans_by_key[key] = span
        return span

    @property
    def spans(self) -> list[SourceSpan]:
        return list(self._spans_by_key.values())


def run_qa(
    deal_slug: str,
    *,
    run_id: str,
    deals_dir: Path = DEALS_DIR,
) -> dict[str, Any]:
    seed, selection, blocks, evidence_items = load_source_inputs(deal_slug, run_id=run_id, deals_dir=deals_dir)
    extract_dir = deals_dir / deal_slug / "extract"
    qa_dir = deals_dir / deal_slug / "qa"
    review_dir = deals_dir / deal_slug / "review"
    qa_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)

    actor_output = ActorExtractionOutput.model_validate_json((extract_dir / "actors_raw.json").read_text(encoding="utf-8"))
    event_output = EventExtractionOutput.model_validate_json((extract_dir / "events_raw.json").read_text(encoding="utf-8"))

    document_lines = _load_document_lines(deals_dir / deal_slug / "source" / "filings")
    span_registry = SpanRegistry(
        blocks=blocks,
        evidence_items=evidence_items,
        document_lines=document_lines,
        selection_document_id=selection.document_id,
        selection_accession_number=selection.accession_number,
        selection_filing_type=selection.filing_type,
    )

    findings: list[QAFinding] = []
    exclusions: list[ExtractionExclusion] = []

    actors, actor_id_map, actor_findings = _reconcile_actors(actor_output.actors, span_registry)
    findings.extend(actor_findings)
    count_assertions = _reconcile_count_assertions(actor_output.count_assertions, span_registry)
    events, event_exclusions, event_findings = _reconcile_events(
        event_output.events,
        span_registry=span_registry,
        actor_id_map=actor_id_map,
    )
    findings.extend(event_findings)
    exclusions.extend(event_exclusions)
    exclusions.extend(
        ExtractionExclusion(
            exclusion_id=f"llm-exclusion-{index:04d}",
            category=exclusion.category,
            block_ids=exclusion.block_ids,
            explanation=exclusion.explanation,
        )
        for index, exclusion in enumerate(event_output.exclusions, start=1)
    )

    if selection.selected_candidate is None or not blocks:
        findings.append(
            QAFinding(
                finding_id="qa-missing-chronology",
                severity=ReviewSeverity.BLOCKER,
                code="missing_chronology",
                message="No chronology blocks were available for QA reconciliation.",
                review_required=True,
            )
        )

    extraction = DealExtraction(
        run_id=run_id,
        deal_slug=deal_slug,
        seed=seed,
        source_selection=selection,
        actors=actors,
        count_assertions=count_assertions,
        spans=span_registry.spans,
        events=events,
        exclusions=exclusions,
        unresolved_mentions=sorted(set(actor_output.unresolved_mentions + event_output.unresolved_mentions)),
        extraction_notes=event_output.coverage_notes,
    )
    completeness_metrics, completeness_findings = compute_completeness_metrics(
        extraction,
        evidence_items=evidence_items,
    )
    findings.extend(completeness_findings)

    report = QAReport(
        run_id=run_id,
        deal_slug=deal_slug,
        blocker_count=sum(1 for finding in findings if finding.severity == ReviewSeverity.BLOCKER),
        warning_count=sum(1 for finding in findings if finding.severity == ReviewSeverity.WARNING),
        findings=findings,
        completeness_metrics=completeness_metrics,
        passes_export_gate=not any(finding.severity == ReviewSeverity.BLOCKER for finding in findings),
    )

    overrides = load_review_overrides(review_dir)
    if overrides:
        report = apply_review_overrides(report, overrides=overrides)

    atomic_write_json(qa_dir / CANONICAL_FILENAME, extraction.model_dump(mode="json"))
    atomic_write_json(qa_dir / QA_REPORT_FILENAME, report.model_dump(mode="json"))
    atomic_write_jsonl(qa_dir / SPAN_REGISTRY_FILENAME, [span.model_dump(mode="json") for span in span_registry.spans])

    return {
        "deal_slug": deal_slug,
        "actor_count": len(actors),
        "event_count": len(events),
        "span_count": len(span_registry.spans),
        "blocker_count": report.blocker_count,
        "warning_count": report.warning_count,
        "passes_export_gate": report.passes_export_gate,
    }


def _reconcile_actors(
    raw_actors: list[RawActorRecord],
    span_registry: SpanRegistry,
) -> tuple[list[ActorRecord], dict[str, str], list[QAFinding]]:
    actor_records: dict[tuple[str, str, str | None, int | None], ActorRecord] = {}
    actor_id_map: dict[str, str] = {}
    findings: list[QAFinding] = []
    ordinal = 1
    for raw_actor in raw_actors:
        key = _actor_key(raw_actor)
        span_ids = span_registry.resolve_many(raw_actor.evidence_refs)
        if key not in actor_records:
            canonical_actor_id = _stable_actor_id(raw_actor, ordinal)
            ordinal += 1
            actor_records[key] = ActorRecord(
                actor_id=canonical_actor_id,
                display_name=raw_actor.display_name,
                canonical_name=raw_actor.canonical_name,
                aliases=list(dict.fromkeys(raw_actor.aliases)),
                role=raw_actor.role,
                advisor_kind=raw_actor.advisor_kind,
                bidder_kind=raw_actor.bidder_kind,
                listing_status=raw_actor.listing_status,
                geography=raw_actor.geography,
                is_grouped=raw_actor.is_grouped,
                group_size=raw_actor.group_size,
                group_label=raw_actor.group_label,
                first_mention_span_ids=span_ids,
                notes=list(raw_actor.notes),
            )
        else:
            existing = actor_records[key]
            actor_records[key] = existing.model_copy(
                update={
                    "aliases": list(dict.fromkeys([*existing.aliases, *raw_actor.aliases])),
                    "first_mention_span_ids": list(dict.fromkeys([*existing.first_mention_span_ids, *span_ids])),
                    "notes": list(dict.fromkeys([*existing.notes, *raw_actor.notes])),
                }
            )
        actor_id_map[raw_actor.actor_id] = actor_records[key].actor_id

    for span in span_registry.spans:
        if span.match_type == QuoteMatchType.UNRESOLVED:
            findings.append(
                QAFinding(
                    finding_id=f"qa-{span.span_id}",
                    severity=ReviewSeverity.BLOCKER,
                    code="unresolved_span",
                    message="Evidence reference could not be resolved exactly in source text.",
                    related_span_ids=[span.span_id],
                    review_required=True,
                )
            )
    return list(actor_records.values()), actor_id_map, findings


def _reconcile_count_assertions(
    raw_assertions: list[RawCountAssertion],
    span_registry: SpanRegistry,
) -> list[CountAssertion]:
    assertions: list[CountAssertion] = []
    for index, raw_assertion in enumerate(raw_assertions, start=1):
        assertions.append(
            CountAssertion(
                assertion_id=f"assertion-{index:04d}",
                count=raw_assertion.count,
                subject=raw_assertion.subject,
                qualifier_text=raw_assertion.qualifier_text,
                date=None,
                span_ids=span_registry.resolve_many(raw_assertion.evidence_refs),
            )
        )
    return assertions


def _reconcile_events(
    raw_events: list[RawEventRecord],
    *,
    span_registry: SpanRegistry,
    actor_id_map: dict[str, str],
) -> tuple[list, list[ExtractionExclusion], list[QAFinding]]:
    events = []
    exclusions: list[ExtractionExclusion] = []
    findings: list[QAFinding] = []
    previous_date: DateValue | None = None

    for index, raw_event in enumerate(raw_events, start=1):
        primary_span_ids = span_registry.resolve_many(raw_event.evidence_refs)
        resolved_actor_ids: list[str] = []
        for actor_id in raw_event.actor_ids:
            canonical_actor_id = actor_id_map.get(actor_id)
            if canonical_actor_id is None:
                findings.append(
                    QAFinding(
                        finding_id=f"qa-event-actor-{index:04d}-{actor_id}",
                        severity=ReviewSeverity.BLOCKER,
                        code="unknown_actor_reference",
                        message=f"Event references actor {actor_id!r} which is absent from the actor roster.",
                        related_span_ids=primary_span_ids,
                        review_required=True,
                    )
                )
                continue
            resolved_actor_ids.append(canonical_actor_id)

        date_value = parse_date_value(
            raw_event.date.raw_text,
            anchor_date=previous_date,
            anchor_event_id=events[-1].event_id if events else None,
        )
        previous_date = date_value if date_value.sort_date is not None else previous_date
        event_id = f"event-{index:04d}"

        if raw_event.event_type == EventType.PROPOSAL and raw_event.whole_company_scope is False:
            exclusions.append(
                ExtractionExclusion(
                    exclusion_id=f"exclusion-{index:04d}",
                    category="partial_company_bid",
                    block_ids=[ref.block_id for ref in raw_event.evidence_refs if ref.block_id],
                    explanation=raw_event.whole_company_scope_note
                    or "Proposal does not target the whole company.",
                )
            )
            findings.append(
                QAFinding(
                    finding_id=f"qa-partial-company-{index:04d}",
                    severity=ReviewSeverity.BLOCKER,
                    code="partial_company_bid_in_events",
                    message="A partial-company bid reached canonical event reconciliation.",
                    related_span_ids=primary_span_ids,
                    review_required=True,
                )
            )
            continue

        event_model, event_findings = _build_event_model(
            raw_event,
            event_id=event_id,
            date_value=date_value,
            actor_ids=resolved_actor_ids,
            primary_span_ids=primary_span_ids,
        )
        findings.extend(event_findings)
        if event_model is not None:
            events.append(event_model)

    return events, exclusions, findings


def _build_event_model(
    raw_event: RawEventRecord,
    *,
    event_id: str,
    date_value: DateValue,
    actor_ids: list[str],
    primary_span_ids: list[str],
):
    findings: list[QAFinding] = []
    kwargs = {
        "event_id": event_id,
        "event_type": raw_event.event_type,
        "date": date_value,
        "actor_ids": actor_ids,
        "primary_span_ids": primary_span_ids,
        "summary": raw_event.summary,
        "notes": raw_event.notes,
    }

    if raw_event.event_type in {
        EventType.TARGET_SALE,
        EventType.TARGET_SALE_PUBLIC,
        EventType.BIDDER_SALE,
        EventType.BIDDER_INTEREST,
        EventType.ACTIVIST_SALE,
        EventType.SALE_PRESS_RELEASE,
        EventType.BID_PRESS_RELEASE,
        EventType.IB_RETENTION,
    }:
        return ProcessMarkerEvent(**kwargs), findings
    if raw_event.event_type == EventType.NDA:
        return NDAEvent(**kwargs, nda_signed=raw_event.nda_signed), findings
    if raw_event.event_type == EventType.PROPOSAL:
        if raw_event.terms is None or raw_event.formality_signals is None:
            findings.append(
                QAFinding(
                    finding_id=f"qa-proposal-shape-{event_id}",
                    severity=ReviewSeverity.BLOCKER,
                    code="proposal_missing_required_fields",
                    message="Proposal event was missing terms or formality signals after validation.",
                    related_span_ids=primary_span_ids,
                    review_required=True,
                )
            )
            return None, findings
        terms = MoneyTerms(
            raw_text=raw_event.terms.raw_text,
            currency=raw_event.terms.currency,
            value_per_share=raw_event.terms.value_per_share,
            lower_per_share=raw_event.terms.lower_per_share,
            upper_per_share=raw_event.terms.upper_per_share,
            total_enterprise_value=raw_event.terms.total_enterprise_value,
            is_range=raw_event.terms.is_range,
        )
        if terms.is_range and (terms.lower_per_share is None or terms.upper_per_share is None):
            findings.append(
                QAFinding(
                    finding_id=f"qa-range-bounds-{event_id}",
                    severity=ReviewSeverity.BLOCKER,
                    code="range_bid_missing_bounds",
                    message="Range bid did not preserve both lower and upper bounds.",
                    related_span_ids=primary_span_ids,
                    review_required=True,
                )
            )
        signals = FormalitySignals(
            contains_range=raw_event.formality_signals.contains_range,
            mentions_indication_of_interest=raw_event.formality_signals.mentions_indication_of_interest,
            mentions_preliminary=raw_event.formality_signals.mentions_preliminary,
            mentions_non_binding=raw_event.formality_signals.mentions_non_binding,
            mentions_binding_offer=raw_event.formality_signals.mentions_binding_offer,
            includes_draft_merger_agreement=raw_event.formality_signals.includes_draft_merger_agreement,
            includes_marked_up_agreement=raw_event.formality_signals.includes_marked_up_agreement,
            requested_binding_offer_via_process_letter=raw_event.formality_signals.requested_binding_offer_via_process_letter,
            after_final_round_announcement=raw_event.formality_signals.after_final_round_announcement,
            after_final_round_deadline=raw_event.formality_signals.after_final_round_deadline,
            signal_span_ids=primary_span_ids,
        )
        return ProposalEvent(
            **kwargs,
            terms=terms,
            consideration_type=raw_event.consideration_type or ConsiderationType.UNKNOWN,
            whole_company_scope=raw_event.whole_company_scope,
            whole_company_scope_note=raw_event.whole_company_scope_note,
            formality_signals=signals,
        ), findings
    if raw_event.event_type in {
        EventType.DROP,
        EventType.DROP_BELOW_M,
        EventType.DROP_BELOW_INF,
        EventType.DROP_AT_INF,
        EventType.DROP_TARGET,
    }:
        return DropEvent(**kwargs, drop_reason_text=raw_event.drop_reason_text), findings
    if raw_event.event_type in {
        EventType.FINAL_ROUND_INF_ANN,
        EventType.FINAL_ROUND_INF,
        EventType.FINAL_ROUND_ANN,
        EventType.FINAL_ROUND,
        EventType.FINAL_ROUND_EXT_ANN,
        EventType.FINAL_ROUND_EXT,
    }:
        deadline_date = None
        if raw_event.deadline_date is not None:
            deadline_date = parse_date_value(raw_event.deadline_date.raw_text, anchor_date=date_value)
        return RoundEvent(
            **kwargs,
            round_scope=raw_event.round_scope or _default_round_scope(raw_event.event_type),
            deadline_date=deadline_date,
        ), findings
    if raw_event.event_type == EventType.EXECUTED:
        executed_with_actor_id = None
        if raw_event.executed_with_actor_id is not None:
            executed_with_actor_id = next((actor_id for actor_id in actor_ids if actor_id.endswith(raw_event.executed_with_actor_id.split('-')[-1])), None)
        return OutcomeEvent(**kwargs, executed_with_actor_id=executed_with_actor_id), findings
    if raw_event.event_type in {EventType.TERMINATED, EventType.RESTARTED}:
        return CycleBoundaryEvent(**kwargs, boundary_note=raw_event.boundary_note), findings
    raise ValueError(f"Unsupported event type: {raw_event.event_type}")


def _default_round_scope(event_type: EventType) -> str:
    if event_type in {EventType.FINAL_ROUND_INF_ANN, EventType.FINAL_ROUND_INF}:
        return "informal"
    if event_type in {EventType.FINAL_ROUND_EXT_ANN, EventType.FINAL_ROUND_EXT}:
        return "extension"
    return "formal"


def _load_document_lines(filings_dir: Path) -> dict[str, list[str]]:
    lines_by_document: dict[str, list[str]] = {}
    if not filings_dir.exists():
        return lines_by_document
    for path in filings_dir.glob("*.txt"):
        lines_by_document[path.stem] = path.read_text(encoding="utf-8").splitlines()
    return lines_by_document


def _actor_key(raw_actor: RawActorRecord) -> tuple[str, str, str | None, int | None]:
    canonical = _normalize_actor_name(raw_actor.canonical_name or raw_actor.display_name)
    group_label = raw_actor.group_label if raw_actor.is_grouped else None
    return (raw_actor.role.value, canonical, group_label, raw_actor.group_size)


def _stable_actor_id(raw_actor: RawActorRecord, ordinal: int) -> str:
    normalized = _normalize_actor_name(raw_actor.canonical_name or raw_actor.display_name)
    return normalized or f"actor-{ordinal:04d}"


def _normalize_actor_name(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized


def _fallback_lines(item: EvidenceItem) -> list[str]:
    return item.raw_text.splitlines() or [item.raw_text]
