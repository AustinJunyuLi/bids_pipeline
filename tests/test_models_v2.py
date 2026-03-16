from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import TypeAdapter, ValidationError

from pipeline.models.common import (
    ConsiderationType,
    DatePrecision,
    EventType,
    QuoteMatchType,
    SCHEMA_VERSION,
)
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
    EventUnion,
)
from pipeline.models.source import (
    ChronologyCandidate,
    ChronologySelection,
    SeedDeal,
)


def _artifact_kwargs(artifact_type: str, *, deal_slug: str | None = "imprivata") -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": artifact_type,
        "created_at": datetime(2026, 3, 16, tzinfo=UTC),
        "pipeline_version": "0.1.0",
        "run_id": "run-1",
        "deal_slug": deal_slug,
    }


def _date_value(raw_text: str = "July 11, 2016") -> DateValue:
    return DateValue(
        raw_text=raw_text,
        normalized_start=date(2016, 7, 11),
        normalized_end=date(2016, 7, 11),
        sort_date=date(2016, 7, 11),
        precision=DatePrecision.EXACT_DAY,
    )


def _seed() -> SeedDeal:
    return SeedDeal(
        **_artifact_kwargs("seed_deal", deal_slug="imprivata"),
        target_name="Imprivata, Inc.",
        acquirer_seed="Thoma Bravo",
        date_announced_seed=date(2016, 7, 11),
        primary_url_seed="https://www.sec.gov/Archives/edgar/data/1285550/000119312516677939/d208987ddefm14a.htm",
        is_reference=True,
        seed_row_refs=["row-42"],
    )


def _chronology_selection() -> ChronologySelection:
    candidate = ChronologyCandidate(
        document_id="doc-1",
        heading_text="Background of the Merger",
        heading_normalized="background of the merger",
        start_line=1148,
        end_line=2376,
        score=900,
        source_methods=["txt_heading", "txt_search"],
        is_standalone_background=False,
        diagnostics={"line_count": 1228},
    )
    return ChronologySelection(
        **_artifact_kwargs("chronology_selection"),
        document_id="doc-1",
        accession_number="0001193125-16-677939",
        filing_type="DEFM14A",
        selected_candidate=candidate,
        confidence="high",
        adjudication_basis="Deterministic heading winner with no close competitor.",
        alternative_candidates=[],
        review_required=False,
    )


def _source_span(match_type: QuoteMatchType = QuoteMatchType.EXACT) -> SourceSpan:
    return SourceSpan(
        span_id="span-1",
        document_id="doc-1",
        accession_number="0001193125-16-677939",
        filing_type="DEFM14A",
        start_line=1200,
        end_line=1202,
        block_ids=["B001"],
        anchor_text="submitted a proposal",
        quote_text="Party A submitted a proposal.",
        quote_text_normalized="party a submitted a proposal.",
        match_type=match_type,
    )


def _proposal_terms() -> MoneyTerms:
    return MoneyTerms(
        raw_text="$25.00 per share",
        value_per_share=Decimal("25.00"),
        is_range=False,
    )


def _base_event_kwargs() -> dict:
    return {
        "event_id": "event-1",
        "date": _date_value(),
        "actor_ids": ["actor-1"],
        "primary_span_ids": ["span-1"],
        "summary": "A dated event occurred.",
    }


def _deal_extraction(*, span_match_type: QuoteMatchType = QuoteMatchType.EXACT) -> DealExtraction:
    return DealExtraction(
        **_artifact_kwargs("deal_extraction"),
        seed=_seed(),
        source_selection=_chronology_selection(),
        actors=[
            ActorRecord(
                actor_id="actor-1",
                display_name="Party A",
                canonical_name="party-a",
                aliases=["Bidder A"],
                role="bidder",
                bidder_kind="financial",
                listing_status="public",
                geography="domestic",
                is_grouped=False,
                first_mention_span_ids=["span-1"],
            )
        ],
        count_assertions=[
            CountAssertion(
                assertion_id="count-1",
                count=4,
                subject="final_round_invitees",
                qualifier_text="four bidders advanced",
                date=_date_value(),
                span_ids=["span-1"],
            )
        ],
        spans=[_source_span(match_type=span_match_type)],
        events=[
            ProposalEvent(
                **_base_event_kwargs(),
                event_type=EventType.PROPOSAL,
                terms=_proposal_terms(),
                consideration_type=ConsiderationType.CASH,
                whole_company_scope=True,
                formality_signals=FormalitySignals(),
            )
        ],
        exclusions=[
            ExtractionExclusion(
                exclusion_id="exclusion-1",
                category="partial_company_bid",
                block_ids=["B003"],
                explanation="The filing describes an asset purchase, not a whole-company proposal.",
            )
        ],
        unresolved_mentions=[],
        extraction_notes=[],
    )


