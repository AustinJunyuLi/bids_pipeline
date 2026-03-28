# Phase 4: Enhanced Gates - Research

**Researched:** 2026-03-28
**Domain:** Deterministic semantic validation for M&A deal extraction artifacts
**Confidence:** HIGH

## Summary

Phase 4 adds four new semantic gates that validate whether extracted deal events form a logically coherent M&A narrative. The existing gate stack (check -> verify -> coverage) catches structural defects, evidence grounding failures, and missed cues. The new gates catch a different class of error: extracted events that are individually valid but collectively impossible or inconsistent as a deal timeline.

The implementation is well-scoped. All four gates operate on existing artifact schemas (events, actors, spans, blocks, verification_findings) with no new data dependencies. The architecture decision to create a separate stage with its own CLI command and output directory fits the established pattern exactly. Each existing gate module (check.py at 248 lines, verify.py at 584 lines, coverage.py at 377 lines) follows the same structure: load artifacts, run check functions, collect findings, write report, return exit code.

**Primary recommendation:** Create a single `gates.py` module with one function per gate, a `GateFinding` Pydantic model with per-rule severity assignment, and the same `run_gates()` / `_build_report()` pattern used by check.py. Sort events by date before applying cross-event rules (GATE-02) because live data shows events in array order that differ from chronological order.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** The 4 new gates live in a new dedicated stage (`gates.py` or `semantic_check.py`), separate from the existing check/verify/coverage files. Clean separation: structural checks in check.py, evidence validation in verify.py, coverage audit in coverage.py, semantic checks in the new file.
- **D-02:** The new stage runs after coverage and before enrich-core in the pipeline sequence: `check -> verify -> coverage -> gates -> enrich-core`. Semantic gates act as a final quality filter before enrichment.
- **D-03:** The new stage gets its own CLI command (e.g., `skill-pipeline gates --deal <slug>`) and its own output directory under `data/skill/<slug>/gates/`.
- **D-04:** Findings use tiered severity. Each gate rule has a pre-assigned severity level. High-confidence violations (impossible sequences like proposal-after-executed) are blockers. Lower-confidence checks (date precision mismatches, attention clustering patterns) are warnings. The gate stage passes overall unless at least one blocker exists.
- **D-05:** The severity assignment is per-rule, not per-gate. A single gate (e.g., GATE-02 cross-event logic) can produce both blocker and warning findings depending on which rule fired.
- **D-06:** Start with 5-7 core invariant rules that are almost never wrong. Do not attempt a comprehensive 15-20 rule set in this phase. The initial rule set should include at minimum: (1) No proposal after executed in same cycle, (2) No nda after drop without restarted in between, (3) final_round_ann must precede final_round, (4) executed must be the last substantive event in its cycle, (5) NDA signers must appear in at least one downstream event.
- **D-07:** Additional rules beyond the initial 5-7 will be added in future phases based on real false-positive data. Do not pre-build a rule suppression mechanism.
- **D-08:** Attention decay produces a diagnostic report only -- no automatic re-extraction trigger. The report includes: failure count by block-position quartile, hot spots (blocks with 3+ failures clustered nearby), and a decay score (0.0 to 1.0 where 1.0 = perfect uniform distribution, lower = concentrated failures indicating attention loss).
- **D-09:** The attention decay diagnostic analyzes verify findings (quote match failures) by the block position of the associated quotes. It consumes verification_findings.json and spans.json, not raw extraction artifacts.

### Claude's Discretion
- Exact file name and module structure for the new stage (gates.py vs semantic_check.py vs enhanced_gates.py)
- Internal organization of the 4 gates within the module (separate functions, classes, or a registry pattern)
- Exact threshold for the attention decay score (if any) to distinguish "healthy" from "concerning" patterns
- How to handle deals with very few events (e.g., < 5) where statistical clustering is meaningless
- Exact Pydantic model names for the gate report and findings

