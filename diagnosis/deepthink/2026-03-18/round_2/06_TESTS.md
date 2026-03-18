# Test Suite

---

## tests/test_extract_pipeline.py
```python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.extract.actors import run_actor_extraction
from pipeline.extract.events import _invoke_event_call, run_event_extraction
from pipeline.extract.merge import merge_event_outputs
from pipeline.extract.recovery import build_recovery_block_subset, needs_recovery_audit, recover_missing_events
from pipeline.extract.utils import atomic_write_jsonl
from pipeline.llm.backend import LLMUsage, StructuredResult
from pipeline.llm.prompts import PromptPack
from pipeline.llm.token_budget import ComplexityClass
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
        if callable(self.token_count):
            return self.token_count(messages=messages, system=system, model=model)
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
                provider="test",
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


def test_run_actor_extraction_rejects_empty_structured_payload(tmp_path: Path):
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
    deals_dir = tmp_path / "deals"
    _write_source_inputs(tmp_path, slug=slug, blocks=blocks, evidence_items=[])

    backend = QueueBackend([ActorExtractionOutput()])

    with pytest.raises(ValueError, match="empty structured payload"):
        run_actor_extraction(slug, run_id="run-test", backend=backend, deals_dir=deals_dir)


def test_run_actor_extraction_uses_prompt_based_budgeting(tmp_path: Path):
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
            evidence_id="doc-2:E0001",
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

    def token_counter(*, messages, system, model=None):
        rendered = messages[0]["content"]
        if (
            system == PromptPack.ACTOR_SYSTEM_PROMPT
            and "<cross_filing_evidence>" in rendered
            and "doc-2:E0001" in rendered
            and "source_accession_number: doc-1" in rendered
        ):
            return 9_001
        return 123

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
        ],
        token_count=token_counter,
    )

    run_actor_extraction(slug, run_id="run-test", backend=backend, deals_dir=deals_dir)

    assert backend.calls[0]["kind"] == "count"
    assert backend.calls[0]["system"] == PromptPack.ACTOR_SYSTEM_PROMPT
    assert "<cross_filing_evidence>" in backend.calls[0]["messages"][0]["content"]
    assert backend.calls[1]["kind"] == "invoke"
    assert backend.calls[1]["max_tokens"] == 1_800


def test_run_actor_extraction_preserves_openai_gpt5_budget_floor(tmp_path: Path):
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
    deals_dir = tmp_path / "deals"
    _write_source_inputs(tmp_path, slug=slug, blocks=blocks, evidence_items=[])

    backend = QueueBackend(
        [
            ActorExtractionOutput(
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
                        evidence_refs=[RawEvidenceRef(block_id="B001", anchor_text="Party A contacted")],
                    )
                ]
            )
        ],
        token_count=9_001,
    )
    backend.provider = "openai"
    backend.model = "gpt-5.4"

    run_actor_extraction(slug, run_id="run-test", backend=backend, deals_dir=deals_dir)

    assert backend.calls[1]["max_tokens"] == 4_500


def test_run_actor_extraction_accepts_local_agent_backend(tmp_path: Path):
    from pipeline.llm import LocalAgentBackend

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
    deals_dir = tmp_path / "deals"
    _write_source_inputs(tmp_path, slug=slug, blocks=blocks, evidence_items=[])

    requests: list[dict] = []

    def bridge_runner(payload: dict) -> dict:
        requests.append(payload)
        return {
            "ok": True,
            "request_id": payload["request_id"],
            "raw_text": json.dumps(
                {
                    "actors": [
                        {
                            "actor_id": "party-a",
                            "display_name": "Party A",
                            "canonical_name": "Party A",
                            "aliases": [],
                            "role": "bidder",
                            "advisor_kind": None,
                            "bidder_kind": "financial",
                            "listing_status": "private",
                            "geography": "domestic",
                            "is_grouped": False,
                            "group_size": None,
                            "group_label": None,
                            "evidence_refs": [{"block_id": "B001", "anchor_text": "Party A contacted"}],
                            "notes": [],
                        }
                    ],
                    "count_assertions": [],
                    "unresolved_mentions": [],
                }
            ),
            "worker_id": "worker-1",
            "latency_ms": 12,
        }

    backend = LocalAgentBackend(bridge_runner=bridge_runner)

    summary = run_actor_extraction(slug, run_id="run-test", backend=backend, deals_dir=deals_dir)

    assert summary["actor_count"] == 1
    usage_payload = json.loads((deals_dir / slug / "extract" / "actor_usage.json").read_text(encoding="utf-8"))
    assert usage_payload["provider"] == "local_agent"
    assert requests[0]["schema_name"] == "ActorExtractionOutput"


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


def test_run_event_extraction_accepts_local_agent_backend(tmp_path: Path):
    from pipeline.llm import LocalAgentBackend

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
    deals_dir = tmp_path / "deals"
    _write_source_inputs(tmp_path, slug=slug, blocks=blocks, evidence_items=[])
    extract_dir = deals_dir / slug / "extract"
    extract_dir.mkdir(parents=True, exist_ok=True)
    actors_output = {
        "actors": [
            {
                "actor_id": "party-a",
                "display_name": "Party A",
                "canonical_name": "Party A",
                "aliases": [],
                "role": "bidder",
                "advisor_kind": None,
                "bidder_kind": "financial",
                "listing_status": "private",
                "geography": "domestic",
                "is_grouped": False,
                "group_size": None,
                "group_label": None,
                "evidence_refs": [{"block_id": "B001", "anchor_text": "Party A submitted"}],
                "notes": [],
            }
        ],
        "count_assertions": [],
        "unresolved_mentions": [],
    }
    (extract_dir / "actors_raw.json").write_text(json.dumps(actors_output, indent=2), encoding="utf-8")

    requests: list[dict] = []

    def bridge_runner(payload: dict) -> dict:
        requests.append(payload)
        return {
            "ok": True,
            "request_id": payload["request_id"],
            "raw_text": json.dumps(
                {
                    "events": [
                        {
                            "event_type": "proposal",
                            "date": {"raw_text": "July 5, 2016", "normalized_hint": None, "relative_to": None},
                            "actor_ids": ["party-a"],
                            "summary": "Party A submitted an indication of interest.",
                            "evidence_refs": [{"block_id": "B001", "anchor_text": "indication of interest"}],
                            "terms": {
                                "raw_text": "$25.00 per share",
                                "currency": "USD",
                                "value_per_share": "25.00",
                                "lower_per_share": None,
                                "upper_per_share": None,
                                "total_enterprise_value": None,
                                "is_range": False,
                            },
                            "consideration_type": "cash",
                            "whole_company_scope": True,
                            "whole_company_scope_note": None,
                            "formality_signals": {
                                "contains_range": False,
                                "mentions_indication_of_interest": True,
                                "mentions_preliminary": False,
                                "mentions_non_binding": False,
                                "mentions_binding_offer": False,
                                "includes_draft_merger_agreement": False,
                                "includes_marked_up_agreement": False,
                                "requested_binding_offer_via_process_letter": False,
                                "after_final_round_announcement": False,
                                "after_final_round_deadline": False,
                            },
                            "drop_reason_text": None,
                            "round_scope": None,
                            "deadline_date": None,
                            "executed_with_actor_id": None,
                            "boundary_note": None,
                            "nda_signed": True,
                            "notes": [],
                        }
                    ],
                    "exclusions": [],
                    "unresolved_mentions": [],
                    "coverage_notes": [],
                }
            ),
            "worker_id": "worker-2",
            "latency_ms": 15,
        }

    backend = LocalAgentBackend(bridge_runner=bridge_runner)

    summary = run_event_extraction(slug, run_id="run-test", backend=backend, deals_dir=deals_dir)

    assert summary["event_count"] == 1
    usage_payload = json.loads((extract_dir / "event_usage.json").read_text(encoding="utf-8"))
    assert usage_payload["calls"][0]["provider"] == "local_agent"
    assert requests[0]["schema_name"] == "EventExtractionOutput"


def test_event_complexity_uses_full_rendered_prompt_tokens(tmp_path: Path):
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
            evidence_id="doc-1:E0001",
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

    def token_counter(*, messages, system, model=None):
        rendered = messages[0]["content"]
        if (
            system == PromptPack.EVENT_SYSTEM_PROMPT
            and "<actor_roster>" in rendered
            and "<cross_filing_evidence>" in rendered
            and "party-a" in rendered
            and "doc-1:E0001" in rendered
        ):
            return 9_001
        return 123

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
                    ),
                ]
            )
        ],
        token_count=token_counter,
    )

    run_event_extraction(slug, run_id="run-test", backend=backend, deals_dir=deals_dir)

    usage_payload = json.loads((extract_dir / "event_usage.json").read_text(encoding="utf-8"))
    assert usage_payload["token_count"] == 9_001
    assert usage_payload["complexity"] == ComplexityClass.MODERATE.value
    assert backend.calls[0]["system"] == PromptPack.EVENT_SYSTEM_PROMPT
    assert "<actor_roster>" in backend.calls[0]["messages"][0]["content"]
    assert "<cross_filing_evidence>" in backend.calls[0]["messages"][0]["content"]


def test_classify_complexity_simple_requires_both_low_tokens_and_low_lines():
    from pipeline.llm.token_budget import classify_complexity, ComplexityClass

    result = classify_complexity(7000, 200, 5)

    assert result != ComplexityClass.SIMPLE
    assert result == ComplexityClass.MODERATE


def test_invoke_event_call_raises_budget_for_openai_gpt5():
    backend = QueueBackend([EventExtractionOutput(events=[])])
    backend.provider = "openai"
    backend.model = "gpt-5.4"

    _invoke_event_call(
        backend,
        seed_context={
            "deal_slug": "petsmart-inc",
            "target_name": "PetSmart",
            "accession_number": "doc-1",
            "filing_type": "DEFM14A",
        },
        actor_roster=[],
        blocks=[
            ChronologyBlock(
                block_id="B001",
                document_id="doc-1",
                ordinal=1,
                start_line=1,
                end_line=1,
                raw_text="Party A submitted an indication of interest.",
                clean_text="Party A submitted an indication of interest.",
                is_heading=False,
            )
        ],
        chunk_mode="single_pass",
        chunk_id="all",
        prior_round_context=[],
        evidence_items=[],
        model=None,
        complexity=ComplexityClass.MODERATE,
    )

    assert backend.calls[0]["max_tokens"] == 12_000


def test_invoke_event_call_raises_budget_for_anthropic_moderate_chunks():
    backend = QueueBackend([EventExtractionOutput(events=[])])
    backend.provider = "anthropic"
    backend.model = "claude-sonnet-4-6"

    _invoke_event_call(
        backend,
        seed_context={
            "deal_slug": "imprivata",
            "target_name": "Imprivata",
            "accession_number": "doc-1",
            "filing_type": "DEFM14A",
        },
        actor_roster=[],
        blocks=[
            ChronologyBlock(
                block_id="B001",
                document_id="doc-1",
                ordinal=1,
                start_line=1,
                end_line=1,
                raw_text="Party A submitted an indication of interest.",
                clean_text="Party A submitted an indication of interest.",
                is_heading=False,
            )
        ],
        chunk_mode="single_pass",
        chunk_id="all",
        prior_round_context=[],
        evidence_items=[],
        model=None,
        complexity=ComplexityClass.MODERATE,
    )

    assert backend.calls[0]["max_tokens"] == 10_000


def test_merge_event_outputs_handles_mixed_none_and_string_evidence_refs():
    mixed_event = RawEventRecord(
        event_type=EventType.NDA,
        date=RawDateHint(raw_text="July 5, 2016"),
        actor_ids=["party-a"],
        summary="Party A signed a confidentiality agreement.",
        evidence_refs=[
            RawEvidenceRef(block_id="B001", anchor_text="Party A submitted"),
            RawEvidenceRef(evidence_id="E0001", anchor_text="supporting evidence"),
        ],
    )

    merged = merge_event_outputs([EventExtractionOutput(events=[mixed_event])])

    assert len(merged.events) == 1


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
```

