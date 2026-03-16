# M&A Deal Extraction Pipeline — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a four-stage Python pipeline that extracts M&A bidding data from SEC filings using edgartools and Claude, validated against Alex's 9 corrected reference deals.

**Architecture:** Four sequential stages (Source → Extract → Enrich → Assemble), each reading inputs from disk and writing outputs to disk. A batch runner loops over a seed CSV and tracks status in a JSON file. edgartools handles all EDGAR interactions. Anthropic Claude handles actor and event extraction via structured output.

**Tech Stack:** Python 3.11+, edgartools, anthropic, pydantic, openpyxl

**Design doc:** `docs/plans/2026-03-16-pipeline-design.md`

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `pipeline/__init__.py`
- Create: `pipeline/config.py`
- Create: `data/.gitkeep`

**Step 1: Create requirements.txt**

```
edgartools>=5.23
anthropic>=0.49
pydantic>=2.0
openpyxl>=3.1
pytest>=8.0
```

**Step 2: Create pipeline package**

`pipeline/__init__.py` — empty file.

`pipeline/config.py` — project paths, filing type constants, and API config:

```python
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DEALS_DIR = DATA_DIR / "deals"
SEEDS_PATH = DATA_DIR / "seeds.csv"
STATUS_PATH = DATA_DIR / "status.json"
OUTPUT_DIR = DATA_DIR / "output"

ANTHROPIC_MODEL = "claude-sonnet-4-20250514"

PRIMARY_FILING_TYPES = ("DEFM14A", "PREM14A", "SC 14D-9", "SC 13E-3", "S-4", "SC TO-T")
SUPPLEMENTARY_FILING_TYPES = ("SC 13D", "DEFA14A", "8-K")

PRIMARY_PREFERENCE = {ft: i for i, ft in enumerate(PRIMARY_FILING_TYPES)}
```

**Step 3: Create data directory**

```bash
mkdir -p data
touch data/.gitkeep
```

**Step 4: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: all packages install without error.

**Step 5: Verify imports**

```bash
python -c "import edgar; import anthropic; import pydantic; print('OK')"
```

Expected: `OK`

**Step 6: Commit**

```bash
git add requirements.txt pipeline/ data/.gitkeep
git commit -m "scaffold: project structure, dependencies, config"
```

---

## Task 2: Seed CSV Generation

**Files:**
- Create: `pipeline/seeds.py`
- Create: `tests/test_seeds.py`

This is a one-time script that reads `raw/deal_details_Alex_2026.xlsx` and
produces `data/seeds.csv`. Run once, then the CSV is the input going forward.

**Step 1: Write test for slug generation**

```python
# tests/test_seeds.py
from pipeline.seeds import make_slug

def test_slug_basic():
    assert make_slug("Imprivata, Inc.") == "imprivata-inc"

def test_slug_ampersand():
    assert make_slug("Providence & Worcester Railroad Co/RI/") == "providence-worcester-railroad-co-ri"

def test_slug_strips_trailing_hyphens():
    slug = make_slug("PetSmart, Inc.")
    assert not slug.endswith("-")
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_seeds.py -v
```

Expected: FAIL (module not found)

**Step 3: Implement seeds.py**

`pipeline/seeds.py` must:
1. Read `raw/deal_details_Alex_2026.xlsx` with openpyxl.
2. Extract unique deals (group by TargetName — each deal has many event rows).
3. For each deal, extract: target_name, acquirer (winning bidder), date_announced,
   URL (if present).
4. Generate `deal_slug` from target_name.
5. Tag Alex's 9 reference deals with `is_reference = true`.
6. Write `data/seeds.csv`.

Key function signatures:

```python
def make_slug(name: str) -> str:
    """Lowercase, strip punctuation, collapse to hyphens."""

def extract_seeds(xlsx_path: Path) -> list[dict]:
    """Read deal_details xlsx, return one dict per unique deal."""

def write_seeds(seeds: list[dict], output_path: Path) -> None:
    """Write seeds to CSV."""

def main():
    """Entry point: read xlsx, write seeds.csv."""
```

The 9 reference deals to tag (by target name matching):
- Providence & Worcester
- Medivation
- Imprivata
- Zep
- Petsmart
- Penford
- Mac Gray
- Saks
- STec

**Step 4: Run test to verify it passes**

```bash
python -m pytest tests/test_seeds.py -v
```

Expected: PASS

**Step 5: Run seed generation**

```bash
python -m pipeline.seeds
```

Expected: `data/seeds.csv` created with ~390 rows. Inspect first 10 rows.

**Step 6: Commit**

```bash
git add pipeline/seeds.py tests/test_seeds.py data/seeds.csv
git commit -m "feat: seed CSV generation from deal_details xlsx"
```

