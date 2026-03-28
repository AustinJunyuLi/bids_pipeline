# Phase 4: Enhanced Gates - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Add 4 new deterministic semantic checks that catch error classes the current structural and evidence gates miss. These checks validate whether extracted events make logical sense as an M&A deal narrative, independent of whether the data is structurally valid or evidence-grounded.

</domain>

<decisions>
## Implementation Decisions

### Gate Architecture
- **D-01:** The 4 new gates live in a new dedicated stage (`gates.py` or `semantic_check.py`), separate from the existing check/verify/coverage files. Clean separation: structural checks in check.py, evidence validation in verify.py, coverage audit in coverage.py, semantic checks in the new file.
- **D-02:** The new stage runs after coverage and before enrich-core in the pipeline sequence: `check -> verify -> coverage -> gates -> enrich-core`. Semantic gates act as a final quality filter before enrichment.
- **D-03:** The new stage gets its own CLI command (e.g., `skill-pipeline gates --deal <slug>`) and its own output directory under `data/skill/<slug>/gates/`.

### Finding Severity Policy
- **D-04:** Findings use tiered severity. Each gate rule has a pre-assigned severity level. High-confidence violations (impossible sequences like proposal-after-executed) are blockers. Lower-confidence checks (date precision mismatches, attention clustering patterns) are warnings. The gate stage passes overall unless at least one blocker exists.
- **D-05:** The severity assignment is per-rule, not per-gate. A single gate (e.g., GATE-02 cross-event logic) can produce both blocker and warning findings depending on which rule fired.

### Cross-Event Domain Rules (GATE-02)
- **D-06:** Start with 5-7 core invariant rules that are almost never wrong. Do not attempt a comprehensive 15-20 rule set in this phase. The initial rule set should include at minimum:
  1. No `proposal` after `executed` in the same cycle
  2. No `nda` after `drop` without a `restarted` in between
  3. `final_round_ann` must precede `final_round` (deadline requires announcement)
  4. `executed` must be the last substantive event in its cycle
  5. NDA signers must appear in at least one downstream event (proposal, drop, or outcome)
- **D-07:** Additional rules beyond the initial 5-7 will be added in future phases based on real false-positive data from running these gates across the 9-deal corpus. Do not pre-build a rule suppression mechanism.

### Attention Decay Diagnostics (GATE-04)
- **D-08:** Attention decay produces a diagnostic report only — no automatic re-extraction trigger. The report includes: failure count by block-position quartile, hot spots (blocks with 3+ failures clustered nearby), and a decay score (0.0 to 1.0 where 1.0 = perfect uniform distribution of failures, lower = concentrated failures indicating attention loss).
- **D-09:** The attention decay diagnostic analyzes verify findings (quote match failures) by the block position of the associated quotes. It consumes the verification_findings.json and spans.json outputs, not raw extraction artifacts.

### Claude's Discretion
- Exact file name and module structure for the new stage (gates.py vs semantic_check.py vs enhanced_gates.py)
- Internal organization of the 4 gates within the module (separate functions, classes, or a registry pattern)
- Exact threshold for the attention decay score (if any) to distinguish "healthy" from "concerning" patterns
- How to handle deals with very few events (e.g., < 5) where statistical clustering is meaningless
- Exact Pydantic model names for the gate report and findings

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope
- `.planning/ROADMAP.md` — Phase 4 goal, scope, exit criteria, and requirements (GATE-01 through GATE-04)
- `.planning/REQUIREMENTS.md` — GATE-01 (temporal consistency), GATE-02 (cross-event logic), GATE-03 (per-actor lifecycle), GATE-04 (attention decay)
- `.planning/PROJECT.md` — project constraints (correctness priority, fail-fast, filing-text-only truth)

### Existing Gate Implementation
- `skill_pipeline/check.py` — current structural gate (248 lines). Pattern for check functions, finding models, report structure.
- `skill_pipeline/verify.py` — current evidence gate (584 lines). Quote validation, verification findings, verification log. GATE-04 consumes its outputs.
- `skill_pipeline/coverage.py` — current coverage gate (377 lines). Evidence-to-event matching.

