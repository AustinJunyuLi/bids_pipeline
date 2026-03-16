from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pipeline.models.qa import QAFinding, QAReport


OVERRIDE_FILENAMES = ("overrides.json", "overrides.yaml", "overrides.yml")


def load_review_overrides(review_dir: Path) -> dict[str, Any]:
    for filename in OVERRIDE_FILENAMES:
        path = review_dir / filename
        if not path.exists():
            continue
        if path.suffix == ".json":
            return json.loads(path.read_text(encoding="utf-8"))
        try:
            import yaml  # type: ignore
        except ModuleNotFoundError:
            raise ModuleNotFoundError(
                "yaml review overrides require PyYAML; use JSON overrides or install PyYAML."
            )
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        return payload or {}
    return {}


def apply_review_overrides(report: QAReport, *, overrides: dict[str, Any]) -> QAReport:
    suppress_codes = set(overrides.get("suppress_codes", []))
    upgraded_codes = {str(code): severity for code, severity in (overrides.get("upgrade_codes", {}) or {}).items()}
    findings: list[QAFinding] = []
    for finding in report.findings:
        if finding.code in suppress_codes:
            continue
        if finding.code in upgraded_codes:
            findings.append(finding.model_copy(update={"severity": upgraded_codes[finding.code]}))
        else:
            findings.append(finding)
    blocker_count = sum(1 for finding in findings if finding.severity == "blocker")
    warning_count = sum(1 for finding in findings if finding.severity == "warning")
    return report.model_copy(
        update={
            "findings": findings,
            "blocker_count": blocker_count,
            "warning_count": warning_count,
            "passes_export_gate": blocker_count == 0,
        }
    )


def findings_by_code(report: QAReport) -> dict[str, list[QAFinding]]:
    grouped: dict[str, list[QAFinding]] = {}
    for finding in report.findings:
        grouped.setdefault(finding.code, []).append(finding)
    return grouped
