# M&A Deal Extraction Pipeline — Design Index

## Current

The active pipeline architecture is the v3 evidence-first rewrite.

- **Design:** [`docs/plans/2026-03-16-pipeline-design-v3.md`](plans/2026-03-16-pipeline-design-v3.md)
- **Prompt engineering spec:** [`docs/plans/2026-03-16-prompt-engineering-spec.md`](plans/2026-03-16-prompt-engineering-spec.md)
- **LLM rewrite adoption design:** [`docs/plans/2026-03-17-llm-rewrite-adoption-design.md`](plans/2026-03-17-llm-rewrite-adoption-design.md)
- **LLM rewrite adoption implementation:** [`docs/plans/2026-03-17-llm-rewrite-adoption-implementation.md`](plans/2026-03-17-llm-rewrite-adoption-implementation.md)

Architecture: 7-stage evidence-first pipeline (Raw Discovery & Freeze, Enhanced
Preprocess / Source Build, LLM Extraction, Reconciliation & QA, Enrichment,
Export, Reference Validation).

## Notes

Superseded v1 and v2 design/implementation plans were removed from the active
tree during cleanup so review bundles only carry the current planning surface.

Active external review rounds are retained under `diagnosis/deepthink/`.
