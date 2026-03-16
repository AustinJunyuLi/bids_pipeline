# audit-and-reconcile

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

Verify quotes against the frozen .txt files, reconcile extracted counts
against the filing's own numeric assertions, and run a structural
integrity audit over the full extraction. Produces `census.json` (the
merged party roster with self-check results) and `audit_flags.json`
(structured review flags for downstream skills).

**FRESH EYES.** This skill runs in a SEPARATE subagent from extraction.
The auditor approaches verification without knowing what the extractor
"intended" -- it re-reads the .txt and checks whether the artifacts are
consistent with the source. This separation is architecturally critical:
confirmation bias from the extraction context would defeat the purpose
of an audit.

## Input

- `Data/deals/<slug>/extraction/actors.jsonl` (initial roster from
  Skill 4)
- `Data/deals/<slug>/extraction/actors_extended.jsonl` (new actors
  minted by Skill 5, if exists)
- `Data/deals/<slug>/extraction/events.jsonl` (from Skill 5)
- `Data/deals/<slug>/extraction/event_actor_links.jsonl` (from Skill 5)
- `Data/deals/<slug>/extraction/count_assertions.json` (from Skill 4)
- `Data/deals/<slug>/source/filings/<accession>.txt` (frozen filing
  text -- read-only, MUST NOT be modified)
- `Data/deals/<slug>/source/corpus_manifest.json` (to identify filing
  paths)

## Output

- `Data/deals/<slug>/extraction/census.json` (merged party roster +
  count assertions + self_check section with reconciliations,
  structural_audit, and lifecycle_audit)
- `Data/deals/<slug>/extraction/audit_flags.json` (structured review
  flags: unresolved actors, unresolved counts, structural issues)
- `Data/deals/<slug>/extraction/decisions.jsonl` (append to existing
  log -- MANDATORY for count_interpretation decisions)

## Tools

| Tool | Purpose |
|------|---------|
| File read | Read .txt chunks for quote verification (offset + limit), read actors.jsonl, actors_extended.jsonl, events.jsonl, event_actor_links.jsonl, count_assertions.json |
| Text search | Search .txt for source_text quotes when line offsets fail |
| File write | Write census.json, audit_flags.json, append to decisions.jsonl |

## Procedure

**CRITICAL:** This skill re-reads .txt chunks but MUST NOT modify any
.txt file. The .txt was frozen at Skill 2. Rewriting would make quote
verification circular.

### Step 1: Merge Actor Roster

1. **Read `extraction/actors.jsonl`** (Skill 4 roster).
2. **Read `extraction/actors_extended.jsonl`** if it exists (Skill 5
   additions).
3. **Merge into a unified party roster.** All actors from both files
   appear in `census.json` `party_roster`. Preserve all fields from
   each source.

### Step 2: Quote Verification (Stage 3A)

For each event in `events.jsonl`, verify its `source_text`:
1. **Re-read the .txt** at `source_line_start` / `source_line_end`
   plus 10 lines of surrounding context.
2. **Check that `source_text` appears** in the re-read chunk. The
   quote must be findable -- not necessarily a perfect substring match,
   but the text must be recognizably present.
3. **If not found:** Re-read a broader chunk (+/- 50 lines). Try to
   locate the quote in the expanded context. This is retry 1.
4. **If still not found:** Use text search to search the entire .txt for a
   distinctive phrase from the source_text. This is retry 2.
5. **After 2 retries:** Flag the quote as unverified in
   `audit_flags.json`. Do not attempt further retries.

See `references/reconciliation-types.md` for full procedure details.

### Step 3: Count Reconciliation (Stage 3B)

For each assertion in `count_assertions.json`:
1. **Count matching extracted records** in events.jsonl and
   event_actor_links.jsonl.
2. **Compare** extracted count vs. expected count.
3. **If match:** Record `status: "pass"` in the reconciliation.
4. **If mismatch:** Provide a typed reconciliation explaining the gap.
   The reconciliation type MUST be one of the 7 allowed types. Never
   use free text.

The 7 reconciliation types are defined in
`references/reconciliation-types.md`.

### Step 4: Structural Integrity Audit (Stage 3C)

Run the 5-point structural audit checklist. Each check must pass or
produce a `needs_review` flag. See
`references/structural-audit.md` for full definitions.

1. NDA coverage
2. Round pair check
3. Process initiation check
4. Lifecycle-event consistency
5. Proposal completeness

### Step 5: Lifecycle Audit (Stage 3D)

Verify every non-advisor actor has a terminal lifecycle status. Count
closed vs. unresolved actors. List unresolved actor_ids.

### Step 6: Write Output

1. **Write `extraction/census.json`** with:
   - `party_roster`: merged roster from Step 1
   - `count_assertions`: carried from count_assertions.json
   - `self_check`: reconciliations (Step 3), structural_audit (Step 4),
     lifecycle_audit (Step 5)

2. **Write `extraction/audit_flags.json`** with:
   - `deal_slug`
   - `flags`: array of flag strings (e.g., "unresolved_actors",
     "unverified_quotes", "count_mismatch", "missing_nda",
     "missing_round_pair")
   - `unresolved_actors`: array of actor_ids without terminal status
   - `unresolved_counts`: array of assertion_ids that failed
     reconciliation

3. **Append to `extraction/decisions.jsonl`** for any
   count_interpretation decisions made during reconciliation.

## Gate

`extraction/census.json` exists (pass or fail-open).

## Failure Mode

**Fail open.** Unresolved issues are flagged in `audit_flags.json` and
`census.json` self_check section. The pipeline continues. Downstream
skills will see the flags and propagate `needs_review` to master_rows.csv.

## Common Mistakes

- **Accepting free-text count reconciliation.** Every reconciliation
  MUST use one of the 7 typed categories: `advisor_exclusion`,
  `stale_process`, `unnamed_aggregate`, `filing_approximation`,
  `consortium_counted_once`, `partial_bidder_excluded`, or
  `unresolved`. Never write prose explanations in place of a type.

## Decision Log (MANDATORY)

Every count_interpretation decision MUST be logged to
`extraction/decisions.jsonl`. Example: choosing to apply
`unnamed_aggregate` reconciliation when the filing says "15 buyers"
but only 12 are individually named.

## Required Reading

1. `references/reconciliation-types.md` -- quote verification procedure,
   7 count reconciliation types, census.json full schema,
   audit_flags.json schema
2. `references/structural-audit.md` -- 5-point structural audit
   checklist with pass/fail criteria
