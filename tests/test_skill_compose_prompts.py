"""Prompt composition regression tests: chunks, checklist, render, integration."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from skill_pipeline.pipeline_models.prompt import PromptChunkWindow
from skill_pipeline.pipeline_models.source import (
    ChronologyBlock,
    EvidenceItem,
    EvidenceType,
)
from skill_pipeline.prompts.checklist import build_evidence_checklist
from skill_pipeline.prompts.chunks import (
    build_chunk_windows,
    estimate_block_tokens,
)
from skill_pipeline.prompts.render import render_actor_packet, render_event_packet


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_block(
    block_id: str,
    ordinal: int,
    clean_text: str,
    *,
    is_heading: bool = False,
) -> ChronologyBlock:
    """Build a minimal ChronologyBlock for testing."""
    return ChronologyBlock(
        block_id=block_id,
        document_id="doc-test",
        ordinal=ordinal,
        start_line=ordinal * 10,
        end_line=ordinal * 10 + 5,
        raw_text=clean_text,
        clean_text=clean_text,
        is_heading=is_heading,
        date_mentions=[],
        entity_mentions=[],
        evidence_density=0,
        temporal_phase="other",
    )


def _make_evidence(
    evidence_id: str,
    evidence_type: EvidenceType,
    raw_text: str,
    *,
    start_line: int = 1,
    end_line: int = 2,
) -> EvidenceItem:
    """Build a minimal EvidenceItem for testing."""
    return EvidenceItem(
        evidence_id=evidence_id,
        document_id="doc-test",
        accession_number="0001193125-16-000001",
        filing_type="SC 14D9",
        start_line=start_line,
        end_line=end_line,
        raw_text=raw_text,
        evidence_type=evidence_type,
        confidence="high",
    )


# ---------------------------------------------------------------------------
# Token estimator
# ---------------------------------------------------------------------------

class TestEstimateBlockTokens:
    def test_short_block(self):
        block = _make_block("B001", 0, "Hello world")
        tokens = estimate_block_tokens(block)
        assert tokens == math.ceil(2 * 1.35)

    def test_empty_clean_text(self):
        block = _make_block("B001", 0, "")
        assert estimate_block_tokens(block) == 0

    def test_deterministic(self):
        block = _make_block("B001", 0, "one two three four five")
        t1 = estimate_block_tokens(block)
        t2 = estimate_block_tokens(block)
        assert t1 == t2


# ---------------------------------------------------------------------------
# Chunk planner
# ---------------------------------------------------------------------------

class TestBuildChunkWindows:
    def test_single_pass_when_under_budget(self):
        """All blocks fit -> one single_pass window, no overlap."""
        blocks = [_make_block(f"B{i:03d}", i, "word " * 10) for i in range(3)]
        windows = build_chunk_windows(blocks, chunk_budget=99999)
        assert len(windows) == 1
        w = windows[0]
        assert w.chunk_count == 1
        assert w.target_block_ids == ["B000", "B001", "B002"]
        assert w.overlap_block_ids == []

    def test_chunked_windows_have_overlap(self):
        """Budget forces 2+ windows; overlap_block_ids must be populated."""
        # Each block ~14 tokens (10 words * 1.35 = 14)
        blocks = [_make_block(f"B{i:03d}", i, "word " * 10) for i in range(6)]
        windows = build_chunk_windows(blocks, chunk_budget=30)
        assert len(windows) > 1
        for w in windows:
            assert w.chunk_count == len(windows)
        # Interior windows should have overlap
        for w in windows[1:]:
            assert len(w.overlap_block_ids) > 0, f"window {w.window_id} has no overlap"

    def test_overlap_exactly_2_blocks(self):
        """Overlap is capped at overlap_blocks=2 adjacent blocks."""
        blocks = [_make_block(f"B{i:03d}", i, "word " * 10) for i in range(10)]
        windows = build_chunk_windows(blocks, chunk_budget=30, overlap_blocks=2)
        for w in windows:
            # Overlap should never exceed 2 leading + 2 trailing = 4
            assert len(w.overlap_block_ids) <= 4

    def test_target_block_ids_never_overlap_with_overlap_ids(self):
        """Target and overlap block ID sets must be disjoint."""
        blocks = [_make_block(f"B{i:03d}", i, "word " * 10) for i in range(8)]
        windows = build_chunk_windows(blocks, chunk_budget=30)
        for w in windows:
            target_set = set(w.target_block_ids)
            overlap_set = set(w.overlap_block_ids)
            assert target_set.isdisjoint(overlap_set), (
                f"window {w.window_id}: target and overlap share {target_set & overlap_set}"
            )

    def test_all_blocks_covered_by_target_ids(self):
        """Every block appears in exactly one window's target_block_ids."""
        blocks = [_make_block(f"B{i:03d}", i, "word " * 10) for i in range(8)]
        windows = build_chunk_windows(blocks, chunk_budget=30)
        all_target = []
        for w in windows:
            all_target.extend(w.target_block_ids)
        assert all_target == [f"B{i:03d}" for i in range(8)]

    def test_empty_blocks_raises(self):
        with pytest.raises(ValueError, match="blocks must not be empty"):
            build_chunk_windows([], chunk_budget=100)

    def test_zero_budget_raises(self):
        blocks = [_make_block("B000", 0, "word")]
        with pytest.raises(ValueError, match="chunk_budget must be positive"):
            build_chunk_windows(blocks, chunk_budget=0)

    def test_single_block_always_single_pass(self):
        block = _make_block("B000", 0, "word " * 5000)
        windows = build_chunk_windows([block], chunk_budget=10)
        # One block always goes into one window even if it exceeds budget
        assert len(windows) == 1
        assert windows[0].target_block_ids == ["B000"]

    def test_window_ids_are_sequential(self):
        blocks = [_make_block(f"B{i:03d}", i, "word " * 10) for i in range(6)]
        windows = build_chunk_windows(blocks, chunk_budget=30)
        for i, w in enumerate(windows):
            assert w.window_id == f"w{i}"
            assert w.chunk_index == i


