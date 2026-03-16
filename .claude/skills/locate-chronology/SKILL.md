# locate-chronology

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

Find the "Background of the Merger/Offer" narrative section in the
primary filing's `.txt` file. This section contains the chronological
narrative of the deal process that all downstream extraction skills read.
Skip table-of-contents entries and cross-references -- find the actual
multi-paragraph narrative section.

## Input

- `Data/deals/<slug>/source/filings/<accession>.txt` (the primary
  filing's frozen text, written by Skill 2)
- `Data/deals/<slug>/source/corpus_manifest.json` (to identify the
  primary filing's accession number)

## Output

- `Data/deals/<slug>/source/chronology_bookmark.json`
  Contains the section heading, start/end line numbers, confidence, and
  selection basis.

## Tools

| Tool | Purpose |
|------|---------|
| Text search | Search .txt for heading patterns |
| File read | Read .txt at candidate locations to verify narrative content |
| File write | Write chronology_bookmark.json |

## Procedure

1. **Identify the primary filing's `.txt` path** from
   `corpus_manifest.json` (entry with `role: "primary"`).

2. **Search for heading patterns** using text search on the `.txt` file.
   Look for (case-insensitive):
   - "Background of the Merger"
   - "Background of the Offer"
   - "Background of the Transaction"
   See `references/section-patterns.md` for the full pattern list.

3. **For each match, verify it is the real narrative section:**
   - Read 20-30 lines starting from the match.
   - The real section has: specific dates, party names, multi-paragraph
     prose describing meetings, contacts, and negotiations.
   - **Reject** matches that are:
     - Table of contents entries (just a heading + page number)
     - Cross-references in "Summary" sections ("See 'Background of the
       Merger' beginning on page X")
     - Section headers in exhibits or appendices with minimal content

4. **Determine section boundaries:**
   - `start_line`: The line containing the heading.
   - `end_line`: The line before the next major section heading (e.g.,
     "Opinion of", "Certain Projections", "Reasons for the Merger",
     "Interests of", "Material United States Federal Income Tax").
   - Read around the estimated end boundary to find the exact transition.

5. **Write `source/chronology_bookmark.json`** with the validated
   bookmark. Include `selection_basis` explaining how the real section
   was distinguished from any TOC/cross-reference hits.

## Gate

`chronology_bookmark.json` exists with valid `start_line` and `end_line`
(both positive integers, end > start).

## Failure Mode

**Fail closed.** If no chronology section is found after checking all
heading pattern matches, write `source/failure_bundle.json` and stop.
Do not proceed to Skill 4.

```json
{
  "reason": "no chronology section found in primary filing",
  "last_successful_step": "txt_searched",
  "candidates_found": ["<accession>"]
}
```

## Common Mistakes

- **Mistaking a TOC entry or cross-reference for the real chronology
  section.** Always verify that the matched heading is followed by
  narrative content (dates, party names, multi-paragraph prose), not
  just a page number or "See page X" reference.

## Required Reading

1. `references/section-patterns.md` -- heading patterns, TOC avoidance,
   chronology_bookmark.json schema
