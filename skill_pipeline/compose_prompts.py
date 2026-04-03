"""Deterministic prompt composition for the live v2 observation contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal
from uuid import uuid4

from skill_pipeline.complexity import classify_deal_complexity
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
from skill_pipeline.prompts.render import render_observation_v2_packet
from skill_pipeline.seeds import load_seed_entry


_PACKAGE_DIR = Path(__file__).resolve().parent
_ASSETS_DIR = _PACKAGE_DIR / "prompt_assets"
_OBSERVATIONS_V2_PREFIX = _ASSETS_DIR / "observations_v2_prefix.md"
_OBSERVATIONS_V2_EXAMPLES = _ASSETS_DIR / "observations_v2_examples.md"


def _load_blocks(path: Path) -> list[ChronologyBlock]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Empty chronology blocks file: {path}")
    blocks: list[ChronologyBlock] = []
    seen_ids: set[str] = set()
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        block = ChronologyBlock.model_validate_json(line)
        if block.block_id in seen_ids:
            raise ValueError(f"Duplicate block_id in chronology blocks: {block.block_id}")
        seen_ids.add(block.block_id)
        blocks.append(block)
    if not blocks:
        raise ValueError(f"No valid chronology blocks in: {path}")
    blocks.sort(key=lambda b: b.ordinal)
    return blocks


def _load_evidence(path: Path) -> list[EvidenceItem]:
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


def _filter_evidence_for_window(
    blocks: list[ChronologyBlock],
    evidence_items: list[EvidenceItem],
    window: PromptChunkWindow,
) -> list[EvidenceItem]:
    visible_ids = set(window.target_block_ids) | set(window.overlap_block_ids)
    visible_blocks = [block for block in blocks if block.block_id in visible_ids]
    if not visible_blocks:
        raise ValueError(
            f"Prompt window {window.window_id} references no known chronology blocks."
        )

    filtered: list[EvidenceItem] = []
    for item in evidence_items:
        for block in visible_blocks:
            if item.document_id != block.document_id:
                continue
            if item.start_line <= block.end_line and item.end_line >= block.start_line:
                filtered.append(item)
                break
    return filtered


def _write_packet_files(
    packet_dir: Path,
    prefix_text: str,
    body_text: str,
    rendered_text: str,
) -> tuple[str, str, str]:
    packet_dir.mkdir(parents=True, exist_ok=True)

    prefix_path = packet_dir / "prefix.md"
    body_path = packet_dir / "body.md"
    rendered_path = packet_dir / "rendered.md"

    prefix_path.write_text(prefix_text, encoding="utf-8")
    body_path.write_text(body_text, encoding="utf-8")
    rendered_path.write_text(rendered_text, encoding="utf-8")

    return str(prefix_path), str(body_path), str(rendered_path)


def _compose_observation_v2_packets(
    deal_slug: str,
    target_name: str,
    accession_number: str | None,
    filing_type: str | None,
    blocks: list[ChronologyBlock],
    evidence_items: list[EvidenceItem],
    windows: list[PromptChunkWindow],
    packets_dir: Path,
) -> list[PromptPacketArtifact]:
    task_instructions = (
        "IMPORTANT: You MUST follow the quote-before-extract protocol.\n"
        "\n"
        "Step 1 - QUOTE: Read the chronology blocks above. Copy every verbatim passage "
        "needed to support party, cohort, and observation extraction into the quotes array. "
        "Each quote needs a unique quote_id (Q001, Q002, ...), the source block_id, and the "
        "exact filing text.\n"
        "\n"
        "Step 2 - EXTRACT: Return filing-literal structure only. Build:\n"
        "- parties: named bidders, advisors, activists, target-side boards/entities, and aliases\n"
        "- cohorts: unnamed bidder groups with exact_count, known members when explicit, and "
        "the observation that created the cohort\n"
        "- observations: only the six v2 observation types "
        "(process, agreement, solicitation, proposal, status, outcome)\n"
        "\n"
        "--- TEMPORAL ORDER CONSTRAINT ---\n"
        "`requested_by_observation_id` links a proposal to the solicitation that prompted it.\n"
        "RULE: The linked solicitation MUST have date <= proposal date.\n"
        "If no solicitation occurred on or before the proposal date, set "
        "`requested_by_observation_id` to null.\n"
        "Common mistake: linking all proposals to the final-round solicitation even when "
        "earlier proposals predate it. An unsolicited proposal MUST have null.\n"
        "--- END TEMPORAL ORDER CONSTRAINT ---\n"
        "\n"
        "--- OUTCOME ACTOR CONSTRAINT ---\n"
        "When `outcome_kind` is `executed` or `restarted`, include the bidder or bidder-cohort "
        "in `subject_refs` or `counterparty_refs`.\n"
        "If the summary names an actor like 'Buyer Group' or 'New Mountain Capital', their "
        "`party_id` MUST appear in the refs.\n"
        "--- END OUTCOME ACTOR CONSTRAINT ---\n"
        "\n"
        "Observation rules:\n"
        "- Do not emit analyst rows, benchmark rows, dropout labels, bid labels, or other "
        "derived judgments.\n"
        "- Keep every field filing-literal. If a structured field is ambiguous, set it to null "
        "or use the appropriate `other` escape hatch with a short detail string.\n"
        "- Use quote_ids, never evidence_refs or inline anchor_text.\n"
        "- Populate `recipient_refs` whenever the filing names invitees or gives a reusable "
        "cohort such as finalists, remaining bidders, or a named bidder set.\n"
        "- Proposals must use bidder or bidder-cohort subject_refs.\n"
        "- Preserve proposal-local formality clues when literal text supports them: "
        "`mentions_non_binding`, `includes_draft_merger_agreement`, and `includes_markup`.\n"
        "- Keep agreement families distinct: `nda`, `amendment`, `standstill`, `exclusivity`, "
        "`clean_team`, and `merger_agreement` are not interchangeable.\n"
        "- Solicitation observations should represent the request/announcement, with due_date "
        "when the filing gives a deadline.\n"
        "- Status observations cover expressed interest, withdrawal, exclusion, cannot-improve, "
        "selected-to-advance, and similar literal process states.\n"
        "- When the filing gives only a relative date, anchor it to the nearest explicit date "
        "in the same local context and preserve the resulting non-exact precision.\n"
        "\n"
        "Return a single JSON object with keys in this order: "
        "quotes, parties, cohorts, observations, exclusions, coverage."
    )
    packets: list[PromptPacketArtifact] = []

    for window in windows:
        packet_id = f"observations-v2-{window.window_id}"
        chunk_mode: Literal["single_pass", "chunked"] = (
            "single_pass" if window.chunk_count == 1 else "chunked"
        )
        window_evidence = _filter_evidence_for_window(blocks, evidence_items, window)

        prefix_text, body_text, rendered_text = render_observation_v2_packet(
            deal_slug=deal_slug,
            target_name=target_name,
            accession_number=accession_number,
            filing_type=filing_type,
            window=window,
            blocks=blocks,
            evidence_items=window_evidence,
            prefix_asset_path=_OBSERVATIONS_V2_PREFIX,
            examples_asset_path=_OBSERVATIONS_V2_EXAMPLES,
            task_instructions=task_instructions,
        )

        packet_dir = packets_dir / packet_id
        prefix_path, body_path, rendered_path = _write_packet_files(
            packet_dir, prefix_text, body_text, rendered_text,
        )

        packets.append(
            PromptPacketArtifact(
                packet_id=packet_id,
                packet_family="observations_v2",
                chunk_mode=chunk_mode,
                window_id=window.window_id,
                prefix_path=prefix_path,
                body_path=body_path,
                rendered_path=rendered_path,
                evidence_ids=[ei.evidence_id for ei in window_evidence],
            )
        )

    return packets


def run_compose_prompts(
    deal_slug: str,
    project_root: Path = PROJECT_ROOT,
    *,
    mode: Literal["observations"] = "observations",
    contract: Literal["v2"] = "v2",
    chunk_budget: int = 6000,
    routing: Literal["auto", "single-pass", "chunked"] = "auto",
) -> PromptPacketManifest:
    """Build live v2 observation prompt packet artifacts for a deal."""
    if contract != "v2":
        raise ValueError("compose-prompts only supports the live v2 contract")
    if mode != "observations":
        raise ValueError("compose-prompts only supports mode='observations'")

    paths = build_skill_paths(deal_slug, project_root=project_root)

    missing: list[Path] = []
    if not paths.chronology_blocks_path.exists():
        missing.append(paths.chronology_blocks_path)
    if not paths.evidence_items_path.exists():
        missing.append(paths.evidence_items_path)
    if missing:
        missing_names = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(
            f"Missing required source artifacts for compose-prompts: {missing_names}"
        )

    ensure_output_directories(paths)

    blocks = _load_blocks(paths.chronology_blocks_path)
    evidence_items = _load_evidence(paths.evidence_items_path)
    seed = load_seed_entry(deal_slug, seeds_path=paths.seeds_path)

    complexity: Literal["simple", "complex"] | None = None
    if routing == "single-pass":
        force_single_pass = True
    elif routing == "chunked":
        force_single_pass = False
    else:
        complexity = classify_deal_complexity(blocks)
        force_single_pass = complexity == "simple"
    effective_budget = "single-pass" if force_single_pass else str(chunk_budget)

    accession_number: str | None = None
    filing_type: str | None = None
    selection_path = paths.source_dir / "chronology_selection.json"
    if selection_path.exists():
        selection = json.loads(selection_path.read_text(encoding="utf-8"))
        accession_number = selection.get("accession_number")
        filing_type = selection.get("filing_type")

    windows = build_chunk_windows(
        blocks,
        chunk_budget,
        single_pass=force_single_pass,
    )

    run_id = f"compose-{uuid4().hex[:8]}"
    packets = _compose_observation_v2_packets(
        deal_slug=deal_slug,
        target_name=seed.target_name,
        accession_number=accession_number,
        filing_type=filing_type,
        blocks=blocks,
        evidence_items=evidence_items,
        windows=windows,
        packets_dir=paths.prompt_v2_packets_dir,
    )

    notes = [
        "contract=v2",
        "mode=observations",
        f"chunk_budget={chunk_budget}",
        f"routing={routing}",
        f"effective_budget={effective_budget}",
        f"source_blocks={len(blocks)}",
        f"source_evidence_items={len(evidence_items)}",
        f"chunk_windows={len(windows)}",
    ]
    if complexity is not None:
        notes.append(f"complexity={complexity}")

    manifest = PromptPacketManifest(
        run_id=run_id,
        pipeline_version=PIPELINE_VERSION,
        deal_slug=deal_slug,
        source_accession_number=accession_number,
        packets=packets,
        asset_files=[str(_OBSERVATIONS_V2_PREFIX), str(_OBSERVATIONS_V2_EXAMPLES)],
        notes=notes,
    )
    paths.prompt_v2_manifest_path.write_text(
        manifest.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return manifest
