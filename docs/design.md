# M&A Deal Extraction Pipeline — Design Index

## Current

The live implementation in this worktree is the v2 observation-graph workflow.

Operational sequence:

1. `skill-pipeline raw-fetch --deal <slug>`
2. `skill-pipeline preprocess-source --deal <slug>`
3. `skill-pipeline compose-prompts --deal <slug> --mode observations`
4. `/extract-deal-v2 <slug>`
5. `skill-pipeline canonicalize-v2 --deal <slug>`
6. `skill-pipeline check-v2 --deal <slug>`
7. `skill-pipeline coverage-v2 --deal <slug>`
8. `skill-pipeline gates-v2 --deal <slug>`
9. `/verify-extraction-v2 <slug>`
10. `skill-pipeline derive --deal <slug>`
11. `skill-pipeline db-load-v2 --deal <slug>`
12. `skill-pipeline db-export-v2 --deal <slug>`
13. `/reconcile-alex <slug>` (optional, post-export only)

Artifact flow:

- `raw/<slug>/` contains immutable frozen filing text plus seed-only discovery metadata.
- `data/deals/<slug>/source/` contains `chronology_blocks.jsonl` and `evidence_items.jsonl`.
- `data/skill/<slug>/prompt_v2/` contains composed v2 prompt packet artifacts.
- `data/skill/<slug>/extract_v2/` contains quote-first and canonical observations plus `spans.json`.
- `data/skill/<slug>/{check_v2,coverage_v2,gates_v2,derive,export_v2}/` contains downstream deterministic validation, derivation, and export outputs.
- The retired v1 tree is recoverable through Git tag `v1-working-tree-2026-04-01` and archived milestone docs, not through working-tree artifacts.

Current design constraints:

- Upstream source preparation is seed-only and single-primary-document.
- The live prompt composition contract is `--mode observations`.
- The live generation boundary is before `skill-pipeline db-export-v2 --deal <slug>` completes.
- `derive` must only run after passing `check-v2`, `coverage-v2`, and `gates-v2`.
- `db-load-v2` requires canonical observations, derivations, and structured coverage findings.
- `skill-pipeline deal-agent` is preflight/summary only; `/deal-agent` is the clean rerun orchestrator.
- The retired v1 runtime is absent from the working tree and recoverable only through Git history.

## Notes

Historical design iterations (pre-v2) are preserved in git history only.
The live implementation authority is `skill_pipeline/` plus `.claude/skills/`.
Consult `CLAUDE.md` for the current artifact contract.
