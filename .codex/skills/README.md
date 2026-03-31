# Skills

Derived mirror of `.claude/skills/` for Codex.

| Skill | Description |
|---|---|
| `deal-agent` | Use when orchestrating the live v2 deal workflow from raw filing fetch through v2 DuckDB export, with a clean rerun that overwrites current v2 results. |
| `deal-agent-legacy` | Use when you explicitly need the archived v1 event-first workflow with interpretive enrichment and legacy db-export outputs. |
| `enrich-deal` | Legacy-only v1 skill for adding interpretive enrichment to verified event-first extraction artifacts. |
| `extract-deal` | Legacy-only v1 skill for extracting event-first actor and event artifacts from preprocessed SEC filing source. |
| `extract-deal-v2` | Use when extracting quote-first v2 observation artifacts (parties, cohorts, observations) from preprocessed SEC filing source for a specific deal. |
| `reconcile-alex` | Use when a deal has completed the live v2 pipeline and you need post-export benchmark reconciliation against Alex's spreadsheet. |
| `reconcile-alex-legacy` | Use when you explicitly need benchmark reconciliation on the archived v1 event-first export surface. |
| `verify-extraction` | Legacy-only v1 skill for checking and repairing event-first extraction artifacts before enrichment. |
| `verify-extraction-v2` | Use when checking and repairing v2 observation extraction artifacts against filing text before derivation. |

Refresh this mirror with `python scripts/sync_skill_mirrors.py`.