---

## Task 3: Pydantic Schemas

**Files:**
- Create: `pipeline/schemas.py`
- Create: `tests/test_schemas.py`

All data models for extraction I/O and disk artifacts. Keep lean — only
what's needed for the four stages.

**Step 1: Write schema validation tests**

```python
# tests/test_schemas.py
import pytest
from pipeline.schemas import Actor, Event, EventEvidence, ActorExtraction, EventExtraction

def test_actor_valid():
    a = Actor(actor_id="party-a", name="Party A", aliases=[], actor_type="bidder",
              bidder_subtype="financial", is_grouped=False, group_size=None,
              source_quote="Party A signed a confidentiality agreement")
    assert a.actor_id == "party-a"

def test_actor_invalid_type():
    with pytest.raises(Exception):
        Actor(actor_id="x", name="X", aliases=[], actor_type="INVALID",
              bidder_subtype=None, is_grouped=False, group_size=None,
              source_quote="text")

def test_event_with_range():
    ev = Event(event_id="e1", event_type="proposal", date="mid-February 2013",
               date_normalized="2013-02-15", actor_ids=["party-a"],
               value=None, value_lower=7.5, value_upper=8.0,
               consideration_type="cash",
               evidence=EventEvidence(), source_quote="offered $7.50-$8.00", note=None)
    assert ev.value_lower == 7.5
    assert ev.value_upper == 8.0

def test_event_invalid_type():
    with pytest.raises(Exception):
        Event(event_id="e1", event_type="INVALID", date="Jan 1",
              date_normalized=None, actor_ids=[], value=None,
              value_lower=None, value_upper=None, consideration_type=None,
              evidence=EventEvidence(), source_quote="text", note=None)
```

**Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_schemas.py -v
```

Expected: FAIL (module not found)

**Step 3: Implement schemas.py**

Models to define:

```python
from enum import StrEnum
from pydantic import BaseModel

class ActorType(StrEnum):
    BIDDER = "bidder"
    ADVISOR = "advisor"
    ACTIVIST = "activist"
    TARGET_BOARD = "target_board"

class BidderSubtype(StrEnum):
    STRATEGIC = "strategic"
    FINANCIAL = "financial"
    NON_US = "non_us"

class EventType(StrEnum):
    TARGET_SALE = "target_sale"
    TARGET_SALE_PUBLIC = "target_sale_public"
    BIDDER_SALE = "bidder_sale"
    BIDDER_INTEREST = "bidder_interest"
    ACTIVIST_SALE = "activist_sale"
    SALE_PRESS_RELEASE = "sale_press_release"
    BID_PRESS_RELEASE = "bid_press_release"
    IB_RETENTION = "ib_retention"
    NDA = "nda"
    PROPOSAL = "proposal"
    DROP = "drop"
    DROP_BELOW_M = "drop_below_m"
    DROP_BELOW_INF = "drop_below_inf"
    DROP_AT_INF = "drop_at_inf"
    DROP_TARGET = "drop_target"
    FINAL_ROUND_INF_ANN = "final_round_inf_ann"
    FINAL_ROUND_INF = "final_round_inf"
    FINAL_ROUND_ANN = "final_round_ann"
    FINAL_ROUND = "final_round"
    FINAL_ROUND_EXT_ANN = "final_round_ext_ann"
    FINAL_ROUND_EXT = "final_round_ext"
    EXECUTED = "executed"
    TERMINATED = "terminated"
    RESTARTED = "restarted"

class EventEvidence(BaseModel):
    preceded_by_process_letter: bool | None = None
    accompanied_by_merger_agreement: bool | None = None
    post_final_round: bool | None = None
    filing_language: str | None = None

class Actor(BaseModel):
    actor_id: str
    name: str
    aliases: list[str]
    actor_type: ActorType
    bidder_subtype: BidderSubtype | None = None
    is_grouped: bool
    group_size: int | None = None
    source_quote: str

class ActorExtraction(BaseModel):
    actors: list[Actor]
    count_assertions: list[str]

class Event(BaseModel):
    event_id: str
    event_type: EventType
    date: str
    date_normalized: str | None = None
    actor_ids: list[str]
    value: float | None = None
    value_lower: float | None = None
    value_upper: float | None = None
    consideration_type: str | None = None
    evidence: EventEvidence
    source_quote: str
    note: str | None = None

class DealMetadata(BaseModel):
    target_name: str
    acquirer: str | None = None
    deal_outcome: str | None = None
    date_announced: str | None = None
    date_effective: str | None = None
    consideration_type: str | None = None

class EventExtraction(BaseModel):
    events: list[Event]
    deal_metadata: DealMetadata

