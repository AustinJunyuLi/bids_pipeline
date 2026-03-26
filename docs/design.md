# M&A Deal Extraction Pipeline — Design Index

## Current

The active implementation in this worktree is the seed-only `skill_pipeline`
hybrid workflow. For the detailed stage inventory, artifact contracts, and gate
boundaries, see [`docs/workflow-contract.md`](workflow-contract.md).

Operational sequence (compact):

```text
raw-fetch -> preprocess-source -> /extract-deal -> canonicalize
-> check -> verify -> coverage -> /verify-extraction
-> enrich-core -> /enrich-deal -> /export-csv
```

`skill-pipeline source-discover --deal <slug>` is an auxiliary no-fetch helper
and is not part of the main generation chain.

`/reconcile-alex` is optional and post-export only.

Key artifact roots:

- `raw/<slug>/` -- immutable frozen filing text plus seed-only discovery metadata
- `data/deals/<slug>/source/` -- chronology blocks and evidence items
- `data/skill/<slug>/extract/` -- raw or canonical actors/events plus `spans.json`
- `data/skill/<slug>/{check,verify,coverage,enrich,export}/` -- downstream stage outputs

Design constraints:

- Upstream source preparation is seed-only and single-primary-document.
- Canonical extract artifacts require a valid `spans.json` sidecar.
- `enrich-core` must only run after passing `check`, `verify`, and `coverage`.
- `skill-pipeline deal-agent` is preflight/summary only, not the end-to-end runner.

Stage classification, artifact paths, and gate behavior are documented in
[`docs/workflow-contract.md`](workflow-contract.md).

## Notes

The v3 evidence-first rewrite plans remain useful historical background, but
they are not the authoritative description of the current runtime surface in
this worktree:

- [`docs/plans/2026-03-16-pipeline-design-v3.md`](plans/2026-03-16-pipeline-design-v3.md)
- [`docs/plans/2026-03-16-prompt-engineering-spec.md`](plans/2026-03-16-prompt-engineering-spec.md)

Active external review rounds are retained under `diagnosis/deepthink/`.
