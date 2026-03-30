# Phase 9: Deal-Specific Fixes + Revalidation - Research

**Researched:** 2026-03-30
**Domain:** LLM-driven extraction repair, deterministic pipeline rerun, cross-deal reconciliation measurement
**Confidence:** HIGH

## Summary

Phase 9 is an artifact-repair and revalidation phase, not a feature phase. The
two affected deals (Zep, Medivation) have specific, well-characterized defects
in their extraction artifacts. Zep's `evt_005` and `evt_008` incorrectly include
`bidder_new_mountain_capital` in their `actor_ids`, despite NMC explicitly
declining to participate in the 2014 process. Medivation's `coverage_notes`
reference drop events `evt_027` and `evt_029` that do not exist in the events
array -- a mismatch between the coverage sweep and the actual extraction state.

The repair strategy is straightforward: re-extract the affected deals using the
Phase 8-updated extraction guidance in `.claude/skills/extract-deal/SKILL.md`,
run the full deterministic pipeline from `canonicalize` through `db-export`, and
then measure the refreshed 9-deal reconciliation against the 2026-03-29
baseline. The existing skill infrastructure (extract-deal, verify-extraction,
deal-agent, reconcile-alex) already provides every workflow needed. No new
Python code, CLI commands, or schema changes are required.

**Primary recommendation:** Plan this as 3 sequential waves: (1) Zep re-extraction
and deterministic pipeline rerun, (2) Medivation re-extraction and deterministic
pipeline rerun, (3) corpus-wide reconciliation comparison against the 2026-03-29
baseline. Each wave gates the next.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Treat Phase 9 as affected-deal artifact repair plus rerun work, not
  as a new runtime-feature phase. Use the live on-disk artifacts as the
  starting truth when roadmap text and current files disagree.
- **D-02:** Keep the Phase 8 extraction guidance as the operative extraction
  contract. Re-run Zep and Medivation with the canonical
  `.claude/skills/extract-deal/SKILL.md` workflow before considering any new
  extraction-doc edits.
- **D-03:** Re-extract only the affected deals (`zep`, `medivation`) during the
  blind generation portion of this phase. The other seven deals remain frozen
  until the post-export reconciliation comparison.
- **D-04:** Zep has one explicit acceptance gate: remove
  `bidder_new_mountain_capital` from `evt_005` and `evt_008` in the rerun
  output. Do not preserve the current actor contamination just because later
  deterministic stages can tolerate it.
- **D-05:** Do not add a synthetic NMC April 14 drop merely to mirror Alex's
  tracker convention. The filing says NMC declined to submit an IOI, and the
  reconciliation report already marks that row as convention-dependent rather
  than a required pipeline event.
- **D-06:** If a fresh Zep rerun also surfaces filing-grounded improvements that
  now fall out naturally from the Phase 8 guidance, such as the March 27
  process-letter milestone or the May 14 Party X drop, keep them. They are
  welcome byproducts, but not separate acceptance gates.
- **D-07:** Planning must reconcile the stale milestone wording against the live
  Medivation artifact state before execution. The current
  `data/skill/medivation/extract/events_raw.json` already contains `evt_013`
  and `evt_017` as August 8 proposal events, so Phase 9 should not blindly
  "restore" IDs that already exist.
- **D-08:** The observed Medivation integrity problem to solve is that
  `coverage_notes` still cite drop events `evt_027` and `evt_029` even though
  those events are absent from the current `events` array. Treat that
  extraction/canonicalization mismatch as the concrete live defect unless fresh
  rerun evidence shows a different root cause.
- **D-09:** Preserve Medivation's existing bidder-round chronology. Do not
  collapse Company 1-4 proposals, round milestones, or extension-round events
  just to look more like Alex's coarser spreadsheet representation.
- **D-10:** Prefer targeted reruns from prompt composition / extraction forward
  for Zep and Medivation, followed by the full deterministic chain:
  `canonicalize`, `check`, `verify`, `coverage`, `gates`, `enrich-core`,
  `db-load`, and `db-export`. Do not re-fetch filings or wipe raw artifacts
  unless a prerequisite input is actually stale or corrupt.
