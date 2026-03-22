# QA, Enrichment, Export, Normalization

---

## pipeline/qa/__init__.py
```python
from pipeline.qa.completeness import compute_completeness_metrics
from pipeline.qa.review import apply_review_overrides, findings_by_code, load_review_overrides
from pipeline.qa.rules import run_qa

__all__ = [
    "apply_review_overrides",
    "compute_completeness_metrics",
    "findings_by_code",
    "load_review_overrides",
    "run_qa",
]
```

---

## pipeline/qa/rules.py
```python
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
```

---

## pipeline/qa/completeness.py
```python
from __future__ import annotations

from pipeline.models.common import EventType, ReviewSeverity
from pipeline.models.extraction import DealExtraction
from pipeline.models.qa import QAFinding
from pipeline.models.source import EvidenceItem


def compute_completeness_metrics(
    extraction: DealExtraction,
    *,
    evidence_items: list[EvidenceItem],
) -> tuple[dict[str, int | bool], list[QAFinding]]:
    proposal_count = sum(1 for event in extraction.events if event.event_type == EventType.PROPOSAL)
    nda_count = sum(1 for event in extraction.events if event.event_type == EventType.NDA)
    outcome_count = sum(
        1
        for event in extraction.events
        if event.event_type in {EventType.EXECUTED, EventType.TERMINATED}
    )
    financial_item_count = sum(1 for item in evidence_items if item.evidence_type.value == "financial_term")
    process_item_count = sum(1 for item in evidence_items if item.evidence_type.value == "process_signal")
    unresolved_span_count = sum(1 for span in extraction.spans if span.match_type.value == "unresolved")

    findings: list[QAFinding] = []
    if proposal_count == 0 and financial_item_count > 0:
        findings.append(
            QAFinding(
                finding_id="qa-missing-proposal",
                severity=ReviewSeverity.WARNING,
                code="missing_proposal_events",
                message="Financial evidence items were detected but no proposal events were extracted.",
                review_required=True,
            )
        )
    if nda_count == 0 and process_item_count > 0:
        findings.append(
            QAFinding(
                finding_id="qa-missing-nda",
                severity=ReviewSeverity.WARNING,
                code="missing_nda_events",
                message="Process evidence items were detected but no NDA events were extracted.",
                review_required=True,
            )
        )
    if outcome_count == 0:
        findings.append(
            QAFinding(
                finding_id="qa-missing-outcome",
                severity=ReviewSeverity.WARNING,
                code="missing_outcome_event",
                message="No executed or terminated outcome event was extracted.",
                review_required=True,
            )
        )
    if unresolved_span_count:
        findings.append(
            QAFinding(
                finding_id="qa-unresolved-spans",
                severity=ReviewSeverity.BLOCKER,
                code="unresolved_spans_present",
                message="One or more evidence spans could not be resolved exactly.",
                related_span_ids=[span.span_id for span in extraction.spans if span.match_type.value == "unresolved"],
                review_required=True,
            )
        )

    return {
        "actor_count": len(extraction.actors),
        "event_count": len(extraction.events),
        "proposal_count": proposal_count,
        "nda_count": nda_count,
        "outcome_count": outcome_count,
        "financial_evidence_item_count": financial_item_count,
        "process_evidence_item_count": process_item_count,
        "unresolved_span_count": unresolved_span_count,
        "passes_basic_completeness": outcome_count > 0 and proposal_count > 0,
    }, findings
```

---

## pipeline/qa/review.py
```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pipeline.models.qa import QAFinding, QAReport


OVERRIDE_FILENAMES = ("overrides.json", "overrides.yaml", "overrides.yml")


def load_review_overrides(review_dir: Path) -> dict[str, Any]:
    for filename in OVERRIDE_FILENAMES:
        path = review_dir / filename
        if not path.exists():
            continue
        if path.suffix == ".json":
            return json.loads(path.read_text(encoding="utf-8"))
        try:
            import yaml  # type: ignore
        except ModuleNotFoundError:
            raise ModuleNotFoundError(
                "yaml review overrides require PyYAML; use JSON overrides or install PyYAML."
            )
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        return payload or {}
    return {}


def apply_review_overrides(report: QAReport, *, overrides: dict[str, Any]) -> QAReport:
    suppress_codes = set(overrides.get("suppress_codes", []))
    upgraded_codes = {str(code): severity for code, severity in (overrides.get("upgrade_codes", {}) or {}).items()}
    findings: list[QAFinding] = []
    for finding in report.findings:
        if finding.code in suppress_codes:
            continue
        if finding.code in upgraded_codes:
            findings.append(finding.model_copy(update={"severity": upgraded_codes[finding.code]}))
        else:
            findings.append(finding)
    blocker_count = sum(1 for finding in findings if finding.severity == "blocker")
    warning_count = sum(1 for finding in findings if finding.severity == "warning")
    return report.model_copy(
        update={
            "findings": findings,
            "blocker_count": blocker_count,
            "warning_count": warning_count,
            "passes_export_gate": blocker_count == 0,
        }
    )


def findings_by_code(report: QAReport) -> dict[str, list[QAFinding]]:
    grouped: dict[str, list[QAFinding]] = {}
    for finding in report.findings:
        grouped.setdefault(finding.code, []).append(finding)
    return grouped
```

