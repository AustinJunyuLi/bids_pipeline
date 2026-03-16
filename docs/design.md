# M&A Deal Extraction Pipeline — Design Index

## Current (v2)

Adopted 2026-03-16 based on GPT Pro Round 1 architectural review.

- **Design:** [`docs/plans/2026-03-16-pipeline-design-v2.md`](plans/2026-03-16-pipeline-design-v2.md)
- **Implementation plan:** [`docs/plans/2026-03-16-pipeline-implementation-v2.md`](plans/2026-03-16-pipeline-implementation-v2.md)
- **Prompt engineering spec:** [`docs/plans/2026-03-16-prompt-engineering-spec.md`](plans/2026-03-16-prompt-engineering-spec.md)

Architecture: 6-stage evidence-first DAG (Source Discovery, Chronology Localization,
Extraction, Reconciliation/QA, Enrichment, Export/Validation).

## Superseded (v1)

Original 4-stage linear pipeline, replaced by v2.

- **Design:** [`docs/plans/2026-03-16-pipeline-design.md`](plans/2026-03-16-pipeline-design.md)
- **Implementation plan:** [`docs/plans/2026-03-16-pipeline-implementation.md`](plans/2026-03-16-pipeline-implementation.md)

## Review Artifacts

- GPT Pro Round 1 reply: `diagnosis/gptpro/2026-03-16/round_1_reply.md`
- Meeting notes: `diagnosis/gptpro/2026-03-16/round_1_meeting_notes.md`
