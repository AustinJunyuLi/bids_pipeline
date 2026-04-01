---
name: extract-deal-v2
description: Use when extracting quote-first v2 observation artifacts (parties, cohorts, observations) from preprocessed SEC filing source for a specific deal.
---

# extract-deal-v2

## Design Principles

1. The filing is the single source of truth.
2. Extract only filing-literal structure; do not emit analyst rows or benchmark-shape judgments.
3. Quote before extract: every structured record cites `quote_ids`.
4. Preserve ambiguity explicitly with `null` or `other_detail`; do not silently infer.

## Purpose

Single-contract LLM extraction for the v2 observation graph. The output is a
quote-first `observations_raw.json` payload containing:

- `quotes`
- `parties`
- `cohorts`
- `observations`
- `exclusions`
- `coverage`

## When To Use

- Called by `/deal-agent <slug>` as the live default extraction step, or independently via `/extract-deal-v2 <slug>`.
- Prerequisite: `skill-pipeline raw-fetch`, `skill-pipeline preprocess-source`,
  and `skill-pipeline compose-prompts --deal <slug> --mode observations`
  have already run.

## Benchmark Boundary

Benchmark materials are forbidden during generation. Do not consult benchmark
files, benchmark notes, `example/`, `diagnosis/`,
`data/skill/<slug>/reconcile/*`, or `/reconcile-alex` before
`skill-pipeline db-export-v2 --deal <slug>` completes.

## Reads

| File | What it provides |
|---|---|
| `data/skill/<slug>/prompt_v2/manifest.json` | Prompt packet manifest for v2 observation extraction |
| `data/skill/<slug>/prompt_v2/packets/*/rendered.md` | Fully rendered v2 extraction packets |
| `data/deals/<slug>/source/chronology_selection.json` | Selected filing metadata |
| `data/deals/<slug>/source/chronology_blocks.jsonl` | Filing chronology blocks |
| `data/deals/<slug>/source/evidence_items.jsonl` | Deterministic extraction cues |
| `raw/<slug>/filings/*.txt` | Frozen filing text for exact quotes |

## Extraction Contract

Return one JSON object with keys in this exact order:

1. `quotes`
2. `parties`
3. `cohorts`
4. `observations`
5. `exclusions`
6. `coverage`

### Quotes

- Each quote must have `quote_id`, `block_id`, and exact verbatim `text`.
- Reuse quote IDs across multiple structured records when the same filing quote
  supports them.

### Parties

Extract named parties only:

- bidders
- advisors
- activists
- target-side boards/committees/entities

Use `advised_party_id` only when the filing explicitly says who the advisor
represents.

### Cohorts

Extract unnamed bidder groups only when the filing gives a count or clearly
describes a reusable cohort. Examples:

- "15 potentially interested financial buyers"
- "three finalists"
- "two bidders working together"

Do not invent synthetic anonymous slots.

### Observations

Use only these six observation types:

- `process`
- `agreement`
- `solicitation`
- `proposal`
- `status`
- `outcome`

Subtype guidance:

- `process`
  Use for sale launches, public announcements, advisor retention, and press
  releases.
- `agreement`
  Use for NDAs, standstills, exclusivity, merger agreements, amendments, clean
  teams, or `other`. Keep those agreement families distinct; do not collapse
  exclusivity, standstill, clean-team, or amendment facts into plain `nda`.
- `solicitation`
  Use for requests to submit IOIs, LOIs, binding offers, or best-and-final
  bids. Populate `due_date` when the filing states a deadline, and populate
  `recipient_refs` whenever the filing names invitees or a reusable cohort.
- `proposal`
  Use for actual offers or price-bearing indications. Populate `terms` when the
  economics are stated. Set `requested_by_observation_id` only when the
  proposal responds to a same-day-or-earlier solicitation; never point forward.
  Preserve literal formality clues through `mentions_non_binding`,
  `includes_draft_merger_agreement`, and `includes_markup` when the text
  supports them.
- `status`
  Use for expressed interest, withdrawal, exclusion, cannot-improve,
  selected-to-advance, limited-assets-only, and similar literal states.
- `outcome`
  Use for executed, terminated, restarted, or `other`. Include bidder or
  bidder-cohort refs when the filing names the actor, and keep relative dates
  anchored but non-exact.

### Filing-Literal Examples

- "The board authorized management to explore strategic alternatives."
  -> `process` / `sale_launch`
- "Company A entered into a confidentiality agreement."
  -> `agreement` / `nda`
- "Parties B and C were asked to submit best and final offers by May 30."
  -> `solicitation` with `requested_submission: "best_and_final"` and `due_date`
- "Party D submitted a written indication of interest at $17.00 per share."
  -> `proposal` with `terms.per_share = 17.00`
- "Party E indicated it would not continue in the process."
  -> `status` / `not_interested` or `withdrew`, whichever is literally supported
- "The merger agreement was executed."
  -> `outcome` / `executed`

## Writes

| File | Content |
|---|---|
| `data/skill/<slug>/extract_v2/observations_raw.json` | Quote-first v2 observation artifact |

## Validation

Before handing off, validate the packet artifacts with:

`python scripts/validate_prompt_packets.py --deal <slug> --expect-sections`

Then confirm the written JSON validates against the runtime schema by running:

`skill-pipeline canonicalize-v2 --deal <slug>`
