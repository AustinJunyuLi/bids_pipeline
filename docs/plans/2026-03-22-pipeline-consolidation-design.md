# Pipeline Consolidation Design

> Historical note: this is an implementation-era design record. The live production contract is in `CLAUDE.md`, and the final runtime deleted migration-only surfaces such as `deal-agent`, `source-discover`, `canonicalize`, and their old path aliases.

**Date:** 2026-03-22
**Status:** Approved
**Goal:** Consolidate all production pipeline stages into deterministic Python
modules within `skill_pipeline/`, replacing the hybrid agent+CLI workflow with
`skill-pipeline run --deal <slug>` for production execution while keeping
benchmark reconciliation as a standalone post-production script.

## Motivation

The current hybrid workflow splits execution between 4 agent skills
(`/extract-deal`, `/verify-extraction`, `/enrich-deal`, `/export-csv`) and 5
deterministic CLI stages. Agent skills introduce instability: non-deterministic
orchestration, varying interpretation across sessions, no automated testing of
skill behavior, and manual stage chaining. Consolidation eliminates these by
encoding all logic as Python code with programmatic LLM calls via API.

## Architecture

```
raw/<slug>/filings/*.txt                    (frozen truth)
data/deals/<slug>/source/                   (preprocessed source bundle)
    |
skill-pipeline run --deal <slug>
    |
    +-- 1. extract           [LLM]   -> extract/actors_raw.json, events_raw.json
    +-- 2. materialize       [det]   -> materialize/actors.json, events.json, spans.json
    +-- 3. check             [det]   -> check/check_report.json                    [gate]
    +-- 4. verify            [det]   -> verify/verification_findings.json
    +-- 5. coverage          [det]   -> coverage/coverage_findings.json
    +-- 6. omission-audit    [LLM]   -> coverage/omission_findings.json
    +-- 7. repair            [LLM]   -> patches extract/ raw artifacts (max 2 rounds)
    |      each round: re-run 2-5 (deterministic), gate on blockers
    +-- 8. enrich-core       [det]   -> enrich/deterministic_enrichment.json
    +-- 9. enrich-interpret  [LLM]   -> enrich/enrichment.json
    +-- 10. export           [det]   -> export/deal_events.csv

post-production only:
python scripts/reconcile_alex.py --deal <slug>
    -> reconcile/alex_rows.json, reconcile/reconciliation_report.json
```

### Key architectural decisions

1. **Repair edits pre-materialized (raw) artifacts, not canonical.** The LLM
   speaks raw schema (evidence_refs, DateHint). Materialize deterministically
   converts raw -> canonical (evidence_span_ids, ResolvedDate, spans). This
   makes materialize a pure, rerunnable function: same raw input -> same
   canonical output. Repair patches `extract/` raw artifacts; re-materialize
   produces fresh canonical artifacts from the patched raw.

2. **Materialize replaces canonicalize.** Same operations (span resolution, date
   normalization, dedup, NDA-gate, unnamed-party recovery), new name. The old
   name carried baggage from the deleted canonical `pipeline/` package.
   `canonicalize.py` is renamed to `materialize.py`. Output directory changes
   from `canonicalize/` to `materialize/`. Canonical artifacts move from
   `extract/` to `materialize/` (raw artifacts stay in `extract/`, preserved).

3. **Omission-audit runs once before repair.** Deterministic coverage catches
   regex-matched cues. Omission-audit adds an LLM layer for semantic gaps that
   regex misses. Both feed findings into repair. Post-repair re-runs are
   deterministic only (materialize + check + verify + coverage). No re-run of
   omission-audit inside the repair loop.

4. **Single LLM provider.** GPT-5.4 via NewAPI (OpenAI-compatible proxy). One
   `invoke_structured()` function wrapping the OpenAI SDK. No provider
   abstraction. Prompted JSON mode (schema in system prompt). Temperature 0.0,
   with backend defaults controlled by `NEWAPI_*` environment variables.

