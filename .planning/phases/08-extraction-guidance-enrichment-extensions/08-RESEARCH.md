# Phase 8: Extraction Guidance + Enrichment Extensions - Research

**Researched:** 2026-03-30
**Domain:** Skill doc authoring, deterministic enrichment extension, DB schema plumbing
**Confidence:** HIGH

## Summary

Phase 8 has two distinct workstreams: (1) updating the extraction skill docs with guidance for round milestones, verbal indications, and NDA exclusions, and (2) extending the deterministic enrichment runtime with DropTarget classification and contextual all_cash inference. Both workstreams are well-constrained by user decisions D-01 through D-12 and the existing code patterns are thoroughly understood.

The skill doc workstream is pure documentation: editing `.claude/skills/extract-deal/SKILL.md` and running the mirror sync. No Python code changes are needed for EXTRACT-01/02/03. The enrichment workstream requires additions to `enrich_core.py` (DropTarget detection, all_cash inference), `models.py` (schema), `db_schema.py` (enrichment table column), `db_load.py` (all_cash loading), and `db_export.py` (all_cash override preference). It also requires matching regression tests.

**Primary recommendation:** Split into two plans: Plan 01 for skill doc updates (EXTRACT-01/02/03) with mirror sync, Plan 02 for deterministic enrichment extensions (ENRICH-02/03) with full DB plumbing and regression tests.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Edit `.claude/skills/extract-deal/SKILL.md` as the canonical skill source, then sync `.codex/skills/` and `.cursor/skills/` from it with `scripts/sync_skill_mirrors.py`. Do not hand-edit the mirrors independently.
- **D-02:** Round milestone guidance stays inside the existing six round event types already supported by the schema: `final_round_inf_ann`, `final_round_inf`, `final_round_ann`, `final_round`, `final_round_ext_ann`, and `final_round_ext`. Phase 8 adds extraction guidance and examples, not new event types or new round fields.
- **D-03:** Verbal or oral whole-company bids with explicit economics are still `proposal` events. "Oral" or "verbal" affects the event summary, notes, and formality signals; it does not make the event ineligible for extraction.
- **D-04:** NDA exclusion remains a skill-doc behavior change, not a schema expansion. Rollover equity agreements, bidder-bidder teaming agreements, and non-target diligence agreements stay out of `nda` events unless the filing clearly ties them to target sale-process diligence. Phase 8 should not add `nda_subtype`.
- **D-05:** Reuse the existing `DropoutClassification` label vocabulary and the existing `dropout_classifications` key inside `deterministic_enrichment.json`. Do not create a second deterministic dropout artifact or a parallel label set.
- **D-06:** The deterministic layer should stay sparse and conservative: Phase 8 emits `DropTarget` only when target-initiated exclusion is filing-grounded by round invitation context and/or explicit exclusion language in `drop_reason_text`. Other drop events can remain unlabeled in deterministic enrichment so downstream export still falls back to generic `Drop`.
- **D-07:** `DropTarget` directionality must match the existing `.claude/skills/enrich-deal/SKILL.md` rule: if the bidder first signals it will not improve, will not continue, or cannot proceed, that event is not `DropTarget` just because the target later confirms exclusion.
- **D-08:** Do not rewrite `terms.consideration_type` in extract artifacts or canonical events. Contextual `all_cash` is an enrichment/export concern and must travel through an explicit deterministic override path.
- **D-09:** Add an auditable deterministic `all_cash` override keyed by event_id, or an equivalent nullable enrichment-table column, so `db-load` and `db-export` can prefer the inferred value before falling back to `events.terms_consideration_type`.
- **D-10:** `all_cash` inference is cycle-local and fail-closed. Propagate `true` only when cash consideration is unambiguous from executed deal context or the same-cycle proposal set. Never infer through mixed/CVR structures (for example Providence & Worcester), and never override explicit mixed or non-cash terms.
- **D-11:** Phase 8 must ship deterministic regression tests together with the doc changes. Runtime tests should cover `DropTarget` and `all_cash` propagation using synthetic fixtures inspired by live cases; skill-level validation should cover mirror sync and the new extraction guidance text.
- **D-12:** Phase 8 stops at docs plus deterministic runtime/output wiring. Re-extraction, artifact repair, and reconciliation reruns remain Phase 9.