### Deferred Ideas (OUT OF SCOPE)
- Comprehensive cross-event rule set (15-20 rules) -- defer until false-positive data from the initial 5-7 rules across the 9-deal corpus informs which rules are safe to add
- Automatic re-extraction trigger from attention decay diagnostic -- defer to Phase 5 or later
- Rule suppression mechanism for known edge cases -- defer until real false positives are observed
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GATE-01 | Temporal consistency check validates event dates are chronologically consistent with evidence positions in filing | Block metadata (date_mentions, temporal_phase) from Phase 1 provides comparison basis. Spans provide block_id linkage. Research confirms stec has 235 blocks with date_mentions available. |
| GATE-02 | Cross-event logic validation enforces domain invariants (no proposal after executed, no NDA after drop without restart, etc.) | Research confirms medivation has a real post-executed drop event (evt_044) that would be caught. Event sorting by date is required -- array order differs from chronological order in live data. Cycle detection logic exists in enrich_core._cycle_ranges(). |
| GATE-03 | Per-actor lifecycle coverage verifies every NDA signer appears in downstream events | Research confirms stec has 6 NDA signers all appearing in downstream events (clean). Medivation has 5 NDA signers all appearing downstream. Set-membership check is straightforward. |
| GATE-04 | Attention decay diagnostics cluster verification failures by block position to detect attention loss | Research confirms stec has 0 verify failures (clean pass), so attention decay diagnostic would report 0.0 decay. Medivation also has 0 verify failures. Tests must use synthetic failures. Spans provide block_id -> ordinal mapping for quartile binning. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.x (installed) | Finding/report models | Already used for all artifact models in models.py |
| Python stdlib | 3.11+ | Date parsing, statistics, collections | No external deps needed for this phase |

### Supporting
No new dependencies required. All four gates operate on existing artifact schemas and use standard library operations (date comparison, set intersection, collections.Counter).

## Architecture Patterns

### Recommended Module Structure
```
skill_pipeline/
  gates.py              # New: all 4 gates in one module (~300-400 lines)
```

**Rationale for `gates.py`:** Follows the naming convention of the CLI subcommand (`skill-pipeline gates`). Short, clear, and parallel to `check.py`, `verify.py`, `coverage.py`. The alternative names (`semantic_check.py`, `enhanced_gates.py`) are longer without adding clarity.

### Recommended Internal Organization

Use separate private functions per gate, each returning `list[GateFinding]`. No classes, no registry pattern. This matches the existing check.py pattern exactly.

```python
# Pattern: each gate is a function returning findings
def _gate_temporal_consistency(artifacts, blocks) -> list[GateFinding]: ...
def _gate_cross_event_logic(artifacts) -> list[GateFinding]: ...
def _gate_actor_lifecycle(artifacts) -> list[GateFinding]: ...
def _gate_attention_decay(verification_findings, spans, blocks) -> GateAttentionReport: ...

def run_gates(deal_slug: str, *, project_root: Path = PROJECT_ROOT) -> int:
    # Load inputs, run all gates, write report, return exit code
```

### Pattern: Finding Model with Per-Rule Severity

```python
class GateFinding(SkillModel):
    gate_id: str                # "temporal_consistency", "cross_event_logic", etc.
    rule_id: str                # "proposal_after_executed", "nda_after_drop", etc.
    severity: Literal["blocker", "warning"]
    description: str
    event_ids: list[str] = Field(default_factory=list)
    actor_ids: list[str] = Field(default_factory=list)
    block_ids: list[str] = Field(default_factory=list)

class GateAttentionDecay(SkillModel):
    quartile_counts: list[int]  # [q1_failures, q2_failures, q3_failures, q4_failures]
    hot_spots: list[dict]       # blocks with 3+ nearby failures
    decay_score: float          # 0.0 to 1.0, 1.0 = uniform

class GateReport(SkillModel):
    findings: list[GateFinding] = Field(default_factory=list)
    attention_decay: GateAttentionDecay | None = None
    summary: GateReportSummary

class GateReportSummary(SkillModel):
    blocker_count: int
    warning_count: int
    status: Literal["pass", "fail"]
```

**Key design:** `attention_decay` is a separate field on `GateReport`, not a finding, because it is diagnostic-only and never a blocker (per D-08). It can be `None` when there are no verification failures to analyze.

### Pattern: Event Sorting for Cross-Event Rules

**Critical finding from live data:** The medivation events array has events out of chronological order. Event evt_042 (dated April 20, 2016) appears at array index 41 after evt_040 (executed, dated August 20, 2016) at index 37. Event evt_044 (drop, dated August 10) appears at array index 43 after the executed event.

Cross-event rules (GATE-02) MUST sort events by date before checking invariants. Use `sort_date` from the `ResolvedDate` when available, falling back to `normalized_start`. Events with no parseable date should be excluded from ordering-dependent checks with a warning.

