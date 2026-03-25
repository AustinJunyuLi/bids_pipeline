# Phase 2: Deterministic Stage Interfaces - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Keep the preprocess-to-extract and extract-to-deterministic-stage interfaces precise and independently runnable. For this discussion, the relevant boundary is the handoff from preprocessed chronology blocks into `/extract-deal`, with the constraint that any routing change must preserve the existing downstream contract for canonicalize, check, verify, coverage, and enrich-core.

</domain>

<decisions>
## Implementation Decisions

### Extraction routing strategy
- **D-01:** Do not replace the current actor/event separation with a pure chunk-first unified extraction flow as the default architecture.
- **D-02:** Prefer a hybrid routing design: keep actor extraction on the full chronology, then route only event extraction through chunked windows for complex deals, followed by one global recovery or audit pass across the full chronology.
- **D-03:** Use chunking as an attention-control mechanism for complex event extraction, not as a reason to abandon global actor context.

### Complexity gating
- **D-04:** Add deterministic routing criteria before `/extract-deal` or at extract entry: chronology size and expected complexity should decide whether events run in single-pass or chunked mode.
- **D-05:** The exact thresholds are not locked yet, but the current preference is to start from the historical prompt-spec rule of thumb: full-context actor pass always, chunked event pass only for complex deals.

### Merge and recovery behavior
- **D-06:** Any chunked event mode must preserve the same final artifact contract: one `actors_raw.json`, one `events_raw.json`, and no new manual cleanup burden for deterministic stages.
- **D-07:** Chunked event extraction should use overlapping block windows plus a final whole-chronology audit or recovery pass to catch cross-chunk omissions, boundary mistakes, duplicate proposals, and missed process markers.
- **D-08:** Evidence items should guide re-read and recovery targeting, but should not be dumped wholesale into the extraction prompt as a substitute for chronology reading.

### the agent's Discretion
- Exact token or line thresholds for simple, moderate, and complex routing
- How chunk overlap is represented and how many blocks overlap by default
- Whether chunk metadata lives only in prompt context or is also persisted to an intermediate artifact
- The deterministic merge or dedup strategy for chunk-level event drafts before canonicalize

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase and project contract
- `.planning/ROADMAP.md` — Phase 2 scope, requirements, and success criteria
- `.planning/REQUIREMENTS.md` — `WFLO-02`, `WFLO-03`, and `QUAL-03`
- `.planning/PROJECT.md` — brownfield constraints: fail-fast behavior, seed-only source boundary, hybrid workflow
- `.planning/codebase/ARCHITECTURE.md` — current hybrid architecture and stage layering

### Live preprocess and extraction surfaces
- `skill_pipeline/preprocess/source.py` — current preprocess output contract; seed-only single-document behavior and stale snippet invalidation
- `skill_pipeline/source/blocks.py` — current chronology block construction; paragraph-like blocks with headings split out
- `skill_pipeline/source/evidence.py` — evidence-item generation; useful as re-read cues, too noisy to treat as prompt-equivalent chronology
- `.claude/skills/extract-deal/SKILL.md` — current actor/event extraction contract and two-pass expectations

### Historical but relevant routing design
- `docs/plans/2026-03-16-prompt-engineering-spec.md` — historical prompt design that already recommends full-context actor extraction and chunked event extraction for complex deals; useful reference, not the active runtime contract

[If additional implementation docs are created during planning, add them here.]

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `skill_pipeline/source/blocks.py`: chronology is already split into paragraph-sized `ChronologyBlock` records with stable `block_id`s, which is a natural unit for chunk windows.
- `skill_pipeline/source/evidence.py`: evidence scan already surfaces dated actions, process signals, actor hints, money mentions, and outcomes that can drive targeted re-read or recovery after chunk extraction.

### Established Patterns
- Preprocess is deterministic and fail-fast: `skill_pipeline/preprocess/source.py` rejects multi-document drift and removes stale `supplementary_snippets.jsonl`.
- Downstream deterministic stages expect one final extract artifact set, not multiple chunk artifacts.
- The repo prefers deterministic gating around LLM stages rather than pushing more ambiguity downstream.

### Integration Points
- Any routing change primarily touches `/extract-deal` and possibly the preprocess-to-extract metadata surface.
- Canonicalize, check, verify, coverage, and enrich-core should continue to read the same final extract paths without manual stitching.

</code_context>

<specifics>
## Specific Ideas

- Actual chronology block counts are large enough to create attention risk on complex deals even though individual blocks are small:
  - `stec`: 235 blocks, about 87,966 raw characters total
  - `medivation`: 165 blocks, about 57,703 raw characters total
  - `imprivata`: 101 blocks, about 51,823 raw characters total
- Individual blocks are already paragraph-like, usually a few hundred characters, so the problem is not oversized blocks but the total number of blocks the model must track across the full event timeline.
- Historical prompt guidance in `docs/plans/2026-03-16-prompt-engineering-spec.md` already anticipated this exact split:
  - actor pass: full chronology
  - event pass: full chronology for simple deals, chunked windows for complex deals
- Evidence-item volumes are too large and noisy to feed wholesale:
  - `imprivata`: 3,122 evidence items
  - `zep`: 3,239 evidence items
  - `medivation`: 617 evidence items
- Current live preprocess deletes stale `supplementary_snippets.jsonl`, so any revised extraction design should not depend on that file as a hard prerequisite.

</specifics>

<deferred>
## Deferred Ideas

- Fully retrieval-driven extraction that replaces chronology-first reading with evidence-first prompt construction
- Multi-filing or supplementary-filing extraction support beyond the current seed-only source boundary

</deferred>

---

*Phase: 02-deterministic-stage-interfaces*
*Context gathered: 2026-03-25*
