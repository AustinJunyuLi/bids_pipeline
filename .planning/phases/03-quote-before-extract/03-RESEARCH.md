# Phase 3: Quote-Before-Extract - Research

**Researched:** 2026-03-28
**Domain:** LLM extraction response format, schema migration, deterministic pipeline stage updates
**Confidence:** HIGH

## Summary

Phase 3 replaces the `evidence_refs` (block_id + anchor_text) extraction format with a quote-first format where the LLM emits a top-level `quotes` array of verbatim filing passages before emitting structured actors/events that reference those quotes by `quote_id`. This is a schema-level change that propagates through three layers: (1) prompt composition task instructions that tell the LLM to produce the new format, (2) Pydantic models and the extract artifact loader that define and detect the new format, and (3) canonicalize and verify stages that consume quotes instead of evidence_refs for span resolution and quote validation.

The existing codebase is well-prepared for this change. `resolve_text_span()` in provenance.py and `find_anchor_in_segment()` in normalize/quotes.py are directly reusable -- the new code rewires how they are called, not what they do. Canonicalize already follows a pattern of iterating references and resolving each to a span; the same pattern applies to quotes. Verify already matches anchor text against filing text; the same matching applies to quote text. The current stec artifacts are already in canonical form (evidence_span_ids), so stec must be re-extracted through the new quote-first protocol before Phase 3 exit criteria can be validated.

**Primary recommendation:** Implement this as a clean format replacement with no dual-path support. Define new Pydantic models (`QuoteEntry`, updated `RawSkillActorRecord` and `RawSkillEventRecord` using `quote_ids`), update the extract artifact loader to detect the new format, rewrite canonicalize to map quotes to spans, rewrite verify to validate quotes against filing text, and update task instructions in compose-prompts to communicate the quote-first protocol.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** The LLM produces a single JSON response with a top-level `quotes` array followed by the structured `actors` or `events` array. Quotes come first in the JSON, structured data second. Not two sequential LLM calls.
- **D-02:** Each quote entry has `quote_id`, `block_id`, and `text` (verbatim filing passage). Quote IDs are stable identifiers (e.g., `Q001`, `Q002`) assigned by the LLM during extraction.
- **D-03:** Actors and events reference `quote_ids` (list of strings) instead of carrying inline `evidence_refs` with `anchor_text`. The `evidence_refs` field and its `anchor_text` subfield are replaced, not augmented.
- **D-04:** New format only. No dual-path support in canonicalize or verify. Old `evidence_refs`-based code paths are removed.
- **D-05:** Existing stec and medivation extraction artifacts become stale. Both deals must be re-extracted through the new quote-first protocol before Phase 3 exit criteria can be validated.
- **D-06:** The `EvidenceRef` model and related legacy helpers can be cleaned out of `models.py` and downstream stages once the new format is wired.
- **D-07:** Canonicalize maps quotes directly to spans: `quote.text` + `quote.block_id` -> `resolve_text_span()` -> `spans.json`. Actors/events `quote_ids` are resolved to `evidence_span_ids` through the quote-to-span mapping.
- **D-08:** Verify runs two validation rounds: Round 1 checks each `quote.text` against the actual filing text (EXACT/NORMALIZED matching). Round 2 checks that every actor/event references valid `quote_ids` that exist in the quotes array.
- **D-09:** The quote-first format should produce higher EXACT match rates in verify because the LLM is structurally forced to commit to verbatim text before building structured data on top of it.

### Claude's Discretion
- Exact JSON schema field names for the quote-first response (as long as quotes precede structured data and use quote_ids for linkage)
- Whether to keep `evidence_refs` as a deprecated alias during the transition or remove immediately
- Internal refactoring approach for canonicalize (incremental edits vs clean rewrite of span resolution)
- How the prompt assets (`task_instructions` text in compose-prompts) communicate the quote-first requirement to the LLM

### Deferred Ideas (OUT OF SCOPE)
- Chunk-budget overhead accounting (CRITICAL-1 from GPT audit) -- deferred to Phase 5 complexity routing
- Complexity-based routing (PROMPT-06) -- Phase 5
- Few-shot expansion (INFRA-07) -- Phase 5
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PROMPT-05 | Quote-before-extract protocol forces the LLM to cite verbatim passages before emitting structured events | New Pydantic models (QuoteEntry, updated actor/event records), updated task instructions in compose-prompts, rewritten canonicalize quote-to-span mapping, rewritten verify quote validation, updated extract artifact loader |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

