# Architecture Patterns: v1.1 Reconciliation + Execution-Log Quality Fixes

**Domain:** Integration architecture for reconciliation-driven fixes and execution-log hardening
**Researched:** 2026-03-29
**Scope:** How new features integrate with existing `skill_pipeline/` stages

## Existing Architecture Summary

```
seeds.csv
  -> raw-fetch          -> raw/<slug>/*
  -> preprocess-source  -> data/deals/<slug>/source/*
  -> compose-prompts    -> data/skill/<slug>/prompt/*
  -> /extract-deal      -> data/skill/<slug>/extract/{actors_raw,events_raw}.json
  -> canonicalize       -> actors_raw.json, events_raw.json, spans.json (in-place upgrade)
  -> check              -> check_report.json
  -> verify             -> verification_findings.json, verification_log.json
  -> coverage           -> coverage_findings.json, coverage_summary.json
  -> gates              -> gates_report.json
  -> /verify-extraction -> (repair loop if deterministic findings are repairable)
  -> enrich-core        -> deterministic_enrichment.json
  -> db-load            -> pipeline.duckdb
  -> db-export          -> deal_events.csv
```

Key files touched by v1.1 changes:
- `skill_pipeline/models.py` -- Pydantic schemas
- `skill_pipeline/enrich_core.py` -- bid classification, round pairing, cycles
- `skill_pipeline/canonicalize.py` -- quote-to-span resolution, dedup, NDA gate
- `skill_pipeline/check.py` -- structural gate (NDA count assertions)
- `skill_pipeline/coverage.py` -- evidence coverage audit
- `skill_pipeline/gates.py` -- semantic gates (temporal, cross-event, lifecycle)
- `skill_pipeline/db_load.py` -- DuckDB ingestion
- `skill_pipeline/db_export.py` -- CSV export from DuckDB
- `skill_pipeline/db_schema.py` -- DuckDB DDL

## Integration Point 1: bid_type Rule Priority Fix in enrich_core.py

### Problem

`_classify_proposal()` in `enrich_core.py` (lines 209-272) applies rules in this
order:

1. **Rule 1** (line 224-231): If `contains_range`, `mentions_indication_of_interest`,
   `mentions_preliminary`, or `mentions_non_binding` -> **Informal**
2. **Rule 2** (line 234-241): If `includes_draft_merger_agreement`,
   `includes_marked_up_agreement`, or `mentions_binding_offer` -> **Formal**
3. **Rule 2.5** (line 244-250): If `after_final_round_deadline` or
   `after_final_round_announcement` -> **Formal**

Rule 1 fires before Rule 2.5, so a final-round proposal that uses
"indication of interest" language is classified Informal even though it should
be Formal because it arrived after a final-round announcement/deadline.

### Fix Location

**File:** `skill_pipeline/enrich_core.py`, function `_classify_proposal()`

**Change:** Reorder rules so that Rule 2.5 (after-final-round) is evaluated
**before** Rule 1 (informal signals). The M&A convention is that process
position (final round) overrides language signals (IOI phrasing). The corrected
order should be:

```
1. Rule 2   (explicit formal docs: merger agreement, binding offer)     -> Formal
2. Rule 2.5 (after final round announcement/deadline, no formal docs)   -> Formal
3. Rule 1   (informal signals: range, IOI, preliminary, non-binding)    -> Informal
4. Rule 3   (after selective round)                                     -> Formal
5. Rule 4   (residual)                                                  -> Uncertain
```

Rationale for this ordering:
- Explicit formal docs (Rule 2) always win -- a signed merger agreement is Formal
  regardless of process position.
- Process position (Rule 2.5) beats language signals because M&A convention
  treats final-round submissions as Formal even when the filing uses IOI phrasing.
  This is the root cause of the 5+ deal misclassification bug.
- Informal signals (Rule 1) only apply when the proposal is NOT in a
  final-round context.
- Selective-round inference (Rule 3) fills remaining gaps.
- Residual -> Uncertain.

### Additional Consideration: `requested_binding_offer_via_process_letter`

The `FormalitySignals` model already includes
`requested_binding_offer_via_process_letter`. This signal should be incorporated
into Rule 2 or treated as equivalent to Rule 2.5 -- if the process letter
solicited a binding response, the submission is Formal.

### Downstream Impact