---

## pipeline/normalize/__init__.py
```python
from pipeline.normalize.dates import parse_date_value
from pipeline.normalize.quotes import (
    find_anchor_in_segment,
    normalize_for_matching,
    reconstruct_quote_text,
)
from pipeline.normalize.spans import resolve_anchor_span

__all__ = [
    "find_anchor_in_segment",
    "normalize_for_matching",
    "parse_date_value",
    "reconstruct_quote_text",
    "resolve_anchor_span",
]
```

---

## pipeline/normalize/quotes.py
```python
from __future__ import annotations

from pipeline.models.common import QuoteMatchType


TRANSLATIONS = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2013": "-",
    "\u2014": "-",
    "\u2212": "-",
    "\u00a0": " ",
    "\x91": "'",
    "\x92": "'",
    "\x93": '"',
    "\x94": '"',
    "\x96": "-",
    "\x97": "-",
}
QUOTE_CHARS = frozenset({"'", '"'})


def normalize_for_matching(text: str) -> str:
    normalized, _index_map = normalize_for_matching_with_map(text)
    return normalized


def normalize_for_matching_batch(texts: list[str]) -> list[str]:
    return [normalize_for_matching(text) for text in texts]


def normalize_for_matching_with_map(text: str) -> tuple[str, list[int]]:
    chars: list[str] = []
    index_map: list[int] = []
    previous_space = False

    for index, char in enumerate(text):
        replacement = TRANSLATIONS.get(char, char)
        for normalized_char in replacement.lower():
            if normalized_char.isspace():
                if previous_space:
                    continue
                chars.append(" ")
                index_map.append(index)
                previous_space = True
                continue

            chars.append(normalized_char)
            index_map.append(index)
            previous_space = False

    while chars and chars[0] == " ":
        chars.pop(0)
        index_map.pop(0)
    while chars and chars[-1] == " ":
        chars.pop()
        index_map.pop()

    return "".join(chars), index_map


def simplify_for_matching_with_map(text: str, index_map: list[int]) -> tuple[str, list[int]]:
    chars: list[str] = []
    simplified_map: list[int] = []

    for index, char in enumerate(text):
        if char in QUOTE_CHARS:
            continue
        chars.append(char)
        simplified_map.append(index_map[index])

    return "".join(chars), simplified_map


def strip_parenthetical_text_with_map(text: str, index_map: list[int]) -> tuple[str, list[int]]:
    chars: list[str] = []
    stripped_map: list[int] = []
    depth = 0

    for index, char in enumerate(text):
        if char == "(":
            depth += 1
            continue
        if char == ")" and depth:
            depth -= 1
            continue
        if depth:
            continue
        chars.append(char)
        stripped_map.append(index_map[index])

    return "".join(chars), stripped_map


def compact_alnum_with_map(text: str, index_map: list[int]) -> tuple[str, list[int]]:
    chars: list[str] = []
    compact_map: list[int] = []

    for index, char in enumerate(text):
        if not char.isalnum():
            continue
        chars.append(char)
        compact_map.append(index_map[index])

    return "".join(chars), compact_map


def reconstruct_quote_text(lines: list[str]) -> str:
    return " ".join(line.strip() for line in lines if line.strip())


def find_anchor_in_segment(
    raw_segment: str,
    anchor_text: str,
) -> tuple[QuoteMatchType, int | None, int | None]:
    exact_start = raw_segment.find(anchor_text)
    if exact_start != -1:
        return QuoteMatchType.EXACT, exact_start, exact_start + len(anchor_text)

    normalized_segment, index_map = normalize_for_matching_with_map(raw_segment)
    normalized_anchor = normalize_for_matching(anchor_text)
    if normalized_anchor:
        normalized_start = normalized_segment.find(normalized_anchor)
        if normalized_start != -1:
            normalized_end = normalized_start + len(normalized_anchor) - 1
            original_start = index_map[normalized_start]
            original_end = index_map[normalized_end] + 1
            return QuoteMatchType.NORMALIZED, original_start, original_end

        simplified_segment, simplified_map = simplify_for_matching_with_map(normalized_segment, index_map)
        simplified_anchor, _anchor_map = simplify_for_matching_with_map(
            normalized_anchor,
            list(range(len(normalized_anchor))),
        )
        if simplified_anchor:
            simplified_start = simplified_segment.find(simplified_anchor)
            if simplified_start != -1:
                simplified_end = simplified_start + len(simplified_anchor) - 1
                original_start = simplified_map[simplified_start]
                original_end = simplified_map[simplified_end] + 1
                return QuoteMatchType.FUZZY, original_start, original_end

        parenthetical_segment, parenthetical_map = strip_parenthetical_text_with_map(
            normalized_segment,
            index_map,
        )
        parenthetical_anchor, _anchor_map = strip_parenthetical_text_with_map(
            normalized_anchor,
            list(range(len(normalized_anchor))),
        )
        if parenthetical_anchor:
            parenthetical_start = parenthetical_segment.find(parenthetical_anchor)
            if parenthetical_start != -1:
                parenthetical_end = parenthetical_start + len(parenthetical_anchor) - 1
                original_start = parenthetical_map[parenthetical_start]
                original_end = parenthetical_map[parenthetical_end] + 1
                return QuoteMatchType.FUZZY, original_start, original_end

        compact_segment, compact_map = compact_alnum_with_map(parenthetical_segment, parenthetical_map)
        compact_anchor, _anchor_map = compact_alnum_with_map(
            parenthetical_anchor,
            list(range(len(parenthetical_anchor))),
        )
        if compact_anchor:
            compact_start = compact_segment.find(compact_anchor)
            if compact_start != -1:
                compact_end = compact_start + len(compact_anchor) - 1
                original_start = compact_map[compact_start]
                original_end = compact_map[compact_end] + 1
                return QuoteMatchType.FUZZY, original_start, original_end

    return QuoteMatchType.UNRESOLVED, None, None
```

