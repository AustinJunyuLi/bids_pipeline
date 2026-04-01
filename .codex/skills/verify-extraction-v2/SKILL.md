---
name: verify-extraction-v2
description: Use when checking and repairing v2 observation extraction artifacts against filing text before derivation.
---

# verify-extraction-v2

## Design Principles

1. The filing is the single source of truth.
2. Verification is exact or normalized quote matching, not semantic paraphrase.
3. Repair the artifact in place when the filing supports a clear fix.
4. Keep the observation graph literal; do not "repair" by adding derived rows.

## Purpose

Fact-check `extract_v2/observations_raw.json` or canonical
`extract_v2/observations.json` against the filing text, then repair issues so
the deterministic v2 stages can pass:

- `canonicalize-v2`
- `check-v2`
- `coverage-v2`
- `gates-v2`
- `derive`

## When To Use

- Called by `/deal-agent <slug>` when deterministic v2 findings are repairable, or independently via `/verify-extraction-v2 <slug>`.
- Prerequisite: `/extract-deal-v2 <slug>` already produced
  `data/skill/<slug>/extract_v2/observations_raw.json`.

## Benchmark Boundary

Benchmark materials are forbidden during verification. Do not consult
`example/`, `diagnosis/`, benchmark spreadsheets, `reconcile/*`, or
`/reconcile-alex` before `skill-pipeline db-export-v2 --deal <slug>` completes.

## Reads

| File | What it provides |
|---|---|
| `data/skill/<slug>/extract_v2/observations_raw.json` | Quote-first v2 artifact to repair |
| `data/deals/<slug>/source/chronology_blocks.jsonl` | Filing chronology blocks |
| `data/deals/<slug>/source/evidence_items.jsonl` | Deterministic source cues |
| `raw/<slug>/filings/*.txt` | Frozen filing text |

After canonicalization / validation:

| File | What it provides |
|---|---|
| `data/skill/<slug>/extract_v2/observations.json` | Canonical v2 observations with `evidence_span_ids` |
| `data/skill/<slug>/extract_v2/spans.json` | Span registry |
| `data/skill/<slug>/check_v2/check_report.json` | Structural validation findings |
| `data/skill/<slug>/coverage_v2/coverage_findings.json` | Structured uncovered-cue findings |
| `data/skill/<slug>/gates_v2/gates_report.json` | Graph semantic findings |

## Checks

### Quote Verification

- Every `quote_id` referenced from parties, cohorts, and observations must map
  to an exact filing quote.
- Search the referenced `block_id` first.
- If needed, expand to +/- 3 lines in the raw filing text.
- If still unresolved, repair the quote text or retarget the record to the
  correct quote.

### Reference Integrity

- Every `subject_ref`, `counterparty_ref`, and `recipient_ref` must resolve to a
  party or cohort.
- Every `requested_by_observation_id`, `revises_observation_id`,
  `supersedes_observation_id`, and `related_observation_id` must resolve to a
  real observation.
- `requested_by_observation_id` must only point to a same-day-or-earlier
  solicitation; never repair by pointing a proposal forward to a later request.
- Solicitation summaries that name invitees or a reusable cohort should not
  leave `recipient_refs` empty.
- Executed or restarted outcomes that name a buyer should carry bidder or
  bidder-cohort refs.
- Every cohort `created_by_observation_id` must resolve to a real observation.

### Literal-Only Boundary

- Do not add analyst rows.
- Do not convert ambiguous text into derived judgments.
- Use `other_detail` when the filing is literal but the enum is too narrow.
- Preserve non-exact date precision; do not turn proxy or relative timing into
  an exact day unless the filing provides an explicit anchor.

## Repair Loop

1. Run `skill-pipeline canonicalize-v2 --deal <slug>`.
2. Run `skill-pipeline check-v2 --deal <slug>`.
3. Run `skill-pipeline coverage-v2 --deal <slug>`.
4. Run `skill-pipeline gates-v2 --deal <slug>`.
5. Re-read filing text around every blocker or uncovered cue.
6. Repair `observations_raw.json` in place.
7. Repeat the deterministic validation loop once.
8. If blockers remain after the second pass, stop and report them.

## Writes

| File | Content |
|---|---|
| `data/skill/<slug>/extract_v2/observations_raw.json` | Repaired v2 quote-first artifact |
| `data/skill/<slug>/extract_v2/observations.json` | Canonical repaired v2 observations |
| `data/skill/<slug>/extract_v2/spans.json` | Canonical repaired span registry |
| `data/skill/<slug>/check_v2/check_report.json` | Structural findings |
| `data/skill/<slug>/coverage_v2/coverage_findings.json` | Coverage findings |
| `data/skill/<slug>/coverage_v2/coverage_summary.json` | Coverage summary |
| `data/skill/<slug>/gates_v2/gates_report.json` | Semantic gate findings |
