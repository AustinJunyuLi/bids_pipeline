---
phase: quick
plan: 260329-hyh
type: execute
wave: 1
depends_on: []
files_modified:
  - skill_pipeline/verify.py
  - tests/test_skill_verify.py
  - .claude/skills/deal-agent/SKILL.md
autonomous: true
requirements: []
---

<objective>
Fix four deal-agent orchestrator issues found during meticulous procedure trace.

Purpose: The deal-agent SKILL.md procedure has three workflow gaps (compose-prompts
event packets never generated, db-load/db-export not re-run after enrich-deal,
stale gates after verify-extraction repairs), and verify.py has a code bug where
canonical-branch quote findings are silently dropped.

Output: Corrected verify.py with regression test, corrected SKILL.md procedure.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@.claude/skills/deal-agent/SKILL.md
@skill_pipeline/verify.py (lines 484-521 — _collect_verification_findings)
@tests/test_skill_verify.py (lines 455-476 — existing canonical test pattern)
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Fix verify.py canonical quote findings bug and add regression test</name>
  <files>skill_pipeline/verify.py, tests/test_skill_verify.py</files>
  <behavior>
    - Test: After canonicalize, verify on an artifact with a deliberately broken span
      anchor_text produces a quote_verification finding. Currently the canonical
      branch (lines 506-510) computes quote_findings and quote_checks but never
      appends them to the findings list or adds quote_checks to total_checks.
      The test must confirm that quote_verification findings from the canonical
      branch appear in the output findings artifact.
  </behavior>
  <action>
    **Bug location:** `skill_pipeline/verify.py`, function `_collect_verification_findings`,
    lines 506-510. The `else` branch (canonical mode) calls
    `_check_quote_verification_canonical()` and assigns to `quote_findings` and
    `quote_checks`, but never runs `findings.extend(quote_findings)` or
    `total_checks += quote_checks`.

    **Fix:** Add two lines after line 510 (after the canonical branch call), before
    the `evidence_findings` block:

    ```python
        findings.extend(quote_findings)
        total_checks += quote_checks
    ```

    The fixed block should read:

    ```python
    else:
        quote_findings, quote_checks = _check_quote_verification_canonical(
            artifacts,
            document_lines,
        )
        findings.extend(quote_findings)
        total_checks += quote_checks
    ```

    **Regression test:** Add `test_verify_canonical_quote_findings_collected` to
    `tests/test_skill_verify.py`. Pattern:

    1. Call `_write_verify_fixture_for_clean_pass(tmp_path)`.
    2. Call `run_canonicalize("imprivata", project_root=tmp_path)` to produce canonical artifacts.
    3. Read `spans.json`, corrupt one span's `anchor_text` to a string that will
       not match the filing text (e.g., "ZZZZZ_NONEXISTENT_TEXT_ZZZZZ").
    4. Write the corrupted spans back.
    5. Call `run_verify("imprivata", project_root=tmp_path)`.
    6. Assert `exit_code == 1`.
    7. Assert at least one finding has `check_type == "quote_verification"` in the
       output findings. This test would FAIL on the unfixed code (findings silently
       dropped) and PASS on the fixed code.

    Follow the existing test helper pattern: use `_read_findings_list(paths.verification_findings_path)`.
  </action>
  <verify>
    <automated>cd /home/austinli/Projects/bids_pipeline && python -m pytest tests/test_skill_verify.py::test_verify_canonical_quote_findings_collected -xvs</automated>
  </verify>
  <done>
    - The canonical branch in _collect_verification_findings appends quote_findings
      to findings and adds quote_checks to total_checks.
    - Regression test proves canonical quote_verification findings appear in output.
    - Full verify test suite passes: `python -m pytest tests/test_skill_verify.py -x`
  </done>
</task>