### Models and Data Contracts
- `skill_pipeline/models.py` — `CheckFinding`, `SkillCheckReport`, `VerificationFinding`, `SkillVerificationLog`, `RawSkillEventRecord`, `RawSkillActorRecord`, `FormalitySignals`, `MoneyTerms`
- `skill_pipeline/extract_artifacts.py` — `LoadedExtractArtifacts`, format detection, mode dispatch (`quote_first` vs `canonical`)
- `skill_pipeline/paths.py` — `SkillPathSet`, `build_skill_paths()` — new output directory pattern

### Block Metadata (from Phase 1)
- `skill_pipeline/pipeline_models/source.py` — `ChronologyBlock` with `date_mentions`, `entity_mentions`, `evidence_density`, `temporal_phase` annotation fields

### Prior Phase Context
- `.planning/phases/03-quote-before-extract/03-CONTEXT.md` — quote-first format decisions (quote_ids, block_ids on quotes)
- `.planning/phases/01-foundation-annotation/01-CONTEXT.md` — block annotation decisions (temporal phase, evidence density)

### Pipeline Flow
- `skill_pipeline/cli.py` — CLI entry points; new `gates` subcommand needed
- `CLAUDE.md` — end-to-end flow documentation (needs gates inserted between coverage and enrich-core)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CheckFinding` / `SkillCheckReport` models in `models.py` — the gate report can follow the same finding-based structure with `check_id`, `severity`, `description`, `event_ids`, `actor_ids` fields.
- `_get_actor_event_records()` in `check.py` — dispatches on `quote_first` vs `canonical` mode. The new gates need the same dispatch pattern.
- `_load_document_lines()` and `_load_chronology_blocks()` in `verify.py` — needed for GATE-01 (temporal consistency) to compare event dates against block positions.
- `build_skill_paths()` in `paths.py` — extend with a `gates_dir` property for `data/skill/<slug>/gates/`.

### Established Patterns
- Gate stages return exit code 0 (pass) or 1 (fail). The new stage should follow the same convention.
- Findings are written as JSON (`*_report.json` or `*_findings.json`) with a summary object containing counts.
- CLI subcommands follow the pattern: `run_<stage>()` function called from `cli.py` with `--deal <slug>` argument.

### Integration Points
- `cli.py` — new `gates` subcommand registration
- `paths.py` — new `gates_dir` and `gates_report_path` on `SkillPathSet`
- `CLAUDE.md` end-to-end flow — insert `gates` between `coverage` and `enrich-core`
- `deal_agent.py` — add gates summary to the deal status report

</code_context>

<specifics>
## Specific Ideas

- GATE-01 (temporal consistency) can use the `date_mentions` and `temporal_phase` annotations from Phase 1's block metadata. An event dated "March 2009" in a block annotated `temporal_phase: bidding` with `date_mentions: ["June 2013"]` is a red flag.
- GATE-02 (cross-event logic) operates on sorted event lists. Sort events by normalized_hint date, then walk the sequence checking invariant rules. Each rule is a function that takes the event list and returns findings.
- GATE-03 (per-actor lifecycle) is essentially a set-membership check: build the set of NDA signers, then verify each appears in at least one proposal, drop, or outcome event's actor_ids.
- GATE-04 (attention decay) does not need access to the filing text itself — it only needs block positions from spans.json and failure counts from verification_findings.json.

</specifics>

<deferred>
## Deferred Ideas

- Comprehensive cross-event rule set (15-20 rules) — defer until false-positive data from the initial 5-7 rules across the 9-deal corpus informs which rules are safe to add
- Automatic re-extraction trigger from attention decay diagnostic — defer to Phase 5 or later
- Rule suppression mechanism for known edge cases — defer until real false positives are observed

</deferred>

---

*Phase: 04-enhanced-gates*
*Context gathered: 2026-03-28*
