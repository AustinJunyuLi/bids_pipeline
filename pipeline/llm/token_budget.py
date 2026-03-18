from __future__ import annotations

from enum import StrEnum

from pipeline.llm.prompts import PromptPack
from pipeline.models.source import ChronologyBlock


class ComplexityClass(StrEnum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


async def count_chronology_tokens(backend, blocks: list[ChronologyBlock], model: str) -> int:
    return await backend.acount_tokens(
        messages=[{"role": "user", "content": PromptPack.render_blocks(blocks)}],
        system="",
        model=model,
    )


def classify_complexity(
    token_count: int,
    line_count: int,
    actor_count: int,
) -> ComplexityClass:
    if actor_count > 15 or token_count > 15_000 or line_count > 400:
        return ComplexityClass.COMPLEX
    if token_count <= 8_000 and line_count <= 150:
        return ComplexityClass.SIMPLE
    return ComplexityClass.MODERATE


def plan_event_chunks(
    blocks: list[ChronologyBlock],
    *,
    token_budget_per_chunk: int = 5_000,
    overlap_blocks: int = 1,
) -> list[list[ChronologyBlock]]:
    if not blocks:
        return []

    overlap_blocks = max(0, overlap_blocks)
    estimated_tokens = [_estimate_block_tokens(block) for block in blocks]
    chunks: list[list[ChronologyBlock]] = []
    start = 0

    while start < len(blocks):
        total = 0
        end = start
        while end < len(blocks):
            block_tokens = estimated_tokens[end]
            if end > start and total + block_tokens > token_budget_per_chunk:
                break
            total += block_tokens
            end += 1
        chunks.append(blocks[start:end])
        if end >= len(blocks):
            break
        start = max(end - overlap_blocks, start + 1)

    return chunks


def estimate_max_output_tokens(complexity: ComplexityClass, call_type: str) -> int:
    budgets = {
        "actor": {
            ComplexityClass.SIMPLE: 1_200,
            ComplexityClass.MODERATE: 1_800,
            ComplexityClass.COMPLEX: 2_400,
        },
        "event": {
            ComplexityClass.SIMPLE: 3_000,
            ComplexityClass.MODERATE: 5_000,
            ComplexityClass.COMPLEX: 7_000,
        },
        "recovery": {
            ComplexityClass.SIMPLE: 1_000,
            ComplexityClass.MODERATE: 1_500,
            ComplexityClass.COMPLEX: 2_000,
        },
        "repair": {
            ComplexityClass.SIMPLE: 1_000,
            ComplexityClass.MODERATE: 1_000,
            ComplexityClass.COMPLEX: 1_000,
        },
    }
    if call_type not in budgets:
        raise ValueError(f"Unsupported call_type: {call_type}")
    return budgets[call_type][complexity]


def _estimate_block_tokens(block: ChronologyBlock) -> int:
    text = (block.clean_text or block.raw_text).strip()
    return max(1, len(text) // 4)
