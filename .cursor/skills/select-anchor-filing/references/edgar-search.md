# EDGAR Search Reference

## CIK Resolution

The seed CSV has `deal_slug`, `target_name`, and `filing_url` but no CIK.
Every EDGAR filing search requires a CIK. Resolve it first.

### Full-Text Search (preferred)

```bash
curl -s \
  -H "User-Agent: austinli@research.edu deal-extraction-tool/1.0" \
  "https://efts.sec.gov/LATEST/search-index?q=%22<target_name>%22&dateRange=custom&startdt=<YYYY-MM-DD>&enddt=<YYYY-MM-DD>"
```

Extract the CIK from the results. Use a date range spanning the expected
deal period (e.g., 1 year before to 1 year after the deal).

### Company Search (fallback)

```bash
curl -s \
  -H "User-Agent: austinli@research.edu deal-extraction-tool/1.0" \
  "https://www.sec.gov/cgi-bin/browse-edgar?company=<target_name>&CIK=&type=&dateb=&owner=include&count=40&search_text=&action=getcompany"
```

Parse the HTML response to find the CIK in the results table. Look for
the company name match and extract the CIK number.

## Company Filings by Type

Once CIK is resolved, search for each filing type:

```bash
curl -s \
  -H "User-Agent: austinli@research.edu deal-extraction-tool/1.0" \
  "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=<CIK>&type=<FILING_TYPE>&dateb=&owner=include&count=10&search_text=&action=getcompany"
```

Replace `<FILING_TYPE>` with each of: `DEFM14A`, `PREM14A`, `SC+14D-9`,
`SC+13E-3`, `S-4`, `SC+TO-T`.

For supplementary searches also use: `SC+13D`, `DEFA14A`, `8-K`.

## Filing Index Page

Each filing has an index page listing all documents:

```bash
curl -s \
  -H "User-Agent: austinli@research.edu deal-extraction-tool/1.0" \
  "https://www.sec.gov/Archives/edgar/data/<CIK>/<ACCESSION_DASHES>/"
```

Parse the document table to find the main .htm file. Select the largest
.htm document that matches the filing type description. Log why other
documents (exhibits, graphics, XML) were rejected.

## SEC User-Agent Requirement

SEC blocks requests without a proper User-Agent header. **Every** curl
command to `sec.gov` or `efts.sec.gov` must include:

```bash
-H "User-Agent: austinli@research.edu deal-extraction-tool/1.0"
```

Requests without this header will receive a 403 or connection reset.

## source_selection.json Schema

```json
{
  "deal_slug": "petsmart-inc",
  "cik": "863894",
  "target_name": "PetSmart, Inc.",
  "primary_searches": [
    {
      "filing_type": "DEFM14A",
      "results_count": 3,
      "disposition": "selected",
      "selected_accession_number": "0001571049-15-000695",
      "reason": null
    },
    {
      "filing_type": "PREM14A",
      "results_count": 0,
      "disposition": "not_found",
      "selected_accession_number": null,
      "reason": "no results for this filing type"
    },
    {
      "filing_type": "SC 14D-9",
      "results_count": 1,
      "disposition": "searched_not_used",
      "selected_accession_number": null,
      "reason": "DEFM14A selected as primary; fuller background section"
    },
    {
      "filing_type": "SC 13E-3",
      "results_count": 0,
      "disposition": "not_found",
      "selected_accession_number": null,
      "reason": "no results for this filing type"
    },
    {
      "filing_type": "S-4",
      "results_count": 0,
      "disposition": "not_applicable",
      "selected_accession_number": null,
      "reason": "all-cash deal; no stock exchange registration needed"
    },
    {
      "filing_type": "SC TO-T",
      "results_count": 2,
      "disposition": "searched_not_used",
      "selected_accession_number": null,
      "reason": "DEFM14A selected as primary; tender offer filing has shorter background"
    }
  ],
  "supplementary_searches": [
    {
      "filing_type": "SC 13D",
      "results_count": 2,
      "disposition": "selected",
      "selected_accession_number": "0001571049-14-001234",
      "reason": "activist filing with pre-deal context"
    },
    {
      "filing_type": "DEFA14A",
      "results_count": 5,
      "disposition": "searched_not_used",
      "selected_accession_number": null,
      "reason": "additional soliciting materials; no new chronology content"
    },
    {
      "filing_type": "8-K",
      "results_count": 12,
      "disposition": "selected",
      "selected_accession_number": "0001571049-14-005678",
      "reason": "merger announcement 8-K with execution date"
    }
  ],
  "document_selection": {
    "index_url": "https://www.sec.gov/Archives/edgar/data/863894/000157104915000695/",
    "documents_listed": [
      {
        "filename": "d123456defm14a.htm",
        "description": "DEFM14A",
        "size": "1.2MB"
      },
      {
        "filename": "d123456ex99-1.htm",
        "description": "Exhibit 99.1",
        "size": "45KB"
      }
    ],
    "selected_document": "d123456defm14a.htm",
    "selection_rationale": "largest .htm document matching filing type description"
  }
}
```

### Field Reference

**primary_searches** (array, one entry per filing type searched):
- `filing_type`: string -- one of the 6 primary types
- `results_count`: int -- how many filings found for this type
- `disposition`: string -- `selected`, `searched_not_used`, `not_applicable`, `not_found`, `uncertain`
- `selected_accession_number`: string | null -- accession if selected
- `reason`: string | null -- why this disposition (null if selected)

**supplementary_searches** (array, one entry per supplementary type):
- Same fields as primary_searches

**document_selection** (object, for the selected primary filing):
- `index_url`: string -- EDGAR index page URL
- `documents_listed`: array -- all documents on the index page
- `selected_document`: string -- filename of the chosen document
- `selection_rationale`: string -- why this document was chosen