---

## tests/test_qa_stage.py
```python
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
from pipeline.extract.utils import _assert_evidence_ids_unique



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


def test_assert_evidence_ids_unique_raises_on_duplicates():
    items = [
        EvidenceItem(
            evidence_id="E0001",
            document_id="a",
            accession_number="a",
            filing_type="DEFM14A",
            start_line=1,
            end_line=1,
            raw_text="x",
            evidence_type=EvidenceType.FINANCIAL_TERM,
            confidence="high",
            matched_terms=["x"],
        ),
        EvidenceItem(
            evidence_id="E0001",
            document_id="b",
            accession_number="b",
            filing_type="PREM14A",
            start_line=1,
            end_line=1,
            raw_text="y",
            evidence_type=EvidenceType.FINANCIAL_TERM,
            confidence="high",
            matched_terms=["y"],
        ),
    ]

    import pytest

    with pytest.raises(ValueError, match="Duplicate evidence_id"):
        _assert_evidence_ids_unique(items)
```

---

## tests/test_quotes.py
```python
import json
from pathlib import Path

from pipeline.models.common import QuoteMatchType
from pipeline.models.source import ChronologyBlock
from pipeline.normalize.quotes import find_anchor_in_segment
from pipeline.normalize.spans import resolve_anchor_span, resolve_text_span
from pipeline.source.blocks import build_chronology_blocks
from pipeline.source.locate import select_chronology


RAW_DIR = Path(__file__).resolve().parent.parent / "raw"
DATA_DEALS = Path(__file__).resolve().parent.parent / "data" / "deals"


def test_exact_quote_match_resolves_single_line_span():
    lines = [
        "BACKGROUND OF THE MERGER",
        "",
        "On March 9, 2016, Thoma Bravo sent an unsolicited, non-binding indication of interest letter.",
        "",
        "OPINION OF FINANCIAL ADVISOR",
    ]
    blocks = [
        ChronologyBlock(
            block_id="B002",
            document_id="doc-1",
            ordinal=2,
            start_line=3,
            end_line=3,
            raw_text=lines[2],
            clean_text=lines[2],
            is_heading=False,
        )
    ]

    span = resolve_anchor_span(
        blocks,
        lines,
        block_id="B002",
        anchor_text="Thoma Bravo sent an unsolicited",
        document_id="doc-1",
        accession_number="0000000000-00-000001",
        filing_type="DEFM14A",
        span_id="span-1",
    )

    assert span.match_type == QuoteMatchType.EXACT
    assert span.start_line == 3
    assert span.end_line == 3
    assert span.quote_text == lines[2]


def test_normalized_quote_match_handles_curly_quotes_and_dashes():
    lines = [
        "BACKGROUND OF THE MERGER",
        "",
        "Party A’s “non-binding” indication—of interest remained under review.",
        "",
        "OTHER HEADING",
    ]
    blocks = [
        ChronologyBlock(
            block_id="B002",
            document_id="doc-2",
            ordinal=2,
            start_line=3,
            end_line=3,
            raw_text=lines[2],
            clean_text=lines[2],
            is_heading=False,
        )
    ]

    span = resolve_anchor_span(
        blocks,
        lines,
        block_id="B002",
        anchor_text='Party A\'s "non-binding" indication-of interest',
        document_id="doc-2",
        accession_number="0000000000-00-000002",
        filing_type="DEFM14A",
        span_id="span-2",
    )

    assert span.match_type == QuoteMatchType.NORMALIZED
    assert span.start_line == 3
    assert span.end_line == 3
    assert span.quote_text == lines[2]


def test_unresolved_quote_path_returns_unresolved_span():
    lines = [
        "BACKGROUND OF THE MERGER",
        "",
        "On March 9, 2016, Thoma Bravo sent an unsolicited, non-binding indication of interest letter.",
        "",
        "OPINION OF FINANCIAL ADVISOR",
    ]
    blocks = [
        ChronologyBlock(
            block_id="B002",
            document_id="doc-3",
            ordinal=2,
            start_line=3,
            end_line=3,
            raw_text=lines[2],
            clean_text=lines[2],
            is_heading=False,
        )
    ]

    span = resolve_anchor_span(
        blocks,
        lines,
        block_id="B002",
        anchor_text="anchor text that is not present",
        document_id="doc-3",
        accession_number="0000000000-00-000003",
        filing_type="DEFM14A",
        span_id="span-3",
    )

    assert span.match_type == QuoteMatchType.UNRESOLVED
    assert span.resolution_note is not None
    assert span.start_line == 3
    assert span.end_line == 3


def test_apostrophe_stripped_matching_returns_fuzzy():
    match_type, start, end = find_anchor_in_segment(
        "the Company\x92s financial advisor, Barclays Capital Inc.",
        "the Companys financial advisor, Barclays Capital Inc.",
    )

    assert match_type == QuoteMatchType.FUZZY
    assert start is not None
    assert end is not None


def test_inline_quote_stripped_matching_returns_fuzzy():
    match_type, start, end = find_anchor_in_segment(
        'Goodwin Procter LLP (\x93Goodwin\x94) were in attendance.',
        "Goodwin Procter LLP (Goodwin) were in attendance.",
    )

    assert match_type == QuoteMatchType.FUZZY
    assert start is not None
    assert end is not None


def test_parenthetical_inserted_matching_returns_fuzzy():
    match_type, start, end = find_anchor_in_segment(
        'On December 14, 2014, PetSmart, Inc. (the "Company") entered into an Agreement and Plan of Merger.',
        "On December 14, 2014, PetSmart, Inc. entered into an Agreement and Plan of Merger",
    )

    assert match_type == QuoteMatchType.FUZZY
    assert start is not None
    assert end is not None


def test_compact_alnum_matching_returns_fuzzy_for_spacing_artifacts():
    match_type, start, end = find_anchor_in_segment(
        "G& W submitted a revised LOI together withmark-upsof the merger agreement and the voting agreement.",
        "together with mark-ups of the merger agreement",
    )

    assert match_type == QuoteMatchType.FUZZY
    assert start is not None
    assert end is not None


def test_paraphrase_anchor_stays_unresolved():
    match_type, start, end = find_anchor_in_segment(
        "it did not believe that the Board would be interested in a transaction",
        "the Board would not be interested",
    )

    assert match_type == QuoteMatchType.UNRESOLVED
    assert start is None
    assert end is None


def test_resolve_text_span_expands_one_line_for_split_date_prefix():
    raw_lines = [
        "On",
        "March 13, 2015, New Mountain Capital communicated that the $20.05 per share offer price was best and final.",
    ]

    span = resolve_text_span(
        raw_lines,
        start_line=2,
        end_line=2,
        block_ids=["B001"],
        anchor_text="On March 13, 2015",
        document_id="doc-1",
        accession_number="0000000000-00-000004",
        filing_type="DEFM14A",
        span_id="span-4",
    )

    assert span.match_type == QuoteMatchType.NORMALIZED
    assert span.start_line == 1
    assert span.end_line == 2


def test_resolve_text_span_expands_three_lines_for_late_line_continuation():
    raw_lines = [
        "From April 1 through April 17, 2013, sTec negotiated non-disclosure agreements and scheduled management",
        "presentations with interested parties. On April 4, 2013, sTec entered into a non-disclosure agreement with Company E, on April 10, it entered into a non-disclosure agreement with Company D, on",
        "April 11, it entered into a non-disclosure agreement with Company F, another",
        "27",
        "participant in the storage industry, and on April 17, it entered into a non-disclosure agreement with Company G.",
    ]

    span = resolve_text_span(
        raw_lines,
        start_line=1,
        end_line=3,
        block_ids=["B001"],
        anchor_text="it entered into a non-disclosure agreement with Company G",
        document_id="doc-1",
        accession_number="0000000000-00-000005",
        filing_type="DEFM14A",
        span_id="span-5",
    )

    assert span.match_type == QuoteMatchType.EXACT
    assert span.start_line == 5
    assert span.end_line == 5


def test_real_focus_filing_block_generates_canonical_quote_span():
    bookmark = json.loads((DATA_DEALS / "petsmart-inc" / "source" / "chronology.json").read_text(encoding="utf-8"))
    accession = bookmark["accession_number"]
    lines = (RAW_DIR / "petsmart-inc" / "filings" / f"{accession}.txt").read_text(encoding="utf-8").splitlines()
    selection = select_chronology(
        lines,
        document_id=accession,
        accession_number=accession,
        filing_type="DEFM14A",
    )
    blocks = build_chronology_blocks(lines, selection=selection)
    target_block = next(
        block
        for block in blocks
        if "JANA Partners filed a Schedule 13D" in block.clean_text
    )

    span = resolve_anchor_span(
        blocks,
        lines,
        block_id=target_block.block_id,
        anchor_text="JANA Partners filed a Schedule 13D",
        document_id=accession,
        accession_number=accession,
        filing_type="DEFM14A",
        span_id="span-real-1",
    )

    assert span.match_type == QuoteMatchType.EXACT
    assert span.start_line == 1119
    assert span.end_line == 1119
    assert "JANA Partners filed a Schedule 13D" in span.quote_text
```