- **D-11:** Prefer rerun plus `verify-extraction` repair loops over hand-editing
  canonical artifacts. If a surgical patch is unavoidable, preserve event IDs
  and evidence-backed provenance, then immediately rerun the downstream
  deterministic stages.
- **D-12:** Post-export validation is corpus-wide even though the rerun is not.
  After both affected deals pass `db-export`, compare the refreshed 9-deal
  reconciliation outputs against the 2026-03-29 baseline and require a better
  atomic match rate plus fewer filing-contradicted pipeline claims.
- **D-13:** Benchmark materials stay fenced off until each affected deal
  completes `skill-pipeline db-export --deal <slug>`. Reconciliation is a
  read-only diagnostic step that measures the rerun; it must not steer blind
  extraction or repair work.

### Claude's Discretion
- Whether the first attempt is a clean extraction-stage rerun or a targeted
  verify-repair loop, as long as the benchmark boundary is preserved and the
  acceptance gates above are met
- Whether any stale planning text in ROADMAP/REQUIREMENTS should be updated
  during planning or at the start of execution, as long as the live artifact
  state is made explicit before Phase 9 implementation begins
- Exact comparison format for reporting the new 9-deal reconciliation deltas,
  as long as it makes the baseline-vs-rerun improvement auditable

### Deferred Ideas (OUT OF SCOPE)
- Add a first-class exclusivity event type for Zep's February 27, 2015
  exclusivity agreement
- Add benchmark-style aggregate non-participant drop rows when the filing only
  supports cohort-level inference
- Re-extract the full 9-deal corpus from scratch rather than only Zep and
  Medivation
- Expand the schema to mirror Alex's `Bidder Sale` summary-row convention for
  hostile-process framing
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EXTRACT-04 | Zep NMC actor error corrected -- remove NMC from evt_005 and evt_008 actor_ids | Live defect confirmed: `evt_005` and `evt_008` both list `bidder_new_mountain_capital` alongside grouped actors. Filing says NMC "declined to submit" an IOI. Clean re-extraction with current SKILL.md should naturally exclude NMC from these grouped events. |
| EXTRACT-05 | Medivation missing drops restored -- evt_013 and evt_017 present in events_raw.json with filing-grounded evidence | Live artifact state differs from requirement wording: `evt_013` and `evt_017` already exist as August 8 proposals. The real defect is `coverage_notes` citing non-existent `evt_027` and `evt_029` drop events. A clean re-extraction resolves the mismatch by regenerating both events and coverage_notes from scratch. |
| RERUN-01 | Affected deals re-extracted with updated skill docs and re-run through full deterministic pipeline | Both deals have raw filings and source artifacts intact. The deterministic chain (`canonicalize` through `db-export`) ran successfully in the 7-deal rerun session. Re-extraction uses the canonical deal-agent workflow stages. |
| RERUN-02 | 9-deal reconciliation re-run shows improved atomic match rate and reduced filing-contradicted pipeline claims vs baseline | The 2026-03-29 baseline is documented in `data/reconciliation_cross_deal_analysis.md` (156 matched, 45 pipeline-wins, 16 alex-wins). Reconciliation uses the existing `/reconcile-alex` skill per-deal plus cross-deal analysis. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Key directives that constrain Phase 9 implementation:

- **Benchmark boundary:** Benchmark materials are forbidden before `db-export` completes. Reconciliation is post-export only and read-only.
- **Filing text is the only factual source of truth.** Extraction must trace to `source_accession_number` + verbatim `source_text`.
- **Fail fast:** Do not add silent fallbacks. Fail fast on missing files, schema drift, contradictory state.
- **Raw filing immutability:** Never rewrite raw filing text under `raw/<slug>/filings/`.
- **Deterministic stages own validation:** Fixes should be proven by rerunning deterministic stages, not by unverified manual edits.
- **Skill mirror sync:** Update `.claude/skills/` first, then sync mirrors via `scripts/sync_skill_mirrors.py`.
- **Agent working rules:** Solve the real problem (not symptoms), do not overengineer, do not expand scope, do not infer architecture from stale docs.
- **Canonical extract filenames:** Live files are `actors_raw.json` and `events_raw.json` (not `actors.json`/`events.json`).
- **db-load requires canonical + spans.json + deterministic_enrichment.json.** Missing sidecars are an error.
- **verify treats only EXACT and NORMALIZED as passing.** FUZZY does not pass.

