# Domain Pitfalls: v1.1 Reconciliation + Execution-Log Quality Fixes

**Domain:** Adding enrichment rule fixes, new event types, inference improvements, and deterministic stage hardening to a working 9-deal SEC M&A extraction pipeline
**Researched:** 2026-03-29
**Context:** 265 passing tests, 9 completed deals, 12 deterministic stages, 4 local-agent skills

---

## Critical Pitfalls

Mistakes that cause regressions in the existing 9-deal corpus, corrupt canonical artifacts, or silently change classification semantics. Each pitfall below is grounded in evidence from the actual codebase, the 7-deal fresh rerun execution logs, and the cross-deal reconciliation analysis.

---

### Pitfall 1: Enrichment Rule Priority Inversion Regresses Existing Classifications

**What goes wrong:** The bid_type classification in `enrich_core.py` uses a numbered-rule cascade (Rule 1 -> Rule 2 -> Rule 2.5 -> Rule 3 -> Rule 4). The v1.1 fix must make Rule 2.5 (after final round = Formal) take priority over Rule 1 (IOI/preliminary/non-binding language = Informal). If this is implemented as a simple reordering of the `if` chain, it could flip classifications for early-round proposals that legitimately ARE informal but happen to appear after a filing mentions "final round" in a different context.

**Why it happens:** The current Rule 1 checks `mentions_indication_of_interest`, `mentions_preliminary`, `mentions_non_binding`, and `contains_range`. These are binary booleans on the event's `formality_signals` object. Rule 2.5 checks `after_final_round_deadline` and `after_final_round_announcement`. The fix needs to make Rule 2.5 override Rule 1 specifically for proposals that are chronologically after a final round, but the `formality_signals` booleans are set by the LLM extraction, not by deterministic pipeline logic. If the LLM sets `after_final_round_announcement=True` on a proposal that is actually pre-final-round (an extraction error), the new priority will misclassify it as Formal.

**Consequences:** The 5+ deals affected by the current bug (mac-gray, stec, prov-worcester, imprivata, penford) get correct classifications, but previously-correct Informal classifications in other deals could flip to Formal. The reconciliation analysis specifically shows imprivata's `$19.25 best-and-final` and mac-gray's `Party A $18` and `Party B $17-19` should become Formal. But if the rule reordering is too aggressive, early-round IOIs in stec or zep that correctly have `mentions_indication_of_interest=True` could be misclassified.

**Prevention:**
1. **Snapshot all 9 deals' current bid_classifications before the fix.** Run `skill-pipeline enrich-core` for every deal, save outputs. After the fix, diff all 9 deals' classifications and verify every change is intentional.
2. **Do not simply reorder the if-chain.** Instead, make Rule 2.5 a pre-check that short-circuits Rule 1. The logic should be: "If after_final_round AND has informal signals, the final-round context wins." This is narrower than "always check final-round before informal signals."
3. **Add per-deal regression tests.** For each of the 5 affected deals, add a test with the exact formality_signals from the real event, asserting the corrected classification. Also add tests for events that should remain Informal (early-round IOIs).
4. **Test the `contains_range` edge case.** A final-round proposal with a price range (e.g., "$17-19") legitimately triggers `contains_range=True`. The fix should still classify this as Formal if it's a final-round response.

**Warning signs:** More than 5 classification changes across the 9-deal corpus. Any deal that had zero classification issues in reconciliation suddenly showing changes.

**Detection:** Before/after diff of `deterministic_enrichment.json` across all 9 deals.

**Phase:** Phase 1 (enrichment rule fixes). Must be addressed first because downstream formal_boundary computation depends on bid_classifications.

---

### Pitfall 2: New Event Types Break Downstream Consumers Without Schema Migration

**What goes wrong:** Adding new event types (round milestones, DropTarget, verbal indications) to the `Literal` union in `models.py` requires updating every downstream consumer that pattern-matches on event_type. The Pydantic `Literal` type provides compile-time safety for the schema, but the *behavioral* consumers -- `enrich_core.py`, `gates.py`, `coverage.py`, `check.py`, `db_load.py`, `db_schema.py` -- all have hardcoded sets of event types they handle.