---

## tests/test_llm_backend.py
```python
from __future__ import annotations

import asyncio
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import BaseModel, ConfigDict

from pipeline.config import PROJECT_ROOT
from pipeline.models.source import ChronologyBlock

from pipeline.llm import AnthropicBackend, LLMBackend, LLMUsage, StructuredResult
from pipeline.llm.backend import StructuredOutputExhaustedError, _augment_repair_validation_errors
from pipeline.llm.prompts import PromptPack
from pipeline.llm.schemas import ActorExtractionOutput, EventExtractionOutput, pydantic_to_anthropic_schema
from pipeline.llm.token_budget import (
    ComplexityClass,
    classify_complexity,
    count_chronology_tokens,
    estimate_max_output_tokens,
    plan_event_chunks,
)


PROMPT_SPEC_PATH = PROJECT_ROOT / "docs" / "plans" / "2026-03-16-prompt-engineering-spec.md"


class TinyOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str


class FakeAnthropicAsyncMessages:
    def __init__(self, responses: list[SimpleNamespace] | None = None, *, token_count: int = 0) -> None:
        self.responses = list(responses or [])
        self.token_count = token_count
        self.create_calls: list[dict] = []
        self.count_calls: list[dict] = []

    async def create(self, **kwargs):
        self.create_calls.append(kwargs)
        if not self.responses:
            raise AssertionError("No fake responses queued for create().")
        return self.responses.pop(0)

    async def count_tokens(self, **kwargs):
        self.count_calls.append(kwargs)
        return SimpleNamespace(input_tokens=self.token_count)


class FakeAnthropicAsyncClient:
    def __init__(self, responses: list[SimpleNamespace] | None = None, *, token_count: int = 0) -> None:
        self.messages = FakeAnthropicAsyncMessages(responses=responses, token_count=token_count)


class FakeOpenAICompletions:
    def __init__(self, responses: list[SimpleNamespace] | None = None) -> None:
        self.responses = list(responses or [])
        self.create_calls: list[dict] = []

    async def create(self, **kwargs):
        self.create_calls.append(kwargs)
        if not self.responses:
            raise AssertionError("No fake responses queued for create().")
        return self.responses.pop(0)


class FakeOpenAIAsyncClient:
    def __init__(self, responses: list[SimpleNamespace] | None = None) -> None:
        self.chat = SimpleNamespace(completions=FakeOpenAICompletions(responses=responses))


class RecordingTokenBackend:
    def __init__(self, token_count: int) -> None:
        self.token_count = token_count
        self.calls: list[dict] = []

    async def acount_tokens(self, *, messages, system, model=None):
        self.calls.append({"messages": messages, "system": system, "model": model})
        return self.token_count


class ConcurrencyMessages:
    def __init__(self, response_factory) -> None:
        self.response_factory = response_factory
        self.active = 0
        self.max_active = 0
        self.create_calls: list[dict] = []

    async def create(self, **kwargs):
        self.create_calls.append(kwargs)
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0.01)
        self.active -= 1
        return self.response_factory('{"value": "ok"}')

    async def count_tokens(self, **kwargs):
        return SimpleNamespace(input_tokens=123)


class ConcurrencyClient:
    def __init__(self, response_factory) -> None:
        self.messages = ConcurrencyMessages(response_factory)


def _contains_key(value, key: str) -> bool:
    if isinstance(value, dict):
        if key in value:
            return True
        return any(_contains_key(child, key) for child in value.values())
    if isinstance(value, list):
        return any(_contains_key(child, key) for child in value)
    return False


def _extract_fenced_block(markdown_text: str, heading: str) -> str:
    pattern = rf"## {re.escape(heading)}\n\n```(?:\w+)?\n(.*?)\n```"
    match = re.search(pattern, markdown_text, re.DOTALL)
    assert match is not None, f"Heading {heading!r} not found in prompt spec."
    return match.group(1).strip()


def _build_test_blocks() -> list[ChronologyBlock]:
    blocks: list[ChronologyBlock] = []
    for index in range(4):
        block_id = f"B{index + 1:03d}"
        blocks.append(
            ChronologyBlock(
                block_id=block_id,
                document_id="doc-1",
                ordinal=index + 1,
                start_line=100 + index,
                end_line=100 + index,
                raw_text="alpha beta gamma delta",
                clean_text="alpha beta gamma delta",
                is_heading=False,
            )
        )
    return blocks


def _mock_openai_response(
    payload: str,
    *,
    prompt_tokens: int = 120,
    completion_tokens: int = 24,
    request_id: str = "resp_test_123",
    model: str = "gpt-4.1-mini",
    output_text: str | None = None,
    finish_reason: str = "stop",
) -> SimpleNamespace:
    usage = SimpleNamespace(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    message = SimpleNamespace(content=payload)
    choice = SimpleNamespace(message=message, finish_reason=finish_reason)
    return SimpleNamespace(
        id=request_id,
        model=model,
        choices=[choice],
        usage=usage,
        output_text=output_text,
    )


def test_llm_exports_and_config_constants_exist():
    from pipeline.config import (
        ANTHROPIC_API_KEY_ENV,
        DEFAULT_CONCURRENCY_LIMIT,
        DEFAULT_STRUCTURED_OUTPUT_MODE,
        LLM_JSON_REPAIR_ATTEMPTS,
        LLM_MAX_RETRIES,
        OPENAI_API_KEY_ENV,
    )

    assert AnthropicBackend
    assert LLMBackend
    assert LLMUsage
    assert StructuredResult
    assert ANTHROPIC_API_KEY_ENV == "ANTHROPIC_API_KEY"
    assert OPENAI_API_KEY_ENV == "OPENAI_API_KEY"
    assert DEFAULT_CONCURRENCY_LIMIT == 8
    assert LLM_MAX_RETRIES == 3
    assert LLM_JSON_REPAIR_ATTEMPTS == 2
    assert DEFAULT_STRUCTURED_OUTPUT_MODE == "prompted_json"


def test_build_backend_factory_supports_both_providers(monkeypatch: pytest.MonkeyPatch):
    from pipeline.llm import OpenAIBackend, build_backend

    monkeypatch.setenv("BIDS_LLM_PROVIDER", "openai")
    backend = build_backend(async_client=FakeOpenAIAsyncClient())
    assert isinstance(backend, OpenAIBackend)

    monkeypatch.setenv("BIDS_LLM_PROVIDER", "anthropic")
    backend = build_backend(async_client=FakeAnthropicAsyncClient())
    assert isinstance(backend, AnthropicBackend)


def test_build_backend_factory_supports_local_agent(monkeypatch: pytest.MonkeyPatch):
    from pipeline.llm import LocalAgentBackend, build_backend

    monkeypatch.setenv("BIDS_LLM_PROVIDER", "local_agent")
    backend = build_backend()

    assert isinstance(backend, LocalAgentBackend)


def test_prompt_pack_uses_verbatim_system_prompts_from_spec():
    spec_text = PROMPT_SPEC_PATH.read_text()

    assert PromptPack.ACTOR_SYSTEM_PROMPT == _extract_fenced_block(
        spec_text, "Actor Extraction System Prompt"
    )
    assert PromptPack.EVENT_SYSTEM_PROMPT == _extract_fenced_block(
        spec_text, "Event Extraction System Prompt"
    )
    assert PromptPack.RECOVERY_SYSTEM_PROMPT == _extract_fenced_block(
        spec_text, "Targeted Recovery Audit System Prompt"
    )
    assert PromptPack.REPAIR_SYSTEM_PROMPT == _extract_fenced_block(
        spec_text, "JSON Repair System Prompt"
    )


def test_prompt_pack_requires_explicit_proposal_economics_and_contiguous_anchors():
    assert "Proposal events require explicit economics." in PromptPack.EVENT_SYSTEM_PROMPT
    assert "anchor_text must be a contiguous verbatim substring" in PromptPack.EVENT_SYSTEM_PROMPT
    assert "anchor_text must be a contiguous verbatim substring" in PromptPack.ACTOR_SYSTEM_PROMPT


def test_render_actor_user_message_includes_context_and_blocks(sample_blocks):
    rendered = PromptPack.render_actor_user_message(
        {
            "deal_slug": "imprivata",
            "target_name": "Imprivata, Inc.",
            "acquirer_seed": "Thoma Bravo",
            "date_announced_seed": "2016-07-11",
            "accession_number": "0001193125-16-677939",
            "filing_type": "DEFM14A",
        },
        sample_blocks,
    )

    assert "<deal_context>" in rendered
    assert "deal_slug: imprivata" in rendered
    assert "source_accession_number: 0001193125-16-677939" in rendered
    assert "B001 [L1200-L1202]:" in rendered
    assert "B002 [L1203-L1205]:" in rendered


def test_render_event_user_message_serializes_actor_roster_and_chunk_context(
    sample_blocks, sample_actor_roster
):
    rendered = PromptPack.render_event_user_message(
        {
            "deal_slug": "imprivata",
            "target_name": "Imprivata, Inc.",
            "accession_number": "0001193125-16-677939",
            "filing_type": "DEFM14A",
        },
        sample_actor_roster,
        sample_blocks,
        chunk_mode="chunked",
        chunk_id="chunk-2",
        prior_round_context=["final_round_ann on July 1, 2016"],
    )

    assert "chunk_mode: chunked" in rendered
    assert "chunk_id: chunk-2" in rendered
    assert '"actor_id": "party-a"' in rendered
    assert "final_round_ann on July 1, 2016" in rendered


def test_render_structured_system_prompt_adds_json_contract():
    rendered = PromptPack.render_structured_system_prompt("You are a tester.", TinyOutput)

    assert rendered.startswith("You are a tester.")
    assert "<json_output_contract>" in rendered
    assert "Return exactly one JSON object" in rendered
    assert "value: string" in rendered


def test_prompt_version_is_stable_for_same_text():
    version_one = PromptPack.prompt_version("hello world")
    version_two = PromptPack.prompt_version("hello world")
    version_three = PromptPack.prompt_version("different text")

    assert version_one == version_two
    assert version_one != version_three
    assert re.fullmatch(r"[0-9a-f]{64}", version_one)


def test_pydantic_to_anthropic_schema_inlines_nested_models():
    schema = pydantic_to_anthropic_schema(ActorExtractionOutput)

    assert "$defs" not in schema
    assert not _contains_key(schema, "$ref")
    assert schema["additionalProperties"] is False
    actor_schema = schema["properties"]["actors"]["items"]
    assert actor_schema["additionalProperties"] is False
    evidence_ref_schema = actor_schema["properties"]["evidence_refs"]["items"]
    block_id_schema = evidence_ref_schema["properties"]["block_id"]
    assert any(option.get("type") == "string" for option in block_id_schema.get("anyOf", [])) or block_id_schema.get("type") == "string"


def test_extract_json_candidate_handles_fenced_json():
    from pipeline.llm.json_utils import extract_json_candidate

    raw = "Here you go:\n```json\n{\n  \"value\": \"ok\"\n}\n```"
    assert extract_json_candidate(raw) == '{\n  "value": "ok"\n}'


def test_augment_repair_validation_errors_adds_event_schema_guidance():
    errors = [
        "events.21: Value error, Proposal events require terms",
        "events.22.terms.total_enterprise_value: Input should be a valid decimal",
    ]

    augmented = _augment_repair_validation_errors("EventExtractionOutput", errors)

    assert augmented[:2] == errors
    assert any("remove that proposal event" in message for message in augmented)
    assert any("numeric money fields must be plain numbers only" in message for message in augmented)


def test_extract_json_candidate_does_not_drop_to_nested_array_when_top_level_object_is_malformed():
    from pipeline.llm.json_utils import extract_json_candidate

    raw = '{\n  "events": [\n    {"value": "ok"}\n  ],\n  "exclusions":\n'
    assert extract_json_candidate(raw) == raw.strip()


def test_schema_profile_keeps_pipeline_schemas_off_anthropic_native_path():
    from pipeline.llm.schema_profile import anthropic_native_safe, profile_model_schema

    tiny_profile = profile_model_schema(TinyOutput)
    actor_profile = profile_model_schema(ActorExtractionOutput)
    event_profile = profile_model_schema(EventExtractionOutput)

    assert anthropic_native_safe(tiny_profile) is True
    assert anthropic_native_safe(actor_profile) is False
    assert anthropic_native_safe(event_profile) is False
    assert event_profile.optional_param_count > actor_profile.optional_param_count


def test_count_chronology_tokens_renders_blocks_for_backend(sample_blocks):
    backend = RecordingTokenBackend(token_count=321)

    count = asyncio.run(
        count_chronology_tokens(backend, sample_blocks, model="claude-sonnet-4-20250514")
    )

    assert count == 321
    assert backend.calls[0]["system"] == ""
    assert "B001 [L1200-L1202]:" in backend.calls[0]["messages"][0]["content"]


@pytest.mark.parametrize(
    ("token_count", "line_count", "actor_count", "expected"),
    [
        (7000, 250, 5, ComplexityClass.MODERATE),
        (9000, 100, 5, ComplexityClass.MODERATE),
        (9000, 250, 5, ComplexityClass.MODERATE),
        (16000, 100, 5, ComplexityClass.COMPLEX),
        (9000, 250, 16, ComplexityClass.COMPLEX),
    ],
)
def test_classify_complexity_respects_thresholds(token_count, line_count, actor_count, expected):
    assert classify_complexity(token_count, line_count, actor_count) == expected


def test_plan_event_chunks_uses_one_block_overlap():
    chunks = plan_event_chunks(_build_test_blocks(), token_budget_per_chunk=10, overlap_blocks=1)

    assert [[block.block_id for block in chunk] for chunk in chunks] == [
        ["B001", "B002"],
        ["B002", "B003"],
        ["B003", "B004"],
    ]


def test_estimate_max_output_tokens_scales_with_complexity():
    simple_actor = estimate_max_output_tokens(ComplexityClass.SIMPLE, "actor")
    simple_event = estimate_max_output_tokens(ComplexityClass.SIMPLE, "event")
    complex_event = estimate_max_output_tokens(ComplexityClass.COMPLEX, "event")

    assert simple_actor > 0
    assert simple_event >= simple_actor
    assert complex_event > simple_event


def test_anthropic_prompted_json_mode_adds_contract_and_cache_control(mock_anthropic_response):
    client = FakeAnthropicAsyncClient(responses=[mock_anthropic_response('{"value": "ok"}')])
    backend = AnthropicBackend(async_client=client, model="claude-sonnet-4-20250514")

    result = asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=256,
        )
    )

    create_call = client.messages.create_calls[0]
    assert result.output.value == "ok"
    assert re.fullmatch(r"[0-9a-f]{64}", result.prompt_version)
    assert create_call["cache_control"] == {"type": "ephemeral"}
    assert "output_config" not in create_call or "format" not in create_call.get("output_config", {})
    assert "<json_output_contract>" in create_call["system"]
    assert result.structured_mode == "prompted_json"


