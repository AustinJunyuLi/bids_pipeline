from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from skill_pipeline.pipeline_models.source import ChronologyBlock

REQUIRED_KEYS = {
    "date_mentions",
    "entity_mentions",
    "evidence_density",
    "temporal_phase",
}
ALLOWED_TEMPORAL_PHASES = {"initiation", "bidding", "outcome", "other"}


def _discover_local_deals(project_root: Path) -> list[str]:
    deals_root = project_root / "data" / "deals"
    if not deals_root.exists():
        return []

    discovered: list[str] = []
    for deal_dir in sorted(path for path in deals_root.iterdir() if path.is_dir()):
        blocks_path = deal_dir / "source" / "chronology_blocks.jsonl"
        if blocks_path.exists():
            discovered.append(deal_dir.name)
    return discovered


def _blocks_path(project_root: Path, deal_slug: str) -> Path:
    return project_root / "data" / "deals" / deal_slug / "source" / "chronology_blocks.jsonl"


def _load_blocks(path: Path) -> list[ChronologyBlock]:
    if not path.exists():
        raise FileNotFoundError(f"Missing chronology blocks artifact: {path}")

    blocks: list[ChronologyBlock] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        missing_keys = sorted(REQUIRED_KEYS - payload.keys())
        if missing_keys:
            raise ValueError(
                f"{path}:{line_number} missing required annotation key(s): {', '.join(missing_keys)}"
            )
        blocks.append(ChronologyBlock.model_validate_json(line))

    if not blocks:
        raise ValueError(f"{path} contains zero chronology blocks.")
    return blocks


def _spot_check(project_root: Path, deal_slug: str) -> None:
    blocks = _load_blocks(_blocks_path(project_root, deal_slug))
    has_semantic_block = any(
        block.date_mentions
        and block.entity_mentions
        and block.evidence_density > 0
        and block.temporal_phase in ALLOWED_TEMPORAL_PHASES
        for block in blocks
    )
    if not has_semantic_block:
        raise ValueError(
            f"{deal_slug} failed spot check: no block had non-empty date_mentions, "
            "non-empty entity_mentions, evidence_density > 0, and an allowed temporal_phase."
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate annotated chronology block artifacts under the current source contract."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=PROJECT_ROOT,
    )
    parser.add_argument(
        "--deals",
        nargs="*",
        help="Deal slugs to validate. Defaults to locally available source artifacts.",
    )
    parser.add_argument(
        "--spot-check",
        help="Run the semantic spot check on one deal after schema validation.",
    )
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    deals = args.deals or _discover_local_deals(project_root)
    if not deals:
        raise ValueError("No local deal source artifacts found to validate.")

    for deal_slug in deals:
        _load_blocks(_blocks_path(project_root, deal_slug))
        print(f"validated {deal_slug}")

    if args.spot_check:
        _spot_check(project_root, args.spot_check)
        print(f"spot-check passed {args.spot_check}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
