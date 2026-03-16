---
name: freeze-filing-text
description: Use when fetching selected SEC filings, freezing immutable text snapshots, or rebuilding corpus manifests after filing selection.
---

# freeze-filing-text

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

Fetch ALL filings flagged in `source_selection.json` (primary and
supplementary with disposition `"selected"`). Convert each to clean text.
Freeze as an immutable archive. The `.txt` files produced by this skill
are NEVER modified after creation -- all downstream extraction reads from
these frozen snapshots.

## Input

- `Data/deals/<slug>/source/source_selection.json` (written by Skill 1)

## Output

- `Data/deals/<slug>/source/filings/<accession>.html` -- one per filing
- `Data/deals/<slug>/source/filings/<accession>.txt` -- one per filing
- `Data/deals/<slug>/source/corpus_manifest.json` -- metadata for all
  fetched filings

## Tools

| Tool | Purpose |
|------|---------|
| Shell (curl) | Fetch filing HTML from EDGAR. Always include SEC User-Agent header. |
| Shell (python3) | HTML-to-text conversion (strip tags, collapse whitespace). |
| File write | Write .html, .txt, and corpus_manifest.json |

All SEC access is via `curl` in a shell command.

## Procedure

1. **Read `source_selection.json`** to get the list of filings to fetch.
   Identify:
   - The primary filing (disposition `"selected"` in `primary_searches`)
   - All supplementary filings (disposition `"selected"` in
     `supplementary_searches`)

2. **For the primary filing:**
   a. curl the filing HTML using the URL from `document_selection`.
      Save as `source/filings/<accession>.html`.
   b. Convert HTML to text using the python3 one-liner (see
      `references/text-snapshot-rules.md`).
      Save as `source/filings/<accession>.txt`.
   c. **Verify:** If curl returns non-200 or empty content, write
      `failure_bundle.json` and STOP.

3. **For each supplementary filing with disposition `"selected"`:**
   a. curl the filing's EDGAR index page, select the main .htm document.
   b. curl the filing HTML, save as `source/filings/<accession>.html`.
   c. Convert to text, save as `source/filings/<accession>.txt`.
   d. **On failure:** Log the error in corpus_manifest.json but do NOT
      stop. Supplementary failures do not block the pipeline.

4. **Write `source/corpus_manifest.json`** with metadata for every filing
   fetched. See `references/text-snapshot-rules.md` for the schema.

## SEC User-Agent (Required)

All curl commands to `sec.gov` must include:

```bash
-H "User-Agent: austinli@research.edu deal-extraction-tool/1.0"
```

## Gate

Primary `.html` and `.txt` files exist on disk.

## Failure Mode

**Fail closed on primary filing.** If the primary filing curl returns
non-200 or produces empty content, write `source/failure_bundle.json`
and stop.

```json
{
  "reason": "primary filing fetch failed: HTTP <status_code>",
  "last_successful_step": "source_selection_read",
  "candidates_found": ["<accession>"]
}
```

**Fail open on supplementary filings.** Log failures in
`corpus_manifest.json` with `"fetch_status": "failed"` but continue.

## Common Mistakes

- **Overwriting .txt after this skill.** The `.txt` is FROZEN after
  creation. Never modified by any downstream skill. Rewriting makes
  quote verification circular.

## Required Reading

1. `references/text-snapshot-rules.md` -- HTML-to-text rules, frozen
   contract, corpus_manifest.json schema