### Claude's Discretion
- Exact phrasing and example selection inside the skill docs, as long as the examples are filing-grounded and reinforce the decisions above
- Exact field name for the deterministic `all_cash` override, as long as it is explicit, auditable, and separate from extract literals
- Whether `DropTarget` detection starts from round invitation deltas, `drop_reason_text`, or both, as long as target directionality is preserved

### Deferred Ideas (OUT OF SCOPE)
- `nda_subtype` schema support across raw/canonical models, gates, coverage, enrichment, DB load, and export
- Full deterministic `DropBelowM`, `DropBelowInf`, and `DropAtInf` classification
- Re-extracting affected deals and measuring reconciliation gains (Phase 9)
- Additional bid-type refinements beyond the current deterministic rule set
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EXTRACT-01 | Extraction skill docs include round milestone event guidance with filing-grounded examples | Skill doc structure analyzed; existing 6 round event types in taxonomy confirmed; stec evt_017/evt_018/evt_021/evt_022 as primary examples; current SKILL.md lacks round-specific extraction guidance beyond basic taxonomy table |
| EXTRACT-02 | Extraction skill docs include verbal/oral price indication guidance with examples | mac-gray evt_013/evt_020 and penford evt_005 as reference patterns; D-03 confirms verbal bids are still `proposal` events; formality_signals handling documented |
| EXTRACT-03 | Extraction skill docs include NDA exclusion guidance for rollover-side and non-target confidentiality agreements | Phase 6 already hardened gates/coverage tolerance; D-04 confirms doc-level only, no schema expansion; coverage.py patterns as reference for what to exclude |
| ENRICH-02 | Deterministic DropTarget classification for committee-driven field narrowing | Round pairing already computed in enrich_core.py; `_pair_rounds()` tracks `invited_actor_ids` and `is_selective`; `dropout_classifications` key already exists in interpretive enrichment schema; deterministic enrichment currently has no dropout_classifications |
| ENRICH-03 | Contextual all_cash inference from deal-level consideration patterns | Current db_export.py derives all_cash from `events.terms_consideration_type == "cash"` only; needs new enrichment field, DB column, load/export plumbing |
</phase_requirements>

## Architecture Patterns

### Workstream 1: Skill Doc Updates (EXTRACT-01/02/03)

**What changes:**
- `.claude/skills/extract-deal/SKILL.md` -- add three new guidance sections
- Mirror sync via `scripts/sync_skill_mirrors.py`
- Optionally extend `skill_pipeline/prompt_assets/event_examples.md` with new few-shot examples

**Edit strategy for SKILL.md:**

The current SKILL.md has these sections in order:
1. Design Principles
2. Purpose / When To Use / Benchmark Boundary
3. Reads / Preflight / Extraction Method (Pass 1/Pass 2)
4. Writes (schema docs)
5. Reference: Event Taxonomy (20 types)
6. Reference: Formality Signals
7. Reference: Exclusions

Round milestone guidance (EXTRACT-01) belongs in the Extraction Method section, after the existing event extraction rules and before the Pass 2 gap re-read. A new subsection like "### Round Milestone Events" with guidance on the 6 round event types, paired announcement/deadline patterns, and `invited_actor_ids` population.

Verbal indication guidance (EXTRACT-02) belongs in the same area, near the proposal extraction rules. A subsection like "### Verbal/Oral Price Indications" clarifying D-03: oral bids with explicit economics are `proposal` events, oral signals without explicit price are not.

NDA exclusion guidance (EXTRACT-03) belongs near the existing NDA extraction rules. A subsection like "### NDA Exclusion Guidance" listing what should NOT be extracted as `nda` events: rollover equity agreements, bidder-bidder teaming agreements, and non-target diligence agreements.

**Filing-grounded examples for each:**

| Requirement | Primary Example Deal | Event IDs | Pattern |
|-------------|---------------------|-----------|---------|
| EXTRACT-01 (rounds) | stec | evt_017 (final_round_ann), evt_018 (final_round), evt_021 (final_round_ext_ann), evt_022 (final_round_ext) | Formal round announcement with 2 invited bidders, followed by deadline; then extension round with same 2 bidders |
| EXTRACT-02 (verbal) | mac-gray | evt_013 (oral $17.65), evt_020 (oral $18.50) | Oral priced proposals from Party A with explicit per-share economics; still `proposal` events |
| EXTRACT-02 (verbal) | penford | evt_005 | Oral indication from Party D at $17.00; still a `proposal` event |
| EXTRACT-03 (NDA exclusion) | imprivata | coverage context | Filing mentions confidentiality agreements in rollover-equity context -- not sale-process NDAs |

