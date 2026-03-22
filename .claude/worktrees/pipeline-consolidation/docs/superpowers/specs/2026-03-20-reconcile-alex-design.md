# Reconcile-Alex: Pipeline vs Hand-Coded Spreadsheet Reconciliation

**Date:** 2026-03-20
**Status:** DRAFT
**Approach:** C (match first, verify selectively)

## Purpose

Deterministic CLI stage that compares the pipeline's extraction artifacts against Alex's hand-coded spreadsheet (`example/deal_details_Alex_2026.xlsx`), then arbitrates disagreements and validates orphan events against the raw SEC filing text.

Alex's spreadsheet is susceptible to human review errors but embodies the correct collection logic. The pipeline may hallucinate or miss events. Neither source is authoritative — the raw filing text is the tiebreaker.

## Inputs

### Pipeline side (intermediate artifacts with evidence refs)

| File | Content |
|---|---|
| `data/skill/<slug>/extract/actors_raw.json` | Actor names, types, evidence_refs |
| `data/skill/<slug>/extract/events_raw.json` | Events, dates, amounts, evidence_refs |
| `data/skill/<slug>/enrich/enrichment.json` | bid_classifications, dropout_classifications (full enrichment) |
| `data/deals/<slug>/source/chronology_blocks.jsonl` | block_id → filing line mapping |

If `enrichment.json` does not exist but `deterministic_enrichment.json` does, read `bid_classifications` from the deterministic artifact. `dropout_classifications` require `enrichment.json` — if absent, skip dropout subtype comparison and note it in the report.

### Alex side

| File | Content |
|---|---|
| `example/deal_details_Alex_2026.xlsx` | Hand-coded events, filtered by target_name |

### Raw filing (for arbitration + existence checks)

| File | Content |
|---|---|
| `raw/<slug>/filings/*.txt` | Frozen SEC filing text |
| `raw/<slug>/document_registry.json` | Filing inventory with document IDs |

### Metadata

| File | Content |
|---|---|
| `data/seeds.csv` | slug → target_name mapping |

## Output

```
data/skill/<slug>/reconcile/reconciliation_report.json
```

## Prerequisites

- Extraction must have run (`actors_raw.json`, `events_raw.json` must exist)
- At least one enrichment artifact must exist (`enrichment.json` or `deterministic_enrichment.json`)
- Alex's spreadsheet must contain rows for the deal's `target_name`
- Raw filings must exist under `raw/<slug>/`
- Fail fast with `FileNotFoundError` if any prerequisite is missing

## Event Type Mapping

Pipeline internal `event_type` maps to Alex's `bid_note` taxonomy for matching. Match groups collapse subtypes so that matching uses coarse categories and comparison checks fine-grained labels.

### Core mapping (pipeline → Alex)

| Pipeline `event_type` | Alex `bid_note` | Match group |
|---|---|---|
| `proposal` | row where `bid_value` is not null/NA and `bid_note` is `NA` | `bid` |
| `nda` | `NDA` | `nda` |
| `drop` | `Drop`, `DropM`, `DropTarget`, `DropBelowInf`, `DropAtInf` | `drop` |
| `ib_retention` | `IB` | `ib` |
| `target_sale` | `Target Sale` | `target_sale` |
| `target_sale_public` | `Target Sale Public` | `target_sale_public` |
| `bidder_sale` | `Bidder Sale` | `bidder_sale` |
| `bidder_interest` | `Bidder Interest` | `bidder_interest` |
| `activist_sale` | `Activist Sale` | `activist_sale` |
| `sale_press_release` | `Sale Press Release` | `sale_press_release` |
| `bid_press_release` | `Bid Press Release` | `bid_press_release` |
| `executed` | `Executed` | `executed` |
| `terminated` | `Terminated` | `terminated` |
| `restarted` | `Restarted` | `restarted` |
| `final_round_ann` | `Final Round Ann` | `final_round_ann` |
| `final_round` | `Final Round` | `final_round` |
| `final_round_inf_ann` | `Final Round Inf Ann` | `final_round_inf_ann` |
| `final_round_inf` | `Final Round Inf` | `final_round_inf` |
| `final_round_ext_ann` | `Final Round Ext Ann` | `final_round_ext_ann` |
| `final_round_ext` | `Final Round Ext` | `final_round_ext` |

### Identifying proposals in Alex's data