@pytest.mark.parametrize(
    ("event", "expected_type"),
    [
        (
            ProcessMarkerEvent(
                **_base_event_kwargs(),
                event_type=EventType.TARGET_SALE,
            ),
            ProcessMarkerEvent,
        ),
        (
            NDAEvent(
                **_base_event_kwargs(),
                event_type=EventType.NDA,
            ),
            NDAEvent,
        ),
        (
            ProposalEvent(
                **_base_event_kwargs(),
                event_type=EventType.PROPOSAL,
                terms=_proposal_terms(),
                consideration_type=ConsiderationType.CASH,
                whole_company_scope=True,
                formality_signals=FormalitySignals(),
            ),
            ProposalEvent,
        ),
        (
            DropEvent(
                **_base_event_kwargs(),
                event_type=EventType.DROP,
                drop_reason_text="The bidder withdrew after due diligence.",
            ),
            DropEvent,
        ),
        (
            RoundEvent(
                **_base_event_kwargs(),
                event_type=EventType.FINAL_ROUND,
                round_scope="formal",
                deadline_date=_date_value("July 15, 2016"),
            ),
            RoundEvent,
        ),
        (
            OutcomeEvent(
                **_base_event_kwargs(),
                event_type=EventType.EXECUTED,
                executed_with_actor_id="actor-2",
            ),
            OutcomeEvent,
        ),
        (
            CycleBoundaryEvent(
                **_base_event_kwargs(),
                event_type=EventType.TERMINATED,
                boundary_note="The board ended the process.",
            ),
            CycleBoundaryEvent,
        ),
    ],
)
def test_event_family_models_validate(event, expected_type):
    assert isinstance(event, expected_type)


def test_deal_extraction_round_trip_serializes_event_union():
    extraction = _deal_extraction()
    payload = extraction.model_dump_json()

    restored = DealExtraction.model_validate_json(payload)

    assert restored.seed.target_name == "Imprivata, Inc."
    assert isinstance(restored.events[0], ProposalEvent)
    assert restored.events[0].terms.value_per_share == Decimal("25.00")


def test_event_union_round_trip_uses_discriminator():
    proposal = ProposalEvent(
        **_base_event_kwargs(),
        event_type=EventType.PROPOSAL,
        terms=_proposal_terms(),
        consideration_type=ConsiderationType.CASH,
        whole_company_scope=True,
        formality_signals=FormalitySignals(),
    )
    adapter = TypeAdapter(EventUnion)

    payload = adapter.dump_json(proposal)
    restored = adapter.validate_json(payload)

    assert isinstance(restored, ProposalEvent)
    assert restored.event_type == EventType.PROPOSAL


def test_grouped_actor_requires_group_metadata():
    with pytest.raises(ValidationError):
        ActorRecord(
            actor_id="actor-group",
            display_name="Unnamed financial buyers group 1",
            canonical_name="unnamed-financial-buyers-group-1",
            aliases=[],
            role="bidder",
            bidder_kind="financial",
            listing_status="private",
            geography="domestic",
            is_grouped=True,
            first_mention_span_ids=["span-1"],
        )


def test_proposal_requires_meaningful_terms():
    with pytest.raises(ValidationError):
        ProposalEvent(
            **_base_event_kwargs(),
            event_type=EventType.PROPOSAL,
            terms=MoneyTerms(raw_text=None, is_range=False),
            consideration_type=ConsiderationType.CASH,
            whole_company_scope=True,
            formality_signals=FormalitySignals(),
        )


def test_round_event_requires_round_scope():
    with pytest.raises(ValidationError):
        RoundEvent(
            **_base_event_kwargs(),
            event_type=EventType.FINAL_ROUND,
        )


def test_canonical_deal_extraction_rejects_unresolved_quote_spans():
    payload = _deal_extraction(
        span_match_type=QuoteMatchType.UNRESOLVED
    ).model_dump()
    payload["artifact_type"] = "canonical_extraction"

    with pytest.raises(ValidationError):
        DealExtraction.model_validate(payload)