---

## pipeline/normalize/spans.py
```python
from __future__ import annotations

from pipeline.models.common import QuoteMatchType
from pipeline.models.extraction import SourceSpan
from pipeline.models.source import ChronologyBlock, EvidenceItem
from pipeline.normalize.quotes import find_anchor_in_segment, normalize_for_matching, reconstruct_quote_text

SPAN_EXPANSION_LINES = 3


def resolve_anchor_span(
    blocks: list[ChronologyBlock],
    raw_lines: list[str],
    *,
    block_id: str,
    anchor_text: str,
    document_id: str,
    accession_number: str | None,
    filing_type: str,
    span_id: str,
) -> SourceSpan:
    block = next(block for block in blocks if block.block_id == block_id)
    return resolve_text_span(
        raw_lines,
        start_line=block.start_line,
        end_line=block.end_line,
        block_ids=[block_id],
        anchor_text=anchor_text,
        document_id=document_id,
        accession_number=accession_number,
        filing_type=filing_type,
        span_id=span_id,
    )


def resolve_evidence_item_span(
    evidence_item: EvidenceItem,
    raw_lines: list[str],
    *,
    anchor_text: str,
    span_id: str,
) -> SourceSpan:
    return resolve_text_span(
        raw_lines,
        start_line=evidence_item.start_line,
        end_line=evidence_item.end_line,
        block_ids=[],
        anchor_text=anchor_text,
        document_id=evidence_item.document_id,
        accession_number=evidence_item.accession_number,
        filing_type=evidence_item.filing_type,
        span_id=span_id,
    )


def resolve_text_span(
    raw_lines: list[str],
    *,
    start_line: int,
    end_line: int,
    block_ids: list[str],
    anchor_text: str,
    document_id: str,
    accession_number: str | None,
    filing_type: str,
    span_id: str,
) -> SourceSpan:
    block_lines = raw_lines[start_line - 1 : end_line]
    raw_segment = "\n".join(block_lines)
    match_type, start_idx, end_idx = find_anchor_in_segment(raw_segment, anchor_text)

    window_start_line = start_line
    resolved_lines = block_lines
    if match_type == QuoteMatchType.UNRESOLVED:
        expanded_start_line = max(1, start_line - SPAN_EXPANSION_LINES)
        expanded_end_line = min(len(raw_lines), end_line + SPAN_EXPANSION_LINES)
        if expanded_start_line != start_line or expanded_end_line != end_line:
            expanded_lines = raw_lines[expanded_start_line - 1 : expanded_end_line]
            expanded_segment = "\n".join(expanded_lines)
            expanded_match_type, expanded_start_idx, expanded_end_idx = find_anchor_in_segment(
                expanded_segment,
                anchor_text,
            )
            if expanded_match_type != QuoteMatchType.UNRESOLVED:
                match_type = expanded_match_type
                start_idx = expanded_start_idx
                end_idx = expanded_end_idx
                window_start_line = expanded_start_line
                resolved_lines = expanded_lines

    if match_type == QuoteMatchType.UNRESOLVED or start_idx is None or end_idx is None:
        quote_text = reconstruct_quote_text(block_lines)
        return SourceSpan(
            span_id=span_id,
            document_id=document_id,
            accession_number=accession_number,
            filing_type=filing_type,
            start_line=start_line,
            end_line=end_line,
            start_char=None,
            end_char=None,
            block_ids=block_ids,
            anchor_text=anchor_text,
            quote_text=quote_text,
            quote_text_normalized=normalize_for_matching(quote_text),
            match_type=QuoteMatchType.UNRESOLVED,
            resolution_note=f"Anchor text was not found between lines {start_line}-{end_line}.",
        )

    resolved_start_line, start_char = _segment_offset_to_line_position(
        resolved_lines,
        window_start_line,
        start_idx,
    )
    resolved_end_line, end_char_inclusive = _segment_offset_to_line_position(
        resolved_lines,
        window_start_line,
        end_idx - 1,
    )
    selected_lines = raw_lines[resolved_start_line - 1 : resolved_end_line]
    quote_text = reconstruct_quote_text(selected_lines)
    return SourceSpan(
        span_id=span_id,
        document_id=document_id,
        accession_number=accession_number,
        filing_type=filing_type,
        start_line=resolved_start_line,
        end_line=resolved_end_line,
        start_char=start_char,
        end_char=end_char_inclusive + 1,
        block_ids=block_ids,
        anchor_text=anchor_text,
        quote_text=quote_text,
        quote_text_normalized=normalize_for_matching(quote_text),
        match_type=match_type,
        resolution_note=None,
    )


def _segment_offset_to_line_position(
    block_lines: list[str],
    base_line_number: int,
    char_offset: int,
) -> tuple[int, int]:
    running = 0
    for offset, line in enumerate(block_lines):
        line_length = len(line)
        if char_offset < running + line_length:
            return base_line_number + offset, char_offset - running
        running += line_length
        if offset < len(block_lines) - 1:
            if char_offset == running:
                return base_line_number + offset, line_length
            running += 1
    return base_line_number + len(block_lines) - 1, len(block_lines[-1]) if block_lines else 0
```