def test_anthropic_auto_mode_uses_native_schema_for_tiny_output(mock_anthropic_response):
    client = FakeAnthropicAsyncClient(responses=[mock_anthropic_response('{"value": "ok"}')])
    backend = AnthropicBackend(
        async_client=client, model="claude-sonnet-4-20250514", structured_mode="auto"
    )

    asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=256,
        )
    )

    create_call = client.messages.create_calls[0]
    assert create_call["output_config"]["format"]["type"] == "json_schema"
    assert create_call["output_config"]["format"]["schema"]["additionalProperties"] is False


def test_anthropic_provider_native_mode_uses_native_schema_for_tiny_output(
    mock_anthropic_response,
):
    client = FakeAnthropicAsyncClient(responses=[mock_anthropic_response('{"value": "ok"}')])
    backend = AnthropicBackend(
        async_client=client,
        model="claude-sonnet-4-20250514",
        structured_mode="provider_native",
    )

    asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=256,
        )
    )

    create_call = client.messages.create_calls[0]
    assert create_call["output_config"]["format"]["type"] == "json_schema"
    assert create_call["output_config"]["format"]["schema"]["additionalProperties"] is False


def test_anthropic_auto_mode_falls_back_to_prompted_json_for_pipeline_schema(mock_anthropic_response):
    client = FakeAnthropicAsyncClient(
        responses=[
            mock_anthropic_response(
                '{"actors": [], "count_assertions": [], "unresolved_mentions": []}'
            )
        ]
    )
    backend = AnthropicBackend(
        async_client=client, model="claude-sonnet-4-20250514", structured_mode="auto"
    )

    asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=ActorExtractionOutput,
            max_tokens=256,
        )
    )

    create_call = client.messages.create_calls[0]
    assert "output_config" not in create_call or "format" not in create_call.get("output_config", {})
    assert "<json_output_contract>" in create_call["system"]


