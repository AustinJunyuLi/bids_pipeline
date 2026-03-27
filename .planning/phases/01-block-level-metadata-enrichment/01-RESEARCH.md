# Phase 1: Block-Level Metadata Enrichment - Research

**Researched:** 2026-03-27
**Domain:** Deterministic text annotation for SEC filing chronology blocks (Python regex, Pydantic schema extension, line-range overlap computation)
**Confidence:** HIGH

---

## Summary

Phase 1 enriches `ChronologyBlock` objects with four deterministic annotation fields: date mentions, entity mentions, evidence density score, and temporal phase hint. These annotations are consumed downstream by the prompt composition engine (Phase 2) as structured attention-steering metadata.

All infrastructure for this work already exists in the codebase. The date regex patterns in `normalize/dates.py` are comprehensive and directly reusable. The evidence item line ranges are structurally compatible with block line ranges, making density computation a straightforward interval-overlap scan. The only substantive design question is schema extension strategy: whether to add optional fields to `ChronologyBlock` directly or produce a parallel `AnnotatedBlock` artifact.

The key insight from examining the stec data: the chronology section ends at block B102/B103 (execution of merger agreement / press release), after which B103 onward is fairness opinion and board reasons — outside the deal-process narrative. The "Background of the Merger" section is the true extraction target and its phase structure is predictable: initiation signals (board authorizes, advisor search), bidding signals (NDAs, proposals, process letters), and closing signals (merger agreement execution, press release).

**Primary recommendation:** Add four optional fields to `ChronologyBlock` using `model_copy(update=...)` in a new `annotate_blocks()` function in `skill_pipeline/source/annotate.py`. Run annotation as a post-step in `preprocess_source_deal()`, replacing the existing block list in the JSONL output. Use `EXACT_DAY_RE` from `normalize/dates.py` for date extraction (not the lighter `DATE_FRAGMENT_RE` from `evidence.py`). Compute evidence density with a single sorted-scan of evidence items by start_line. Derive temporal phase from ordinal position buckets with lexical override from closing keywords.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `re` (stdlib) | Python 3.11+ stdlib | Regex pattern matching for date/entity extraction | Already used throughout the codebase; no dependency to add |
| `pydantic` | Already installed (see pyproject.toml) | Schema definition and validation of annotated blocks | Project-wide schema standard; `PipelineModel` base class already enforces `extra="forbid"` |
| `skill_pipeline.normalize.dates` | Internal | Date parsing with full precision ladder | Avoids duplicating comprehensive regex patterns; `EXACT_DAY_RE`, `PARTIAL_MONTH_RE`, `MONTH_ONLY_RE` cover all SEC filing date formats |
| `skill_pipeline.source.evidence` | Internal | `DATE_FRAGMENT_RE`, `ACTOR_TERMS`, `PROCESS_TERMS` | Entity-hint patterns already tuned for SEC filing vocabulary |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `bisect` (stdlib) | Python 3.11+ stdlib | Binary search for efficient evidence overlap lookup | Use when evidence list is large (996 items for stec); `bisect.bisect_left` on sorted start_line list gives O(log n) lookup per block |
| `collections.defaultdict` | stdlib | Grouping evidence items by line range for overlap check | Use if building an inverted index from evidence to blocks |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Adding fields to `ChronologyBlock` | Separate `AnnotatedBlock` model | Separate model avoids changing the source schema but forces downstream consumers to load two artifacts. Adding optional fields to `ChronologyBlock` is simpler and keeps the JSONL self-contained. |
| Reusing `DATE_FRAGMENT_RE` from `evidence.py` | `EXACT_DAY_RE` + `MONTH_ONLY_RE` from `dates.py` | `DATE_FRAGMENT_RE` is deliberately permissive (used to flag paragraphs, not extract dates). For per-block annotation, use the higher-precision patterns from `dates.py` that return structured date objects. |
| LLM-based temporal phase classification | Regex + position-based heuristics | LLM classification violates the determinism requirement. Position + keyword heuristics are sufficient and fast. |

---

## Architecture Patterns

### Recommended Project Structure

