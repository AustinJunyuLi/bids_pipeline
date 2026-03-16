from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from pipeline.schemas import (
    Actor,
    CountAssertion,
    Deal,
    Decision,
    Event,
    EventActorLink,
    Reconciliation,
)


ArtifactT = TypeVar("ArtifactT")


@dataclass(slots=True, frozen=True)
class ProviderConfig:
    """Static configuration for a concrete LLM provider implementation."""

    provider_name: str
    model_id: str
    api_key_env_var: str
    max_retries: int
    timeout_seconds: int


@dataclass(slots=True, frozen=True)
class ProviderCost:
    """Token and cost accounting for a single provider call."""

    input_tokens: int
    output_tokens: int
    cost_usd: float


@dataclass(slots=True, frozen=True)
class ProviderResult(Generic[ArtifactT]):
    """Structured record of a provider call and its materialized artifacts."""

    artifacts: ArtifactT
    cost: ProviderCost
    model_id: str
    prompt_version: str


class Provider(ABC):
    """Abstract interface for all stage 2 extraction and reconciliation providers."""

    config: ProviderConfig

    @property
    @abstractmethod
    def last_result(self) -> ProviderResult[Any] | None:
        """Return metadata for the most recent provider call, if available."""

    @abstractmethod
    def extract_actors(
        self,
        chronology_text: str,
        deal_slug: str,
        accession_number: str,
    ) -> tuple[list[Actor], list[CountAssertion], list[Decision]]:
        """Extract actor rows and count assertions from chronology text.

        Returns a tuple of validated Actor rows, CountAssertion rows, and Decision rows.
        Concrete implementations should populate ``last_result`` with token and cost
        information for this call.
        """

    @abstractmethod
    def extract_events(
        self,
        chronology_text: str,
        deal_slug: str,
        actors: list[Actor],
        accession_number: str,
    ) -> tuple[list[Event], list[EventActorLink], list[Decision]]:
        """Extract event rows and event-actor links given a locked actor roster.

        Returns a tuple of validated Event rows, EventActorLink rows, and Decision rows.
        Concrete implementations should populate ``last_result`` with token and cost
        information for this call.
        """

    @abstractmethod
    def reconcile_counts(
        self,
        count_assertions: list[CountAssertion],
        actors: list[Actor],
        events: list[Event],
        links: list[EventActorLink],
    ) -> list[Reconciliation]:
        """Generate typed count reconciliation explanations for extracted data.

        Returns a list of Reconciliation rows. Concrete implementations should populate
        ``last_result`` with token and cost information for this call.
        """

    @abstractmethod
    def extract_deal_metadata(
        self,
        chronology_text: str,
        deal_slug: str,
        events: list[Event],
        actors: list[Actor],
    ) -> Deal:
        """Extract deal-level metadata and provenance.

        Returns a Deal model. Concrete implementations should populate ``last_result``
        with token and cost information for this call.
        """
