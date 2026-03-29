# Technology Stack: v1.1 Reconciliation + Execution-Log Quality Fixes

**Project:** Filing-Grounded M&A Extraction Pipeline
**Researched:** 2026-03-29
**Scope:** Stack additions/changes for 6 targeted capability areas

## Executive Assessment

No new dependencies are required. All six v1.1 capability areas are achievable
through modifications to existing Python modules using the current stack:
Python 3.12, Pydantic 2.12.5, DuckDB 1.5.1, and the standard library. This is
the correct outcome for a brownfield hardening milestone -- adding libraries
would signal scope creep.

## Current Stack (DO NOT CHANGE)

| Technology | Installed Version | Pin | Purpose |
|---|---|---|---|
| Python | 3.12.10 | >=3.11 | Runtime |
| Pydantic | 2.12.5 | >=2.0 | Schema validation, artifact contracts |
| DuckDB | 1.5.1 | >=1.2 | Canonical structured store |
| edgartools | >=5.23 | <6.0 | SEC filing fetch |
| openpyxl | >=3.1 | | Spreadsheet I/O |
| pytest | >=8.0 | | Test framework |

## Capability Analysis: What Each Feature Needs

### 1. bid_type Enrichment Rule Priority Fix

**Files affected:** `skill_pipeline/enrich_core.py`

**Problem:** Rule 1 (IOI/indication-of-interest language -> Informal) fires
before Rule 2.5 (after final round -> Formal). Final-round submissions that
use IOI language get misclassified as Informal across 5+ deals.

**Stack needs:** None. This is a pure logic reordering in `_classify_proposal`.

**Implementation approach:** Reorder the rule cascade so that Rule 2.5 (after
final round announcement/deadline) evaluates before Rule 1 (informal signal
language). The M&A convention is clear: submissions solicited by a process
letter or responding to a final round deadline are Formal regardless of
"indication of interest" language in the filing text. The current code at
lines 223-272 of `enrich_core.py` evaluates in order: Rule 1 (Informal) ->
Rule 2 (Formal) -> Rule 2.5 (Formal after final round) -> Rule 3 (Formal
after selective round) -> Rule 4 (Uncertain). The fix reorders to:
Rule 2.5 -> Rule 2 -> Rule 1 -> Rule 3 -> Rule 4.

Also consider adding `requested_binding_offer_via_process_letter` as a Formal
signal that should override informal language -- the field already exists on
`FormalitySignals` but is not used in the classification logic.

**Testing:** Existing `tests/test_skill_enrich_core.py` covers bid
classification. Add regression cases for the 5 deals identified in the
reconciliation analysis (mac-gray, stec, prov-worcester, imprivata, penford).

### 2. Round Milestone Event Types and DropTarget Events

**Files affected:** `skill_pipeline/models.py` (schema), extraction skill
docs under `.claude/skills/`, `skill_pipeline/db_export.py` (export mapping),
`skill_pipeline/gates.py` (event phase mapping), `skill_pipeline/enrich_core.py`
(round pairing)

**Problem:** The extraction schema already defines `final_round_inf_ann`,
`final_round_inf`, `final_round_ann`, `final_round`, `final_round_ext_ann`,
`final_round_ext` event types. These exist in the `Literal` union for both
`RawSkillEventRecord.event_type` and `SkillEventRecord.event_type`. The issue
is that the local-agent extraction skill does not consistently produce these
events. The `DropTarget` event type (committee-driven field narrowing) is
genuinely missing from the schema.

**Stack needs:** None. Pydantic `Literal` union expansion is a one-line schema
change.

**Implementation approach for DropTarget:**
- Add `"drop_target"` to the `event_type` Literal union in both
  `RawSkillEventRecord` and `SkillEventRecord` in `models.py`.
- Add `"drop_target"` to `EVENT_PHASES` in `gates.py` (mapped to `{"bidding"}`).
- Add `"drop_target"` to `EVENT_TYPE_PRIORITY` and `NOTE_BY_EVENT_TYPE` in
  `db_export.py`.