def test_anthropic_repairs_after_validation_error_without_native_schema(mock_anthropic_response):
    client = FakeAnthropicAsyncClient(
        responses=[
            mock_anthropic_response("{}"),
            mock_anthropic_response('```json\n{"value": "ok"}\n```', request_id="msg_repair_456"),
        ]
    )
    backend = AnthropicBackend(async_client=client, model="claude-sonnet-4-20250514")

    result = asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=256,
        )
    )

    assert result.output.value == "ok"
    assert result.repair_count == 1
    assert len(client.messages.create_calls) == 2
    assert PromptPack.REPAIR_SYSTEM_PROMPT in client.messages.create_calls[1]["system"]
    assert "format" not in client.messages.create_calls[1].get("output_config", {})


def test_anthropic_raises_structured_output_exhausted_error_after_repair_limit(
    mock_anthropic_response,
):
    client = FakeAnthropicAsyncClient(
        responses=[
            mock_anthropic_response("{}"),
            mock_anthropic_response("still not valid json"),
        ]
    )
    backend = AnthropicBackend(
        async_client=client,
        model="claude-sonnet-4-20250514",
        max_validation_retries=1,
    )

    with pytest.raises(StructuredOutputExhaustedError, match="Unable to validate TinyOutput"):
        asyncio.run(
            backend.ainvoke_structured(
                messages=[{"role": "user", "content": "hello"}],
                system="You are a tester.",
                output_schema=TinyOutput,
                max_tokens=256,
            )
        )


