# M&A Deal Extraction Pipeline — Design

**Date:** 2026-03-16
**Status:** Approved
**Scope:** Production pipeline for ~390 deals, validated on Alex's 9 corrected references

## Context

Alex Gorbenko's collection instructions define the extraction spec for M&A
bidding data from SEC filings. The Chicago RAs collected an initial dataset
(`deal_details.xlsx`, ~390 deals, ~9,300 rows). Alex corrected 9 deals in
`deal_details_Alex_2026.xlsx` and documented the methodology in
`CollectionInstructions_Alex_2026.qmd`.

Two prior architecture proposals (Deep Think, GPT Pro) were archived as
over-engineered. This design replaces both with a simpler four-stage pipeline.

## Design Principles

1. The filing is the single source of truth. Every fact traces to
   `source_accession_number` + verbatim `source_quote`.
2. Facts before judgments. Claude extracts evidence attributes. Python
   classifies formal/informal deterministically.
3. Alex's instructions are the extraction spec, never a factual source.
4. Categorical encoding internally; binary indicators deferred to estimation
   export.

## Architecture

Four stages per deal. Each reads from disk, writes to disk. Stages are
independently re-runnable.

```
seed CSV → Stage 1: Source → Stage 2: Extract → Stage 3: Enrich → Stage 4: Assemble
             (edgartools)     (Claude API)       (Python rules)    (CSV writer)
             no LLM           2 calls/deal       no LLM            no LLM
```

| Stage | Module | Responsibility | LLM | Failure mode |
|-------|--------|---------------|-----|-------------|
| 1 | `source.py` | Find filings, download, freeze text, locate chronology | No | Fail closed |
| 2 | `extract.py` | Two-pass Claude extraction (actors, then events) | Yes | Fail open |
| 3 | `enrich.py` | Classify formal/informal, segment cycles, determine boundary | No | Fail open |
| 4 | `assemble.py` | Flatten to per-deal CSV + global master CSV | No | Always succeeds |

Supporting modules:

- `schemas.py` — Pydantic models for Claude structured output and disk artifacts
- `run.py` — Batch runner with status tracking and CLI
- `config.py` — Paths, API key env var, filing type constants

## Directory Structure

```
bids_data/
├── pipeline/
│   ├── __init__.py
│   ├── config.py
│   ├── schemas.py          (~200-300 lines)
│   ├── source.py           (Stage 1)
│   ├── extract.py          (Stage 2)
│   ├── enrich.py           (Stage 3)
│   ├── assemble.py         (Stage 4)
│   └── run.py              (batch runner + CLI)
│
├── data/
│   ├── seeds.csv
│   ├── status.json
│   ├── deals/
│   │   └── <slug>/
│   │       ├── source/
│   │       │   ├── filings/<accession>.html
│   │       │   ├── filings/<accession>.txt
│   │       │   ├── filing_manifest.json
│   │       │   └── chronology.json
│   │       ├── extraction/
│   │       │   ├── actors.json
│   │       │   └── events.json
│   │       ├── enrichment/
│   │       │   └── enriched_events.json
│   │       └── output.csv
│   └── output/
│       └── master.csv
│
├── docs/
├── raw/
└── requirements.txt
```

## Stage 1: Source (edgartools, no LLM)

Uses `edgartools` (v5.23+) for the full EDGAR workflow. Replaces ~1,200 lines
of custom code with the library's built-in CIK resolution, filing search,
document selection, and HTML-to-text conversion.

### Procedure

1. Resolve CIK from `target_name` via `edgar.Company(target_name)`.
2. Search for each of 6 primary filing types (DEFM14A, PREM14A, SC 14D-9,
   SC 13E-3, S-4, SC TO-T) and 3 supplementary types (SC 13D, DEFA14A, 8-K).
3. Select the primary filing that contains the "Background of the Merger/Offer"
   section. Prefer DEFM14A > PREM14A > SC 14D-9 > SC 13E-3.
4. Download primary filing HTML. Convert to text via `filing.text()`.
5. Freeze both `.html` and `.txt` to `source/filings/`.
6. Locate the chronology section in the `.txt` using heading detection
   (regex scoring of "Background of the Merger/Offer" candidates, rejecting
   TOC entries). Write bounds to `chronology.json`.
7. Write `filing_manifest.json` listing all filings searched, found, selected.

### Artifacts

- `source/filings/<accession>.html` — immutable HTML archive
- `source/filings/<accession>.txt` — frozen plain text (never modified downstream)
- `source/filing_manifest.json` — discovery log
- `source/chronology.json` — `{accession, heading, start_line, end_line}`

### Gate condition

Primary `.txt` exists AND chronology section found (valid start_line, end_line).
Failure = deal skipped, logged to status.json.

### sec2md experiment

