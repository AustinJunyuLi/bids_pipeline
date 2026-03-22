# Codebase Review Request — bids-data-pipeline (Round 3)

**Commit:** 942b6e7 (2026-03-18)
**Files uploaded:** 9 consolidated files covering ~107 source files
**Prior rounds:** Round 2 (2026-03-18) — same commit, your Round 2 review evaluated below

## How to Read the Uploaded Files

| File | Contents |
|------|----------|
| 00_PROJECT_OVERVIEW.md | CLAUDE.md, AGENTS.md, git history, seeds.csv, config |
| 01_MODELS_AND_SCHEMAS.md | All Pydantic models + LLM output schemas |
| 02_PREPROCESSING.md | Raw EDGAR fetch, preprocess source, evidence scanning |
| 03_LLM_INFRASTRUCTURE.md | LLM backend protocol, providers, prompts, token budgeting |
| 04_EXTRACTION.md | CLI, actor/event extraction, chunk merging, recovery audit |
| 05_QA_ENRICH_EXPORT.md | QA span resolution, enrichment classification, CSV export |
| 06_TESTS.md | Key test files in full, rest summarized |
| 07_SKILLS_AND_ALEX.md | Skills vs pipeline separation, Alex's full collection instructions, Alex's hand-collected benchmark data |
| 08_ROUND2_ASSESSMENT_AND_AUDITS.md | **READ THIS FIRST** — Our independent assessment of your Round 2 recommendations + comprehensive agent audit findings with bugs |

**CRITICAL INSTRUCTIONS ON INTELLECTUAL HONESTY:**

I am a serious academic researcher. I need your **honest, independent judgment** — not agreement, not flattery, not validation. We are aiming for perfection. A single undetected error in this pipeline will contaminate a dataset destined for a top-3 finance journal.

1. **Do NOT open with compliments.** Go straight to substance.
2. **Do NOT agree with our assessment just because we presented it.** File 08 contains our independent evaluation of your Round 2 recommendations. We pushed back on several of your findings. **You are expected to push back on every one of our judgments if you believe we are wrong.** If we dismissed a valid concern of yours, say so and explain why we were wrong. If we accepted something we shouldn't have, tell us. We would rather have a harsh, correct design than a comfortable, flawed one.
3. **Challenge our assumptions ruthlessly.** If we ruled out an approach prematurely, say so. If our "bug findings" from the agent audits are actually working-as-intended, tell us. If our prioritization is wrong, reorder it. Nothing in file 08 is sacred.
4. **Distinguish your confidence levels explicitly.** "I am confident that X" vs "I suspect Y but haven't verified" vs "Z is speculative." Do not present uncertain claims with false confidence.
5. **Prioritize correctness over our feelings.** A polite "your assessment is wrong at point 3" is infinitely more valuable than diplomatic agreement that lets an error survive into the implementation plan.
6. **If you and we disagree, DO NOT silently concede.** State the disagreement, present your evidence, and let the stronger argument win. We will implement whatever survives this adversarial process — yours or ours.

**CRITICAL INSTRUCTIONS ON VERBOSITY AND DETAIL:**

This is a rigorous academic research project. Your response must be **exhaustive, meticulous, and complete**. Specifically:

1. **Do NOT abbreviate.** Do not say "the rest is analogous" or "remains unchanged" without providing a complete justification showing WHY.
2. **Do NOT provide sketches.** Provide complete specifications with every detail shown.
3. **Do NOT summarize.** If a schema needs changes, provide the complete Pydantic model, not a description.
4. **Show ALL reasoning.** Every design decision, every trade-off, every edge case.
5. **Your response should be VERY LONG.** A short response means you have abbreviated something. We expect and want a long, detailed response.
6. **For schema changes:** Provide complete Pydantic class definitions ready to paste.
7. **For new modules:** Provide complete function signatures, docstrings, and control flow.
8. **Verify your own work.** After specifying a change, trace through the end-to-end pipeline to confirm it doesn't break anything.

The cost of verbosity is zero. The cost of a gap in a design doc is weeks of wasted implementation time. Err on the side of too much detail, never too little.

## CRITICAL FRAMING: Two Separate Systems

**You MUST keep these clearly separated in your analysis.**

### System 1: The Deterministic Pipeline (production code)

