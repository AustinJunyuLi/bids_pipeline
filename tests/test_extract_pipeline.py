from __future__ import annotations

import json
from pathlib import Path

from pipeline.extract.actors import run_actor_extraction
from pipeline.extract.events import run_event_extraction
from pipeline.extract.merge import merge_event_outputs
from pipeline.extract.recovery import build_recovery_block_subset, needs_recovery_audit, recover_missing_events
from pipeline.extract.utils import atomic_write_jsonl
from pipeline.llm.backend import LLMUsage, StructuredResult
from pipeline.llm.schemas import (
    ActorExtractionOutput,
    EventExtractionOutput,
    RawActorRecord,
    RawDateHint,
    RawEventRecord,
    RawEvidenceRef,
    RawExclusion,
    RawFormalitySignals,
    RawMoneyTerms,
    RecoveryAuditOutput,
    RecoveryTarget,
)
from pipeline.models.common import ActorRole, BidderKind, ConsiderationType, EventType, ListingStatus, GeographyFlag
from pipeline.models.source import ChronologyBlock, ChronologySelection, ChronologyCandidate, EvidenceItem, EvidenceType
from pipeline.extract.utils import atomic_write_json


class QueueBackend:
    def __init__(self, outputs, *, token_count: int = 5000) -> None:
        self.outputs = list(outputs)
        self.token_count = token_count
        self.calls: list[dict] = []

    def count_tokens(self, *, messages, system, model=None):
        self.calls.append({"kind": "count", "messages": messages, "system": system, "model": model})
        return self.token_count

    def invoke_structured(self, *, messages, system, output_schema, max_tokens, model=None, cache=True):
        self.calls.append(
            {
                "kind": "invoke",
                "messages": messages,
                "system": system,
                "model": model,
                "schema": output_schema.__name__,
                "max_tokens": max_tokens,
            }
        )
        if not self.outputs:
            raise AssertionError("No queued fake outputs left.")
        output = self.outputs.pop(0)
        if not isinstance(output, output_schema):
            raise AssertionError(f"Expected {output_schema.__name__}, got {type(output).__name__}")
        return StructuredResult(
            output=output,
            usage=LLMUsage(
                input_tokens=100,
                cache_creation_input_tokens=0,
                cache_read_input_tokens=0,
                output_tokens=50,
                cost_usd=0.01,
                latency_ms=10,
                request_id=f"req-{len(self.calls)}",
                model=model or "fake-model",
            ),
            raw_json=output.model_dump_json(),
            prompt_version="test-prompt",
        )


def _write_source_inputs(tmp_path: Path, *, slug: str, blocks: list[ChronologyBlock], evidence_items: list[EvidenceItem]) -> Path:
    source_dir = tmp_path / "deals" / slug / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
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
            score=999,
            source_methods=["txt_heading"],
            is_standalone_background=True,
        ),
        confidence="high",
        adjudication_basis="test",
        review_required=False,
    )
    atomic_write_json(source_dir / "chronology_selection.json", selection.model_dump(mode="json"))
    atomic_write_jsonl(source_dir / "chronology_blocks.jsonl", [block.model_dump(mode="json") for block in blocks])
    atomic_write_jsonl(source_dir / "evidence_items.jsonl", [item.model_dump(mode="json") for item in evidence_items])
    return source_dir


def test_run_actor_extraction_uses_blocks_and_evidence_appendix(tmp_path: Path):
    slug = "petsmart-inc"
    blocks = [
        ChronologyBlock(
            block_id="B001",
            document_id="doc-1",
            ordinal=1,
            start_line=1,
            end_line=1,
            raw_text="On July 1, 2016, Party A contacted the Company.",
            clean_text="On July 1, 2016, Party A contacted the Company.",
            is_heading=False,
        )
    ]
    evidence_items = [
        EvidenceItem(
            evidence_id="E0001",
            document_id="doc-2",
            accession_number="doc-2",
            filing_type="8-K",
            start_line=1,
            end_line=1,
            raw_text="A shareholder pushed for a strategic review.",
            evidence_type=EvidenceType.ACTOR_IDENTIFICATION,
            confidence="high",
            matched_terms=["shareholder"],
            actor_hint="shareholder",
        )
    ]
    deals_dir = tmp_path / "deals"
    _write_source_inputs(tmp_path, slug=slug, blocks=blocks, evidence_items=evidence_items)

    backend = QueueBackend(
        [
            ActorExtractionOutput(
                actors=[
                    RawActorRecord(
                        actor_id="party-a",
                        display_name="Party A",
                        canonical_name="Party A",
                        aliases=["Bidder A"],
                        role=ActorRole.BIDDER,
                        bidder_kind=BidderKind.FINANCIAL,
                        listing_status=ListingStatus.PRIVATE,
                        geography=GeographyFlag.DOMESTIC,
                        is_grouped=False,
                        evidence_refs=[RawEvidenceRef(block_id="B001", anchor_text="Party A contacted")],
                    )
                ]
            )
        ]
    )

    result = run_actor_extraction(slug, run_id="run-test", backend=backend, deals_dir=deals_dir)

    assert result["actor_count"] == 1
    actors_path = deals_dir / slug / "extract" / "actors_raw.json"
    assert actors_path.exists()
    rendered_prompt = backend.calls[0]["messages"][0]["content"]
    assert "B001 [L1-L1]:" in rendered_prompt
    assert "<cross_filing_evidence>" in rendered_prompt
    assert 'E0001 (actor_identification)' in rendered_prompt


