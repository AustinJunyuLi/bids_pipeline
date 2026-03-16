import pytest

from pipeline.schemas import (
    Actor,
    ActorExtraction,
    ChronologyBookmark,
    Event,
    EventEvidence,
    EventExtraction,
)


def test_actor_valid():
    actor = Actor(
        actor_id="party-a",
        name="Party A",
        aliases=[],
        actor_type="bidder",
        bidder_subtype="financial",
        is_grouped=False,
        group_size=None,
        source_quote="Party A signed a confidentiality agreement",
    )
    assert actor.actor_id == "party-a"


def test_actor_invalid_type():
    with pytest.raises(Exception):
        Actor(
            actor_id="x",
            name="X",
            aliases=[],
            actor_type="INVALID",
            bidder_subtype=None,
            is_grouped=False,
            group_size=None,
            source_quote="text",
        )


def test_event_with_range():
    event = Event(
        event_id="e1",
        event_type="proposal",
        date="mid-February 2013",
        date_normalized="2013-02-15",
        actor_ids=["party-a"],
        value=None,
        value_lower=7.5,
        value_upper=8.0,
        consideration_type="cash",
        evidence=EventEvidence(),
        source_quote="offered $7.50-$8.00",
        note=None,
    )
    assert event.value_lower == 7.5
    assert event.value_upper == 8.0


def test_event_invalid_type():
    with pytest.raises(Exception):
        Event(
            event_id="e1",
            event_type="INVALID",
            date="Jan 1",
            date_normalized=None,
            actor_ids=[],
            value=None,
            value_lower=None,
            value_upper=None,
            consideration_type=None,
            evidence=EventEvidence(),
            source_quote="text",
            note=None,
        )


def test_extraction_containers_validate():
    actor_extraction = ActorExtraction(
        actors=[
            Actor(
                actor_id="party-a",
                name="Party A",
                aliases=[],
                actor_type="bidder",
                bidder_subtype="financial",
                is_grouped=False,
                group_size=None,
                source_quote="Party A signed a confidentiality agreement",
            )
        ],
        count_assertions=["20 parties executed confidentiality agreements"],
    )
    event_extraction = EventExtraction(
        events=[
            Event(
                event_id="e1",
                event_type="nda",
                date="January 15, 2015",
                date_normalized="2015-01-15",
                actor_ids=["party-a"],
                value=None,
                value_lower=None,
                value_upper=None,
                consideration_type=None,
                evidence=EventEvidence(),
                source_quote="Party A executed a confidentiality agreement.",
                note=None,
            )
        ],
        deal_metadata={"target_name": "Imprivata, Inc."},
    )
    assert len(actor_extraction.actors) == 1
    assert len(event_extraction.events) == 1


def test_chronology_bookmark_supports_audit_metadata():
    bookmark = ChronologyBookmark(
        accession_number="0001193125-16-677939",
        heading="Background of the Merger",
        start_line=1148,
        end_line=2376,
        confidence="high",
        selection_basis="Selected the standalone heading over TOC and cross-reference matches.",
    )
    assert bookmark.confidence == "high"
