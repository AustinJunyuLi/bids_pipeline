from __future__ import annotations

from types import SimpleNamespace

import pytest

from pipeline.models.extraction import ActorRecord
from pipeline.models.source import ChronologyBlock


@pytest.fixture
def sample_blocks() -> list[ChronologyBlock]:
    return [
        ChronologyBlock(
            block_id="B001",
            document_id="doc-1",
            ordinal=1,
            start_line=1200,
            end_line=1202,
            raw_text="On July 1, 2016, Party A contacted the Company.\nThe board considered the outreach.",
            clean_text="On July 1, 2016, Party A contacted the Company. The board considered the outreach.",
            is_heading=False,
        ),
        ChronologyBlock(
            block_id="B002",
            document_id="doc-1",
            ordinal=2,
            start_line=1203,
            end_line=1205,
            raw_text="On July 5, 2016, Party A submitted an indication of interest of $25.00 per share.",
            clean_text="On July 5, 2016, Party A submitted an indication of interest of $25.00 per share.",
            is_heading=False,
        ),
    ]


@pytest.fixture
def sample_actor_roster() -> list[ActorRecord]:
    return [
        ActorRecord(
            actor_id="party-a",
            display_name="Party A",
            canonical_name="party-a",
            aliases=["Bidder A"],
            role="bidder",
            bidder_kind="financial",
            listing_status="public",
            geography="domestic",
            is_grouped=False,
            first_mention_span_ids=["span-1"],
        )
    ]


@pytest.fixture
def mock_anthropic_response():
    def factory(
        payload: str,
        *,
        input_tokens: int = 1000,
        cache_creation_input_tokens: int = 0,
        cache_read_input_tokens: int = 0,
        output_tokens: int = 250,
        request_id: str = "msg_test_123",
        model: str = "claude-sonnet-4-20250514",
    ) -> SimpleNamespace:
        usage = SimpleNamespace(
            input_tokens=input_tokens,
            cache_creation_input_tokens=cache_creation_input_tokens,
            cache_read_input_tokens=cache_read_input_tokens,
            output_tokens=output_tokens,
        )
        text_block = SimpleNamespace(type="text", text=payload)
        return SimpleNamespace(
            id=request_id,
            model=model,
            content=[text_block],
            usage=usage,
        )

    return factory