# Enrichment output
class EnrichedEvent(BaseModel):
    """Event with classification and cycle info appended."""
    event: Event
    bid_type: str | None = None          # "formal" | "informal"
    classification_rule: str | None = None
    cycle_id: str | None = None

class Enrichment(BaseModel):
    enriched_events: list[EnrichedEvent]
    initiation_type: str | None = None
    formal_boundary_event_id: str | None = None

# Source stage artifacts
class ChronologyBookmark(BaseModel):
    accession_number: str
    heading: str
    start_line: int
    end_line: int

class FilingRecord(BaseModel):
    filing_type: str
    accession_number: str | None = None
    filing_date: str | None = None
    url: str | None = None
    disposition: str  # "selected" | "found" | "not_found"
    html_path: str | None = None
    txt_path: str | None = None

class FilingManifest(BaseModel):
    deal_slug: str
    cik: str | None = None
    target_name: str
    filings: list[FilingRecord]

# Status tracking
class DealStatus(BaseModel):
    status: str
    last_stage: str | None = None
    cost_usd: float = 0.0
    events_extracted: int = 0
    actors_extracted: int = 0
    error: str | None = None
    timestamp: str | None = None
```

**Step 4: Run tests**

```bash
python -m pytest tests/test_schemas.py -v
```

Expected: all PASS

**Step 5: Commit**

```bash
git add pipeline/schemas.py tests/test_schemas.py
git commit -m "feat: pydantic schemas for all pipeline artifacts"
```

---

## Task 4: Stage 1 — Source (edgartools)

**Files:**
- Create: `pipeline/source.py`
- Create: `tests/test_source.py`

This is the largest single module. It uses edgartools for EDGAR interactions
and implements chronology section detection.

**Step 1: Write test for chronology locator**

The chronology locator is the one piece of custom logic in Stage 1. Test it
independently with a fake filing text.

```python
# tests/test_source.py
from pipeline.source import locate_chronology

FAKE_FILING = """
TABLE OF CONTENTS

Background of the Merger............................15

BACKGROUND OF THE MERGER

On January 15, 2015, the Board of Directors of the Company met to discuss
strategic alternatives. Representatives of Goldman Sachs presented a
preliminary analysis of potential transaction structures.

On February 1, 2015, Party A submitted an indication of interest at $25.00
per share. On February 5, 2015, Party B submitted an indication of interest
at $23.00 to $25.00 per share.

OPINION OF GOLDMAN SACHS & CO. LLC

Goldman Sachs rendered its oral opinion to the Board.
""".strip()

def test_locate_chronology_finds_real_section():
    lines = FAKE_FILING.splitlines()
    result = locate_chronology(lines)
    assert result is not None
    start, end, heading = result
    assert "BACKGROUND OF THE MERGER" in heading
    # Should skip TOC entry and find the real narrative
    assert start > 3  # past the TOC entry
    assert end > start

def test_locate_chronology_rejects_toc():
    lines = FAKE_FILING.splitlines()
    result = locate_chronology(lines)
    start, end, heading = result
    section = "\n".join(lines[start:end+1])
    # The real section has dates and party names
    assert "January 15, 2015" in section
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_source.py -v
```

Expected: FAIL

**Step 3: Implement source.py**

Key functions:

```python
def run(seed: dict, deal_dir: Path) -> ChronologyBookmark:
    """Stage 1 entry point. Returns chronology bookmark or raises SourceError."""

def search_filings(target_name: str) -> list[FilingRecord]:
    """Use edgartools to search for all filing types for a target."""

def select_primary(filings: list[FilingRecord]) -> FilingRecord:
    """Pick the best filing based on type preference and chronology presence."""

def download_and_freeze(filing: FilingRecord, deal_dir: Path) -> tuple[Path, Path]:
    """Download filing HTML, convert to text, save both. Return (html_path, txt_path)."""

def locate_chronology(lines: list[str]) -> tuple[int, int, str] | None:
    """Find Background of the Merger section. Returns (start_line, end_line, heading)."""

def write_manifest(deal_dir: Path, manifest: FilingManifest) -> None:
    """Write filing_manifest.json."""

def write_chronology_bookmark(deal_dir: Path, bookmark: ChronologyBookmark) -> None:
    """Write chronology.json."""