# ---------------------------------------------------------------------------
# Evidence checklist
# ---------------------------------------------------------------------------

class TestBuildEvidenceChecklist:
    def test_empty_items_returns_empty(self):
        assert build_evidence_checklist([]) == ""

    def test_grouped_by_evidence_type(self):
        items = [
            _make_evidence("E001", EvidenceType.DATED_ACTION, "some text"),
            _make_evidence("E002", EvidenceType.FINANCIAL_TERM, "price text"),
            _make_evidence("E003", EvidenceType.DATED_ACTION, "another action"),
        ]
        result = build_evidence_checklist(items)
        # Both dated actions grouped under one header
        assert result.count("### Dated actions to extract") == 1
        assert result.count("### Financial terms to capture") == 1
        assert "E001" in result
        assert "E002" in result
        assert "E003" in result

    def test_bullets_include_evidence_id(self):
        items = [
            _make_evidence("E007", EvidenceType.ACTOR_IDENTIFICATION, "actor text"),
        ]
        result = build_evidence_checklist(items)
        assert "**E007**" in result

    def test_bullets_include_line_range(self):
        items = [
            _make_evidence(
                "E010", EvidenceType.PROCESS_SIGNAL, "signal",
                start_line=42, end_line=45,
            ),
        ]
        result = build_evidence_checklist(items)
        assert "L42-L45" in result

    def test_hint_parts_rendered(self):
        item = EvidenceItem(
            evidence_id="E020",
            document_id="doc",
            accession_number="0001193125-16-000001",
            filing_type="SC 14D9",
            start_line=1,
            end_line=2,
            raw_text="text",
            evidence_type=EvidenceType.FINANCIAL_TERM,
            confidence="high",
            date_text="March 15",
            value_hint="$42.00",
        )
        result = build_evidence_checklist([item])
        assert "date: March 15" in result
        assert "value: $42.00" in result


# ---------------------------------------------------------------------------
# Packet rendering helpers
# ---------------------------------------------------------------------------

ASSETS_DIR = Path(__file__).resolve().parent.parent / "skill_pipeline" / "prompt_assets"


def _single_pass_window(block_ids: list[str]) -> PromptChunkWindow:
    return PromptChunkWindow(
        window_id="w0",
        chunk_index=0,
        chunk_count=1,
        target_block_ids=block_ids,
        overlap_block_ids=[],
        estimated_tokens=100,
    )


def _chunked_window(
    target_ids: list[str],
    overlap_ids: list[str],
    *,
    chunk_index: int = 0,
    chunk_count: int = 2,
) -> PromptChunkWindow:
    return PromptChunkWindow(
        window_id=f"w{chunk_index}",
        chunk_index=chunk_index,
        chunk_count=chunk_count,
        target_block_ids=target_ids,
        overlap_block_ids=overlap_ids,
        estimated_tokens=100,
    )


