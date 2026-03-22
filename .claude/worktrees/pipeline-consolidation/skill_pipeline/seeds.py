from __future__ import annotations

import csv
from pathlib import Path

from skill_pipeline.config import SEEDS_PATH
from skill_pipeline.models import SeedEntry


def load_seed_entry(deal_slug: str, *, seeds_path: Path = SEEDS_PATH) -> SeedEntry:
    if not seeds_path.exists():
        raise FileNotFoundError(f"Seed registry does not exist: {seeds_path}")

    with seeds_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if (row.get("deal_slug") or "").strip() != deal_slug:
                continue
            return SeedEntry(
                deal_slug=deal_slug,
                target_name=(row.get("target_name") or "").strip(),
                acquirer=_optional_text(row.get("acquirer")),
                date_announced=_optional_text(row.get("date_announced")),
                primary_url=_optional_text(row.get("primary_url")),
                is_reference=_parse_bool(row.get("is_reference")),
            )
    raise ValueError(f"Unknown deal slug in seed registry: {deal_slug}")


def _optional_text(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    return cleaned or None


def _parse_bool(value: str | None) -> bool:
    normalized = (value or "").strip().lower()
    return normalized in {"1", "true", "yes", "y"}
