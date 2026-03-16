# segment-processes

## Design Principles

1. The filing is the single source of truth. Every fact traces to
   `source_accession_number` + verbatim `source_text`.
2. Fail closed on source ambiguity. Fail open on extraction incompleteness.
3. Facts before judgments. Proposals are raw events. Classification is
   Skill 8, not Skill 5.
4. Alex's collection instructions are the extraction spec. Used for
   methodology and taxonomy. Never as a factual source.
5. master.csv is the review artifact, not the estimation artifact.

## Overview

Identify deal cycles (terminated/restarted process boundaries), assign
events to cycles, and build round structure with invited sets within
each cycle. This is the first enrichment skill -- it adds structure to
the factual extraction layer without modifying it.

## Input

- `Data/deals/<slug>/extraction/events.jsonl` (from Skill 5)
- `Data/deals/<slug>/extraction/actors.jsonl` (from Skill 4)
- `Data/deals/<slug>/extraction/actors_extended.jsonl` (from Skill 5,
  if exists)

## Output

- `Data/deals/<slug>/enrichment/process_cycles.jsonl` (one JSON line
  per cycle, with rounds nested within)
- `Data/deals/<slug>/extraction/decisions.jsonl` (append to existing
  log -- MANDATORY for cycle_boundary decisions)

## Tools

| Tool | Purpose |
|------|---------|
| File read | Read events.jsonl, actors.jsonl, actors_extended.jsonl |
| File write | Write process_cycles.jsonl, append to decisions.jsonl |

## Procedure

### Step 1: Load Events and Actors

1. **Read `extraction/events.jsonl`** and sort by date.
2. **Read `extraction/actors.jsonl`** and `actors_extended.jsonl` (if
   exists) to get the full actor roster.

### Step 2: Identify Cycle Boundaries

1. **Scan events for `terminated` and `restarted` event types.** These
   mark cycle boundaries.
2. **Single-cycle deals (most deals):** If no `terminated` or
   `restarted` events exist, the deal has one cycle spanning from the
   first to the last event. Record it.
3. **Multi-cycle deals:** Each terminated process gets its own cycle
   with `status: "terminated"`. Events from the terminated cycle are
   assigned to that cycle, not the active one. A `restarted` event
   marks the beginning of the next cycle.
4. **For each boundary decision**, log to `decisions.jsonl` with
   `decision_type: "cycle_boundary"`, including the basis for the
   boundary placement and confidence level.

See `references/cycle-rules.md` for detailed segmentation rules.

### Step 3: Assign Events to Cycles

1. **For each event**, assign it to the appropriate cycle based on
   its date and the cycle boundaries.
2. **Events before the first `terminated`** belong to cycle 1.
3. **Events between `terminated` and `restarted`** are liminal --
   assign based on context. If ambiguous, flag `needs_review`.
4. **Events after the last `restarted`** belong to the final active
   cycle.

### Step 4: Build Round Structure

1. **Identify round announcement events** (`final_round_inf_ann`,
   `final_round_ann`, `final_round_ext_ann`) within each cycle.
2. **Pair each announcement with its deadline event** (matching type:
   `*_ann` maps to the corresponding non-`_ann` event type).
3. **Determine the invited set** for each round from the round
   announcement event's `source_text` and linked actors in
   `event_actor_links.jsonl`.
4. **Nest rounds within their parent cycle** in the output.

**IMPORTANT:** Rounds have NO `round_type` field. Formal/informal
classification lives on individual proposals in `judgments.jsonl`
(Skill 8), not on rounds. Do not add any round_type, formality, or
classification field to the round object.

### Step 5: Write Output

1. **Write `enrichment/process_cycles.jsonl`** -- one JSON line per
   cycle. See `references/cycle-rules.md` for full schema.
2. **Append to `extraction/decisions.jsonl`** for every cycle_boundary
   decision.

## Gate

At least 1 cycle in `enrichment/process_cycles.jsonl`.

## Failure Mode

**Fail open.** Uncertain cycle boundaries produce `needs_review` flags
on the affected cycle. The pipeline continues with best-effort
segmentation.

## Decision Log (MANDATORY)

Every cycle_boundary decision MUST be logged to
`extraction/decisions.jsonl`. Examples:

- Placing a cycle boundary at a `terminated` event when multiple
  termination signals exist.
- Deciding whether a "pause" in the process constitutes a true
  termination or just a delay.
- Assigning ambiguous events (between terminated and restarted) to
  a specific cycle.

## Required Reading

1. `references/cycle-rules.md` -- cycle segmentation rules, round
   structure requirements, process_cycles.jsonl full schema with
   examples
