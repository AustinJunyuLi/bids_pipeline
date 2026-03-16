from __future__ import annotations

import csv
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

from pipeline.export.alex_compat import ALEX_COMPAT_COLUMNS, build_alex_compat_rows
from pipeline.export.flatten import flatten_review_rows
from pipeline.export.review_csv import run_export
from pipeline.models.common import (
    ActorRole,
    BidderKind,
    ClassificationLabel,
    ConsiderationType,
    DatePrecision,
    EventType,
    GeographyFlag,
    ListingStatus,
    ReviewSeverity,
)
from pipeline.models.enrichment import CycleRecord, DealEnrichment, DerivedMetrics, ProposalClassification
from pipeline.models.extraction import (
    ActorRecord,
    DateValue,
    DealExtraction,
    FormalitySignals,
    ProcessMarkerEvent,
    ProposalEvent,
    RoundEvent,
    SourceSpan,
    MoneyTerms,
)
from pipeline.models.qa import QAFinding, QAReport
from pipeline.models.source import ChronologyCandidate, ChronologySelection, SeedDeal



def _date(raw: str, value: date) -> DateValue:
    return DateValue(
        raw_text=raw,
        normalized_start=value,
        normalized_end=value,
        sort_date=value,
        precision=DatePrecision.EXACT_DAY,
    )



def _build_artifacts(slug: str):
    seed = SeedDeal(
        run_id="run-test",
        deal_slug=slug,
        target_name="PetSmart, Inc.",
        acquirer_seed="BC Partners",
        date_announced_seed=date(2014, 12, 15),
        primary_url_seed="https://example.test/deal",
        is_reference=True,
        created_at=datetime.now(UTC),
    )
    selection = ChronologySelection(
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
            end_line=10,
            score=100,
            source_methods=["txt_heading"],
            is_standalone_background=True,
        ),
        confidence="high",
        adjudication_basis="test",
        review_required=False,
    )
    actor_a = ActorRecord(
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
    )
    actor_b = ActorRecord(
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
    )
    spans = [
        SourceSpan(
            span_id="span-1",
            document_id="doc-1",
            accession_number="doc-1",
            filing_type="DEFM14A",
            start_line=5,
            end_line=5,
            quote_text="Party A submitted an indication of interest of $25.00 per share.",
            quote_text_normalized="party a submitted an indication of interest of $25.00 per share.",
            match_type="exact",
        ),
        SourceSpan(
            span_id="span-2",
            document_id="doc-1",
            accession_number="doc-1",
            filing_type="DEFM14A",
            start_line=7,
            end_line=7,
            quote_text="The board announced the final round.",
            quote_text_normalized="the board announced the final round.",
            match_type="exact",
        ),
    ]
    extraction = DealExtraction(
        run_id="run-test",
        deal_slug=slug,
        seed=seed,
        source_selection=selection,
        actors=[actor_a, actor_b],
        spans=spans,
        events=[
            ProcessMarkerEvent(
                event_id="event-0001",
                event_type=EventType.BIDDER_INTEREST,
                date=_date("January 2, 2016", date(2016, 1, 2)),
                actor_ids=["party-a", "party-b"],
                primary_span_ids=["span-2"],
                summary="Two bidders expressed interest.",
            ),
            ProposalEvent(
                event_id="event-0002",
                event_type=EventType.PROPOSAL,
                date=_date("January 5, 2016", date(2016, 1, 5)),
                actor_ids=["party-a"],
                primary_span_ids=["span-1"],
                summary="Party A submitted an informal bid.",
                terms=MoneyTerms(value_per_share=Decimal("25.00"), is_range=False),
                consideration_type=ConsiderationType.CASH,
                whole_company_scope=True,
                formality_signals=FormalitySignals(mentions_indication_of_interest=True),
            ),
            RoundEvent(
                event_id="event-0003",
                event_type=EventType.FINAL_ROUND_ANN,
                date=_date("January 10, 2016", date(2016, 1, 10)),
                actor_ids=[],
                primary_span_ids=["span-2"],
                summary="Final round announced.",
                round_scope="formal",
            ),
        ],
    )
    enrichment = DealEnrichment(
        run_id="run-test",
        deal_slug=slug,
        classifications={
            "event-0002": ProposalClassification(
                label=ClassificationLabel.INFORMAL,
                rule_id="I2_explicit_informal_language",
                rule_version="test",
            )
        },
        cycles=[CycleRecord(cycle_id="cycle-001", start_event_id="event-0001", end_event_id="event-0003", boundary_basis="single_cycle")],
        event_sequence={"event-0001": 1, "event-0002": 2, "event-0003": 3},
        event_cycle_map={"event-0001": "cycle-001", "event-0002": "cycle-001", "event-0003": "cycle-001"},
        formal_boundary_event_ids={"cycle-001": None},
        derived_metrics=DerivedMetrics(
            unique_bidders_total=2,
            unique_bidders_named=2,
            unique_bidders_grouped=0,
            peak_active_bidders=2,
            proposal_count_total=1,
            proposal_count_formal=0,
            proposal_count_informal=1,
            nda_count=0,
            duration_days=8,
            cycle_count=1,
        ),
    )
    report = QAReport(
        run_id="run-test",
        deal_slug=slug,
        blocker_count=0,
        warning_count=1,
        findings=[
            QAFinding(
                finding_id="f1",
                severity=ReviewSeverity.WARNING,
                code="note",
                message="test warning",
                related_event_ids=["event-0002"],
            )
        ],
        passes_export_gate=True,
    )
    return extraction, enrichment, report