Alex's `bid_note` of `"NA"` means "normal bid event" — not missing data. To distinguish from truly missing values in other columns, a proposal row in Alex's data satisfies: `bid_note == "NA"` AND `bid_value` is populated (not null/not string "NA").

### Unmapped Alex bid_note values

The spreadsheet contains edge-case event types that have no pipeline equivalent:

| Alex `bid_note` | Handling |
|---|---|
| `Exclusivity*` (case-insensitive prefix match on `"Exclusivity"`) | Match group `exclusivity` — will appear as Alex-only orphan |
| `IB Terminated` | Match group `ib_terminated` — Alex-only orphan |
| `Final Round Inf Ext`, `Final Round Inf Ext Ann` | Match group `final_round_inf_ext` / `final_round_inf_ext_ann` — Alex-only orphan |
| `Target Interest` | Match group `target_interest` — Alex-only orphan |
| Any other unrecognized `bid_note` value | Match group `unknown` — Alex-only orphan, logged with the raw value |

These are legitimate Alex events that the pipeline's event taxonomy does not yet cover. They will always appear as orphans, and the existence check will determine whether the filing supports them.

### Drop Subtype Name Mapping

Three systems use slightly different names for drop subtypes:

| Pipeline enrichment (`DropoutClassification.label`) | Alex spreadsheet (`bid_note`) | Canonical comparison label |
|---|---|---|
| `Drop` | `Drop` | `Drop` |
| `DropBelowM` | `DropM` | `DropBelowM` → `DropM` for comparison |
| `DropBelowInf` | `DropBelowInf` | `DropBelowInf` |
| `DropAtInf` | `DropAtInf` | `DropAtInf` |
| `DropTarget` | `DropTarget` | `DropTarget` |

When comparing dropout subtypes, normalize the pipeline's `DropBelowM` to `DropM` before comparison with Alex.

## Event Matching Algorithm

Three-tier greedy matching. Each tier consumes from the unmatched pool; once paired, events are removed from both sides.

### Date Derivation

**Pipeline side**: Parse `SkillEventRecord.date.normalized_hint` (a string like `"2016-03-09"`) into a `datetime.date`. If `normalized_hint` is null or unparseable, the event is excluded from date-based matching and flagged as an orphan.

**Alex side**: `bid_date_rough` is mixed-type in the spreadsheet — `datetime` objects for real dates and the string `"NA"` for missing dates. If the cell is a `datetime`, convert via `.date()`. If the cell is a string (including `"NA"`) or `None`, exclude from matching and flag as orphan.

### Tier 1 (strict)

- Date: exact match (pipeline parsed date == Alex date)
- Category: match group must be equal
- Actor: normalized names must match (pipeline `display_name` checked first, then `aliases`)

### Tier 2 (relaxed date)

- Date: ±3 calendar days
- Category: match group must be equal
- Actor: normalized names must match
- Within tier, prefer closest date

### Tier 3 (date + category only)

- Date: ±3 calendar days
- Category: match group must be equal
- Actor: skipped (catches name spelling differences)
- Within tier, prefer closest date
- **Risk note**: For deals with many concurrent NDA signings (30+ parties in the same week), Tier 3 may produce false-positive matches. These will be visible in the report as matched pairs with different actor names.

### Actor Name Normalization

Lowercase, strip suffixes (`inc`, `inc.`, `corp`, `corp.`, `corporation`, `llc`, `l.l.c.`, `ltd`, `l.p.`, `co`, `co.`, `company`), strip leading `the`, collapse whitespace, strip trailing punctuation (commas, periods).

Pipeline side: check `SkillActorRecord.display_name` first; if no match, check each entry in `aliases`.

Examples:
- `"THOMA BRAVO, LLC"` → `"thoma bravo"` ≈ `"Thoma Bravo"` → `"thoma bravo"`
- `"Party A"` → `"party a"` ≈ `"PARTY A"` → `"party a"`

### Grouped/Aggregate Actors

Alex has rows like `"39 parties"` or `"16 financial bidders"` for bulk NDA signings. Pipeline may have individual unnamed actors (`a1`, `a2`, ...) or a single grouped actor with `is_grouped=True`. These won't match 1:1. Flag as `aggregate_mismatch` rather than orphans.

Detection heuristic: Alex's `BidderName` matches pattern `r"\d+\s+(parties|bidders|financial|strategic)"` (case-insensitive).

## Field Comparison (Matched Pairs)

Only compare fields relevant to the event type:

| Field | Pipeline source | Alex source | Event types |
|---|---|---|---|
| `bid_value` | `terms.per_share` | `bid_value` / `bid_value_pershare` | proposals |
| `bid_range` | `terms.range_low`–`range_high` | `bid_value_lower`–`bid_value_upper` | proposals |
| `bid_type` | `enrichment.bid_classifications[evt].label` | `bid_type` | proposals |
| `dropout_subtype` | `enrichment.dropout_classifications[evt].label` (normalized: `DropBelowM` → `DropM`) | `bid_note` subtype | drops |
| `bidder_type` | actor fields → type code | `bidder_type_note` | NDAs (first appearance) |
| `date_precise` | `date.normalized_hint` when exact | `bid_date_precise` | all |
| `all_cash` | `terms.consideration_type == "cash"` → 1 | `all_cash` | proposals |

### Bidder Type Code Mapping

Pipeline actor fields (`bidder_kind`, `listing_status`, `geography`) map to Alex's shorthand:

| bidder_kind | listing_status | geography | Alex code |
|---|---|---|---|
| strategic | private | domestic | `S` |
| financial | private | domestic | `F` |
| strategic | public | domestic | `public S` |
| financial | public | domestic | `public F` |
| strategic | private | non_us | `non-US S` |
| financial | private | non_us | `non-US F` |
| strategic | public | non_us | `non-US public S` |
| financial | public | non_us | `non-US public F` |

**Compound bidder type notes**: Alex's `bidder_type_note` sometimes contains compound values like `"3S, 13F"`, `"S and F"`, or typos like `"Informsl"`. When the Alex value does not match any single code from the table above, skip the comparison for this field and add a note: `"compound_bidder_type_skipped"`.

### Data Quality Normalization (Alex side)

Before comparison, normalize known data quality issues:
- `bid_type`: `"Informsl"` → `"Informal"` (known typo)
- `bid_type`: strip whitespace
- `all_cash`: `"NA "` (trailing space) → `"NA"`

### Tolerances

- Bid values: ±$0.01 (rounding)
- Dates: exact match required (any difference is a mismatch)

## Arbitration (A): Filing-Text Verification of Disagreements

When a field disagrees between matched events:

1. Resolve the pipeline event's `evidence_refs` → `block_id` → chronology block → `start_line`/`end_line`
2. Read the raw `.txt` filing segment with ±5 line expansion
3. Search segment for both claimed values using format variants:
   - **Amounts**: `"$25"`, `"$25.00"`, `"25.00 per share"`, `"25 per share"`
   - **Dates**: `"June 15"`, `"June 15, 2016"`, `"June 2016"`
   - **Bid type keywords**: `"indication of interest"`, `"preliminary"`, `"marked-up merger agreement"`, `"draft merger agreement"`, `"process letter"`, `"binding"`, `"non-binding"`
   - **Dropout keywords**: `"below market"`, `"declined to increase"`, `"not invited"`, `"withdrew"`, `"no longer interested"`
4. Verdict: `"pipeline"` | `"alex"` | `"both"` | `"neither"` | `"no_evidence"`
5. Include filing snippet in report (max 500 characters, truncated with `…` if longer)

If the pipeline event has no `evidence_refs`, verdict is `"no_evidence"`.

## Existence Checks (C): Orphan Event Verification

### Pipeline-only orphans

Have evidence_refs. Verify `anchor_text` against filing via existing `find_anchor_in_segment` from `normalize.quotes`. Follow the same strict policy as `verify.py`: EXACT and NORMALIZED = `grounded`, FUZZY and UNRESOLVED = `ungrounded`. Include filing snippet (max 500 chars).

### Alex-only orphans

No evidence refs. Search the full chronology section (all chronology blocks concatenated) for:
1. Date patterns from `bid_date_rough` (e.g., `"June 15"`, `"June 15, 2016"`, month-day variants)
2. Actor name (`BidderName`, normalized)
3. Dollar amount if present (e.g., `"$25"`, `"$25.00"`)

If ≥2 of these found within a 50-line window: `likely_grounded` with snippet. Otherwise: `ungrounded`.

(Window enlarged from 20 to 50 lines because SEC chronology narratives for a single event can span 30-50 lines.)

## Report Schema

All models inherit from `SkillModel` (not `PipelineModel`), consistent with all other skill-stage output artifacts in `models.py`.

