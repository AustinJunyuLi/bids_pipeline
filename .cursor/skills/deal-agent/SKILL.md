---
name: deal-agent
description: Use when extracting one or more M&A deals from SEC filings end-to-end or rerunning the repo-local skill pipeline for a deal slug.
---

# deal-agent

## Design Principles

1. The filing is the single source of truth. Every fact traces to
   `source_accession_number` + verbatim `source_text`.
2. Fail closed on source ambiguity. Fail open on extraction incompleteness.
3. Facts before judgments. Proposals are raw events. Classification is
   Skill 8, not Skill 5.
4. Alex's collection instructions are the extraction spec. Used for
   methodology and taxonomy. Never as a factual source.
5. `master.csv` is the review artifact, not the estimation artifact.

## Overview

Thin orchestrator that spawns 9 extraction skills as isolated subagents.
Each skill runs with a fresh context window, reads inputs from disk, writes
outputs to disk, and returns a short summary. The file system is the message
bus. The orchestrator checks gates by file existence and line counts only.

Use this file plus `references/gate-conditions.md`. Do not fall back to
same-named skills from other repos or global locations.

## When To Use

- Extracting one or more M&A deals from SEC filings end-to-end.
- Invoke as `/deal-agent <slug>`.
- Each sub-skill is also independently invocable for re-runs
  (for example, `/classify-bids-and-boundary <slug>` after reviewing
  extraction).

## Skills

| # | Skill | Artifact | Failure Mode |
|---|-------|----------|--------------|
| 1 | select-anchor-filing | source/source_selection.json | Fail closed |
| 2 | freeze-filing-text | source/filings/*.html, *.txt | Fail closed |
| 3 | locate-chronology | source/chronology_bookmark.json | Fail closed |
| 4 | build-party-register | extraction/actors.jsonl | Fail open |
| 5 | extract-events | extraction/events.jsonl | Fail open |
| 6 | audit-and-reconcile | extraction/census.json | Fail open |
| 7 | segment-processes | enrichment/process_cycles.jsonl | Fail open |
| 8 | classify-bids-and-boundary | enrichment/judgments.jsonl | Fail open |
| 9 | render-review-rows | master_rows.csv | Always succeeds |

## Procedure

```
1. Read seed entry for <slug> from Data/reference/deal_url_seeds.csv.
2. Create Data/deals/<slug>/ directory structure:
   source/, source/filings/, extraction/, enrichment/, review/
3. For each skill 1-9:
   a. Spawn a subagent with:
      - Skill name as prompt context
      - deal_slug as the sole argument
      - The subagent loads its own repo-local SKILL.md + references
   b. Subagent reads inputs from disk, does its work, writes outputs to disk.
   c. Subagent returns a 3-5 line summary to orchestrator.
   d. Orchestrator checks gate condition BY READING FILES ON DISK
      (see references/gate-conditions.md).
   e. If gate fails:
      - Skills 1-3: STOP. Write failure_bundle.json. Report failure to user.
      - Skills 4-8: Log warning, continue to next skill.
      - Skill 9: Should not fail (pure denormalization).
4. Report summary to user:
   - Events extracted, actors found
   - Review flags and needs_review status
   - Any skills that failed open
```

**The orchestrator NEVER loads extraction knowledge.** It checks gates by
file existence and line counts, not by parsing artifact content. Its context
stays small because it only keeps subagent summaries plus gate outcomes.

**Two-channel communication:** Artifacts flow skill-to-skill via disk (full
fidelity). Summaries flow skill-to-orchestrator only (lossy, used for gate
checks). The orchestrator never forwards Skill N's summary to Skill N+1 — it
passes only `deal_slug`.

## Required Reading

1. `references/gate-conditions.md` — gate checks for each skill and failure policy