```python
def _sort_events_by_date(events) -> list:
    """Sort events chronologically. Events without dates are appended at the end."""
    with_date = []
    without_date = []
    for evt in events:
        sort_date = evt.date.sort_date if hasattr(evt.date, 'sort_date') else None
        if sort_date is None and hasattr(evt.date, 'normalized_hint'):
            # quote_first mode: try normalized_hint
            hint = evt.date.normalized_hint
            if hint:
                sort_date = date.fromisoformat(hint)
        if sort_date:
            with_date.append((sort_date, evt))
        else:
            without_date.append(evt)
    with_date.sort(key=lambda x: x[0])
    return [evt for _, evt in with_date] + without_date
```

### Pattern: Mode-Aware Artifact Access

The gates module needs the same `quote_first` vs `canonical` dispatch pattern used by check.py. Use `_get_actor_event_records()` to get the right record types regardless of mode.

```python
def _get_actor_event_records(artifacts: LoadedExtractArtifacts):
    if artifacts.mode == "quote_first":
        return artifacts.raw_actors.actors, artifacts.raw_events.events
    return artifacts.actors.actors, artifacts.events.events
```

### Anti-Patterns to Avoid
- **Do not sort events by array position for invariant checks:** Live data proves array order != chronological order.
- **Do not make attention decay a pass/fail gate:** Per D-08, it is diagnostic only.
- **Do not add the gates stage to enrich-core's _require_gate_artifacts() in this phase:** The gate stage is new and its integration with enrich-core gating should be validated first. Add it as a documented follow-up.
- **Do not parse unparseable dates:** Events with `precision: "unknown"` and no `sort_date` should be excluded from date-ordering checks, not guessed at.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cycle detection | Custom cycle segmentation | `enrich_core._cycle_ranges()` pattern | Already proven correct; same restart-delimited logic needed here. Import the logic or duplicate the small function. |
| Date sorting | Custom date normalization | `ResolvedDate.sort_date` / `DateHint.normalized_hint` | Dates are already resolved by canonicalize. Use what exists. |
| Block ordinal mapping | Custom block position lookup | Load chronology_blocks.jsonl, build `{block_id: ordinal}` dict | Straightforward, no library needed. |
| Finding serialization | Custom JSON builder | Pydantic `model_dump_json(indent=2)` | Matches all existing gate output patterns. |

## Common Pitfalls

### Pitfall 1: Array Order vs Chronological Order
**What goes wrong:** Cross-event invariant rules fire false positives because events are not in chronological order in the JSON artifact.
**Why it happens:** The extraction process may emit events in discovery order (order encountered in filing text) rather than chronological order. The medivation data confirms this: a drop event dated Aug 10 appears after an executed event dated Aug 20 in the array.
**How to avoid:** Always sort events by `sort_date` (canonical) or `normalized_hint` (quote_first) before applying GATE-02 rules.
**Warning signs:** Tests pass on stec but fail on medivation with unexpected "proposal after executed" findings.

### Pitfall 2: Date-Less Events in Ordering Checks
**What goes wrong:** Events with `precision: "unknown"` and no parseable date cause None comparison errors or get silently excluded from cycle membership.
**Why it happens:** Some events (stec has 8 with unknown precision) have dates like "fourth quarter of 2012" or "mid-March, 2013" that the deterministic parser cannot resolve.
**How to avoid:** Exclude undated events from ordering-dependent checks. Emit a warning-level finding for undated events that would be relevant to cross-event rules (e.g., an undated NDA).
**Warning signs:** `TypeError: '<' not supported between instances of 'NoneType' and 'datetime.date'`.

### Pitfall 3: Quote-First vs Canonical Mode Dispatch
**What goes wrong:** Gates crash on `AttributeError` because they access `.actors.actors` when the artifacts are in `quote_first` mode (which uses `.raw_actors.actors`).
**Why it happens:** Same trap that tripped check.py and coverage.py in earlier phases. The `load_extract_artifacts()` dispatcher sets mode-specific fields to None.
**How to avoid:** Use the `_get_actor_event_records()` pattern from check.py. Write tests for both modes.
**Warning signs:** Tests pass for canonical fixtures but fail on quote_first fixtures.

