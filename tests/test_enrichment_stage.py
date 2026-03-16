from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from pipeline.enrich import run_enrichment
from pipeline.models.common import (
    ActorRole,
    BidderKind,
    ConsiderationType,
    DatePrecision,
    EventType,
    GeographyFlag,
    ListingStatus,
)
from pipeline.models.extraction import (
    ActorRecord,
    CycleBoundaryEvent,
    DateValue,
    DealExtraction,
    FormalitySignals,
    MoneyTerms,
    ProcessMarkerEvent,
    ProposalEvent,
    RoundEvent,
)
from pipeline.models.source import ChronologyCandidate, ChronologySelection, SeedDeal



def _seed(slug: str) -> SeedDeal:
    return SeedDeal(
        run_id="run-test",
        deal_slug=slug,
        target_name="PetSmart, Inc.",
        acquirer_seed="BC Partners",
        date_announced_seed=date(2014, 12, 15),
        primary_url_seed="https://example.test/deal",
        is_reference=True,
        created_at=datetime.now(UTC),
    )



def _selection(slug: str) -> ChronologySelection:
    return ChronologySelection(
        run_id="run-test",
        deal_slug=slug,
        document_id="doc-1",
        accession_number="doc-1",
        filing_type="DEFM14A",
        selected_candidate=ChronologyCandidate(
            document_id="doc-1",
            heading_text="Background of the Merger",
            heading_normalized="background of the merger",
            start_line=1,
            end_line=50,
            score=500,
            source_methods=["txt_heading"],
            is_standalone_background=True,
        ),
        confidence="high",
        adjudication_basis="test",
        review_required=False,
    )



def _date(raw: str, value: date) -> DateValue:
    return DateValue(
        raw_text=raw,
        normalized_start=value,
        normalized_end=value,
        sort_date=value,
        precision=DatePrecision.EXACT_DAY,
    )



def _write_extraction(tmp_path: Path, slug: str) -> Path:
    deals_dir = tmp_path / "deals"
    qa_dir = deals_dir / slug / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)
    extraction = DealExtraction(
        run_id="run-test",
        deal_slug=slug,
        seed=_seed(slug),
        source_selection=_selection(slug),
        actors=[
            ActorRecord(
                actor_id="party-a",
                display_name="Party A",
                canonical_name="Party A",
                aliases=[],
                role=ActorRole.BIDDER,
                bidder_kind=BidderKind.FINANCIAL,
                listing_status=ListingStatus.PRIVATE,
                geography=GeographyFlag.DOMESTIC,
                is_grouped=False,
                first_mention_span_ids=["span-1"],
            ),
            ActorRecord(
                actor_id="party-b",
                display_name="Party B",
                canonical_name="Party B",
                aliases=[],
                role=ActorRole.BIDDER,
                bidder_kind=BidderKind.STRATEGIC,
                listing_status=ListingStatus.PUBLIC,
                geography=GeographyFlag.NON_US,
                is_grouped=False,
                first_mention_span_ids=["span-2"],
            ),
        ],
        spans=[],
        events=[
            ProcessMarkerEvent(
                event_id="event-0001",
                event_type=EventType.TARGET_SALE,
                date=_date("January 1, 2016", date(2016, 1, 1)),
                actor_ids=[],
                primary_span_ids=[],
                summary="Board decided to explore a sale.",
            ),
            ProposalEvent(
                event_id="event-0002",
                event_type=EventType.PROPOSAL,
                date=_date("January 10, 2016", date(2016, 1, 10)),
                actor_ids=["party-a"],
                primary_span_ids=[],
                summary="Party A submitted a range bid.",
                terms=MoneyTerms(lower_per_share=Decimal("25.00"), upper_per_share=Decimal("27.00"), is_range=True),
                consideration_type=ConsiderationType.CASH,
                whole_company_scope=True,
                formality_signals=FormalitySignals(contains_range=True),
            ),
            RoundEvent(
                event_id="event-0003",
                event_type=EventType.FINAL_ROUND_ANN,
                date=_date("February 1, 2016", date(2016, 2, 1)),
                actor_ids=[],
                primary_span_ids=[],
                summary="Formal round announced.",
                round_scope="formal",
            ),
            ProposalEvent(
                event_id="event-0004",
                event_type=EventType.PROPOSAL,
                date=_date("February 5, 2016", date(2016, 2, 5)),
                actor_ids=["party-b"],
                primary_span_ids=[],
                summary="Party B submitted a binding bid with a draft merger agreement.",
                terms=MoneyTerms(value_per_share=Decimal("31.00"), is_range=False),
                consideration_type=ConsiderationType.CASH,
                whole_company_scope=True,
                formality_signals=FormalitySignals(includes_draft_merger_agreement=True),
            ),
            CycleBoundaryEvent(
                event_id="event-0005",
                event_type=EventType.TERMINATED,
                date=_date("May 1, 2016", date(2016, 5, 1)),
                actor_ids=[],
                primary_span_ids=[],
                summary="Process terminated.",
            ),
            CycleBoundaryEvent(
                event_id="event-0006",
                event_type=EventType.RESTARTED,
                date=_date("December 1, 2016", date(2016, 12, 1)),
                actor_ids=[],
                primary_span_ids=[],
                summary="Process restarted.",
            ),
        ],
    )
    (qa_dir / "extraction_canonical.json").write_text(extraction.model_dump_json(indent=2), encoding="utf-8")
    return deals_dir



def test_run_enrichment_classifies_proposals_and_segments_cycles(tmp_path: Path):
    deals_dir = _write_extraction(tmp_path, "petsmart-inc")

    result = run_enrichment("petsmart-inc", run_id="run-test", deals_dir=deals_dir)

    assert result["cycle_count"] == 2
    enrichment_path = deals_dir / "petsmart-inc" / "enrich" / "deal_enrichment.json"
    payload = enrichment_path.read_text(encoding="utf-8")
    assert '"event-0002"' in payload
    assert '"informal"' in payload
    assert '"formal"' in payload
