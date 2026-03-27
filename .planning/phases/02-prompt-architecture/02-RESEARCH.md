# Phase 2 Research — Prompt Architecture

**Researched:** 2026-03-27
**Scope:** Phase 2 only
**Confidence:** HIGH

## Executive Summary

Phase 2 should add a deterministic prompt-packet stage to the live
`skill_pipeline` runtime without turning Python into the model caller. The
current repo has annotated `ChronologyBlock` and `EvidenceItem` artifacts from
Phase 1, but it still jumps directly from `preprocess-source` to the
local-agent `/extract-deal` skill. There is no persisted prompt-packet layer,
no prompt artifact directory under `data/skill/<slug>/`, and no deterministic
chunk planner.

The clean implementation shape is:

- add a new deterministic `compose-prompts` stage in `skill_pipeline`
- persist provider-neutral prompt packet artifacts under `data/skill/<slug>/prompt/`
- keep model invocation and agent-specific calling details inside
  `.claude/skills/extract-deal/SKILL.md`
- make the new stage reusable by both actor extraction and event extraction
- validate the prompt packets deterministically before asking the local agent
  to use them

The live code already provides most of the raw inputs needed for Phase 2:

- `skill_pipeline/pipeline_models/source.py` defines annotated chronology
  blocks and evidence items
- `skill_pipeline/paths.py` centralizes artifact-path conventions
- `.claude/skills/extract-deal/SKILL.md` defines the live actor/event extraction
  contract
- `docs/plans/2026-03-16-prompt-engineering-spec.md` contains still-useful
  historical guidance on XML sections, actor roster placement, and chronology
  ordering

The main thing missing is a prompt-specific subsystem. There is no existing
`skill_pipeline/prompts/` package, no packet model module, and no prompt
validator script.

## Recommended Implementation Shape

### 1. Add a First-Class Deterministic Prompt Stage

The runtime should grow a new CLI command:

- `skill-pipeline compose-prompts --deal <slug> --mode actors|events|all`

This command should:

- load `chronology_blocks.jsonl` and `evidence_items.jsonl`
- optionally load a locked actor roster for event packets
- build prompt packet artifacts without any LLM call
- write a manifest plus packet files under `data/skill/<slug>/prompt/`

Recommended artifact layout:

- `data/skill/<slug>/prompt/manifest.json`
- `data/skill/<slug>/prompt/packets/<packet_id>/prefix.md`
- `data/skill/<slug>/prompt/packets/<packet_id>/body.md`
- `data/skill/<slug>/prompt/packets/<packet_id>/rendered.md`

This keeps prompt packets out of `extract/`, which should remain reserved for
LLM-produced actors/events.

### 2. Keep Packet Models Separate From Existing Extract Models

Prompt artifacts should live in a dedicated schema module such as:

- `skill_pipeline/pipeline_models/prompt.py`

Recommended model families:

- `PromptChunkWindow`
- `PromptPacketArtifact`
- `PromptPacketManifest`

These models should capture:

- packet family (`actors` or `events`)
- chunk mode (`single_pass` or `chunked`)
- target block IDs
- overlap block IDs
- estimated token count
- asset paths and rendered packet file paths

Do not hide these details in untyped dicts. Phase 2 is an artifact-contract
phase as much as a rendering phase.

### 3. Separate Chunk Planning, Checklist Construction, And Rendering

The new logic should be split into deterministic helpers, not one giant
orchestrator:

- `skill_pipeline/prompts/chunks.py`
- `skill_pipeline/prompts/checklist.py`
- `skill_pipeline/prompts/render.py`

Recommended responsibilities:

- `chunks.py`: token estimation, whole-block chunk windows, exact 2-block overlap
- `checklist.py`: convert evidence items into a compact active checklist
- `render.py`: build packet sections in a fixed order and write packet files

The chunk planner should support both:

- `single_pass` packets when the block set fits the chosen budget
- `chunked` packets when it does not

Phase 2 should not hard-code the final complexity-routing policy. Phase 5 owns
the decision rule for when simple deals route to single-pass versus multi-chunk.
Phase 2 only needs the engine to make both packet types possible.

### 4. Use File-Backed Provider-Neutral Prompt Assets

Stable prompt material should live in versioned repo files, not embedded
triple-quoted strings. Recommended asset families:

- actor prefix / taxonomy guidance
- event prefix / taxonomy guidance
- compact few-shot examples

The repo currently has no live prompt-asset directory. Creating one inside
`skill_pipeline/` is acceptable as long as it remains provider-neutral and does
not introduce model-calling logic.

### 5. Update The Extract Skill To Consume Packets, Not Compose Them

After `compose-prompts` exists, `.claude/skills/extract-deal/SKILL.md` should
change from “read raw source artifacts and mentally assemble prompts” to “read
the composed prompt packet artifacts and execute the extraction passes against
those packets.”

Because `CLAUDE.md` declares `.codex/skills/` and `.cursor/skills/` as derived
mirrors, Phase 2 planning must include mirror sync when the canonical
`.claude/skills/extract-deal/SKILL.md` changes.

### 6. Validate With Deterministic Tests Plus One Real Deal

The correct validation stack for Phase 2 is:

- packet model tests
- chunk-planner and render tests
- CLI and path-contract tests
- prompt packet validator on `stec`
- one human-readable `stec` packet inspection
- one `stec` extraction run through the new packets before Phase 2 closes

That final extraction-quality check is necessary because the roadmap exit
criteria require equal or better quality versus baseline, not just pretty packet
files.

## Risks To Watch

### Mixing Prompt Artifacts Into `extract/`

Do not write prompt packets into `data/skill/<slug>/extract/`. That directory
already means “LLM-produced actor/event artifacts.” Mixing prompt inputs and
model outputs will blur stage boundaries and make diagnostics harder.

### Smuggling Provider Behavior Back Into Python

The phase goal is prompt composition, not a Python LLM runtime. Avoid any
design that adds provider names, API payloads, chat roles, or model-call retry
logic to `skill_pipeline`.

### Locking In Phase 5 Routing Too Early

It is correct to implement chunk planning now. It is not correct to freeze the
final `<=150 blocks` / `<=8 actors` routing thresholds in Phase 2. Those belong
to PROMPT-06 in Phase 5.

### Overweight Few-Shot Payloads

The historical spec is explicit that few-shots must stay short. A good Phase 2
engine needs file-backed few-shots, but not long examples that bury the filing
text.

### Skill Mirror Drift

Any change to `.claude/skills/extract-deal/SKILL.md` should be mirrored into
`.codex/skills/` and `.cursor/skills/`, or the repo’s mirror-sync tests will
drift.

## Validation Architecture

### Automated Checks

- Model and path contract:
  `python -m pytest -q tests/test_skill_prompt_models.py tests/test_skill_pipeline.py`
- Renderer and chunk planner:
  `python -m pytest -q tests/test_skill_compose_prompts.py`
- Skill/docs boundary:
  `python -m pytest -q tests/test_skill_mirror_sync.py tests/test_benchmark_separation_policy.py tests/test_runtime_contract_docs.py`
- Full suite:
  `python -m pytest -q`

### Packet Validation

Add a deterministic helper script:

- `scripts/validate_prompt_packets.py`

It should:

- load `manifest.json`
- validate packet artifacts with the prompt packet models
- check for required XML sections in rendered packets
- assert overlap sections only appear for chunked windows
- support a concrete `stec` validation command

### Manual Checks

- Inspect one `stec` actor packet and one `stec` event packet
- confirm chronology blocks are visually above task instructions
- confirm the event packet includes actor roster and evidence checklist
- confirm chunked packets, if any, clearly distinguish `<overlap_context>` from
  primary extraction blocks
- before closing the phase, run `/extract-deal stec` using the generated prompt
  packets and compare downstream gate quality to the pre-Phase-2 baseline

## Files To Read First During Execution

- `.planning/phases/02-prompt-architecture/02-CONTEXT.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/PROJECT.md`
- `.claude/skills/extract-deal/SKILL.md`
- `.claude/skills/verify-extraction/SKILL.md`
- `docs/design.md`
- `docs/plans/2026-03-16-prompt-engineering-spec.md`
- `docs/plans/2026-03-16-pipeline-design-v3.md`
- `skill_pipeline/cli.py`
- `skill_pipeline/models.py`
- `skill_pipeline/paths.py`
- `skill_pipeline/pipeline_models/source.py`
- `skill_pipeline/preprocess/source.py`

---
*Phase 2 research created from the live codebase, live skill contract, and historical prompt-design background docs*