### Pitfall 4: Cycle Boundaries and Restarted Events
**What goes wrong:** GATE-02 rule "executed must be last substantive event in cycle" fires incorrectly when there is a restarted event after executed.
**Why it happens:** `restarted` is itself a cycle boundary event. The rule needs to check within a cycle, not across cycles. stec has 1 restarted event.
**How to avoid:** Use cycle-local checking. Segment events into cycles first (same logic as enrich_core._cycle_ranges()), then check invariants within each cycle.
**Warning signs:** False positive on stec where `restarted` follows `terminated` which follows `executed`.

### Pitfall 5: Empty Verification Findings for Attention Decay
**What goes wrong:** GATE-04 attempts quartile binning on zero failures and produces division-by-zero or meaningless statistics.
**Why it happens:** Both stec and medivation currently have 0 verification failures. Many deals will pass verify cleanly.
**How to avoid:** When verification_findings.json contains 0 failures, report a neutral attention_decay object: quartile_counts=[0,0,0,0], hot_spots=[], decay_score=1.0 (perfect uniformity means no decay detected). Short-circuit the analysis.
**Warning signs:** `ZeroDivisionError` in quartile calculation or decay score formula.

### Pitfall 6: Failing to Update enrich-core Gate Requirements
**What goes wrong:** enrich-core's `_require_gate_artifacts()` does not know about the new gates stage. Running `enrich-core` does not check whether gates passed.
**Why it happens:** The gates stage is inserted between coverage and enrich-core, but enrich-core only checks check_report, verification_log, and coverage_summary.
**How to avoid:** Update `_require_gate_artifacts()` to also require the gates report. However, this must be done carefully -- if gates fail, enrich-core should refuse to run.
**Warning signs:** enrich-core runs successfully even though gates found blockers.

## Code Examples

### Gate Function Pattern (following check.py)
```python
# Source: skill_pipeline/check.py pattern
def _gate_cross_event_proposal_after_executed(
    sorted_events: list,
    cycle_ranges: list[tuple[int, int]],
) -> list[GateFinding]:
    """GATE-02 Rule 1: No proposal after executed in same cycle."""
    findings: list[GateFinding] = []
    for cycle_start, cycle_end in cycle_ranges:
        executed_idx = None
        for idx in range(cycle_start, cycle_end + 1):
            evt = sorted_events[idx]
            if evt.event_type == "executed":
                executed_idx = idx
            elif evt.event_type == "proposal" and executed_idx is not None:
                findings.append(
                    GateFinding(
                        gate_id="cross_event_logic",
                        rule_id="proposal_after_executed",
                        severity="blocker",
                        description=(
                            f"Proposal {evt.event_id} occurs after executed event "
                            f"{sorted_events[executed_idx].event_id} in same cycle."
                        ),
                        event_ids=[evt.event_id, sorted_events[executed_idx].event_id],
                    )
                )
    return findings
```

### Attention Decay Analysis Pattern
```python
# Source: GATE-04 design from CONTEXT.md D-08, D-09
def _gate_attention_decay(
    verification_findings: list[dict],
    span_index: dict[str, SpanRecord],
    blocks: list[ChronologyBlock],
) -> GateAttentionDecay:
    """Cluster verification failures by block position quartile."""
    block_ordinals = {b.block_id: b.ordinal for b in blocks}
    total_blocks = len(blocks)

    # Map each failure to a block ordinal
    failure_ordinals: list[int] = []
    for finding in verification_findings:
        for block_id in finding.get("block_ids", []):
            ordinal = block_ordinals.get(block_id)
            if ordinal is not None:
                failure_ordinals.append(ordinal)

    if not failure_ordinals:
        return GateAttentionDecay(
            quartile_counts=[0, 0, 0, 0],
            hot_spots=[],
            decay_score=1.0,
        )

    # Bin into quartiles by block ordinal position
    q_size = total_blocks / 4
    quartile_counts = [0, 0, 0, 0]
    for ordinal in failure_ordinals:
        q_idx = min(int((ordinal - 1) / q_size), 3)
        quartile_counts[q_idx] += 1

    # Decay score: 1.0 = uniform, lower = concentrated
    # Using normalized entropy
    total = sum(quartile_counts)
    if total == 0:
        decay_score = 1.0
    else:
        import math
        max_entropy = math.log(4)
        entropy = -sum(
            (c / total) * math.log(c / total)
            for c in quartile_counts
            if c > 0
        )
        decay_score = round(entropy / max_entropy, 3) if max_entropy > 0 else 1.0

    return GateAttentionDecay(
        quartile_counts=quartile_counts,
        hot_spots=_find_hot_spots(failure_ordinals),
        decay_score=decay_score,
    )
```