---

## pipeline/normalize/dates.py
```python
from __future__ import annotations

import calendar
import re
from datetime import date, timedelta

from pipeline.models.common import DatePrecision
from pipeline.models.extraction import DateValue


MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

EXACT_DAY_RE = re.compile(
    r"(?i)\b("
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
    r")\s+(\d{1,2}),\s+(\d{4})\b"
)
PARTIAL_MONTH_RE = re.compile(
    r"(?i)\b(early|mid|late)[-\s]+("
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
    r")\s+(\d{4})\b"
)
MONTH_ONLY_RE = re.compile(
    r"(?i)\b("
    r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
    r")\s+(\d{4})\b"
)
QUARTER_RE = re.compile(
    r"(?i)\b(first|1st|second|2nd|third|3rd|fourth|4th|q[1-4])\s+quarter\s+(\d{4})\b|\b(q[1-4])\s+(\d{4})\b"
)
YEAR_RE = re.compile(r"^\s*(\d{4})\s*$")


def parse_date_value(
    raw_text: str,
    *,
    anchor_date: DateValue | date | None = None,
    anchor_event_id: str | None = None,
) -> DateValue:
    text = raw_text.strip()

    exact_match = EXACT_DAY_RE.search(text)
    if exact_match:
        month = MONTHS[exact_match.group(1).lower()]
        day = int(exact_match.group(2))
        year = int(exact_match.group(3))
        parsed = date(year, month, day)
        return _make_date_value(
            raw_text=text,
            normalized_start=parsed,
            normalized_end=parsed,
            sort_date=parsed,
            precision=DatePrecision.EXACT_DAY,
        )

    partial_match = PARTIAL_MONTH_RE.search(text)
    if partial_match:
        modifier = partial_match.group(1).lower()
        month = MONTHS[partial_match.group(2).lower()]
        year = int(partial_match.group(3))
        last_day = calendar.monthrange(year, month)[1]
        if modifier == "early":
            start_day, end_day, sort_day = 1, min(10, last_day), 5
            precision = DatePrecision.MONTH_EARLY
        elif modifier == "mid":
            start_day, end_day, sort_day = 11, min(20, last_day), 15
            precision = DatePrecision.MONTH_MID
        else:
            start_day, end_day, sort_day = 21, last_day, min(25, last_day)
            precision = DatePrecision.MONTH_LATE
        return _make_date_value(
            raw_text=text,
            normalized_start=date(year, month, start_day),
            normalized_end=date(year, month, end_day),
            sort_date=date(year, month, sort_day),
            precision=precision,
        )

    month_match = MONTH_ONLY_RE.search(text)
    if month_match:
        month = MONTHS[month_match.group(1).lower()]
        year = int(month_match.group(2))
        last_day = calendar.monthrange(year, month)[1]
        return _make_date_value(
            raw_text=text,
            normalized_start=date(year, month, 1),
            normalized_end=date(year, month, last_day),
            sort_date=date(year, month, 1),
            precision=DatePrecision.MONTH,
        )

    quarter_match = QUARTER_RE.search(text)
    if quarter_match:
        quarter_token = quarter_match.group(1) or quarter_match.group(3)
        year_text = quarter_match.group(2) or quarter_match.group(4)
        quarter = _quarter_number(quarter_token.lower())
        year = int(year_text)
        start_month = 1 + (quarter - 1) * 3
        end_month = start_month + 2
        last_day = calendar.monthrange(year, end_month)[1]
        return _make_date_value(
            raw_text=text,
            normalized_start=date(year, start_month, 1),
            normalized_end=date(year, end_month, last_day),
            sort_date=date(year, start_month, 1),
            precision=DatePrecision.QUARTER,
        )

    relative = _parse_relative_date(text, anchor_date=anchor_date, anchor_event_id=anchor_event_id)
    if relative is not None:
        return relative

    year_match = YEAR_RE.search(text)
    if year_match:
        year = int(year_match.group(1))
        return _make_date_value(
            raw_text=text,
            normalized_start=date(year, 1, 1),
            normalized_end=date(year, 12, 31),
            sort_date=date(year, 1, 1),
            precision=DatePrecision.YEAR,
        )

    return _make_date_value(
        raw_text=text,
        normalized_start=None,
        normalized_end=None,
        sort_date=None,
        precision=DatePrecision.UNKNOWN,
        resolution_note="Unable to parse date deterministically.",
    )


def parse_date_values(
    raw_texts: list[str],
    *,
    anchor_date: DateValue | date | None = None,
    anchor_event_id: str | None = None,
) -> list[DateValue]:
    return [
        parse_date_value(
            raw_text,
            anchor_date=anchor_date,
            anchor_event_id=anchor_event_id,
        )
        for raw_text in raw_texts
    ]


def _parse_relative_date(
    text: str,
    *,
    anchor_date: DateValue | date | None,
    anchor_event_id: str | None,
) -> DateValue | None:
    anchor = _extract_anchor_date(anchor_date)
    if anchor is None:
        return None

    lowered = text.lower()
    delta_days = None
    if lowered in {"later that day", "that day", "same day"}:
        delta_days = 0
    elif lowered in {"the following day", "the next day", "next day", "one day later"}:
        delta_days = 1
    elif lowered == "two days later":
        delta_days = 2
    elif lowered == "three days later":
        delta_days = 3
    elif lowered in {"the following week", "the next week", "one week later"}:
        delta_days = 7

    if delta_days is None:
        return None

    resolved = anchor + timedelta(days=delta_days)
    return _make_date_value(
        raw_text=text,
        normalized_start=resolved,
        normalized_end=resolved,
        sort_date=resolved,
        precision=DatePrecision.RELATIVE,
        anchor_event_id=anchor_event_id,
        resolution_note=f"Resolved relative date from anchor {anchor.isoformat()}.",
        is_inferred=True,
    )


def _extract_anchor_date(anchor_date: DateValue | date | None) -> date | None:
    if isinstance(anchor_date, date):
        return anchor_date
    if anchor_date is None:
        return None
    return anchor_date.sort_date or anchor_date.normalized_start


def _quarter_number(token: str) -> int:
    mapping = {
        "first": 1,
        "1st": 1,
        "q1": 1,
        "second": 2,
        "2nd": 2,
        "q2": 2,
        "third": 3,
        "3rd": 3,
        "q3": 3,
        "fourth": 4,
        "4th": 4,
        "q4": 4,
    }
    return mapping[token]


def _make_date_value(
    *,
    raw_text: str,
    normalized_start: date | None,
    normalized_end: date | None,
    sort_date: date | None,
    precision: DatePrecision,
    anchor_event_id: str | None = None,
    resolution_note: str | None = None,
    is_inferred: bool = False,
) -> DateValue:
    return DateValue(
        raw_text=raw_text,
        normalized_start=normalized_start,
        normalized_end=normalized_end,
        sort_date=sort_date,
        precision=precision,
        anchor_event_id=anchor_event_id,
        resolution_note=resolution_note,
        is_inferred=is_inferred,
    )
```

