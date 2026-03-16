# Deal Extraction Pipeline — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an 8-stage SEC deal-extraction pipeline in `bids_data/pipeline/` that extracts evidence-backed facts from EDGAR filings via bounded LLM calls, applies all economic/policy logic in deterministic Python, and exports Alex-style flat rows at the end.

**Architecture:** A single-deal Python pipeline orchestrated by a CLI. Stages 1/4/5/6/7/8 are pure Python scripts. Stages 2/3 use direct LLM API calls with structured outputs (Pydantic models) via a provider-agnostic interface. Every artifact is JSONL. A DuckDB mirror is rebuilt from JSONL for cross-deal queries.

**Tech Stack:** Python 3.13, Pydantic v2, httpx, tiktoken, dateutil, duckdb, pytest. LLM providers: anthropic SDK + openai SDK behind an abstract interface.

---

## Background for the Implementing Agent

You are building a pipeline that reads SEC proxy filings (DEFM14A, PREM14A, etc.) and extracts a structured chronology of M&A auction events. The filing's "Background of the Merger" section is a 10-50 page narrative describing who signed NDAs, who bid, at what price, who dropped out, and how the deal ended.

The pipeline has 8 stages:

```
DealSeed → FrozenCorpus → ActorRoster → RawFacts → VerifiedFacts
         → NormalizedFacts → SemanticState → EvidenceLedger → ModelView
```

**Critical design rules:**
- LLMs extract raw evidence only. They never classify formal/informal, never expand grouped bidders, never compute derived values.
- All policy logic (classification, cycle segmentation, noise filtering) lives in deterministic Python.
- The primitive is the atomic fact, not the spreadsheet row. Rows are projected at the end.
- Grouped bidders (e.g. "16 financial sponsors") stay as one entity with a cardinality integer.
- Range bids store lower + upper bounds. Never collapse to midpoint.
- Dates store raw text + normalized interval + precision flag.
- Every fact carries provenance: accession number, paragraph ID, verbatim quote.

**Key files to read for domain context:**
- `docs/CollectionInstructions_Alex_2026.qmd` — Alex Gorbenko's extraction spec
- `docs/plans/2026-03-15-pipeline-review-meeting-notes.md` — design rationale

---

## Task 1: Project Scaffold and Dependencies

**Files:**
- Create: `pipeline/pyproject.toml`
- Create: `pipeline/src/deal_pipeline/__init__.py`
- Create: `pipeline/src/deal_pipeline/py.typed`
- Create: `pipeline/tests/__init__.py`
- Create: `pipeline/tests/conftest.py`

### Step 1: Create the directory tree

```bash
mkdir -p pipeline/src/deal_pipeline/stages
mkdir -p pipeline/src/deal_pipeline/llm
mkdir -p pipeline/src/deal_pipeline/policy
mkdir -p pipeline/prompts
mkdir -p pipeline/tests/stages
mkdir -p pipeline/tests/policy
mkdir -p pipeline/config
mkdir -p pipeline/data/deals
```

### Step 2: Write `pyproject.toml`

```toml
[project]
name = "deal-pipeline"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.0",
    "httpx>=0.27",
    "tiktoken>=0.7",
    "python-dateutil>=2.9",
    "duckdb>=1.0",
    "anthropic>=0.40",
    "openai>=1.50",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.24"]

[project.scripts]
deal-pipeline = "deal_pipeline.cli:main"

[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

### Step 3: Write `__init__.py` and marker files

`pipeline/src/deal_pipeline/__init__.py`:
```python
"""SEC deal extraction pipeline."""
__version__ = "0.1.0"
```

`pipeline/src/deal_pipeline/py.typed`: empty file.

`pipeline/tests/__init__.py`: empty file.

`pipeline/tests/conftest.py`:
```python
from pathlib import Path
import pytest

FIXTURES = Path(__file__).parent / "fixtures"

@pytest.fixture
def fixtures_dir():
    return FIXTURES
```

### Step 4: Install in dev mode and verify

```bash
cd pipeline && pip install -e ".[dev]" && pytest --co -q
```

Expected: 0 tests collected, no errors.

### Step 5: Commit

```bash
git init && git add -A && git commit -m "scaffold: project structure and dependencies"
```

---

## Task 2: Event Ontology and Core Pydantic Schemas

This is the most important task. Every later stage depends on these types being right.

**Files:**
- Create: `pipeline/src/deal_pipeline/ontology.py`
- Create: `pipeline/src/deal_pipeline/schemas.py`
- Test: `pipeline/tests/test_ontology.py`
- Test: `pipeline/tests/test_schemas.py`

### Step 1: Write ontology tests

`pipeline/tests/test_ontology.py`:

```python
from deal_pipeline.ontology import EventFamily, EventType, EVENT_REGISTRY

def test_every_event_type_has_a_family():
    for et in EventType:
        assert et in EVENT_REGISTRY, f"{et} missing from registry"
        assert isinstance(EVENT_REGISTRY[et].family, EventFamily)

def test_families_from_alex_instructions():
    families = {f.value for f in EventFamily}
    required = {
        "process_initiation", "advisor", "nda", "proposal",
        "dropout", "round", "execution", "process_lifecycle",
        "exclusivity", "press_release",
    }
    assert required.issubset(families)

def test_known_missing_types_from_audit():
    types = {et.value for et in EventType}
    assert "ib_terminated" in types
    assert "target_interest" in types
    assert "exclusivity_granted" in types
    assert "final_round_inf_ext_ann" in types
    assert "final_round_inf_ext" in types

def test_alex_bid_note_mapping_coverage():
    from deal_pipeline.ontology import ALEX_BID_NOTE_MAP
    required_notes = {
        "Target Sale", "Target Sale Public", "Bidder Sale",
        "Bidder Interest", "Activist Sale", "Sale Press Release",
        "Bid Press Release", "IB", "NDA", "Informal Bid", "Formal Bid",
        "Drop", "DropBelowM", "DropBelowInf", "DropAtInf", "DropTarget",
        "Final Round Ann", "Final Round", "Final Round Inf Ann",
        "Final Round Inf", "Final Round Ext Ann", "Final Round Ext",
        "Executed", "Terminated", "Restarted",
    }
    mapped_notes = set(ALEX_BID_NOTE_MAP.values())
    assert required_notes.issubset(mapped_notes), (
        f"Missing: {required_notes - mapped_notes}"
    )