### CLI Integration Pattern
```python
# Source: skill_pipeline/cli.py existing subcommand pattern
gates_parser = subparsers.add_parser(
    "gates",
    help="Run semantic gates on extracted skill artifacts.",
)
gates_parser.add_argument("--deal", required=True)
gates_parser.add_argument(
    "--project-root",
    type=Path,
    default=PROJECT_ROOT,
    help=argparse.SUPPRESS,
)

# In main():
if args.command == "gates":
    return run_gates(args.deal, project_root=args.project_root)
```

### Paths Extension Pattern
```python
# Source: skill_pipeline/paths.py existing pattern
# Add to SkillPathSet:
gates_dir: Path
gates_report_path: Path

# Add to build_skill_paths():
gates_dir = skill_root / "gates"
# ... include in return:
gates_dir=gates_dir,
gates_report_path=gates_dir / "gates_report.json",

# Add to ensure_output_directories():
paths.gates_dir.mkdir(parents=True, exist_ok=True)
```

### Deal-Agent Summary Extension Pattern
```python
# Source: skill_pipeline/deal_agent.py existing pattern
class GatesStageSummary(SkillModel):
    status: StageStatus
    blocker_count: int = 0
    warning_count: int = 0

# Add to DealAgentSummary:
gates: GatesStageSummary
```

## Integration Points Summary

The following files require modification:

| File | Change | Purpose |
|------|--------|---------|
| `skill_pipeline/gates.py` | NEW | All 4 gates and run_gates() |
| `skill_pipeline/models.py` | ADD | GateFinding, GateAttentionDecay, GateReport, GateReportSummary, GatesStageSummary models |
| `skill_pipeline/paths.py` | ADD | gates_dir, gates_report_path to SkillPathSet and build_skill_paths() |
| `skill_pipeline/cli.py` | ADD | `gates` subcommand |
| `skill_pipeline/deal_agent.py` | ADD | gates summary in DealAgentSummary |
| `skill_pipeline/enrich_core.py` | MODIFY | Add gates_report to _require_gate_artifacts() |
| `tests/test_skill_gates.py` | NEW | Tests for all 4 gates |
| `CLAUDE.md` | MODIFY | Insert gates in end-to-end flow, add artifact contract |

## GATE-02 Cross-Event Rules: Severity Matrix

| Rule | Invariant | Severity | Rationale |
|------|-----------|----------|-----------|
| proposal_after_executed | No proposal after executed in same cycle | blocker | Logically impossible; indicates event ordering or cycle assignment error |
| nda_after_drop | No NDA after drop without restarted in between | blocker | NDA signing after withdrawal is contradictory without restart |
| announcement_before_deadline | final_round_ann must precede final_round in same cycle | blocker | Deadline without prior announcement is structurally broken |
| executed_last_in_cycle | executed must be last substantive event in its cycle | warning | Press releases and drops from other bidders can legitimately follow; not always an error |
| nda_signer_downstream | NDA signers must appear in at least one downstream event | warning | Could be legitimate if bidder signed NDA but deal was dropped before any proposal; depends on data quality expectations |

**Note on Rule 4:** The medivation data shows a `drop` event (evt_044 for bidder_sanofi, dated Aug 10) that chronologically precedes `executed` (evt_040, dated Aug 20) but would follow it if not date-sorted. After date sorting, it correctly precedes executed. However, a `bid_press_release` (evt_041, Aug 22) legitimately follows `executed`. The rule must define "substantive" carefully: `{proposal, nda, drop, final_round_ann, final_round, executed}` are substantive; press releases, bidder_interest, ib_retention, and target_sale are not.

**Note on Rule 5:** This overlaps with GATE-03 per-actor lifecycle. The CONTEXT.md lists it as both a GATE-02 rule and the entire GATE-03 requirement. Implement it once in GATE-03 and reference it from the GATE-02 rule set to avoid duplicate findings.

## GATE-01 Temporal Consistency: Design Details

GATE-01 validates that event dates are consistent with the temporal phase of their evidence blocks. This uses the Phase 1 block annotations: `temporal_phase` (initiation/bidding/outcome/other) and `date_mentions`.