```

Implementation notes for the developer:

- `search_filings`: Use `edgar.Company(target_name)`, then
  `company.get_filings(form=form_type)` for each type. Catch exceptions for
  CIK resolution failures.
- `download_and_freeze`: Use `filing.html()` and `filing.text()` from
  edgartools. Write atomically to `source/filings/`.
- `locate_chronology`: Port the heading-detection logic from the archive
  `stage1_sourcing.py` (lines 681-797). Key patterns:
  - Primary regex: `r"(?i)background\s+of\s+(?:the\s+)?(?:merger|offer|transaction)"`
  - Reject TOC entries: real sections have dates + multi-paragraph prose (>50 lines).
  - End boundary: look for "Opinion of", "Certain Projections", "Reasons for".
  - Score candidates by narrative quality (date count, paragraph count).
- Create `source/`, `source/filings/`, `extraction/`, `enrichment/` dirs.

**Step 4: Run tests**

```bash
python -m pytest tests/test_source.py -v
```

Expected: PASS

**Step 5: Manual integration test on one deal**

```bash
python -c "
from pathlib import Path
from pipeline.source import run
seed = {'deal_slug': 'imprivata', 'target_name': 'Imprivata, Inc.', 'primary_url': ''}
deal_dir = Path('data/deals/imprivata')
deal_dir.mkdir(parents=True, exist_ok=True)
result = run(seed, deal_dir)
print(f'Chronology: lines {result.start_line}-{result.end_line} ({result.end_line - result.start_line} lines)')
print(f'Heading: {result.heading}')
"
```

Expected: chronology found (typically 200-1000 lines), heading contains
"Background of the Merger".

Inspect the frozen text:

```bash
wc -l data/deals/imprivata/source/filings/*.txt
head -5 data/deals/imprivata/source/chronology.json
```

**Step 6: Commit**

```bash
git add pipeline/source.py tests/test_source.py
git commit -m "feat: Stage 1 source — edgartools fetch, chronology locator"
```

---

## Task 5: Stage 2 — Extract (Claude API)

**Files:**
- Create: `pipeline/extract.py`
- Create: `pipeline/prompts.py`
- Create: `tests/test_extract.py`

**Step 1: Write prompt templates**

`pipeline/prompts.py` — system prompts for both Claude calls. These are the
most important text artifacts in the pipeline. Derive directly from Alex's
collection instructions (`docs/CollectionInstructions_Alex_2026.qmd`).

Key sections of the actor prompt:
- Identify every entity that signed an NDA or participated in the process.
- Classify as bidder/advisor/activist/target_board.
- For bidders: strategic/financial/non_us.
- Grouped entities ("16 financial buyers") get `is_grouped: true` with size.
- Record verbatim source_quote for first mention.
- Extract count assertions ("20 parties signed NDAs").

Key sections of the event prompt:
- Use the locked actor roster (injected as JSON).
- Extract all 23 event types from the taxonomy.
- For proposals: extract value, value_lower, value_upper, consideration_type.
- Extract evidence attributes (process letter, merger agreement, final round,
  filing language) but DO NOT classify formal/informal.
- Every event must have a verbatim source_quote.
- Normalize dates when obvious; preserve original text always.

```python
# pipeline/prompts.py

ACTOR_SYSTEM_PROMPT = """You are extracting party information from an SEC filing...
[Full prompt derived from Alex's instructions — see CollectionInstructions_Alex_2026.qmd]
"""

EVENT_SYSTEM_PROMPT = """You are extracting chronological M&A events from an SEC filing...
[Full prompt with 23-type taxonomy — see event-taxonomy.md reference]
"""
```

The developer MUST read these files to write accurate prompts:
- `docs/CollectionInstructions_Alex_2026.qmd` (the extraction spec)
- `.cursor/skills/extract-events/references/event-taxonomy.md` (23 event types)
- `.cursor/skills/build-party-register/references/actor-scheme.md` (actor rules)

**Step 2: Write test for extraction parsing**

```python
# tests/test_extract.py
import json
from pipeline.schemas import ActorExtraction, EventExtraction

def test_actor_extraction_parses():
    """Verify schema validates realistic Claude output."""
    raw = {
        "actors": [
            {"actor_id": "party-a", "name": "Party A", "aliases": ["Bidder A"],
             "actor_type": "bidder", "bidder_subtype": "financial",
             "is_grouped": False, "group_size": None,
             "source_quote": "Party A, a financial sponsor, signed a confidentiality agreement"}
        ],
        "count_assertions": ["20 parties executed confidentiality agreements"]
    }
    result = ActorExtraction.model_validate(raw)
    assert len(result.actors) == 1

def test_event_extraction_parses():
    """Verify schema validates realistic Claude output."""
    raw = {
        "events": [
            {"event_id": "e1", "event_type": "nda", "date": "January 15, 2015",
             "date_normalized": "2015-01-15", "actor_ids": ["party-a"],
             "value": None, "value_lower": None, "value_upper": None,
             "consideration_type": None,
             "evidence": {"preceded_by_process_letter": None,
                          "accompanied_by_merger_agreement": None,
                          "post_final_round": None, "filing_language": None},
             "source_quote": "Party A executed a confidentiality agreement on January 15, 2015",
             "note": None}
        ],
        "deal_metadata": {"target_name": "Imprivata, Inc.", "acquirer": "Thoma Bravo",
                          "deal_outcome": "completed", "date_announced": "2016-06-06",
                          "date_effective": "2016-09-01", "consideration_type": "cash"}
    }
    result = EventExtraction.model_validate(raw)
    assert len(result.events) == 1
```

**Step 3: Run test to verify it fails**

```bash
python -m pytest tests/test_extract.py -v
```

Expected: should PASS if schemas are already implemented from Task 3. If not,
fix schema issues first.

**Step 4: Implement extract.py**

```python
# pipeline/extract.py
import anthropic
from pipeline.schemas import ActorExtraction, EventExtraction, ChronologyBookmark
from pipeline.prompts import ACTOR_SYSTEM_PROMPT, EVENT_SYSTEM_PROMPT
from pipeline.config import ANTHROPIC_MODEL

def run(deal_dir: Path) -> tuple[ActorExtraction, EventExtraction]:
    """Stage 2 entry point. Read chronology text, make 2 Claude calls, write artifacts."""

def _read_chronology_text(deal_dir: Path) -> str:
    """Read frozen .txt and extract lines between chronology bookmark bounds."""

def _extract_actors(client: anthropic.Anthropic, chronology_text: str, deal_slug: str) -> ActorExtraction:
    """Claude Call 1: extract actors. Uses structured output with prompt caching."""

def _extract_events(client: anthropic.Anthropic, chronology_text: str,
                    actors: ActorExtraction, deal_slug: str) -> EventExtraction:
    """Claude Call 2: extract events against locked actor roster."""

def _write_artifacts(deal_dir: Path, actors: ActorExtraction, events: EventExtraction) -> None:
    """Write actors.json and events.json to extraction/."""
```

Implementation notes:

- Use `anthropic.Anthropic()` client (reads `ANTHROPIC_API_KEY` env var).
- For structured output, use `client.messages.create()` with `response_model`
  or `tools` parameter to enforce the Pydantic schema. Check Anthropic docs
  for current structured output API.
- Prompt caching: place chronology text in a system message with
  `cache_control={"type": "ephemeral"}` so Call 2 gets the cached text.
- Retry up to 2x on API errors or validation failures.
- The `run()` function should return cost info (input_tokens, output_tokens)
  for status tracking.

**Step 5: Integration test on Imprivata (requires ANTHROPIC_API_KEY)**

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python -c "
from pathlib import Path
from pipeline.extract import run
deal_dir = Path('data/deals/imprivata')
actors, events = run(deal_dir)
print(f'Actors: {len(actors.actors)}')
print(f'Events: {len(events.events)}')
for a in actors.actors[:5]:
    print(f'  {a.actor_id}: {a.name} ({a.actor_type})')
for e in events.events[:5]:
    print(f'  {e.event_type}: {e.date} — {e.source_quote[:80]}')
"
```

Expected: actors and events extracted from Imprivata filing. Inspect
`data/deals/imprivata/extraction/actors.json` and `events.json`.

**Step 6: Commit**

```bash
git add pipeline/extract.py pipeline/prompts.py tests/test_extract.py
git commit -m "feat: Stage 2 extract — Claude two-pass actor and event extraction"
```

---

## Task 6: Stage 3 — Enrich (deterministic Python)

**Files:**
- Create: `pipeline/enrich.py`
- Create: `tests/test_enrich.py`

**Step 1: Write classification rule tests**

```python
# tests/test_enrich.py
from pipeline.enrich import classify_proposal
from pipeline.schemas import Event, EventEvidence

def _make_proposal(**kwargs) -> Event:
    defaults = dict(event_id="e1", event_type="proposal", date="Jan 1",
                    date_normalized=None, actor_ids=["a1"], value=25.0,
                    value_lower=None, value_upper=None, consideration_type="cash",
                    evidence=EventEvidence(), source_quote="offered $25", note=None)
    defaults.update(kwargs)
    if "evidence" in kwargs and isinstance(kwargs["evidence"], dict):
        defaults["evidence"] = EventEvidence(**kwargs["evidence"])
    return Event(**defaults)

def test_merger_agreement_is_formal():
    ev = _make_proposal(evidence={"accompanied_by_merger_agreement": True})
    bid_type, rule = classify_proposal(ev)
    assert bid_type == "formal"
    assert rule == "merger_agreement"

def test_post_final_round_is_formal():
    ev = _make_proposal(evidence={"post_final_round": True})
    bid_type, rule = classify_proposal(ev)
    assert bid_type == "formal"
    assert rule == "post_final_round"

def test_indication_of_interest_is_informal():
    ev = _make_proposal(evidence={"filing_language": "indication of interest"})
    bid_type, rule = classify_proposal(ev)
    assert bid_type == "informal"
    assert rule == "indication_of_interest"

def test_range_bid_is_informal():
    ev = _make_proposal(value_lower=7.5, value_upper=8.0)
    bid_type, rule = classify_proposal(ev)
    assert bid_type == "informal"
    assert rule == "range_bid"

def test_default_is_informal():
    ev = _make_proposal()
    bid_type, rule = classify_proposal(ev)
    assert bid_type == "informal"
    assert rule == "default"

def test_merger_agreement_overrides_range():
    ev = _make_proposal(value_lower=7.5, value_upper=8.0,
                        evidence={"accompanied_by_merger_agreement": True})
    bid_type, rule = classify_proposal(ev)
    assert bid_type == "formal"
    assert rule == "merger_agreement"
```

**Step 2: Run tests to verify they fail**

```bash
python -m pytest tests/test_enrich.py -v
```

Expected: FAIL

**Step 3: Implement enrich.py**

```python
# pipeline/enrich.py

def run(deal_dir: Path) -> Enrichment:
    """Stage 3 entry point. Read extraction artifacts, apply rules, write enrichment."""

def classify_proposal(event: Event) -> tuple[str, str]:
    """Apply formal/informal classification rules. Returns (bid_type, rule_name)."""

def segment_cycles(events: list[Event]) -> dict[str, str]:
    """Assign cycle_id to each event. Returns {event_id: cycle_id}."""

def determine_formal_boundary(enriched: list[EnrichedEvent]) -> str | None:
    """Find the earliest formal proposal event_id."""

def determine_initiation(events: list[Event]) -> str | None:
    """Find initiation type from earliest initiation event."""
```

Classification rules (priority order):
1. `evidence.accompanied_by_merger_agreement` → formal, rule="merger_agreement"
2. `evidence.post_final_round` → formal, rule="post_final_round"
3. `evidence.filing_language` contains "indication of interest" → informal,
   rule="indication_of_interest"
4. `value_lower is not None and value_upper is not None and value_lower != value_upper`
   → informal, rule="range_bid"
5. Default → informal, rule="default"

Cycle segmentation:
- Scan events chronologically for `terminated`/`restarted`.
- Assign `<slug>_c1`, `<slug>_c2`, etc.
- Single-cycle deals: all events get `<slug>_c1`.

**Step 4: Run tests**

```bash
python -m pytest tests/test_enrich.py -v
```

Expected: all PASS

**Step 5: Integration test on Imprivata**

```bash
python -c "
from pathlib import Path
from pipeline.enrich import run
deal_dir = Path('data/deals/imprivata')
result = run(deal_dir)
formal = [e for e in result.enriched_events if e.bid_type == 'formal']
informal = [e for e in result.enriched_events if e.bid_type == 'informal']
print(f'Total enriched events: {len(result.enriched_events)}')
print(f'Formal bids: {len(formal)}, Informal bids: {len(informal)}')
print(f'Initiation: {result.initiation_type}')
"
```

**Step 6: Commit**

```bash
git add pipeline/enrich.py tests/test_enrich.py
git commit -m "feat: Stage 3 enrich — formal/informal classification, cycle segmentation"
```

---

## Task 7: Stage 4 — Assemble (CSV writer)

**Files:**
- Create: `pipeline/assemble.py`
- Create: `tests/test_assemble.py`

**Step 1: Write test for bid_note mapping and row generation**

```python
# tests/test_assemble.py
from pipeline.assemble import event_type_to_bid_note, build_row

def test_bid_note_mapping():
    assert event_type_to_bid_note("nda") == "NDA"
    assert event_type_to_bid_note("proposal") == ""
    assert event_type_to_bid_note("drop") == "Drop"
    assert event_type_to_bid_note("final_round_ann") == "Final Round Ann"
    assert event_type_to_bid_note("executed") == "Executed"
    assert event_type_to_bid_note("ib_retention") == "IB"
    assert event_type_to_bid_note("target_sale") == "Target Sale"
```

**Step 2: Run test to verify it fails**

```bash
python -m pytest tests/test_assemble.py -v
```

Expected: FAIL

**Step 3: Implement assemble.py**

```python
# pipeline/assemble.py
import csv

REVIEW_COLUMNS = [
    "deal_slug", "target_name", "acquirer",
    "event_date", "event_date_normalized",
    "actor_name", "actor_type", "bidder_subtype",
    "event_type", "bid_note",
    "bid_value_pershare", "bid_value_lower", "bid_value_upper",
    "bid_type", "classification_rule",
    "consideration_type", "cycle_id",
    "source_quote", "note",
]

BID_NOTE_MAP = {
    "target_sale": "Target Sale",
    "target_sale_public": "Target Sale Public",
    "bidder_sale": "Bidder Sale",
    "bidder_interest": "Bidder Interest",
    "activist_sale": "Activist Sale",
    "sale_press_release": "Sale Press Release",
    "bid_press_release": "Bid Press Release",
    "ib_retention": "IB",
    "nda": "NDA",
    "proposal": "",
    "drop": "Drop",
    "drop_below_m": "DropBelowM",
    "drop_below_inf": "DropBelowInf",
    "drop_at_inf": "DropAtInf",
    "drop_target": "DropTarget",
    "final_round_inf_ann": "Final Round Inf Ann",
    "final_round_inf": "Final Round Inf",
    "final_round_ann": "Final Round Ann",
    "final_round": "Final Round",
    "final_round_ext_ann": "Final Round Ext Ann",
    "final_round_ext": "Final Round Ext",
    "executed": "Executed",
    "terminated": "Terminated",
    "restarted": "Restarted",
}

def run(deal_dir: Path) -> Path:
    """Stage 4 entry point. Read all artifacts, write per-deal output.csv."""

def event_type_to_bid_note(event_type: str) -> str:
    return BID_NOTE_MAP.get(event_type, event_type)

def build_rows(deal_slug: str, seed: dict, actors: ActorExtraction,
               enrichment: Enrichment) -> list[dict]:
    """Build flat CSV rows from extraction + enrichment artifacts."""

def write_deal_csv(rows: list[dict], output_path: Path) -> None:
    """Write per-deal output.csv."""

def rebuild_master(data_dir: Path) -> None:
    """Read all per-deal output.csv files, concatenate to output/master.csv."""
```

Row building logic:
- For each enriched event, look up the actor(s) by actor_id.
- For events with multiple actors (rare), produce one row per actor.
- For events with no actor (e.g., final_round_ann), produce one row with
  blank actor fields.
- Sort rows by: event_date_normalized → event_type priority → actor_name.
- Truncate source_quote to 200 characters.
- `bid_value_pershare` = `value` if present, else `value_lower` for ranges.

**Step 4: Run tests**

```bash
python -m pytest tests/test_assemble.py -v
```

Expected: PASS

**Step 5: Integration test on Imprivata**

```bash
python -c "
from pathlib import Path
from pipeline.assemble import run
deal_dir = Path('data/deals/imprivata')
csv_path = run(deal_dir)
print(f'Written to: {csv_path}')
# Count rows
import csv
with open(csv_path) as f:
    reader = csv.DictReader(f)
    rows = list(reader)
print(f'Rows: {len(rows)}')
print(f'Columns: {list(rows[0].keys())}')
"
```

**Step 6: Commit**

```bash
git add pipeline/assemble.py tests/test_assemble.py
git commit -m "feat: Stage 4 assemble — 19-column CSV writer with bid_note mapping"
```

---

## Task 8: Batch Runner

**Files:**
- Create: `pipeline/run.py`
- Create: `pipeline/__main__.py`

**Step 1: Implement run.py with CLI**

```python
# pipeline/run.py
import argparse
import json
from datetime import datetime, timezone

def load_status(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}

def save_status(status: dict, path: Path) -> None:
    path.write_text(json.dumps(status, indent=2))

def update_deal_status(status: dict, slug: str, **kwargs) -> None:
    if slug not in status:
        status[slug] = {}
    status[slug].update(kwargs)
    status[slug]["timestamp"] = datetime.now(timezone.utc).isoformat()

def run_deal(seed: dict, data_dir: Path, stages: list[str], status: dict) -> None:
    """Run pipeline stages for a single deal."""
    slug = seed["deal_slug"]
    deal_dir = data_dir / "deals" / slug
    deal_dir.mkdir(parents=True, exist_ok=True)

    if "source" in stages:
        update_deal_status(status, slug, status="source")
        source.run(seed, deal_dir)

    if "extract" in stages:
        update_deal_status(status, slug, status="extract")
        actors, events = extract.run(deal_dir)

    if "enrich" in stages:
        update_deal_status(status, slug, status="enrich")
        enrich.run(deal_dir)

    if "assemble" in stages:
        update_deal_status(status, slug, status="assemble")
        assemble.run(deal_dir)

    update_deal_status(status, slug, status="done")

def main():
    parser = argparse.ArgumentParser(description="M&A Deal Extraction Pipeline")
    parser.add_argument("--slug", help="Process a single deal")
    parser.add_argument("--stage", help="Run only this stage",
                        choices=["source", "extract", "enrich", "assemble"])
    parser.add_argument("--force", action="store_true", help="Re-run completed deals")
    args = parser.parse_args()
    # ... load seeds, filter, loop, handle errors, save status
```

`pipeline/__main__.py`:

```python
from pipeline.run import main
main()
```

**Step 2: Test CLI invocation**

```bash
python -m pipeline.run --slug imprivata --force
```

Expected: runs all 4 stages on Imprivata, prints progress, writes status.json.

```bash
python -m pipeline.run --slug imprivata --stage extract --force
```

Expected: re-runs only Stage 2 (extraction) for Imprivata.

**Step 3: Verify status.json**

```bash
cat data/status.json | python -m json.tool
```

Expected: Imprivata shows `"status": "done"` with event/actor counts.

**Step 4: Verify output files**

```bash
ls -la data/deals/imprivata/source/filings/
cat data/deals/imprivata/source/chronology.json | python -m json.tool
head -5 data/deals/imprivata/extraction/actors.json
head -5 data/deals/imprivata/extraction/events.json
head -2 data/deals/imprivata/output.csv
```

**Step 5: Commit**

```bash
git add pipeline/run.py pipeline/__main__.py
git commit -m "feat: batch runner with CLI, status tracking, per-stage re-run"
```

---

## Task 9: Validation — Alex's 9 Reference Deals

**Files:**
- Create: `scripts/validate_reference_deals.py`

This is the acceptance test. Run the pipeline on Alex's 9 corrected deals and
compare output against `deal_details_Alex_2026.xlsx`.

**Step 1: Run pipeline on all 9 reference deals**

```bash
python -m pipeline.run --slug imprivata
python -m pipeline.run --slug medivation
python -m pipeline.run --slug petsmart-inc
python -m pipeline.run --slug providence-worcester
python -m pipeline.run --slug zep
python -m pipeline.run --slug penford
python -m pipeline.run --slug mac-gray
python -m pipeline.run --slug saks
python -m pipeline.run --slug stec
```

Or, if seeds.csv has `is_reference` column:

```bash
# Filter to reference deals only
python -m pipeline.run --reference-only
```

**Step 2: Write validation script**

`scripts/validate_reference_deals.py`:
- Read `data/output/master.csv` (pipeline output, filtered to reference deals).
- Read `raw/deal_details_Alex_2026.xlsx` (Alex's truth, filtered to the same
  9 deals).
- For each deal, compare:
  - Event count
  - Actor count
  - For each event row: does it match an Alex row by (date, actor, event_type)?
  - For matched rows: bid_value accuracy, bid_type agreement
- Print a comparison report.

**Step 3: Review results, iterate**

This is the feedback loop. Common issues to fix:
- Missing events → adjust Claude prompt to be more exhaustive.
- Wrong actor linking → adjust actor prompt or add alias handling.
- Classification disagreements → adjust enrichment rules.
- Date parsing errors → adjust date normalization.

Each iteration: tweak prompts/rules → re-run `--stage extract` or
`--stage enrich` → re-validate.

**Step 4: Commit validation script**

```bash
git add scripts/validate_reference_deals.py
git commit -m "feat: validation script for 9 reference deals"
```

---

## Summary: Task Execution Order

| Task | Description | Depends on | ~Effort |
|------|-------------|-----------|---------|
| 1 | Project scaffolding | — | 10 min |
| 2 | Seed CSV generation | Task 1 | 30 min |
| 3 | Pydantic schemas | Task 1 | 30 min |
| 4 | Stage 1: Source | Tasks 1, 3 | 60 min |
| 5 | Stage 2: Extract | Tasks 3, 4 | 90 min |
| 6 | Stage 3: Enrich | Tasks 3, 5 | 45 min |
| 7 | Stage 4: Assemble | Tasks 3, 6 | 45 min |
| 8 | Batch runner | Tasks 4-7 | 30 min |
| 9 | Validation | Task 8 | 60 min |

**Total estimated effort: ~7 hours**

Tasks 2 and 3 can run in parallel. Tasks 4-7 are strictly sequential
(each stage's output is the next stage's input).

---

## Checkpoint Review Points

After each task, verify before proceeding:

- **After Task 4 (Source):** Can we find and download the Imprivata DEFM14A?
  Is the chronology section correctly bounded?
- **After Task 5 (Extract):** Do the extracted actors and events for Imprivata
  look reasonable? Are source_quotes verbatim from the filing?
- **After Task 6 (Enrich):** Do the formal/informal classifications match
  Alex's for Imprivata?
- **After Task 8 (Runner):** Can we run `python -m pipeline.run --slug imprivata`
  end-to-end and get a valid `output.csv`?
- **After Task 9 (Validation):** How do the 9 reference deals compare to
  Alex's corrections?
