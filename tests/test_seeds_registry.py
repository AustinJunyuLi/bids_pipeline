import csv
from pathlib import Path

import pytest

from pipeline.models.seed import SeedRegistryEntry
from pipeline.seeds import (
    REQUIRED_SEED_COLUMNS,
    build_seed_registry,
    entry_to_seed_artifact,
    load_seed_registry,
)


def _write_seed_csv(path: Path, rows: list[dict[str, str]], headers: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def test_load_seed_registry_rejects_missing_required_headers(tmp_path):
    csv_path = tmp_path / "seeds.csv"
    headers = [column for column in REQUIRED_SEED_COLUMNS if column != "primary_url"]
    _write_seed_csv(
        csv_path,
        rows=[
            {
                "deal_slug": "imprivata",
                "target_name": "Imprivata, Inc.",
                "acquirer": "Thoma Bravo",
                "date_announced": "2016-07-11",
                "is_reference": "true",
            }
        ],
        headers=headers,
    )

    with pytest.raises(ValueError, match="primary_url"):
        load_seed_registry(csv_path)


def test_build_seed_registry_groups_target_name_variants_under_one_slug():
    entries = build_seed_registry(
        [
            {
                "deal_slug": "imprivata-inc",
                "target_name": "Imprivata, Inc.",
                "acquirer": "Thoma Bravo",
                "date_announced": "2016-07-11",
                "primary_url": "https://example.com/1",
                "is_reference": "true",
            },
            {
                "deal_slug": "IMPRIVATA-INC",
                "target_name": "IMPRIVATA INC",
                "acquirer": "",
                "date_announced": "",
                "primary_url": "https://example.com/1",
                "is_reference": "false",
            },
        ]
    )

    assert len(entries) == 1
    assert entries[0].deal_slug == "imprivata"
    assert len(entries[0].evidence) == 2


def test_build_seed_registry_preserves_conflicting_seed_evidence():
    entries = build_seed_registry(
        [
            {
                "deal_slug": "petsmart-inc",
                "target_name": "PetSmart, Inc.",
                "acquirer": "BC Partners",
                "date_announced": "2014-12-14",
                "primary_url": "https://example.com/a",
                "is_reference": "true",
            },
            {
                "deal_slug": "petsmart-inc",
                "target_name": "PetSmart Inc",
                "acquirer": "Apollo",
                "date_announced": "2014-12-14",
                "primary_url": "https://example.com/b",
                "is_reference": "true",
            },
        ]
    )

    entry = entries[0]
    assert entry.acquirer == "BC Partners"
    assert set(entry.conflicting_evidence["acquirer"]) == {"Apollo", "BC Partners"}
    assert set(entry.conflicting_evidence["primary_url"]) == {
        "https://example.com/a",
        "https://example.com/b",
    }


def test_entry_to_seed_artifact_emits_without_row_refs():
    entry = SeedRegistryEntry(
        deal_slug="imprivata",
        target_name="Imprivata, Inc.",
        acquirer="Thoma Bravo",
        date_announced=None,
        primary_url="https://example.com/1",
        is_reference=True,
    )

    artifact = entry_to_seed_artifact(entry, run_id="run-1")

    assert artifact.deal_slug == "imprivata"
    assert artifact.seed_row_refs == []


def test_build_seed_registry_handles_malformed_dates():
    entries = build_seed_registry(
        [
            {
                "deal_slug": "medivation-inc",
                "target_name": "Medivation, Inc.",
                "acquirer": "Pfizer",
                "date_announced": "mid-August 2016",
                "primary_url": "https://example.com/medivation",
                "is_reference": "true",
            }
        ]
    )

    assert entries[0].date_announced is None