```
skill_pipeline/
├── source/
│   ├── annotate.py        # NEW: annotate_blocks() function
│   ├── blocks.py          # UNCHANGED: build_chronology_blocks()
│   └── evidence.py        # UNCHANGED: scan_document_evidence()
├── pipeline_models/
│   └── source.py          # MODIFIED: ChronologyBlock gets 4 optional annotation fields
└── preprocess/
    └── source.py          # MODIFIED: calls annotate_blocks() after build_chronology_blocks()
```

### Pattern 1: Optional Fields on ChronologyBlock

**What:** Add four optional annotation fields directly to `ChronologyBlock`. Fields are `None` by default so existing code loading un-annotated JSONL files does not break.

**When to use:** When the annotation is produced in the same pipeline stage that produces the blocks, and downstream consumers benefit from a single unified artifact.

**Schema extension:**

```python
# In skill_pipeline/pipeline_models/source.py
class ChronologyBlock(PipelineModel):
    block_id: str
    document_id: str
    ordinal: int
    start_line: int
    end_line: int
    raw_text: str
    clean_text: str
    is_heading: bool
    page_break_before: bool = False
    page_break_after: bool = False
    # --- annotation fields added in Phase 1 ---
    date_mentions: list[str] = Field(default_factory=list)
    entity_hints: list[str] = Field(default_factory=list)
    evidence_density: int = 0
    temporal_phase: str | None = None
```

**Key invariant:** All four fields have defaults (`[]`, `[]`, `0`, `None`), so existing `ChronologyBlock.model_validate()` calls on JSONL files written before Phase 1 continue to work without migration. The `extra="forbid"` constraint on `PipelineModel` is not violated because fields are declared, not extra.

**Backward-compatibility test:** Load a pre-Phase-1 JSONL line (missing all four fields) and confirm `ChronologyBlock.model_validate()` succeeds — the defaults fill in. This test belongs in `tests/test_skill_preprocess_source.py`.

### Pattern 2: Post-Build Annotation Step

**What:** `annotate_blocks()` takes the output of `build_chronology_blocks()` and the output of `scan_document_evidence()` and returns annotated `ChronologyBlock` objects using `model_copy(update=...)`.

**When to use:** When annotation requires cross-referencing two already-built data structures (blocks + evidence items).