def test_anthropic_acount_tokens_uses_count_endpoint():
    client = FakeAnthropicAsyncClient(token_count=456)
    backend = AnthropicBackend(async_client=client, model="claude-sonnet-4-20250514")

    count = asyncio.run(
        backend.acount_tokens(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
        )
    )

    assert count == 456
    assert client.messages.count_calls[0]["model"] == "claude-sonnet-4-20250514"


def test_anthropic_sync_wrapper_invokes_structured_without_event_loop(mock_anthropic_response):
    client = FakeAnthropicAsyncClient(responses=[mock_anthropic_response('{"value": "ok"}')])
    backend = AnthropicBackend(async_client=client, model="claude-sonnet-4-20250514")

    result = backend.invoke_structured(
        messages=[{"role": "user", "content": "hello"}],
        system="You are a tester.",
        output_schema=TinyOutput,
        max_tokens=256,
    )

    assert result.output.value == "ok"


def test_concurrency_limit_caps_parallel_requests(mock_anthropic_response):
    client = ConcurrencyClient(mock_anthropic_response)
    backend = AnthropicBackend(
        async_client=client,
        model="claude-sonnet-4-20250514",
        concurrency_limit=2,
    )

    async def invoke_many() -> None:
        await asyncio.gather(
            *[
                backend.ainvoke_structured(
                    messages=[{"role": "user", "content": f"hello-{idx}"}],
                    system="You are a tester.",
                    output_schema=TinyOutput,
                    max_tokens=128,
                )
                for idx in range(5)
            ]
        )

    asyncio.run(invoke_many())

    assert client.messages.max_active <= 2