## Architecture Patterns

### Rerun Strategy: Targeted Rebuild vs Full Clean

Two rerun strategies exist in the repo:

**Strategy A: Full clean rebuild (via `/deal-agent <slug>`):**
- Deletes `data/skill/<slug>/` and `data/deals/<slug>/source/` entirely
- Preserves `raw/<slug>/` (immutable)
- Rebuilds everything from raw-fetch through db-export
- Pros: no stale artifact risk
- Cons: unnecessary re-fetching and re-preprocessing when source is clean

**Strategy B: Targeted extraction-forward rerun (D-10 preferred):**
- Deletes only `data/skill/<slug>/extract/`, `check/`, `verify/`, `coverage/`, `gates/`, `enrich/`, `export/`, `canonicalize/`, `prompt/`
- Preserves `raw/<slug>/` and `data/deals/<slug>/source/`
- Starts from `compose-prompts` forward
- Pros: faster, avoids EDGAR network calls
- Cons: must verify source artifacts are still valid

**Recommendation:** Use Strategy B (per D-10). Both deals have verified raw filings
and source artifacts from the 2026-03-29 7-deal rerun. Source artifacts
(`chronology_blocks.jsonl`, `evidence_items.jsonl`) are derived deterministically
from raw filings, so they cannot be stale unless raw filings changed (they
cannot, by immutability contract).

### Stage Ordering for Targeted Rerun

Per the deal-agent workflow and D-10:

```
1. Delete: data/skill/<slug>/{extract,check,verify,coverage,gates,enrich,export,canonicalize,prompt}/
2. Ensure output directories exist
3. skill-pipeline compose-prompts --deal <slug> --mode actors
4. /extract-deal <slug>                    [LLM -- actor + event extraction]
5. skill-pipeline compose-prompts --deal <slug> --mode events
6. skill-pipeline canonicalize --deal <slug>
7. skill-pipeline check --deal <slug>
8. skill-pipeline verify --deal <slug>
9. skill-pipeline coverage --deal <slug>
10. skill-pipeline gates --deal <slug>
11. /verify-extraction <slug>              [LLM -- repair loop if needed]
12. (if structural repairs: re-run steps 7-10 before continuing)
13. skill-pipeline enrich-core --deal <slug>
14. skill-pipeline db-load --deal <slug>
15. skill-pipeline db-export --deal <slug>
```

### Reconciliation Baseline Comparison Pattern

Post-export reconciliation follows the reconcile-alex workflow:

```
1. /reconcile-alex zep                     [post-export, read-only]
2. /reconcile-alex medivation              [post-export, read-only]
3. Re-run cross-deal analysis for all 9 deals
4. Compare new atomic match rate vs 2026-03-29 baseline
5. Compare filing-contradicted pipeline claims vs baseline
```

### Recommended Project Structure

The following artifact paths are affected by Phase 9:

```
data/skill/zep/
  extract/actors_raw.json          # regenerated
  extract/events_raw.json          # regenerated -- NMC removed from evt_005/evt_008
  extract/spans.json               # regenerated
  canonicalize/                    # regenerated
  check/                           # regenerated
  verify/                          # regenerated
  coverage/                        # regenerated
  gates/                           # regenerated
  enrich/                          # regenerated
  export/deal_events.csv           # regenerated
  reconcile/reconciliation_report.json  # refreshed post-export

data/skill/medivation/
  extract/actors_raw.json          # regenerated
  extract/events_raw.json          # regenerated -- coverage_notes/events mismatch resolved
  extract/spans.json               # regenerated
  canonicalize/                    # regenerated
  check/                           # regenerated
  verify/                          # regenerated
  coverage/                        # regenerated
  gates/                           # regenerated
  enrich/                          # regenerated
  export/deal_events.csv           # regenerated
  reconcile/reconciliation_report.json  # refreshed post-export

data/reconciliation_cross_deal_analysis.md  # refreshed with new numbers
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Extraction repair | Manual JSON edits to events_raw.json | Re-extraction via `/extract-deal` + `/verify-extraction` | Manual edits break span provenance, skip canonicalization, and bypass verification gates |
| Deterministic pipeline validation | Ad-hoc checks on output JSON | `skill-pipeline check/verify/coverage/gates` chain | These stages enforce the full invariant set and produce auditable findings |
| Reconciliation measurement | Manual counting of improvements | `/reconcile-alex` per-deal + cross-deal analysis script | The reconcile-alex skill produces structured reports with filing arbitration |
| Event ID stability | Renumbering events after extraction | Let extraction assign IDs, let canonicalize handle dedup | Event IDs are integration surfaces referenced by verify, enrich, db-load |
| Artifact cleanup | Selective file deletion | Delete the full `data/skill/<slug>/` subtree for extraction-forward stages | Partial cleanup risks stale artifacts from a prior pass contaminating the new run |

**Key insight:** Phase 9 adds zero new code. Every tool needed already exists. The
risk is operational (running stages in the wrong order, violating the benchmark
boundary, or accepting a rerun that does not actually fix the defect) rather
than technical.

## Common Pitfalls

### Pitfall 1: Stale Artifact Contamination
**What goes wrong:** Running `canonicalize` or `verify` against a mix of old and
new extraction artifacts produces misleading results.
**Why it happens:** Partial cleanup leaves old `spans.json` or `canonicalize_log.json`
from the prior run, which the new pipeline may try to read or merge with.
**How to avoid:** Delete the entire `data/skill/<slug>/{extract,canonicalize,check,verify,coverage,gates,enrich,export,prompt}/`
tree before starting the re-extraction, not just `events_raw.json`.
**Warning signs:** Canonicalize log referencing spans that do not match the new
extraction; verify finding "fixed" issues that were from the old run.

### Pitfall 2: Benchmark Boundary Violation
**What goes wrong:** Looking at reconciliation reports or Alex's spreadsheet before
`db-export` completes, then unconsciously steering extraction to match Alex.
**Why it happens:** The user naturally wants to verify improvement, and the
reconciliation data is right there in the repo.
**How to avoid:** Hard fence: no reads of `data/skill/<slug>/reconcile/`,
`example/`, `diagnosis/`, or `/reconcile-alex` until after `db-export`. The plan
must make this explicit as a gate between extraction/deterministic stages and
reconciliation stages.
**Warning signs:** Extraction mentioning Alex row counts or benchmark field names.

### Pitfall 3: Medivation Requirement Misread
**What goes wrong:** The planner or executor tries to "restore" `evt_013` and
`evt_017` as if they are missing, when they already exist as August 8 proposal
events.
**Why it happens:** The ROADMAP success criterion says "Medivation events_raw.json
contains evt_013 and evt_017 with filing-grounded evidence quotes." This reads
as if those events need to be added. But the live artifact already has them.
**How to avoid:** Recognize that the real defect (per D-07 and D-08) is the
`coverage_notes` citing `evt_027` and `evt_029` as extracted drops when those
events do not exist in the events array. A clean re-extraction resolves this
because both events and coverage_notes are regenerated from scratch.
**Warning signs:** A plan task that says "add evt_013 to Medivation" -- that
event already exists.

### Pitfall 4: Event ID Instability After Re-extraction
**What goes wrong:** The LLM re-extraction assigns different event IDs to the same
events, breaking references in downstream discussions, session logs, and the
reconciliation report.
**Why it happens:** Event IDs (`evt_001`, `evt_002`, ...) are assigned
sequentially by the LLM at extraction time. A new extraction may reorder events
or add/remove events, shifting all subsequent IDs.
**How to avoid:** Accept that event IDs will change after re-extraction. The
acceptance gates should be checked against the new ID space, not the old one.
The success criteria for Zep (D-04) should verify that NMC is not in any
grouped-proposal or grouped-drop actor_ids, not that specific old event IDs
persist.
**Warning signs:** A plan that gates on "evt_005 must not contain NMC" when the
new extraction may not have an `evt_005` at all.

### Pitfall 5: DuckDB Lock Contention During db-load/db-export
**What goes wrong:** Running `db-load` for Zep and then immediately `db-export`
hits a transient DuckDB file lock because the database file was not fully
released.
**Why it happens:** DuckDB uses file-level locking. On Windows/WSL, lock release
can be slightly delayed.
**How to avoid:** Phase 6 already added bounded exponential backoff retry for
lock contention in `db-export` (HARD-05). Run the two deals sequentially, not
in parallel, to avoid cross-deal lock conflicts on the shared `pipeline.duckdb`.
**Warning signs:** `duckdb.IOException` containing "Could not set lock on file"
or "used by another process."

### Pitfall 6: Reconciliation Improvement Measurement Error
**What goes wrong:** Comparing new per-deal reconciliation reports to the old
baseline but using different counting methodologies (e.g., including aggregate
rows in the match rate for one but not the other).
**Why it happens:** The reconciliation skill evolved across sessions, and earlier
reports may have subtly different structures.
**How to avoid:** Re-run `/reconcile-alex` for both affected deals first, then
regenerate the cross-deal analysis using the same methodology for all 9 deals.
The 7 frozen deals' reconciliation reports should remain unchanged, but the
cross-deal summary must be regenerated from all 9 updated per-deal reports.
**Warning signs:** An improvement number that cannot be broken down into
per-deal deltas.

## Code Examples

### Targeted Artifact Cleanup Before Re-extraction

```bash
# Source: deal-agent SKILL.md step 0, adapted for targeted rerun (D-10)
# Preserve raw/ and data/deals/<slug>/source/ -- only wipe downstream
SLUG="zep"
rm -rf "data/skill/${SLUG}/extract"
rm -rf "data/skill/${SLUG}/canonicalize"
rm -rf "data/skill/${SLUG}/check"
rm -rf "data/skill/${SLUG}/verify"
rm -rf "data/skill/${SLUG}/coverage"
rm -rf "data/skill/${SLUG}/gates"
rm -rf "data/skill/${SLUG}/enrich"
rm -rf "data/skill/${SLUG}/export"
rm -rf "data/skill/${SLUG}/prompt"
# Recreate directories
mkdir -p "data/skill/${SLUG}"/{extract,canonicalize,check,verify,coverage,gates,enrich,export,prompt}
```

### Full Deterministic Pipeline Rerun (Post-Extraction)

```bash
# Source: CLAUDE.md end-to-end flow, deal-agent SKILL.md stages 5-9b
SLUG="zep"
skill-pipeline canonicalize --deal "$SLUG"
skill-pipeline check --deal "$SLUG"
skill-pipeline verify --deal "$SLUG"
skill-pipeline coverage --deal "$SLUG"
skill-pipeline gates --deal "$SLUG"
# LLM repair loop via /verify-extraction only if all errors are repairable
skill-pipeline enrich-core --deal "$SLUG"
skill-pipeline db-load --deal "$SLUG"
skill-pipeline db-export --deal "$SLUG"
```

### Acceptance Check: Zep NMC Removal

```python
# Source: REQUIREMENTS.md EXTRACT-04, adapted for verification
import json

