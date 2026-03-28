# Phase 3: Quote-Before-Extract - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Change the LLM extraction response format so the model must cite verbatim filing passages before emitting structured actors/events. Update canonicalize and verify to consume the new quote-first format natively. Commit to the new format only — no dual-path support for the old evidence_refs format.

</domain>

<decisions>
## Implementation Decisions

### Response Format
- **D-01:** The LLM produces a single JSON response with a top-level `quotes` array followed by the structured `actors` or `events` array. Quotes come first in the JSON, structured data second. Not two sequential LLM calls.
- **D-02:** Each quote entry has `quote_id`, `block_id`, and `text` (verbatim filing passage). Quote IDs are stable identifiers (e.g., `Q001`, `Q002`) assigned by the LLM during extraction.
- **D-03:** Actors and events reference `quote_ids` (list of strings) instead of carrying inline `evidence_refs` with `anchor_text`. The `evidence_refs` field and its `anchor_text` subfield are replaced, not augmented.

### Format Compatibility
- **D-04:** New format only. No dual-path support in canonicalize or verify. Old `evidence_refs`-based code paths are removed.
- **D-05:** Existing stec and medivation extraction artifacts become stale. Both deals must be re-extracted through the new quote-first protocol before Phase 3 exit criteria can be validated.
- **D-06:** The `EvidenceRef` model and related legacy helpers can be cleaned out of `models.py` and downstream stages once the new format is wired.

### Downstream Pipeline Updates
- **D-07:** Canonicalize maps quotes directly to spans: `quote.text` + `quote.block_id` → `resolve_text_span()` → `spans.json`. Actors/events `quote_ids` are resolved to `evidence_span_ids` through the quote-to-span mapping.
- **D-08:** Verify runs two validation rounds: Round 1 checks each `quote.text` against the actual filing text (EXACT/NORMALIZED matching). Round 2 checks that every actor/event references valid `quote_ids` that exist in the quotes array.
- **D-09:** The quote-first format should produce higher EXACT match rates in verify because the LLM is structurally forced to commit to verbatim text before building structured data on top of it.

### Claude's Discretion
- Exact JSON schema field names for the quote-first response (as long as quotes precede structured data and use quote_ids for linkage)
- Whether to keep `evidence_refs` as a deprecated alias during the transition or remove immediately
- Internal refactoring approach for canonicalize (incremental edits vs clean rewrite of span resolution)
- How the prompt assets (`task_instructions` text in compose-prompts) communicate the quote-first requirement to the LLM

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope
- `.planning/ROADMAP.md` — authoritative Phase 3 goal, scope, and exit criteria
- `.planning/REQUIREMENTS.md` — PROMPT-05 (quote-before-extract protocol)
- `.planning/PROJECT.md` — project-level constraints (correctness priority, filing-text-only truth)

### Prior Phase Carry-Forward
- `.planning/phases/01-foundation-annotation/01-CONTEXT.md` — no Python LLM wrapper constraint
- `.planning/phases/02-prompt-architecture/02-CONTEXT.md` — packet layout, XML sections, data-first ordering
- `.planning/phases/02-prompt-architecture/02-GPT54-AUDIT.md` — audit findings (item 1 deferred to Phase 5)

### Live Extraction Contract
- `.claude/skills/extract-deal/SKILL.md` — current extraction workflow, actor/event schemas, evidence_ref format (to be replaced)
- `.claude/skills/verify-extraction/SKILL.md` — downstream repair workflow
- `docs/design.md` — end-to-end runtime sequence

### Source + Artifact Models
- `skill_pipeline/models.py` — `EvidenceRef`, `SpanRecord`, actor/event artifact schemas (to be updated)
- `skill_pipeline/canonicalize.py` — current span resolution from evidence_refs (to be rewritten for quotes)
- `skill_pipeline/verify.py` — current anchor_text matching (to be rewritten for quote validation)
- `skill_pipeline/extract_artifacts.py` — artifact loader (format detection)
- `skill_pipeline/provenance.py` — `resolve_text_span()` (reusable as-is for quote→span resolution)
- `skill_pipeline/normalize/quotes.py` — `find_anchor_in_segment()` (reusable for quote matching)

### Prompt Composition
- `skill_pipeline/compose_prompts.py` — task_instructions text needs quote-first protocol
- `skill_pipeline/prompt_assets/actors_prefix.md` — actor extraction prefix (needs quote-first instructions)
- `skill_pipeline/prompt_assets/events_prefix.md` — event extraction prefix (needs quote-first instructions)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `skill_pipeline/provenance.py:resolve_text_span()` already resolves text + block_id to a SpanRecord with line/char offsets — directly applicable for quote→span mapping.
- `skill_pipeline/normalize/quotes.py:find_anchor_in_segment()` already does EXACT/NORMALIZED/FUZZY matching — reusable for quote validation in verify.
- `skill_pipeline/prompts/render.py` already renders `<task_instructions>` sections — the quote-first protocol is a task instruction change, not a renderer architecture change.

### Established Patterns
- Canonicalize currently iterates `evidence_refs`, calls `resolve_text_span()` for each, and builds `spans.json`. The same pattern applies to quotes: iterate `quotes`, resolve each, build spans.
- Verify currently iterates evidence_refs and matches anchor_text against filing text. The same pattern applies: iterate quotes and match quote.text against filing text.
- Both stages use `_load_document_lines()` for filing text access — unchanged.

### Integration Points
- `actors_raw.json` and `events_raw.json` schema changes (quote_ids replaces evidence_refs)
- `compose-prompts` task instruction text (add quote-first protocol)
- `.claude/skills/extract-deal/SKILL.md` response format documentation
- `extract_artifacts.py` loader (detect new format, reject old)

</code_context>

<specifics>
## Specific Ideas

- The key insight is structural: by forcing quotes before structured data, the LLM cannot fabricate anchor text because it must commit to verbatim passages before building events on top of them.
- The verify stage should see measurably higher EXACT match rates — this is the primary quality signal for Phase 3 success.
- `resolve_text_span()` and `find_anchor_in_segment()` are the core reusable functions — the new code mostly rewires how they're called, not what they do.

</specifics>

<deferred>
## Deferred Ideas

- Chunk-budget overhead accounting (CRITICAL-1 from GPT audit) — deferred to Phase 5 complexity routing
- Complexity-based routing (PROMPT-06) — Phase 5
- Few-shot expansion (INFRA-07) — Phase 5

</deferred>

---

*Phase: 03-quote-before-extract*
*Context gathered: 2026-03-28*