```python
# skill_pipeline/source/annotate.py

from __future__ import annotations

import bisect
import re

from skill_pipeline.normalize.dates import EXACT_DAY_RE, MONTH_ONLY_RE, PARTIAL_MONTH_RE
from skill_pipeline.pipeline_models.source import ChronologyBlock, EvidenceItem
from skill_pipeline.source.evidence import ACTOR_TERMS, PROCESS_TERMS, OUTCOME_TERMS


CLOSING_KEYWORDS = frozenset({
    "merger agreement",
    "executed",
    "execution of the merger",
    "press release",
    "announced",
    "effective time",
    "consummated",
    "stockholder approval",
    "shareholder approval",
    "termination fee",
})

BIDDING_KEYWORDS = frozenset({
    "indication of interest",
    "letter of intent",
    "non-disclosure agreement",
    "confidentiality agreement",
    "process letter",
    "bid deadline",
    "final bid",
    "best and final",
    "due diligence",
    "management presentation",
    "draft merger agreement",
    "exclusivity",
    "first round",
    "second round",
    "final round",
    "go-shop",
    "superior proposal",
})

INITIATION_KEYWORDS = frozenset({
    "strategic alternatives",
    "potential sale",
    "investment banker",
    "financial advisor",
    "special committee",
    "exploration",
    "preliminary",
    "informal approach",
    "market check",
    "board authorized",
})

_DATE_PATTERNS = [EXACT_DAY_RE, PARTIAL_MONTH_RE, MONTH_ONLY_RE]

_PARTY_RE = re.compile(r"\b(?:Party|Bidder|Company)\s+[A-Z]\b")
_BOARD_RE = re.compile(
    r"\b(?:Special Committee|Transaction Committee|Board of Directors|Independent Directors)\b",
    re.IGNORECASE,
)
_ADVISOR_RE = re.compile(
    r"\b(?:financial advisor|investment bank(?:er)?|legal advisor|outside counsel|law firm)\b",
    re.IGNORECASE,
)


def annotate_blocks(
    blocks: list[ChronologyBlock],
    evidence_items: list[EvidenceItem],
) -> list[ChronologyBlock]:
    """Return blocks with date_mentions, entity_hints, evidence_density, temporal_phase."""
    if not blocks:
        return blocks

    # Build sorted evidence index for efficient overlap queries
    ev_starts = [ev.start_line for ev in evidence_items]
    ev_ends = [ev.end_line for ev in evidence_items]

    total = len(blocks)
    # Closing phase detection: scan last 15% of blocks for closing keywords
    closing_threshold = max(1, int(total * 0.85))

    annotated: list[ChronologyBlock] = []
    for block in blocks:
        date_mentions = _extract_date_mentions(block.clean_text)
        entity_hints = _extract_entity_hints(block.clean_text)
        density = _compute_evidence_density(
            block.start_line, block.end_line, evidence_items, ev_starts, ev_ends
        )
        phase = _classify_temporal_phase(block, closing_threshold, total)
        annotated.append(
            block.model_copy(update={
                "date_mentions": date_mentions,
                "entity_hints": entity_hints,
                "evidence_density": density,
                "temporal_phase": phase,
            })
        )
    return annotated


def _extract_date_mentions(text: str) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []
    for pattern in _DATE_PATTERNS:
        for match in pattern.finditer(text):
            val = match.group(0).strip()
            if val not in seen:
                seen.add(val)
                results.append(val)
    return results


def _extract_entity_hints(text: str) -> list[str]:
    hints: list[str] = []
    for match in _PARTY_RE.finditer(text):
        hints.append(match.group(0))
    for match in _BOARD_RE.finditer(text):
        hints.append(match.group(0))
    for match in _ADVISOR_RE.finditer(text):
        hints.append(match.group(0))
    # Deduplicate while preserving first-occurrence order
    seen: set[str] = set()
    deduped: list[str] = []
    for h in hints:
        normalized = h.lower()
        if normalized not in seen:
            seen.add(normalized)
            deduped.append(h)
    return deduped


def _compute_evidence_density(
    block_start: int,
    block_end: int,
    evidence_items: list[EvidenceItem],
    ev_starts: list[int],
    ev_ends: list[int],
) -> int:
    # Count evidence items whose line range overlaps [block_start, block_end]
    # An overlap exists when ev_start <= block_end AND ev_end >= block_start
    lo = bisect.bisect_left(ev_starts, block_start)
    # Walk backward to catch items that start before block_start but end inside it
    lo = max(0, lo - 1)
    count = 0
    for i in range(lo, len(evidence_items)):
        if ev_starts[i] > block_end:
            break
        if ev_ends[i] >= block_start:
            count += 1
    return count
```

### Pattern 3: Temporal Phase Classification

**What:** Three phases derived from content keywords and ordinal position. Keyword signals override position heuristics so an explicit closing signal (e.g., "executed the merger agreement") is always labeled `closing` regardless of position.

**Phase definitions:**

| Phase | Signal | Rationale |
|-------|--------|-----------|
| `initiation` | Ordinal <= 33% of total blocks, or INITIATION_KEYWORDS match | Deal setup: board authorizations, advisor engagement, preliminary contacts |
| `bidding` | Ordinal in 33–85% range, or BIDDING_KEYWORDS match | Active process: NDAs, IOIs, process letters, bid rounds |
| `closing` | Ordinal >= 85% of total blocks, or CLOSING_KEYWORDS match | Definitive agreement and post-execution sections |

**Important note on stec data:** Block B103 onward in stec is the fairness opinion / board reasons section, not deal process narrative. The temporal phase label on these blocks will be `closing`, which is correct — these blocks describe the rationale after execution and the LLM should treat them as supporting context rather than new event sources.

```python
def _classify_temporal_phase(
    block: ChronologyBlock,
    closing_threshold: int,
    total: int,
) -> str:
    lowered = block.clean_text.lower()

    # Keyword overrides always win over position
    if any(kw in lowered for kw in CLOSING_KEYWORDS):
        return "closing"
    if any(kw in lowered for kw in BIDDING_KEYWORDS):
        return "bidding"

    # Position fallback
    initiation_threshold = max(1, int(total * 0.33))
    if block.ordinal <= initiation_threshold:
        return "initiation"
    if block.ordinal >= closing_threshold:
        return "closing"
    return "bidding"
```

