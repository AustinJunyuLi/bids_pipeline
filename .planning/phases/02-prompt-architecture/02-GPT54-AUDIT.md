# Phase 2 Adversarial Audit — GPT 5.4 xhigh

**Date:** 2026-03-28
**Auditor:** GPT 5.4 (xhigh reasoning effort) via /collaborate adversarial audit
**Defender:** Claude Opus 4.6
**Thread:** 019d31bf-ce61-76d3-80f3-7a57290b16b0

## Audit Scope

Full Phase 2 prompt architecture implementation: `compose_prompts.py`,
`prompts/chunks.py`, `prompts/checklist.py`, `prompts/render.py`,
`pipeline_models/prompt.py`.

## Findings

### CRITICAL-1: Chunk budget ignores rendered packet overhead

**Location:** `chunks.py:build_chunk_windows()`, `render.py`, `compose_prompts.py`

**Issue:** The chunk budget (`--chunk-budget 6000`) only governs target-block
token selection. The actual rendered packet also includes:
- Overlap blocks (2 blocks per side)
- Full evidence checklist (can be 1000+ items for large deals)
- Actor roster JSON (event packets)
- Prefix assets (actors_prefix.md, events_prefix.md, event_examples.md)
- Deal context metadata
- Task instructions

GPT demonstrated that a window with `estimated_tokens=1350` rendered to 3071
words (~4100 tokens). The budget is effectively a lower bound on target content
rather than an upper bound on total packet size.

**Impact:** For complex deals requiring chunked extraction, packets may exceed
the LLM's effective context window, causing truncated reads or degraded
extraction quality. For stec (235 blocks, single-pass), this does not bite
because the entire filing fits in one window.

**Verdict:** Agree. Real issue. Fix priority depends on when chunked extraction
is first used in production.

**Fix options:**
1. Budget against full rendered packet: estimate overhead from evidence count,
   prefix asset size, and roster size, then subtract from chunk_budget before
   passing to the planner.
2. Post-render size check: after rendering each packet, measure actual token
   estimate and warn/fail if it exceeds a declared limit.
3. Defer to Phase 5 (complexity routing) when the routing thresholds are set
   and actual context limits are known.

**Recommended:** Option 2 (post-render check) is cheapest and most accurate.
Implement as a validation step in `_write_packet_files()` or as a flag on the
manifest.

---

### MAJOR-2: Every chunk receives the full filing-wide evidence checklist

**Location:** `compose_prompts.py:_compose_actor_packets()` line 145,
`_compose_event_packets()` line 203

**Issue:** Both `_compose_*_packets()` pass the entire `evidence_items` list to
every packet window, regardless of which blocks are in that window. In chunked
mode, window `w0` covering blocks B001-B050 receives evidence items from lines
501-503 (which correspond to blocks B200+).

**Impact:** Wastes tokens on irrelevant evidence cues. Worse, the LLM sees
checklist items referencing text not present in the packet, which could cause:
- Hallucinated extractions from non-visible evidence
- Confusion about which evidence applies to the visible chronology
- Reduced extraction precision in chunked mode

**Verdict:** Agree. This is the highest-impact extraction quality issue.

**Fix:** Filter evidence items per window by intersecting evidence line ranges
(`start_line`, `end_line`) with the union of target + overlap block line ranges.
Only include evidence items whose line ranges overlap with blocks visible in that
window. Update `evidence_ids` in the packet artifact accordingly.

```python
def _filter_evidence_for_window(
    evidence_items: list[EvidenceItem],
    blocks: list[ChronologyBlock],
    window: PromptChunkWindow,
) -> list[EvidenceItem]:
    visible_ids = set(window.target_block_ids) | set(window.overlap_block_ids)
    visible_blocks = [b for b in blocks if b.block_id in visible_ids]
    if not visible_blocks:
        return []
    min_line = min(b.start_line for b in visible_blocks)
    max_line = max(b.end_line for b in visible_blocks)
    return [
        ei for ei in evidence_items
        if ei.start_line <= max_line and ei.end_line >= min_line
    ]
```