The following CLAUDE.md directives constrain this phase:

- **Filing text is the only factual source of truth** -- quotes must be verbatim from filing text
- **Fail fast on missing files, schema drift, contradictory state, invalid assumptions** -- no silent fallbacks when encountering old-format artifacts
- **`skill_pipeline` is deterministic; LLM calls remain in `.claude/skills/`** -- task instruction changes live in prompt_assets and compose_prompts, not new LLM wrappers
- **Treat `raw/`, `data/deals/<slug>/source/`, and `data/skill/<slug>/` as generated artifacts** -- extraction artifacts will be regenerated
- **`verify` only treats `EXACT` and `NORMALIZED` quote matches as passing. `FUZZY` does not pass** -- this invariant is preserved in the new quote validation
- **Canonical extract loading requires `spans.json`; missing sidecars are an error** -- unchanged
- **`check`, `verify`, and `coverage` are blocker gates before `enrich-core`** -- unchanged
- **Target Python 3.11+ with explicit types on public functions, Pydantic-first schema style, snake_case for Python names and JSON keys** -- new models follow this
- **Add focused regression tests for behavior changes** -- tests needed for new format detection, quote-to-span mapping, quote validation
- **When skill docs change, update `.claude/skills/` first, then sync mirrors** -- extract-deal SKILL.md must be updated for quote-first format
- **`actors_raw.json` and `events_raw.json` are the live filenames** (not `actors.json` or `events.json`)

## Architecture Patterns

### Schema Change Topology

The quote-before-extract format change propagates through these layers:

```
Layer 1: Prompt Instructions (compose-prompts task_instructions + prompt_assets)
  |
  v
Layer 2: LLM Response Format (SKILL.md contract, extraction output schema)
  |
  v
Layer 3: Pydantic Models (models.py: QuoteEntry, updated Raw*Record, artifact schemas)
  |
  v
Layer 4: Extract Artifact Loader (extract_artifacts.py: detect quote-first format)
  |
  v
Layer 5: Canonicalize (canonicalize.py: quote -> resolve_text_span() -> spans.json)
  |
  v
Layer 6: Verify (verify.py: quote.text validation + quote_id referential integrity)
  |
  v
Layer 7: Downstream consumers (check.py reads canonical, unchanged)
```

### Recommended Implementation Order

```
1. Models (QuoteEntry, updated Raw records)     -- foundation for everything
2. Extract artifact loader (format detection)    -- needed by canonicalize/verify
3. Canonicalize (quote-to-span mapping)          -- consumes new models
4. Verify (quote validation)                     -- consumes new models
5. Prompt assets + compose-prompts               -- task instruction update
6. SKILL.md + skill mirrors                      -- extraction contract update
7. Re-extraction (stec, medivation)              -- validation
```

### Current vs New Response Format

**Current (evidence_refs):**
```json
{
  "actors": [
    {
      "actor_id": "bidder_thoma_bravo",
      "evidence_refs": [
        {"block_id": "B042", "evidence_id": null, "anchor_text": "representatives of Thoma Bravo informally approached"}
      ]
    }
  ]
}
```

**New (quote-first):**
```json
{
  "quotes": [
    {"quote_id": "Q001", "block_id": "B042", "text": "representatives of Thoma Bravo informally approached"}
  ],
  "actors": [
    {
      "actor_id": "bidder_thoma_bravo",
      "quote_ids": ["Q001"]
    }
  ]
}
```

### New Pydantic Models

```python
class QuoteEntry(SkillModel):
    quote_id: str
    block_id: str
    text: str
```

The `RawSkillActorRecord` and `RawSkillEventRecord` models replace `evidence_refs: list[EvidenceRef]` with `quote_ids: list[str]`.

The `RawCountAssertion` model replaces `evidence_refs: list[EvidenceRef]` with `quote_ids: list[str]`.

Top-level artifact models add `quotes: list[QuoteEntry]`:

```python
class RawSkillActorsArtifact(SkillModel):
    quotes: list[QuoteEntry]
    actors: list[RawSkillActorRecord]
    count_assertions: list[RawCountAssertion] = Field(default_factory=list)
    unresolved_mentions: list[str] = Field(default_factory=list)

class RawSkillEventsArtifact(SkillModel):
    quotes: list[QuoteEntry]
    events: list[RawSkillEventRecord]
    exclusions: list[SkillExclusionRecord] = Field(default_factory=list)
    coverage_notes: list[str] = Field(default_factory=list)
```

### Canonicalize Quote-to-Span Mapping

The new canonicalize flow replaces `_resolve_ref_to_span_id()` with a quote-centric resolution:

1. Build `quote_id -> QuoteEntry` index from the artifact's `quotes` array
2. For each quote: look up the block by `quote.block_id` in `blocks_by_id`
3. Call `resolve_text_span(raw_lines, start_line=block.start_line, end_line=block.end_line, anchor_text=quote.text, ...)` -- same function, different caller
4. Build `quote_id -> span_id` mapping
5. For each actor/event: map `quote_ids` to `evidence_span_ids` through the quote-to-span mapping

This is structurally simpler than the current code because quotes always have a `block_id` (no evidence_id-only path), eliminating the evidence_id lookup branch.

### Verify Quote Validation

Verify's new flow has two distinct check types:

**Round 1 -- Quote Text Validation:**
For each quote in the `quotes` array:
1. Look up the block by `quote.block_id`
2. Get the raw filing lines for the block's document
3. Call `_resolve_quote_match(raw_segment, quote.text, raw_lines, start_line, end_line)`
4. EXACT and NORMALIZED pass; FUZZY and UNRESOLVED are errors

**Round 2 -- Quote ID Referential Integrity:**
For each actor/event:
1. Check that every `quote_id` in the record exists in the artifact's `quotes` array
2. Missing quote_ids are errors

This replaces the current pattern of iterating `evidence_refs` per actor/event.

### Extract Artifact Loader Update

`extract_artifacts.py` currently detects canonical vs legacy format by checking for `evidence_span_ids` in the payload. With the new format:

- **Quote-first format:** payload has a top-level `quotes` key and records have `quote_ids` (not `evidence_refs`)
- **Canonical format:** payload records have `evidence_span_ids` (post-canonicalize)
- **Legacy format:** payload records have `evidence_refs` -- this is the format being removed

Per D-04, the loader should fail fast on legacy format (no dual-path). Detection logic:

```python
def _detect_format(payload: dict) -> Literal["quote_first", "canonical"]:
    if "quotes" in payload:
        return "quote_first"
    # Check for canonical evidence_span_ids
    for key in ("actors", "events"):
        for item in payload.get(key, []):
            if "evidence_span_ids" in item:
                return "canonical"
    raise ValueError("Unrecognized extract artifact format (legacy evidence_refs no longer supported)")
```

The `LoadedExtractArtifacts` dataclass needs a third mode or the quote-first artifacts need to be loadable through a clear path that canonicalize consumes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Text span resolution from quote text + block_id | Custom string matching / line offset calculation | `provenance.resolve_text_span()` | Already handles EXACT/NORMALIZED/FUZZY cascading, line-to-char offset conversion, and span expansion |
| Quote text matching against filing | Custom substring search | `normalize.quotes.find_anchor_in_segment()` | Already handles Unicode normalization, smart quotes, parenthetical stripping, and alnum compaction |
| Chronology block lookup by ID | Custom dict building | Existing `blocks_by_id` pattern used in both canonicalize.py and verify.py | Well-tested, with duplicate ID detection |
| Document line loading | Custom file reader | Existing `_load_document_lines()` in canonicalize.py and verify.py | Handles encoding, directory validation, and file-keying by document_id |

**Key insight:** The quote-first format change is primarily a rewiring of how existing functions are called, not new algorithmic work. `resolve_text_span()` and `find_anchor_in_segment()` are the reusable core.

## Common Pitfalls

### Pitfall 1: Quotes Without Valid Block IDs
**What goes wrong:** The LLM assigns a `block_id` that does not exist in the chronology blocks, causing canonicalize to fail.
**Why it happens:** The LLM may confuse block IDs, especially in chunked extraction where overlap blocks are visible.
**How to avoid:** Canonicalize and verify should fail fast with a clear error when a quote references an unknown block_id. Task instructions should emphasize that block_ids must match the supplied chronology blocks exactly.
**Warning signs:** `KeyError` on `blocks_by_id[quote.block_id]` in canonicalize.

