---
phase: 02-prompt-architecture
verified: 2026-03-27T23:58:00Z
status: passed
score: 9/9 must-haves verified
must_haves:
  truths:
    - "`skill-pipeline compose-prompts` exists as a deterministic runtime stage and performs no model calls"
    - "prompt packet artifacts live under `data/skill/<slug>/prompt/` instead of being mixed into `extract/`"
    - "prompt packet manifests and paths are schema-validated rather than untyped dicts"
    - "rendered prompt packets place chronology blocks before task instructions"
    - "chunk windows never split chronology blocks and chunked packets use explicit 2-block `<overlap_context>` sections"
    - "evidence items are rendered as an active checklist rather than a passive appendix"
    - "the live extraction skill reads composed prompt packet artifacts instead of mentally assembling prompts from raw source inputs"
    - "prompt packet artifacts can be validated deterministically on `stec` before an LLM extraction run"
    - "runtime docs and deal-agent status expose the prompt stage without introducing provider-specific Python behavior"
  artifacts:
    - path: "skill_pipeline/pipeline_models/prompt.py"
      provides: "prompt packet artifact schema"
      status: verified
    - path: "skill_pipeline/compose_prompts.py"
      provides: "deterministic prompt composition stage entrypoint"
      status: verified
    - path: "skill_pipeline/prompts/chunks.py"
      provides: "deterministic whole-block chunk planning"
      status: verified
    - path: "skill_pipeline/prompts/render.py"
      provides: "provider-neutral packet rendering"
      status: verified
    - path: "skill_pipeline/prompts/checklist.py"
      provides: "evidence checklist builder"
      status: verified
    - path: "scripts/validate_prompt_packets.py"
      provides: "deterministic validator for prompt packet artifacts"
      status: verified
    - path: "tests/test_skill_prompt_models.py"
      provides: "schema and path contract regression coverage"
      status: verified
    - path: "tests/test_skill_compose_prompts.py"
      provides: "prompt chunking and rendering regression coverage"
      status: verified
    - path: ".claude/skills/extract-deal/SKILL.md"
      provides: "canonical extract workflow contract for prompt packet consumption"
      status: verified
    - path: "docs/design.md"
      provides: "updated runtime sequence including compose-prompts"
      status: verified
  key_links:
    - from: "skill_pipeline/cli.py"
      to: "skill_pipeline/compose_prompts.py"
      via: "compose-prompts subcommand dispatch calling run_compose_prompts"
      status: verified
    - from: "skill_pipeline/paths.py"
      to: "skill_pipeline/models.py"
      via: "SkillPathSet prompt_dir, prompt_packets_dir, prompt_manifest_path"
      status: verified
    - from: "skill_pipeline/compose_prompts.py"
      to: "skill_pipeline/prompts/chunks.py"
      via: "build_chunk_windows import and call"
      status: verified
    - from: "skill_pipeline/compose_prompts.py"
      to: "skill_pipeline/prompts/render.py"
      via: "render_actor_packet and render_event_packet import and call"
      status: verified
    - from: ".claude/skills/extract-deal/SKILL.md"
      to: "scripts/validate_prompt_packets.py"
      via: "preflight instructions referencing validator"
      status: verified
    - from: "tests/test_skill_mirror_sync.py"
      to: ".claude/skills/extract-deal/SKILL.md"
      via: "mirror byte-equality assertions"
      status: verified
requirements:
  - id: INFRA-01
    status: satisfied
  - id: INFRA-02
    status: satisfied
  - id: INFRA-03
    status: satisfied
  - id: INFRA-05
    status: satisfied
  - id: PROMPT-01
    status: satisfied
  - id: PROMPT-02
    status: satisfied
  - id: PROMPT-03
    status: satisfied
  - id: PROMPT-04
    status: satisfied
---

# Phase 2: Prompt Architecture Verification Report

