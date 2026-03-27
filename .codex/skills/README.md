# Skills

Derived mirror of `.claude/skills/` for Codex.

| Skill | Description |
|---|---|
| `deal-agent` | Use when orchestrating the repo's end-to-end skill workflow for a deal after raw fetch and source preprocessing already ran. |
| `enrich-deal` | Use when enriching verified skill extraction artifacts with bid classification, cycle structure, initiation judgment, and advisory or count review. |
| `export-csv` | Use when flattening skill extraction and enrichment artifacts into the repo review CSV for a deal. |
| `extract-deal` | Use when extracting skill-workflow actor and event artifacts from preprocessed SEC filing source for a specific deal. |
| `reconcile-alex` | Use when a deal has completed the skill-native pipeline and you need benchmark reconciliation against Alex's spreadsheet, especially for row mismatches, aggregate spreadsheet rows, or disagreements that require filing-text arbitration. |
| `verify-extraction` | Use when checking and repairing skill-workflow extraction artifacts against filing text before enrichment. |

Refresh this mirror with `python scripts/sync_skill_mirrors.py`.