Optionally store `.md` via `sec2md.convert_to_markdown()` alongside `.txt` to
compare Claude extraction quality on markdown vs. plaintext input. Not on the
critical path.

## Stage 2: Extract (Claude API, two passes)

Two structured-output API calls per deal using Anthropic's SDK.

### Call 1: Actor Extraction

**Input:** Chronology section text + system prompt with Alex's actor rules.

**Schema (enforced via structured output):**

```python
class Actor(BaseModel):
    actor_id: str              # "party-a", "western-digital", "goldman-sachs"
    name: str                  # as it appears in the filing
    aliases: list[str]         # other names for the same entity
    actor_type: str            # "bidder" | "advisor" | "activist" | "target_board"
    bidder_subtype: str | None # "strategic" | "financial" | "non_us" | None
    is_grouped: bool           # True for "16 financial buyers"
    group_size: int | None
    source_quote: str          # first mention, verbatim

class ActorExtraction(BaseModel):
    actors: list[Actor]
    count_assertions: list[str]
```

### Call 2: Event Extraction

**Input:** Same chronology text + locked actor roster from Call 1 + system prompt
with Alex's 23-type event taxonomy.

**Schema:**

```python
class EventEvidence(BaseModel):
    preceded_by_process_letter: bool | None
    accompanied_by_merger_agreement: bool | None
    post_final_round: bool | None
    filing_language: str | None  # "indication of interest", "binding", etc.

class Event(BaseModel):
    event_id: str
    event_type: str            # one of 23 types
    date: str                  # original text, e.g. "mid-February 2013"
    date_normalized: str | None # ISO 8601 best-effort
    actor_ids: list[str]       # references to Call 1 actor_ids
    value: float | None        # per-share bid value
    value_lower: float | None
    value_upper: float | None
    consideration_type: str | None  # "cash" | "stock" | "mixed"
    evidence: EventEvidence
    source_quote: str          # verbatim from filing, mandatory
    note: str | None

class DealMetadata(BaseModel):
    target_name: str
    acquirer: str
    deal_outcome: str | None
    date_announced: str | None
    date_effective: str | None
    consideration_type: str | None

class EventExtraction(BaseModel):
    events: list[Event]
    deal_metadata: DealMetadata
```

### Key rules

- No formal/informal classification during extraction. Claude extracts
  evidence attributes; Stage 3 classifies.
- `source_quote` is mandatory on every actor and every event.
- Date normalization is best-effort. `date` field always preserves original
  text.
- Prompt caching: chronology text placed in system prompt with cache control.
  Call 2 gets the cached text essentially free.
- Up to 2 retries on API errors or schema validation failures.

### Artifacts

- `extraction/actors.json` — Call 1 output
- `extraction/events.json` — Call 2 output

### Gate condition

At least 1 actor and 1 event extracted. Failure = deal marked `failed_extract`,
pipeline continues to next deal.

## Stage 3: Enrich (deterministic Python, no LLM)

### 3a. Formal/Informal Classification

For each `proposal` event, apply rules in priority order:

| Priority | Condition | Classification |
|----------|----------|---------------|
| 1 | `evidence.accompanied_by_merger_agreement` is true | Formal |
| 2 | `evidence.post_final_round` is true | Formal |
| 3 | `evidence.filing_language` contains "indication of interest" OR range bid (`value_lower != value_upper`) | Informal |
| 4 | Default | Informal |

Each classification records which rule fired.

### 3b. Cycle Segmentation

- `terminated` / `restarted` events split the timeline into cycles.
- Single-cycle deals: one cycle containing all events.
- Multi-cycle: events before `terminated` → cycle 1, events after `restarted`
  → cycle 2.

### 3c. Formal Boundary

Earliest formal proposal event. The round announcement (if any) immediately
preceding it is the formal boundary.

### 3d. Initiation Judgment

Earliest initiation event (`target_sale`, `bidder_sale`, `activist_sale`,
`bidder_interest`) determines `initiation_type`.

### Artifact

- `enrichment/enriched_events.json` — events augmented with `bid_type`,
  `classification_rule`, `cycle_id`, `formal_boundary_event_id`,
  `initiation_type`.

## Stage 4: Assemble (CSV writer, no LLM)

### Per-deal CSV (19 columns, review format)