- `deterministic_enrichment.json` `bid_classifications` values change for 5+
  deals.
- `db-load` and `db-export` consume `bid_classifications` as-is, so no schema
  change needed downstream.
- Existing tests for `enrich_core` must be updated to reflect the new rule
  priority. New tests should cover the specific scenario: proposal with
  `mentions_indication_of_interest=True` AND
  `after_final_round_announcement=True` -> Formal (not Informal).

### What Changes

| Component | Change Type | Details |
|-----------|-------------|---------|
| `enrich_core.py` | **Modified** | Reorder `_classify_proposal()` rule evaluation |
| `tests/test_enrich_core.py` | **Modified** | Update expected classifications, add final-round IOI test |

### What Does NOT Change

- `models.py` -- `FormalitySignals` and `BidClassification` schemas are unchanged.
- `db_schema.py` -- enrichment table schema is unchanged.
- No new files needed.


## Integration Point 2: New Event Types (Round Milestones, DropTarget)

### Current State

`models.py` already defines these event types in both `RawSkillEventRecord` and
`SkillEventRecord` Literal unions (lines 173-194 and 243-265):

```python
"final_round_inf_ann", "final_round_inf",
"final_round_ann", "final_round",
"final_round_ext_ann", "final_round_ext",
```

Round milestone event types are **already present in the schema**. The pipeline
already supports them in `gates.py` (`SUBSTANTIVE_EVENT_TYPES`,
`ROUND_ANNOUNCEMENT_RULES`, `EVENT_PHASES`), `enrich_core.py` (`ROUND_PAIRS`,
`_pair_rounds()`), and `db_export.py` (`EVENT_TYPE_PRIORITY`,
`NOTE_BY_EVENT_TYPE`, `BIDDERLESS_EVENT_TYPES`).

The gap is in extraction: the local-agent `/extract-deal` skill docs do not
instruct the LLM to produce these event types consistently. This is a
skill-doc change, not a Python-side schema change.

### DropTarget Event Type: New Addition

`DropTarget` (committee-driven field narrowing) does NOT exist in the current
schema. The `DropoutClassification` model (line 364) already has the label
`"DropTarget"`, but there is no corresponding `event_type` in the event Literal
unions.

**Design decision:** DropTarget is NOT a new event_type. It is a **drop event**
where the committee narrows the field, and the dropout classification labels it
as `DropTarget`. The existing `drop` event type with
`DropoutClassification.label = "DropTarget"` is the correct modeling. The
enrichment layer (interpretive `/enrich-deal` or future deterministic rule)
assigns the `DropTarget` label based on whether the drop was committee-driven
versus bidder-initiated.

### Per-Stage Impact

| Stage | Round Milestones | DropTarget |
|-------|-----------------|------------|
| **models.py** | No change needed (types already exist) | No change needed (`DropTarget` is a dropout label, not an event_type) |
| **check.py** | No change needed (no event-type-specific structural checks for these) | No change needed (drop events already validated) |
| **coverage.py** | **May need new cue family** for round milestone cues (currently only covers `proposal`, `nda`, `withdrawal_or_drop`, `process_initiation`, `bidder_interest`, `advisor`). Consider adding a `round_milestone` cue family to detect filing language like "invited parties to submit final round bids" and flag uncovered round announcements. | No change needed (drops already covered by `withdrawal_or_drop` cue family) |
| **gates.py** | No change needed (round announcement rules already in `ROUND_ANNOUNCEMENT_RULES`, `SUBSTANTIVE_EVENT_TYPES`, `EVENT_PHASES`) | No change needed (drop events already validated in lifecycle/cross-event gates) |
| **enrich_core.py** | No change needed (`ROUND_PAIRS` already processes round milestone events) | **May need deterministic DropTarget classification rule**: if a drop event's `actor_ids` include target_board or if the `drop_reason_text` indicates committee decision, classify as DropTarget. Currently this is an interpretive enrichment task. |
| **db_load.py** | No change needed (events table already stores any event_type as TEXT) | No change needed |
| **db_export.py** | No change needed (`EVENT_TYPE_PRIORITY`, `NOTE_BY_EVENT_TYPE`, `BIDDERLESS_EVENT_TYPES` already include all round milestone types) | The `_note_value()` function already handles drop events via `dropout_label`. No change needed if enrichment writes the label. |
| **Extraction skill docs** | **Must update** `.claude/skills/` to instruct explicit extraction of round milestone events | **Must update** skill docs to recognize committee-driven narrowing as drop events |

