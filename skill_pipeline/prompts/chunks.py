"""Deterministic whole-block chunk planner with exact 2-block overlap windows.

Estimates tokens from block text using a word-count heuristic and plans chunk
windows that never split a chronology block.  When all blocks fit the budget,
emits a single ``single_pass`` window.  Otherwise emits ordered ``chunked``
windows whose ``overlap_block_ids`` contain the 2 adjacent context blocks
outside the target window.
"""

from __future__ import annotations

import math

from skill_pipeline.pipeline_models.prompt import PromptChunkWindow
from skill_pipeline.pipeline_models.source import ChronologyBlock


def estimate_block_tokens(block: ChronologyBlock) -> int:
    """Return a deterministic token estimate for *block*.

    Uses ``ceil(word_count * 1.35)`` as a calibration heuristic for typical
    English prose.  SEC filing text with legal terms and dollar amounts may
    diverge -- validate against actual ``stec`` packet sizes in Plan 03.
    """
    word_count = len(block.clean_text.split())
    return math.ceil(word_count * 1.35)


def build_chunk_windows(
    blocks: list[ChronologyBlock],
    chunk_budget: int,
    *,
    overlap_blocks: int = 2,
) -> list[PromptChunkWindow]:
    """Plan chunk windows over *blocks* that fit *chunk_budget* tokens each.

    Args:
        blocks: Ordered chronology blocks (by ordinal).
        chunk_budget: Maximum target-block token budget per window.
        overlap_blocks: Number of adjacent context blocks to include as
            overlap outside each target window.  Fixed at 2.

    Returns:
        A list of :class:`PromptChunkWindow` instances.  One
        ``single_pass`` window when total tokens fit, otherwise ordered
        ``chunked`` windows.

    Raises:
        ValueError: If *blocks* is empty or *chunk_budget* is not positive.
    """
    if not blocks:
        raise ValueError("blocks must not be empty")
    if chunk_budget <= 0:
        raise ValueError("chunk_budget must be positive")

    # Pre-compute per-block token estimates
    token_map: dict[str, int] = {}
    for b in blocks:
        token_map[b.block_id] = estimate_block_tokens(b)

    total_tokens = sum(token_map.values())

    # Single-pass when everything fits
    if total_tokens <= chunk_budget:
        window = PromptChunkWindow(
            window_id="w0",
            chunk_index=0,
            chunk_count=1,
            target_block_ids=[b.block_id for b in blocks],
            overlap_block_ids=[],
            estimated_tokens=total_tokens,
        )
        return [window]

    # Greedy whole-block chunking
    windows: list[PromptChunkWindow] = []
    i = 0
    n = len(blocks)

    while i < n:
        target_ids: list[str] = []
        target_tokens = 0

        # Accumulate whole blocks until budget is reached
        while i < n:
            block_tok = token_map[blocks[i].block_id]
            # Always include at least one block per window
            if target_ids and target_tokens + block_tok > chunk_budget:
                break
            target_ids.append(blocks[i].block_id)
            target_tokens += block_tok
            i += 1

        windows.append(
            PromptChunkWindow(
                window_id="",  # placeholder, set below
                chunk_index=len(windows),
                chunk_count=0,  # placeholder, set below
                target_block_ids=target_ids,
                overlap_block_ids=[],  # placeholder, set below
                estimated_tokens=target_tokens,
            )
        )

    chunk_count = len(windows)

    # Build a block_id -> index lookup for overlap computation
    block_index: dict[str, int] = {b.block_id: idx for idx, b in enumerate(blocks)}

    for wi, win in enumerate(windows):
        win.window_id = f"w{wi}"
        win.chunk_count = chunk_count

        # Compute overlap: blocks adjacent to target window but outside it
        first_target_idx = block_index[win.target_block_ids[0]]
        last_target_idx = block_index[win.target_block_ids[-1]]

        overlap_ids: list[str] = []

        # Leading overlap: up to `overlap_blocks` blocks before the target
        for oi in range(
            max(0, first_target_idx - overlap_blocks), first_target_idx
        ):
            bid = blocks[oi].block_id
            if bid not in win.target_block_ids:
                overlap_ids.append(bid)

        # Trailing overlap: up to `overlap_blocks` blocks after the target
        for oi in range(
            last_target_idx + 1,
            min(n, last_target_idx + 1 + overlap_blocks),
        ):
            bid = blocks[oi].block_id
            if bid not in win.target_block_ids:
                overlap_ids.append(bid)

        win.overlap_block_ids = overlap_ids

    return windows
