from __future__ import annotations

import json
from pathlib import Path

from pipeline.extract.utils import atomic_write_json, atomic_write_jsonl
from pipeline.llm.schemas import (
    ActorExtractionOutput,
    EventExtractionOutput,
    RawActorRecord,
    RawDateHint,
    RawEventRecord,
    RawEvidenceRef,
    RawFormalitySignals,
    RawMoneyTerms,
)
from pipeline.models.common import ActorRole, BidderKind, ConsiderationType, EventType, GeographyFlag, ListingStatus
from pipeline.models.extraction import DealExtraction
from pipeline.models.qa import QAReport
from pipeline.models.source import ChronologyBlock, ChronologyCandidate, ChronologySelection, EvidenceItem, EvidenceType
from pipeline.qa.rules import run_qa



def _write_source_and_extract_inputs(tmp_path: Path, *, slug: str, missing_actor: bool = False) -> Path:
    deals_dir = tmp_path / "deals"
    source_dir = deals_dir / slug / "source"
    extract_dir = deals_dir / slug / "extract"
    filings_dir = source_dir / "filings"
    filings_dir.mkdir(parents=True, exist_ok=True)
    extract_dir.mkdir(parents=True, exist_ok=True)

    lines = [
        "Background of the Merger",
        "",
        "On July 1, 2016, Party A signed a confidentiality agreement.",
        "",
        "On July 5, 2016, Party A submitted an indication of interest of $25.00 per share.",
        "",
        "On July 10, 2016, the merger agreement was executed.",
    ]
    (filings_dir / "doc-1.txt").write_text("\n".join(lines), encoding="utf-8")

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
            end_line=7,
            score=500,
            source_methods=["txt_heading"],
            is_standalone_background=True,
        ),
        confidence="high",
        adjudication_basis="test",
        review_required=False,
    )
    blocks = [
        ChronologyBlock(
            block_id="B001",
            document_id="doc-1",
            ordinal=1,
            start_line=1,
            end_line=1,
            raw_text="Background of the Merger",
            clean_text="Background of the Merger",
            is_heading=True,
        ),
        ChronologyBlock(
            block_id="B002",
            document_id="doc-1",
            ordinal=2,
            start_line=3,
            end_line=3,
            raw_text=lines[2],
            clean_text=lines[2],
            is_heading=False,
        ),
        ChronologyBlock(
            block_id="B003",
            document_id="doc-1",
            ordinal=3,
            start_line=5,
            end_line=5,
            raw_text=lines[4],
            clean_text=lines[4],
            is_heading=False,
        ),
        ChronologyBlock(
            block_id="B004",
            document_id="doc-1",
            ordinal=4,
            start_line=7,
            end_line=7,
            raw_text=lines[6],
            clean_text=lines[6],
            is_heading=False,
        ),
    ]
    evidence_items = [
        EvidenceItem(
            evidence_id="E0001",
            document_id="doc-1",
            accession_number="doc-1",
            filing_type="DEFM14A",
            start_line=5,
            end_line=5,
            raw_text=lines[4],
            evidence_type=EvidenceType.FINANCIAL_TERM,
            confidence="high",
            matched_terms=["$25.00 per share"],
            value_hint="$25.00 per share",
        )
    ]
    atomic_write_json(source_dir / "chronology_selection.json", selection.model_dump(mode="json"))
    atomic_write_jsonl(source_dir / "chronology_blocks.jsonl", [block.model_dump(mode="json") for block in blocks])
    atomic_write_jsonl(source_dir / "evidence_items.jsonl", [item.model_dump(mode="json") for item in evidence_items])

    actor_output = ActorExtractionOutput(
        actors=[] if missing_actor else [
            RawActorRecord(
                actor_id="party-a",
                display_name="Party A",
                canonical_name="Party A",
                aliases=[],
                role=ActorRole.BIDDER,
                bidder_kind=BidderKind.FINANCIAL,
                listing_status=ListingStatus.PRIVATE,
                geography=GeographyFlag.DOMESTIC,
                is_grouped=False,
                evidence_refs=[RawEvidenceRef(block_id="B002", anchor_text="Party A signed")],
            )
        ],
    )
    events = [
        RawEventRecord(
            event_type=EventType.NDA,
            date=RawDateHint(raw_text="July 1, 2016"),
            actor_ids=[] if missing_actor else ["party-a"],
            summary="Party A signed a confidentiality agreement.",
            evidence_refs=[RawEvidenceRef(block_id="B002", anchor_text="signed a confidentiality agreement")],
        ),
        RawEventRecord(
            event_type=EventType.PROPOSAL,
            date=RawDateHint(raw_text="July 5, 2016"),
            actor_ids=["missing-actor"] if missing_actor else ["party-a"],
            summary="Party A submitted an indication of interest.",
            evidence_refs=[RawEvidenceRef(block_id="B003", anchor_text="indication of interest")],
            terms=RawMoneyTerms(value_per_share="25.00", is_range=False, raw_text="$25.00 per share"),
            consideration_type=ConsiderationType.CASH,
            whole_company_scope=True,
            formality_signals=RawFormalitySignals(mentions_indication_of_interest=True),
        ),
        RawEventRecord(
            event_type=EventType.EXECUTED,
            date=RawDateHint(raw_text="July 10, 2016"),
            actor_ids=[] if missing_actor else ["party-a"],
            summary="The merger agreement was executed.",
            evidence_refs=[RawEvidenceRef(block_id="B004", anchor_text="merger agreement was executed")],
        ),
    ]
    (extract_dir / "actors_raw.json").write_text(actor_output.model_dump_json(indent=2), encoding="utf-8")
    (extract_dir / "events_raw.json").write_text(EventExtractionOutput(events=events).model_dump_json(indent=2), encoding="utf-8")
    return deals_dir



def test_run_qa_builds_canonical_extraction_and_report(tmp_path: Path):
    deals_dir = _write_source_and_extract_inputs(tmp_path, slug="petsmart-inc")

    result = run_qa("petsmart-inc", run_id="run-test", deals_dir=deals_dir)

    assert result["passes_export_gate"] is True
    qa_dir = deals_dir / "petsmart-inc" / "qa"
    extraction = DealExtraction.model_validate_json((qa_dir / "extraction_canonical.json").read_text(encoding="utf-8"))
    report = QAReport.model_validate_json((qa_dir / "report.json").read_text(encoding="utf-8"))

    assert len(extraction.actors) == 1
    assert len(extraction.events) == 3
    assert extraction.spans[0].quote_text
    assert report.blocker_count == 0



def test_run_qa_flags_unknown_actor_references_as_blockers(tmp_path: Path):
    deals_dir = _write_source_and_extract_inputs(tmp_path, slug="petsmart-inc", missing_actor=True)

    result = run_qa("petsmart-inc", run_id="run-test", deals_dir=deals_dir)

    assert result["passes_export_gate"] is False
    report = QAReport.model_validate_json(
        (deals_dir / "petsmart-inc" / "qa" / "report.json").read_text(encoding="utf-8")
    )
    assert any(finding.code == "unknown_actor_reference" for finding in report.findings)