### Workstream 2: Deterministic Enrichment Extensions (ENRICH-02/03)

**Pattern: DropTarget Detection (ENRICH-02)**

Current state: `enrich_core.py` already computes `rounds` via `_pair_rounds()` which tracks `invited_actor_ids` and `is_selective`. The deterministic enrichment output currently has NO `dropout_classifications` key -- that lives only in interpretive `enrichment.json` from the enrich-deal skill.

Detection algorithm (recommended):

```python
def _classify_dropouts(
    events: list[SkillEventRecord],
    rounds: list[dict],
) -> dict[str, dict]:
    """Deterministic DropTarget classification based on round invitation deltas."""
    result: dict[str, dict] = {}
    event_order = [e.event_id for e in events]

    for evt in events:
        if evt.event_type != "drop":
            continue

        # Check D-07 directionality: if bidder signaled withdrawal first, skip
        if _bidder_signaled_withdrawal(evt):
            continue

        # Check if target excluded this bidder via round invitation context
        if _target_excluded_via_round(evt, events, rounds, event_order):
            result[evt.event_id] = {
                "label": "DropTarget",
                "basis": "...",  # auditable basis string
                "source_text": evt.drop_reason_text or "",
            }

    return result
```

Target-exclusion signals (from CONTEXT.md D-06):
1. **Round invitation delta**: Bidder was active (had NDA, no prior drop) at time of round announcement, but NOT in `invited_actor_ids` for that round. The drop event occurs after the round announcement.
2. **Explicit exclusion language in `drop_reason_text`**: Phrases like "did not invite", "determined not to include", "excluded from", "not selected to participate".

D-07 bidder-signaled-withdrawal keywords to check in `drop_reason_text`: "could not improve", "would not be in a position", "no longer interested", "unable to proceed", "would not move forward", "declined to improve", "not prepared to move forward".

**Pattern: Contextual all_cash Inference (ENRICH-03)**

Current state: `db_export.py` line 303 does:
```python
cash_value = "1" if event.get("terms_consideration_type") == "cash" else "NA"
```

This means all_cash=1 only when the individual event's `terms.consideration_type` is explicitly `"cash"`. Many deals have proposals where consideration_type is `null` even though the entire deal is clearly all-cash.

The inference algorithm (recommended):

```python
def _infer_all_cash_overrides(
    events: list[SkillEventRecord],
    cycles: list[dict],
) -> dict[str, bool]:
    """Cycle-local all_cash inference. Fail-closed: only infers true when unambiguous."""
    result: dict[str, bool] = {}
    event_order = [e.event_id for e in events]

    for cycle in cycles:
        cycle_events = _events_in_cycle(events, cycle, event_order)

        # Find executed event in this cycle
        executed = [e for e in cycle_events if e.event_type == "executed"]
        if not executed:
            continue

        # Check executed event's consideration_type first
        exec_terms = executed[0].terms
        if exec_terms and exec_terms.consideration_type == "cash":
            # Propagate to all proposals in cycle that lack explicit type
            for evt in cycle_events:
                if evt.event_type == "proposal" and (
                    evt.terms is None or evt.terms.consideration_type is None
                ):
                    result[evt.event_id] = True
            continue

        # Check if ALL proposals with explicit type are cash
        typed_proposals = [
            e for e in cycle_events
            if e.event_type == "proposal" and e.terms and e.terms.consideration_type
        ]
        if typed_proposals and all(
            e.terms.consideration_type == "cash" for e in typed_proposals
        ):
            # Propagate to untyped proposals
            for evt in cycle_events:
                if evt.event_type == "proposal" and (
                    evt.terms is None or evt.terms.consideration_type is None
                ):
                    result[evt.event_id] = True

        # D-10: Never infer through mixed/CVR -- fail closed

    return result
```

**DB Schema Addition:**

Add `all_cash_override` column to the `enrichment` table in `db_schema.py`:

```sql
CREATE TABLE IF NOT EXISTS enrichment (
    deal_slug TEXT NOT NULL,
    event_id TEXT NOT NULL,
    dropout_label TEXT,
    dropout_basis TEXT,
    bid_label TEXT,
    bid_rule_applied DOUBLE,
    bid_basis TEXT,
    all_cash_override BOOLEAN,     -- NEW: deterministic all_cash inference
    PRIMARY KEY (deal_slug, event_id)
);
```

**DB Load Changes:**

In `db_load.py` `_load_enrichment()`, read `all_cash_overrides` from `deterministic_enrichment.json` and populate the new column.

**DB Export Changes:**

In `db_export.py` `_format_event_row()`, replace the current direct `terms_consideration_type` check with a two-step preference:

```python
# Prefer deterministic all_cash override, then fall back to extract literal
if enrichment_row and enrichment_row.get("all_cash_override") is True:
    cash_value = "1"
elif event.get("terms_consideration_type") == "cash":
    cash_value = "1"
else:
    cash_value = "NA"
```

### Deterministic Enrichment Output Schema Extension

Current `deterministic_enrichment.json` has:
```json
{
    "rounds": [...],
    "bid_classifications": {...},
    "cycles": [...],
    "formal_boundary": {...}
}
```

Phase 8 adds:
```json
{
    "rounds": [...],
    "bid_classifications": {...},
    "cycles": [...],
    "formal_boundary": {...},
    "dropout_classifications": {...},    // NEW: sparse, DropTarget only
    "all_cash_overrides": {...}          // NEW: event_id -> true
}
```

### Recommended Project Structure (files touched)

```
.claude/skills/extract-deal/SKILL.md         # EXTRACT-01/02/03: guidance additions
.codex/skills/extract-deal/SKILL.md          # mirror sync
.cursor/skills/extract-deal/SKILL.md         # mirror sync
skill_pipeline/enrich_core.py                # ENRICH-02: _classify_dropouts()
                                             # ENRICH-03: _infer_all_cash_overrides()
skill_pipeline/models.py                     # no changes needed (DropoutClassification already exists)
skill_pipeline/db_schema.py                  # ENRICH-03: all_cash_override column
skill_pipeline/db_load.py                    # ENRICH-02/03: load new enrichment fields
skill_pipeline/db_export.py                  # ENRICH-02/03: prefer override, dropout label
tests/test_skill_enrich_core.py              # ENRICH-02/03: regression tests
tests/test_skill_db_load.py                  # ENRICH-03: all_cash loading test
tests/test_skill_db_export.py                # ENRICH-02/03: all_cash + dropout in export
tests/test_skill_mirror_sync.py              # EXTRACT-01/02/03: content assertions
skill_pipeline/prompt_assets/event_examples.md  # optional: new few-shot examples
```

### Anti-Patterns to Avoid

- **Mutating extract artifacts:** D-08 explicitly forbids rewriting `terms.consideration_type`. All inferences go through enrichment.
- **Creating parallel label sets:** D-05 requires reusing the existing `DropoutClassification` model and `dropout_classifications` key.
- **Over-classifying drops:** D-06 says only emit `DropTarget` when target-initiated exclusion is filing-grounded. Other drops stay unlabeled in deterministic enrichment.
- **Inferring all_cash through mixed deals:** D-10 is fail-closed. Providence & Worcester (cash + CVR) must NOT get all_cash=true.
- **Hand-editing mirror files:** D-01 requires canonical edit in `.claude/skills/`, then sync.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Mirror synchronization | Manual file copy | `scripts/sync_skill_mirrors.py` | Already handles directory cleanup, README generation, and is tested |
| Round pairing for DropTarget | New round calculation | `_pair_rounds()` output from existing enrichment | Already computed before bid classification; reuse the same `rounds` list |
| Bidder active state tracking | New bidder state tracker | `_active_counts_for_cycle()` in enrich_core.py | Already tracks NDA -> active, drop -> inactive per bidder |
| DB schema migration | Manual ALTER TABLE | `CREATE TABLE IF NOT EXISTS` with new column | DuckDB schema is recreated via DDL; no migration needed |

## Common Pitfalls