**Approach:**
1. For each event with a resolved date, find its evidence blocks via span -> block_id mapping
2. Compare event date against block date_mentions (where normalized dates exist)
3. Flag when an event date differs from its block date_mentions by more than a reasonable threshold

**Severity:**
- blocker: Event date contradicts block date by >2 years (almost certainly a misattribution)
- warning: Event date outside block's temporal_phase expected range (weaker signal)

**Handling undated blocks:** Many blocks have date_mentions with `normalized: null` (e.g., "November" without year). Skip these -- the check is only meaningful when both the event date and block date_mention are parseable.

**Deal with few datable blocks:** If fewer than 3 blocks have parseable date_mentions, skip the temporal consistency check entirely (emit informational note, not a finding).

## GATE-04 Attention Decay: Design Details

**Input:** `verification_findings.json` (findings array) + `spans.json` (span -> block mapping) + `chronology_blocks.jsonl` (block ordinals)

**Flow:**
1. Load verification findings that have `block_ids` populated
2. Map each finding's `block_ids` to ordinals using the block ordinal index
3. Bin failure counts into 4 quartiles by block ordinal position
4. Identify hot spots: contiguous regions of 3+ blocks with failures within a 5-block window
5. Compute decay score using normalized entropy across quartiles

**Decay score interpretation:**
- 1.0: Failures uniformly distributed (no attention decay pattern)
- 0.7-1.0: Mild concentration, likely noise
- 0.3-0.7: Moderate concentration, suggests attention pattern
- 0.0-0.3: Severe concentration, likely attention decay

**Threshold recommendation:** No automatic pass/fail threshold per D-08. Include the score and let the human consumer decide. A diagnostic note at score < 0.5 reading "Attention decay pattern detected: failures concentrated in [quartile names]" would be helpful.

**Edge cases:**
- 0 findings: Return neutral report (decay_score=1.0, all counts zero)
- 1-2 findings: Return computed values but add note "too few failures for statistical significance"
- All findings in one block: Likely a single bad quote, not attention decay. Note this.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Structural checks only (check.py) | + Evidence grounding (verify.py) | Phase 3 (2026-03) | Caught quote mismatches |
| Evidence grounding only | + Coverage audit (coverage.py) | Phase 3 (2026-03) | Caught missed evidence cues |
| Coverage audit only | + Semantic gates (this phase) | Phase 4 (2026-03) | Catches logically impossible event sequences |

## Open Questions

1. **Should GATE-02 "executed_last_in_cycle" be a blocker or warning?**
   - What we know: Medivation has a drop after executed that is correctly date-ordered before it. Press releases legitimately follow.
   - What's unclear: Whether a blocker is appropriate when considering edge cases.
   - Recommendation: Use warning severity. The medivation data shows this is not always a hard error. Promote to blocker in future phases if false positive rate is low.

2. **How to handle quote_first mode for GATE-01?**
   - What we know: In quote_first mode, events have `DateHint` (raw_text + normalized_hint) not `ResolvedDate` (sort_date). Spans don't exist yet.
   - What's unclear: Whether temporal consistency is meaningful before canonicalization.
   - Recommendation: For quote_first mode, use `QuoteEntry.block_id` to find blocks, and `DateHint.normalized_hint` for date comparison. Skip GATE-04 in quote_first mode since it needs span data.

3. **Should enrich-core refuse to run if gates fail, starting immediately?**
   - What we know: enrich-core currently requires check pass + verify pass + coverage pass.
   - What's unclear: Whether introducing gates as a hard prerequisite immediately is safe for the existing 9-deal corpus.
   - Recommendation: Add the gates prerequisite to enrich-core but ensure all existing deals pass the new gates first. If any deal fails, fix the gate rules or add that deal-specific fix before updating enrich-core.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (installed, 203 tests current) |
