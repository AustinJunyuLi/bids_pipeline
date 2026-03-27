# Phase 2: Prompt Architecture - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a deterministic prompt composition engine that turns annotated source artifacts into provider-neutral extraction prompt packets. This phase defines packet structure, chunk construction, overlap rendering, checklist formatting, and artifact contracts. It does not add a Python-side LLM wrapper, and it does not yet change the quote-before-extract response format from Phase 3.

</domain>

<decisions>
## Implementation Decisions

### Prompt Engine Boundary
- **D-01:** The prompt composition engine lives in `skill_pipeline` as deterministic code, but it only assembles packet artifacts. Model invocation remains in `.claude/skills/`, preserving the no-Python-wrapper constraint from Phase 1.
- **D-02:** Prompt packets are first-class artifacts, not ephemeral strings hidden inside `/extract-deal`. Planning should assume a dedicated prompt-artifact directory under `data/skill/<slug>/` so composition outputs stay separate from extracted actors/events.

### Packet Families + Layout
- **D-03:** The engine should support at least two packet families: actor extraction packets and event extraction packets. Event packets consume a locked actor roster; actor packets do not.
- **D-04:** Packet layout is data-first. Primary chronology text appears before instructions, and the actionable query/instructions appear at the end of the packet. Stable guidance and taxonomy should be separated from chunk-specific body content.
- **D-05:** The packet contract should use explicit XML-style sections for deterministic rendering, including deal context, optional actor roster, evidence checklist, overlap context, primary chronology blocks, and task instructions.

### Chunking + Overlap
- **D-06:** The engine should support both single-pass and chunked packet modes from the same deterministic contract. Phase 2 should not hard-code final complexity-routing thresholds; that broader routing policy stays deferred to Phase 5.
- **D-07:** Chunk boundaries must be computed on whole chronology blocks only. No chunk may split a block mid-text.
- **D-08:** Chunked packets must include exactly 2 blocks of overlap rendered in a dedicated `<overlap_context>` section, clearly separated from the primary extraction target blocks.

### Evidence + Few-Shot Packaging
- **D-09:** Evidence items should be rendered as an active checklist, grouped and filtered for extraction usefulness, not dumped as a passive raw appendix.
- **D-10:** Few-shot examples and stable instruction assets should be file-backed and provider-neutral. Planning should assume reusable prompt assets checked into the repo and loaded deterministically by the composition engine.

### the agent's Discretion
- Exact artifact filenames and manifest schema for prompt packets
- Exact token-estimation method used for chunk planning
- Exact grouping rules for evidence checklist sections, as long as they remain deterministic and concise
- Whether prompt assets live under `skill_pipeline/` or another repo-owned provider-neutral directory, as long as they are versioned and testable

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Scope
- `.planning/ROADMAP.md` — authoritative Phase 2 goal, scope, and exit criteria
- `.planning/REQUIREMENTS.md` — PROMPT-01 through PROMPT-04 and INFRA-01 through INFRA-05
- `.planning/PROJECT.md` — project-level constraint that `skill_pipeline` stays deterministic and provider-agnostic
- `.planning/STATE.md` — current project position and the non-blocking Medivation seed-quality follow-up

### Prior-Phase Carry-Forward
- `.planning/phases/01-foundation-annotation/01-CONTEXT.md` — locked Phase 1 decisions, especially that annotated chronology blocks exist to feed prompt composition and that no Python LLM wrapper is allowed
- `.planning/phases/01-foundation-annotation/01-03-SUMMARY.md` — confirms all 9 active deals now have validated annotated source artifacts

### Live Extraction Contract
- `.claude/skills/extract-deal/SKILL.md` — current extraction workflow contract the prompt packets must support
- `.claude/skills/verify-extraction/SKILL.md` — downstream repair workflow that depends on the extract artifact contract
- `docs/design.md` — current end-to-end runtime sequence and artifact boundaries

### Source + Artifact Models
- `skill_pipeline/pipeline_models/source.py` — annotated `ChronologyBlock` and `EvidenceItem` structures that feed packet assembly
- `skill_pipeline/preprocess/source.py` — source artifact builder that now produces the annotated inputs
- `skill_pipeline/paths.py` — existing deterministic artifact path conventions to extend cleanly for prompt packet outputs
- `skill_pipeline/cli.py` — current CLI stage boundaries and naming conventions

### Historical Prompt Background
- `docs/plans/2026-03-16-prompt-engineering-spec.md` — historical but useful background for packet structure, XML sections, actor roster usage, and chronology-first ordering
- `docs/plans/2026-03-16-pipeline-design-v3.md` — historical background on chunking, overlap, actor roster injection, and evidence appendix design

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Annotated `ChronologyBlock` records in `skill_pipeline/pipeline_models/source.py` already provide date/entity/evidence-density/temporal-phase metadata that Phase 2 should render directly instead of recomputing.
- `EvidenceItem` artifacts already exist as deterministic extraction anchors and can drive the active checklist formatting.
- `.claude/skills/extract-deal/SKILL.md` already defines the actor/event extraction contract and taxonomy, so Phase 2 can target that live interface instead of inventing a new extraction schema.
- `skill_pipeline/paths.py` centralizes artifact locations and is the natural place to extend path contracts for prompt-packet outputs.

### Established Patterns
- `skill_pipeline` is deterministic, stage-oriented, and fail-fast. Prompt composition should follow the same pattern: explicit inputs, explicit outputs, no hidden provider behavior.
- Artifact contracts are filesystem-backed and audit-friendly. Prompt packets should be persisted and inspectable, not transient strings.
- Repo truth for LLM behavior lives in `.claude/skills/`, not Python provider wrappers. The new engine must support those skills without absorbing model-calling logic.

### Integration Points
- `preprocess-source` outputs under `data/deals/<slug>/source/` are the direct prompt-engine inputs.
- `/extract-deal` is the immediate consumer that should read or reference the prompt packet artifacts.
- Future phases depend on the same packet contract: Phase 3 adds quote-before-extract, and Phase 5 adds complexity routing and expanded few-shots.

</code_context>

<specifics>
## Specific Ideas

- The repo already has a strong historical preference for XML-like prompt sections and chronology-first rendering. Phase 2 should preserve that direction but strip any stale provider-specific assumptions.
- The user wants Phase 2 to move forward now; Medivation seed-quality hardening is intentionally parked as a separate Claude todo and should not be folded into this phase.

</specifics>

<deferred>
## Deferred Ideas

- Complexity-based routing thresholds and automatic simple-vs-chunked mode selection belong to Phase 5 (`PROMPT-06`), even though Phase 2 should make both packet modes possible.
- Quote-before-extract response protocol belongs to Phase 3 (`PROMPT-05`), not this phase.
- Seed-quality hardening for wrong-accession filings remains deferred in `.planning/todos/pending/2026-03-27-investigate-seed-quality-guard-for-medivation-style-bad-accession.md`.

</deferred>

---

*Phase: 02-prompt-architecture*
*Context gathered: 2026-03-27*