- Add `"drop_target"` to `BIDDERLESS_EVENT_TYPES` in `db_export.py` (since
  these are committee-driven, not bidder-initiated).
- Update the extraction skill docs to describe `drop_target` semantics:
  committee or target board narrows the field, distinct from a bidder-initiated
  `drop` which models a bidder choosing to leave.
- The `DropTarget` is semantically different from `drop`: a `drop` means the
  bidder left; a `drop_target` means the target/committee excluded the bidder.
  The `drop_reason_text` field already exists on the event record and can
  carry the committee rationale.

**Implementation approach for round milestone extraction consistency:**
- The schema types already exist. The fix is in extraction skill docs: update
  `.claude/skills/` to explicitly instruct round milestone extraction with
  examples for each type.
- Ensure `enrich_core.py` `_pair_rounds` correctly handles the already-defined
  `ROUND_PAIRS` tuples.

**Testing:** Add schema validation tests that `drop_target` is accepted.
Add integration tests that `db_export` renders `drop_target` events correctly.

### 3. Contextual all_cash Inference

**Files affected:** `skill_pipeline/enrich_core.py`, `skill_pipeline/db_export.py`,
`skill_pipeline/db_schema.py`

**Problem:** Currently `db_export.py` line 303 emits `cash_value = "1"` only
when `event.terms.consideration_type == "cash"` at the individual event level.
The reconciliation analysis shows deals where all proposals from an acquirer
are cash but individual events may not have `consideration_type` set because
the filing does not repeat "cash" on every mention.

**Stack needs:** None. This is enrichment logic.

**Implementation approach:** Add a contextual inference rule to `enrich_core`:
- For each bidder, collect all proposal events where `consideration_type` is
  explicitly set.
- If every explicitly-set consideration type for a bidder is "cash" and the
  executed event for that bidder is also cash (or consideration_type is null
  on the executed event), infer `all_cash=True` for all that bidder's
  proposals.
- Store this in the deterministic enrichment artifact alongside bid
  classifications.
- `db_export.py` reads the inference from the enrichment table rather than
  only checking the per-event `terms.consideration_type`.

This is a conservative inference: it only propagates when ALL evidence agrees.
It does not guess "cash" when some events say "mixed." The reconciliation
analysis confirms this matches Alex's approach where he is right (Penford,
PetSmart) and avoids his error (Prov-Worcester cash+CVR).

**Testing:** Add test cases covering the propagation rule and the
mixed-consideration guard.

### 4. Canonicalize quote_id Collision Prevention

**Files affected:** `skill_pipeline/canonicalize.py`

**Problem:** The execution log shows `penford` hit duplicate quote_id
collisions during canonicalize because actor-side and event-side quote arrays
independently used `q_001`, `q_002`, etc. The current code at line 99-103 of
`canonicalize.py` checks for duplicates within the combined quotes list but
raises a hard error. The extraction agent generates quote IDs independently
per-pass (actor pass, event pass), creating collisions.

**Stack needs:** None. This is defensive dedup/renumber logic.

**Implementation approach:** Instead of raising on duplicate `quote_id`,
canonicalize should deterministically renumber colliding IDs. The approach:
1. Build a combined quote list from `actors_raw.quotes + events_raw.quotes`.
2. Detect collisions where the same `quote_id` appears in both lists.
3. For colliding event-side quotes, renumber by appending to a counter above
   the actor-side max (e.g., if actors use `q_001` through `q_042`, event
   `q_001` becomes `q_043`).
4. Update all `quote_ids` references in the events array to use the new IDs.
5. Log the renumbering in the canonicalize log under a new `"quote_id_remap"`
   key.
6. The existing `seen_ids` check at line 99 becomes the collision detector
   instead of a hard error.

This is safe because quote IDs are internal to the raw extraction artifacts
and are mapped to span IDs during canonicalization. The quote IDs themselves
are never persisted in canonical output.

**Testing:** Add a regression test with overlapping actor/event quote IDs and
verify the renumbered output has unique span mappings.

### 5. Coverage False Positive Heuristics

