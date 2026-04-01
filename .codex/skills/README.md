# Skills

Derived mirror of `.claude/skills/` for Codex.

| Skill | Description |
|---|---|
| `deal-agent` | Use when orchestrating the live v2 deal workflow from raw filing fetch through v2 DuckDB export, with a clean rerun that overwrites current v2 results. |
| `extract-deal-v2` | Use when extracting quote-first v2 observation artifacts (parties, cohorts, observations) from preprocessed SEC filing source for a specific deal. |
| `reconcile-alex` | Use when a deal has completed the live v2 pipeline and you need post-export benchmark reconciliation against Alex's spreadsheet. |
| `verify-extraction-v2` | Use when checking and repairing v2 observation extraction artifacts against filing text before derivation. |

Refresh this mirror with `python scripts/sync_skill_mirrors.py`.