```python
class ReconciliationReport(SkillModel):
    deal_slug: str
    target_name: str
    pipeline_event_count: int
    alex_event_count: int
    matched_count: int
    pipeline_only_count: int
    alex_only_count: int
    aggregate_mismatch_count: int
    field_mismatches: list[FieldMismatch]
    pipeline_only: list[OrphanEvent]
    alex_only: list[OrphanEvent]
    summary: ReconciliationSummary

class FieldMismatch(SkillModel):
    pipeline_event_id: str
    alex_bidder_id: float              # Alex's BidderID (int or fractional)
    field: str                         # e.g., "bid_value", "bid_type"
    pipeline_value: str
    alex_value: str
    filing_supports: Literal["pipeline", "alex", "both", "neither", "no_evidence"]
    filing_snippet: str | None         # max 500 chars

class OrphanEvent(SkillModel):
    source: Literal["pipeline", "alex"]
    event_id: str | None               # pipeline event_id when source="pipeline", else None
    alex_bidder_id: float | None       # Alex BidderID when source="alex", else None
    event_type: str                    # normalized match group label
    actor_name: str | None
    date_rough: str | None             # ISO format YYYY-MM-DD
    value: float | None
    filing_verdict: Literal["grounded", "likely_grounded", "ungrounded"]
    filing_snippet: str | None         # max 500 chars

class ReconciliationSummary(SkillModel):
    status: Literal["pass", "warn", "fail"]
    match_rate: float                  # matched_count / max(pipeline_event_count, alex_event_count); 1.0 if both are 0
    field_mismatch_count: int
    arbitration_pipeline_wins: int     # filing supports pipeline
    arbitration_alex_wins: int         # filing supports alex
    arbitration_inconclusive: int      # both + neither + no_evidence
    orphan_grounded_count: int         # orphans with filing support (grounded + likely_grounded)
    orphan_ungrounded_count: int       # orphans without filing support
```

### Status Logic (evaluated in order — first match wins)

1. `fail`: match_rate < 0.7 OR (orphan_ungrounded_count > orphan_grounded_count AND orphan_ungrounded_count > 0)
2. `warn`: match_rate < 0.9 OR orphan_ungrounded_count > 0 OR field_mismatch_count > 0
3. `pass`: everything else

CLI exit code: `run_reconcile` returns 1 on `fail`, 0 on `pass` or `warn`.

## Files to Create

| File | Purpose |
|---|---|
| `skill_pipeline/reconcile.py` | Core module: loading, matching, comparison, arbitration, existence checks, report building |
| `tests/test_skill_reconcile.py` | Test suite with fixtures for matching, field comparison, arbitration, orphan detection |
| `.claude/skills/reconcile-alex/SKILL.md` | Skill doc following existing SKILL.md format (frontmatter with name/description, sections: Design Principles, Purpose, When To Use, Reads, Writes, Gate) |

## Files to Modify

| File | Change |
|---|---|
| `skill_pipeline/models.py` | Add `ReconciliationReport`, `FieldMismatch`, `OrphanEvent`, `ReconciliationSummary` models. Add `reconcile_dir: Path` and `reconcile_report_path: Path` to `SkillPathSet`. |
| `skill_pipeline/paths.py` | Add `reconcile_dir` and `reconcile_report_path` construction in `build_skill_paths()`. Add `paths.reconcile_dir` to `ensure_output_directories()`. |
| `skill_pipeline/cli.py` | Add `reconcile` subcommand with `--deal` arg, dispatch to `run_reconcile()`. |

## Entry Point

```python
def run_reconcile(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    """Compare pipeline artifacts vs Alex's spreadsheet, arbitrate via filing text.

    Return 0 on pass/warn, 1 on fail.
    """
```

CLI: `skill-pipeline reconcile --deal imprivata`

## Invariants

- Read-only: no modification to pipeline artifacts, Alex's spreadsheet, or raw filings
- Deterministic: no LLM calls, no randomness
- Fail fast: missing prerequisites raise FileNotFoundError immediately
- Reuses existing `find_anchor_in_segment` from `normalize.quotes` for pipeline-side verification
- `openpyxl` is already a declared dependency in `pyproject.toml`

## Not in Scope

- This stage is NOT integrated into the `DealAgentSummary` or the deal-agent orchestrator workflow. It is an independent validation tool run after the pipeline completes.
- No modification to Alex's spreadsheet or pipeline artifacts based on reconciliation results.
- No automatic correction of either source.