### Anti-Patterns to Avoid

- **Calling `parse_resolved_date()` for per-block annotation:** That function returns a `ResolvedDate` object (with anchor resolution, relative-date logic, etc.). For block annotation, only the raw string match is needed — call the pattern directly with `.finditer()`. `parse_resolved_date()` adds overhead and requires an `anchor_date` for relative dates that is unavailable at this stage.

- **Sorting evidence items by start_line inside `annotate_blocks()`:** The evidence list from `scan_document_evidence()` is produced by scanning paragraphs in order, so it is already ordered by start_line. Calling `sorted()` adds O(n log n) work unnecessarily. Verify ordering with an assertion if uncertain, but do not re-sort.

- **Using `set()` for entity hint deduplication with case variants:** "Special Committee" and "special committee" are the same entity. Normalize to lowercase before adding to the seen set (keep the original-case form in the output list).

- **Raising exceptions when annotation fields produce empty results:** An empty `date_mentions` list or `evidence_density=0` is a valid outcome for heading blocks (e.g., page number blocks like `B004: "23"`). Annotation should never fail; it produces empty/zero annotations for content-free blocks.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Date extraction regex | Custom month/day/year pattern | `EXACT_DAY_RE`, `PARTIAL_MONTH_RE`, `MONTH_ONLY_RE` from `skill_pipeline/normalize/dates.py` | These patterns already handle edge cases: abbreviated months, "early/mid/late Month YYYY", ranges, partial dates. They are tested and tuned for SEC filing text. |
| Entity pattern matching | Bespoke NER or LLM entity extraction | Regex patterns in `skill_pipeline/source/evidence.py` (`ACTOR_TERMS`, `_PARTY_RE`, `_BOARD_RE`) | These patterns are already calibrated to M&A filing vocabulary. Extending them is lower risk than building new patterns. |
| Interval overlap computation | Custom loop over all evidence items | `bisect.bisect_left` on pre-sorted start_line list | Standard O(log n) lookup for sorted sequences. The naive O(n*m) loop (n=234 blocks, m=996 evidence items = 233k comparisons) is acceptable but unnecessary. |
| Schema versioning for new fields | Version flag in block metadata | Pydantic `default_factory` on new fields | Pydantic's default mechanism gives backward compatibility for free. Adding `date_mentions: list[str] = Field(default_factory=list)` means old JSONL lines validate without the field. |

**Key insight:** The codebase's text patterns were written specifically for M&A proxy filing language. Do not replace them with generic NLP tools (spaCy, NLTK) — they would introduce a new dependency with lower domain precision and violate the "no fallback, fail fast" principle.

---

## Common Pitfalls

### Pitfall 1: `extra="forbid"` blocks new schema fields
**What goes wrong:** Adding fields to `ChronologyBlock` without declaring them in the model causes `model_validate()` to raise `ValidationError: extra inputs not permitted` when loading new-format JSONL files with old schema expectations.
**Why it happens:** `PipelineModel` configures `extra="forbid"` globally. Any JSON key not in the field declarations is rejected.
**How to avoid:** Declare all four new fields explicitly in `ChronologyBlock` with defaults. Never add fields to the JSON output without corresponding declarations. Do NOT change `extra="forbid"` to `extra="allow"` — that would silently accept schema drift throughout the pipeline.
**Warning signs:** `ValidationError` mentioning "extra inputs" during `model_validate_json()` in tests or downstream stages.

### Pitfall 2: Evidence items span multiple blocks, inflating density counts
**What goes wrong:** An evidence item covering lines L1282–L1285 (block B008) also overlaps page-number block B009 (line L1287) if the overlap check is strictly `ev_end >= block_start`.
**Why it happens:** Page-number blocks (ordinals like "23", "24") have single-line ranges that may fall inside the gap between two evidence items, creating apparent overlaps.
**How to avoid:** The overlap logic `ev_start <= block_end AND ev_end >= block_start` is mathematically correct. The "inflation" in page number blocks is real but acceptable — density=1 on a page number block is a harmless artifact that the LLM prompt will ignore since the block content is trivial. Do not add special-case logic for page number blocks.
**Warning signs:** Suspiciously high density on 1-line blocks. Accept this as expected behavior.

