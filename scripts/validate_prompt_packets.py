"""Deterministic validator for prompt packet artifacts.

Loads ``data/skill/<slug>/prompt/manifest.json``, validates every packet
through the ``PromptPacketManifest`` schema, opens each ``rendered.md`` file,
and asserts that required XML-style section tags are present.

Exit codes:
    0  All packets valid.
    1  One or more validation failures.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from skill_pipeline.pipeline_models.prompt import PromptPacketManifest

# Tags that must appear in every rendered prompt packet.
REQUIRED_TAGS = frozenset({
    "<chronology_blocks>",
    "<evidence_checklist>",
    "<task_instructions>",
})

# Additional tag required for chunked packets.
CHUNKED_TAG = "<overlap_context>"


def validate_manifest(
    deal_slug: str,
    *,
    project_root: Path,
    contract: str = "v1",
    expect_sections: bool = False,
) -> list[str]:
    """Validate prompt packet artifacts for *deal_slug*.

    Returns a list of error strings (empty means pass).
    """
    prompt_dir = "prompt_v2" if contract == "v2" else "prompt"
    manifest_path = project_root / "data" / "skill" / deal_slug / prompt_dir / "manifest.json"
    if not manifest_path.exists():
        return [f"Manifest not found: {manifest_path}"]

    raw_text = manifest_path.read_text(encoding="utf-8")
    try:
        manifest = PromptPacketManifest.model_validate(json.loads(raw_text))
    except Exception as exc:
        return [f"Manifest schema validation failed: {exc}"]

    if manifest.deal_slug != deal_slug:
        return [
            f"Manifest deal_slug mismatch: expected {deal_slug!r}, "
            f"got {manifest.deal_slug!r}"
        ]

    if not manifest.packets:
        return ["Manifest contains zero packets"]

    errors: list[str] = []

    for packet in manifest.packets:
        rendered_path = Path(packet.rendered_path)
        if not rendered_path.exists():
            errors.append(f"Packet {packet.packet_id}: rendered file missing: {rendered_path}")
            continue

        rendered_text = rendered_path.read_text(encoding="utf-8")

        if expect_sections:
            for tag in REQUIRED_TAGS:
                if tag not in rendered_text:
                    errors.append(
                        f"Packet {packet.packet_id}: missing required tag {tag}"
                    )

            if packet.chunk_mode == "chunked" and CHUNKED_TAG not in rendered_text:
                errors.append(
                    f"Packet {packet.packet_id}: chunked packet missing {CHUNKED_TAG}"
                )

    return errors


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate prompt packet artifacts for a deal.",
    )
    parser.add_argument("--deal", required=True, help="Deal slug to validate.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root directory.",
    )
    parser.add_argument(
        "--contract",
        choices=["v1", "v2"],
        default="v1",
        help="Prompt contract family to validate (default: v1).",
    )
    parser.add_argument(
        "--expect-sections",
        action="store_true",
        help="Assert required XML section tags in every rendered packet.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    errors = validate_manifest(
        args.deal,
        project_root=args.project_root,
        contract=args.contract,
        expect_sections=args.expect_sections,
    )
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"PASS: All prompt packets valid for {args.deal}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