### Summary for Round Milestones

The Python infrastructure is already complete. The bottleneck is **extraction
quality**: the LLM must be instructed to emit `final_round_inf_ann`,
`final_round_ann`, `final_round_ext_ann` etc. as separate events. This is a
skill-doc and few-shot-example change, not a code change.

### Summary for DropTarget

Model the committee-narrowing as `event_type: "drop"` with
`DropoutClassification.label = "DropTarget"`. The enrichment layer assigns the
label. Consider adding a deterministic heuristic to `enrich_core.py` that
classifies drops as DropTarget when:
- The drop has no explicit bidder-initiated withdrawal language
- Multiple actors drop simultaneously in the same event
- The event summary references "committee" or "board" decision language

This is a **new function in enrich_core.py** (`_classify_dropouts()`) that
produces `dropout_classifications` in `deterministic_enrichment.json`.


## Integration Point 3: all_cash Inference Logic

### Problem

The pipeline currently only marks `all_cash` (via
`MoneyTerms.consideration_type = "cash"`) when the filing sentence explicitly
says "cash." The reconciliation analysis shows this is too conservative.

### Where It Lives

The `consideration_type` field is set during **extraction** by the LLM. The
pipeline's deterministic stages do not currently infer or override
`consideration_type`.

### Recommended Approach

Add a deterministic inference rule to `enrich_core.py` that can upgrade
`consideration_type` to `"cash"` based on contextual signals:

1. **Deal-level cash inference:** If the `executed` event has
   `consideration_type = "cash"`, propagate `cash` to all proposals in the
   same cycle that lack an explicit `consideration_type` for the same bidder.

2. **Bidder-level consistency:** If a bidder's first proposal is `cash` and
   subsequent proposals have no explicit `consideration_type`, inherit `cash`.

3. **Filing-language heuristic:** If the event summary or evidence text contains
   "all cash" or "cash consideration" but `consideration_type` is null, set to
   `"cash"`.

### Integration Location

**File:** `skill_pipeline/enrich_core.py`

Add a new function `_infer_consideration_type()` that:
- Reads the events list and the actors artifact
- Applies the inference rules above
- Returns a dict of `{event_id: inferred_consideration_type}` for events
  where the type was upgraded
- Writes the inference results into `deterministic_enrichment.json`

### What Changes

| Component | Change Type | Details |
|-----------|-------------|---------|
| `enrich_core.py` | **Modified** | Add `_infer_consideration_type()` function, include results in enrichment output |
| `deterministic_enrichment.json` | **Extended** | Add `consideration_type_inferences` key |
| `db_load.py` | **Modified** | Load inferred consideration types into enrichment table |
| `db_schema.py` | **Modified** | Add `consideration_type_inferred` TEXT column to enrichment table |
| `db_export.py` | **Modified** | Use inferred consideration type when original is null |

### What Does NOT Change

- `models.py` -- the extraction schema is unchanged; inference happens at
  enrichment time, not extraction time.
- `check.py`, `coverage.py`, `gates.py` -- no new validation needed for inferred
  consideration types.


## Integration Point 4: Canonicalize quote_id Collision Prevention

### Problem

`canonicalize.py` line 103 raises `ValueError` on duplicate `quote_id` in the
quotes array:

```python
if quote.quote_id in seen_ids:
    raise ValueError(f"Duplicate quote_id {quote.quote_id!r} in quotes array")
```

The actors and events extraction passes can independently produce overlapping
`quote_id` values (e.g., both use `q001`, `q002`, etc.). When
`_resolve_quotes_to_spans()` receives the merged `all_quotes` list (line 408),
it hits this collision.

### Root Cause

The LLM extraction produces actors and events in separate passes. Both passes
start their quote_id counters from `q001`. The current code (line 408) merges
them naively:

```python
all_quotes = list(loaded.raw_actors.quotes) + list(loaded.raw_events.quotes)
```

### Fix Location

**File:** `skill_pipeline/canonicalize.py`, in `run_canonicalize()`

**Strategy:** Before merging, detect overlapping quote_ids between the two sets
and renumber the event-side quote_ids with a disambiguating prefix or offset.
Specifically:

```python
def _deduplicate_quote_ids(
    actors_artifact: RawSkillActorsArtifact,
    events_artifact: RawSkillEventsArtifact,
) -> tuple[RawSkillActorsArtifact, RawSkillEventsArtifact]:
    """Renumber event-side quote_ids if they collide with actor-side quote_ids."""
    actor_ids = {q.quote_id for q in actors_artifact.quotes}
    collisions = {q.quote_id for q in events_artifact.quotes if q.quote_id in actor_ids}
    if not collisions:
        return actors_artifact, events_artifact
    # Build remapping: evt_q001, evt_q002, ...
    remap = {qid: f"evt_{qid}" for qid in collisions}
    # Apply remap to events quotes and event records
    ...
```

This function should:
1. Detect overlapping quote_ids between actor and event quote sets
2. Build a remapping dict for colliding event-side quote_ids
3. Apply the remapping to: events quotes list, each event's `quote_ids` field
4. Return the updated artifacts
5. Call this BEFORE `_resolve_quotes_to_spans()`

### Alternative: Remove the Hard Error

The current `ValueError` is correct fail-fast behavior. The fix should prevent
the collision upstream rather than weakening the validation. Removing the error
would allow silent data corruption where two different quotes share the same ID.

### What Changes

| Component | Change Type | Details |
|-----------|-------------|---------|
| `canonicalize.py` | **Modified** | Add `_deduplicate_quote_ids()`, call before merge |
| `canonicalize.py` | **No removal** | Keep the `ValueError` guard as a safety net |
| `tests/test_canonicalize.py` | **Modified** | Add regression test with overlapping quote_ids |

### What Does NOT Change

- `models.py` -- quote_id is a string; no schema change needed.
- All downstream stages work with span_ids, not quote_ids; renumbering is
  contained within canonicalize.


## Integration Point 5: DuckDB Lock Retry Strategy

### Problem

`db-export` hit a transient DuckDB lock immediately after `db-load` in the
7-deal rerun. DuckDB uses file-level locking for write access. When `db-load`
closes its connection, the OS may not immediately release the file lock,
causing the subsequent `db-export` (read-only) to fail.

### Current Code

`db_schema.py` `open_pipeline_db()` (line 99-109) opens a DuckDB connection
with no retry logic:

```python
def open_pipeline_db(db_path: Path, *, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    if not read_only:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path), read_only=read_only)
    if not read_only:
        _ensure_schema(con)
    return con
```

### Recommended Strategy

Add retry logic to `open_pipeline_db()` with exponential backoff, constrained
to transient lock errors only:

```python
import time

MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 0.5

def open_pipeline_db(db_path: Path, *, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    if not read_only:
        db_path.parent.mkdir(parents=True, exist_ok=True)

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            con = duckdb.connect(str(db_path), read_only=read_only)
            if not read_only:
                _ensure_schema(con)
            return con
        except duckdb.IOException as exc:
            if "lock" not in str(exc).lower():
                raise
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(INITIAL_BACKOFF_SECONDS * (2 ** attempt))
    raise last_error  # type: ignore[misc]
```

**Design principles:**
- Only catch `duckdb.IOException` with "lock" in the message -- do not swallow
  other errors.
- Short backoff (0.5s, 1s, 2s) because DuckDB lock releases are nearly instant
  once the prior connection is fully closed.
- 3 retries max. If the lock persists after ~3.5s total, something else is
  wrong and should fail fast.
- Log retries to stderr for observability.

### What Changes

| Component | Change Type | Details |
|-----------|-------------|---------|
| `db_schema.py` | **Modified** | Add retry loop with backoff in `open_pipeline_db()` |
| `tests/test_db_schema.py` | **New or modified** | Test retry behavior with mocked lock error |

### What Does NOT Change

- `db_load.py`, `db_export.py` -- they call `open_pipeline_db()` and benefit
  automatically.
- No schema changes.


## Integration Point 6: Coverage False Positive Hardening

### Problem

Coverage produced false-positive NDA cues on contextual
confidentiality-agreement mentions (e.g., "which had executed a confidentiality
agreement" used as a relative clause describing a party, not as a new NDA
signing event).

### Current State

`coverage.py` already has some guards against this pattern (lines 112-123):