### Pitfall 3: `MONTH_ONLY_RE` matching non-date "May" (modal verb)
**What goes wrong:** The sentence "sTec may pursue alternatives" triggers `MONTH_ONLY_RE` and returns "may" as a date mention because the pattern matches `\b(may)\s+(\d{4})\b` — but only if followed by a 4-digit year. The standalone word "may" without a year does not match.
**Why it happens:** `MONTH_ONLY_RE` requires `\b(month)\s+(\d{4})\b` — the year is mandatory. The false-positive risk is low but not zero (e.g., "may 2013 be the year...").
**How to avoid:** Apply `EXACT_DAY_RE` first, then `PARTIAL_MONTH_RE`, then `MONTH_ONLY_RE`, and deduplicate by match span to avoid re-tagging the same text. The scan order (most specific to least specific) limits false positives.
**Warning signs:** `date_mentions` containing standalone "may" without a year. Monitor during testing on stec data.

### Pitfall 4: Temporal phase "closing" applied too early due to keyword matches in background/preamble
**What goes wrong:** Block B002 in stec mentions "a sale of the company" which could trigger on weak closing keywords. Early background blocks get labeled `closing`.
**Why it happens:** Keywords are extracted from clean_text without considering that background blocks often preview the entire deal history.
**How to avoid:** The keyword override only fires on `CLOSING_KEYWORDS` which are specific post-execution terms ("executed", "merger agreement", "press release", "effective time"). The word "sale" is intentionally not in CLOSING_KEYWORDS. Keep the closing keyword set narrow and precise.
**Warning signs:** `temporal_phase="closing"` appearing on blocks B001–B020. If this happens, audit CLOSING_KEYWORDS for overly broad entries.

### Pitfall 5: Annotation running before evidence items exist
**What goes wrong:** If `annotate_blocks()` is called with an empty `evidence_items` list because the evidence scan failed silently, all blocks get `evidence_density=0`, producing misleading low-signal annotations.
**Why it happens:** The `preprocess_source_deal()` function catches exceptions and re-raises, but if `scan_document_evidence()` returns an empty list (rather than raising), annotation proceeds silently with wrong data.
**How to avoid:** In `preprocess_source_deal()`, after `scan_document_evidence()`, assert `len(evidence_items) > 0` before calling `annotate_blocks()`. This is consistent with the fail-fast principle: zero evidence items means the scan failed, and the pipeline should abort rather than write misleading annotations.
**Warning signs:** All blocks showing `evidence_density: 0` in the output JSONL.

---

## Code Examples

Verified patterns from codebase inspection:

### Using model_copy to add annotation fields without mutating
```python
# Source: skill_pipeline/pipeline_models/common.py (PipelineModel pattern)
# model_copy(update=...) is the Pydantic v2 non-mutating update pattern
annotated = block.model_copy(update={
    "date_mentions": ["February 13, 2013"],
    "entity_hints": ["Special Committee", "Company B"],
    "evidence_density": 3,
    "temporal_phase": "initiation",
})
```

### Integrating annotate_blocks into preprocess_source_deal
```python
# Source: skill_pipeline/preprocess/source.py (integration point)
blocks = build_chronology_blocks(lines, selection=selection)
if not blocks:
    raise ValueError(...)

evidence_items = _dedupe_evidence_items(
    scan_document_evidence(lines, document_id=..., ...)
)

# Phase 1: annotate blocks with deterministic metadata
from skill_pipeline.source.annotate import annotate_blocks
blocks = annotate_blocks(blocks, evidence_items)
```

### Evidence density overlap computation with bisect
```python
# Efficient interval overlap: find evidence items overlapping [block_start, block_end]
import bisect

ev_starts = [ev.start_line for ev in evidence_items]  # already sorted
lo = bisect.bisect_left(ev_starts, block_start)
lo = max(0, lo - 1)  # step back to catch items starting before block_start
count = 0
for i in range(lo, len(evidence_items)):
    if ev_starts[i] > block_end:
        break
    if evidence_items[i].end_line >= block_start:
        count += 1
```

