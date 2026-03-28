"""Complexity-based deal classification for extraction routing."""

from __future__ import annotations

from typing import Literal

from skill_pipeline.pipeline_models.source import ChronologyBlock

SIMPLE_DEAL_MAX_BLOCKS: int = 150


def classify_deal_complexity(
    blocks: list[ChronologyBlock],
    *,
    max_blocks: int = SIMPLE_DEAL_MAX_BLOCKS,
) -> Literal["simple", "complex"]:
    """Classify a deal as simple or complex based on chronology block count."""
    if len(blocks) <= max_blocks:
        return "simple"
    return "complex"