def test_run_event_extraction_single_pass_writes_usage_and_events(tmp_path: Path):
    slug = "petsmart-inc"
    blocks = [
        ChronologyBlock(
            block_id="B001",
            document_id="doc-1",
            ordinal=1,
            start_line=1,
            end_line=1,
            raw_text="On July 5, 2016, Party A submitted an indication of interest of $25.00 per share.",
            clean_text="On July 5, 2016, Party A submitted an indication of interest of $25.00 per share.",
            is_heading=False,
        )
    ]
    evidence_items = [
        EvidenceItem(
            evidence_id="E0001",
            document_id="doc-1",
            accession_number="doc-1",
            filing_type="DEFM14A",
            start_line=1,
            end_line=1,
            raw_text=blocks[0].raw_text,
            evidence_type=EvidenceType.FINANCIAL_TERM,
            confidence="high",
            matched_terms=["$25.00 per share"],
            value_hint="$25.00 per share",
        )
    ]
    deals_dir = tmp_path / "deals"
    _write_source_inputs(tmp_path, slug=slug, blocks=blocks, evidence_items=evidence_items)
    extract_dir = deals_dir / slug / "extract"
    extract_dir.mkdir(parents=True, exist_ok=True)
    actors_output = ActorExtractionOutput(
        actors=[
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
                evidence_refs=[RawEvidenceRef(block_id="B001", anchor_text="Party A submitted")],
            )
        ]
    )
    (extract_dir / "actors_raw.json").write_text(actors_output.model_dump_json(indent=2), encoding="utf-8")

    backend = QueueBackend(
        [
            EventExtractionOutput(
                events=[
                    RawEventRecord(
                        event_type=EventType.NDA,
                        date=RawDateHint(raw_text="July 1, 2016"),
                        actor_ids=["party-a"],
                        summary="Party A signed a confidentiality agreement.",
                        evidence_refs=[RawEvidenceRef(block_id="B001", anchor_text="Party A submitted")],
                    ),
                    RawEventRecord(
                        event_type=EventType.PROPOSAL,
                        date=RawDateHint(raw_text="July 5, 2016"),
                        actor_ids=["party-a"],
                        summary="Party A submitted an indication of interest.",
                        evidence_refs=[RawEvidenceRef(block_id="B001", anchor_text="indication of interest")],
                        terms=RawMoneyTerms(value_per_share="25.00", is_range=False, raw_text="$25.00 per share"),
                        consideration_type=ConsiderationType.CASH,
                        whole_company_scope=True,
                        formality_signals=RawFormalitySignals(mentions_indication_of_interest=True),
                    ),
                    RawEventRecord(
                        event_type=EventType.EXECUTED,
                        date=RawDateHint(raw_text="July 10, 2016"),
                        actor_ids=["party-a"],
                        summary="The merger agreement was executed.",
                        evidence_refs=[RawEvidenceRef(block_id="B001", anchor_text="Party A submitted")],
                    )
                ]
            )
        ],
        token_count=200,
    )

    result = run_event_extraction(slug, run_id="run-test", backend=backend, deals_dir=deals_dir)

    assert result["event_count"] == 3
    assert result["chunk_mode"] == "single_pass"
    usage_payload = json.loads((extract_dir / "event_usage.json").read_text(encoding="utf-8"))
    assert usage_payload["chunk_mode"] == "single_pass"
    assert usage_payload["calls"][0]["request_id"] == "req-2"


def test_merge_and_recovery_helpers_fill_missing_proposals(sample_blocks):
    base = EventExtractionOutput(
        events=[],
        exclusions=[RawExclusion(category="other", explanation="none")],
        coverage_notes=["no proposal extracted"],
    )
    recovered = EventExtractionOutput(
        events=[
            RawEventRecord(
                event_type=EventType.PROPOSAL,
                date=RawDateHint(raw_text="July 5, 2016"),
                actor_ids=["party-a"],
                summary="Recovered proposal.",
                evidence_refs=[RawEvidenceRef(block_id="B002", anchor_text="indication of interest")],
                terms=RawMoneyTerms(value_per_share="25.00", is_range=False, raw_text="$25.00 per share"),
                consideration_type=ConsiderationType.CASH,
                whole_company_scope=True,
                formality_signals=RawFormalitySignals(mentions_indication_of_interest=True),
            )
        ]
    )
    merged = merge_event_outputs([base, recovered])
    assert len(merged.events) == 1

    evidence_items = [
        EvidenceItem(
            evidence_id="E0001",
            document_id="doc-1",
            accession_number="doc-1",
            filing_type="DEFM14A",
            start_line=1,
            end_line=1,
            raw_text="Party A submitted an indication of interest of $25.00 per share.",
            evidence_type=EvidenceType.FINANCIAL_TERM,
            confidence="high",
            matched_terms=["$25.00 per share"],
            value_hint="$25.00 per share",
        )
    ]
    assert needs_recovery_audit(base, evidence_items=evidence_items) is True

    recovery_output = RecoveryAuditOutput(
        recovery_targets=[
            RecoveryTarget(
                target_type="proposal",
                block_ids=["B002"],
                reason="financial term without proposal",
                anchor_text="indication of interest",
                suggested_event_types=[EventType.PROPOSAL],
            )
        ]
    )
    subset = build_recovery_block_subset(recovery_output, sample_blocks)
    assert [block.block_id for block in subset] == ["B002"]

    repaired = recover_missing_events(base, recovered)
    assert len(repaired.events) == 1