with open("data/skill/zep/extract/events_raw.json") as f:
    data = json.load(f)

for event in data["events"]:
    if event["event_type"] in ("proposal", "drop"):
        assert "bidder_new_mountain_capital" not in event.get("actor_ids", []) or \
               event.get("summary", "").startswith("New Mountain Capital"), \
               f"NMC contamination in grouped event {event['event_id']}"
```

### Acceptance Check: Medivation Coverage Consistency

```python
# Source: CONTEXT.md D-08, adapted for verification
import json, re

with open("data/skill/medivation/extract/events_raw.json") as f:
    data = json.load(f)

event_ids = {e["event_id"] for e in data["events"]}
for note in data.get("coverage_notes", []):
    # Extract all evt_NNN references from coverage notes
    referenced = set(re.findall(r"evt_\d+", note))
    for ref in referenced:
        assert ref in event_ids, \
            f"coverage_notes references {ref} which is not in events array"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| evidence_refs on actors/events | Quote-first schema with quote_ids + spans.json | Phase 3 (v1.0) | All extraction now uses quote-before-extract protocol |
| IOI language overrides process position | Process position overrides IOI language for bid_type | Phase 7 (v1.1) | Final-round proposals now classified Formal |
| No round milestone extraction guidance | Explicit 6-type round taxonomy in SKILL.md | Phase 8 (v1.1) | New extractions can capture round milestones |
| No verbal indication guidance | Explicit oral/verbal proposal guidance in SKILL.md | Phase 8 (v1.1) | Oral priced bids now extracted as proposals |
| No NDA exclusion guidance | Explicit rollover/teaming/non-target exclusion rules | Phase 8 (v1.1) | Prevents false NDA events |
| No deterministic DropTarget | enrich-core emits DropTarget from round invitation deltas | Phase 8 (v1.1) | Committee-driven narrowing detected automatically |
| No contextual all_cash | enrich-core infers all_cash from deal-level patterns | Phase 8 (v1.1) | Fewer NA all_cash values in export |