---

## pipeline/enrich/__init__.py
```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pipeline.config import DEALS_DIR
from pipeline.enrich.classify import classify_proposals
from pipeline.enrich.cycles import assign_event_sequence, order_events, segment_cycles
from pipeline.enrich.features import compute_derived_metrics
from pipeline.extract.utils import atomic_write_json
from pipeline.models.enrichment import DealEnrichment
from pipeline.models.extraction import DealExtraction


ENRICHMENT_FILENAME = "deal_enrichment.json"


def run_enrichment(
    deal_slug: str,
    *,
    run_id: str,
    deals_dir: Path = DEALS_DIR,
) -> dict[str, Any]:
    qa_dir = deals_dir / deal_slug / "qa"
    enrich_dir = deals_dir / deal_slug / "enrich"
    enrich_dir.mkdir(parents=True, exist_ok=True)

    extraction = DealExtraction.model_validate_json((qa_dir / "extraction_canonical.json").read_text(encoding="utf-8"))
    ordered_events = order_events(extraction)
    event_sequence = assign_event_sequence(extraction)
    classifications = classify_proposals(extraction, ordered_events=ordered_events)
    cycles, event_cycle_map, formal_boundary_event_ids = segment_cycles(
        extraction,
        classifications=classifications,
    )
    derived_metrics = compute_derived_metrics(
        extraction,
        classifications=classifications,
        cycles=cycles,
        event_cycle_map=event_cycle_map,
    )

    enrichment = DealEnrichment(
        run_id=run_id,
        deal_slug=deal_slug,
        classifications=classifications,
        cycles=cycles,
        event_sequence=event_sequence,
        event_cycle_map=event_cycle_map,
        formal_boundary_event_ids=formal_boundary_event_ids,
        derived_metrics=derived_metrics,
    )
    atomic_write_json(enrich_dir / ENRICHMENT_FILENAME, enrichment.model_dump(mode="json"))
    return {
        "deal_slug": deal_slug,
        "cycle_count": len(cycles),
        "formal_proposal_count": derived_metrics.proposal_count_formal,
        "informal_proposal_count": derived_metrics.proposal_count_informal,
    }


__all__ = [
    "ENRICHMENT_FILENAME",
    "classify_proposals",
    "compute_derived_metrics",
    "run_enrichment",
    "segment_cycles",
]
```