This is `pipeline/` — Python code that runs via CLI commands. It produces the FINAL dataset for the academic paper. Files 00-06 contain this code.

```
Stage 1: raw fetch           DETERMINISTIC  (EDGAR API)
Stage 2: preprocess source   DETERMINISTIC  (regex evidence scanning)
Stage 3A: extract actors     LLM            (structured output → JSON)
Stage 3B: extract events     LLM            (structured output → JSON)
Stage 4: QA / span resolve   DETERMINISTIC  (substring matching, dedup)
Stage 5: enrich              DETERMINISTIC  (7 priority rules, cycles)
Stage 6: export              DETERMINISTIC  (CSV denormalization)
Stage 7: validate            DETERMINISTIC  (reference metrics)
```

### System 2: The Deal-Agent Skills (facilitating tool)

Prompt instructions for Claude Code subagents. File 07. Development aid, not production.

## Context: What Happened in Round 2

In Round 2, you provided an exhaustive assessment of the pipeline against Alex Gorbenko's requirements. We independently evaluated every recommendation with Claude Opus + 4 specialized audit agents that read every line of source code. Our assessment is in file 08.

**Key areas of agreement:**
- Initiation judgment needs to be promoted to System 1 (Stage 5 LLM call)
- `advised_actor_id` on `ActorRecord` is a real schema gap
- NDA aggregation is a formatting-only gap in `alex_compat.py`
- `invited_actor_ids` on `RoundEvent` is needed for Rule F2 selectivity
- N=9 is a calibration set, not a validation set — holdout needed
- Frozen inference log for reproducibility
- Cycle segmentation's 180-day rule is sound

**Key areas of disagreement:**
- Your claim that `prompted_json` causes HTTP 400 errors due to "assistant prefilling" is **factually incorrect** — the pipeline uses system prompt injection, not assistant prefilling, and already supports `provider_native` mode
- Your "catastrophically flawed" dropout classification framing is overblown — the LLM reads the same narrative text Alex reads, and the subtypes are textual patterns, not quantitative judgments
- "Delete chunking" is wrong because the real constraint is output tokens, not input tokens — and most deals don't trigger chunking anyway
- N-run protocol is premature before proving single-shot works on the 9 reference deals

**Critical bugs our agents found:**
1. `events.py` line 73: enum-vs-string comparison means chunking ALWAYS activates (every deal gets chunked regardless of complexity)
2. `backend.py`: missing `import json` — latent crash
3. `state.py`: `review_items` table has no `run_id` column — global instead of per-run counts
4. `qa/review.py`: enum-vs-string severity comparison silently fails
5. `features.py`: `peak_active_bidders` never removes actors and counts non-bidders
6. `classify.py`: `last_round_event` carries across cycle boundaries

See file 08 for the complete list of 23 findings.

---

## Your Task (Round 3): Design the Augmented Pipeline + Write the Implementation Plan

We have now completed the diagnostic phase. We know:
- Exactly what the pipeline does (files 00-06)
- Exactly what Alex requires (file 07)
- Where the gaps are between them (your Round 2 + our assessment in file 08)
- Where the bugs are (agent audits in file 08)

**We need you to produce TWO deliverables:**

### Deliverable 1: Complete Pipeline Design

Produce a **complete architectural specification** that a developer can implement from. You have full freedom to reshape the pipeline as you see fit — merge stages, split stages, add stages, change the LLM/deterministic boundary, restructure models, introduce new patterns. Whatever you believe produces the best system for this research goal.

Your design must cover at minimum:

**(a) Pipeline Topology** — If you're keeping the current 7-stage DAG, say so and why. If you're changing it, show the new topology with stage boundaries, inputs, outputs, and the LLM vs deterministic split for each stage.

**(b) Schema Changes — Complete Pydantic Models** — For every model that changes or is new, provide the COMPLETE Pydantic class definition (not a diff). Include all fields, types, defaults, validators, `model_config`, and imports. We listed candidates in file 08 (`ActorRecord`, `RoundEvent`, `FormalitySignals`, `DealEnrichment`, LLM schemas, etc.) but you may add, remove, or restructure these as you see fit.

**(c) New and Modified Modules** — For every new module, provide: purpose, complete function signatures with types, control flow, error handling policy, input/output artifacts, and test requirements. For every modified module, specify: which functions change, the before/after logic, and edge cases. You decide which modules need creation or modification based on your design.