**Files affected:** `skill_pipeline/coverage.py`

**Problem:** The execution log documents two classes of false positives:
(a) Contextual confidentiality-agreement mentions that are not actual NDA
    signing events (e.g., "which had executed a confidentiality agreement"
    as a backward reference, or due-diligence confidentiality agreements that
    are not sale-process NDAs).
(b) Negotiation-continuation language appearing in the same text block as
    drop language, causing the block to be flagged as an uncovered drop when
    the bidder actually continued negotiating.

The execution log notes that some heuristic fixes were already applied
mid-rerun. This milestone should formalize and test those fixes.

**Stack needs:** None. This is NLP-level phrase matching with standard library
string operations.

**Implementation approach:**
- **Confidentiality false positives:** The existing `references_prior_executed_nda`
  and `has_target_due_diligence_confidentiality_language` guards in
  `_classify_cue_family` (lines 112-122 of `coverage.py`) already handle some
  cases. Extend with:
  - Rollover-side confidentiality agreements (e.g., investor signing CA as
    part of equity rollover, not as a bidder entering a sale process). Detect
    via phrases like "rollover", "equity commitment", "co-invest" near
    "confidentiality agreement."
  - Post-execution confidentiality mentions that reference the merger
    agreement's confidentiality provisions rather than a standalone NDA.
- **Drop false positives:** The existing `has_continue_negotiation_language`
  guard (lines 148-155) was added during the rerun. Ensure it is robust:
  verify the guard covers variations like "decided to proceed," "agreed to
  continue discussions," and "continued to engage."

**Testing:** The execution log mentions regressions were added to
`tests/test_skill_coverage.py`. Verify they cover the specific false-positive
patterns for saks (contextual CA mentions) and zep (negotiation continuation).

### 6. DuckDB Lock Resilience

**Files affected:** `skill_pipeline/db_schema.py`, `skill_pipeline/db_export.py`,
`skill_pipeline/db_load.py`

**Problem:** The execution log shows `db-export --deal zep` hit a transient
DuckDB lock immediately after `db-load` completed. DuckDB uses file-level
locking and does not expose a `busy_timeout` parameter. When `db-load` closes
its write connection and `db-export` immediately opens a read-only connection,
the OS-level file lock may not yet be released.

**Stack needs:** None. No new dependencies. DuckDB 1.5.1 is the current
installed version and is recent enough.

**Implementation approach:** Add a simple retry loop in `open_pipeline_db`
for `duckdb.IOException` (the exception DuckDB raises when it cannot acquire
the file lock):

```python
import time
import duckdb

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 0.5

def open_pipeline_db(db_path: Path, *, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    if not read_only:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            con = duckdb.connect(str(db_path), read_only=read_only)
            if not read_only:
                _ensure_schema(con)
            return con
        except duckdb.IOException as exc:
            last_error = exc
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
    raise last_error
```

This is the minimal correct fix. DuckDB's own documentation recommends
application-level retry for transient lock contention. The retry window is
short (0.5s, 1.0s, 1.5s) and only catches `IOException`, not general errors.

**Why not connection pooling or WAL mode:** DuckDB is an embedded database.
Connection pooling is meaningless for a single-process CLI tool that opens one
connection per command invocation. WAL mode is DuckDB's default already for
write connections. The transient lock is an OS-level file handle release timing
issue, not a database-level concurrency problem.

**Testing:** Add a unit test that monkeypatches `duckdb.connect` to raise
`IOException` on the first call and succeed on the second, verifying the retry
loop.

## What NOT to Add

| Rejected Addition | Reason |
|---|---|
| New Python dependencies | All 6 features are implementable with existing stack |
| tenacity or retry library | stdlib `time.sleep` with 3-line loop is sufficient for DuckDB lock retry |
| NLP library (spaCy, nltk) | Coverage heuristics use exact phrase matching, not statistical NLP |
| Additional database (SQLite, Postgres) | DuckDB is the canonical store; adding alternatives creates split-brain |
| async/await infrastructure | CLI tool with sequential stage execution; async adds complexity for zero benefit |
| Schema migration framework (alembic) | Single embedded DB with drop-and-reload per deal; migrations are overkill |
| hashlib for quote_id generation | Sequential renumbering is deterministic and debuggable; content hashing is opaque |
| Configuration file for enrichment rules | Rule ordering is code logic, not user-configurable behavior; config adds indirection |