### Writing annotated blocks to JSONL (no change needed in preprocess/source.py)
```python
# Source: skill_pipeline/preprocess/source.py (_atomic_write_jsonl pattern)
# The existing write call works unchanged because model_dump() includes all fields
_atomic_write_jsonl(
    source_dir / "chronology_blocks.jsonl",
    [block.model_dump(mode="json") for block in blocks],  # blocks is now annotated
)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|-----------------|--------------|--------|
| Flat block metadata (block_id, lines, text, is_heading only) | Block metadata + date/entity/density/phase annotations | Phase 1 (this phase) | Downstream prompt composer can select high-density blocks, annotate XML tags per evidence density, wrap temporal phase groups |
| Evidence items as passive appendix in prompt | Evidence density surfaced in block metadata for selective inclusion | Phase 1 + Phase 2 | LLM prompt can show `<high_evidence_density>` on relevant blocks without listing all 996 items |
| No temporal structure in chronology | Phase-tagged blocks for XML wrapping | Phase 1 + Phase 2 | Enables `<process_phase name="bidding">` wrapping recommended in CONTEXT_AND_ATTENTION.md |

**Deprecated/outdated:**
- Raw block metadata without annotations: still valid artifact format (backward-compatible), but Phase 2+ prompt code should assume annotated format is present.

---

## Open Questions

1. **Should annotation run on heading-only blocks?**
   - What we know: Heading blocks (e.g., B001 "Background of the Merger", B009 "24") have `is_heading=True` and minimal text. The annotation logic will produce empty `date_mentions`, empty `entity_hints`, `evidence_density=0`, and a position-derived `temporal_phase`.
   - What's unclear: Whether the prompt composition engine (Phase 2) will skip heading blocks entirely or use their phase label for grouping.
   - Recommendation: Annotate all blocks including headings. The downstream consumer can filter `is_heading=True` blocks. Do not add special-case logic in `annotate_blocks()`.

2. **What entity patterns are missing from the current `_extract_actor_hint()` in evidence.py?**
   - What we know: The current patterns capture "Party A/B/C", "Board", "Special Committee", "Goldman Sachs"-style names with known suffix words.
   - What's unclear: Whether named company patterns (e.g., "sTec", "WDC") from the seed should be added dynamically. These are deal-specific and not hardcoded.
   - Recommendation: For Phase 1, do not add deal-specific company names. Use the generic patterns that work across all 9 deals. Deal-specific enrichment (e.g., passing target_name and acquirer to `annotate_blocks()`) can be added in a follow-up if Phase 2 prompt testing shows entity hints are too sparse.

3. **How should `evidence_density` be interpreted by the prompt composer?**
   - What we know: The research recommends marking blocks as `<high_evidence_density>` in the prompt XML. The threshold for "high" is undefined.
   - What's unclear: Whether density=1 or density>=2 is the right threshold for the high-density marker.
   - Recommendation: Compute the raw integer count in Phase 1; let Phase 2 decide the threshold. Do not bake thresholds into the annotation schema. The prompt composer can use `evidence_density >= 2` or any other threshold without changing the source artifact.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 1 is purely Python code changes with no external tool dependencies. All required libraries (`re`, `bisect`, `pydantic`) are Python stdlib or already installed in the project environment.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pytest.ini` (root, `testpaths = tests`) |