### Pitfall 2: Quote Text Not Found in Block
**What goes wrong:** The quote `text` field does not match any substring in the referenced block's filing text, even after normalization.
**Why it happens:** The LLM paraphrases instead of copying verbatim, or copies from a different block than the one it tagged.
**How to avoid:** Verify catches this as a quote_verification error. The structural forcing of quotes-first is specifically designed to reduce this -- the LLM commits to verbatim text before building structured data.
**Warning signs:** High UNRESOLVED or FUZZY match rates in verify.

### Pitfall 3: Orphaned Quotes (No Actor/Event References Them)
**What goes wrong:** The quotes array contains entries that no actor or event references, wasting span resolution work.
**Why it happens:** LLM extracts a quote during reading but does not use it in structured output.
**How to avoid:** Canonicalize should log orphaned quotes but not fail on them (they are harmless noise). Verify can flag them as warnings.
**Warning signs:** `quote_id` present in `quotes` array but absent from all actor/event `quote_ids` fields.

### Pitfall 4: Duplicate Quote IDs
**What goes wrong:** Two quotes share the same `quote_id`, causing ambiguous resolution in canonicalize.
**Why it happens:** LLM generates non-unique IDs or reuses an ID across chunks.
**How to avoid:** Pydantic model validation or canonicalize pre-check should fail fast on duplicate quote_ids within an artifact.
**Warning signs:** Multiple entries in `quotes` with the same `quote_id`.

### Pitfall 5: Existing Test Fixtures Use evidence_refs Format
**What goes wrong:** After removing evidence_refs support, all existing tests that build legacy fixtures break.
**Why it happens:** Every test in test_skill_canonicalize.py and test_skill_verify.py uses `evidence_refs` in its fixture data.
**How to avoid:** Update all test fixtures to use the quote-first format (`quotes` + `quote_ids`). This is a significant amount of test fixture rewriting but is mandatory for D-04 (no dual-path).
**Warning signs:** Mass test failures after model changes.

### Pitfall 6: Count Assertions Also Need Quote IDs
**What goes wrong:** `RawCountAssertion` still has `evidence_refs` after actor/event records are updated, causing schema validation failures.
**Why it happens:** Count assertions are a secondary data structure that is easy to overlook.
**How to avoid:** Update `RawCountAssertion` to use `quote_ids: list[str]` instead of `evidence_refs: list[EvidenceRef]`. Update canonicalize to resolve count assertion quote_ids through the same quote-to-span mapping.
**Warning signs:** Pydantic validation errors on count_assertions with `evidence_refs` field.

## Code Examples

### Quote-to-Span Resolution in Canonicalize

```python
# Source: existing provenance.py resolve_text_span() -- reused with new caller
def _resolve_quotes_to_spans(
    quotes: list[QuoteEntry],
    *,
    blocks_by_id: dict[str, ChronologyBlock],
    document_lines: dict[str, list[str]],
    document_meta: dict[str, dict],
) -> tuple[list[dict], dict[str, str]]:
    """Resolve each quote to a SpanRecord, return spans and quote_id->span_id map."""
    spans: list[dict] = []
    quote_to_span: dict[str, str] = {}

    for quote in quotes:
        block = blocks_by_id.get(quote.block_id)
        if block is None:
            raise ValueError(f"Quote {quote.quote_id!r} references unknown block_id {quote.block_id!r}")

        meta = document_meta.get(block.document_id, {})
        raw_lines = document_lines.get(block.document_id)
        if raw_lines is None:
            raise FileNotFoundError(f"Missing filing text for document_id {block.document_id!r}")

        span_id = f"span_{len(spans) + 1:04d}"
        span = resolve_text_span(
            raw_lines,
            start_line=block.start_line,
            end_line=block.end_line,
            block_ids=[block.block_id],
            evidence_ids=[],
            anchor_text=quote.text,
            document_id=block.document_id,
            accession_number=meta.get("accession_number"),
            filing_type=meta.get("filing_type", "UNKNOWN"),
            span_id=span_id,
        )
        spans.append(span.model_dump(mode="json"))
        quote_to_span[quote.quote_id] = span_id

    return spans, quote_to_span
```

