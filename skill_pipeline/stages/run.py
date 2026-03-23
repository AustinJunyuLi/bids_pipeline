"""End-to-end production orchestrator for the skill pipeline."""

from __future__ import annotations

from pathlib import Path

from skill_pipeline.core.config import PROJECT_ROOT
from skill_pipeline.stages import export as export_stage
from skill_pipeline.stages import extract as extract_stage
from skill_pipeline.stages import materialize as materialize_stage
from skill_pipeline.stages.enrich import core as enrich_core_stage
from skill_pipeline.stages.enrich import interpret as enrich_interpret_stage
from skill_pipeline.stages.qa import check as check_stage
from skill_pipeline.stages.qa import coverage as coverage_stage
from skill_pipeline.stages.qa import omission_audit as omission_audit_stage
from skill_pipeline.stages.qa import repair as repair_stage
from skill_pipeline.stages.qa import verify as verify_stage


def _run_stage(label: str, fn, deal_slug: str, project_root: Path) -> int:
    """Run a stage, print pass/fail, return its exit code."""
    print(f"{label}...", end=" ", flush=True)
    rc = fn(deal_slug, project_root=project_root)
    print("PASS" if rc == 0 else "FAIL")
    return rc


def run_deal(
    deal_slug: str,
    *,
    project_root: Path = PROJECT_ROOT,
) -> int:
    """Run the production skill pipeline through export.

    All QA stages run unconditionally so repair gets the fullest picture.
    The pipeline gates at repair: if repair fails, enrichment and export
    do not run. Reconciliation is intentionally standalone.
    """
    # --- Stage 1: Extract ---
    print("[1/10] Extracting actors and events...", flush=True)
    extract_stage.run_extract(deal_slug, project_root=project_root)
    print("[1/10] Extracting actors and events... done")

    # --- Stage 2: Materialize ---
    print("[2/10] Materializing canonical artifacts...", flush=True)
    materialize_stage.run_materialize(deal_slug, project_root=project_root)
    print("[2/10] Materializing canonical artifacts... done")

    # --- Stages 3-6: QA (all run unconditionally, findings go to disk) ---
    _run_stage("[3/10] Structural checks", check_stage.run_check, deal_slug, project_root)
    _run_stage("[4/10] Quote verification", verify_stage.run_verify, deal_slug, project_root)
    _run_stage("[5/10] Coverage audit", coverage_stage.run_coverage, deal_slug, project_root)
    _run_stage("[6/10] Omission audit", omission_audit_stage.run_omission_audit, deal_slug, project_root)

    # --- Stage 7: Repair (the gate) ---
    print("[7/10] Repair loop...", flush=True)
    try:
        rc = repair_stage.run_repair(deal_slug, project_root=project_root)
    except RuntimeError as exc:
        print(f"[7/10] Repair loop... FAIL: {exc}")
        return 1
    if rc != 0:
        print("[7/10] Repair loop... FAIL")
        return 1
    print("[7/10] Repair loop... PASS")

    # --- Stage 8: Enrich core ---
    print("[8/10] Deterministic enrichment...", flush=True)
    enrich_core_stage.run_enrich_core(deal_slug, project_root=project_root)
    print("[8/10] Deterministic enrichment... done")

    # --- Stage 9: Enrich interpret ---
    print("[9/10] Interpretive enrichment...", flush=True)
    enrich_interpret_stage.run_enrich_interpret(deal_slug, project_root=project_root)
    print("[9/10] Interpretive enrichment... done")

    # --- Stage 10: Export ---
    print("[10/10] Exporting CSV...", flush=True)
    export_stage.run_export(deal_slug, project_root=project_root)
    print("[10/10] Exporting CSV... done")

    print(
        "\nPost-production benchmark QA remains standalone: "
        f"python scripts/reconcile_alex.py --deal {deal_slug}"
    )
    print(f"Pipeline complete for {deal_slug}.")
    return 0
