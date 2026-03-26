from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from skill_pipeline.pipeline_models.raw import RawDocumentRegistry
from skill_pipeline.pipeline_models.source import ChronologyBlock, EvidenceItem, FrozenDocument
from skill_pipeline.raw.fetch import text_sha256


@dataclass(frozen=True)
class ResolvedFrozenDocumentPaths:
    txt_path: Path
    html_path: Path | None
    md_path: Path | None


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


def load_document_registry(path: Path) -> RawDocumentRegistry:
    return RawDocumentRegistry.model_validate_json(path.read_text(encoding="utf-8"))


def validate_frozen_document(
    document: FrozenDocument,
    *,
    project_root: Path,
    deal_slug: str,
) -> ResolvedFrozenDocumentPaths:
    txt_path = resolve_frozen_document_path(
        project_root,
        deal_slug,
        document.txt_path,
    )
    if not txt_path.exists():
        raise FileNotFoundError(f"Missing raw filing text: {txt_path}")

    txt_bytes = txt_path.read_bytes()
    if len(txt_bytes) != document.byte_count_txt:
        raise ValueError(
            f"Raw filing byte_count_txt mismatch for {document.document_id}: "
            f"registry={document.byte_count_txt} actual={len(txt_bytes)}"
        )

    # Use text_sha256 (CRLF-normalizing) intentionally: the registry records
    # a hash of LF-normalized bytes written by write_immutable_text, so on a
    # Windows checkout where git may convert LF→CRLF the byte_count check
    # above catches the size change while the text hash still verifies the
    # semantic content matches.  Switching to a raw-bytes hash would produce
    # a confusing double failure on CRLF-converted files.
    actual_sha256 = text_sha256(txt_bytes.decode("utf-8"))
    if actual_sha256 != document.sha256_txt:
        raise ValueError(
            f"Raw filing sha256_txt mismatch for {document.document_id}: "
            f"registry={document.sha256_txt} actual={actual_sha256}"
        )

    html_path = _resolve_optional_frozen_document_path(
        project_root,
        deal_slug,
        document.html_path,
    )
    md_path = _resolve_optional_frozen_document_path(
        project_root,
        deal_slug,
        document.md_path,
    )
    return ResolvedFrozenDocumentPaths(
        txt_path=txt_path,
        html_path=html_path,
        md_path=md_path,
    )


def resolve_frozen_document_path(
    project_root: Path,
    deal_slug: str,
    relative_path: str,
) -> Path:
    allowed_root = (project_root / "raw" / deal_slug / "filings").resolve()
    candidate = (project_root / relative_path).resolve()
    if not candidate.is_relative_to(allowed_root):
        raise ValueError(
            f"Frozen document path must stay under {allowed_root}: {relative_path}"
        )
    return candidate


def _resolve_optional_frozen_document_path(
    project_root: Path,
    deal_slug: str,
    relative_path: str | None,
) -> Path | None:
    if relative_path is None:
        return None
    return resolve_frozen_document_path(project_root, deal_slug, relative_path)