## Live Defect Inventory

### Zep: NMC Actor Contamination (EXTRACT-04)

**Current state (verified against live artifact):**
- `evt_005` (proposal, 2014-04-14): `actor_ids` = `["bidder_new_mountain_capital", "grouped_other_financial_bidders", "grouped_initial_strategic_bidder"]`
- `evt_008` (drop, 2014-06-19): `actor_ids` = `["bidder_new_mountain_capital", "grouped_other_financial_bidders", "grouped_initial_strategic_bidder"]`

**Filing truth:** NMC signed an NDA (`evt_003`) but declined to submit an IOI.
NMC's active participation begins in 2015 (`evt_010` bidder_interest, `evt_011`
proposal) after the sale process restarted. The 2014 grouped proposal and drop
events should not include NMC.

**Root cause:** The original extraction conflated NMC's NDA participation with
IOI submission, treating all NDA signers as IOI participants.

**Acceptance gate:** After re-extraction, no grouped proposal or grouped drop
event in the 2014 cycle should contain `bidder_new_mountain_capital` in
`actor_ids`.

### Medivation: Coverage Notes / Events Array Mismatch (EXTRACT-05)

**Current state (verified against live artifact):**
- `coverage_notes` contains `"drop: extracted (evt_027, evt_029)"`
- Event IDs in events array: `evt_001` through `evt_035`, but `evt_027` and
  `evt_029` are missing (gap in sequence)