<task type="auto">
  <name>Task 2: Fix deal-agent SKILL.md procedure (3 workflow gaps)</name>
  <files>.claude/skills/deal-agent/SKILL.md</files>
  <action>
    Apply three targeted edits to `.claude/skills/deal-agent/SKILL.md`:

    **Fix 1 (HIGH): Split compose-prompts into actor and event packet steps.**

    Current step 3a runs compose-prompts once with no --mode flag, which defaults to
    `--mode all`. But `--mode all` only generates actor packets (compose_prompts.py
    lines 407-408: `compose_actors = mode in ("actors", "all")`,
    `compose_events = mode == "events"`). Event packets are never generated because
    `--mode events` is never called after actor extraction produces `actors_raw.json`.

    Replace step 3a with two steps:

    - Step 3a: `skill-pipeline compose-prompts --deal <slug> --mode actors`
      Gate: prompt/manifest.json exists, actor_packet_count > 0.
      Generates actor prompt packets consumed by extract-deal for actor extraction.

    - New step 4a (after step 4 extract-deal, before step 4a canonicalize):
      `skill-pipeline compose-prompts --deal <slug> --mode events`
      Gate: prompt/manifest.json updated, event_packet_count > 0.
      Generates event prompt packets. Requires actors_raw.json from step 4.

    Renumber subsequent steps accordingly. The existing step 4 (extract-deal) stays
    where it is but the canonicalize step (old 4a) shifts to accommodate the new
    event packet step.

    Actually, on reflection, the renumbering gets messy. Use this cleaner approach:
    - Step 3a stays but explicitly says `--mode actors` and notes it generates actor
      packets only.
    - Insert a new step 4-post between extract-deal (step 4) and canonicalize (old 4a):
      "Run `skill-pipeline compose-prompts --deal <slug> --mode events`"
      with note that this requires actors_raw.json from step 4.
    - Canonicalize becomes 4b (was 4a). Check becomes 4c (was 4b).

    Renumber the full procedure cleanly from 1 through the end.

    **Fix 2 (MEDIUM): Add db-load/db-export re-run after enrich-deal.**

    Current procedure runs db-load (7a) and db-export (7b) BEFORE enrich-deal (8).
    After enrich-deal writes enrichment.json with dropout_classifications, the
    DuckDB and CSV are stale.

    After current step 8 (enrich-deal), add:

    - Step 8a: Re-run `skill-pipeline db-load --deal <slug>`
      Note: Picks up enrichment.json overlay written by enrich-deal.
      Gate: pipeline.duckdb updated with interpretive enrichment data.

    - Step 8b: Re-run `skill-pipeline db-export --deal <slug>`
      Note: Regenerates deal_events.csv with dropout_classifications from enrichment.
      Gate: deal_events.csv updated and non-empty.

    **Fix 3 (LOW-MEDIUM): Add re-validation note after verify-extraction.**

    After step 6 (verify-extraction), add a bracketed note:

    "Note: If verify-extraction made structural changes (added/removed events,
    changed dates, modified actor references), re-run steps 4c through 5b
    (check, verify, coverage, gates) before proceeding to enrich-core. Enrich-core
    uses gate artifacts that may be stale after structural repairs."

    Also update the Skills table at the top to reflect the compose-prompts split:
    row 0a becomes "compose-prompts --mode actors" and a new row 0b becomes
    "compose-prompts --mode events" (requires actors_raw.json). The existing 0b
    (extract-deal) shifts to 0c.
  </action>
  <verify>
    <automated>cd /home/austinli/Projects/bids_pipeline && grep -c "mode actors\|mode events" .claude/skills/deal-agent/SKILL.md && grep -c "Re-run.*db-load\|Re-run.*db-export" .claude/skills/deal-agent/SKILL.md && grep -c "structural changes" .claude/skills/deal-agent/SKILL.md</automated>
  </verify>
  <done>
    - Step 3a explicitly uses --mode actors.
    - A new step after extract-deal calls --mode events.
    - Steps 8a and 8b re-run db-load and db-export after enrich-deal.
    - A note after verify-extraction warns about re-validation when structural
      changes occurred.
    - Skills table updated to reflect compose-prompts split.
    - Procedure step numbering is consistent and sequential.
  </done>
</task>

</tasks>

<verification>
1. Full verify test suite: `python -m pytest tests/test_skill_verify.py -x`
2. Full test suite: `python -m pytest -x -q`
3. SKILL.md procedure reads coherently end-to-end with no numbering gaps.
4. No other test files or source files affected.
</verification>

<success_criteria>
- verify.py canonical branch appends quote_findings and increments total_checks
- Regression test proves the fix catches previously-silent canonical quote findings
- deal-agent SKILL.md procedure generates both actor and event prompt packets
- deal-agent SKILL.md re-runs db-load and db-export after enrich-deal
- deal-agent SKILL.md warns about stale gates after verify-extraction repairs
- Full pytest suite green
</success_criteria>

<output>
After completion, create `.planning/quick/260329-hyh-fix-4-deal-agent-orchestrator-issues/260329-hyh-SUMMARY.md`
</output>