## Version Constraints

The current `pyproject.toml` pins are appropriate. No changes needed:

```toml
dependencies = [
  "edgartools>=5.23,<6.0",
  "openpyxl>=3.1",
  "pydantic>=2.0",
  "duckdb>=1.2",
  "pytest>=8.0",
]
```

DuckDB 1.5.1 (installed) is well above the >=1.2 floor. The `IOException`
class used for retry has been stable since DuckDB 0.9.x. Pydantic 2.12.5
supports all `Literal` union features needed for schema expansion.

## Integration Points

### Cross-Module Dependency Map for v1.1 Changes

```
models.py (schema: add drop_target)
  -> canonicalize.py (handles new event type in dedup/gate)
  -> check.py (no change needed -- generic event checks)
  -> coverage.py (no change needed -- cue families don't target drop_target)
  -> gates.py (add drop_target to EVENT_PHASES)
  -> enrich_core.py (drop_target not a proposal, no classification needed)
  -> db_load.py (no change -- generic event loader)
  -> db_export.py (add drop_target to EVENT_TYPE_PRIORITY, NOTE_BY_EVENT_TYPE, BIDDERLESS_EVENT_TYPES)

enrich_core.py (rule reorder + all_cash inference)
  -> db_load.py (may need enrichment table column for all_cash)
  -> db_export.py (read all_cash from enrichment)
  -> db_schema.py (may need enrichment DDL update for all_cash column)

canonicalize.py (quote_id collision fix)
  -> No downstream changes -- quote IDs are internal to raw artifacts

coverage.py (false positive heuristics)
  -> No downstream changes -- coverage findings are advisory

db_schema.py (retry logic)
  -> db_load.py (inherits via open_pipeline_db)
  -> db_export.py (inherits via open_pipeline_db)
```

### DuckDB Schema Evolution for all_cash

If `all_cash` inference is stored in the enrichment table, the DDL in
`db_schema.py` needs a new column:

```sql
ALTER TABLE enrichment ADD COLUMN all_cash BOOLEAN;
```

But since `db-load` uses drop-and-reload per deal, the simpler approach is to
add `all_cash BOOLEAN` to the `CREATE TABLE IF NOT EXISTS enrichment` DDL.
Existing data is wiped on reload. No migration needed.

## Confidence Assessment

| Area | Confidence | Basis |
|---|---|---|
| bid_type rule fix | HIGH | Bug root cause confirmed in reconciliation analysis; code path is clear |
| DropTarget schema | HIGH | Pydantic Literal expansion is trivial; event type pattern well-established |
| all_cash inference | MEDIUM | Logic is clear but boundary cases (mixed consideration, CVR deals) need careful test design |
| quote_id collision | HIGH | Bug root cause confirmed in execution log; renumbering approach is deterministic |
| Coverage heuristics | MEDIUM | Phrase-matching heuristics require iterative tuning; initial patterns from execution log but may need expansion |
| DuckDB lock retry | HIGH | Standard pattern; DuckDB docs recommend application-level retry |

## Sources

- DuckDB concurrency documentation: https://duckdb.org/docs/stable/connect/concurrency
- DuckDB Python API: https://duckdb.org/docs/stable/clients/python/dbapi
- Cross-deal reconciliation analysis: `data/reconciliation_cross_deal_analysis.md` (local artifact)
- 7-deal execution log: `quality_reports/session_logs/2026-03-29_7-deal-rerun_master.md` (local artifact)
- Existing source code: `skill_pipeline/enrich_core.py`, `skill_pipeline/canonicalize.py`, `skill_pipeline/coverage.py`, `skill_pipeline/db_schema.py`, `skill_pipeline/models.py`, `skill_pipeline/gates.py`, `skill_pipeline/db_export.py`
