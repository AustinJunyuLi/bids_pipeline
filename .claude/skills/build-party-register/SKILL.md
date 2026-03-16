# build-party-register

## Design Principles

1. The filing is the single source of truth. Every fact traces to
   `source_accession_number` + verbatim `source_text`.
2. Fail closed on source ambiguity. Fail open on extraction incompleteness.
3. Facts before judgments. Proposals are raw events. Classification is
   Skill 8, not Skill 5.
4. Alex's collection instructions are the extraction spec. Used for
   methodology and taxonomy. Never as a factual source.
5. master.csv is the review artifact, not the estimation artifact.

## Overview

Read the chronology section of the primary filing, identify all parties
mentioned in the narrative, assign stable actor IDs, and extract the
filing's own count assertions (numeric claims about how many parties
signed NDAs, submitted bids, etc.). This roster is the scaffold for
event extraction in Skill 5. It is intentionally initial, not final --
Skill 5 can mint new actors discovered during event extraction.

## Input

- `Data/deals/<slug>/source/filings/<accession>.txt` (primary filing,
  frozen by Skill 2)
- `Data/deals/<slug>/source/chronology_bookmark.json` (line range from
  Skill 3)

## Output

- `Data/deals/<slug>/extraction/actors.jsonl` (initial party roster)
- `Data/deals/<slug>/extraction/count_assertions.json` (filing's own
  numeric claims about party counts, NDA counts, etc.)
- `Data/deals/<slug>/extraction/decisions.jsonl` (append-only decision
  log -- MANDATORY for alias_merge and actor_type_classification)

## Tools

| Tool | Purpose |
|------|---------|
| File read | Read .txt at bookmark line range (offset + limit), read chronology_bookmark.json |
| File write | Write actors.jsonl, count_assertions.json, decisions.jsonl |

## Procedure

1. **Read the chronology bookmark** from
   `source/chronology_bookmark.json`. Extract `accession_number`,
   `start_line`, `end_line`.

2. **Read the chronology section** from the primary `.txt` using the
   bookmark line range. Read in manageable chunks (500-800 lines) if
   the section is long.

3. **Identify all parties** mentioned in the chronology:
   - **Named parties with filing labels:** "Party A", "Bidder B",
     "Company C" -- use the filing's own pseudonym system.
   - **Named entities:** "J.P. Morgan", "Goldman Sachs" -- identified
     by name in the filing.
   - **Unnamed parties from aggregates:** If the filing says "15
     financial buyers were contacted", create unnamed actors for
     those not individually identified.
   - **Advisors:** Investment banks, financial advisors, law firms.

4. **Assign stable actor IDs** following the scheme in
   `references/actor-scheme.md`. Each ID is `<deal_slug>/<label>`.

5. **Classify each actor** by type (bidder, advisor, activist,
   target_board) and bidder subtype (strategic, financial, non_us,
   mixed) where applicable. See `references/actor-scheme.md` for
   type definitions.

6. **Extract count assertions** from the filing text. These are the
   filing's own numeric claims: "15 parties signed NDAs",
   "8 indications of interest were received", etc. For each:
   - Record the exact assertion text as `source_text`
   - Record what is being counted (`metric`)
   - Record the number (`expected_count`)
   - Record the time scope and cycle scope
   - Record line numbers for provenance

7. **Write `extraction/actors.jsonl`** -- one JSON line per actor.
   See `references/actor-scheme.md` for the full schema.

8. **Write `extraction/count_assertions.json`** -- array of assertion
   objects.

9. **Write decision log entries** to `extraction/decisions.jsonl` for
   every alias_merge and actor_type_classification decision made.

## Gate

At least 1 actor in `extraction/actors.jsonl`.

## Failure Mode

**Fail open.** An incomplete roster is acceptable -- Skill 5
(extract-events) can mint new actors discovered during event
extraction. Those new actors go to `extraction/actors_extended.jsonl`,
not overwriting this skill's `actors.jsonl`.

## Common Mistakes

- **Treating a banker as a bidder.** Investment banks (J.P. Morgan,
  Goldman Sachs, etc.) retained by the target are advisors, not
  bidders. Their role is `advisor`, not `bidder`. Only classify as
  `bidder` if the bank or its fund is making an acquisition bid.
  When in doubt, log an `actor_type_classification` decision to
  `decisions.jsonl`.

## Decision Log (MANDATORY)

Every alias_merge and actor_type_classification decision MUST be
logged to `extraction/decisions.jsonl`. Examples:

- Merging "Party A" and "Company A" as the same entity based on
  paragraph context.
- Classifying a financial institution as advisor vs. bidder.
- Interpreting an aggregate count ("approximately 20 parties") as
  a specific number.

See `references/actor-scheme.md` for `decisions.jsonl` schema and
decision type definitions.

## Required Reading

1. `references/actor-scheme.md` -- actor ID scheme, naming rules,
   types, actors.jsonl schema, count_assertions.json schema,
   decisions.jsonl schema