```

### Step 2: Run tests — verify they fail

```bash
cd pipeline && pytest tests/test_ontology.py -v
```

Expected: ImportError — `deal_pipeline.ontology` does not exist.

### Step 3: Implement `ontology.py`

```python
"""Event ontology for M&A deal extraction.

Anchored to Alex Gorbenko's collection instructions (2026-03-03).
Version-frozen per batch. No mid-batch edits.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum


class EventFamily(str, Enum):
    PROCESS_INITIATION = "process_initiation"
    ADVISOR = "advisor"
    NDA = "nda"
    PROPOSAL = "proposal"
    DROPOUT = "dropout"
    ROUND = "round"
    EXECUTION = "execution"
    PROCESS_LIFECYCLE = "process_lifecycle"
    EXCLUSIVITY = "exclusivity"
    PRESS_RELEASE = "press_release"


class EventType(str, Enum):
    # --- process_initiation ---
    TARGET_SALE = "target_sale"
    TARGET_SALE_PUBLIC = "target_sale_public"
    BIDDER_SALE = "bidder_sale"
    BIDDER_INTEREST = "bidder_interest"
    ACTIVIST_SALE = "activist_sale"
    TARGET_INTEREST = "target_interest"

    # --- advisor ---
    IB_RETENTION = "ib_retention"
    IB_TERMINATED = "ib_terminated"

    # --- nda ---
    NDA = "nda"

    # --- proposal ---
    PROPOSAL = "proposal"

    # --- dropout ---
    DROP = "drop"
    DROP_BELOW_M = "drop_below_m"
    DROP_BELOW_INF = "drop_below_inf"
    DROP_AT_INF = "drop_at_inf"
    DROP_TARGET = "drop_target"

    # --- round ---
    FINAL_ROUND_INF_ANN = "final_round_inf_ann"
    FINAL_ROUND_INF = "final_round_inf"
    FINAL_ROUND_ANN = "final_round_ann"
    FINAL_ROUND = "final_round"
    FINAL_ROUND_EXT_ANN = "final_round_ext_ann"
    FINAL_ROUND_EXT = "final_round_ext"
    FINAL_ROUND_INF_EXT_ANN = "final_round_inf_ext_ann"
    FINAL_ROUND_INF_EXT = "final_round_inf_ext"

    # --- execution ---
    EXECUTED = "executed"

    # --- process_lifecycle ---
    TERMINATED = "terminated"
    RESTARTED = "restarted"

    # --- exclusivity ---
    EXCLUSIVITY_GRANTED = "exclusivity_granted"
    EXCLUSIVITY_EXPIRED = "exclusivity_expired"

    # --- press_release ---
    SALE_PRESS_RELEASE = "sale_press_release"
    BID_PRESS_RELEASE = "bid_press_release"


@dataclass(frozen=True)
class EventSpec:
    event_type: EventType
    family: EventFamily
    requires_actor: bool
    requires_value: bool
    alex_bid_note: str


EVENT_REGISTRY: dict[EventType, EventSpec] = {
    # process_initiation
    EventType.TARGET_SALE: EventSpec(EventType.TARGET_SALE, EventFamily.PROCESS_INITIATION, False, False, "Target Sale"),
    EventType.TARGET_SALE_PUBLIC: EventSpec(EventType.TARGET_SALE_PUBLIC, EventFamily.PROCESS_INITIATION, False, False, "Target Sale Public"),
    EventType.BIDDER_SALE: EventSpec(EventType.BIDDER_SALE, EventFamily.PROCESS_INITIATION, True, False, "Bidder Sale"),
    EventType.BIDDER_INTEREST: EventSpec(EventType.BIDDER_INTEREST, EventFamily.PROCESS_INITIATION, True, False, "Bidder Interest"),
    EventType.ACTIVIST_SALE: EventSpec(EventType.ACTIVIST_SALE, EventFamily.PROCESS_INITIATION, True, False, "Activist Sale"),
    EventType.TARGET_INTEREST: EventSpec(EventType.TARGET_INTEREST, EventFamily.PROCESS_INITIATION, True, False, "Target Interest"),
    # advisor
    EventType.IB_RETENTION: EventSpec(EventType.IB_RETENTION, EventFamily.ADVISOR, True, False, "IB"),
    EventType.IB_TERMINATED: EventSpec(EventType.IB_TERMINATED, EventFamily.ADVISOR, True, False, "IB Terminated"),
    # nda
    EventType.NDA: EventSpec(EventType.NDA, EventFamily.NDA, True, False, "NDA"),
    # proposal
    EventType.PROPOSAL: EventSpec(EventType.PROPOSAL, EventFamily.PROPOSAL, True, True, ""),
    # dropout
    EventType.DROP: EventSpec(EventType.DROP, EventFamily.DROPOUT, True, False, "Drop"),
    EventType.DROP_BELOW_M: EventSpec(EventType.DROP_BELOW_M, EventFamily.DROPOUT, True, False, "DropBelowM"),
    EventType.DROP_BELOW_INF: EventSpec(EventType.DROP_BELOW_INF, EventFamily.DROPOUT, True, False, "DropBelowInf"),
    EventType.DROP_AT_INF: EventSpec(EventType.DROP_AT_INF, EventFamily.DROPOUT, True, False, "DropAtInf"),
    EventType.DROP_TARGET: EventSpec(EventType.DROP_TARGET, EventFamily.DROPOUT, True, False, "DropTarget"),
    # round
    EventType.FINAL_ROUND_INF_ANN: EventSpec(EventType.FINAL_ROUND_INF_ANN, EventFamily.ROUND, False, False, "Final Round Inf Ann"),
    EventType.FINAL_ROUND_INF: EventSpec(EventType.FINAL_ROUND_INF, EventFamily.ROUND, False, False, "Final Round Inf"),
    EventType.FINAL_ROUND_ANN: EventSpec(EventType.FINAL_ROUND_ANN, EventFamily.ROUND, False, False, "Final Round Ann"),
    EventType.FINAL_ROUND: EventSpec(EventType.FINAL_ROUND, EventFamily.ROUND, False, False, "Final Round"),
    EventType.FINAL_ROUND_EXT_ANN: EventSpec(EventType.FINAL_ROUND_EXT_ANN, EventFamily.ROUND, False, False, "Final Round Ext Ann"),
    EventType.FINAL_ROUND_EXT: EventSpec(EventType.FINAL_ROUND_EXT, EventFamily.ROUND, False, False, "Final Round Ext"),
    EventType.FINAL_ROUND_INF_EXT_ANN: EventSpec(EventType.FINAL_ROUND_INF_EXT_ANN, EventFamily.ROUND, False, False, "Final Round Inf Ext Ann"),
    EventType.FINAL_ROUND_INF_EXT: EventSpec(EventType.FINAL_ROUND_INF_EXT, EventFamily.ROUND, False, False, "Final Round Inf Ext"),
    # execution
    EventType.EXECUTED: EventSpec(EventType.EXECUTED, EventFamily.EXECUTION, True, False, "Executed"),
    # process_lifecycle
    EventType.TERMINATED: EventSpec(EventType.TERMINATED, EventFamily.PROCESS_LIFECYCLE, False, False, "Terminated"),
    EventType.RESTARTED: EventSpec(EventType.RESTARTED, EventFamily.PROCESS_LIFECYCLE, True, False, "Restarted"),
    # exclusivity
    EventType.EXCLUSIVITY_GRANTED: EventSpec(EventType.EXCLUSIVITY_GRANTED, EventFamily.EXCLUSIVITY, True, False, "Exclusivity"),
    EventType.EXCLUSIVITY_EXPIRED: EventSpec(EventType.EXCLUSIVITY_EXPIRED, EventFamily.EXCLUSIVITY, True, False, "Exclusivity Expired"),
    # press_release
    EventType.SALE_PRESS_RELEASE: EventSpec(EventType.SALE_PRESS_RELEASE, EventFamily.PRESS_RELEASE, False, False, "Sale Press Release"),
    EventType.BID_PRESS_RELEASE: EventSpec(EventType.BID_PRESS_RELEASE, EventFamily.PRESS_RELEASE, True, False, "Bid Press Release"),
}

ALEX_BID_NOTE_MAP: dict[EventType, str] = {
    et: spec.alex_bid_note for et, spec in EVENT_REGISTRY.items()
}


def bid_note_for_proposal(bid_type: str) -> str:
    """Return Alex-style bid_note for a classified proposal."""
    return f"{bid_type.capitalize()} Bid"
```

### Step 4: Run tests — verify they pass

```bash
pytest tests/test_ontology.py -v
```

Expected: all pass.

### Step 5: Write schema tests

`pipeline/tests/test_schemas.py`:

```python
import pytest
from pydantic import ValidationError
from deal_pipeline.schemas import (
    DealSeed, Actor, ActorKind, RawFact, NormalizedFact,
    ProposalEvidence, DateInterval, ValueInterval,
)

def test_deal_seed_requires_slug_and_target():
    seed = DealSeed(deal_slug="s-t-e-c-inc", target_name="STEC INC")
    assert seed.deal_slug == "s-t-e-c-inc"

def test_actor_grouped():
    a = Actor(
        actor_id="stec/group_18",
        canonical_name="18 prospective acquirers",
        actor_kind=ActorKind.BIDDER,
        is_grouped=True,
        group_cardinality=18,
    )
    assert a.is_grouped and a.group_cardinality == 18

def test_actor_ungrouped_default():
    a = Actor(
        actor_id="stec/wdc",
        canonical_name="Western Digital Corporation",
        actor_kind=ActorKind.BIDDER,
    )
    assert not a.is_grouped and a.group_cardinality is None

def test_raw_fact_requires_quote():
    with pytest.raises(ValidationError):
        RawFact(
            fact_id="f1", chunk_id="c1",
            candidate_event_type="proposal",
            raw_date_text="May 3, 2013",
            raw_quote="",  # empty
        )

def test_proposal_evidence_flags():
    ev = ProposalEvidence(
        mentions_draft_agreement=True,
        mentions_indication_of_interest=False,
    )
    assert ev.mentions_draft_agreement is True

def test_date_interval():
    d = DateInterval(lower="2013-05-03", upper="2013-05-03", precision="exact")
    assert d.lower == "2013-05-03"

def test_date_interval_approximate():
    d = DateInterval(lower="2013-02-01", upper="2013-02-28", precision="month_only")
    assert d.precision == "month_only"

def test_value_interval_range():
    v = ValueInterval(lower=6.60, upper=7.10, basis="per_share")
    assert v.lower == 6.60 and v.upper == 7.10
```

### Step 6: Run tests — verify they fail

```bash
pytest tests/test_schemas.py -v
```

Expected: ImportError.

### Step 7: Implement `schemas.py`

```python
"""Pydantic models for all pipeline artifacts.