```python
references_prior_executed_nda = any(
    phrase in text or phrase in text_compact
    for phrase in (
        "which had executed a confidentiality agreement",
        "who had executed a confidentiality agreement",
        "that had executed a confidentiality agreement",
    )
)
has_target_due_diligence_confidentiality_language = (...)
```

And these are used as exclusion conditions (line 192-195, 201-203).

### Fix Location

**File:** `skill_pipeline/coverage.py`, in `_classify_cue_family()`

**Change:** Expand the exclusion phrases in `references_prior_executed_nda` and
`has_target_due_diligence_confidentiality_language` to cover additional
contextual patterns observed in the 7-deal rerun. Specifically:
- "had previously executed a confidentiality agreement"
- "had already entered into a confidentiality agreement"
- "pursuant to the confidentiality agreement"
- "under the terms of the confidentiality agreement"
- Other back-reference patterns that describe existing NDAs rather than new
  signings.

### What Changes

| Component | Change Type | Details |
|-----------|-------------|---------|
| `coverage.py` | **Modified** | Expand exclusion phrases in `_classify_cue_family()` |
| `tests/test_skill_coverage.py` | **Modified** | Add regression tests for contextual CA mentions |


## Integration Point 7: check.py Grouped NDA Count Assertions

### Problem

`check.py` `_check_nda_count_gaps()` (lines 174-219) counts NDA-signing bidders
but does not account for `group_size` on grouped actors. A single grouped actor
representing "4 unnamed financial sponsors" should count as 4, not 1, toward
the count assertion.

### Current State

The function already has `_counted_bidder_weight()` (lines 48-51) which returns
`group_size` for grouped actors, but line 203 uses it correctly:

```python
grounded_actor_count = sum(_counted_bidder_weight(actor) for actor in grounded_actors)
```

Wait -- examining more carefully, the function **does** use
`_counted_bidder_weight()` on line 203. The issue reported in the execution log
was that the extraction did not have proper grouped-actor records at the time.
After the extraction was repaired with grouped bidder cohorts, check passed.

### Verification

The check.py code is already correct for grouped NDA counts as long as the
extraction artifacts properly model grouped actors with `is_grouped=True` and
`group_size` set. The execution-log fix was in the **extraction artifacts**, not
in check.py.

**Possible remaining gap:** If a count assertion references
`nda_signed_financial_buyers` and some financial buyers signed NDAs but were
never modeled as actors (fully unnamed), the count gap persists. This is an
extraction completeness issue, not a check.py bug.

### What Changes

| Component | Change Type | Details |
|-----------|-------------|---------|
| `check.py` | **No code change needed** | Already handles `group_size` via `_counted_bidder_weight()` |
| `.claude/skills/` | **Modified** | Extraction skill docs should emphasize grouped-actor modeling |
| `tests/test_skill_check.py` | **Modified** | Ensure grouped-actor test coverage exists |


## Integration Point 8: Gates Rejecting Rollover Confidentiality Agreements

### Problem

Gates or check rejected deals where a confidentiality agreement was modeled as
an NDA event but represented a rollover-side or non-target-process agreement
(e.g., PetSmart Longview confidentiality agreement was not part of the sale
process).

### Root Cause

This is an **extraction error**, not a gate/check bug. The LLM modeled a
non-sale-process confidentiality agreement as an `nda` event. The gate correctly
identified the lifecycle inconsistency (NDA signer with no downstream events),
and the correct fix was to remove the erroneous event from the extraction.

### Recommendation

No code change in gates.py. Instead:
1. Update extraction skill docs to distinguish sale-process NDAs from
   rollover/due-diligence/non-target confidentiality agreements.
2. Consider adding to the `SkillExclusionRecord` categories a new category
   `"non_process_nda"` so the extraction can explicitly document why it excluded
   a confidentiality agreement mention.

### What Changes

| Component | Change Type | Details |
|-----------|-------------|---------|
| `gates.py` | **No change needed** | Gate behavior is correct |
| `models.py` | **Optional** | Add `"non_process_nda"` to `SkillExclusionRecord.category` Literal |
| `.claude/skills/` | **Modified** | Clarify NDA vs non-process CA distinction |


## Integration Point 9: Verbal/Oral Price Indication Support

### Problem

The pipeline misses verbal/oral price indications (e.g., STEC Company D,
PetSmart Bidder 3) because extraction skill docs focus on written submissions.