class TestRenderActorPacket:
    def test_section_ordering(self):
        """Chronology blocks must appear before task instructions."""
        blocks = [_make_block("B000", 0, "chronology text here")]
        evidence = [_make_evidence("E001", EvidenceType.DATED_ACTION, "ev")]
        window = _single_pass_window(["B000"])

        _, _, rendered = render_actor_packet(
            deal_slug="test-deal",
            target_name="TestCo",
            accession_number="0001",
            filing_type="SC 14D9",
            window=window,
            blocks=blocks,
            evidence_items=evidence,
            prefix_asset_path=ASSETS_DIR / "actors_prefix.md",
            task_instructions="Extract actors now.",
        )

        chron_pos = rendered.index("<chronology_blocks>")
        task_pos = rendered.index("<task_instructions>")
        assert chron_pos < task_pos

    def test_no_actor_roster_in_actor_packet(self):
        blocks = [_make_block("B000", 0, "text")]
        window = _single_pass_window(["B000"])
        _, _, rendered = render_actor_packet(
            deal_slug="test",
            target_name="T",
            accession_number=None,
            filing_type=None,
            window=window,
            blocks=blocks,
            evidence_items=[],
            prefix_asset_path=ASSETS_DIR / "actors_prefix.md",
            task_instructions="Do it.",
        )
        assert "<actor_roster>" not in rendered

    def test_no_overlap_in_single_pass(self):
        blocks = [_make_block("B000", 0, "text")]
        window = _single_pass_window(["B000"])
        _, _, rendered = render_actor_packet(
            deal_slug="test",
            target_name="T",
            accession_number=None,
            filing_type=None,
            window=window,
            blocks=blocks,
            evidence_items=[],
            prefix_asset_path=ASSETS_DIR / "actors_prefix.md",
            task_instructions="Do it.",
        )
        assert "<overlap_context>" not in rendered

    def test_overlap_in_chunked_actor_packet(self):
        blocks = [
            _make_block("B000", 0, "first block"),
            _make_block("B001", 1, "second block"),
            _make_block("B002", 2, "third block"),
        ]
        window = _chunked_window(["B001"], ["B000", "B002"])
        _, _, rendered = render_actor_packet(
            deal_slug="test",
            target_name="T",
            accession_number=None,
            filing_type=None,
            window=window,
            blocks=blocks,
            evidence_items=[],
            prefix_asset_path=ASSETS_DIR / "actors_prefix.md",
            task_instructions="Do it.",
        )
        assert "<overlap_context>" in rendered
        assert "</overlap_context>" in rendered


class TestRenderEventPacket:
    def test_actor_roster_present(self):
        blocks = [_make_block("B000", 0, "text")]
        window = _single_pass_window(["B000"])
        _, _, rendered = render_event_packet(
            deal_slug="test",
            target_name="T",
            accession_number=None,
            filing_type=None,
            window=window,
            blocks=blocks,
            evidence_items=[],
            actor_roster_json='{"actors": []}',
            prefix_asset_path=ASSETS_DIR / "events_prefix.md",
            task_instructions="Extract events.",
        )
        assert "<actor_roster>" in rendered
        assert "</actor_roster>" in rendered

    def test_no_overlap_in_single_pass_event(self):
        blocks = [_make_block("B000", 0, "text")]
        window = _single_pass_window(["B000"])
        _, _, rendered = render_event_packet(
            deal_slug="test",
            target_name="T",
            accession_number=None,
            filing_type=None,
            window=window,
            blocks=blocks,
            evidence_items=[],
            actor_roster_json='{"actors": []}',
            prefix_asset_path=ASSETS_DIR / "events_prefix.md",
            task_instructions="Extract events.",
        )
        assert "<overlap_context>" not in rendered

    def test_overlap_in_chunked_event_packet(self):
        blocks = [
            _make_block("B000", 0, "leading context"),
            _make_block("B001", 1, "target content"),
            _make_block("B002", 2, "trailing context"),
        ]
        window = _chunked_window(["B001"], ["B000", "B002"])
        _, _, rendered = render_event_packet(
            deal_slug="test",
            target_name="T",
            accession_number=None,
            filing_type=None,
            window=window,
            blocks=blocks,
            evidence_items=[],
            actor_roster_json='{"actors": []}',
            prefix_asset_path=ASSETS_DIR / "events_prefix.md",
            task_instructions="Extract events.",
        )
        assert "<overlap_context>" in rendered

    def test_section_ordering_event(self):
        """Chronology blocks before task instructions in event packets."""
        blocks = [_make_block("B000", 0, "chron text")]
        window = _single_pass_window(["B000"])
        _, _, rendered = render_event_packet(
            deal_slug="test",
            target_name="T",
            accession_number=None,
            filing_type=None,
            window=window,
            blocks=blocks,
            evidence_items=[],
            actor_roster_json='{}',
            prefix_asset_path=ASSETS_DIR / "events_prefix.md",
            task_instructions="Do events.",
        )
        chron_pos = rendered.index("<chronology_blocks>")
        task_pos = rendered.index("<task_instructions>")
        assert chron_pos < task_pos

    def test_evidence_checklist_in_rendered(self):
        blocks = [_make_block("B000", 0, "text")]
        evidence = [_make_evidence("E099", EvidenceType.OUTCOME_FACT, "outcome text")]
        window = _single_pass_window(["B000"])
        _, _, rendered = render_event_packet(
            deal_slug="test",
            target_name="T",
            accession_number=None,
            filing_type=None,
            window=window,
            blocks=blocks,
            evidence_items=evidence,
            actor_roster_json='{}',
            prefix_asset_path=ASSETS_DIR / "events_prefix.md",
            task_instructions="Do it.",
        )
        assert "<evidence_checklist>" in rendered
        assert "E099" in rendered
