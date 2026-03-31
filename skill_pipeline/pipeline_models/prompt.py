from __future__ import annotations

from typing import Literal

from pydantic import Field

from skill_pipeline.pipeline_models.common import ArtifactEnvelope, PipelineModel


class PromptChunkWindow(PipelineModel):
    """Describes a single chunk window over chronology blocks."""

    window_id: str
    chunk_index: int
    chunk_count: int
    target_block_ids: list[str]
    overlap_block_ids: list[str] = Field(default_factory=list)
    estimated_tokens: int


class PromptPacketArtifact(PipelineModel):
    """Metadata for one prompt packet file set."""

    packet_id: str
    packet_family: Literal["actors", "events", "observations_v2"]
    chunk_mode: Literal["single_pass", "chunked"]
    window_id: str
    prefix_path: str
    body_path: str
    rendered_path: str
    evidence_ids: list[str] = Field(default_factory=list)
    actor_roster_source_path: str | None = None


class PromptPacketManifest(ArtifactEnvelope):
    """Top-level manifest for all prompt packets produced for a deal."""

    artifact_type: str = "prompt_packet_manifest"
    deal_slug: str
    source_accession_number: str | None = None
    packets: list[PromptPacketArtifact] = Field(default_factory=list)
    asset_files: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
