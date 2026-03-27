"""Prompt composition regression tests: chunks, checklist, render, integration."""

from __future__ import annotations

import math

import pytest

from skill_pipeline.pipeline_models.source import (
    ChronologyBlock,
    EvidenceItem,
    EvidenceType,
)
from skill_pipeline.prompts.chunks import (
    build_chunk_windows,
    estimate_block_tokens,
)


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