**Phase Goal:** Build the deterministic prompt composition engine that assembles extraction prompt packets from annotated blocks.
**Verified:** 2026-03-27T23:58:00Z
**Status:** passed
**Re-verification:** No -- initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `skill-pipeline compose-prompts` exists as a deterministic runtime stage and performs no model calls | VERIFIED | CLI subcommand parsed and dispatched (cli.py L163-185, L244-252). Zero provider SDK imports in compose_prompts.py (grep confirmed). |
| 2 | Prompt packet artifacts live under `data/skill/<slug>/prompt/` instead of being mixed into `extract/` | VERIFIED | paths.py L23,56-58 sets prompt_dir = skill_root / "prompt". ensure_output_directories creates prompt_dir and prompt_packets_dir. stec artifacts exist at data/skill/stec/prompt/. |
| 3 | Prompt packet manifests and paths are schema-validated rather than untyped dicts | VERIFIED | PromptPacketManifest, PromptPacketArtifact, PromptChunkWindow are Pydantic models in pipeline_models/prompt.py. Exported from __init__.py. 192-line test file validates schema. JSON round-trip confirmed. |
| 4 | Rendered prompt packets place chronology blocks before task instructions | VERIFIED | render.py body_parts ordering: deal_context, chronology_blocks, overlap_context, evidence_checklist, actor_roster, task_instructions. Tests assert `<chronology_blocks>` index < `<task_instructions>` index. |
| 5 | Chunk windows never split chronology blocks and chunked packets use explicit 2-block `<overlap_context>` sections | VERIFIED | chunks.py build_chunk_windows accumulates whole blocks (L80-92), overlap_blocks=2 default (L33). Tests verify target/overlap disjointness, all blocks covered, overlap capped at 4 (2 leading + 2 trailing). |
| 6 | Evidence items are rendered as an active checklist rather than a passive appendix | VERIFIED | checklist.py groups by EvidenceType with imperative headers ("Dated actions to extract", etc.), renders markdown checkboxes with evidence_id, line range, and hint parts. Tests confirm grouped output and evidence ID presence. |
| 7 | The live extraction skill reads composed prompt packet artifacts instead of mentally assembling prompts from raw source inputs | VERIFIED | .claude/skills/extract-deal/SKILL.md Reads table includes prompt manifest and packet files. Preflight section instructs running compose-prompts before extraction. Mirror files (.codex, .cursor) are byte-identical. |
| 8 | Prompt packet artifacts can be validated deterministically on `stec` before an LLM extraction run | VERIFIED | scripts/validate_prompt_packets.py exists (123 lines), checks schema + rendered tags. `python scripts/validate_prompt_packets.py --deal stec --expect-sections` outputs "PASS: All prompt packets valid for stec." |
| 9 | Runtime docs and deal-agent status expose the prompt stage without introducing provider-specific Python behavior | VERIFIED | CLAUDE.md contains compose-prompts in runtime split, end-to-end flow, artifact contract, and dev commands. docs/design.md includes compose-prompts in sequence. deal_agent.py imports PromptStageSummary and wires _summarize_prompt. No provider SDK imports anywhere in the stage. |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `skill_pipeline/pipeline_models/prompt.py` | Prompt packet artifact schema | VERIFIED | 44 lines, 3 Pydantic models (PromptChunkWindow, PromptPacketArtifact, PromptPacketManifest), Literal-typed fields, exported from __init__.py |
| `skill_pipeline/compose_prompts.py` | Deterministic prompt composition stage entrypoint | VERIFIED | 373 lines, run_compose_prompts function, loads blocks/evidence, builds windows, renders packets, writes manifest. No provider imports. |
| `skill_pipeline/prompts/chunks.py` | Deterministic whole-block chunk planning | VERIFIED | 139 lines, estimate_block_tokens and build_chunk_windows exported. Greedy whole-block algorithm with 2-block overlap. |
| `skill_pipeline/prompts/render.py` | Provider-neutral packet rendering | VERIFIED | 213 lines, render_actor_packet and render_event_packet. Fixed XML section ordering. Actor roster only in event packets. |
| `skill_pipeline/prompts/checklist.py` | Evidence checklist builder | VERIFIED | 82 lines, build_evidence_checklist groups by type with imperative headers. |
| `scripts/validate_prompt_packets.py` | Deterministic validator for prompt packet artifacts | VERIFIED | 123 lines, validates schema + rendered content tags. --expect-sections flag, --deal, --project-root. |
| `tests/test_skill_prompt_models.py` | Schema and path contract regression coverage | VERIFIED | 192 lines (min 40 required). Covers all 3 models, validation errors, round-trip, envelope inheritance. |
| `tests/test_skill_compose_prompts.py` | Prompt chunking and rendering regression coverage | VERIFIED | 636 lines (min 60 required). 34+ tests covering chunks, checklist, render, and end-to-end integration. |
| `.claude/skills/extract-deal/SKILL.md` | Canonical extract workflow contract for prompt packet consumption | VERIFIED | Contains data/skill/<slug>/prompt/manifest.json in Reads table, preflight instructions, packet-based extraction method. |
| `docs/design.md` | Updated runtime sequence including compose-prompts | VERIFIED | Contains compose-prompts in operational sequence and artifact flow. |
| `skill_pipeline/prompt_assets/actors_prefix.md` | Stable actor extraction prefix | VERIFIED | 35 lines, provider-neutral, no chat-role wrappers. |
| `skill_pipeline/prompt_assets/events_prefix.md` | Stable event extraction prefix | VERIFIED | 29 lines, provider-neutral, no chat-role wrappers. |
| `skill_pipeline/prompt_assets/event_examples.md` | Few-shot event examples | VERIFIED | 22 lines, range proposal and formal-round examples. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `skill_pipeline/cli.py` | `skill_pipeline/compose_prompts.py` | compose-prompts subcommand dispatch | VERIFIED | cli.py L11 imports run_compose_prompts, L163-185 registers subcommand, L244-252 dispatches call |
| `skill_pipeline/paths.py` | `skill_pipeline/models.py` | SkillPathSet prompt paths | VERIFIED | models.py L56-58 declares prompt_dir, prompt_packets_dir, prompt_manifest_path. paths.py L23,56-58 builds them. paths.py L70-71 ensures directories. |
| `skill_pipeline/compose_prompts.py` | `skill_pipeline/prompts/chunks.py` | build_chunk_windows import and call | VERIFIED | compose_prompts.py L24 imports build_chunk_windows, L308 calls it. |
| `skill_pipeline/compose_prompts.py` | `skill_pipeline/prompts/render.py` | render_actor_packet, render_event_packet import and call | VERIFIED | compose_prompts.py L25 imports both, L138 calls render_actor_packet, L196 calls render_event_packet. |
| `.claude/skills/extract-deal/SKILL.md` | `scripts/validate_prompt_packets.py` | Preflight instructions referencing validator | VERIFIED | SKILL.md line references validate_prompt_packets.py with --expect-sections flag. |
| `tests/test_skill_mirror_sync.py` | `.claude/skills/extract-deal/SKILL.md` | Mirror synchronization assertions | VERIFIED | Tests assert prompt manifest reference in canonical, byte-equality for .codex and .cursor mirrors. Both mirrors confirmed identical via diff. |

