# Plan: Three-Layer Fix for Gates-v2 Failures

**Status:** DRAFT  
**Date:** 2026-04-02

## Context

37 gates-v2 blockers across 7 deals (imprivata, mac-gray, medivation, petsmart-inc, saks, stec, zep) block the pipeline at the semantic gates stage. Two root causes:

1. **Forward `requested_by_observation_id`** (35 blockers, 6 deals): Proposals link to solicitations that occur AFTER them — up to 128 days forward. The LLM confuses "belongs to the same process" with "responds to this specific solicitation."
2. **Missing bidder actor on outcomes** (2 blockers, 2 deals): Executed/restarted outcomes name the bidder in summary text but omit them from structured `subject_refs`/`counterparty_refs`.

The prompt already states the rules correctly in 3 places, but the LLM ignores them ~17% of the time. Canonicalization passes the bad data through untouched. Gates catches it but can only block, not fix.

The user wants the most fundamental fix: improve all three layers (prompt, canonicalization, extraction) and re-run all 7 deals.

## Approach

Three layers, in order:

### Layer 1: Prompt Improvements (3 files)

**1a. `skill_pipeline/prompt_assets/observations_v2_prefix.md`**

Add two visually prominent CRITICAL RULE blocks after the ground rules list. The current rules are buried in a flat bullet list at lines 9 and 11. Restructure:

- Keep existing ground rules
- Add `CRITICAL — TEMPORAL ORDER` block explaining: `requested_by_observation_id` must be null unless a solicitation with date <= proposal date exists. "Same process" is NOT sufficient — only a direct temporal predecessor qualifies. Common mistake: linking all proposals to the final-round solicitation.
- Add `CRITICAL — OUTCOME ACTOR` block explaining: executed/restarted outcomes must include the bidder party_id or cohort_id in refs. If the summary names an actor, it must appear in structured refs.

**1b. `skill_pipeline/prompt_assets/observations_v2_examples.md`**

Add concrete JSON examples after existing type-mapping bullets:

- CORRECT: solicitation dated March 2, proposal dated March 8, `requested_by_observation_id` set
- CORRECT: unsolicited proposal, `requested_by_observation_id: null`
- WRONG (marked): proposal dated March 1 linking to solicitation dated June 24
- CORRECT: executed outcome with bidder in `subject_refs`

Keep all existing examples intact.

**1c. `skill_pipeline/compose_prompts.py` (lines 131-153)**

Insert two delimited constraint blocks near the top of `task_instructions` (after the quote-before-extract protocol, before general observation rules):

```
--- TEMPORAL ORDER CONSTRAINT ---
requested_by_observation_id links a proposal to the solicitation that prompted it.
RULE: The linked solicitation MUST have date <= proposal date.
If no solicitation occurred on or before the proposal date, set to null.
Common mistake: linking all proposals to the final-round solicitation.
--- END TEMPORAL ORDER CONSTRAINT ---

--- OUTCOME ACTOR CONSTRAINT ---
executed/restarted outcomes must include bidder party_id or cohort_id in refs.
If the summary names the actor, their party_id MUST appear in subject_refs or counterparty_refs.
--- END OUTCOME ACTOR CONSTRAINT ---
```

### Layer 2: Canonicalization Enforcement (1 file + tests)

**2a. `skill_pipeline/canonicalize.py`**

Add two repair functions called between `_upgrade_raw_observation_artifact_v2()` and `ObservationArtifactV2.model_validate()`:

```python
observations_dict = _upgrade_raw_observation_artifact_v2(...)
observations_dict = _repair_forward_requested_by(observations_dict)    # NEW
observations_dict = _repair_outcome_bidder_refs(observations_dict)     # NEW
canonical_observations = ObservationArtifactV2.model_validate(observations_dict)
```

Also apply in the `else` branch (canonical re-load path at line 171) for idempotency.

**`_repair_forward_requested_by(observations_dict) -> dict`:**
1. Build date index from `observation.date.sort_date` for all observations
2. For each proposal with `requested_by_observation_id` set:
   - Look up the linked observation
   - If linked observation is not a solicitation, or solicitation date > proposal date: set to `null`
3. Return modified dict

Uses same date parsing logic as `gates_v2._parse_date()` (read `sort_date` from the date dict).

**`_repair_outcome_bidder_refs(observations_dict) -> dict`:**
1. Build party name index: map lowercased `display_name`, `canonical_name`, aliases → `party_id` for all parties with `role == "bidder"`
2. Build cohort index: all cohort_ids
3. For each outcome with `outcome_kind in {"executed", "restarted"}`:
   - Check if any bidder party_id or cohort_id exists in `subject_refs + counterparty_refs`
   - If not: scan `summary` text for exact matches against bidder party names
   - If matches found: add matched party_ids to `subject_refs`
   - If no matches: leave unchanged (cannot invent information)
4. Return modified dict

Both functions log each repair action for auditability.

**2b. `tests/test_skill_canonicalize_v2.py`**

Add 5 new test cases using the existing fixture pattern:

1. `test_forward_requested_by_nullified` — proposal at March 31, solicitation at April 15 → link nullified
2. `test_valid_requested_by_preserved` — solicitation at March 15, proposal at March 31 → link kept
3. `test_outcome_bidder_refs_repaired` — executed outcome with empty refs, "Bidder A" in summary → `subject_refs` populated
4. `test_outcome_bidder_refs_already_present` — bidder already in refs → no change
5. `test_outcome_no_false_positive` — summary doesn't name any bidder → refs stay empty

### Layer 3: Re-extraction and Full Pipeline Rerun

After Layers 1-2 are implemented and tests pass:

1. `python -m pytest -q` — full test suite
2. Re-compose prompts for all 7 failing deals
3. `/extract-deal-v2` for all 7 deals (fresh LLM extraction with improved prompts)
4. Full deterministic pipeline tail: canonicalize → check → coverage → gates → derive → db-load → db-export
5. Verify all 7 deals show 0 gates blockers
6. Regression check: re-compose + canonicalize + gates for penford and providence-worcester (must still pass)

## Files to Modify

| File | Change |
|------|--------|
| `skill_pipeline/prompt_assets/observations_v2_prefix.md` | Add CRITICAL RULE blocks |
| `skill_pipeline/prompt_assets/observations_v2_examples.md` | Add JSON examples |
| `skill_pipeline/compose_prompts.py` | Add constraint blocks in task_instructions |
| `skill_pipeline/canonicalize.py` | Add `_repair_forward_requested_by()` and `_repair_outcome_bidder_refs()` |
| `tests/test_skill_canonicalize_v2.py` | Add 5 repair test cases |

## Verification

1. All existing tests pass (`python -m pytest -q`)
2. New canonicalize repair tests pass
3. All 9 deals clear gates-v2 with 0 blockers
4. penford and providence-worcester do not regress
5. Exported CSVs generated for all 9 deals

## Risks

- **Prompt changes may over-correct**: LLM might null out `requested_by_observation_id` even when a valid prior solicitation exists. Mitigated by Layer 2 only nullifying forward refs, not fixing false nullification.
- **Bidder name matching is heuristic**: Exact string matching against summary text. Conservative — only matches known party names. Will not catch cases where the summary uses a name variant not in the aliases list.
- **Prompt token budget**: Adding ~30 lines to examples. Current examples are 28 lines. Modest increase, unlikely to impact chunking.
