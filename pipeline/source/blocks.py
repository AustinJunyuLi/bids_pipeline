from __future__ import annotations

from pipeline.models.source import ChronologyBlock, ChronologySelection
from pipeline.source.locate import looks_like_heading


def build_chronology_blocks(
    lines: list[str],
    *,
    selection: ChronologySelection,
) -> list[ChronologyBlock]:
    candidate = selection.selected_candidate
    if candidate is None:
        return []

    selected_lines = lines[candidate.start_line - 1 : candidate.end_line]
    blocks: list[ChronologyBlock] = []
    buffer: list[str] = []
    block_start: int | None = None
    ordinal = 1

    def flush(is_heading: bool = False) -> None:
        nonlocal buffer, block_start, ordinal
        if not buffer or block_start is None:
            return
        block_end = block_start + len(buffer) - 1
        raw_text = "\n".join(buffer)
        clean_text = " ".join(line.strip() for line in buffer if line.strip())
        blocks.append(
            ChronologyBlock(
                block_id=f"B{ordinal:03d}",
                document_id=candidate.document_id,
                ordinal=ordinal,
                start_line=block_start,
                end_line=block_end,
                raw_text=raw_text,
                clean_text=clean_text,
                is_heading=is_heading,
            )
        )
        ordinal += 1
        buffer = []
        block_start = None

    for offset, line in enumerate(selected_lines, start=candidate.start_line):
        stripped = line.strip()
        if not stripped:
            flush()
            continue

        line_is_heading = looks_like_heading(line)
        if line_is_heading and not buffer:
            buffer = [line]
            block_start = offset
            flush(is_heading=True)
            continue

        if block_start is None:
            block_start = offset
        buffer.append(line)

    flush()
    return blocks