### Data-Flow Trace (Level 4)

Not applicable -- this phase produces a deterministic file-writing pipeline stage, not a UI component rendering dynamic data. The compose-prompts stage reads source artifacts (chronology_blocks.jsonl, evidence_items.jsonl) and writes prompt packet files. The data flow was verified through the stec end-to-end validation: real source artifacts in, real prompt packet files out, validator confirms content tags present.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| CLI parses compose-prompts | `build_parser().parse_args(['compose-prompts', '--deal', 'stec'])` | command=compose-prompts deal=stec mode=all budget=6000 | PASS |
| Chunk planner produces single_pass for small input | `build_chunk_windows([block], 10000)` | windows=1 mode=single_pass | PASS |
| Prompt model round-trips through JSON | `PromptPacketManifest.model_validate_json(manifest.model_dump_json())` | round_trip_ok=True | PASS |
| stec prompt packets pass validation | `python scripts/validate_prompt_packets.py --deal stec --expect-sections` | PASS: All prompt packets valid for stec. | PASS |
| Full test suite passes | `python -m pytest -q` | 191 passed, 3 warnings in 0.72s | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| INFRA-01 | 02-01, 02-03 | Local-agent extraction flows can enforce schema-constrained structured outputs without introducing a Python-side provider wrapper | SATISFIED | Prompt packet schemas are Pydantic models. No provider SDK imports in any phase 2 file. Extraction skill contract references prompt packets, not provider APIs. |
| INFRA-02 | 02-01, 02-03 | Repo-level extraction and orchestration contracts remain agent- and provider-agnostic | SATISFIED | All prompt assets, render functions, and CLI are provider-neutral. CLAUDE.md, docs/design.md, and skill docs describe compose-prompts without provider specifics. |
| INFRA-03 | 02-02, 02-03 | Prompt composition exposes a reusable static prefix separate from chunk-specific content | SATISFIED | render.py returns (prefix_text, body_text, rendered_text) tuple. compose_prompts.py writes prefix.md and body.md as separate files per packet. Prefix loaded from stable prompt_assets/. |
| INFRA-05 | 02-01, 02-02, 02-03 | A deterministic prompt composition engine assembles extraction prompt packets | SATISFIED | run_compose_prompts loads source, builds chunk windows, renders packets, writes manifest. All steps deterministic. stec validated end-to-end. 191 tests pass. |
| PROMPT-01 | 02-02, 02-03 | Extraction prompts place chronology text first and instructions/query last | SATISFIED | render.py body_parts ordering: deal_context, chronology_blocks, ..., task_instructions. Multiple tests assert positional ordering. |
| PROMPT-02 | 02-02, 02-03 | Chunk boundaries align with chronology block boundaries; never split mid-block | SATISFIED | chunks.py build_chunk_windows accumulates whole blocks only (L80-92). "at least one block per window" guarantee even if oversized. Tests verify all blocks appear in exactly one window's target_block_ids. |
| PROMPT-03 | 02-02, 02-03 | Chunked extraction includes 2-block overlap with explicit `<overlap_context>` XML tags | SATISFIED | chunks.py overlap_blocks=2 default. render.py emits `<overlap_context>` section only when overlap_block_ids is non-empty. Tests confirm overlap present in chunked, absent in single_pass. |
| PROMPT-04 | 02-02, 02-03 | Evidence items formatted as an active checklist the LLM must address | SATISFIED | checklist.py build_evidence_checklist groups by type with imperative headers, renders checkbox bullets with evidence_id, line range, and hints. Tests confirm grouped output. |