### Pitfall 1: DropTarget Directionality Inversion
**What goes wrong:** Classifying a bidder-initiated withdrawal as DropTarget because the target later "confirmed" the exclusion.
**Why it happens:** The filing often describes both perspectives: "Party X said it could not improve" followed by "the Committee then determined not to include Party X." The second clause looks like target exclusion.
**How to avoid:** Check `drop_reason_text` for bidder-signaled-withdrawal keywords FIRST. Only proceed to round-invitation-delta check if no bidder withdrawal signal is found. D-07 is explicit about this ordering.
**Warning signs:** stec evt_023 ("WDC was not prepared to move forward") is bidder-initiated even though WDC was technically excluded from further rounds. Same for stec evt_024 (Company D diligence constraint).

### Pitfall 2: all_cash False Positive on Mixed Consideration
**What goes wrong:** Inferring all_cash=true for a deal where the executed transaction includes cash + CVR (contingent value rights).
**Why it happens:** Providence & Worcester's final G&W proposal says "cash" but the deal structure includes CVR. If the inference only checks `consideration_type` fields, it might see all proposals as cash.
**How to avoid:** Check the executed event's consideration_type. If it is `mixed`, `other`, or `null` (and no explicit cash), do NOT propagate. Check all typed proposals in the cycle -- if any is non-cash, stop. D-10 says "never infer through mixed/CVR structures."
**Warning signs:** providence-worcester has 9 proposals with null consideration_type and only 1 with explicit "cash" (the final G&W proposal). The inference should NOT propagate from that single cash proposal to the others because the deal itself is cash+CVR.

### Pitfall 3: Skill Doc Mirror Drift
**What goes wrong:** Tests fail because `.codex/skills/` or `.cursor/skills/` don't match `.claude/skills/` after editing.
**Why it happens:** Forgetting to run `scripts/sync_skill_mirrors.py` after editing the canonical skill doc.
**How to avoid:** Always run mirror sync immediately after editing SKILL.md. The `test_skill_mirror_sync.py` tests will catch drift.
**Warning signs:** `test_codex_mirror_matches_canonical_extract_skill` and `test_cursor_mirror_matches_canonical_extract_skill` failures.

### Pitfall 4: DB Schema Column Addition Without Load/Export Updates
**What goes wrong:** Adding `all_cash_override` to the DDL but not updating `_load_enrichment()` INSERT statement or `_query_enrichment()` SELECT, causing silent NULLs or missing data.
**Why it happens:** DuckDB `CREATE TABLE IF NOT EXISTS` silently succeeds even when the existing table lacks the new column. The schema is only applied on fresh databases.
**How to avoid:** For existing databases, the DDL will not add the column. The code must handle both cases: (1) fresh DB gets the column from DDL, (2) existing DB needs an explicit `ALTER TABLE ADD COLUMN IF NOT EXISTS` or a recreation strategy. Since `db-load` does DELETE + INSERT per deal, the cleanest approach is to add the column via ALTER TABLE IF NOT EXISTS before the INSERT.
**Warning signs:** `_query_enrichment()` in db_export.py already does dynamic column detection via `PRAGMA table_info('enrichment')` for optional columns. Follow this pattern for `all_cash_override`.

### Pitfall 5: Phase 7 Over-Promotion Bug Interaction
**What goes wrong:** Phase 8 enrichment changes interact with the known Rule 2 over-promotion bug from Phase 7 (stec evt_025, saks evt_013).
**Why it happens:** The HANDOFF.md documents that Rule 2 has a range-bid guard (`not sig.contains_range or _has_best_and_final_language(evt)`) that was already shipped. The current code already handles this correctly -- the guard is in place.
**How to avoid:** Verify that Phase 8's changes to enrich_core.py do not alter `_classify_proposal()`. Phase 8 adds new functions (`_classify_dropouts`, `_infer_all_cash_overrides`) but should not modify existing bid classification logic.
**Warning signs:** Any test regression in the existing bid classification tests (lines 461-700 of test_skill_enrich_core.py).

## Code Examples

### DropTarget Detection Logic

