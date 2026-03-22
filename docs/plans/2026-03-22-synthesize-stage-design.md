# Synthesize Stage Design

**Date:** 2026-03-22
**Status:** Approved
**Goal:** Close the structural-event gap between the pipeline and Alex's benchmark by adding a deterministic `synthesize` stage that infers auction-structure events from already-extracted data.

## Problem

Reconciliation against Alex's benchmark (stec: 0.76 match rate, saks: 0.48) reveals the pipeline consistently misses structural events that Alex codes: round boundaries, implicit drops at signing, go-shop drops, partial-company drops, and IB retention. The LLM extraction prompt already asks for these event types, but yield is unreliable.

The root cause is a category mismatch: these events are either **inferred** (not explicitly stated in the filing) or **semi-formulaic** (stated but in patterns the LLM inconsistently captures). Deterministic rules are more reliable, auditable, and testable than LLM extraction for this class of events.

## Approach: Deterministic-First

Keep the LLM focused on narrative extraction (proposals, NDAs, explicit drops, bidder interest, process initiation, executed). Add a new deterministic `synthesize` stage that generates structural events from the events the LLM already extracts reliably.

## Pipeline Position

```
/extract-deal              → actors_raw.json, events_raw.json
skill-pipeline canonicalize     → canonical schema, spans.json
skill-pipeline synthesize       → ← NEW: synthetic structural events
skill-pipeline check            → structural gate
skill-pipeline verify           → span verification
skill-pipeline coverage         → source coverage audit
```

## Input Contract

- `data/skill/<slug>/extract/actors_raw.json` (canonical, post-canonicalize)
- `data/skill/<slug>/extract/events_raw.json` (canonical, post-canonicalize)
- `data/skill/<slug>/extract/spans.json`
- `data/deals/<slug>/source/chronology_blocks.jsonl`
- `data/deals/<slug>/source/evidence_items.jsonl`
- `raw/<slug>/filings/*.txt` (full filing text for IB regex scan)
- `raw/<slug>/document_registry.json` (document_id → filing path)

## Output Contract

- Mutates `events_raw.json` in place (appends synthetic events), following canonicalize's precedent
- Writes `data/skill/<slug>/synthesize/synthesize_log.json` recording every synthetic event and its derivation rule
- Idempotent: checks for existing `synthesis_source` events before running; re-runs are no-ops

## Schema Changes

**One new optional field on event records:**

```
synthesis_source: str | None
```

Values: `implicit_drop_at_signing`, `go_shop_drop`, `partial_company_drop`, `round_boundary_inferred`, `ib_retention_scan`. Null for LLM-extracted events.

**No new event types.** All synthesized events use existing types from the 20-type taxonomy.

## Synthesis Rules

### Rule 1: Implicit Drop at Signing (`implicit_drop_at_signing`)

**Trigger:** An `executed` event exists with `executed_with_actor_id`.

**Logic:**
1. Find all actors with at least one `nda` event.
2. Exclude the acquirer (`executed_with_actor_id`).
3. Exclude actors with an existing explicit `drop` event.
4. For each remaining actor, synthesize a `drop` event:
   - `date` = execution date
   - `drop_reason_text` = "Implicit dropout at merger signing"
   - `actor_ids` = [actor_id]
   - `evidence_refs` = reference the `executed` event's evidence spans

### Rule 2: Go-Shop Drops (`go_shop_drop`)

**Trigger:** An `executed` event exists AND filing text contains go-shop language.

**Logic:**
1. Scan filing text for go-shop period dates (regex near "go-shop", "solicitation period", "no-shop").
2. Find actors whose `nda` date falls within or after the go-shop start.
3. Exclude actors with an existing `proposal` or explicit `drop`.
4. Synthesize a `drop` event dated at go-shop expiry:
   - `drop_reason_text` = "Go-shop period expired without proposal"
   - `evidence_refs` = reference the go-shop filing passage

### Rule 3: Partial-Company Drops (`partial_company_drop`)

**Trigger:** `events_raw.json` has an `exclusions` array with `partial_company_bid` entries.

**Logic:**
1. Read the `exclusions` array.
2. For each partial-company exclusion, synthesize a `drop` event:
   - `event_type` = "drop"
   - `drop_reason_text` from exclusion text
   - Date from exclusion's date or nearest process event
   - `evidence_refs` from the exclusion's evidence refs

### Rule 4: Round Boundary Inference (`round_boundary_inferred`)

**Trigger:** 3+ proposals from different actors land on the same date (±1 day).