### Quote Validation in Verify

```python
# Source: existing verify.py _resolve_quote_match() -- reused with new caller
def _check_quote_validation(
    quotes: list[QuoteEntry],
    blocks: list[ChronologyBlock],
    document_lines: dict[str, list[str]],
) -> tuple[list[VerificationFinding], int]:
    """Validate each quote.text against the filing text in the referenced block."""
    findings: list[VerificationFinding] = []
    total_checks = 0
    blocks_by_id = {b.block_id: b for b in blocks}

    for quote in quotes:
        total_checks += 1
        block = blocks_by_id.get(quote.block_id)
        if block is None:
            findings.append(VerificationFinding(
                check_type="quote_verification",
                severity="error",
                repairability="repairable",
                description=f"Quote {quote.quote_id!r} references unknown block_id {quote.block_id!r}",
            ))
            continue

        raw_lines = document_lines.get(block.document_id, [])
        if not raw_lines:
            findings.append(VerificationFinding(
                check_type="quote_verification",
                severity="error",
                repairability="repairable",
                description=f"No document lines for quote {quote.quote_id!r}",
            ))
            continue

        segment_lines = raw_lines[block.start_line - 1 : block.end_line]
        raw_segment = "\n".join(segment_lines)
        match_type = _resolve_quote_match(
            raw_segment, quote.text, raw_lines, block.start_line, block.end_line
        )
        if match_type in {QuoteMatchType.FUZZY, QuoteMatchType.UNRESOLVED}:
            findings.append(VerificationFinding(
                check_type="quote_verification",
                severity="error",
                repairability="repairable",
                description=f"Quote {quote.quote_id!r} text not found at EXACT/NORMALIZED level in block {quote.block_id}",
                block_ids=[quote.block_id],
                anchor_text=quote.text,
            ))

    return findings, total_checks
```

### Updated Task Instructions for Compose-Prompts

```python
# Actor extraction task instructions
actor_task_instructions = (
    "IMPORTANT: You MUST follow the quote-before-extract protocol.\n"
    "\n"
    "Step 1 - QUOTE: Read the chronology blocks above. For every passage that "
    "identifies an actor, copy the exact verbatim text into the quotes array. "
    "Each quote needs a unique quote_id (Q001, Q002, ...), the block_id it "
    "comes from, and the verbatim text.\n"
    "\n"
    "Step 2 - EXTRACT: Build the actors array. Each actor references quote_ids "
    "from Step 1 instead of inline evidence. Do not include anchor_text or "
    "evidence_refs.\n"
    "\n"
    "Return a single JSON object with: quotes, actors, count_assertions, "
    "unresolved_mentions. The quotes array MUST appear first."
)

# Event extraction task instructions
event_task_instructions = (
    "IMPORTANT: You MUST follow the quote-before-extract protocol.\n"
    "\n"
    "Step 1 - QUOTE: Read the chronology blocks above. For every passage that "
    "describes an M&A event, copy the exact verbatim text into the quotes array. "
    "Each quote needs a unique quote_id (Q001, Q002, ...), the block_id it "
    "comes from, and the verbatim text.\n"
    "\n"
    "Step 2 - EXTRACT: Build the events array using the locked actor roster. "
    "Each event references quote_ids from Step 1 instead of inline evidence. "
    "Do not include anchor_text or evidence_refs.\n"
    "\n"
    "Return a single JSON object with: quotes, events, exclusions, "
    "coverage_notes. The quotes array MUST appear first."
)
```

## Files to Modify

### Python Source (skill_pipeline/)

