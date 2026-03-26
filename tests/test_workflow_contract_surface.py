"""Regression tests for the committed workflow contract surface.

These assertions protect the contract doc and the design index from silent
drift. If a stage is added, removed, or reclassified, the relevant test
should fail until the contract is updated intentionally.
"""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CONTRACT_PATH = PROJECT_ROOT / "docs" / "workflow-contract.md"
DESIGN_PATH = PROJECT_ROOT / "docs" / "design.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Contract doc existence and structure
# ---------------------------------------------------------------------------


def test_workflow_contract_exists() -> None:
    assert CONTRACT_PATH.exists(), "docs/workflow-contract.md must exist"


def test_workflow_contract_minimum_length() -> None:
    text = _read(CONTRACT_PATH)
    line_count = len(text.splitlines())
    assert line_count >= 80, (
        f"docs/workflow-contract.md has {line_count} lines; "
        "expected at least 80 for a meaningful contract"
    )


# ---------------------------------------------------------------------------
# End-to-end stage order
# ---------------------------------------------------------------------------

EXPECTED_STAGE_ORDER = [
    "raw-fetch",
    "preprocess-source",
    "/extract-deal",
    "canonicalize",
    "check",
    "verify",
    "coverage",
    "/verify-extraction",
    "enrich-core",
    "/enrich-deal",
    "/export-csv",
]


def test_contract_contains_full_stage_order() -> None:
    text = _read(CONTRACT_PATH)
    for stage in EXPECTED_STAGE_ORDER:
        assert stage in text, (
            f"docs/workflow-contract.md must mention stage '{stage}'"
        )


def test_contract_stage_order_is_correct() -> None:
    """Stages must appear in the documented order within the contract."""
    text = _read(CONTRACT_PATH)
    positions = []
    for stage in EXPECTED_STAGE_ORDER:
        pos = text.index(stage)
        positions.append((stage, pos))
    for i in range(len(positions) - 1):
        current_stage, current_pos = positions[i]
        next_stage, next_pos = positions[i + 1]
        assert current_pos < next_pos, (
            f"Stage '{current_stage}' must appear before '{next_stage}' "
            f"in docs/workflow-contract.md"
        )


# ---------------------------------------------------------------------------
# Deterministic vs LLM classification
# ---------------------------------------------------------------------------


def test_contract_contains_deterministic_vs_llm_heading() -> None:
    text = _read(CONTRACT_PATH)
    assert "Deterministic vs LLM Mix" in text, (
        "docs/workflow-contract.md must contain the heading "
        "'Deterministic vs LLM Mix'"
    )


# ---------------------------------------------------------------------------
# verify-extraction repair step placement
# ---------------------------------------------------------------------------


def test_contract_documents_verify_extraction_after_deterministic_gates() -> None:
    """verify-extraction must be documented as a repair step after the
    deterministic verify and coverage stages."""
    text = _read(CONTRACT_PATH)
    verify_pos = text.index("verify-extraction")
    assert "verify" in text[:verify_pos] and "coverage" in text[:verify_pos], (
        "docs/workflow-contract.md must document /verify-extraction after "
        "the deterministic verify and coverage stages"
    )


# ---------------------------------------------------------------------------
# deal-agent disambiguation
# ---------------------------------------------------------------------------


def test_contract_distinguishes_cli_deal_agent_from_skill() -> None:
    text = _read(CONTRACT_PATH)
    assert "skill-pipeline deal-agent" in text, (
        "docs/workflow-contract.md must mention 'skill-pipeline deal-agent'"
    )
    assert "/deal-agent" in text, (
        "docs/workflow-contract.md must mention '/deal-agent'"
    )
    assert "preflight" in text.lower() or "summary" in text.lower(), (
        "docs/workflow-contract.md must describe the CLI deal-agent as "
        "preflight or summary"
    )


# ---------------------------------------------------------------------------
# reconcile-alex post-export boundary
# ---------------------------------------------------------------------------


def test_contract_documents_reconcile_alex_as_post_export() -> None:
    text = _read(CONTRACT_PATH)
    assert "/reconcile-alex" in text, (
        "docs/workflow-contract.md must mention /reconcile-alex"
    )
    assert "post-export only" in text.lower(), (
        "docs/workflow-contract.md must state /reconcile-alex is post-export only"
    )


# ---------------------------------------------------------------------------
# Design index references the contract
# ---------------------------------------------------------------------------


def test_design_index_references_workflow_contract() -> None:
    text = _read(DESIGN_PATH)
    assert "workflow-contract.md" in text, (
        "docs/design.md must reference docs/workflow-contract.md so the "
        "detailed contract remains discoverable from the design index"
    )