```python
# Source: enrich_core.py pattern analysis + CONTEXT.md D-06/D-07

# Bidder-signaled-withdrawal keywords (D-07)
_BIDDER_WITHDRAWAL_SIGNALS = (
    "could not improve",
    "would not improve",
    "would not be in a position",
    "no longer interested",
    "unable to proceed",
    "would not move forward",
    "not prepared to move forward",
    "declined to improve",
    "was not able to increase",
    "not in a position to actively conduct",
    "could not increase",
    "would not continue",
    "cannot proceed",
    "would not proceed",
)

def _is_bidder_signaled_withdrawal(drop_reason_text: str | None) -> bool:
    if not drop_reason_text:
        return False
    lower = drop_reason_text.lower()
    return any(signal in lower for signal in _BIDDER_WITHDRAWAL_SIGNALS)

# Target-exclusion signals (D-06)
_TARGET_EXCLUSION_SIGNALS = (
    "did not invite",
    "determined not to invite",
    "determined not to include",
    "excluded from",
    "not selected to participate",
    "was not invited",
    "were not invited",
    "not included in",
    "narrowed the field",
    "reduced the group",
)

def _has_target_exclusion_language(drop_reason_text: str | None) -> bool:
    if not drop_reason_text:
        return False
    lower = drop_reason_text.lower()
    return any(signal in lower for signal in _TARGET_EXCLUSION_SIGNALS)
```

### all_cash Override in DB Export

```python
# Source: db_export.py line 303 current pattern + CONTEXT.md D-09

# Current (Phase 7):
cash_value = "1" if event.get("terms_consideration_type") == "cash" else "NA"

# Phase 8 replacement:
all_cash_override = enrichment_row.get("all_cash_override") if enrichment_row else None
if all_cash_override is True:
    cash_value = "1"
elif event.get("terms_consideration_type") == "cash":
    cash_value = "1"
else:
    cash_value = "NA"
```

### Deterministic Enrichment Output Extension

```python
# Source: enrich_core.py run_enrich_core() line 519-527

# Current:
_write_json(
    paths.deterministic_enrichment_path,
    {
        "rounds": rounds,
        "bid_classifications": bid_classifications,
        "cycles": cycles,
        "formal_boundary": formal_boundary,
    },
)

# Phase 8 adds:
dropout_classifications = _classify_dropouts(events, rounds)
all_cash_overrides = _infer_all_cash_overrides(events, cycles)

_write_json(
    paths.deterministic_enrichment_path,
    {
        "rounds": rounds,
        "bid_classifications": bid_classifications,
        "cycles": cycles,
        "formal_boundary": formal_boundary,
        "dropout_classifications": dropout_classifications,
        "all_cash_overrides": all_cash_overrides,
    },
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| all_cash from explicit `terms.consideration_type` only | Will add contextual inference via enrichment override | Phase 8 | Improves coverage for penford, petsmart-inc; preserves precision for prov-worcester |
| DropTarget only in interpretive enrichment.json | Will add deterministic DropTarget in deterministic_enrichment.json | Phase 8 | Makes target-exclusion available without running the LLM enrich-deal skill |
| No extraction guidance for round milestones | Will add explicit guidance and examples | Phase 8 | Better extraction quality on next re-extraction (Phase 9) |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (current) |
| Config file | pyproject.toml |
| Quick run command | `python -m pytest tests/test_skill_enrich_core.py -q` |
| Full suite command | `python -m pytest -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXTRACT-01 | Skill doc contains round milestone guidance text | unit | `python -m pytest tests/test_skill_mirror_sync.py -q` | Needs new assertions |
| EXTRACT-02 | Skill doc contains verbal indication guidance text | unit | `python -m pytest tests/test_skill_mirror_sync.py -q` | Needs new assertions |
| EXTRACT-03 | Skill doc contains NDA exclusion guidance text | unit | `python -m pytest tests/test_skill_mirror_sync.py -q` | Needs new assertions |
| ENRICH-02 | DropTarget classification from round invitation context | unit | `python -m pytest tests/test_skill_enrich_core.py -q` | Needs new tests |
| ENRICH-02 | DropTarget respects D-07 directionality | unit | `python -m pytest tests/test_skill_enrich_core.py -q` | Needs new tests |
| ENRICH-02 | DropTarget appears in db-export dropout label column | integration | `python -m pytest tests/test_skill_db_export.py -q` | Needs new tests |
| ENRICH-03 | all_cash inference propagates to untyped proposals | unit | `python -m pytest tests/test_skill_enrich_core.py -q` | Needs new tests |
| ENRICH-03 | all_cash does NOT infer through mixed consideration | unit | `python -m pytest tests/test_skill_enrich_core.py -q` | Needs new tests |
| ENRICH-03 | all_cash override flows through db-load to db-export | integration | `python -m pytest tests/test_skill_db_export.py -q` | Needs new tests |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_skill_enrich_core.py tests/test_skill_db_load.py tests/test_skill_db_export.py tests/test_skill_mirror_sync.py -q`
- **Per wave merge:** `python -m pytest -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] New test functions in `tests/test_skill_enrich_core.py` for DropTarget classification (positive, negative/directionality, sparse/empty)
- [ ] New test functions in `tests/test_skill_enrich_core.py` for all_cash inference (positive, negative/mixed, cycle-local)
- [ ] New test functions in `tests/test_skill_db_load.py` for loading dropout_classifications and all_cash_overrides from deterministic enrichment
- [ ] New test functions in `tests/test_skill_db_export.py` for all_cash override preference and DropTarget label in Note column
- [ ] New assertions in `tests/test_skill_mirror_sync.py` for round milestone, verbal indication, and NDA exclusion text in SKILL.md

