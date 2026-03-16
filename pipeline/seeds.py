import csv
import re
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path

from openpyxl import load_workbook

from pipeline.config import DATA_DIR, PROJECT_ROOT, SEEDS_PATH


RAW_SEEDS_XLSX = PROJECT_ROOT / "raw" / "deal_details_Alex_2026.xlsx"
SEED_COLUMNS = (
    "deal_slug",
    "target_name",
    "acquirer",
    "date_announced",
    "primary_url",
    "is_reference",
)

CANONICAL_SLUG_OVERRIDES = {
    "imprivata-inc": "imprivata",
    "medivation-inc": "medivation",
    "zep-inc": "zep",
    "penford-corp": "penford",
    "mac-gray-corp": "mac-gray",
    "saks-inc": "saks",
    "providence-worcester-rr-co": "providence-worcester",
    "stec-inc": "stec",
    "s-tec-inc": "stec",
    "s-t-e-c-inc": "stec",
}
REFERENCE_SLUGS = {
    "imprivata",
    "medivation",
    "zep",
    "petsmart-inc",
    "penford",
    "mac-gray",
    "saks",
    "providence-worcester",
    "stec",
}


def make_slug(name: str) -> str:
    """Lowercase, strip punctuation, collapse to hyphens."""

    slug = re.sub(r"[^a-z0-9]+", "-", name.lower())
    slug = re.sub(r"-{2,}", "-", slug)
    return slug.strip("-")


def canonical_deal_slug(target_name: str) -> str:
    """Apply stable overrides for known reference/example deals."""

    base_slug = make_slug(target_name)
    return CANONICAL_SLUG_OVERRIDES.get(base_slug, base_slug)


def extract_seeds(xlsx_path: Path) -> list[dict]:
    """Read deal_details xlsx, return one dict per unique deal."""

    workbook = load_workbook(xlsx_path, read_only=True, data_only=True)
    worksheet = workbook[workbook.sheetnames[0]]
    rows = worksheet.iter_rows(values_only=True)
    header = next(rows)
    indices = {name: i for i, name in enumerate(header) if name}

    seeds_by_target: dict[str, dict] = {}
    for row in rows:
        target_name = _clean_text(row[indices["TargetName"]])
        if not target_name:
            continue

        seed = seeds_by_target.setdefault(
            target_name,
            {
                "deal_slug": canonical_deal_slug(target_name),
                "target_name": target_name,
                "acquirer": "",
                "date_announced": "",
                "primary_url": "",
                "is_reference": False,
            },
        )
        seed["acquirer"] = seed["acquirer"] or _clean_text(row[indices["Acquirer"]])
        seed["date_announced"] = seed["date_announced"] or _format_date(
            row[indices["DateAnnounced"]]
        )
        seed["primary_url"] = seed["primary_url"] or _clean_text(row[indices["URL"]])
        seed["is_reference"] = seed["deal_slug"] in REFERENCE_SLUGS

    return list(seeds_by_target.values())


def write_seeds(seeds: list[dict], output_path: Path) -> None:
    """Write seeds to CSV."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SEED_COLUMNS)
        writer.writeheader()
        for seed in seeds:
            row = dict(seed)
            row["is_reference"] = "true" if row["is_reference"] else "false"
            writer.writerow(row)


def main() -> None:
    """Entry point: read xlsx, write seeds.csv."""

    seeds = extract_seeds(RAW_SEEDS_XLSX)
    write_seeds(seeds, SEEDS_PATH)
    print(f"Wrote {len(seeds)} seeds to {SEEDS_PATH}")


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _format_date(value: object) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return _clean_text(value)


if __name__ == "__main__":
    main()