- `evt_013` and `evt_017` exist as August 8 proposals (contrary to the
  ROADMAP's "missing" characterization)

**Root cause hypothesis:** The extraction produced drop events `evt_027` and
`evt_029`, but canonicalization removed them (likely because they referenced
actors without prior NDAs, per the canonicalize dedup/cleanup rules). The
coverage_notes were written during extraction before canonicalization, so they
still reference the removed events.

**Acceptance gate:** After re-extraction, every event ID referenced in
`coverage_notes` must exist in the `events` array. The events array should
remain gap-free after canonicalization (or gaps should be explainable by
the canonicalize log).

### Baseline Reconciliation Numbers (2026-03-29)

| Metric | Zep | Medivation | Corpus-wide |
|--------|-----|------------|-------------|
| Pipeline events | 16 | 33 | 207 |
| Alex rows | 23 | 16 | 269 |
| Matched pairs | 14 | 12 | 156 |
| Pipeline-only | 1 | 19 | 47 |
| Alex-only | 9 | 2 | 65 |
| Aggregate rows | 3 | 2 | 47 |
| Arbitrations: pipeline wins | -- | 10 | 45 |
| Arbitrations: alex wins | -- | 3 | 16 |

The corpus-wide atomic match rate baseline: 156 matched out of 222 Alex atomic
rows = 70.3%.

## Open Questions

1. **Event ID renumbering after re-extraction**
   - What we know: Re-extraction assigns fresh IDs. The Zep acceptance gate
     (D-04) references `evt_005` and `evt_008` by their current IDs, but those
     IDs may shift.
   - What's unclear: Whether the planner should rephrase the acceptance gate in
     terms of event content (grouped 2014-cycle proposal/drop) rather than
     specific IDs.
   - Recommendation: Gate on "no NMC in any grouped-proposal or grouped-drop
     actor_ids in the 2014 cycle" rather than on specific event IDs. The REQUIREMENTS
     text is already specific to "evt_005 and evt_008" but the planner should
     interpret this as the semantic content, not the literal ID string.

2. **Medivation drop restoration vs. coverage_notes fix**
   - What we know: The ROADMAP says "Medivation missing drops restored" but
     the live defect is coverage_notes referencing non-existent events. A clean
     re-extraction fixes both because it regenerates everything.
   - What's unclear: Whether the user expects the re-extraction to also produce
     actual drop events for Medivation bidders who exited the process.
   - Recommendation: A clean re-extraction with Phase 8 guidance will naturally
     produce filing-grounded drops if the filing supports them. Do not artificially
     target specific drop events. The acceptance gate is internal consistency
     (coverage_notes matching the events array) rather than specific drop content.

3. **Reconciliation cross-deal analysis regeneration**
   - What we know: The 2026-03-29 cross-deal analysis was generated manually
     across a session. There is no automated script.
   - What's unclear: How the cross-deal analysis should be regenerated -- same
     manual process, or should the plan include instructions.
   - Recommendation: The reconciliation comparison is an LLM task (reading all
     9 per-deal reports and producing the cross-deal summary). Plan it as an
     explicit step after all per-deal reconciliation reports are updated.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >= 8.0 |
| Config file | `pytest.ini` |
| Quick run command | `python -m pytest -q` |
| Full suite command | `python -m pytest -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXTRACT-04 | Zep NMC not in grouped events | manual + smoke | Inspect `events_raw.json` post-extraction | N/A (artifact-level, not code) |
| EXTRACT-05 | Medivation coverage_notes/events consistency | manual + smoke | Inspect `events_raw.json` post-extraction | N/A (artifact-level, not code) |
| RERUN-01 | Full deterministic pipeline passes for both deals | integration | `skill-pipeline check/verify/coverage/gates/enrich-core/db-load/db-export --deal <slug>` | N/A (CLI commands) |
| RERUN-02 | 9-deal reconciliation improvement | manual | Compare cross-deal analysis to 2026-03-29 baseline | N/A (reconciliation report) |

### Sampling Rate
- **Per deal rerun:** Full deterministic pipeline passes without errors (all stages return success)
- **Per deal export:** Acceptance checks on the specific defect being repaired
- **Phase gate:** 9-deal reconciliation shows measurable improvement vs baseline

### Wave 0 Gaps
None -- existing test infrastructure covers all deterministic pipeline stages.
Phase 9 does not add new code, so no new unit tests are needed. Validation is
at the artifact level (checking output JSON and CSV files) rather than the
code level.

## Sources

### Primary (HIGH confidence)
- Live artifact inspection: `data/skill/zep/extract/events_raw.json` -- confirmed NMC in evt_005 and evt_008 actor_ids
- Live artifact inspection: `data/skill/medivation/extract/events_raw.json` -- confirmed evt_027/evt_029 missing, evt_013/evt_017 present
- `.claude/skills/extract-deal/SKILL.md` -- canonical extraction workflow with Phase 8 updates
- `.claude/skills/verify-extraction/SKILL.md` -- repair loop contract
- `.claude/skills/deal-agent/SKILL.md` -- full stage ordering
- `.claude/skills/reconcile-alex/SKILL.md` -- post-export reconciliation procedure
- `data/reconciliation_cross_deal_analysis.md` -- 2026-03-29 baseline numbers
- `data/skill/zep/reconcile/reconciliation_report.json` -- Zep baseline
- `data/skill/medivation/reconcile/reconciliation_report.json` -- Medivation baseline

### Secondary (MEDIUM confidence)
- `.planning/phases/08-extraction-guidance-enrichment-extensions/08-VERIFICATION.md` -- Phase 8 completed successfully, 318 tests pass
- `quality_reports/session_logs/2026-03-29_7-deal-rerun_master.md` -- Prior rerun patterns and execution model

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries or tools needed; all existing
- Architecture: HIGH -- rerun strategy is well-established in the repo, documented in deal-agent SKILL.md
- Pitfalls: HIGH -- defects are precisely characterized from live artifact inspection and reconciliation reports
- Reconciliation measurement: MEDIUM -- the cross-deal analysis regeneration is manual and methodology alignment needs care

**Research date:** 2026-03-30
**Valid until:** Indefinite (this is a defect-repair phase, not a fast-moving technology domain)