---

## pipeline/enrich/classify.py
```python
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
```

---

## pipeline/enrich/cycles.py
```python
from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from pipeline.models.common import ClassificationLabel, EventType
from pipeline.models.enrichment import CycleRecord, ProposalClassification
from pipeline.models.extraction import CycleBoundaryEvent, DealExtraction, ProcessMarkerEvent, ProposalEvent


REINITIATION_EVENT_TYPES = {
    EventType.TARGET_SALE,
    EventType.TARGET_SALE_PUBLIC,
    EventType.BIDDER_SALE,
    EventType.BIDDER_INTEREST,
    EventType.ACTIVIST_SALE,
    EventType.IB_RETENTION,
    EventType.NDA,
}


def assign_event_sequence(extraction: DealExtraction) -> dict[str, int]:
    ordered = sorted(
        enumerate(extraction.events, start=1),
        key=lambda pair: _event_sort_key(pair[1], pair[0]),
    )
    return {event.event_id: ordinal for ordinal, (_original_index, event) in enumerate(ordered, start=1)}


def order_events(extraction: DealExtraction) -> list:
    return sorted(
        extraction.events,
        key=lambda event: _event_sort_key(event, 0),
    )


def segment_cycles(
    extraction: DealExtraction,
    *,
    classifications: dict[str, ProposalClassification] | None = None,
) -> tuple[list[CycleRecord], dict[str, str], dict[str, str | None]]:
    ordered_events = order_events(extraction)
    if not ordered_events:
        return [], {}, {}

    cycles: list[CycleRecord] = []
    event_cycle_map: dict[str, str] = {}
    formal_boundary_event_ids: dict[str, str | None] = {}

    cycle_index = 1
    current_cycle_id = f"cycle-{cycle_index:03d}"
    current_start_event_id = ordered_events[0].event_id
    current_basis = "single_cycle"

    def close_cycle(end_event_id: str | None, *, review_required: bool = False) -> None:
        nonlocal current_cycle_id, current_start_event_id, current_basis
        cycles.append(
            CycleRecord(
                cycle_id=current_cycle_id,
                start_event_id=current_start_event_id,
                end_event_id=end_event_id,
                boundary_basis=current_basis,
                review_required=review_required,
            )
        )
        formal_boundary_event_ids[current_cycle_id] = _first_formal_proposal(
            current_cycle_id,
            ordered_events,
            event_cycle_map,
            classifications or {},
        )

    previous_event = None
    for event in ordered_events:
        # Explicit restart begins a new cycle on the restart event itself.
        if event.event_type == EventType.RESTARTED and previous_event is not None:
            if previous_event.event_id in event_cycle_map and previous_event.event_id != current_start_event_id:
                close_cycle(previous_event.event_id)
            elif previous_event.event_id in event_cycle_map and previous_event.event_id == current_start_event_id:
                close_cycle(previous_event.event_id)
            cycle_index += 1
            current_cycle_id = f"cycle-{cycle_index:03d}"
            current_start_event_id = event.event_id
            current_basis = "explicit_terminated_restarted"

        elif previous_event is not None and _should_infer_new_cycle(previous_event, event):
            close_cycle(previous_event.event_id, review_required=True)
            cycle_index += 1
            current_cycle_id = f"cycle-{cycle_index:03d}"
            current_start_event_id = event.event_id
            current_basis = "implicit_reinitiation_after_gap"

        event_cycle_map[event.event_id] = current_cycle_id
        if event.event_type == EventType.TERMINATED:
            current_basis = "explicit_terminated_restarted"

        previous_event = event

    close_cycle(ordered_events[-1].event_id)
    return cycles, event_cycle_map, formal_boundary_event_ids


def _event_sort_key(event, original_index: int) -> tuple[date, int, int]:
    sort_date = event.date.sort_date or event.date.normalized_start or date.max
    start_line = 10**9
    if event.primary_span_ids:
        # Event sequence has already been preserved in input ordering; line-based sorting is handled in QA/export.
        start_line = original_index
    return (sort_date, start_line, original_index)


def _should_infer_new_cycle(previous_event, event) -> bool:
    prev_date = previous_event.date.sort_date or previous_event.date.normalized_start
    curr_date = event.date.sort_date or event.date.normalized_start
    if prev_date is None or curr_date is None:
        return False
    gap_days = (curr_date - prev_date).days
    if gap_days < 180:
        return False
    return event.event_type in REINITIATION_EVENT_TYPES


def _first_formal_proposal(
    cycle_id: str,
    ordered_events: Iterable,
    event_cycle_map: dict[str, str],
    classifications: dict[str, ProposalClassification],
) -> str | None:
    for event in ordered_events:
        if event_cycle_map.get(event.event_id) != cycle_id:
            continue
        if not isinstance(event, ProposalEvent):
            continue
        classification = classifications.get(event.event_id)
        if classification and classification.label == ClassificationLabel.FORMAL:
            return event.event_id
    return None
```

---