### Approach

This is primarily an **extraction skill-doc change**. The Python infrastructure
already supports proposals with any terms structure. A verbal indication is
simply a `proposal` event where `formality_signals.mentions_non_binding = True`
and the summary indicates it was verbal.

### What Changes

| Component | Change Type | Details |
|-----------|-------------|---------|
| `models.py` | **No change needed** | Proposal schema already supports verbal indications |
| `.claude/skills/` | **Modified** | Add verbal/oral indication extraction guidance |
| `coverage.py` | **Optional** | Add cue phrases for "verbal indication", "oral proposal" to `_classify_cue_family()` |


## Suggested Build Order

Dependencies determine sequencing. Changes are grouped into layers based on
what blocks what.

### Layer 0: Independent Hardening (no downstream dependencies, can parallelize)

These fixes are isolated improvements that do not affect each other:

| Task | File(s) | Rationale |
|------|---------|-----------|
| DuckDB lock retry | `db_schema.py` | Contained in one function, no schema change |
| Quote_id collision prevention | `canonicalize.py` | Contained in one function, no schema change |
| Coverage false-positive hardening | `coverage.py` | Contained in classifier function |

**All three can be implemented in parallel.** Each has a clear single-function
scope and independent test surface.

### Layer 1: bid_type Rule Priority Fix (blocks enrichment accuracy)

| Task | File(s) | Rationale |
|------|---------|-----------|
| Reorder `_classify_proposal()` rules | `enrich_core.py` | This is the pipeline's biggest accuracy bug per reconciliation; must fix before any re-enrichment |

**Depends on:** Nothing from Layer 0.
**Blocks:** Re-enrichment of all 9 deals, which would give wrong bid_type values
until fixed.

### Layer 2: Extraction Skill-Doc Updates (blocks re-extraction quality)

| Task | File(s) | Rationale |
|------|---------|-----------|
| Round milestone extraction guidance | `.claude/skills/` | Infrastructure exists; extraction must produce the events |
| DropTarget extraction recognition | `.claude/skills/` | Model as drop events with committee-driven context |
| Verbal/oral indication guidance | `.claude/skills/` | Model as proposals with appropriate signals |
| Non-process NDA exclusion guidance | `.claude/skills/` | Prevent rollover-CA false modeling |
| Grouped-actor modeling guidance | `.claude/skills/` | Ensure group_size flows correctly |

**Depends on:** Layer 1 (skill docs should reference corrected bid_type behavior).
**Blocks:** Any fresh extraction run.

### Layer 3: Deterministic Enrichment Extensions (new inference rules)

| Task | File(s) | Rationale |
|------|---------|-----------|
| all_cash inference | `enrich_core.py`, `db_schema.py`, `db_load.py`, `db_export.py` | New enrichment logic with schema extension |
| Deterministic DropTarget classification | `enrich_core.py` | New classification rule for committee-driven drops |

**Depends on:** Layer 1 (builds on corrected enrichment infrastructure).
**Blocks:** Nothing critical, but improves export completeness.

### Layer 4: Optional Model Extensions

| Task | File(s) | Rationale |
|------|---------|-----------|
| `non_process_nda` exclusion category | `models.py` | Low priority, improves extraction documentation |
| Coverage round-milestone cue family | `coverage.py` | Detects missing round milestones after extraction |

**Depends on:** Layer 2 (only useful after extraction produces round milestones).

### Layer 5: Validation Re-run

After all fixes:
1. Re-run `enrich-core` on all 9 deals to verify bid_type corrections
2. Re-run `db-load` and `db-export` to verify DuckDB lock retry works
3. Spot-check `canonicalize` on deals that previously had quote_id collisions

### Dependency Graph

```
Layer 0 (parallel)            Layer 1           Layer 2            Layer 3        Layer 4
+-----------------------+
| DuckDB lock retry     |
+-----------------------+     +-------------+
| quote_id collision    |     | bid_type    |   +-------------+   +------------+
+-----------------------+     | rule fix    |-->| skill-doc   |-->| all_cash   |   +----------+
| coverage FP hardening |     +-------------+   | updates     |   | inference  |   | optional |
+-----------------------+                       +-------------+-->| DropTarget |-->| model    |
                                                                  | classify   |   | exts     |
                                                                  +------------+   +----------+
```

