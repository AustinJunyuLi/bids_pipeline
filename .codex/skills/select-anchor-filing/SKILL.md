---
name: select-anchor-filing
description: Use when starting a new deal extraction or reviewing source filing selection by searching EDGAR, ranking candidate filing types, and selecting anchor and supplementary filings.
---

# select-anchor-filing

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

Search SEC EDGAR for all 6 primary filing types by CIK, rank filings by
chronology quality, and select the primary filing. Also discover
supplementary filing candidates. This is the first skill in the
deal-agent pipeline. If no usable filing is found, write a failure bundle
and stop -- do not proceed to downstream skills.

## Input

- `deal_slug` (passed by orchestrator)
- Seed row from `Data/reference/deal_url_seeds.csv` matching `deal_slug`

## Output

- `Data/deals/<slug>/source/source_selection.json`
  Contains all primary searches, supplementary searches, and document
  selection rationale.

## Tools

| Tool | Purpose |
|------|---------|
| Shell (curl) | All EDGAR access: company search, filings pages, index pages. Always include SEC User-Agent header. |
| File write | Write source_selection.json |

All SEC access is via `curl` in a shell command.

## Procedure

1. **Read seed entry** from `Data/reference/deal_url_seeds.csv` for the
   given `deal_slug`. Extract `target_name`, `filing_url`, and any other
   seed fields.

2. **Resolve CIK.** curl the EDGAR company search page by `target_name`,
   extract the CIK from the HTML response. See
   `references/edgar-search.md` for URL patterns.

3. **Search all 6 primary filing types** by CIK regardless of whether a
   seed URL exists: DEFM14A, PREM14A, SC 14D-9, SC 13E-3, S-4, SC TO-T.
   For each type, curl the company filings page and parse results. Log
   every search and its disposition.

4. **Select primary filing.** Apply the filing preference ranking (see
   `references/filing-types.md`). Pick whichever filing has the most
   complete "Background of the Merger/Offer" section. If the seed provides
   a `filing_url`, treat it as the likely primary, but a higher-ranked
   filing discovered in step 3 may override it.

5. **For the primary filing:** curl its EDGAR index page, parse the
   document list (filename, description, size), select the main .htm
   document. Log the selection rationale and why other documents were
   rejected.

6. **Discover supplementary candidates.** All non-primary filings found in
   step 3 become supplementary candidates. Additionally search for: SC 13D,
   DEFA14A, 8-K. Log disposition for each.

7. **Write `source/source_selection.json`** with primary_searches,
   supplementary_searches, and document_selection. See
   `references/edgar-search.md` for the schema.

## SEC User-Agent (Required)

All curl commands to `sec.gov` or `efts.sec.gov` MUST include:

```bash
-H "User-Agent: austinli@research.edu deal-extraction-tool/1.0"
```

SEC blocks requests without a proper User-Agent header.

## Gate

At least one filing in `source_selection.json` has disposition `"selected"`.

## Failure Mode

**Fail closed.** If no filing has a usable background section after
searching all 6 types, write `source/failure_bundle.json` and stop.
Do not proceed to Skill 2.

```json
{
  "reason": "no usable filing found across all 6 primary types",
  "last_successful_step": "cik_resolved",
  "candidates_found": []
}
```

## Required Reading

1. `references/edgar-search.md` -- CIK resolution, URL patterns, schema
2. `references/filing-types.md` -- type descriptions, preference ranking