## LLM Backend

### Module: `skill_pipeline/llm.py`

Thin wrapper around the OpenAI Python SDK:

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["NEWAPI_API_KEY"],
    base_url=os.environ.get("NEWAPI_BASE_URL", "https://www.linkflow.run/v1"),
)

def invoke_structured(
    system_prompt: str,
    user_message: str,
    output_model: type[BaseModel],
    *,
    model: str = "gpt-5.4",
    max_output_tokens: int | None = None,
    temperature: float = 0.0,
    reasoning_effort: str | None = None,
) -> T:
    """Send prompt, parse JSON, validate against Pydantic model.

    Retry once on validation failure with error feedback.
    Raises on second failure.
    """
```

### Environment variables

```
NEWAPI_API_KEY         -- required
NEWAPI_BASE_URL        -- default: https://www.linkflow.run/v1
NEWAPI_MODEL           -- default: gpt-5.4
NEWAPI_REASONING_EFFORT -- default from environment (current local default: xhigh)
NEWAPI_SERVICE_TIER    -- default from environment (current local default: priority)
EDGAR_IDENTITY         -- required for raw-fetch (unchanged)
```

## New Python Modules

### `skill_pipeline/extract.py`

Replaces `/extract-deal` skill. Two-pass forward scan of the filing.

**Pass 1 -- Actors + Events:**
- Reads chronology_blocks.jsonl + evidence_items.jsonl
- Constructs user message with deal seed context + full chronology + evidence
- System prompt encodes 20-event taxonomy, actor roles, evidence_ref format,
  formality signals, MoneyTerms schema
- Two LLM calls: one for actors (RawSkillActorsArtifact), one for events
  (RawSkillEventsArtifact, with actor roster as context)

**Pass 2 -- Gap re-read:**
- Sweeps all 20 event types, records extracted vs NOT FOUND
- Re-reads source for missed NDAs, drops, process initiation
- Populates coverage_notes

**Group-range bids:** Prompt explicitly handles "N parties submitted in range
X-Y" -> creates N placeholder proposal events with range_low=X, range_high=Y.

**Output:** `extract/actors_raw.json`, `extract/events_raw.json` (raw schema,
never overwritten by materialize)

### `skill_pipeline/materialize.py`

Renamed from `canonicalize.py`. Same operations, new output location.

**Input:** `extract/actors_raw.json`, `extract/events_raw.json` (raw schema)
**Output:** `materialize/actors.json`, `materialize/events.json`,
`materialize/spans.json`, `materialize/materialize_log.json`

Operations:
1. Resolve evidence_refs -> evidence_span_ids via text span resolution
2. Convert DateHint -> ResolvedDate with anchor chaining
3. Deduplicate events by (type, normalized date, actor_ids)
4. Gate drops by NDA (remove drops for actors without prior NDA)
5. Recover unnamed parties from count_assertion gaps

Raw artifacts in `extract/` are never modified. Materialize reads them and
writes canonical artifacts to a separate directory. This makes materialize
idempotent and safely rerunnable after repair.

### `skill_pipeline/omission_audit.py`

New stage. Semantic coverage gap detection via LLM.

- Reads coverage_findings.json + uncovered chronology blocks + evidence items
- Sends uncovered source regions to LLM: "Are any of these regions describing
  M&A events that should have been extracted?"
- LLM returns structured findings with event type, evidence location,
  confidence

**Output:** `coverage/omission_findings.json`

### `skill_pipeline/repair.py`

Replaces `/verify-extraction` skill. LLM-driven repair loop.

- Reads verification_findings.json + coverage_findings.json +
  omission_findings.json
- Gate: if any error-level finding is non_repairable, fail closed
- Constructs prompt with: failing records, evidence context, surrounding filing
  text (+/-5 lines around each failing span)
- LLM returns structured patches: updated evidence_refs, new actor/event
  records
- Applies patches to `extract/actors_raw.json` and `extract/events_raw.json`
- Re-runs materialize -> check -> verify -> coverage (deterministic only)
- Max 2 rounds. If errors remain after round 2, pipeline fails

**Output:** Patched `extract/` artifacts + `repair/repair_log.json`

### `skill_pipeline/enrich_interpret.py`

Replaces `/enrich-deal` skill. Four interpretive LLM tasks:

1. **Dropout classification** -- compare drop context against prior proposals,
   classify as Drop/DropBelowM/DropBelowInf/DropAtInf/DropTarget
2. **Initiation judgment** -- read earliest events + narrative, classify as
   target_driven/bidder_driven/activist_driven/mixed with confidence
3. **Advisory verification** -- confirm advised_actor_id matches filing text
4. **Count reconciliation** -- compare count_assertions against extracted
   counts, classify gaps

Reads canonical artifacts from `materialize/` + deterministic_enrichment.json +
filing text. Each task is a separate LLM call with a focused prompt.

**Output:** `enrich/enrichment.json` (merges deterministic + interpretive)

### `skill_pipeline/export.py`

Replaces `/export-csv` skill. Pure deterministic formatting.

- Reads canonical actors/events from `materialize/` + enrichment.json +
  seeds.csv
- Maps to 14-column CSV per Alex's schema
- BidderID: 5-step sequential algorithm (fractional pre-NDA, integer post-NDA)
- Bidder type: 11-priority composition from actor fields, only on first row
- Date format: MM/DD/YYYY to match Alex's explicit instruction
- Same-date sort order: process markers -> IB -> NDA -> round announcements ->
  drops -> round deadlines -> proposals -> outcomes

**Enterprise-value bids:** When per_share is null but enterprise_value exists,
output enterprise_value in c1 comment + add `enterprise_value_only:evt_XXX` to
review_flags.

**Output:** `export/deal_events.csv`

### `scripts/reconcile_alex.py`

Post-export benchmark QA. Read-only diagnostic.

- Extracts Alex's rows from example/deal_details_Alex_2026.xlsx
- Compares pipeline events to Alex rows by family, date, actor
- Arbitrates disagreements against filing text
- Writes reconciliation_report.json with verdicts

**Output:** `reconcile/reconciliation_report.json`
**Status:** clean / attention / high_attention (informational, never gates)

### `skill_pipeline/run.py`

End-to-end orchestrator. Executes production stages 1-10 in sequence.

```python
def run_deal(deal_slug: str, *, project_root: Path) -> int:
    """Run all pipeline stages for a deal. Returns 0 on success, 1 on failure."""