**Logic:**
1. Group `proposal` events by date (±1 day clustering).
2. For each cluster of 3+ proposals:
   - Synthesize a `final_round` (or `final_round_inf`) event at that date.
   - Look backward 14 days in chronology for process-letter language → synthesize the corresponding `_ann` event.
   - First cluster = informal round; second cluster = formal round.
3. If extension language is found after a formal round, synthesize `final_round_ext_ann` / `final_round_ext`.

### Rule 5: IB Retention Scan (`ib_retention_scan`)

**Trigger:** Always runs.

**Logic:**
1. Scan full filing text with regexes for advisor-retention language:
   - `"retained {NAME} as (its |the Company's )?(financial|legal) advisor"`
   - `"engaged {NAME}"`
   - `"{NAME}, the Company's (longstanding |)financial advisor"`
2. Extract advisor name and approximate date from context.
3. Skip if `ib_retention` event already exists for that actor.
4. Synthesize with `evidence_refs` pointing to filing line.

### Rule 6: Bidder Type Propagation (Export-Layer Only)

Not a synthesis rule. Change to `/export-csv`: populate the `type` column on every row for each actor, not just first appearance. One-line logic change.

## Downstream Stage Impact

| Stage | Change |
|-------|--------|
| `check` | None — structural rules apply uniformly |
| `verify` | Skip span verification for events with `synthesis_source is not None` (rule-derived, no anchor text) |
| `coverage` | None — coverage matches on `event_type` |
| `enrich-core` | Synthetic drops get `dropout_classifications` via existing rules. Synthetic rounds populate `rounds` array. May need minor preference for explicit round events over inference. |
| `/enrich-deal` | None |
| `/export-csv` | Bidder type propagation (Rule 6) |
| `reconcile-alex` | Match rate improves; no logic change |

## Error Handling

| Condition | Behavior |
|-----------|----------|
| `events_raw.json` missing | `FileNotFoundError` — hard fail |
| No `executed` event | Rules 1, 2 skip; logged |
| No proposal clusters ≥ 3 | Rule 4 skips; logged |
| No IB language in filing | Rule 5 skips; logged |
| Empty/missing exclusions | Rule 3 skips; logged |
| Re-run (synthetic events exist) | All rules skip; idempotent |
| Invalid `executed_with_actor_id` | Hard fail — corrupted data |

## Testing

**File:** `tests/test_skill_synthesize.py`

| Test | Input | Assertion |
|------|-------|-----------|
| `test_implicit_drop_at_signing` | 3 NDA actors, 1 executed | 2 synthetic drops |
| `test_implicit_drop_skips_already_dropped` | Actor with explicit drop | No duplicate drop |
| `test_go_shop_drop` | Go-shop NDA, no proposal | 1 go-shop drop |
| `test_partial_company_drop` | Partial-company exclusion | 1 DropTarget |
| `test_round_boundary_3_proposals` | 3 proposals same day | 1 final_round + 1 final_round_ann |
| `test_round_boundary_two_clusters` | 2 date clusters | inf + formal rounds |
| `test_ib_scan_finds_advisor` | Filing with retention language | 1 ib_retention |
| `test_ib_scan_no_duplicate` | Existing ib_retention | No new event |
| `test_idempotent` | Pre-existing synthetic events | No changes |
| `test_bidder_type_propagation` | Multi-row actor | type on every row |

Integration tests against stec and saks verify match rate improvement.

## Updated Hybrid Sequence

```
/deal-agent <slug>
  |-- /extract-deal <slug>
  |-- skill-pipeline canonicalize --deal <slug>
  |-- skill-pipeline synthesize --deal <slug>       ← NEW
  |-- skill-pipeline check --deal <slug>
  |-- skill-pipeline verify --deal <slug>
  |-- skill-pipeline coverage --deal <slug>
  |-- /verify-extraction <slug>
  |-- skill-pipeline enrich-core --deal <slug>
  |-- /enrich-deal <slug>
  |-- /export-csv <slug>
  |-- /reconcile-alex <slug>
```

## Expected Impact

Based on reconciliation analysis:
- **STEC:** 7 pipeline-only orphans → ~4 would be closed by Rules 1, 3, 4. 6 Alex-only orphans → ~6 would be closed. Match rate: 0.76 → ~0.95.
- **SAKS:** 3 pipeline-only orphans → unchanged (already grounded process events). 13 Alex-only orphans → ~9 would be closed by Rules 1, 2, 4, 5. Match rate: 0.48 → ~0.84.