def test_effort_medium_is_sent_without_native_format(mock_anthropic_response):
    client = FakeAnthropicAsyncClient(responses=[mock_anthropic_response('{"value": "ok"}')])
    backend = AnthropicBackend(
        async_client=client, model="claude-sonnet-4-6", reasoning_effort="medium"
    )

    asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=256,
        )
    )

    create_call = client.messages.create_calls[0]
    assert create_call["output_config"]["effort"] == "medium"
    assert "format" not in create_call["output_config"]


def test_sonnet_46_pricing_is_registered():
    from pipeline.llm.anthropic_backend import PRICING

    assert "claude-sonnet-4-6" in PRICING


def test_openai_prompted_json_mode_uses_developer_message_and_reasoning_effort():
    from pipeline.llm import OpenAIBackend

    client = FakeOpenAIAsyncClient(responses=[_mock_openai_response('{"value": "ok"}')])
    backend = OpenAIBackend(
        async_client=client, model="gpt-4.1-mini", reasoning_effort="minimal"
    )

    result = asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=128,
        )
    )

    create_call = client.chat.completions.create_calls[0]
    assert result.output.value == "ok"
    assert create_call["messages"][0]["role"] == "developer"
    assert "<json_output_contract>" in create_call["messages"][0]["content"]
    assert create_call["reasoning_effort"] == "minimal"
    assert "response_format" not in create_call
    assert result.usage.provider == "openai"


def test_openai_prompted_json_mode_prefers_output_text():
    from pipeline.llm import OpenAIBackend

    client = FakeOpenAIAsyncClient(
        responses=[_mock_openai_response("ignored", output_text='{"value": "ok"}')]
    )
    backend = OpenAIBackend(async_client=client, model="gpt-4.1-mini")

    result = asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=128,
        )
    )

    assert result.output.value == "ok"


def test_openai_gpt5_omits_explicit_temperature():
    from pipeline.llm import OpenAIBackend

    client = FakeOpenAIAsyncClient(responses=[_mock_openai_response('{"value": "ok"}')])
    backend = OpenAIBackend(
        async_client=client,
        model="gpt-5.4",
        reasoning_effort="high",
    )

    asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=128,
        )
    )

    create_call = client.chat.completions.create_calls[0]
    assert create_call["reasoning_effort"] == "high"
    assert "temperature" not in create_call


def test_openai_raises_when_length_truncated_response_has_no_visible_text():
    from pipeline.llm import OpenAIBackend

    client = FakeOpenAIAsyncClient(
        responses=[
            _mock_openai_response(
                "",
                model="gpt-5.4-2026-03-05",
                completion_tokens=1800,
                finish_reason="length",
            )
        ]
    )
    backend = OpenAIBackend(
        async_client=client,
        model="gpt-5.4",
        reasoning_effort="high",
    )

    with pytest.raises(ValueError, match="exhausted max_completion_tokens"):
        asyncio.run(
            backend.ainvoke_structured(
                messages=[{"role": "user", "content": "hello"}],
                system="You are a tester.",
                output_schema=TinyOutput,
                max_tokens=1800,
            )
        )


def test_openai_auto_mode_uses_native_schema_for_tiny_output():
    from pipeline.llm import OpenAIBackend

    client = FakeOpenAIAsyncClient(responses=[_mock_openai_response('{"value": "ok"}')])
    backend = OpenAIBackend(async_client=client, model="gpt-4.1-mini", structured_mode="auto")

    asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=128,
        )
    )

    create_call = client.chat.completions.create_calls[0]
    assert create_call["response_format"]["type"] == "json_schema"
    assert create_call["response_format"]["json_schema"]["strict"] is True


def test_openai_repairs_after_validation_error():
    from pipeline.llm import OpenAIBackend

    client = FakeOpenAIAsyncClient(
        responses=[
            _mock_openai_response("{}"),
            _mock_openai_response('```json\n{"value": "ok"}\n```', request_id="resp_repair_456"),
        ]
    )
    backend = OpenAIBackend(async_client=client, model="gpt-4.1-mini")

    result = asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=128,
        )
    )

    assert result.output.value == "ok"
    assert result.repair_count == 1
    assert len(client.chat.completions.create_calls) == 2
    assert PromptPack.REPAIR_SYSTEM_PROMPT in client.chat.completions.create_calls[1]["messages"][0]["content"]


def test_openai_provider_native_mode_uses_native_schema_for_tiny_output():
    from pipeline.llm import OpenAIBackend

    client = FakeOpenAIAsyncClient(responses=[_mock_openai_response('{"value": "ok"}')])
    backend = OpenAIBackend(
        async_client=client,
        model="gpt-4.1-mini",
        structured_mode="provider_native",
    )

    asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=128,
        )
    )

    create_call = client.chat.completions.create_calls[0]
    assert create_call["response_format"]["type"] == "json_schema"
    assert create_call["response_format"]["json_schema"]["strict"] is True


def test_openai_count_tokens_uses_heuristic():
    from pipeline.llm import OpenAIBackend

    backend = OpenAIBackend(async_client=FakeOpenAIAsyncClient())

    count = asyncio.run(
        backend.acount_tokens(
            messages=[{"role": "user", "content": "hello world"}],
            system="You are a tester.",
        )
    )

    assert count > 0


def test_local_agent_backend_rejects_provider_native_mode():
    from pipeline.llm import LocalAgentBackend

    backend = LocalAgentBackend(
        structured_mode="provider_native",
        bridge_runner=lambda payload: {
            "ok": True,
            "request_id": payload["request_id"],
            "raw_text": '{"value": "ok"}',
            "worker_id": "worker-1",
            "latency_ms": 5,
        },
    )

    with pytest.raises(ValueError, match="provider-native structured output is disabled"):
        asyncio.run(
            backend.ainvoke_structured(
                messages=[{"role": "user", "content": "hello"}],
                system="You are a tester.",
                output_schema=TinyOutput,
                max_tokens=128,
            )
        )


def test_local_agent_backend_valid_json_returns_structured_result():
    from pipeline.llm import LocalAgentBackend

    requests: list[dict] = []

    def bridge_runner(payload: dict) -> dict:
        requests.append(payload)
        return {
            "ok": True,
            "request_id": payload["request_id"],
            "raw_text": '{"value": "ok"}',
            "worker_id": "worker-1",
            "latency_ms": 7,
        }

    backend = LocalAgentBackend(bridge_runner=bridge_runner)

    result = asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=128,
        )
    )

    assert result.output.value == "ok"
    assert result.usage.provider == "local_agent"
    assert result.structured_mode == "prompted_json"
    assert requests[0]["system_prompt"].startswith("You are a tester.")
    assert requests[0]["user_prompt"] == "hello"
    assert requests[0]["schema_name"] == "TinyOutput"