These are the canonical data contracts. Every stage reads and writes
instances of these models serialized as JSONL.
"""
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field, model_validator


# ── Enums ──

class ActorKind(str, Enum):
    BIDDER = "bidder"
    ADVISOR = "advisor"
    ACTIVIST = "activist"
    TARGET_BOARD = "target_board"
    LEGAL_ADVISOR = "legal_advisor"


class DatePrecision(str, Enum):
    EXACT = "exact"
    APPROXIMATE = "approximate"
    MONTH_ONLY = "month_only"
    QUARTER_ONLY = "quarter_only"
    UNKNOWN = "unknown"


class ValueBasis(str, Enum):
    PER_SHARE = "per_share"
    TOTAL = "total"
    UNKNOWN = "unknown"


class BidderSubtype(str, Enum):
    STRATEGIC = "S"
    FINANCIAL = "F"
    NON_US_STRATEGIC = "non-US S"
    NON_US_FINANCIAL = "non-US F"
    PUBLIC_STRATEGIC = "public S"
    PUBLIC_FINANCIAL = "public F"
    NON_US_PUBLIC_STRATEGIC = "non-US public S"
    NON_US_PUBLIC_FINANCIAL = "non-US public F"
    UNKNOWN = "unknown"


class ConsiderationType(str, Enum):
    CASH = "cash"
    STOCK = "stock"
    MIXED = "mixed"
    CASH_PLUS_CVR = "cash_plus_cvr"
    UNKNOWN = "unknown"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    REPAIRED = "repaired"
    UNVERIFIED = "unverified"
    FAILED = "failed"


# ── Value Objects ──

class DateInterval(BaseModel):
    lower: str = Field(description="ISO date YYYY-MM-DD")
    upper: str = Field(description="ISO date YYYY-MM-DD")
    precision: str = Field(default="exact")


class ValueInterval(BaseModel):
    lower: float
    upper: float
    basis: str = Field(default="per_share")


class ProposalEvidence(BaseModel):
    mentions_draft_agreement: bool = False
    mentions_markup: bool = False
    mentions_indication_of_interest: bool = False
    mentions_binding_offer: bool = False
    mentions_exclusivity: bool = False
    mentions_process_letter: bool = False
    mentions_whole_company: bool = True
    mentions_partial_asset: bool = False


class SourceRef(BaseModel):
    source_doc_id: str = ""
    paragraph_id: str = ""
    line_start: int | None = None
    line_end: int | None = None


# ── Stage 0: DealSeed ──

class DealSeed(BaseModel):
    deal_slug: str
    target_name: str
    cik: str | None = None
    filing_url: str | None = None
    accession_number: str | None = None


# ── Stage 1: FrozenCorpus ──

class Paragraph(BaseModel):
    paragraph_id: str
    source_doc_id: str
    line_start: int
    line_end: int
    text: str


class Chunk(BaseModel):
    chunk_id: str
    source_doc_id: str
    paragraph_ids: list[str]
    line_start: int
    line_end: int
    text: str
    token_count: int


class ChronologySpan(BaseModel):
    source_doc_id: str
    section_heading: str
    start_line: int
    end_line: int
    confidence: str = "high"


class SourceDoc(BaseModel):
    source_doc_id: str
    accession_number: str
    filing_type: str
    filing_url: str
    filing_date: str = ""
    role: str = "primary"
    html_path: str = ""
    txt_path: str = ""


class DealManifest(BaseModel):
    deal_slug: str
    target_name: str
    cik: str = ""
    source_docs: list[SourceDoc] = []
    chronology_span: ChronologySpan | None = None


# ── Stage 2: ActorRoster ──

class Actor(BaseModel):
    actor_id: str
    canonical_name: str
    actor_kind: ActorKind
    bidder_subtype: BidderSubtype | None = None
    is_grouped: bool = False
    group_cardinality: int | None = None
    parent_group_id: str | None = None
    aliases: list[str] = []
    first_source_ref: SourceRef = Field(default_factory=SourceRef)


class ActorRoster(BaseModel):
    deal_slug: str
    actors: list[Actor] = []
    extractor_version: str = ""
    model_fingerprint: str = ""


# ── Stage 3: RawFacts ──

class RawFact(BaseModel):
    fact_id: str
    chunk_id: str
    candidate_event_type: str
    actor_ids: list[str] = []
    raw_date_text: str = ""
    raw_value_text: str = ""
    raw_quote: str = Field(min_length=1)
    source_ref: SourceRef = Field(default_factory=SourceRef)
    proposal_evidence: ProposalEvidence | None = None
    consideration_type: str = ""
    extractor_version: str = ""
    model_fingerprint: str = ""


# ── Stage 4: VerifiedFacts ──

class VerifiedFact(BaseModel):
    fact_id: str
    verification_status: VerificationStatus
    quote_match: bool = True
    actor_ids_valid: bool = True
    repair_note: str = ""
    original_fact: RawFact


# ── Stage 5: NormalizedFacts ──

class NormalizedFact(BaseModel):
    fact_id: str
    candidate_event_type: str
    actor_ids: list[str] = []
    date: DateInterval | None = None
    value: ValueInterval | None = None
    consideration_type: str = ""
    proposal_evidence: ProposalEvidence | None = None
    raw_quote: str
    source_ref: SourceRef = Field(default_factory=SourceRef)
    raw_date_text: str = ""
    raw_value_text: str = ""


# ── Stage 6: SemanticState ──

class Cycle(BaseModel):
    cycle_id: str
    cycle_sequence: int
    start_fact_id: str = ""
    end_fact_id: str = ""
    status: str = "active"


class Judgment(BaseModel):
    judgment_id: str
    target_type: str
    target_id: str
    judgment_kind: str
    judgment_value: str
    rule_id: str
    confidence: str = "high"
    supporting_fact_ids: list[str] = []


class Ambiguity(BaseModel):
    ambiguity_id: str
    target_type: str
    target_id: str
    description: str
    options: list[str] = []
    resolution: str = ""


# ── Stage 7: EvidenceLedger ──

class Event(BaseModel):
    event_id: str
    event_type: str
    cycle_id: str = ""
    date: DateInterval | None = None
    value: ValueInterval | None = None
    consideration_type: str = ""
    is_aggregate: bool = False
    supporting_fact_ids: list[str] = []
    exclusion_reason: str = ""
    policy_version: str = ""


class EventActorLink(BaseModel):
    event_id: str
    actor_id: str
    role: str = "bidder"


# ── Stage 8: ModelView (export) ──

class ExportRow(BaseModel):
    deal_slug: str = ""
    target_name: str = ""
    acquirer: str = ""
    date_announced: str = ""
    date_effective: str = ""
    url: str = ""
    bidder_id: str = ""
    bidder_name: str = ""
    bidder_type_note: str = ""
    bid_value: str = ""
    bid_value_pershare: str = ""
    bid_value_lower: str = ""
    bid_value_upper: str = ""
    bid_type: str = ""
    bid_date_rough: str = ""
    bid_note: str = ""
    all_cash: str = ""
    event_id: str = ""
    event_type: str = ""
    cycle_id: str = ""
    source_quote: str = ""
    needs_review: str = "false"
    review_flags: str = ""
```

### Step 8: Run tests — verify they pass

```bash
pytest tests/test_schemas.py tests/test_ontology.py -v
```

Expected: all pass.

### Step 9: Commit

```bash
git add -A && git commit -m "feat: event ontology and Pydantic schemas"
```

---

## Task 3: Provider-Agnostic LLM Interface

**Files:**
- Create: `pipeline/src/deal_pipeline/llm/__init__.py`
- Create: `pipeline/src/deal_pipeline/llm/base.py`
- Create: `pipeline/src/deal_pipeline/llm/anthropic_backend.py`
- Create: `pipeline/src/deal_pipeline/llm/openai_backend.py`
- Test: `pipeline/tests/test_llm_interface.py`

### Step 1: Write the interface test

```python
"""tests/test_llm_interface.py"""
from deal_pipeline.llm.base import LLMClient, LLMResponse
from pydantic import BaseModel

def test_llm_response_model():
    r = LLMResponse(content="hello", model="test", input_tokens=10, output_tokens=5)
    assert r.content == "hello"

def test_llm_client_is_abstract():
    import pytest
    with pytest.raises(TypeError):
        LLMClient()
```

### Step 2: Run — verify fail

```bash
pytest tests/test_llm_interface.py -v
```

### Step 3: Implement `llm/base.py`

```python
"""Provider-agnostic LLM interface."""
from __future__ import annotations
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Any


class LLMResponse(BaseModel):
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    raw: Any = None


class LLMClient(ABC):
    @abstractmethod
    def complete(
        self,
        system: str,
        user: str,
        *,
        model: str = "",
        temperature: float = 0.0,
        max_tokens: int = 4096,
        response_schema: type[BaseModel] | None = None,
    ) -> LLMResponse:
        ...
```

### Step 4: Implement `llm/anthropic_backend.py`

```python
"""Anthropic Claude backend."""
from __future__ import annotations
import json
from pydantic import BaseModel
from deal_pipeline.llm.base import LLMClient, LLMResponse

try:
    import anthropic
except ImportError:
    anthropic = None  # type: ignore


class AnthropicClient(LLMClient):
    def __init__(self, api_key: str | None = None, default_model: str = "claude-sonnet-4-20250514"):
        if anthropic is None:
            raise ImportError("pip install anthropic")
        self._client = anthropic.Anthropic(api_key=api_key)
        self._default_model = default_model

    def complete(
        self,
        system: str,
        user: str,
        *,
        model: str = "",
        temperature: float = 0.0,
        max_tokens: int = 4096,
        response_schema: type[BaseModel] | None = None,
    ) -> LLMResponse:
        model = model or self._default_model
        messages = [{"role": "user", "content": user}]

        kwargs: dict = dict(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages,
        )

        if response_schema is not None:
            schema = response_schema.model_json_schema()
            kwargs["tools"] = [{
                "name": "structured_output",
                "description": "Return structured data",
                "input_schema": schema,
            }]
            kwargs["tool_choice"] = {"type": "tool", "name": "structured_output"}

        resp = self._client.messages.create(**kwargs)

        if response_schema is not None:
            for block in resp.content:
                if block.type == "tool_use":
                    content = json.dumps(block.input)
                    break
            else:
                content = resp.content[0].text if resp.content else ""
        else:
            content = resp.content[0].text if resp.content else ""

        return LLMResponse(
            content=content,
            model=model,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
        )
```

### Step 5: Implement `llm/openai_backend.py`

```python
"""OpenAI backend."""
from __future__ import annotations
from pydantic import BaseModel
from deal_pipeline.llm.base import LLMClient, LLMResponse

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str | None = None, default_model: str = "gpt-4o"):
        if OpenAI is None:
            raise ImportError("pip install openai")
        self._client = OpenAI(api_key=api_key)
        self._default_model = default_model

    def complete(
        self,
        system: str,
        user: str,
        *,
        model: str = "",
        temperature: float = 0.0,
        max_tokens: int = 4096,
        response_schema: type[BaseModel] | None = None,
    ) -> LLMResponse:
        model = model or self._default_model
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        kwargs: dict = dict(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        if response_schema is not None:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": response_schema.__name__,
                    "schema": response_schema.model_json_schema(),
                    "strict": True,
                },
            }

        resp = self._client.chat.completions.create(**kwargs)
        choice = resp.choices[0]

        return LLMResponse(
            content=choice.message.content or "",
            model=model,
            input_tokens=resp.usage.input_tokens if resp.usage else 0,
            output_tokens=resp.usage.output_tokens if resp.usage else 0,
        )
```

### Step 6: Write `llm/__init__.py`

```python
from deal_pipeline.llm.base import LLMClient, LLMResponse
from deal_pipeline.llm.anthropic_backend import AnthropicClient
from deal_pipeline.llm.openai_backend import OpenAIClient

__all__ = ["LLMClient", "LLMResponse", "AnthropicClient", "OpenAIClient"]
```

### Step 7: Run tests — verify pass

```bash
pytest tests/test_llm_interface.py -v
```

### Step 8: Commit

```bash
git add -A && git commit -m "feat: provider-agnostic LLM interface with Anthropic and OpenAI backends"
```

---

## Task 4: Stage 1 — FrozenCorpus

**Files:**
- Create: `pipeline/src/deal_pipeline/stages/__init__.py`
- Create: `pipeline/src/deal_pipeline/stages/frozen_corpus.py`
- Test: `pipeline/tests/stages/test_frozen_corpus.py`
- Create: `pipeline/tests/stages/__init__.py`

### Step 1: Write tests

Key behaviors to test (unit tests with fixture HTML, not live EDGAR):
1. `strip_html_to_text` preserves paragraph breaks, strips tags
2. `build_paragraphs` creates stable paragraph IDs with line numbers
3. `build_chunks` creates token-budgeted chunks with overlap
4. `find_chronology_span` finds "Background of the Merger" heading

Create a test fixture at `pipeline/tests/fixtures/sample_filing.html` with ~20 paragraphs of fake SEC prose including a "Background of the Merger" heading.

```python
"""tests/stages/test_frozen_corpus.py"""
from pathlib import Path
from deal_pipeline.stages.frozen_corpus import (
    strip_html_to_text,
    build_paragraphs,
    build_chunks,
    find_chronology_span,
)

SAMPLE = Path(__file__).parent.parent / "fixtures" / "sample_filing.html"

def test_strip_html_removes_tags():
    html = "<p>Hello <b>world</b></p><script>bad</script>"
    text = strip_html_to_text(html)
    assert "<" not in text
    assert "bad" not in text
    assert "Hello world" in text

def test_build_paragraphs_assigns_stable_ids():
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    paras = build_paragraphs(text, source_doc_id="test_doc")
    assert len(paras) == 3
    assert paras[0].paragraph_id == "test_doc_p0"
    assert paras[1].text == "Second paragraph."

def test_build_chunks_respects_token_budget():
    text = "\n\n".join(f"Paragraph {i} with some filler text." for i in range(20))
    paras = build_paragraphs(text, source_doc_id="test")
    chunks = build_chunks(paras, source_doc_id="test", max_tokens=100, overlap_paragraphs=2)
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.token_count <= 150  # allow small overshoot for paragraph alignment

def test_build_chunks_overlap():
    text = "\n\n".join(f"Paragraph {i}." for i in range(10))
    paras = build_paragraphs(text, source_doc_id="test")
    chunks = build_chunks(paras, source_doc_id="test", max_tokens=30, overlap_paragraphs=2)
    if len(chunks) >= 2:
        ids_0 = set(chunks[0].paragraph_ids)
        ids_1 = set(chunks[1].paragraph_ids)
        assert len(ids_0 & ids_1) > 0, "chunks should overlap"

def test_find_chronology_span():
    text = "Some preamble.\n\nBackground of the Merger\n\nOn January 5..."
    span = find_chronology_span(text, source_doc_id="test")
    assert span is not None
    assert "background" in span.section_heading.lower()
```

### Step 2: Run — verify fail

```bash
pytest tests/stages/test_frozen_corpus.py -v
```

### Step 3: Implement `stages/frozen_corpus.py`

Implement:
- `strip_html_to_text(html: str) -> str` — remove script/style/head, strip tags, collapse whitespace, preserve double-newline paragraph breaks.
- `build_paragraphs(text: str, source_doc_id: str) -> list[Paragraph]` — split on double newlines, assign stable IDs.
- `build_chunks(paragraphs, source_doc_id, max_tokens=2000, overlap_paragraphs=2) -> list[Chunk]` — use tiktoken `cl100k_base` for counting, slide forward dropping oldest paragraphs when budget exceeded, always include overlap.
- `find_chronology_span(text, source_doc_id) -> ChronologySpan | None` — regex search for "Background of the Merger/Offer/Transaction", skip TOC lines (short lines), return line range.
- `fetch_filing(url: str, output_dir: Path) -> Path` — httpx GET with SEC User-Agent, save HTML.
- `run_frozen_corpus(seed: DealSeed, output_dir: Path) -> DealManifest` — orchestrate the full stage.

Use `tiktoken` for token counting. Use `re` for HTML stripping (no lxml dependency needed for SEC HTML).

### Step 4: Run — verify pass

```bash
pytest tests/stages/test_frozen_corpus.py -v
```

### Step 5: Commit

```bash
git add -A && git commit -m "feat: Stage 1 FrozenCorpus — HTML strip, paragraph index, token-budgeted chunks"
```

---

## Task 5: Stage 2 — ActorRoster

**Files:**
- Create: `pipeline/src/deal_pipeline/stages/actor_roster.py`
- Create: `pipeline/prompts/actor_census.txt`
- Test: `pipeline/tests/stages/test_actor_roster.py`

### Step 1: Write tests

```python
"""tests/stages/test_actor_roster.py"""
from deal_pipeline.stages.actor_roster import merge_actor_lists, ActorCandidate
from deal_pipeline.schemas import ActorKind

def test_merge_deduplicates_by_name():
    candidates = [
        ActorCandidate(name="Party A", kind="bidder", is_grouped=False),
        ActorCandidate(name="Party A", kind="bidder", is_grouped=False),
        ActorCandidate(name="J.P. Morgan", kind="advisor", is_grouped=False),
    ]
    merged = merge_actor_lists(candidates, deal_slug="test")
    names = [a.canonical_name for a in merged]
    assert names.count("Party A") == 1
    assert "J.P. Morgan" in names

def test_grouped_actor_preserved():
    candidates = [
        ActorCandidate(name="15 financial sponsors", kind="bidder", is_grouped=True, group_size=15),
    ]
    merged = merge_actor_lists(candidates, deal_slug="test")
    assert merged[0].is_grouped
    assert merged[0].group_cardinality == 15

def test_sequential_labels_never_merged():
    candidates = [
        ActorCandidate(name="Party A", kind="bidder", is_grouped=False),
        ActorCandidate(name="Party B", kind="bidder", is_grouped=False),
    ]
    merged = merge_actor_lists(candidates, deal_slug="test")
    assert len(merged) == 2

def test_stable_actor_ids():
    candidates = [
        ActorCandidate(name="Western Digital Corporation", kind="bidder", is_grouped=False),
    ]
    merged = merge_actor_lists(candidates, deal_slug="stec")
    assert merged[0].actor_id == "stec/western_digital_corporation"
```

### Step 2: Run — verify fail

### Step 3: Implement

- Define `ActorCandidate` as a simple dataclass for LLM output parsing.
- Write the census prompt in `prompts/actor_census.txt` (~300 tokens). It tells the LLM: "Read this text chunk. List every entity. For grouped entities use is_grouped=true with integer size. Do NOT extract events."
- `extract_actors_from_chunk(chunk: Chunk, llm: LLMClient) -> list[ActorCandidate]` — calls LLM with the chunk text and the census prompt, parses structured output.
- `merge_actor_lists(candidates: list[ActorCandidate], deal_slug: str) -> list[Actor]` — pure Python dedup. Rules: exact match on name, sequential labels (Party A/B/C) never merged, grouped actors stay grouped, ID = `{deal_slug}/{slugified_name}`.
- `run_actor_roster(chunks: list[Chunk], deal_slug: str, llm: LLMClient) -> ActorRoster` — map over chunks, reduce with merge.

### Step 4: Run — verify pass

### Step 5: Commit

```bash
git add -A && git commit -m "feat: Stage 2 ActorRoster — LLM census + deterministic merge"
```

---

## Task 6: Stage 3 — RawFacts

**Files:**
- Create: `pipeline/src/deal_pipeline/stages/raw_facts.py`
- Create: `pipeline/prompts/fact_extraction.txt`
- Test: `pipeline/tests/stages/test_raw_facts.py`

### Step 1: Write tests

Test that:
1. The extraction prompt enforces the roster constraint (no new actors).
2. Raw facts carry all required fields.
3. Proposal facts carry evidence flags but NO formal/informal classification.
4. The output is one JSONL line per fact.

### Step 2: Run — verify fail

### Step 3: Implement

- Write the extraction prompt in `prompts/fact_extraction.txt` (~600 tokens). Key directives: "Extract events from this chunk. Map actors STRICTLY to the provided actor_id list. Do NOT create new actors. Do NOT classify formal/informal. Extract raw date text exactly as written. For proposals, extract lower/upper value strings and evidence flags."
- `extract_facts_from_chunk(chunk, roster, llm) -> list[RawFact]` — sends chunk text + actor ID list + prompt, parses structured output.
- `run_raw_facts(chunks, roster, llm) -> list[RawFact]` — map over chunks.
- Each fact gets a UUID-based `fact_id`.

### Step 4: Run — verify pass

### Step 5: Commit

```bash
git add -A && git commit -m "feat: Stage 3 RawFacts — bounded LLM fact extraction"
```

---

## Task 7: Stage 4 — VerifiedFacts

**Files:**
- Create: `pipeline/src/deal_pipeline/stages/verified_facts.py`
- Test: `pipeline/tests/stages/test_verified_facts.py`

### Step 1: Write tests

Test that:
1. A fact with an exact substring match in the corpus passes verification.
2. A fact with a hallucinated quote fails.
3. A fact referencing an actor_id not in the roster fails.
4. A reflection loop is triggered for a missing NDA (mock the LLM call).

### Step 2: Run — verify fail

### Step 3: Implement

- `verify_quote(fact: RawFact, corpus_text: str) -> bool` — check `fact.raw_quote in corpus_text`.
- `verify_actor_ids(fact: RawFact, roster: ActorRoster) -> bool` — check all actor_ids exist.
- `run_reflection_loop(failure, chunks, roster, llm) -> RawFact | None` — targeted retry with narrow prompt.
- `run_verification(raw_facts, corpus_text, roster, llm) -> tuple[list[VerifiedFact], list[dict]]` — returns verified facts + verification log.

### Step 4: Run — verify pass

### Step 5: Commit

```bash
git add -A && git commit -m "feat: Stage 4 VerifiedFacts — quote checks and reflection loops"
```

---

## Task 8: Stage 5 — NormalizedFacts

**Files:**
- Create: `pipeline/src/deal_pipeline/stages/normalized_facts.py`
- Test: `pipeline/tests/stages/test_normalized_facts.py`

### Step 1: Write tests

Test that:
1. "May 3, 2013" → DateInterval(lower="2013-05-03", upper="2013-05-03", precision="exact")
2. "mid-February 2013" → DateInterval(lower="2013-02-10", upper="2013-02-20", precision="approximate")
3. "6.60-7.10" → ValueInterval(lower=6.60, upper=7.10, basis="per_share")
4. "$6.85 per share" → ValueInterval(lower=6.85, upper=6.85, basis="per_share")
5. Duplicate facts from overlapping chunks are deduplicated.

### Step 2: Run — verify fail

### Step 3: Implement

- `parse_date(raw: str) -> DateInterval` — use `dateutil.parser` for exact dates, dictionary for modifiers ("early"→1-10, "mid"→10-20, "late"→20-end), month-only → first-to-last.
- `parse_value(raw: str) -> ValueInterval | None` — regex for "$X.XX", "X-Y", "X to Y".
- `deduplicate_facts(facts: list[VerifiedFact]) -> list[VerifiedFact]` — hash on `(candidate_event_type, sorted(actor_ids), raw_date_text)`.
- `run_normalization(verified_facts) -> list[NormalizedFact]`.

### Step 4: Run — verify pass

### Step 5: Commit

```bash
git add -A && git commit -m "feat: Stage 5 NormalizedFacts — date/value parsing and dedup"
```

---

## Task 9: Stage 6 — SemanticState (Policy Engine)

This is the most important stage. All hard semantic logic lives here.

**Files:**
- Create: `pipeline/src/deal_pipeline/policy/__init__.py`
- Create: `pipeline/src/deal_pipeline/policy/cycles.py`
- Create: `pipeline/src/deal_pipeline/policy/classification.py`
- Create: `pipeline/src/deal_pipeline/policy/noise.py`
- Create: `pipeline/src/deal_pipeline/policy/groups.py`
- Create: `pipeline/src/deal_pipeline/stages/semantic_state.py`
- Test: `pipeline/tests/policy/test_classification.py`
- Test: `pipeline/tests/policy/test_cycles.py`
- Test: `pipeline/tests/policy/test_noise.py`
- Test: `pipeline/tests/policy/__init__.py`

### Step 1: Write classification tests

```python
"""tests/policy/test_classification.py"""
from deal_pipeline.policy.classification import classify_proposal

def test_draft_agreement_is_formal():
    result = classify_proposal(
        has_draft_agreement=True, is_range=False,
        is_ioi_language=False, post_final_round=False,
        bidder_dropped_and_reentered=False,
    )
    assert result.value == "formal"
    assert result.rule_id == "draft_agreement"

def test_range_bid_is_informal():
    result = classify_proposal(
        has_draft_agreement=False, is_range=True,
        is_ioi_language=False, post_final_round=False,
        bidder_dropped_and_reentered=False,
    )
    assert result.value == "informal"
    assert result.rule_id == "range_bid"

def test_ioi_language_is_informal():
    result = classify_proposal(
        has_draft_agreement=False, is_range=False,
        is_ioi_language=True, post_final_round=False,
        bidder_dropped_and_reentered=False,
    )
    assert result.value == "informal"

def test_post_final_round_is_formal():
    result = classify_proposal(
        has_draft_agreement=False, is_range=False,
        is_ioi_language=False, post_final_round=True,
        bidder_dropped_and_reentered=False,
    )
    assert result.value == "formal"

def test_reentry_without_markup_is_informal():
    result = classify_proposal(
        has_draft_agreement=False, is_range=False,
        is_ioi_language=False, post_final_round=True,
        bidder_dropped_and_reentered=True,
    )
    assert result.value == "informal"
    assert result.rule_id == "reentry_no_markup"

def test_default_is_informal():
    result = classify_proposal(
        has_draft_agreement=False, is_range=False,
        is_ioi_language=False, post_final_round=False,
        bidder_dropped_and_reentered=False,
    )
    assert result.value == "informal"
```

### Step 2: Write cycle segmentation tests

```python
"""tests/policy/test_cycles.py"""
from deal_pipeline.policy.cycles import segment_cycles

def test_terminated_creates_new_cycle():
    events = [
        {"fact_id": "f1", "event_type": "target_sale", "date": "2012-01-01"},
        {"fact_id": "f2", "event_type": "terminated", "date": "2012-06-01"},
        {"fact_id": "f3", "event_type": "restarted", "date": "2013-01-01"},
        {"fact_id": "f4", "event_type": "nda", "date": "2013-02-01"},
    ]
    cycles = segment_cycles(events)
    assert len(cycles) == 2
    assert cycles[0].status == "terminated"
    assert cycles[1].status == "active"

def test_single_cycle_no_termination():
    events = [
        {"fact_id": "f1", "event_type": "target_sale", "date": "2014-01-01"},
        {"fact_id": "f2", "event_type": "nda", "date": "2014-02-01"},
        {"fact_id": "f3", "event_type": "executed", "date": "2014-06-01"},
    ]
    cycles = segment_cycles(events)
    assert len(cycles) == 1
```

### Step 3: Write noise filter tests

```python
"""tests/policy/test_noise.py"""
from deal_pipeline.policy.noise import is_noise_actor

def test_unsolicited_no_nda_no_followup_is_noise():
    actor_events = [{"event_type": "bidder_interest"}]
    process_events = [
        {"event_type": "target_sale", "date": "2014-01-01"},
    ]
    assert is_noise_actor(actor_events, process_events, triggered_process=False)

def test_unsolicited_that_triggered_process_is_not_noise():
    actor_events = [{"event_type": "bidder_sale"}]
    assert not is_noise_actor(actor_events, [], triggered_process=True)

def test_actor_with_nda_is_not_noise():
    actor_events = [
        {"event_type": "bidder_interest"},
        {"event_type": "nda"},
    ]
    assert not is_noise_actor(actor_events, [], triggered_process=False)
```

### Step 4: Run all policy tests — verify fail

```bash
pytest tests/policy/ -v
```

### Step 5: Implement all policy modules

**`policy/classification.py`:**
```python
from dataclasses import dataclass

@dataclass
class ClassificationResult:
    value: str      # "formal" | "informal"
    rule_id: str
    confidence: str = "high"

def classify_proposal(
    *,
    has_draft_agreement: bool,
    is_range: bool,
    is_ioi_language: bool,
    post_final_round: bool,
    bidder_dropped_and_reentered: bool,
) -> ClassificationResult:
    if has_draft_agreement:
        return ClassificationResult("formal", "draft_agreement")
    if is_range:
        return ClassificationResult("informal", "range_bid")
    if is_ioi_language:
        return ClassificationResult("informal", "ioi_language")
    if post_final_round and bidder_dropped_and_reentered:
        return ClassificationResult("informal", "reentry_no_markup")
    if post_final_round:
        return ClassificationResult("formal", "post_final_round")
    return ClassificationResult("informal", "default_informal")
```

**`policy/cycles.py`:** Segment on `terminated`/`restarted` events. Assign cycle IDs.

**`policy/noise.py`:** Check if actor has NDA, executed, or triggered process. If none, mark noise.

**`policy/groups.py`:** Grouped actor lifecycle arithmetic. Track cardinality changes from dropout text.

**`stages/semantic_state.py`:** Orchestrate: sort facts by date → segment cycles → classify proposals → filter noise → emit judgments + ambiguities.

### Step 6: Run all policy tests — verify pass

```bash
pytest tests/policy/ -v
```

### Step 7: Commit

```bash
git add -A && git commit -m "feat: Stage 6 SemanticState — classification, cycles, noise filtering"
```

---

## Task 10: Stage 7 & 8 — EvidenceLedger and ModelView

**Files:**
- Create: `pipeline/src/deal_pipeline/stages/evidence_ledger.py`
- Create: `pipeline/src/deal_pipeline/stages/model_view.py`
- Test: `pipeline/tests/stages/test_evidence_ledger.py`
- Test: `pipeline/tests/stages/test_model_view.py`

### Step 1: Write tests

Test that:
1. Every event in the ledger has non-empty `supporting_fact_ids`.
2. Excluded events have `exclusion_reason` set.
3. Export rows use lower bound for `bid_value_pershare` on range bids.
4. `bidder_id` is a sequential integer rendered at export time from chronological sort.
5. Grouped actors produce exactly one row per event, not N rows.
6. `bid_note` matches Alex's labels via the ontology mapping.

### Step 2: Run — verify fail

### Step 3: Implement

**`stages/evidence_ledger.py`:**
- `build_events(normalized_facts, semantic_state) -> list[Event]` — one event per accepted fact with provenance links.
- `build_event_actor_links(events, facts) -> list[EventActorLink]`
- `write_ledger(deal_dir, events, actors, links, judgments, cycles, ambiguities)` — write all JSONL files.

**`stages/model_view.py`:**
- `project_export_rows(ledger, roster, manifest, judgments) -> list[ExportRow]`
- Sort by `(date, event_type_priority, actor_name)`.
- Assign `bidder_id` as sequential integer after sort.
- For proposals: `bid_value_pershare = value.lower`, `bid_value_lower = value.lower`, `bid_value_upper = value.upper`.
- `bid_note` from `ALEX_BID_NOTE_MAP` for non-proposals; `bid_note_for_proposal(bid_type)` for proposals.
- `bid_type` from the classification judgment.
- Write `export_rows.jsonl` and `export_rows.csv`.

### Step 4: Run — verify pass

### Step 5: Commit

```bash
git add -A && git commit -m "feat: Stage 7-8 EvidenceLedger and ModelView export"
```

---

## Task 11: Pipeline Orchestrator and CLI

**Files:**
- Create: `pipeline/src/deal_pipeline/runner.py`
- Create: `pipeline/src/deal_pipeline/cli.py`
- Test: `pipeline/tests/test_runner.py`

### Step 1: Write tests

Test that `run_pipeline(seed, output_dir, llm)` calls stages in order and writes all expected artifact files.

### Step 2: Run — verify fail

### Step 3: Implement

**`runner.py`:**

```python
def run_pipeline(
    seed: DealSeed,
    output_dir: Path,
    llm: LLMClient,
    *,
    policy_version: str = "v0.1",
) -> Path:
    deal_dir = output_dir / seed.deal_slug
    deal_dir.mkdir(parents=True, exist_ok=True)

    # Stage 1: FrozenCorpus
    manifest = run_frozen_corpus(seed, deal_dir)

    # Stage 2: ActorRoster
    roster = run_actor_roster(chunks, seed.deal_slug, llm)

    # Stage 3: RawFacts
    raw_facts = run_raw_facts(chunks, roster, llm)

    # Stage 4: VerifiedFacts
    verified, vlog = run_verification(raw_facts, corpus_text, roster, llm)

    # Stage 5: NormalizedFacts
    normalized = run_normalization(verified)

    # Stage 6: SemanticState
    state = run_semantic_state(normalized, roster, policy_version)

    # Stage 7: EvidenceLedger
    write_ledger(deal_dir, ...)

    # Stage 8: ModelView
    rows = project_export_rows(...)
    write_export(deal_dir, rows)

    return deal_dir
```

**`cli.py`:**

```python
import argparse
from pathlib import Path
from deal_pipeline.schemas import DealSeed
from deal_pipeline.runner import run_pipeline
from deal_pipeline.llm import AnthropicClient

def main():
    parser = argparse.ArgumentParser(description="Run deal extraction pipeline")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--url", default=None)
    parser.add_argument("--cik", default=None)
    parser.add_argument("--output", default="pipeline/data/deals")
    parser.add_argument("--provider", default="anthropic", choices=["anthropic", "openai"])
    args = parser.parse_args()

    seed = DealSeed(
        deal_slug=args.slug,
        target_name=args.target,
        filing_url=args.url,
        cik=args.cik,
    )

    if args.provider == "anthropic":
        llm = AnthropicClient()
    else:
        from deal_pipeline.llm import OpenAIClient
        llm = OpenAIClient()

    result = run_pipeline(seed, Path(args.output), llm)
    print(f"Done: {result}")
```

### Step 4: Run — verify pass

```bash
pytest tests/test_runner.py -v
```

### Step 5: Commit

```bash
git add -A && git commit -m "feat: pipeline orchestrator and CLI entry point"
```

---

## Task 12: Gold-Set Validation Tooling

**Files:**
- Create: `pipeline/src/deal_pipeline/validation.py`
- Test: `pipeline/tests/test_validation.py`

### Step 1: Write tests

Test that:
1. A perfect match between pipeline output and gold data produces 0 mismatches.
2. A missing event produces a mismatch of type `extraction_bug`.
3. A wrong bid value produces a mismatch of type `normalization_bug`.
4. A wrong formal/informal produces a mismatch of type `policy_bug`.

### Step 2: Run — verify fail

### Step 3: Implement

- `load_gold_set(excel_path: Path, deal_slug: str) -> list[dict]` — read Alex's corrected rows from `deal_details_Alex_2026.xlsx` for one deal.
- `compare_deal(export_rows: list[ExportRow], gold_rows: list[dict]) -> list[Mismatch]` — align on `(date, bidder_name, bid_note)` tuples, classify each difference.
- `MismatchType` enum: `extraction_bug`, `normalization_bug`, `policy_bug`, `policy_ambiguity`, `gold_set_issue`, `row_count_difference`.
- `generate_validation_report(mismatches) -> str` — human-readable markdown report.

### Step 4: Run — verify pass

### Step 5: Commit

```bash
git add -A && git commit -m "feat: gold-set validation and typed mismatch ledger"
```

---

## Execution Notes for the Implementing Agent

1. **TDD is mandatory.** Write the test, watch it fail, then implement. Do not write implementation code before its test.

2. **Do not over-build.** Each stage should be the minimum code that passes its tests. Refactor only after green.

3. **The ontology and schemas (Task 2) are the foundation.** Get these right first. Everything else depends on them.

4. **The policy engine (Task 9) is the hardest part.** The classification rules must match Alex's instructions exactly. When in doubt, default to informal.

5. **LLM calls in tests:** For stages 2/3/4 that call LLMs, write unit tests with mock LLM responses. Integration tests with real API calls are optional and should be marked `@pytest.mark.integration`.

6. **File paths:** All implementation goes under `bids_data/pipeline/`. Raw data stays in `bids_data/raw/`. Docs stay in `bids_data/docs/`.

7. **No legacy code.** Do not import from or reference `informal_bids`. If you need domain knowledge, read `docs/CollectionInstructions_Alex_2026.qmd`.

---

Plan complete and saved to `docs/plans/2026-03-15-deal-pipeline-implementation.md`. Two execution options:

**1. Subagent-Driven (this session)** — I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** — Open new session with executing-plans, batch execution with checkpoints

Which approach?