## pipeline/enrich/features.py
```python
from __future__ import annotations

from datetime import date

from pipeline.models.common import ActorRole, ClassificationLabel
from pipeline.models.enrichment import CycleRecord, DerivedMetrics, ProposalClassification
from pipeline.models.extraction import DealExtraction, NDAEvent, ProposalEvent


def compute_derived_metrics(
    extraction: DealExtraction,
    *,
    classifications: dict[str, ProposalClassification],
    cycles: list[CycleRecord],
    event_cycle_map: dict[str, str],
) -> DerivedMetrics:
    bidder_actors = [actor for actor in extraction.actors if actor.role == ActorRole.BIDDER]
    named_bidders = [actor for actor in bidder_actors if not actor.is_grouped]
    grouped_bidders = [actor for actor in bidder_actors if actor.is_grouped]

    proposal_events = [event for event in extraction.events if isinstance(event, ProposalEvent)]
    nda_events = [event for event in extraction.events if isinstance(event, NDAEvent)]

    formal_count = sum(
        1
        for event in proposal_events
        if classifications.get(event.event_id)
        and classifications[event.event_id].label == ClassificationLabel.FORMAL
    )
    informal_count = sum(
        1
        for event in proposal_events
        if classifications.get(event.event_id)
        and classifications[event.event_id].label == ClassificationLabel.INFORMAL
    )

    duration_days = _duration_days(extraction)
    peak_active_bidders = _peak_active_bidders(extraction)

    return DerivedMetrics(
        unique_bidders_total=len(bidder_actors),
        unique_bidders_named=len(named_bidders),
        unique_bidders_grouped=len(grouped_bidders),
        peak_active_bidders=peak_active_bidders,
        proposal_count_total=len(proposal_events),
        proposal_count_formal=formal_count,
        proposal_count_informal=informal_count,
        nda_count=len(nda_events),
        duration_days=duration_days,
        cycle_count=len(cycles),
    )


def _duration_days(extraction: DealExtraction) -> int | None:
    dated_events = [
        event.date.sort_date or event.date.normalized_start
        for event in extraction.events
        if event.date.sort_date is not None or event.date.normalized_start is not None
    ]
    if not dated_events:
        return None
    return (max(dated_events) - min(dated_events)).days


def _peak_active_bidders(extraction: DealExtraction) -> int | None:
    active: set[str] = set()
    peak = 0
    ordered = sorted(
        extraction.events,
        key=lambda event: (event.date.sort_date or event.date.normalized_start or date.max, event.event_id),
    )
    for event in ordered:
        for actor_id in event.actor_ids:
            active.add(actor_id)
        peak = max(peak, len(active))
    return peak or None
```

---

## pipeline/export/__init__.py
```python
from pipeline.export.alex_compat import ALEX_COMPAT_COLUMNS, build_alex_compat_rows
from pipeline.export.flatten import flatten_review_rows
from pipeline.export.review_csv import run_export, write_dict_csv, write_review_csv

__all__ = [
    "ALEX_COMPAT_COLUMNS",
    "build_alex_compat_rows",
    "flatten_review_rows",
    "run_export",
    "write_dict_csv",
    "write_review_csv",
]
```

---

## pipeline/export/flatten.py
```python
from __future__ import annotations

from collections import defaultdict

from pipeline.models.enrichment import DealEnrichment
from pipeline.models.export import ReviewRow
from pipeline.models.extraction import DealExtraction, ProposalEvent
from pipeline.models.qa import QAReport


def flatten_review_rows(
    extraction: DealExtraction,
    enrichment: DealEnrichment,
    qa_report: QAReport,
) -> list[ReviewRow]:
    actor_lookup = {actor.actor_id: actor for actor in extraction.actors}
    span_lookup = {span.span_id: span for span in extraction.spans}
    event_flags = _event_flags(qa_report)
    rows: list[ReviewRow] = []

    ordered_events = sorted(
        extraction.events,
        key=lambda event: enrichment.event_sequence.get(event.event_id, 10**9),
    )

    for event in ordered_events:
        span = _primary_span(event.primary_span_ids, span_lookup)
        classification = enrichment.classifications.get(event.event_id)
        actor_ids = event.actor_ids or [None]
        for actor_id in actor_ids:
            actor = actor_lookup.get(actor_id) if actor_id else None
            row = ReviewRow(
                deal_slug=extraction.deal_slug or "",
                target_name=extraction.seed.target_name,
                event_sequence=enrichment.event_sequence.get(event.event_id, 0),
                cycle_id=enrichment.event_cycle_map.get(event.event_id),
                event_id=event.event_id,
                event_type=event.event_type.value,
                actor_id=actor_id,
                actor_name=actor.display_name if actor else None,
                actor_role=actor.role.value if actor else None,
                bidder_kind=actor.bidder_kind.value if actor and actor.bidder_kind else None,
                listing_status=actor.listing_status.value if actor and actor.listing_status else None,
                geography=actor.geography.value if actor and actor.geography else None,
                raw_date=event.date.raw_text,
                sort_date=event.date.sort_date,
                value_per_share=event.terms.value_per_share if isinstance(event, ProposalEvent) else None,
                lower_per_share=event.terms.lower_per_share if isinstance(event, ProposalEvent) else None,
                upper_per_share=event.terms.upper_per_share if isinstance(event, ProposalEvent) else None,
                consideration_type=event.consideration_type.value if isinstance(event, ProposalEvent) else None,
                proposal_classification=classification.label.value if classification else None,
                classification_rule=classification.rule_id if classification else None,
                accession_number=span.accession_number if span else None,
                filing_type=span.filing_type if span else None,
                source_lines=_source_lines(span),
                source_quote_full=span.quote_text if span else "",
                qa_flags=event_flags.get(event.event_id, []),
            )
            rows.append(row)
    return rows


def _primary_span(primary_span_ids, span_lookup):
    for span_id in primary_span_ids:
        span = span_lookup.get(span_id)
        if span is not None:
            return span
    return None


def _source_lines(span) -> str:
    if span is None:
        return ""
    if span.start_line == span.end_line:
        return f"L{span.start_line}"
    return f"L{span.start_line}-L{span.end_line}"


def _event_flags(report: QAReport) -> dict[str, list[str]]:
    flags: dict[str, list[str]] = defaultdict(list)
    for finding in report.findings:
        targets = finding.related_event_ids or []
        for event_id in targets:
            flags[event_id].append(finding.code)
    return flags
```