**(d) Classification Cascade** — Provide the COMPLETE formal/informal classification rules in priority order. If you believe the current cascade is wrong, replace it entirely.

**(e) Validation Framework** — Design the framework for comparing pipeline output against Alex's benchmark data (file 07). Cover matching algorithm, error categorization, metrics, handling of Alex's fractional bidderIDs and "rough" dates, and output format.

**(f) Export Specification** — Provide the complete column spec for `alex_compat.csv` with mappings from pipeline models to each column.

### Deliverable 2: Ultra-Meticulous Implementation Plan

After the design is complete, produce an implementation plan that a developer can follow step by step.

**Requirements for the plan:**

1. **Ordered by dependency.** If module B depends on module A's changes, A comes first.

2. **Each step must be atomic and testable.** After completing each step:
   - All existing tests still pass
   - The new test(s) for that step pass
   - The pipeline can still run end-to-end (even if some features are stubs)

3. **For each step, specify:**
   - Which file(s) to modify or create
   - What the change does (in one sentence)
   - What test(s) to add or modify
   - The command to verify: `pytest tests/test_X.py::test_Y -v`
   - Dependencies on prior steps
   - Estimated complexity: trivial / small / medium / large

4. **Group into phases.** You define the phases based on your design. Our file 08 suggested 6 phases but you should restructure if your design calls for a different decomposition.

5. **For Phase 5, specify:**
   - The exact CLI commands to run for each deal
   - What output to check
   - What constitutes "pass" vs "fail" for the integration test

6. **Total step count should be 30-60 steps.** Fewer means steps are too large to be atomic. More means too granular.

## HARD CONSTRAINT: Search for Current State of the Art

**Before answering, you MUST actively search the web for the latest developments as of March 2026.** Do not rely solely on your training data.

Specifically, search for and incorporate:

1. **Current Anthropic API for structured outputs** — verify whether `prompted_json` with system prompt injection still works with Claude 4.6, or whether `output_config.format` is now required. We believe `prompted_json` works fine but want your independent verification.

2. **Current OpenAI API for GPT-5.4** — verify `reasoning_effort` parameter behavior and whether `max_completion_tokens` is still shared between reasoning and output.

3. **Wang & Wang (arXiv:2503.16974)** — verify this paper exists and its actual recommendations for N-run aggregation.

4. **Any new papers on LLM-assisted structured data extraction from legal/financial documents (2025-2026).**

Your design recommendations must reflect actual March 2026 capabilities. Do not recommend features that don't exist.

## Scope of Architectural Freedom

You have **full architectural freedom**. Nothing is sacred — not the 7-stage topology, not the current module boundaries, not our prioritized roadmap in file 08. If you believe the pipeline needs a fundamental reshape — merging stages, splitting stages, adding stages, reordering the DAG, changing the LLM/deterministic boundary, restructuring the model hierarchy, introducing new architectural patterns — do it and justify it.

Our file 08 roadmap is our best current thinking. If it's wrong, replace it. If the phasing is wrong, reorder it. If we're missing something critical, add it. If we're including something unnecessary, cut it.

The only hard constraints are:
- Filing `.txt` files under `raw/` remain immutable truth sources
- The final dataset must be deterministically reproducible from frozen inference logs
- Every extracted fact must trace to `source_accession_number` + verbatim `source_text`
- The output must match Alex Gorbenko's collection methodology (file 07)
- The system must be implementable by one developer in Python 3.11+

## What Success Looks Like

After implementing your plan:
1. All existing tests pass
2. All new tests pass
3. `pipeline extract actors/events --deal imprivata` succeeds with the augmented schemas
4. `pipeline qa --deal imprivata` resolves all spans including new fields
5. `pipeline enrich --deal imprivata` produces initiation judgment + updated classification
6. `pipeline export --deal imprivata` produces `alex_compat.csv` with all 47 columns correctly populated
7. A comparison against Alex's benchmark data for all 9 deals shows zero fatal omissions and MAPE < 5% on bid values

---
_Internal: snapshot_sha=942b6e7, round=3, date=2026-03-18, prior_round=diagnosis/deepthink/2026-03-18/round_2_