---

### MAJOR-3: Event mode embeds unvalidated actor roster

**Location:** `compose_prompts.py:_load_actor_roster_json()` line 76

**Issue:** The loader checks file existence but does not validate the JSON
content against the actor artifact schema. Empty files, malformed JSON, or
wrong-schema content will be silently wrapped in `<actor_roster>` tags and
shipped as a "locked" roster.

**Impact:** Downstream extraction uses the roster as ground truth for actor IDs.
A corrupt roster produces corrupt event extraction.

**Verdict:** Agree. Violates the project's fail-fast philosophy.

**Fix:** Parse `actors_raw.json` through the actor artifact schema (or at
minimum `json.loads()` + verify `"actors"` key exists and is non-empty) before
returning the text. Fail fast on parse errors.

---

### MAJOR-4: Duplicate block_ids silently corrupt chunk math

**Location:** `compose_prompts.py:_load_blocks()`, `chunks.py:build_chunk_windows()`

**Issue:** If `chronology_blocks.jsonl` contains duplicate `block_id` values,
`token_map` and `block_index` dicts silently overwrite earlier entries. Chunk
windows then have incorrect token estimates and block ID lists.

**Impact:** Low in practice — `preprocess-source` generates sequential unique
IDs (B001, B002, ...) and the annotated schema doesn't produce duplicates in
normal operation. But a fail-fast guard is cheap insurance against data
corruption from manual edits or upstream bugs.

**Verdict:** Agree (low risk). Worth adding.

**Fix:** Add to `_load_blocks()`:
```python
seen_ids = set()
for block in blocks:
    if block.block_id in seen_ids:
        raise ValueError(f"Duplicate block_id: {block.block_id}")
    seen_ids.add(block.block_id)
```

---

### MINOR-5: Missing event examples treated as silent fallback

**Location:** `render.py:render_event_packet()` line 173-174,
`compose_prompts.py` line 346

**Issue:** If `event_examples.md` doesn't exist, the renderer silently skips it,
but `run_compose_prompts()` still records the path in `manifest.asset_files`.
Manifest metadata doesn't match what was actually rendered.

**Verdict:** Agree.

**Fix:** Either require the asset to exist (fail-fast), or only add to
`asset_files` if the file was actually loaded and rendered.

---

### MINOR-6: Unresolved block IDs produce empty sections silently

**Location:** `render.py:_render_blocks_section()` line 48-62

**Issue:** If `target_block_ids` contains IDs not present in `blocks`, the
filter silently drops them. Could produce `<chronology_blocks></chronology_blocks>`
(empty) without any error.

**Impact:** Low risk — IDs come from the chunk planner which derives them from
loaded blocks. But a defensive check is consistent with fail-fast philosophy.

**Verdict:** Agree (low risk).

**Fix:** After filtering, verify `len(filtered) == len(block_ids)`. Raise on
mismatch.

---

## Priority Matrix

| # | Severity | Impact on Extraction | Fix Complexity | When to Fix |
|---|----------|---------------------|----------------|-------------|
| 1 | CRITICAL | High (chunked deals) | Medium | Before first chunked extraction |
| 2 | MAJOR | High (chunked deals) | Low | Before first chunked extraction |
| 3 | MAJOR | High (corrupt roster) | Low | Before first event extraction |
| 4 | MAJOR | Low (defensive) | Trivial | Next commit |
| 5 | MINOR | Low (metadata only) | Trivial | Next commit |
| 6 | MINOR | Low (defensive) | Trivial | Next commit |

## Recommendation

Items 2, 3, 4, 5, 6 are straightforward fixes (< 30 lines each). Item 1
requires a design decision about budget semantics and is best addressed alongside
Phase 5 complexity routing when actual context limits are known.

**Suggested approach:** Fix items 2-6 as a gap closure patch. Park item 1 as a
documented constraint with a Phase 5 resolution path.