### Critical Path

The critical path is: **bid_type rule fix -> skill-doc updates -> fresh
extraction -> re-enrichment**. The hardening fixes (Layer 0) are off the
critical path and can be done anytime.

## Data Flow Changes

### New Enrichment Output Fields

`deterministic_enrichment.json` currently contains:
```json
{
  "rounds": [...],
  "bid_classifications": {...},
  "cycles": [...],
  "formal_boundary": {...}
}
```

After v1.1, it will additionally contain:
```json
{
  "consideration_type_inferences": {"evt_007": "cash", ...},
  "dropout_classifications": {"evt_005": {"label": "DropTarget", ...}, ...}
}
```

The `dropout_classifications` key overlaps with the interpretive enrichment
artifact (`enrich/enrichment.json`). Design choice: deterministic dropout
classification should be a **subset** -- only classify drops where deterministic
signals are unambiguous. The interpretive layer fills the rest.

### DuckDB Schema Migration

The `enrichment` table needs one new optional column:

```sql
ALTER TABLE enrichment ADD COLUMN consideration_type_inferred TEXT;
```

Handle this via `_ensure_schema()` in `db_schema.py` using an
`ALTER TABLE ... ADD COLUMN IF NOT EXISTS` pattern rather than requiring a
clean-slate rebuild.

### No Changes To

- Raw filing artifacts (`raw/<slug>/`)
- Source artifacts (`data/deals/<slug>/source/`)
- Prompt packet artifacts (`data/skill/<slug>/prompt/`)
- Extract artifact schema (actors_raw.json, events_raw.json structure)
- Span registry schema (spans.json)
- Check report schema
- Verification log schema
- Coverage findings schema
- Gates report schema

## Anti-Patterns to Avoid

### Anti-Pattern 1: Weakening Fail-Fast Guards
**What:** Removing the `ValueError` on duplicate quote_ids in canonicalize,
or catching and ignoring DuckDB errors broadly.
**Why bad:** Silent data corruption. Two different quotes sharing an ID means
wrong span resolution.
**Instead:** Fix the root cause (renumber colliding IDs) and keep the guard.

### Anti-Pattern 2: Overloading event_type for DropTarget
**What:** Adding `"drop_target"` as a new event_type alongside `"drop"`.
**Why bad:** Every stage with an event_type Literal union would need updating
(models.py, check.py, coverage.py, gates.py, enrich_core.py, db_export.py).
The existing `DropoutClassification.label` is the correct extension point.
**Instead:** Keep `event_type: "drop"` and classify via enrichment labels.

### Anti-Pattern 3: Inference in Extraction
**What:** Asking the LLM to infer all_cash when the filing doesn't say "cash."
**Why bad:** Hallucination risk. The LLM should extract what the filing says.
Inference is a deterministic enrichment responsibility.
**Instead:** Extract the literal consideration_type. Infer missing values
deterministically in `enrich_core.py`.

### Anti-Pattern 4: Schema Migrations That Break Existing Data
**What:** Adding NOT NULL columns to DuckDB tables.
**Why bad:** Existing loaded deals would violate the constraint.
**Instead:** All new columns should be nullable (TEXT, DOUBLE, BOOLEAN with no
NOT NULL constraint).

## Sources

- `skill_pipeline/enrich_core.py` -- current bid classification rules (lines 209-272)
- `skill_pipeline/canonicalize.py` -- quote resolution and collision guard (lines 88-142)
- `skill_pipeline/models.py` -- schema definitions including event types and enrichment models
- `skill_pipeline/check.py` -- NDA count assertion logic (lines 174-219)
- `skill_pipeline/coverage.py` -- cue classification and false-positive guards (lines 84-224)
- `skill_pipeline/gates.py` -- semantic gates including round announcement rules
- `skill_pipeline/db_schema.py` -- DuckDB connection and schema DDL
- `skill_pipeline/db_load.py` -- enrichment loading logic
- `skill_pipeline/db_export.py` -- CSV export with bid_type and consideration_type
- `data/reconciliation_cross_deal_analysis.md` -- cross-deal reconciliation findings
- `quality_reports/session_logs/2026-03-29_7-deal-rerun_master.md` -- execution log
- `.planning/PROJECT.md` -- milestone definition and context