| File | Change | Scope |
|------|--------|-------|
| `models.py` | Add `QuoteEntry`, replace `evidence_refs` with `quote_ids` on Raw* models, add `quotes` to artifact models, remove `EvidenceRef` | Major: new model + field replacements |
| `extract_artifacts.py` | Update format detection: quote-first (has `quotes`) vs canonical (has `evidence_span_ids`), remove legacy path | Moderate: detection logic rewrite |
| `canonicalize.py` | Replace `_resolve_ref_to_span_id()` / `_upgrade_raw_*()` with quote-to-span resolution, update `run_canonicalize()` | Major: core logic rewrite |
| `verify.py` | Replace `_check_quote_verification_legacy()` with quote-based validation, add quote_id referential integrity check, remove legacy path | Major: core logic rewrite |
| `compose_prompts.py` | Update `task_instructions` strings for actor and event extraction | Minor: string changes |
| `prompt_assets/actors_prefix.md` | Update `<evidence>` section to describe quote-first protocol | Minor: text update |
| `prompt_assets/events_prefix.md` | Update `<evidence>` section to describe quote-first protocol | Minor: text update |
| `prompt_assets/event_examples.md` | Update examples to show quote-first format | Minor: text update |
| `check.py` | Update to use `quote_ids` instead of `evidence_refs` for anchor_text checks (if any) | Minor: field name updates |

### Skill Docs

| File | Change | Scope |
|------|--------|-------|
| `.claude/skills/extract-deal/SKILL.md` | Update Evidence Ref Schema to Quote-First schema, update Top-Level Structures, update actor/event record fields | Major: extraction contract rewrite |
| `.claude/skills/verify-extraction/SKILL.md` | Update to describe quote-first validation | Minor: reference update |

### Tests

| File | Change | Scope |
|------|--------|-------|
| `tests/test_skill_canonicalize.py` | Rewrite all fixtures from evidence_refs to quote-first format | Major: all fixtures change |
| `tests/test_skill_verify.py` | Rewrite all fixtures from evidence_refs to quote-first format | Major: all fixtures change |
| `tests/test_skill_check.py` | Update fixtures if check.py uses evidence_refs directly | Moderate: fixture updates |
| New: tests for quote-first format detection | Test extract_artifacts.py detects quotes vs canonical vs rejects legacy | Small: new test file or additions |

### Data Artifacts (Regenerated)

| Path | Action |
|------|--------|
| `data/skill/stec/extract/*` | Stale -- must re-extract through quote-first protocol |
| `data/skill/medivation/extract/*` | Stale -- must re-extract through quote-first protocol |
| `data/skill/stec/prompt/*` | Must regenerate after task instruction changes |
| `data/skill/medivation/prompt/*` | Must regenerate for medivation stress test |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `evidence_refs` with inline `anchor_text` per actor/event | Quote-first: top-level `quotes` array, actors/events reference `quote_ids` | Phase 3 (this phase) | Structural forcing of verbatim citation before extraction |
| Canonicalize resolves evidence_refs to spans | Canonicalize resolves quotes to spans | Phase 3 | Simpler code (no evidence_id branch), same underlying span resolution |
| Verify matches anchor_text per evidence_ref | Verify validates quote.text + checks quote_id referential integrity | Phase 3 | Two-round validation structure (text match + ID integrity) |
| Legacy format detection in extract_artifacts.py | Quote-first format detection, legacy format rejected | Phase 3 | No backward compatibility path |

## Open Questions

1. **EvidenceRef removal timing**
   - What we know: D-06 says EvidenceRef "can be cleaned out" once the new format is wired. D-04 says no dual-path.
   - What's unclear: Whether to remove EvidenceRef immediately in the same plan that adds QuoteEntry, or in a cleanup step after the new format is validated end-to-end.
   - Recommendation: Remove immediately per D-04 (no dual-path). The new format is tested before it ships, so there is no transitional state where both formats coexist.

2. **Quote ID namespace across chunks**
   - What we know: Chunked extraction produces separate actor packets per window. Each packet generates its own quotes.
   - What's unclear: Whether quote_ids should be globally unique across chunks or only unique within a packet.
   - Recommendation: Quote IDs should be unique within a single JSON response (one packet). The canonicalize stage processes each packet's quotes independently. If multi-chunk actors are merged, their quote_ids are combined and must not collide. Task instructions should instruct the LLM to use sequential numbering (Q001, Q002, ...) per response.

3. **Handling evidence_id references in quotes**
   - What we know: Current evidence_refs can have `evidence_id` (for cross-filing evidence from evidence_items.jsonl) instead of or in addition to `block_id`.
   - What's unclear: Whether quotes need an optional `evidence_id` field for non-block evidence, or whether all quotes must reference a block_id.
   - Recommendation: Quote entries use `block_id` only. Evidence items are already mapped to blocks through line-range overlap in the composition engine. If an evidence item is relevant, its text is within a block's range. This eliminates the evidence_id branch entirely and simplifies the quote-to-span mapping.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (standard library, no version pinned in pyproject.toml) |
