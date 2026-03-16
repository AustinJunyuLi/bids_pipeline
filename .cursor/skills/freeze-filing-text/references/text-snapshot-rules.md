# Text Snapshot Rules

## HTML-to-Text Conversion

Use python3 to convert fetched HTML to clean text. The goal is a readable
plain-text file that preserves document structure (paragraph breaks) while
removing all markup.

### Python3 One-Liner

```bash
python3 -c "
import re, sys, html
raw = sys.stdin.read()
# Remove script, style, and head blocks entirely
raw = re.sub(r'<(script|style|head)[^>]*>.*?</\1>', '', raw, flags=re.DOTALL|re.IGNORECASE)
# Replace block-level tags with newlines to preserve paragraph breaks
raw = re.sub(r'</(p|div|tr|li|br|h[1-6])>', '\n', raw, flags=re.IGNORECASE)
raw = re.sub(r'<br\s*/?>', '\n', raw, flags=re.IGNORECASE)
# Strip all remaining HTML tags
raw = re.sub(r'<[^>]+>', '', raw)
# Decode HTML entities
raw = html.unescape(raw)
# Collapse whitespace within lines (preserve newlines)
lines = raw.split('\n')
lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in lines]
# Collapse multiple blank lines to single blank line
result = []
prev_blank = False
for line in lines:
    if line == '':
        if not prev_blank:
            result.append('')
        prev_blank = True
    else:
        result.append(line)
        prev_blank = False
print('\n'.join(result))
" < input.html > output.txt
```

### Rules

1. Remove `<script>`, `<style>`, and `<head>` blocks entirely (content
   and tags).
2. Replace block-level closing tags (`</p>`, `</div>`, `</tr>`, `</li>`,
   `<br>`, `</h1>`-`</h6>`) with newlines to preserve paragraph breaks.
3. Strip all remaining HTML tags.
4. Decode HTML entities (`&amp;` -> `&`, `&#160;` -> space, etc.).
5. Collapse runs of spaces/tabs within each line to a single space.
6. Collapse multiple consecutive blank lines to a single blank line.
7. Do NOT reorder content. The text must follow the same sequence as the
   HTML source.

## Frozen-After-Write Contract

The `.txt` file is **frozen immediately after creation by this skill**.
No downstream skill may modify it. This contract ensures:

- All `source_text` quotes in extraction artifacts are verifiable against
  the original `.txt`.
- Human reviewers can trust `.txt` as the canonical text surface.
- Self-check (Skill 6) re-reads `.txt` chunks to verify quotes but does
  NOT rewrite `.txt`.

**If the `.txt` needs correction, the fix is to re-run this skill
(freeze-filing-text), not to edit the file in place.**

The `.html` file is also retained as the immutable byte-level archive.
It serves as the ultimate source of truth if `.txt` conversion is
ever questioned.

## corpus_manifest.json Schema

Array of filing metadata. One entry per filing fetched (primary and
supplementary).

```json
[
  {
    "accession_number": "0001571049-15-000695",
    "filing_type": "DEFM14A",
    "role": "primary",
    "url": "https://www.sec.gov/Archives/edgar/data/863894/000157104915000695/d123456defm14a.htm",
    "html_filename": "filings/0001571049-15-000695.html",
    "txt_filename": "filings/0001571049-15-000695.txt",
    "filing_date": "2015-01-20",
    "fetch_status": "success"
  },
  {
    "accession_number": "0001571049-14-001234",
    "filing_type": "SC 13D",
    "role": "supplementary",
    "url": "https://www.sec.gov/Archives/edgar/data/863894/000157104914001234/sc13d.htm",
    "html_filename": "filings/0001571049-14-001234.html",
    "txt_filename": "filings/0001571049-14-001234.txt",
    "filing_date": "2014-08-15",
    "fetch_status": "success"
  },
  {
    "accession_number": "0001571049-14-005678",
    "filing_type": "8-K",
    "role": "supplementary",
    "url": "https://www.sec.gov/Archives/edgar/data/863894/000157104914005678/form8k.htm",
    "html_filename": "filings/0001571049-14-005678.html",
    "txt_filename": "filings/0001571049-14-005678.txt",
    "filing_date": "2014-12-14",
    "fetch_status": "failed",
    "fetch_error": "HTTP 403"
  }
]
```

### Field Reference

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| accession_number | string | yes | SEC accession number |
| filing_type | string | yes | DEFM14A, SC 13D, 8-K, etc. |
| role | string | yes | `primary` or `supplementary` |
| url | string | yes | Full URL to the filing document |
| html_filename | string | yes | Relative path to archived HTML |
| txt_filename | string | yes | Relative path to frozen text |
| filing_date | string | yes | YYYY-MM-DD |
| fetch_status | string | yes | `success` or `failed` |
| fetch_error | string | no | Error message if fetch_status is `failed` |
