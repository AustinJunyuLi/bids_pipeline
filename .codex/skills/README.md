# Skills

Derived mirror of `.claude/skills/` for Codex.

| Skill | Description |
|---|---|
| `deal-agent` | Use when orchestrating the repo's end-to-end skill workflow for a deal, from SEC filing fetch through DuckDB export. |
| `enrich-deal` | Use when enriching verified extraction artifacts with interpretive dropout labels, initiation judgment, advisory verification, and count reconciliation. |
| `extract-deal` | Use when extracting skill-workflow actor and event artifacts from preprocessed SEC filing source for a specific deal. |
| `reconcile-alex` | Use when a deal has completed the skill-native pipeline and you need benchmark reconciliation against Alex's spreadsheet, especially for row mismatches, aggregate spreadsheet rows, or disagreements that require filing-text arbitration. |
| `verify-extraction` | Use when checking and repairing skill-workflow extraction artifacts against filing text before enrichment. |

Refresh this mirror with `python scripts/sync_skill_mirrors.py`.