| Config file | pyproject.toml |
| Quick run command | `python -m pytest tests/test_skill_gates.py -x -q` |
| Full suite command | `python -m pytest -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GATE-01 | Temporal consistency: date vs block position | unit | `python -m pytest tests/test_skill_gates.py::test_temporal_consistency_blocker -x` | Wave 0 |
| GATE-01 | Skip when < 3 datable blocks | unit | `python -m pytest tests/test_skill_gates.py::test_temporal_consistency_skip_sparse -x` | Wave 0 |
| GATE-02 | Proposal after executed -> blocker | unit | `python -m pytest tests/test_skill_gates.py::test_proposal_after_executed -x` | Wave 0 |
| GATE-02 | NDA after drop without restart -> blocker | unit | `python -m pytest tests/test_skill_gates.py::test_nda_after_drop -x` | Wave 0 |
| GATE-02 | Announcement before deadline | unit | `python -m pytest tests/test_skill_gates.py::test_announcement_before_deadline -x` | Wave 0 |
| GATE-02 | Executed last in cycle (warning) | unit | `python -m pytest tests/test_skill_gates.py::test_executed_last_in_cycle -x` | Wave 0 |
| GATE-02 | Undated events excluded from ordering checks | unit | `python -m pytest tests/test_skill_gates.py::test_undated_events_excluded -x` | Wave 0 |
| GATE-03 | NDA signer missing from downstream -> warning | unit | `python -m pytest tests/test_skill_gates.py::test_nda_signer_missing_downstream -x` | Wave 0 |
| GATE-03 | All NDA signers present -> pass | unit | `python -m pytest tests/test_skill_gates.py::test_nda_signers_all_present -x` | Wave 0 |
| GATE-04 | Zero failures -> neutral report | unit | `python -m pytest tests/test_skill_gates.py::test_attention_decay_no_failures -x` | Wave 0 |
| GATE-04 | Concentrated failures -> low decay score | unit | `python -m pytest tests/test_skill_gates.py::test_attention_decay_concentrated -x` | Wave 0 |
| GATE-04 | Uniform failures -> high decay score | unit | `python -m pytest tests/test_skill_gates.py::test_attention_decay_uniform -x` | Wave 0 |
| CLI | `skill-pipeline gates --deal slug` subcommand | unit | `python -m pytest tests/test_skill_gates.py::test_gates_cli_subcommand -x` | Wave 0 |
| Integration | stec passes all gates | integration | `python -m pytest tests/test_skill_gates.py::test_stec_gates_pass -x` | Wave 0 |
| Integration | medivation tested against new gates | integration | `python -m pytest tests/test_skill_gates.py::test_medivation_gates -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_skill_gates.py -x -q`
- **Per wave merge:** `python -m pytest -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_skill_gates.py` -- covers all GATE-01 through GATE-04 requirements
- [ ] Test fixtures for: quote_first gates, canonical gates, attention decay with synthetic failures
- [ ] No conftest.py exists; fixture helpers will be inline in test file (consistent with existing test files)

## Sources

### Primary (HIGH confidence)
- `skill_pipeline/check.py` -- structural gate pattern (248 lines, verified structure)
- `skill_pipeline/verify.py` -- evidence gate pattern (584 lines, finding model structure)
- `skill_pipeline/coverage.py` -- coverage gate pattern (377 lines, summary model)
- `skill_pipeline/models.py` -- all Pydantic models (533 lines, CheckFinding/VerificationFinding patterns)
- `skill_pipeline/paths.py` -- path contract (81 lines, SkillPathSet structure)
- `skill_pipeline/cli.py` -- CLI subcommand pattern (258 lines)
- `skill_pipeline/enrich_core.py` -- cycle detection, event sorting, gate prerequisites (494 lines)
- `skill_pipeline/extract_artifacts.py` -- mode dispatch (84 lines)
- `data/skill/stec/extract/events_raw.json` -- 39 events, 8 unknown-precision dates
- `data/skill/medivation/extract/events_raw.json` -- 42 events, post-executed drop confirmed
- `data/skill/stec/extract/spans.json` -- 165 spans, 58 unique block_ids referenced
- `data/skill/stec/verify/verification_findings.json` -- 0 findings (clean pass)
- `data/skill/medivation/verify/verification_findings.json` -- 0 findings (clean pass)

### Secondary (MEDIUM confidence)
- `.planning/phases/04-enhanced-gates/04-CONTEXT.md` -- all locked decisions (D-01 through D-09)
- `.planning/REQUIREMENTS.md` -- GATE-01 through GATE-04 requirement definitions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, purely internal Python code following established patterns
- Architecture: HIGH -- directly mirrors check.py/verify.py/coverage.py patterns verified in code
- Pitfalls: HIGH -- confirmed with real data analysis on stec and medivation artifacts
- Cross-event rules: HIGH -- validated against live event data; medivation confirms real violations exist
- Attention decay: MEDIUM -- design is sound but both test deals have 0 verify failures, so real-world behavior is untested

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable domain, no external dependencies)
