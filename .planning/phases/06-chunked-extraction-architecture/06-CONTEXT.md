# Phase 6: Chunked Extraction Architecture - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning
**Source:** Direct discussion with user

<domain>
## Phase Boundary

Redesign the extraction skill (`/extract-deal`) from two-pass single-shot to all-chunked sequential extraction with consolidation. Add deterministic safety nets in canonicalize and check. Refactor enrich-deal to use event-targeted re-reads instead of full-context calls.

This phase changes how LLM extraction works and adds ~90 lines of deterministic code. It does NOT change the output contract — downstream stages still read the same `actors_raw.json` + `events_raw.json`.
</domain>

<decisions>
## Implementation Decisions

### Extraction Strategy
- All deals go through chunking. No single-shot path. One code path for all deals.
- Chunk size: ~3-4K tokens (~10-12 blocks per chunk).
- Chunks are sequential, not parallel. Each chunk receives the running actor roster from prior chunks (roster carry-forward).
- 1-2 block overlap between adjacent chunks to catch boundary-spanning events.
- Evidence items scoped per chunk: only items whose line range intersects the chunk's block range.

### Consolidation Pass
- Replaces the current Pass 2 (gap re-read). One pass, not two.
- Receives: final actor roster + all chunk event drafts (structured JSON) + count_assertions + evidence gap signals.
- Performs: actor dedup by canonical_name, event dedup for overlap zones, 20-type taxonomy sweep, count reconciliation, targeted re-reads for gaps, global event_id assignment.
- Temporal signals (`after_final_round_announcement`, `after_final_round_deadline`) are set by the consolidation pass since they require cross-chunk event history.

### Chunk Prompt Design
- Each chunk extracts actors AND events together (not separated).
- Each chunk receives: its block window + scoped evidence items + actor roster from prior chunks.
- If a chunk sees a party not on the roster, it mints a new actor (roster carry-forward adds it for subsequent chunks).
- Chunk outputs are transient debug artifacts, not consumed by deterministic pipeline.

### Output Contract
- Final output is the same schema as today: `actors_raw.json` + `events_raw.json` in `data/skill/<slug>/extract/`.
- No changes to artifact paths or Pydantic models.
- Chunk drafts may be written as debug artifacts but are NOT required by canonicalize or any downstream stage.

### Deterministic Pipeline Changes
- `canonicalize.py`: Add `_dedup_actors()` (~50 lines). Groups by (canonical_name_normalized, role, bidder_kind). Picks survivor with most evidence. Rewrites event actor_ids to survivor. Merges evidence_span_ids. Logs in canonicalize_log.
- `check.py`: Add `_check_actor_audit()` (~40 lines). Flags: duplicate canonical_name across actor_ids, bidder with no NDA event, count_assertion gap vs actual roster, advisor missing advised_actor_id.
- `verify.py`, `coverage.py`, `enrich_core.py`: No changes.

### Enrichment Refactor
- `enrich-deal` gets event-targeted re-reads, NOT systematic chunking.
- Per-task scoped context: each enrichment subtask receives only the blocks around the events it's analyzing (~2-3K tokens per task call).
- Dropout classification: one call per drop event with evidence blocks + round context.
- Initiation judgment: one call reading first 10-15 blocks only.
- Advisory verification: one call per advisor with evidence blocks.
- Count reconciliation: one call with count-assertion blocks + full roster.
- Rounds, cycles, formal_boundary, bid_classifications remain in enrich-core (deterministic). enrich-deal does NOT duplicate these.

### Claude's Discretion
- Exact chunk boundary logic (how to split blocks into 3-4K windows)
- Consolidation prompt structure and re-read targeting strategy
- Debug artifact format for chunk drafts
- How roster carry-forward is formatted in chunk prompts
- Test fixture design for chunked extraction scenarios
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Extraction Skill
- `.claude/skills/extract-deal/SKILL.md` — Current two-pass extraction contract (being replaced)

### Deterministic Stages (being modified)
- `skill_pipeline/canonicalize.py` — Adding _dedup_actors; read existing _dedup_events pattern
- `skill_pipeline/check.py` — Adding actor audit; read existing check pattern
- `skill_pipeline/models.py` — Artifact schemas (RawSkillActorsArtifact, RawSkillEventsArtifact, SpanRegistryArtifact)
- `skill_pipeline/paths.py` — Artifact path conventions

### Deterministic Stages (unchanged, but must understand)
- `skill_pipeline/verify.py` — Must still work on chunked extraction output
- `skill_pipeline/coverage.py` — Must still work on chunked extraction output
- `skill_pipeline/enrich_core.py` — Gets better input from chunked extraction

### Source Artifacts (chunk inputs)
- `skill_pipeline/source/blocks.py` — Block building (provides block_id, line ranges)
- `skill_pipeline/source/evidence.py` — Evidence scanning (provides evidence items to scope per chunk)
- `skill_pipeline/preprocess/source.py` — Preprocess pipeline that produces chunk inputs

### Enrichment Skill (being refactored)
- `.claude/skills/enrich-deal/SKILL.md` — Current enrichment contract (being refactored to targeted re-reads)

### Tests
- `tests/test_skill_canonicalize.py` — Existing dedup tests; new actor dedup tests follow this pattern
- `tests/test_skill_check.py` — Existing check tests; new actor audit tests follow this pattern
- `tests/test_skill_pipeline.py` — Integration tests that must pass after changes

### Data for validation
- `data/deals/stec/source/chronology_blocks.jsonl` — Largest deal (235 blocks, ~22K tokens), primary chunking test case
- `data/deals/petsmart-inc/source/chronology_blocks.jsonl` — Silent NDA signer test case (15 NDA, 9 unnamed)
</canonical_refs>

<specifics>
## Specific Ideas

### Deal-level chunking expectations
```
petsmart-inc          36 blocks    6.8K tokens   2-3 chunks
providence-worcester  41 blocks    6.6K tokens   2-3 chunks
saks                  65 blocks    6.5K tokens   2-3 chunks
zep                  114 blocks    9.3K tokens   3 chunks
penford               95 blocks   11.6K tokens   3-4 chunks
imprivata            101 blocks   13.0K tokens   3-4 chunks
medivation           165 blocks   14.4K tokens   4-5 chunks
mac-gray             180 blocks   15.4K tokens   4-5 chunks
stec                 235 blocks   22.0K tokens   6-7 chunks
```

### The petsmart test case
Bidder funnel: 27 contacted -> 15 signed NDA -> 6 submitted IOI -> 4 invited to final round -> 2 dropped -> 3 final bids -> 1 winner. The 9 who signed NDA but never submitted IOI are unnamed. Chunked extraction with better count_assertion capture should produce the assertions that feed unnamed-party recovery in canonicalize.

### Actor dedup key in canonicalize
```python
key = (canonical_name.strip().upper(), role, bidder_kind)
```
Same entity with different actor_ids gets merged. Event actor_ids rewritten to survivor. Evidence_span_ids merged.
</specifics>

<deferred>
## Deferred Ideas

- Multi-filing support (supplementary_snippets.jsonl) — current pipeline is seed-only, chunking design assumes single document
- Parallel chunk execution — deferred because roster carry-forward requires sequential; revisit if latency becomes a bottleneck
- Adaptive chunk sizing based on cue density — uniform ~3-4K is simpler and good enough
- GPT's inter-chunk state protocol (date anchors, round context) — deferred; consolidation handles temporal reasoning instead
</deferred>

---

*Phase: 06-chunked-extraction-architecture*
*Context gathered: 2026-03-25 via direct discussion*