def test_local_agent_backend_uses_base_repair_loop_for_invalid_json():
    from pipeline.llm import LocalAgentBackend

    responses = iter(
        [
            {
                "ok": True,
                "request_id": "req-1",
                "raw_text": "not json",
                "worker_id": "worker-1",
                "latency_ms": 7,
            },
            {
                "ok": True,
                "request_id": "req-2",
                "raw_text": '{"value": "ok"}',
                "worker_id": "worker-2",
                "latency_ms": 8,
            },
        ]
    )
    calls: list[dict] = []

    def bridge_runner(payload: dict) -> dict:
        calls.append(payload)
        return next(responses)

    backend = LocalAgentBackend(bridge_runner=bridge_runner)

    result = asyncio.run(
        backend.ainvoke_structured(
            messages=[{"role": "user", "content": "hello"}],
            system="You are a tester.",
            output_schema=TinyOutput,
            max_tokens=128,
        )
    )

    assert result.output.value == "ok"
    assert result.repair_count == 1
    assert len(calls) == 2
    assert "<validation_errors>" in calls[1]["user_prompt"]


def test_local_agent_backend_raises_on_bridge_error():
    from pipeline.llm import LocalAgentBackend

    backend = LocalAgentBackend(
        bridge_runner=lambda payload: {
            "ok": False,
            "request_id": payload["request_id"],
            "raw_text": None,
            "worker_id": "worker-1",
            "latency_ms": 5,
            "error": "bridge unavailable",
        }
    )

    with pytest.raises(ValueError, match="bridge unavailable"):
        asyncio.run(
            backend.ainvoke_structured(
                messages=[{"role": "user", "content": "hello"}],
                system="You are a tester.",
                output_schema=TinyOutput,
                max_tokens=128,
            )
        )


def test_local_agent_backend_direct_repair_sets_schema_name():
    from pipeline.llm import LocalAgentBackend

    calls: list[dict] = []

    def bridge_runner(payload: dict) -> dict:
        calls.append(payload)
        return {
            "ok": True,
            "request_id": payload["request_id"],
            "raw_text": '{"value": "ok"}',
            "worker_id": "worker-1",
            "latency_ms": 5,
        }

    backend = LocalAgentBackend(bridge_runner=bridge_runner)

    result = asyncio.run(
        backend.arepair_structured(
            original_json="not json",
            errors=["<root>: invalid json"],
            output_schema=TinyOutput,
            max_tokens=128,
        )
    )

    assert result.output.value == "ok"
    assert calls[0]["schema_name"] == "TinyOutput"


def test_summarize_usage_includes_provider_and_repair_count():
    from pipeline.extract.utils import summarize_usage

    result = StructuredResult(
        output=TinyOutput(value="ok"),
        usage=LLMUsage(
            provider="anthropic",
            input_tokens=10,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
            output_tokens=5,
            cost_usd=0.01,
            latency_ms=123,
            request_id="req-1",
            model="claude-sonnet-4-20250514",
        ),
        raw_json='{"value": "ok"}',
        prompt_version="prompt-v1",
        repair_count=1,
        structured_mode="prompted_json",
    )

    summary = summarize_usage(result)
    assert summary["provider"] == "anthropic"
    assert summary["repair_count"] == 1
    assert summary["structured_mode"] == "prompted_json"
```

---

## tests/test_enrichment_stage.py
```python
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
```

---

## tests/test_source_evidence.py
```python
from __future__ import annotations

from pipeline.models.source import EvidenceType
from pipeline.source.evidence import group_evidence_by_type, scan_document_evidence
from pipeline.source.supplementary import evidence_items_to_snippets


def test_scan_document_evidence_detects_key_evidence_types():
    lines = [
        "On March 9, 2016, Party A submitted a non-binding indication of interest of $25.00 to $27.00 per share.",
        "",
        "The Special Committee and its financial advisor discussed the draft merger agreement and due diligence process.",
        "",
        "The merger agreement was executed on March 30, 2016.",
    ]

    evidence = scan_document_evidence(lines, document_id="doc-1", filing_type="DEFM14A")
    evidence_types = {item.evidence_type for item in evidence}

    assert EvidenceType.DATED_ACTION in evidence_types
    assert EvidenceType.FINANCIAL_TERM in evidence_types
    assert EvidenceType.ACTOR_IDENTIFICATION in evidence_types
    assert EvidenceType.PROCESS_SIGNAL in evidence_types
    assert EvidenceType.OUTCOME_FACT in evidence_types

    grouped = group_evidence_by_type(evidence)
    assert grouped[EvidenceType.FINANCIAL_TERM][0].value_hint == "$25.00 to $27.00 per share"


def test_evidence_items_to_snippets_derives_press_release_and_activist_hints():
    lines = [
        "The company issued a press release regarding strategic alternatives.",
        "",
        "A shareholder later pushed for a strategic review.",
        "",
        "The board announced the merger agreement in another press release.",
    ]

    evidence = scan_document_evidence(lines, document_id="doc-2", filing_type="8-K")
    snippets = evidence_items_to_snippets(evidence)

    assert {snippet.event_hint for snippet in snippets} >= {
        "sale_press_release",
        "activist_sale",
        "bid_press_release",
    }


def test_evidence_ids_are_globally_unique_across_filings():
    lines_a = ["", "On March 9, 2016, Thoma Bravo sent an indication of interest at $18.00 per share.", ""]
    lines_b = ["", "On July 12, 2016, Barclays Capital Inc. delivered its fairness opinion.", ""]

    items_a = scan_document_evidence(
        lines_a,
        document_id="filing-a",
        filing_type="DEFM14A",
        accession_number="0001-a",
    )
    items_b = scan_document_evidence(
        lines_b,
        document_id="filing-b",
        filing_type="PREM14A",
        accession_number="0001-b",
    )

    all_ids = [item.evidence_id for item in items_a + items_b]
    assert len(all_ids) == len(set(all_ids)), f"Duplicate evidence IDs: {all_ids}"
    for item in items_a:
        assert "0001-a" in item.evidence_id
    for item in items_b:
        assert "0001-b" in item.evidence_id
```

---

## Test Summary (remaining files)

- `tests/test_cli.py`: 10 tests
- `tests/test_dates.py`: 5 tests
- `tests/test_export_stage.py`: 3 tests
- `tests/test_local_agent_bridge.py`: 5 tests
- `tests/test_locate_reference.py`: 5 tests
- `tests/test_models_v2.py`: 7 tests
- `tests/test_parallel_preprocess.py`: 5 tests
- `tests/test_preprocess_source.py`: 1 tests
- `tests/test_raw_contract.py`: 3 tests
- `tests/test_raw_fetch.py`: 3 tests
- `tests/test_raw_stage.py`: 1 tests
- `tests/test_reference_offline_rebuild.py`: 1 tests
- `tests/test_schemas.py`: 3 tests
- `tests/test_seeds.py`: 4 tests
- `tests/test_seeds_registry.py`: 5 tests
- `tests/test_source_discovery.py`: 4 tests
- `tests/test_source.py`: 8 tests
- `tests/test_state.py`: 6 tests
- `tests/test_validate_stage.py`: 1 tests
