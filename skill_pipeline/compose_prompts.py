"""Deterministic prompt composition stage.

Loads source artifacts, builds chunk windows, renders provider-neutral prompt
packets, and writes a populated manifest.  This stage stops before any model
invocation and must not import provider SDKs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal
from uuid import uuid4

from skill_pipeline.config import PROJECT_ROOT
from skill_pipeline.paths import build_skill_paths, ensure_output_directories
from skill_pipeline.pipeline_models.common import PIPELINE_VERSION
from skill_pipeline.pipeline_models.prompt import (
    PromptChunkWindow,
    PromptPacketArtifact,
    PromptPacketManifest,
)
from skill_pipeline.pipeline_models.source import ChronologyBlock, EvidenceItem
from skill_pipeline.prompts.chunks import build_chunk_windows
from skill_pipeline.prompts.render import render_actor_packet, render_event_packet
from skill_pipeline.seeds import load_seed_entry


# ---------------------------------------------------------------------------
# Asset paths (relative to skill_pipeline package root)
# ---------------------------------------------------------------------------

_PACKAGE_DIR = Path(__file__).resolve().parent
_ASSETS_DIR = _PACKAGE_DIR / "prompt_assets"

_ACTORS_PREFIX = _ASSETS_DIR / "actors_prefix.md"
_EVENTS_PREFIX = _ASSETS_DIR / "events_prefix.md"
_EVENT_EXAMPLES = _ASSETS_DIR / "event_examples.md"


# ---------------------------------------------------------------------------
# JSONL loading helpers
# ---------------------------------------------------------------------------

def _load_blocks(path: Path) -> list[ChronologyBlock]:
    """Load chronology blocks from JSONL, fail fast on parse errors."""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Empty chronology blocks file: {path}")
    blocks: list[ChronologyBlock] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        blocks.append(ChronologyBlock.model_validate_json(line))
    if not blocks:
        raise ValueError(f"No valid chronology blocks in: {path}")
    blocks.sort(key=lambda b: b.ordinal)
    return blocks


def _load_evidence(path: Path) -> list[EvidenceItem]:
    """Load evidence items from JSONL."""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    items: list[EvidenceItem] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        items.append(EvidenceItem.model_validate_json(line))
    return items


def _load_actor_roster_json(path: Path) -> str:
    """Load the actor roster JSON as a raw string.  Fail fast if missing."""
    if not path.exists():
        raise FileNotFoundError(
            f"Actor roster not found: {path}. "
            f"Run actor extraction first (--mode actors), then run --mode events."
        )
    return path.read_text(encoding="utf-8").strip()


# ---------------------------------------------------------------------------
# Packet file writing
# ---------------------------------------------------------------------------

def _write_packet_files(
    packet_dir: Path,
    prefix_text: str,
    body_text: str,
    rendered_text: str,
) -> tuple[str, str, str]:
    """Write prefix.md, body.md, rendered.md and return their relative paths."""
    packet_dir.mkdir(parents=True, exist_ok=True)

    prefix_path = packet_dir / "prefix.md"
    body_path = packet_dir / "body.md"
    rendered_path = packet_dir / "rendered.md"

    prefix_path.write_text(prefix_text, encoding="utf-8")
    body_path.write_text(body_text, encoding="utf-8")
    rendered_path.write_text(rendered_text, encoding="utf-8")

    return str(prefix_path), str(body_path), str(rendered_path)


# ---------------------------------------------------------------------------
# Packet composition per family
# ---------------------------------------------------------------------------

def _compose_actor_packets(
    deal_slug: str,
    target_name: str,
    accession_number: str | None,
    filing_type: str | None,
    blocks: list[ChronologyBlock],
    evidence_items: list[EvidenceItem],
    windows: list[PromptChunkWindow],
    packets_dir: Path,
) -> list[PromptPacketArtifact]:
    """Compose actor extraction prompt packets for each chunk window."""
    task_instructions = (
        "Extract every actor (bidder, advisor, activist, target_board) "
        "from the chronology blocks above. Return actors, count_assertions, "
        "and unresolved_mentions. Use only facts grounded in the filing text."
    )
    packets: list[PromptPacketArtifact] = []

    for window in windows:
        packet_id = f"actors-{window.window_id}"
        chunk_mode: Literal["single_pass", "chunked"] = (
            "single_pass" if window.chunk_count == 1 else "chunked"
        )

        prefix_text, body_text, rendered_text = render_actor_packet(
            deal_slug=deal_slug,
            target_name=target_name,
            accession_number=accession_number,
            filing_type=filing_type,
            window=window,
            blocks=blocks,
            evidence_items=evidence_items,
            prefix_asset_path=_ACTORS_PREFIX,
            task_instructions=task_instructions,
        )

        packet_dir = packets_dir / packet_id
        prefix_path, body_path, rendered_path = _write_packet_files(
            packet_dir, prefix_text, body_text, rendered_text,
        )

        packets.append(PromptPacketArtifact(
            packet_id=packet_id,
            packet_family="actors",
            chunk_mode=chunk_mode,
            window_id=window.window_id,
            prefix_path=prefix_path,
            body_path=body_path,
            rendered_path=rendered_path,
            evidence_ids=[ei.evidence_id for ei in evidence_items],
        ))

    return packets


def _compose_event_packets(
    deal_slug: str,
    target_name: str,
    accession_number: str | None,
    filing_type: str | None,
    blocks: list[ChronologyBlock],
    evidence_items: list[EvidenceItem],
    windows: list[PromptChunkWindow],
    packets_dir: Path,
    actors_raw_path: Path,
) -> list[PromptPacketArtifact]:
    """Compose event extraction prompt packets for each chunk window."""
    actor_roster_json = _load_actor_roster_json(actors_raw_path)

    task_instructions = (
        "Extract all M&A process events from the chronology blocks above "
        "using the locked actor roster. Return events, exclusions, and "
        "coverage_notes. Use only facts grounded in the filing text."
    )
    packets: list[PromptPacketArtifact] = []

    for window in windows:
        packet_id = f"events-{window.window_id}"
        chunk_mode: Literal["single_pass", "chunked"] = (
            "single_pass" if window.chunk_count == 1 else "chunked"
        )

        prefix_text, body_text, rendered_text = render_event_packet(
            deal_slug=deal_slug,
            target_name=target_name,
            accession_number=accession_number,
            filing_type=filing_type,
            window=window,
            blocks=blocks,
            evidence_items=evidence_items,
            actor_roster_json=actor_roster_json,
            prefix_asset_path=_EVENTS_PREFIX,
            event_examples_asset_path=_EVENT_EXAMPLES,
            task_instructions=task_instructions,
        )

        packet_dir = packets_dir / packet_id
        prefix_path, body_path, rendered_path = _write_packet_files(
            packet_dir, prefix_text, body_text, rendered_text,
        )

        packets.append(PromptPacketArtifact(
            packet_id=packet_id,
            packet_family="events",
            chunk_mode=chunk_mode,
            window_id=window.window_id,
            prefix_path=prefix_path,
            body_path=body_path,
            rendered_path=rendered_path,
            evidence_ids=[ei.evidence_id for ei in evidence_items],
            actor_roster_source_path=str(actors_raw_path),
        ))

    return packets


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_compose_prompts(
    deal_slug: str,
    project_root: Path = PROJECT_ROOT,
    *,
    mode: Literal["actors", "events", "all"] = "all",
    chunk_budget: int = 6000,
) -> PromptPacketManifest:
    """Build prompt packet artifacts for a deal.

    Loads chronology_blocks.jsonl and evidence_items.jsonl, builds chunk
    windows, renders prompt packets with prefix/body/rendered files, and
    writes a populated manifest.

    Mode semantics:
        - ``actors``: compose actor extraction packets only.
        - ``events``: compose event extraction packets only.  Requires
          ``actors_raw.json`` to exist (fail fast if missing).
        - ``all``: compose actor packets only.  Event packets require a
          separate ``--mode events`` call after actor extraction completes.

    Args:
        deal_slug: Deal identifier.
        project_root: Repository root.
        mode: Which packet families to compose.
        chunk_budget: Target token budget per chunk window.

    Returns:
        The written PromptPacketManifest.

    Raises:
        FileNotFoundError: If required source artifacts are missing, or if
            mode is ``events`` and ``actors_raw.json`` does not exist.
    """
    paths = build_skill_paths(deal_slug, project_root=project_root)

    # Validate required source inputs exist
    missing: list[Path] = []
    if not paths.chronology_blocks_path.exists():
        missing.append(paths.chronology_blocks_path)
    if not paths.evidence_items_path.exists():
        missing.append(paths.evidence_items_path)
    if missing:
        missing_names = ", ".join(str(p) for p in missing)
        raise FileNotFoundError(
            f"Missing required source artifacts for compose-prompts: {missing_names}"
        )

    # Fail fast: --mode events requires actors_raw.json
    if mode == "events" and not paths.actors_raw_path.exists():
        raise FileNotFoundError(
            f"Actor roster not found at {paths.actors_raw_path}. "
            f"Run actor extraction first (--mode actors), then --mode events."
        )

    # Ensure output directories exist
    ensure_output_directories(paths)

    # Load source artifacts
    blocks = _load_blocks(paths.chronology_blocks_path)
    evidence_items = _load_evidence(paths.evidence_items_path)

    # Load deal context from seed registry
    seed = load_seed_entry(deal_slug, seeds_path=paths.seeds_path)

    # Get accession number from chronology selection if available
    accession_number: str | None = None
    filing_type: str | None = None
    selection_path = paths.source_dir / "chronology_selection.json"
    if selection_path.exists():
        sel_data = json.loads(selection_path.read_text(encoding="utf-8"))
        accession_number = sel_data.get("accession_number")
        filing_type = sel_data.get("filing_type")

    # Build chunk windows
    windows = build_chunk_windows(blocks, chunk_budget)

    run_id = f"compose-{uuid4().hex[:8]}"

    # Determine which families to compose
    compose_actors = mode in ("actors", "all")
    compose_events = mode == "events"

    all_packets: list[PromptPacketArtifact] = []
    asset_files: list[str] = []

    if compose_actors:
        actor_packets = _compose_actor_packets(
            deal_slug=deal_slug,
            target_name=seed.target_name,
            accession_number=accession_number,
            filing_type=filing_type,
            blocks=blocks,
            evidence_items=evidence_items,
            windows=windows,
            packets_dir=paths.prompt_packets_dir,
        )
        all_packets.extend(actor_packets)
        asset_files.append(str(_ACTORS_PREFIX))

    if compose_events:
        event_packets = _compose_event_packets(
            deal_slug=deal_slug,
            target_name=seed.target_name,
            accession_number=accession_number,
            filing_type=filing_type,
            blocks=blocks,
            evidence_items=evidence_items,
            windows=windows,
            packets_dir=paths.prompt_packets_dir,
            actors_raw_path=paths.actors_raw_path,
        )
        all_packets.extend(event_packets)
        asset_files.append(str(_EVENTS_PREFIX))
        asset_files.append(str(_EVENT_EXAMPLES))

    # Build manifest
    manifest = PromptPacketManifest(
        run_id=run_id,
        pipeline_version=PIPELINE_VERSION,
        deal_slug=deal_slug,
        source_accession_number=accession_number,
        packets=all_packets,
        asset_files=asset_files,
        notes=[
            f"mode={mode}",
            f"chunk_budget={chunk_budget}",
            f"source_blocks={len(blocks)}",
            f"source_evidence_items={len(evidence_items)}",
            f"chunk_windows={len(windows)}",
        ],
    )

    # Write manifest
    paths.prompt_manifest_path.write_text(
        manifest.model_dump_json(indent=2),
        encoding="utf-8",
    )

    return manifest