| # | Column | Source |
|---|--------|--------|
| 1 | deal_slug | seed |
| 2 | target_name | seed |
| 3 | acquirer | deal_metadata |
| 4 | event_date | event.date (original text) |
| 5 | event_date_normalized | event.date_normalized (ISO) |
| 6 | actor_name | actor.name |
| 7 | actor_type | actor.actor_type |
| 8 | bidder_subtype | actor.bidder_subtype |
| 9 | event_type | 23-type taxonomy code |
| 10 | bid_note | human-readable label |
| 11 | bid_value_pershare | event.value (value_lower for ranges) |
| 12 | bid_value_lower | event.value_lower |
| 13 | bid_value_upper | event.value_upper |
| 14 | bid_type | "formal" or "informal" |
| 15 | classification_rule | which rule fired |
| 16 | consideration_type | "cash" / "stock" / "mixed" |
| 17 | cycle_id | from enrichment |
| 18 | source_quote | verbatim, truncated to 200 chars |
| 19 | note | event.note |

Rows sorted by: deal_slug → event_date_normalized → event_type priority →
actor_name.

Expandable to 47 columns once extraction quality is validated.

### bid_note mapping

| event_type | bid_note |
|------------|----------|
| target_sale | Target Sale |
| target_sale_public | Target Sale Public |
| bidder_sale | Bidder Sale |
| bidder_interest | Bidder Interest |
| activist_sale | Activist Sale |
| sale_press_release | Sale Press Release |
| bid_press_release | Bid Press Release |
| ib_retention | IB |
| nda | NDA |
| proposal | *(blank)* |
| drop | Drop |
| drop_below_m | DropBelowM |
| drop_below_inf | DropBelowInf |
| drop_at_inf | DropAtInf |
| drop_target | DropTarget |
| final_round_inf_ann | Final Round Inf Ann |
| final_round_inf | Final Round Inf |
| final_round_ann | Final Round Ann |
| final_round | Final Round |
| final_round_ext_ann | Final Round Ext Ann |
| final_round_ext | Final Round Ext |
| executed | Executed |
| terminated | Terminated |
| restarted | Restarted |

### Global master CSV

Same 19 columns, all deals concatenated. Rebuilt from scratch on every run.

## Batch Runner and Error Handling

### CLI

```bash
python -m pipeline.run                           # all deals, all stages
python -m pipeline.run --stage source            # Stage 1 only
python -m pipeline.run --slug imprivata          # one deal
python -m pipeline.run --slug imprivata --force  # re-run completed deal
python -m pipeline.run --slug imprivata --stage extract  # re-run one stage
```

### Status tracking (`data/status.json`)

```json
{
  "imprivata": {
    "status": "done",
    "last_stage": "assemble",
    "cost_usd": 0.04,
    "events_extracted": 47,
    "actors_extracted": 12,
    "timestamp": "2026-03-16T14:30:00Z"
  }
}
```

Status values: `pending`, `source`, `extract`, `enrich`, `assemble`, `done`,
`failed_source`, `failed_extract`, `failed_enrich`.

### Error handling

| Error | Behavior |
|-------|----------|
| EDGAR filing not found | `failed_source`, deal skipped |
| Chronology section not found | `failed_source`, deal skipped |
| Claude API error (rate limit, timeout) | Retry 2x with backoff, then `failed_extract` |
| Claude schema validation failure | Retry 2x, then `failed_extract` |
| Claude content policy refusal | `failed_extract`, no retry |
| Enrichment rule error | `failed_enrich`, log warning |

## Dependencies

```
edgartools>=5.23    # EDGAR search, download, text conversion
anthropic>=0.49     # Claude API with structured output
pydantic>=2.0       # Schema validation
openpyxl>=3.1       # Read deal_details xlsx for seed generation
```

Optional: `sec2md` for markdown conversion experiment.

Python 3.11+.

## Seed CSV

Generated once from `raw/deal_details_Alex_2026.xlsx`:

| Column | Source |
|--------|--------|
| deal_slug | derived from target_name |
| target_name | spreadsheet |
| acquirer | spreadsheet |
| date_announced | spreadsheet |
| primary_url | URL column (if present) |
| is_reference | true for Alex's 9 corrected deals |

## Validation Plan

1. Run pipeline on Alex's 9 reference deals.
2. Compare `output.csv` for each against the corresponding rows in
   `deal_details_Alex_2026.xlsx`.
3. Key metrics: event count match, actor count match, bid value accuracy,
   formal/informal agreement, date accuracy.
4. Iterate on Claude prompts and enrichment rules until 9-deal accuracy is
   satisfactory.
5. Then run on full ~390 deal corpus.

## Cost Estimate

- Claude Sonnet with prompt caching: ~$0.03-0.08 per deal (2 calls)
- 390 deals: ~$12-30 total
- EDGAR downloads: free (public API)

## What This Design Does Not Include (deferred)

- Audit/reconciliation stage (quote verification, structural checks)
- Full 47-column output with review flags
- Cross-vendor audit (GPT vs. Claude comparison)
- Compustat linkage (`cshoc` column)
- Binary indicator columns for estimation export
- `actors_extended.jsonl` open-world minting
- Provider abstraction (single provider: Anthropic)