## Live Data Analysis

### DropTarget Candidates Across 9 Deals

Based on round invitation data and drop events:

| Deal | Drop Event | drop_reason_text | Round Context | Likely Classification |
|------|-----------|-----------------|---------------|----------------------|
| stec evt_014 | "would not continue in the process" | Before formal round | Bidder-initiated (NOT DropTarget) |
| stec evt_019 | "Company H was not able to increase its indicated value range" | Before formal round | Bidder-initiated (NOT DropTarget) |
| stec evt_023 | "WDC was not prepared to move forward" | After formal round | Bidder-initiated (NOT DropTarget) |
| stec evt_024 | "Company D would not be in a position to actively conduct due diligence" | After formal round | Bidder-initiated (NOT DropTarget) |
| saks evt_014 | "Sponsor G was no longer participating" | After formal round, round invited HBC/Sponsor A/Sponsor E only | Possible DropTarget -- Sponsor G was active but not invited to final round |
| mac-gray evt_024 | "Party C did not submit a revised indication" | After informal round; round invited Party A/B/C/CSC | Not DropTarget (Party C was invited but did not respond) |
| providence-worcester evt_015 | "Party D indicated that it would not proceed" | After formal round; no invited_actor_ids populated | Bidder-initiated (NOT DropTarget) |
| penford evt_021 | "did not intend to move forward" | No round context | Bidder-initiated (NOT DropTarget) |
| zep evt_008 | "unable to proceed due to concerns regarding valuation" | No round context | Bidder-initiated (NOT DropTarget) |
| imprivata evt_014-024 | Various bidder-initiated | Various | All bidder-initiated (NOT DropTarget) |

**Key finding:** With the current extracted data, only saks evt_014 (Sponsor G) clearly fits the DropTarget pattern: Sponsor G was active but not invited to the formal round (round invited HBC, Sponsor A, Sponsor E). The `drop_reason_text` says "no longer participating" which is ambiguous on directionality, but the round invitation delta shows target exclusion.

Most other drops across the 9 deals have explicit bidder-withdrawal language in `drop_reason_text`, which D-07 says disqualifies them from DropTarget.

The DropTarget detection should therefore primarily rely on round invitation deltas (bidder active but not invited to next round) rather than `drop_reason_text` keywords, since most target exclusions in the corpus are implicit (committee narrows field) rather than explicitly stated.

### all_cash Inference Candidates

| Deal | Executed consideration | Proposal cash count | Should infer | Reason |
|------|----------------------|---------------------|-------------|--------|
| stec | null | 6/6 cash | Yes | All proposals explicitly cash |
| saks | null | 6/6 cash | Yes | All proposals explicitly cash |
| mac-gray | null | 12/13 cash (1 mixed?) | Investigate | Need to check the non-cash proposal |
| imprivata | null | 6/6 cash | Yes | All proposals explicitly cash |
| petsmart-inc | null | 4/4 cash | Yes | All proposals explicitly cash |
| penford | null | 1/7 cash, 6 null | Maybe | Only 1 explicit, but Ingredion bids were clearly cash |
| providence-worcester | null | 1/10 cash, 9 null | NO | Cash + CVR deal structure |
| medivation | N/A | 0 drops | N/A | No drop events |
| zep | N/A | Need to check | Need to check | |

**Key finding:** The all_cash inference is straightforward for deals where all typed proposals are "cash" (stec, saks, imprivata, petsmart-inc). For penford, the inference is trickier because most proposals lack explicit consideration_type -- but D-10 says fail-closed, so only propagate when unambiguous. providence-worcester is the critical guardrail case.