---

## pipeline/export/review_csv.py
```python
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from pipeline.config import DEALS_DIR
from pipeline.export.alex_compat import ALEX_COMPAT_COLUMNS, build_alex_compat_rows
from pipeline.export.flatten import flatten_review_rows
from pipeline.extract.utils import atomic_write_json
from pipeline.models.enrichment import DealEnrichment
from pipeline.models.extraction import DealExtraction
from pipeline.models.export import ReviewRow
from pipeline.models.qa import QAReport


REVIEW_CSV_FILENAME = "events_long.csv"
ALEX_COMPAT_FILENAME = "alex_compat.csv"
CANONICAL_EXPORT_FILENAME = "canonical_export.json"
REFERENCE_METRICS_FILENAME = "reference_metrics.json"


def run_export(
    deal_slug: str,
    *,
    run_id: str,
    deals_dir: Path = DEALS_DIR,
) -> dict[str, Any]:
    qa_dir = deals_dir / deal_slug / "qa"
    enrich_dir = deals_dir / deal_slug / "enrich"
    export_dir = deals_dir / deal_slug / "export"
    export_dir.mkdir(parents=True, exist_ok=True)

    extraction = DealExtraction.model_validate_json((qa_dir / "extraction_canonical.json").read_text(encoding="utf-8"))
    qa_report = QAReport.model_validate_json((qa_dir / "report.json").read_text(encoding="utf-8"))
    enrichment = DealEnrichment.model_validate_json((enrich_dir / "deal_enrichment.json").read_text(encoding="utf-8"))

    review_rows = flatten_review_rows(extraction, enrichment, qa_report)
    alex_rows = build_alex_compat_rows(extraction, enrichment, qa_report)

    write_review_csv(export_dir / REVIEW_CSV_FILENAME, review_rows)
    write_dict_csv(export_dir / ALEX_COMPAT_FILENAME, alex_rows, fieldnames=ALEX_COMPAT_COLUMNS)
    atomic_write_json(
        export_dir / CANONICAL_EXPORT_FILENAME,
        {
            "run_id": run_id,
            "deal_slug": deal_slug,
            "extraction": extraction.model_dump(mode="json"),
            "qa_report": qa_report.model_dump(mode="json"),
            "enrichment": enrichment.model_dump(mode="json"),
        },
    )
    atomic_write_json(
        export_dir / REFERENCE_METRICS_FILENAME,
        {
            "deal_slug": deal_slug,
            "run_id": run_id,
            "passes_export_gate": qa_report.passes_export_gate,
            "blocker_count": qa_report.blocker_count,
            "warning_count": qa_report.warning_count,
            "actor_count": len(extraction.actors),
            "event_count": len(extraction.events),
            "proposal_count": enrichment.derived_metrics.proposal_count_total,
            "formal_proposal_count": enrichment.derived_metrics.proposal_count_formal,
            "informal_proposal_count": enrichment.derived_metrics.proposal_count_informal,
            "cycle_count": enrichment.derived_metrics.cycle_count,
        },
    )
    return {
        "deal_slug": deal_slug,
        "review_row_count": len(review_rows),
        "alex_row_count": len(alex_rows),
        "passes_export_gate": qa_report.passes_export_gate,
    }


def write_review_csv(path: Path, rows: list[ReviewRow]) -> None:
    fieldnames = list(ReviewRow.model_fields)
    serialised_rows: list[dict[str, Any]] = []
    for row in rows:
        payload = row.model_dump(mode="json")
        payload["qa_flags"] = "; ".join(payload["qa_flags"])
        serialised_rows.append(payload)
    write_dict_csv(path, serialised_rows, fieldnames=fieldnames)


def write_dict_csv(path: Path, rows: list[dict[str, Any]], *, fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})
    temp_path.replace(path)
```

---

## pipeline/export/alex_compat.py
```python
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
```
