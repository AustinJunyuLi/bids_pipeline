from typing import Literal

from pydantic import Field

from skill_pipeline.pipeline_models.common import ArtifactEnvelope
from skill_pipeline.pipeline_models.source import FilingCandidate, FrozenDocument, SeedDeal


class RawDiscoveryManifest(ArtifactEnvelope):
    artifact_type: str = "raw_discovery_manifest"
    seed: SeedDeal
    cik: str | None = None
    primary_candidates: list[FilingCandidate] = Field(default_factory=list)
    supplementary_candidates: list[FilingCandidate] = Field(default_factory=list)
    fetch_scope: Literal["all_candidates"] = "all_candidates"


class RawDocumentRegistry(ArtifactEnvelope):
    artifact_type: str = "raw_document_registry"
    documents: list[FrozenDocument] = Field(default_factory=list)