**Why it happens:** The codebase uses `Literal[...]` unions for event_type validation (correct), but downstream logic uses different subsets of those types for different purposes:

- `gates.py` line 24: `SUBSTANTIVE_EVENT_TYPES` frozenset controls which events get temporal consistency and cross-event logic checks
- `gates.py` line 45: `EVENT_PHASES` dict controls temporal phase validation
- `gates.py` line 68: `ROUND_ANNOUNCEMENT_RULES` dict controls announcement-before-deadline checks
- `enrich_core.py` line 20: `ROUND_PAIRS` controls round pairing
- `coverage.py` line 227: `_suggested_event_types` maps cue families to expected event types
- `check.py`: proposal-specific checks only fire for `event_type == "proposal"`
- `db_load.py` / `db_schema.py`: event table schema must accommodate any new fields

If a new event type is added to the `Literal` union but not to these behavioral sets, the event will pass schema validation but be silently ignored by enrichment, gates, and coverage.

**Consequences:** New event types that are semantically important (e.g., `drop_target` should participate in cross-event logic, `verbal_indication` might need bid_type classification) are created but not enriched, not gated, and not covered. The pipeline appears to work, but the new events are dead weight that confuses downstream consumers like `db-export`.

**Prevention:**
1. **Create a registry of event_type consumers.** Before adding any new type, grep for every location that references event types and document which sets/maps need updating.
2. **Add a regression test that validates event_type coverage.** The test should assert that every type in the `Literal` union appears in at least `SUBSTANTIVE_EVENT_TYPES` OR `EVENT_PHASES` OR is explicitly documented as exempt (e.g., `ib_retention` might not need cross-event logic checks).
3. **Add new types incrementally, one at a time.** Each new type gets its own PR with: schema change + all downstream consumer updates + tests for each consumer's behavior with the new type.
4. **For `drop_target` specifically:** It needs to participate in `_gate_actor_lifecycle` (it's a form of narrowing, not quite a "drop"), it needs coverage cues, and it needs to NOT trigger the NDA-gate in canonicalize (committee exclusions happen without NDA requirements).

**Warning signs:** A new event type passes `check` and `verify` but has no entries in `deterministic_enrichment.json`. Events that appear in `events_raw.json` but are absent from `deal_events.csv`.

**Detection:** Add a test that counts event types in the `Literal` union vs. event types handled in each downstream consumer. Mismatch = failure.

**Phase:** Phase 2 (new event types). Must come after enrichment rule fixes because new types may interact with bid_type classification.

---

### Pitfall 3: Canonicalize Duplicate quote_id Collisions Across Actor/Event Extraction Passes

**What goes wrong:** The two-pass extraction (actors first, then events) produces two independent quote arrays. If both passes use the same quote_id namespace (e.g., both start from `q_001`), `canonicalize.py` line 99-103 raises `ValueError("Duplicate quote_id ...")` when it concatenates the two quote lists. This was observed in production during the 7-deal rerun: "penford: canonicalize hit duplicate quote_id collisions; fixed by renumbering event-side quote ids above the actor-side max."

**Why it happens:** The extraction prompt asks the LLM to number quotes sequentially. Each pass starts from 1. The canonicalize stage concatenates `loaded.raw_actors.quotes + loaded.raw_events.quotes` (line 408) and iterates them, checking for duplicate IDs. The LLM has no knowledge of the actor-pass quote IDs when generating event-pass quotes.

**Consequences:** `canonicalize` fails hard (correct behavior -- fail-fast), but the fix during production was manual artifact surgery. Without hardening, every deal that uses the same quote_id prefix in both passes will hit this wall during the deterministic pipeline.

**Prevention:**
1. **Namespace quote_ids by extraction pass.** The canonicalize stage should prefix actor quotes with `a_` and event quotes with `e_` if collision is detected, rather than aborting. Alternatively, the prompt instructions should require different prefixes.
2. **Better: make canonicalize resilient to collision by auto-renumbering.** When a collision is detected, log it and renumber the later-pass quotes with a monotonically increasing suffix. This is safe because quote_ids are internal references that get replaced by span_ids during canonicalization anyway.
3. **Add a regression test for the collision case.** Create a fixture where actor and event quotes share `q_001` and verify canonicalize handles it gracefully.
4. **Do NOT silently drop colliding quotes.** The current fail-fast is correct in spirit but the fix should be deterministic renumbering, not manual surgery.

**Warning signs:** Canonicalize failures on deals that previously worked after re-extraction.

**Detection:** The `ValueError` is already loud. The pitfall is the manual fix, not the detection.

**Phase:** Phase 4 (canonicalize hardening). Can be addressed independently of enrichment or event type changes.

---

### Pitfall 4: Coverage False Positives Mask Real Gaps (or Real Gaps Mask False Positives)

**What goes wrong:** The coverage stage uses keyword heuristics to detect evidence cues that should have corresponding events. Two failure modes:

**Mode A (False positives masking real work):** The Zep execution log showed coverage flagging a "drop" cue from text like "reevaluating its interest" when the passage immediately continued with "moved forward with negotiations." The fix in v1.0 added a `has_continue_negotiation_language` suppression. Expanding suppression heuristics for v1.1 (e.g., suppressing contextual confidentiality-agreement mentions) risks over-suppressing legitimate cues.

**Mode B (Suppression hides real gaps):** The Saks execution log showed coverage flagging contextual confidentiality-agreement mentions (e.g., "which had executed a confidentiality agreement") as NDA cues when they were actually backward references to previously-extracted NDAs, not new NDA events. The fix correctly suppressed these, but if the suppression pattern is too broad, it could also suppress genuine NDA cues that happen to use similar language.

**Why it happens:** The coverage heuristic in `_classify_cue_family` (lines 84-224) uses substring matching against a curated list of phrases. Each new suppression heuristic (`references_prior_executed_nda`, `has_target_due_diligence_confidentiality_language`, `has_continue_negotiation_language`) is a negative pattern that reduces false positives but increases false negatives. The two forces are in tension: every suppression that removes a false positive could also remove a true positive with similar language.

**Consequences:** If suppression is too aggressive, the coverage gate passes even when events are genuinely missing. If suppression is too conservative, the coverage gate fails on deals where it shouldn't, forcing unnecessary extraction repairs that can introduce new errors.

**Prevention:**
1. **Test suppressions against all 9 deals' evidence_items.** For every new suppression heuristic, run it against the full corpus and verify which cues it suppresses. Each suppressed cue should be manually checked: is this a true false positive?
2. **Maintain a "known false positive" test corpus.** Each false positive that motivates a suppression heuristic becomes a test case. Each genuine NDA/drop/proposal that could be confused with a false positive also becomes a test case.
3. **Log suppression reasons.** When a cue is suppressed by a heuristic, include the suppression reason in the coverage findings at `info` severity (not error/warning). This creates an audit trail.
4. **Never suppress high-confidence cues without an explicit escape hatch.** If a cue has `confidence == "high"` and matches a critical cue family, suppression should require two matching heuristics, not one.

**Warning signs:** Coverage pass rate increasing across deals without corresponding extraction quality improvement. Coverage findings count dropping to zero on complex deals that previously had legitimate warnings.

**Detection:** Track coverage finding counts per deal across versions. A sudden drop without a corresponding extraction fix is suspicious.

**Phase:** Phase 3 (coverage hardening). Should come after new event types are added so the coverage cue vocabulary can be updated simultaneously.

---

### Pitfall 5: NDA Count Assertion Logic Breaks on Grouped Bidders

**What goes wrong:** The check stage's `_check_nda_count_gaps` (lines 174-219) compares the filing's asserted count of NDA signers per bidder kind against the grounded actor count. The production fix during the 7-deal rerun added `_counted_bidder_weight` to count grouped bidders by their `group_size` rather than as 1. But this creates a new failure mode: if a grouped bidder's `group_size` is wrong (set too high by the LLM), the check passes even when individual bidders are missing.

**Why it happens:** Grouped bidders (e.g., "Company 1 through Company 5") have `is_grouped=True` and `group_size=5`. The count assertion says "5 financial buyers signed NDAs." If the LLM creates one grouped bidder with `group_size=5`, the check passes. But if the filing actually names 3 of those 5 individually, the correct extraction has 3 named bidders + 1 grouped bidder with `group_size=2`. The check logic can't distinguish between "correct grouping" and "lazy grouping that hides missed extractions."

**Consequences:** The check gate passes when it shouldn't, allowing incompletely-extracted actor rosters through to enrichment and export. The pipeline produces fewer actor rows than the filing supports.

**Prevention:**
1. **Cross-validate group_size against named actors.** If an actor has `is_grouped=True` and `group_size=N`, verify that no more than `N` actors of the same `bidder_kind` are individually named in the same role. If there are `M` individually named actors, the grouped bidder's effective weight should be `max(0, N - M)`.
2. **Add regression tests for the specific Providence-Worcester case.** The fix was made during production; formalize it as a test.
3. **Do not allow group_size > filing assertion count.** If the filing asserts "6 strategic buyers signed NDAs" and the extraction has 4 named strategics plus a grouped strategic with `group_size=5`, the total (9) exceeds the assertion (6). This should be a warning.

**Warning signs:** Check passes with zero NDA count gaps on deals that previously had warnings. Grouped bidders appearing in deals where the filing names every bidder individually.

**Detection:** Compare grounded actor counts (with group_size weights) against filing assertions. Both under-count and over-count are informative.

**Phase:** Phase 3 (check hardening). Must come after new event types because DropTarget events may affect which actors are "active."

---

### Pitfall 6: Contextual Inference Rules Over-Trigger Beyond Their Domain

**What goes wrong:** The v1.1 milestone includes adding contextual `all_cash` inference (currently the pipeline only marks `all_cash=1` when the filing sentence explicitly says "cash"). Contextual inference means inferring from deal context -- e.g., if all of Bidder X's prior proposals were cash and the final proposal doesn't specify, infer cash. This inference can over-trigger in deals where the consideration structure changes (cash to stock+cash, cash to CVR+cash).

**Why it happens:** The reconciliation analysis specifically flags Providence-Worcester as a case where Alex marked `all_cash=1` on the `$21.15` offer but the actual consideration was "cash + CVR mix." Contextual inference from earlier all-cash bids would incorrectly propagate `all_cash=1` to this mixed-consideration proposal. The inference rule doesn't have visibility into consideration structure changes mid-deal.

**Consequences:** `all_cash` classification errors in the export CSV. These are subtle -- they don't cause pipeline failures, they cause incorrect research output. The pipeline's core value proposition is "filing-grounded correctness," and incorrect inference directly undermines that.

**Prevention:**
1. **Constrain inference to cases with strong evidence.** Only infer `all_cash=1` when: (a) the bidder's ALL prior proposals in the same cycle explicitly mention cash, AND (b) the current proposal does not mention any non-cash consideration (stock, CVR, earnout, contingent). Absence of "cash" alone is not sufficient.
2. **Never infer on the executed event.** The final deal terms are the highest-stakes classification. Require explicit evidence for the executed event's consideration structure.
3. **Add a "consideration_structure_change" gate.** If any event for a bidder mentions non-cash consideration, invalidate all contextual all_cash inferences for that bidder.
4. **Test against the Providence-Worcester CVR case.** This is the known failure case for naive contextual inference.

**Warning signs:** `all_cash=1` appearing on events where the filing mentions "contingent value rights," "stock," "equity," or "earnout." All_cash inference changing the export for deals that previously had null consideration fields.

**Detection:** Diff `deal_events.csv` before and after adding contextual inference. Every new `all_cash=1` value should be manually verifiable against the filing.

**Phase:** Phase 2 (inference improvements). Should come after enrichment rule priority fix because all_cash is an enrichment-level classification.

---

### Pitfall 7: DuckDB Transient Lock Between db-load and db-export

**What goes wrong:** The 7-deal rerun logged: "skill-pipeline db-export --deal zep hit a transient DuckDB lock immediately after db-load; retry succeeded once the short-lived lock-holder exited." DuckDB is single-writer by design. If `db-load` and `db-export` are called in rapid succession (or if a background process holds the WAL), `db-export` fails with a lock error.

**Why it happens:** DuckDB's write-ahead log (WAL) can hold a lock briefly after a write connection closes. The current code in `db_load.py` calls `con.close()` (line 51) and returns, but the WAL flush may not be complete by the time `db-export` opens a new connection. In concurrent execution environments (multiple agents, background processes), the lock window is unpredictable.

**Consequences:** `db-export` fails transiently. The current fix was manual retry, but in automated pipelines this becomes a hard failure that requires human intervention.

**Prevention:**
1. **Add a short retry loop in `db_export.py` connection setup.** If `duckdb.connect()` raises a lock error, wait 1 second and retry up to 3 times. This is the correct fix for transient WAL locks.
2. **Do NOT add retries to `db_load.py`.** The load stage is a write operation and should fail fast on lock conflicts. Only the read-only export should retry.
3. **Open `db-export` connections as read-only.** The current code in `db_schema.py` line 106 uses `read_only=read_only` parameter. Verify that `db_export.py` always passes `read_only=True` to avoid write-lock contention.
4. **Add a test for the lock-retry behavior.** Create a test that holds a write lock on the DuckDB file and verifies that db-export retries and eventually succeeds.
5. **Do NOT add a general retry/lock abstraction.** The lock issue is specific to the db-load -> db-export transition. A general retry wrapper would mask data corruption elsewhere.

**Warning signs:** Intermittent `db-export` failures that succeed on retry. Multiple processes accessing `pipeline.duckdb` simultaneously.

**Detection:** The DuckDB error message is explicit. Log it rather than swallowing it.

**Phase:** Phase 4 (stage hardening). Independent of enrichment or event type changes.

---

### Pitfall 8: Concurrent Artifact Writes Corrupt Schema State

**What goes wrong:** The 7-deal rerun showed the most dangerous production bug: "zep events_raw.json reverted to quote-first while actors_raw.json remained canonical; likely overlapping worker write after canonicalize." This means one process ran canonicalize (upgrading both files to canonical schema), then another process overwrote `events_raw.json` with its own quote-first version, creating a mixed-schema state that violates the pipeline's core invariant.

**Why it happens:** The execution model spawns parallel workers per deal, each with ownership of `data/skill/<slug>/`. But if worker boundaries are not enforced (e.g., a background process from a previous launch is still running), two processes can write to the same artifact file. The pipeline has no file-level locking because DuckDB is the only shared resource and artifact files are per-deal.

**Consequences:** Mixed schema state causes cryptic failures in every downstream stage. `check.py` tries to load canonical actors but quote-first events; the `load_extract_artifacts` function may return a mode that doesn't match one of the files. This is data corruption, not a transient error.

**Prevention:**
1. **Add a schema-mode consistency check at the start of every deterministic stage.** Before `check`, `verify`, `coverage`, `gates`, and `enrich-core` run, verify that `actors_raw.json` and `events_raw.json` are in the same schema mode (both quote-first or both canonical). If they differ, fail hard with a diagnostic message.
2. **Add a "canonicalize complete" sentinel file.** After `canonicalize` writes all three files (`actors_raw.json`, `events_raw.json`, `spans.json`), write a `canonicalize/complete.json` with a timestamp. Downstream stages check this sentinel before proceeding.
3. **Do NOT add file-level locking.** File locks are unreliable across platforms (Windows vs Linux), across process types (Python vs shell), and across failure modes (crashed processes don't release locks). Instead, enforce single-writer-per-deal at the orchestration level.
4. **Document the single-writer-per-deal invariant in CLAUDE.md.** The execution log shows this was a manual enforcement during the 7-deal rerun. It should be a documented hard rule.

**Warning signs:** `load_extract_artifacts` returning unexpected `mode` values. Stages failing with schema validation errors after canonicalize succeeds. Artifacts whose modification timestamps don't match the canonicalize log timestamp.

**Detection:** Schema-mode consistency check (proposed above). Also: compare file modification times of `actors_raw.json`, `events_raw.json`, and `spans.json` -- if they differ by more than a few seconds after canonicalize, something overwrote one of them.

**Phase:** Phase 4 (stage hardening). Critical to fix before any multi-deal re-extraction.

---

## Moderate Pitfalls

---

### Pitfall 9: Gates Rejecting Legitimate NDAs Modeled as Sale-Process NDAs

**What goes wrong:** The execution log reports: "petsmart-inc: gates rejected a rollover-side Longview confidentiality agreement modeled as a sale-process NDA." The cross-event logic gate checks that NDAs don't appear after a bidder has dropped from the cycle. But rollover-side or management-side confidentiality agreements are different from sale-process NDAs -- they're signed by parties who are already part of the acquiring group, not by competing bidders.

**Prevention:**
1. **Add an NDA subtype or purpose field.** Distinguish `nda` events by purpose: `sale_process`, `rollover`, `management`, `due_diligence`. The cross-event logic gate should only apply the "NDA after drop" check to `sale_process` NDAs.
2. **Alternatively, add a gate exemption for NDAs where the actor is the executed-with actor or an affiliate.** If the NDA signer is the same entity that eventually executes the deal, the NDA is likely rollover-side.
3. **Add a regression test for the Petsmart Longview case.**

**Warning signs:** Gates blocking deals that have legitimate late-cycle confidentiality agreements.

**Phase:** Phase 3 (gates hardening). Should be addressed alongside new event types since the NDA subtyping could be part of the schema extension.

---

### Pitfall 10: Verbal/Oral Indication Extraction Creates Unverifiable Events

**What goes wrong:** Adding support for "verbal/oral price indications" (stec Company D, petsmart Bidder 3) creates events where the filing says something like "provided a verbal indication of its interest to pursue a transaction at approximately $X per share." These events have inherently weaker evidence: the filing is reporting hearsay about an oral communication, not quoting a written document.

**Prevention:**
1. **Add a `formality_source` field or mark `mentions_verbal=True` in formality_signals.** This allows downstream consumers to distinguish between written and oral indications.
2. **Verbal indications should always classify as Informal.** Rule 1 should handle these; ensure the new formality signal doesn't interact with Rule 2.5.
3. **Coverage cues for verbal indications should be `medium` confidence at most.** The phrase "verbal indication" in evidence_items should not generate `high`-confidence cues.

**Warning signs:** Verbal indications being classified as Formal by the enrichment rules.

**Phase:** Phase 2 (new event types / inference improvements).

---

### Pitfall 11: Enrichment JSON Schema Drift Between Deterministic and Interpretive Layers

**What goes wrong:** The pipeline has two enrichment artifacts: `deterministic_enrichment.json` (written by `enrich-core`) and `enrichment.json` (written by the local-agent `/enrich-deal` skill). The `db-load` stage reads both. If v1.1 adds new fields to `deterministic_enrichment.json` (e.g., `all_cash` classifications, new round types), the `enrichment.json` schema and the `db-load` reader must also be updated. Schema drift between the two enrichment layers causes silent data loss in the database.

**Prevention:**
1. **Define the enrichment schema in `models.py`, not implicitly.** Currently `deterministic_enrichment.json` is written as a raw dict (enrich_core.py line 492-499). It should use a Pydantic model so schema changes are type-checked.
2. **Add a schema version field to the enrichment artifact.** When `db-load` reads enrichment, it should check the version and fail if it's older than expected.
3. **Update `db_load.py` and `db_schema.py` in the same PR as enrichment changes.** Never land enrichment schema changes without corresponding DB schema changes.

**Warning signs:** Fields present in `deterministic_enrichment.json` that are absent from the `enrichment` table in DuckDB. `db-load` succeeding but `db-export` producing CSVs with null values in new columns.

**Phase:** Every phase that touches enrichment. This is a cross-cutting concern.

---

### Pitfall 12: Test Fixture Staleness After Schema Changes

**What goes wrong:** The test suite uses inline fixture builders (`_base_event`, `_event_payload`, `_write_quote_first_extract_fixture`, `_write_canon_fixture`, `_write_coverage_fixture`) that construct minimal valid artifacts. When v1.1 adds new event types or new fields to `formality_signals`, these fixtures must be updated. Tests that pass with stale fixtures give false confidence -- they test the old schema, not the new one.

**Prevention:**
1. **Add a schema conformance test.** A test that constructs an event of every type in the `Literal` union using `_base_event` and validates it against the Pydantic model. If a new type is added but `_base_event` can't construct it (e.g., because it requires a new required field), the test fails.
2. **When adding a new field, grep all fixture builders.** Update them to include the new field with a sensible default.
3. **When adding a new event type, add at least one test per downstream consumer.** Each of `check`, `verify`, `coverage`, `gates`, `enrich-core`, and `db-load` should have a test with an event of the new type.

**Warning signs:** Tests passing after a schema change without any test file modifications. New event types that have no test coverage.

**Phase:** Every phase. This is a cross-cutting concern.

---

## Minor Pitfalls

---

### Pitfall 13: `_event_semantics_key` in Dedup Missing New Fields

**What goes wrong:** The `_event_semantics_key` function in `canonicalize.py` (line 277-293) builds a JSON key from a hardcoded list of event fields for deduplication. If new fields are added to events (e.g., `consideration_type`, `verbal_indication`), they must be added to this key. Otherwise, events that differ only in the new field will be incorrectly deduped.

**Prevention:** Add new fields to `_event_semantics_key` in the same PR that adds them to the event schema. Add a test that two events differing only in the new field are NOT deduped.

**Phase:** Phase 2 (new event types).

---

### Pitfall 14: `_suggested_event_types` in Coverage Not Updated for New Types

**What goes wrong:** The `_suggested_event_types` mapping in `coverage.py` (line 227-242) maps cue families to expected event types. If a new event type is added (e.g., `drop_target`, `verbal_indication`) but the mapping isn't updated, coverage will never match cues to those event types and will report false uncovered cues.

**Prevention:** Update `_suggested_event_types` in the same PR that adds the new event type. Add a test that a cue matching the new type is correctly covered when the event exists.

**Phase:** Phase 2 (new event types).

---

### Pitfall 15: Missing `DropTarget` in NDA Gate Logic

**What goes wrong:** The canonicalize stage's `_gate_drops_by_nda` function (line 296-327) removes `drop` events for actors without a prior NDA. If `drop_target` is a new event type representing committee-driven field narrowing, it may or may not require a prior NDA. Committee exclusions can remove parties who signed NDAs (normal drops) or parties who were invited but never signed (which would be gated). The NDA-gate logic needs to be explicitly updated for the new type.

**Prevention:** Decide whether `drop_target` participates in NDA-gating. If yes, add it to the drop-type check on line 311. If no (committee exclusions are structural, not participant-driven), explicitly exclude it from the gate. Either way, document the decision and add a test.

**Phase:** Phase 2 (new event types).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation | Severity |
|---|---|---|---|
| Enrichment rule priority fix | Pitfall 1: Regression in existing Informal classifications | Before/after snapshot of all 9 deals' bid_classifications | Critical |
| New event type: drop_target | Pitfall 2: Not added to SUBSTANTIVE_EVENT_TYPES, EVENT_PHASES, coverage cues | Event-type consumer registry test | Critical |
| New event type: verbal_indication | Pitfall 10: Unverifiable events + Pitfall 14: coverage not updated | formality_source field + coverage cue update | Moderate |
| all_cash contextual inference | Pitfall 6: Over-triggering on mixed-consideration deals | Constrained inference + Providence-Worcester test | Critical |
| Canonicalize quote_id hardening | Pitfall 3: Must not silently drop quotes | Auto-renumber with logging | Critical |
| Coverage false-positive suppression | Pitfall 4: Over-suppression hiding real gaps | Corpus-wide suppression audit | Critical |
| Check NDA count with grouped bidders | Pitfall 5: group_size masking incomplete extraction | Cross-validate group_size against named actors | Moderate |
| Gates NDA subtyping | Pitfall 9: Rollover NDAs rejected | NDA purpose field or actor-affiliation check | Moderate |
| DuckDB lock resilience | Pitfall 7: Retry masking data corruption | Read-only retry only, no write retry | Moderate |
| Concurrent write protection | Pitfall 8: Mixed schema state | Schema-mode consistency check | Critical |
| Enrichment schema extension | Pitfall 11: Schema drift between det/interp layers | Pydantic model for enrichment artifact | Moderate |
| All phases | Pitfall 12: Test fixture staleness | Schema conformance test | Moderate |

## Integration Pitfalls (Cross-Cutting)

### The Cascade Problem

The most dangerous v1.1 scenario is: enrichment rule change -> bid_classification change -> formal_boundary change -> cycle segmentation change -> coverage interpretation change -> gates behavior change. Each of these is a different module, and a change in one can cascade through the others in ways that are not visible from unit tests alone.

**Prevention:**
1. **Run the full 9-deal pipeline end-to-end after every behavioral change.** Not just the affected deal -- all 9 deals. The reconciliation analysis showed that bugs in one deal's enrichment rules affect all 9 deals identically.
2. **Create a "golden output" regression corpus.** Snapshot the current `deterministic_enrichment.json` and `deal_events.csv` for all 9 deals. After v1.1, diff against the golden outputs. Every diff should be intentional and documented.
3. **Never change more than one behavioral module per PR.** Enrichment rules, event types, coverage heuristics, and gates logic should be separate PRs that can be independently validated.

### The "Fix One Bug, Create Two" Problem

The reconciliation analysis identified 7 actionable items. The execution log identified 6 hardening items. Fixing all 13 in a single milestone creates combinatorial risk: each fix interacts with the others, and the interaction space is 2^13 = 8192 possible combinations. The probability of an unexpected interaction is high.

**Prevention:**
1. **Prioritize fixes by independence.** Address fixes that don't interact with each other first (canonicalize hardening, DuckDB lock, concurrent write protection). Then address fixes that interact (enrichment rules + new event types + coverage heuristics).
2. **Order phases so each phase's outputs can be fully validated before the next phase changes them.** Don't add new event types until enrichment rules are stable. Don't change coverage heuristics until new event types are stable.

## Sources

- `data/reconciliation_cross_deal_analysis.md` -- cross-deal pipeline vs. Alex analysis (2026-03-29)
- `quality_reports/session_logs/2026-03-29_7-deal-rerun_master.md` -- 7-deal fresh rerun execution log
- `skill_pipeline/enrich_core.py` -- deterministic enrichment with bid_type classification rules
- `skill_pipeline/coverage.py` -- coverage heuristics with false-positive suppression
- `skill_pipeline/canonicalize.py` -- quote-to-span resolution with dedup and NDA-gate
- `skill_pipeline/check.py` -- structural gate with NDA count assertions
- `skill_pipeline/gates.py` -- semantic gates with temporal consistency and cross-event logic
- `skill_pipeline/models.py` -- Pydantic schema with Literal event type unions
- `skill_pipeline/db_load.py` and `skill_pipeline/db_export.py` -- DuckDB I/O