No orphaned requirements. All 8 requirement IDs declared in PLAN frontmatter are present in REQUIREMENTS.md and map to Phase 2. All are satisfied.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| skill_pipeline/prompts/chunks.py | 96-100 | Comments say "placeholder, set below" | Info | Not a stub -- values are overwritten 10 lines later in the same function (L111-137). Algorithmic two-pass pattern. No impact. |

No blocker or warning-level anti-patterns found. No TODO/FIXME/PLACEHOLDER comments in any phase 2 production files. No empty implementations. No provider SDK imports.

### Human Verification Required

### 1. Prompt Packet Content Quality

**Test:** Run `skill-pipeline compose-prompts --deal stec --mode actors --chunk-budget 6000` and manually inspect a rendered.md file for readability and coherence.
**Expected:** Chronology blocks appear in document order with clear block IDs, evidence checklist has actionable imperative bullets, task instructions are clear.
**Why human:** Content quality and readability require human judgment. Automated checks confirm structural correctness but not semantic quality.

### 2. stec End-to-End Extraction Quality

**Test:** Follow the documented stec validation path (compose-prompts -> /extract-deal -> canonicalize -> check -> verify -> coverage) and compare extraction quality to baseline.
**Expected:** Deterministic gates (check, verify, coverage) pass on filing-grounded extraction through composed prompt packets.
**Why human:** The full extraction loop requires running a local agent for the /extract-deal step, which is not automatable within verification.

### Gaps Summary

No gaps found. All 9 observable truths verified. All 13 artifacts pass three-level verification (exist, substantive, wired). All 6 key links confirmed. All 8 requirement IDs satisfied. 191 tests pass. stec prompt packets validated. No provider SDK imports. No blocking anti-patterns.

---

_Verified: 2026-03-27T23:58:00Z_
_Verifier: Claude (gsd-verifier)_
