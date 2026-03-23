"""Shared I/O loaders for JSONL and JSON artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from skill_pipeline.schemas.source import ChronologyBlock, EvidenceItem


def load_chronology_blocks(path: Path) -> list[ChronologyBlock]:
    blocks: list[ChronologyBlock] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        blocks.append(ChronologyBlock.model_validate_json(line))
    return blocks


def load_evidence_items(path: Path) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        items.append(EvidenceItem.model_validate_json(line))
    return items


def load_document_lines(filings_dir: Path) -> dict[str, list[str]]:
    if not filings_dir.exists():
        raise FileNotFoundError(
            f"Raw filings directory not found: {filings_dir}. "
            "Run 'skill-pipeline raw-fetch --deal <slug>' first."
        )
    lines_by_document: dict[str, list[str]] = {}
    for path in filings_dir.glob("*.txt"):
        lines_by_document[path.stem] = path.read_text(encoding="utf-8").splitlines()
    return lines_by_document


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
