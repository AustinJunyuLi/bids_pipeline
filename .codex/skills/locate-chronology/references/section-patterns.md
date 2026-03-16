# Section Patterns Reference

## Heading Patterns

Search the primary `.txt` for these headings (case-insensitive). The
exact wording varies across filings.

### Primary patterns (most common):

- `Background of the Merger`
- `Background of the Offer`
- `Background of the Transaction`

### Variant patterns (less common):

- `Background of the Proposed Merger`
- `Background of the Proposed Transaction`
- `Background and Reasons for the Merger`
- `Background of the Acquisition`
- `Background of the Tender Offer`
- `Background`  (standalone, only if followed by deal narrative)

### Search pattern (combine into one search):

```
(?i)background\s+of\s+the\s+(merger|offer|transaction|proposed\s+merger|proposed\s+transaction|acquisition|tender\s+offer)|(?i)background\s+and\s+reasons\s+for\s+the\s+merger
```

Or search each pattern individually and collect all match locations.

## TOC Avoidance

Multiple matches are expected. The table of contents and summary sections
often mention the heading. Distinguish the real narrative section from
false positives:

### Real narrative section (ACCEPT):
- Heading is followed by multi-paragraph prose (10+ lines of text)
- Contains specific dates ("On August 13, 2014", "In early October")
- Contains party names ("Party A", "the Company", "J.P. Morgan")
- Contains meeting descriptions, phone calls, negotiations
- Typically 200-1000+ lines long

### Table of contents entry (REJECT):
- Heading appears on a line with a page number ("Background of the Merger ... 42")
- Followed by other TOC entries, not narrative text
- Usually in the first 5-10% of the document

### Cross-reference in Summary (REJECT):
- Heading appears within a summary paragraph
- Often preceded by "See" or "as described in"
- Example: "See 'Background of the Merger' beginning on page 42"
- Usually brief (1-3 sentences summarizing the section)

### Exhibit or appendix header (REJECT):
- Heading appears in an exhibit or appendix
- Minimal content (not the main filing's narrative)
- Check surrounding context for "Exhibit" or "Appendix" markers

## Verification Procedure

For each heading match:
1. Read 20-30 lines starting from the match location.
2. Check for dates, party names, and multi-paragraph narrative prose.
3. If the content looks like a TOC entry or cross-reference, reject it
   and move to the next match.
4. If the content is narrative, this is the real section. Proceed to
   boundary detection.

## Section End Boundary

The chronology section typically ends before one of these next-section
headings:

- "Opinion of" (financial advisor's fairness opinion)
- "Certain Projections" or "Certain Financial Projections"
- "Reasons for the Merger" or "Reasons for the Offer"
- "Recommendation of" (board recommendation)
- "Interests of" (interests of directors/officers)
- "Material United States Federal Income Tax"
- "Regulatory Approvals"
- "Financing"
- "The Merger Agreement" or "The Offer"
- "Conditions to"

Read around the estimated end boundary to find the exact transition line.
The `end_line` should be the last line of the chronology narrative, before
the next section heading.

## chronology_bookmark.json Schema

```json
{
  "accession_number": "0001571049-15-000695",
  "section_heading": "Background of the Merger",
  "start_line": 1250,
  "end_line": 1890,
  "confidence": "high",
  "selection_basis": "selected over TOC hit at line 312 and cross-reference at line 4501; verified narrative content with dates and party names starting at line 1251"
}
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| accession_number | string | yes | Primary filing accession number |
| section_heading | string | yes | Exact heading text found in .txt |
| start_line | int | yes | Line number of the heading (1-indexed) |
| end_line | int | yes | Last line of the narrative section |
| confidence | string | yes | `high`, `medium`, or `low` |
| selection_basis | string | yes | How the real section was distinguished from TOC/cross-reference hits |

### Confidence Levels

- **high**: Single clear narrative section, heading exactly matches a
  primary pattern, 200+ lines of dated narrative prose.
- **medium**: Multiple candidate sections; selected the longest one.
  Or heading is a variant pattern.
- **low**: Section heading is ambiguous ("Background" standalone) or
  section boundaries are uncertain. Flag for manual review.