| Config file | none (uses defaults) |
| Quick run command | `python -m pytest -q` |
| Full suite command | `python -m pytest -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROMPT-05a | QuoteEntry model validates quote_id, block_id, text | unit | `python -m pytest tests/test_skill_canonicalize.py -x` | Needs update (Wave 0) |
| PROMPT-05b | Extract artifact loader detects quote-first format | unit | `python -m pytest tests/test_skill_canonicalize.py -x` | Needs update (Wave 0) |
| PROMPT-05c | Extract artifact loader rejects legacy evidence_refs format | unit | `python -m pytest tests/test_skill_canonicalize.py -x` | Needs new test (Wave 0) |
| PROMPT-05d | Canonicalize resolves quotes to spans via resolve_text_span | unit | `python -m pytest tests/test_skill_canonicalize.py -x` | Needs rewrite (Wave 0) |
| PROMPT-05e | Verify validates quote.text against filing text (EXACT/NORMALIZED) | unit | `python -m pytest tests/test_skill_verify.py -x` | Needs rewrite (Wave 0) |
| PROMPT-05f | Verify checks quote_id referential integrity | unit | `python -m pytest tests/test_skill_verify.py -x` | Needs new test (Wave 0) |
| PROMPT-05g | Compose-prompts produces task instructions with quote-first protocol | unit | `python -m pytest tests/test_skill_compose_prompts.py -x` | Needs update |
| PROMPT-05h | stec end-to-end: re-extract, canonicalize, verify pass | integration/manual | `skill-pipeline canonicalize --deal stec && skill-pipeline verify --deal stec` | Manual after re-extraction |
| PROMPT-05i | medivation end-to-end: re-extract, canonicalize, verify | integration/manual | `skill-pipeline canonicalize --deal medivation && skill-pipeline verify --deal medivation` | Manual after re-extraction |

### Sampling Rate
- **Per task commit:** `python -m pytest -q`
- **Per wave merge:** `python -m pytest -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] Rewrite `tests/test_skill_canonicalize.py` fixtures from evidence_refs to quote-first format
- [ ] Rewrite `tests/test_skill_verify.py` fixtures from evidence_refs to quote-first format
- [ ] Add tests for quote-first format detection in extract_artifacts.py
- [ ] Add tests for legacy format rejection in extract_artifacts.py
- [ ] Update `tests/test_skill_check.py` fixtures if check.py references evidence_refs

## Sources

### Primary (HIGH confidence)
- `skill_pipeline/models.py` -- current Pydantic models, EvidenceRef, RawSkillActorRecord, RawSkillEventRecord, SpanRecord
- `skill_pipeline/canonicalize.py` -- current span resolution from evidence_refs, dedup, NDA gate
- `skill_pipeline/verify.py` -- current quote verification (legacy and canonical paths)
- `skill_pipeline/extract_artifacts.py` -- current format detection (legacy vs canonical)
- `skill_pipeline/provenance.py` -- `resolve_text_span()` (reusable as-is)
- `skill_pipeline/normalize/quotes.py` -- `find_anchor_in_segment()` (reusable as-is)
- `skill_pipeline/compose_prompts.py` -- current task_instructions strings
- `skill_pipeline/prompt_assets/` -- current prompt prefix files
- `.claude/skills/extract-deal/SKILL.md` -- current extraction contract and schema
- `data/skill/stec/extract/` -- current stec artifacts (canonical format, 40 spans, 20 EXACT + 20 NORMALIZED)

### Secondary (MEDIUM confidence)
- `.planning/phases/03-quote-before-extract/03-CONTEXT.md` -- locked decisions from discussion
- `.planning/REQUIREMENTS.md` -- PROMPT-05 requirement definition
- `.planning/ROADMAP.md` -- Phase 3 exit criteria

### Tertiary (LOW confidence)
- None -- all findings are based on direct code inspection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries; all changes are within existing Pydantic + pytest stack
- Architecture: HIGH -- direct code inspection of all files that need modification, reusable functions verified
- Pitfalls: HIGH -- derived from understanding the current format detection, model validation, and test fixture patterns

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable -- internal schema change with no external dependencies)