def test_flatten_review_rows_expands_multi_actor_events():
    extraction, enrichment, report = _build_artifacts("petsmart-inc")
    rows = flatten_review_rows(extraction, enrichment, report)

    interest_rows = [row for row in rows if row.event_id == "event-0001"]
    assert len(interest_rows) == 2
    assert rows[0].target_name == "PetSmart, Inc."



def test_alex_compat_rows_have_47_columns_and_export_proposal_type():
    extraction, enrichment, report = _build_artifacts("petsmart-inc")
    rows = build_alex_compat_rows(extraction, enrichment, report)

    assert len(ALEX_COMPAT_COLUMNS) == 47
    assert set(rows[0]) == set(ALEX_COMPAT_COLUMNS)
    proposal_row = next(row for row in rows if row["event_id"] == "event-0002")
    assert proposal_row["bid_type"] == "informal"
    assert proposal_row["bid_note"] == ""



def test_run_export_writes_csv_and_json_artifacts(tmp_path: Path):
    extraction, enrichment, report = _build_artifacts("petsmart-inc")
    deals_dir = tmp_path / "deals"
    qa_dir = deals_dir / "petsmart-inc" / "qa"
    enrich_dir = deals_dir / "petsmart-inc" / "enrich"
    qa_dir.mkdir(parents=True, exist_ok=True)
    enrich_dir.mkdir(parents=True, exist_ok=True)
    (qa_dir / "extraction_canonical.json").write_text(extraction.model_dump_json(indent=2), encoding="utf-8")
    (qa_dir / "report.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    (enrich_dir / "deal_enrichment.json").write_text(enrichment.model_dump_json(indent=2), encoding="utf-8")

    result = run_export("petsmart-inc", run_id="run-test", deals_dir=deals_dir)

    assert result["review_row_count"] == 4
    export_dir = deals_dir / "petsmart-inc" / "export"
    with (export_dir / "alex_compat.csv").open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == ALEX_COMPAT_COLUMNS
        rows = list(reader)
        assert rows[2]["event_id"] == "event-0002"
    metrics = json.loads((export_dir / "reference_metrics.json").read_text(encoding="utf-8"))
    assert metrics["passes_export_gate"] is True
