from datetime import UTC, date, datetime

from pipeline.models.common import SCHEMA_VERSION
from pipeline.models.source import SeedDeal
from pipeline.source.discovery import search_candidates_with_fallback
from pipeline.source.ranking import rank_filing_candidates


def _seed(
    *,
    target_name: str = "ZEP INC",
    announced: date = date(2015, 4, 8),
    primary_url: str = "https://www.sec.gov/Archives/edgar/data/1408287/000104746915004456/a2224606zprem14a.htm",
) -> SeedDeal:
    return SeedDeal(
        schema_version=SCHEMA_VERSION,
        artifact_type="seed_deal",
        created_at=datetime(2026, 3, 16, tzinfo=UTC),
        pipeline_version="0.1.0",
        run_id="run-1",
        deal_slug="zep",
        target_name=target_name,
        acquirer_seed="New Mountain Capital",
        date_announced_seed=announced,
        primary_url_seed=primary_url,
        is_reference=True,
        seed_row_refs=[],
    )


def _raw_filing(
    accession_number: str,
    filing_type: str,
    filing_date: str,
    *,
    url: str | None = None,
) -> dict:
    return {
        "accession_number": accession_number,
        "filing_type": filing_type,
        "filing_date": filing_date,
        "url": url
        or f"https://www.sec.gov/Archives/edgar/data/1/{accession_number.replace('-', '')}/index.htm",
    }


def test_seed_accession_is_preferred_when_valid():
    seed = _seed()
    candidates = rank_filing_candidates(
        seed,
        [
            _raw_filing("0001047469-15-004989", "DEFM14A", "2015-05-26"),
            _raw_filing("0001047469-15-004456", "PREM14A", "2015-05-06"),
        ],
        filing_family="primary",
        top_k=2,
    )

    assert candidates[0].accession_number == "0001047469-15-004456"
    assert candidates[0].ranking_features["seed_accession_match"] is True


def test_stale_supplementary_filings_outside_window_are_rejected():
    seed = _seed(
        target_name="MEDIVATION INC",
        announced=date(2016, 8, 22),
        primary_url="https://www.sec.gov/Archives/edgar/data/1011835/000119312516696911/d234696dsc14d9.htm",
    )
    candidates = rank_filing_candidates(
        seed,
        [
            _raw_filing("0001132413-07-000338", "SC 13D", "2007-12-10"),
            _raw_filing("0001193125-16-686961", "8-K", "2016-08-22"),
        ],
        filing_family="supplementary",
        top_k=3,
    )

    assert [candidate.accession_number for candidate in candidates] == [
        "0001193125-16-686961"
    ]


def test_empty_or_failed_search_falls_back_to_seed_accession_lookup():
    seed = _seed()

    def failing_search(_filing_type: str) -> list[dict]:
        raise RuntimeError("search backend unavailable")

    def fallback_lookup(accession_number: str) -> dict:
        assert accession_number == "0001047469-15-004456"
        return _raw_filing(accession_number, "PREM14A", "2015-05-06")

    candidates = search_candidates_with_fallback(
        seed,
        filing_type="PREM14A",
        filing_family="primary",
        search_fn=failing_search,
        fallback_lookup_fn=fallback_lookup,
        top_k=1,
    )

    assert len(candidates) == 1
    assert candidates[0].accession_number == "0001047469-15-004456"
    assert candidates[0].source_origin == "seed_accession"


def test_ranking_is_deterministic_for_same_distance_candidates():
    seed = _seed(
        target_name="MAC GRAY CORP",
        announced=date(2013, 10, 15),
        primary_url="https://www.sec.gov/Archives/edgar/data/1038280/000104746913010973/a2217482zdefm14a.htm",
    )
    candidates = rank_filing_candidates(
        seed,
        [
            _raw_filing("0001193125-13-408272", "SC 13D", "2013-10-23"),
            _raw_filing("0001104659-13-075539", "DEFA14A", "2013-10-15"),
            _raw_filing("0001104659-13-075536", "8-K", "2013-10-15"),
        ],
        filing_family="supplementary",
        top_k=3,
    )

    assert [candidate.accession_number for candidate in candidates] == [
        "0001104659-13-075539",
        "0001104659-13-075536",
        "0001193125-13-408272",
    ]