## Open Questions

1. **Providence & Worcester all_cash guardrail**
   - What we know: The deal includes cash + CVR. The executed event has null consideration_type. Only 1 of 10 proposals has explicit "cash" type.
   - What's unclear: Should the inference algorithm check for CVR mentions in event summaries/notes, or is the "not all proposals are cash" check sufficient?
   - Recommendation: The fail-closed rule from D-10 handles this: since only 1/10 proposals has explicit cash type, the inference will not fire (typed proposals are not unanimously cash). Add a specific regression test for this case.

2. **DuckDB ALTER TABLE for existing databases**
   - What we know: `CREATE TABLE IF NOT EXISTS` does not add new columns to existing tables. The `_query_enrichment()` function already handles optional columns dynamically.
   - What's unclear: Whether to use `ALTER TABLE ADD COLUMN IF NOT EXISTS` or rely on database recreation.
   - Recommendation: Add `ALTER TABLE enrichment ADD COLUMN IF NOT EXISTS all_cash_override BOOLEAN` to `_ensure_schema()` in db_schema.py. This is safe and additive. DuckDB supports this syntax.

## Project Constraints (from CLAUDE.md)

Directives that constrain implementation:

- **Filing text is the only factual source of truth** -- all enrichment must be filing-grounded
- **Fail fast on missing files, schema drift, contradictory state** -- no silent fallbacks
- **Deterministic enrichment writes auditable JSON** -- `deterministic_enrichment.json` must be reproducible
- **Do not mutate upstream extract artifacts** -- all_cash goes through enrichment, not extract rewrite
- **Python 3.11+ with explicit types on public functions** -- Pydantic-first schema style
- **Add focused regression tests for behavior changes** -- especially enrich-core gating
- **Commit guidance:** concise imperative subjects with conventional prefixes
- **Canonical skill docs under `.claude/skills/`** -- mirrors are derived artifacts
- **Benchmark materials forbidden until `db-export` completes** -- do not reference reconciliation data as generation input
- **`db-load` uses two-tier enrichment loading** -- deterministic first, optional interpretive overlay
- **`db-export` generates CSV from DuckDB, not JSON artifacts** -- the only filing-grounded export boundary

## Sources

### Primary (HIGH confidence)
- `skill_pipeline/enrich_core.py` -- full source read, function-by-function analysis
- `skill_pipeline/models.py` -- complete model inventory including DropoutClassification, BidClassification, SkillEnrichmentArtifact
- `skill_pipeline/db_schema.py` -- full DDL and schema analysis
- `skill_pipeline/db_load.py` -- enrichment loading logic with two-tier overlay pattern
- `skill_pipeline/db_export.py` -- all_cash derivation at line 303, dropout label at line 325
- `.claude/skills/extract-deal/SKILL.md` -- current extraction guidance baseline
- `.claude/skills/enrich-deal/SKILL.md` -- DropTarget directionality rules and dropout taxonomy
- `tests/test_skill_enrich_core.py` -- existing test patterns and fixtures
- `tests/test_skill_db_load.py` -- fixture patterns for db-load tests
- `tests/test_skill_db_export.py` -- export test patterns
- `.planning/phases/07-bid-type-rule-priority/HANDOFF.md` -- Phase 7 over-promotion bug status

### Secondary (MEDIUM confidence)
- `data/reconciliation_cross_deal_analysis.md` -- systematic differences motivating Phase 8
- Live deal artifacts (`data/skill/*/extract/events_raw.json`) -- drop events, consideration types, round invitations analyzed across all 9 deals

### Tertiary (LOW confidence)
- None -- all findings grounded in live code and artifact analysis

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, all changes within existing codebase patterns
- Architecture: HIGH -- clear patterns from prior phases (enrich_core extension, DB schema additions, two-tier enrichment)
- Pitfalls: HIGH -- identified from live data analysis and Phase 7 handoff document
- DropTarget detection: MEDIUM -- live data shows only 1 clear DropTarget candidate (saks evt_014); algorithm correctness depends on future re-extraction producing richer round invitation data
- all_cash inference: HIGH -- clear positive (stec/saks/imprivata/petsmart) and negative (providence-worcester) cases

**Research date:** 2026-03-30
**Valid until:** Stable -- no external dependencies or fast-moving libraries
