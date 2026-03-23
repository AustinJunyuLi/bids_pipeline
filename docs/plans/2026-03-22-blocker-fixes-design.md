# Blocker Fixes for Pipeline Consolidation

Date: 2026-03-22
Status: Approved

## Context

Production code review of the pipeline-consolidation branch identified 4
blockers that must be fixed before any live deal run. All 129 tests pass. The
architecture, schemas, and deterministic stages are clean. The blockers are
concentrated in two areas: the orchestrator (`run.py`) and the LLM backend
(`llm.py` + `repair.py`).

## Fix 1: Orchestrator gates on stage return codes

### Problem

`run_deal()` in `stages/run.py` calls every stage and discards return values.
A deal with unresolved quotes or structural blockers slides all the way to the
final CSV with zero warning.  `run_repair` raises `RuntimeError` on
non-repairable errors, which propagates as an unhandled traceback.

### Design

After each QA stage (check, verify, coverage, omission-audit), inspect the
return code:

- Stages 1-2 (extract, materialize): raise on failure — let exceptions
  propagate naturally.
- Stages 3-6 (check, verify, coverage, omission-audit): return 0 (pass) or
  1 (errors found). If any returns non-zero, print the failure, skip
  remaining QA stages, and jump to repair.
- Stage 7 (repair): wrap in try/except RuntimeError. On failure, print the
  error message and return 1.
- Stages 8-10 (enrich-core, enrich-interpret, export): gate sequentially.
  If enrich fails, do not export.

Print pass/fail after every stage:

```
[1/10] Extracting actors and events... done
[2/10] Materializing canonical artifacts... done
[3/10] Running structural checks... PASS
[4/10] Running quote verification... FAIL (errors found)
       → Entering repair loop
[7/10] Running repair loop... PASS
[8/10] Running deterministic enrichment... done
[9/10] Running interpretive enrichment... done
[10/10] Exporting CSV... done
Pipeline complete for stec.
```

### Files changed

- `skill_pipeline/stages/run.py`
- `tests/test_skill_run.py`

## Fix 2: Truncation detection in LLM backend

### Problem

If the API truncates a response (finish_reason='length'), the JSON is
incomplete. The current code sees a JSONDecodeError, retries, and reports
"failed validation after retry" — hiding the real cause.

### Design

After each `_create_completion` call, before parsing the response content,
check `response.choices[0].finish_reason`. If it equals `"length"`, raise
immediately with a clear message. Do not retry — the retry will also
truncate.

This fix does NOT impose any token budget. The `invoke_structured` function
continues to default `max_output_tokens=None`, which means no
`max_completion_tokens` is sent to the API. The API uses the model's
maximum output length. This is intentional: the user has unlimited token
access and optimizes for quality, not cost.

The truncation check is purely defensive: if the API ever truncates for any
reason (proxy hiccup, model-side limit, upstream outage), the error message
will say exactly what happened instead of a cryptic validation failure.

### Files changed

- `skill_pipeline/core/llm.py` (two sites: lines ~158 and ~187)
- `tests/test_skill_llm.py` (add truncation test)

## Fix 3: Repair uses rendered blocks instead of raw JSONL

### Problem

`_load_filing_context` in `repair.py` reads `chronology_blocks.jsonl` as raw
text. The LLM receives machine-readable JSONL metadata instead of
human-readable filing text. Extract and omission-audit both use
`_render_blocks()` to show clean formatted text — repair should too.

### Design

Replace `_load_filing_context(paths.chronology_blocks_path)` with:

1. Load blocks as `ChronologyBlock` objects from the JSONL file.
2. Render them using `_render_blocks()` from `core/prompts.py` (or a shared
   helper factored from there).

The `_load_filing_context` function is removed. The `_render_blocks`
helper already exists in `core/prompts.py` — make it importable (rename
from private `_render_blocks` to public `render_blocks`).

### Files changed

- `skill_pipeline/stages/qa/repair.py`
- `skill_pipeline/core/prompts.py` (make `render_blocks` public)
- `tests/test_skill_repair.py`

## Fix 4: Remove omission-audit from repair loop

### Problem

After each repair round, `run_omission_audit` is called — an LLM call.
This doubles LLM cost per repair round. If omission-audit finds new
error-level findings after repair, the loop can chase its own tail.

### Design

Remove the `run_omission_audit(deal_slug, project_root=project_root)` call
from the repair loop (line 164 of `repair.py`). The repair loop after each
round re-runs only deterministic stages:

- `run_materialize`
- `run_check`
- `run_verify`
- `run_coverage`

Omission-audit runs once at step 6 in the orchestrator. Its findings feed
into the first repair round via `_load_all_findings`, which reads
`omission_findings.json` from disk. After repair, the omission findings
file is stale but not re-evaluated — the deterministic coverage audit
catches any remaining gaps.

Also remove `_load_findings(paths.omission_findings_path, source="omission")`
from `_load_all_findings` on subsequent rounds? No — keep reading the
initial omission findings. They are still valid for the first round. On the
second round, if the first repair resolved them, the corresponding records
will pass verification and coverage, and the omission findings will be
stale but harmless (repair only acts on findings with matching failing
records).

### Files changed

- `skill_pipeline/stages/qa/repair.py` (remove line 164)
- `tests/test_skill_repair.py` (update loop expectations)

## Non-changes (explicitly preserved)

- `max_output_tokens` defaults to `None` (no cap). Not changed.
- `reasoning_effort` defaults to env var `NEWAPI_REASONING_EFFORT=xhigh`.
  Not changed.
- `service_tier` defaults to env var `NEWAPI_SERVICE_TIER=priority`.
  Not changed.
- The stale impl plan doc (`2026-03-22-pipeline-consolidation-impl.md`)
  proposes `max_output_tokens: int = 16_000` and
  `reasoning_effort: str = "none"`. These were never implemented and
  contradict the production policy. They remain as historical notes only.
