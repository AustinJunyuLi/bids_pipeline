# M&A Deal Extraction Pipeline — Design Index

## Current

The active implementation in this worktree is the seed-only `skill_pipeline`
hybrid workflow.

Operational sequence:

1. `skill-pipeline raw-fetch --deal <slug>`
2. `skill-pipeline preprocess-source --deal <slug>`
3. `skill-pipeline compose-prompts --deal <slug> --mode actors`
4. `/extract-deal <slug>` (two-pass actor/event extraction; the event pass may regenerate prompt packets with `--mode events` after actor extraction creates `actors_raw.json`)
5. `skill-pipeline canonicalize --deal <slug>`
6. `skill-pipeline check --deal <slug>`
7. `skill-pipeline verify --deal <slug>`
8. `skill-pipeline coverage --deal <slug>`
9. `skill-pipeline gates --deal <slug>`
10. `/verify-extraction <slug>`
11. `skill-pipeline enrich-core --deal <slug>`
12. `/enrich-deal <slug>` (mandatory interpretive layer)
13. `skill-pipeline db-load --deal <slug>`
14. `skill-pipeline db-export --deal <slug>`

Artifact flow:

- `raw/<slug>/` contains immutable frozen filing text plus seed-only discovery metadata.
- `data/deals/<slug>/source/` contains `chronology_blocks.jsonl` and `evidence_items.jsonl`.
- `data/skill/<slug>/prompt/` contains composed prompt packet artifacts (`manifest.json` and per-packet `rendered.md`).
- `data/skill/<slug>/extract/` contains raw or canonical actors/events plus `spans.json`.
- `data/skill/<slug>/enrich/` contains `deterministic_enrichment.json` from `enrich-core` plus required interpretive `enrichment.json` from `/enrich-deal`.
- `data/skill/<slug>/{check,verify,coverage,export}/` contains downstream deterministic QA and export outputs.

Current design constraints:

- Upstream source preparation is seed-only and single-primary-document.
- Prompt composition is actors-first; `skill-pipeline compose-prompts --deal <slug> --mode events` requires `actors_raw.json` from actor extraction.
- Canonical extract artifacts require a valid `spans.json` sidecar.
- `enrich-core` must only run after passing `check`, `verify`, `coverage`, and `gates`.
- `/enrich-deal` is a mandatory interpretive gate after `enrich-core` and before `db-load` / `db-export`.
- `db-load` requires both `deterministic_enrichment.json` and interpretive-only `enrichment.json`.
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