```

Gates:
- After check (step 3): fail on blockers
- After repair round re-check (step 7): fail on blockers
- After repair round re-verify (step 7): fail on non_repairable errors

Each stage logs its status. Pipeline stops on first gate failure with clear
error message indicating which stage failed and why.

## Artifact Directory Layout

After consolidation, `data/skill/<slug>/` contains:

| Directory | Stage | Contents |
|-----------|-------|----------|
| `extract/` | extract | `actors_raw.json`, `events_raw.json` (raw schema, preserved) |
| `materialize/` | materialize | `actors.json`, `events.json`, `spans.json`, `materialize_log.json` |
| `check/` | check | `check_report.json` |
| `verify/` | verify | `verification_findings.json`, `verification_log.json` |
| `coverage/` | coverage | `coverage_findings.json`, `coverage_summary.json`, `omission_findings.json` |
| `repair/` | repair | `repair_log.json` |
| `enrich/` | enrich-core + enrich-interpret | `deterministic_enrichment.json`, `enrichment.json` |
| `export/` | export | `deal_events.csv` |
| `reconcile/` | standalone post-production reconcile | `alex_rows.json`, `reconciliation_report.json` |

## Updated CLI

```
skill-pipeline run --deal <slug>              # end-to-end
skill-pipeline extract --deal <slug>          # LLM extraction only
skill-pipeline materialize --deal <slug>      # renamed from canonicalize
skill-pipeline check --deal <slug>            # existing
skill-pipeline verify --deal <slug>           # existing
skill-pipeline coverage --deal <slug>         # existing
skill-pipeline omission-audit --deal <slug>   # LLM coverage gaps
skill-pipeline repair --deal <slug>           # LLM repair loop
skill-pipeline enrich-core --deal <slug>      # existing
skill-pipeline enrich-interpret --deal <slug> # LLM interpretive enrichment
skill-pipeline export --deal <slug>           # deterministic CSV
skill-pipeline deal-agent --deal <slug>       # existing preflight/summary
skill-pipeline raw-fetch --deal <slug>        # existing
skill-pipeline preprocess-source --deal <slug> # existing
python scripts/reconcile_alex.py --deal <slug> # post-production benchmark QA
```

## Testing Strategy

### New test files

| Module | Test File | Approach |
|--------|-----------|----------|
| `llm.py` | `test_skill_llm.py` | Mock OpenAI client |
| `extract.py` | `test_skill_extract.py` | Mock LLM responses |
| `repair.py` | `test_skill_repair.py` | Mock LLM, verify fail-closed + patch logic |
| `enrich_interpret.py` | `test_skill_enrich_interpret.py` | Mock LLM responses |
| `export.py` | `test_skill_export.py` | Pure deterministic, no mocks |
| `omission_audit.py` | `test_skill_omission_audit.py` | Mock LLM responses |
| `run.py` | `test_skill_run.py` | Mock all LLM calls, end-to-end on synthetic fixtures |

### Updated test files

- `test_skill_canonicalize.py` -> `test_skill_materialize.py` (rename + update imports)
- `test_benchmark_separation_policy.py` -> update for deleted skill files

### No live LLM integration tests

All LLM stages tested with mock responses. Live extraction quality validated
via the standalone reconcile script on real deals after production export.

## Cleanup

### Delete
- `pipeline/` directory (already empty)
- `.codex/skills/` and `.cursor/skills/` mirrors
- Agent skill SKILL.md files from `.claude/skills/`
- Stale one-off implementation residue such as `quality_reports/session_logs/2026-03-18_skill-pipeline-design.md`
- Tracked runtime state such as `data/runs/pipeline_state.sqlite`

### Rename
- `skill_pipeline/canonicalize.py` -> `skill_pipeline/materialize.py`
- `data/skill/<slug>/canonicalize/` -> `data/skill/<slug>/materialize/`
- All references in models, paths, CLI, tests

### Dependencies
- Add `openai` to pyproject.toml
- Remove stale canonical pipeline references

### CLAUDE.md updates
- Remove agent skill references (/extract-deal, /verify-extraction, etc.)
- Replace with skill-pipeline CLI commands
- Update artifact directory table
- Simplify end-to-end sequence to single command
- Clarify that archival plans/specs do not override the live operator contract
- Update environment variables section

## Alex Instruction Alignment Fixes

Four medium-severity gaps identified during audit, incorporated into this
design:

1. **Enterprise-value bids** -- export.py surfaces enterprise_value in c1
   comment + review_flags when per_share is null
2. **Group-range bids** -- extract.py prompt handles "N parties submitted in
   range X-Y", materialize links to recovered unnamed actors
3. **Same-date sort order** -- export.py type priority: process markers -> IB ->
   NDA -> round announcements -> drops -> round deadlines -> proposals ->
   outcomes
4. **Date format** -- export.py outputs dates as MM/DD/YYYY per Alex's explicit
   instruction

## Migration Path

1. Implement new modules in worktree (no disruption to main)
2. Run on stec (current active deal) as validation
3. Compare output against existing stec artifacts
4. Run on saks as second validation
5. Run the standalone reconcile script on both deals to verify benchmark alignment
6. Merge to main, update CLAUDE.md
7. Process remaining 7 deals with consolidated pipeline
