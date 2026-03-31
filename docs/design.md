# M&A Deal Extraction Pipeline — Design Index

## Current

The live implementation in this worktree is the v2 observation-graph workflow.

Operational sequence:

1. `skill-pipeline raw-fetch --deal <slug>`
2. `skill-pipeline preprocess-source --deal <slug>`
3. `skill-pipeline compose-prompts --deal <slug> --contract v2 --mode observations`
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
- `data/legacy/v1/` stores archived v1 skill outputs and the pre-cutover DuckDB file.

Current design constraints:

- Upstream source preparation is seed-only and single-primary-document.
- The live prompt composition contract is `--contract v2 --mode observations`.
- The live generation boundary is before `skill-pipeline db-export-v2 --deal <slug>` completes.
- `derive` must only run after passing `check-v2`, `coverage-v2`, and `gates-v2`.
- `db-load-v2` requires canonical observations, derivations, and structured coverage findings.
- `skill-pipeline deal-agent` is preflight/summary only; `/deal-agent` is the clean rerun orchestrator.
- `migrate-extract-v1-to-v2` is historical migration support, not the live extraction path.
- The v1 extract/verify/enrich/export flow is archived and available only through the explicit legacy skills.

## Notes

> **Historical background -- not the authoritative description of the live
> runtime.** The documents below are from earlier design iterations that
> referenced a `pipeline/` package, provider-specific backends, or the v1 event
> contract as the live default. The live implementation authority is
> `skill_pipeline/` plus `.claude/skills/`. Consult `CLAUDE.md` for the current
> artifact contract.

- [`docs/plans/2026-03-16-pipeline-design-v3.md`](plans/2026-03-16-pipeline-design-v3.md)
- [`docs/plans/2026-03-16-prompt-engineering-spec.md`](plans/2026-03-16-prompt-engineering-spec.md)
- [`docs/plans/2026-03-17-llm-rewrite-adoption-design.md`](plans/2026-03-17-llm-rewrite-adoption-design.md)
- [`docs/plans/2026-03-17-llm-rewrite-adoption-implementation.md`](plans/2026-03-17-llm-rewrite-adoption-implementation.md)

Active external review rounds are retained under `diagnosis/deepthink/`.