| Quick run command | `pytest -q tests/test_skill_preprocess_source.py` |
| Full suite command | `pytest -q` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| R5 | `annotate_blocks()` adds `date_mentions` list to each block | unit | `pytest -q tests/test_skill_annotate.py::test_date_mentions_extracted -x` | Wave 0 |
| R5 | `annotate_blocks()` adds `entity_hints` list to each block | unit | `pytest -q tests/test_skill_annotate.py::test_entity_hints_extracted -x` | Wave 0 |
| R5 | `annotate_blocks()` adds `evidence_density` int to each block | unit | `pytest -q tests/test_skill_annotate.py::test_evidence_density_computed -x` | Wave 0 |
| R5 | `annotate_blocks()` adds `temporal_phase` string to each block | unit | `pytest -q tests/test_skill_annotate.py::test_temporal_phase_classified -x` | Wave 0 |
| R5 | Annotated blocks load from JSONL without ValidationError | unit | `pytest -q tests/test_skill_preprocess_source.py::test_annotated_block_roundtrip -x` | Wave 0 |
| R5 | Pre-Phase-1 (unannotated) JSONL still validates via defaults | unit | `pytest -q tests/test_skill_preprocess_source.py::test_unannotated_block_backward_compat -x` | Wave 0 |
| R5 | `preprocess_source_deal()` output includes annotated blocks | integration | `pytest -q tests/test_skill_preprocess_source.py -x` | Exists (partial) |

### Sampling Rate

- **Per task commit:** `pytest -q tests/test_skill_annotate.py tests/test_skill_preprocess_source.py`
- **Per wave merge:** `pytest -q`
- **Phase gate:** Full suite green before moving to Phase 2

### Wave 0 Gaps

- [ ] `tests/test_skill_annotate.py` — covers all R5 annotation behaviors (does not exist yet)
- [ ] Backward-compatibility test in `tests/test_skill_preprocess_source.py` for pre-Phase-1 JSONL lines

*(Existing `tests/test_skill_preprocess_source.py` covers `preprocess_source_deal()` integration but does not test annotation fields.)*

---

## Sources

### Primary (HIGH confidence)

- `skill_pipeline/pipeline_models/source.py` — `ChronologyBlock` schema, `EvidenceItem` schema, field names confirmed by direct code read
- `skill_pipeline/pipeline_models/common.py` — `PipelineModel` with `extra="forbid"` confirmed, `model_config = ConfigDict(extra="forbid")`
- `skill_pipeline/normalize/dates.py` — `EXACT_DAY_RE`, `PARTIAL_MONTH_RE`, `MONTH_ONLY_RE` patterns confirmed, full regex coverage verified
- `skill_pipeline/source/evidence.py` — `DATE_FRAGMENT_RE`, `ACTOR_TERMS`, `PROCESS_TERMS`, `_extract_actor_hint()` patterns confirmed
- `skill_pipeline/source/blocks.py` — `build_chronology_blocks()` output structure confirmed
- `skill_pipeline/preprocess/source.py` — integration point confirmed; `annotate_blocks()` call goes after `build_chronology_blocks()` and `scan_document_evidence()`
- `data/deals/stec/source/chronology_blocks.jsonl` — 234 blocks; B001–B102 are deal-process narrative; B103–B234 are fairness opinion/board reasons
- `data/deals/stec/source/evidence_items.jsonl` — 996 evidence items; ev_starts verified as in-order by paragraph scan
- `.planning/research/CONTEXT_AND_ATTENTION.md` — Temporal phase XML tagging recommendation (section 8), evidence density attention anchors (section 14)

### Secondary (MEDIUM confidence)

- Python `bisect` module documentation — O(log n) sorted-list search confirmed as standard for interval lookup
- Pydantic v2 `model_copy(update=...)` documentation — non-mutating update pattern for `BaseModel` instances; this is the v2 replacement for `.copy(update=...)`

### Tertiary (LOW confidence)

- None. All findings derived from direct codebase inspection and prior project research documents.

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — all libraries are confirmed present in the codebase with verified import paths
- Architecture: HIGH — schema extension pattern verified against `PipelineModel` constraints; integration point in `preprocess_source_deal()` confirmed
- Date extraction patterns: HIGH — `EXACT_DAY_RE` etc. are directly readable from source and tested in the existing test suite
- Evidence density algorithm: HIGH — bisect-based interval overlap is stdlib, deterministic, and correct
- Temporal phase heuristics: MEDIUM — the keyword sets and position thresholds are calibrated against stec data only; may need tuning for other deals
- Entity hint patterns: MEDIUM — existing patterns capture the main M&A actors but may miss deal-specific named parties

**Research date:** 2026-03-27
**Valid until:** 2026-09-27 (6 months; stable — all findings from internal codebase, not external APIs)
