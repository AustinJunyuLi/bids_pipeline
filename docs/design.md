# M&A Deal Extraction Pipeline — Design Index

## Current

The active implementation in this worktree is the seed-only `skill_pipeline`
hybrid workflow.

Operational sequence:

1. `skill-pipeline raw-fetch --deal <slug>`
2. `skill-pipeline preprocess-source --deal <slug>`
3. `skill-pipeline compose-prompts --deal <slug>`
4. `/extract-deal <slug>`
5. `skill-pipeline canonicalize --deal <slug>`
6. `skill-pipeline check --deal <slug>`
7. `skill-pipeline verify --deal <slug>`
8. `skill-pipeline coverage --deal <slug>`
9. `/verify-extraction <slug>`
10. `skill-pipeline enrich-core --deal <slug>`
11. `/enrich-deal <slug>`
12. `/export-csv <slug>`

Artifact flow:

- `raw/<slug>/` contains immutable frozen filing text plus seed-only discovery metadata.
- `data/deals/<slug>/source/` contains `chronology_blocks.jsonl` and `evidence_items.jsonl`.
- `data/skill/<slug>/prompt/` contains composed prompt packet artifacts (`manifest.json` and per-packet `rendered.md`).
- `data/skill/<slug>/extract/` contains raw or canonical actors/events plus `spans.json`.
- `data/skill/<slug>/{check,verify,coverage,enrich,export}/` contains downstream deterministic outputs.

Current design constraints:

- Upstream source preparation is seed-only and single-primary-document.
- Canonical extract artifacts require a valid `spans.json` sidecar.
- `enrich-core` must only run after passing `check`, `verify`, and `coverage`.
- `skill-pipeline deal-agent` is preflight/summary only, not the end-to-end runner.

## Notes

> **Historical background -- not the authoritative description of the live
> runtime.** The documents below are from earlier design iterations that
> referenced a `pipeline/` package, provider-specific backends, and model-pinned
> guidance. The live implementation authority is `skill_pipeline/` plus
> `.claude/skills/`. Consult `CLAUDE.md` for the current artifact contract.

- [`docs/plans/2026-03-16-pipeline-design-v3.md`](plans/2026-03-16-pipeline-design-v3.md)
- [`docs/plans/2026-03-16-prompt-engineering-spec.md`](plans/2026-03-16-prompt-engineering-spec.md)
- [`docs/plans/2026-03-17-llm-rewrite-adoption-design.md`](plans/2026-03-17-llm-rewrite-adoption-design.md)
- [`docs/plans/2026-03-17-llm-rewrite-adoption-implementation.md`](plans/2026-03-17-llm-rewrite-adoption-implementation.md)

Active external review rounds are retained under `diagnosis/deepthink/`.
