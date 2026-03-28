---
phase: 03-quote-before-extract
verified: 2026-03-28T10:02:48Z
status: gaps_found
score: 5/7 must-haves verified
gaps:
  - truth: "Active extract-artifact runtime consumers continue to work after the quote_first migration"
    status: failed
    reason: "`skill_pipeline.deal_agent` still branches on the removed `legacy` mode and crashes when summarizing current extract artifacts."
    artifacts:
      - path: "skill_pipeline/deal_agent.py"
        issue: "Lines 80-81 still test `artifacts.mode == \"legacy\"`; quote-first artifacts fall into the canonical branch and dereference `artifacts.actors` / `artifacts.events` as None."
      - path: "tests/test_skill_pipeline.py"
        issue: "`run_deal_agent()` fails in the phase regression tests at lines 305 and 366 with `AttributeError: 'NoneType' object has no attribute 'actors'`."
    missing:
      - "Update `_summarize_extract()` to support `quote_first` alongside canonical artifacts."
      - "Rerun `python -m pytest tests/test_skill_pipeline.py -q --tb=short` and the full suite until green."
  - truth: "Coverage-facing consumers and tests are aligned with the quote_first extract contract"
    status: failed
    reason: "The coverage surface still contains legacy-mode assumptions, and its tests still materialize raw artifacts in the retired legacy shape."
    artifacts:
      - path: "skill_pipeline/coverage.py"
        issue: "Lines 227-243 still dispatch on `legacy` and reference removed `evidence_refs` fields."
      - path: "tests/test_skill_coverage.py"
        issue: "Default fixtures at lines 49-52 write raw artifacts without top-level `quotes` or canonical `evidence_span_ids`; 5 tests now fail because `load_extract_artifacts()` rejects that format."
    missing:
      - "Make coverage explicitly canonical-only or add proper `quote_first` handling; remove the stale `legacy` branch either way."
      - "Migrate `tests/test_skill_coverage.py` fixtures to the supported extract schema and rerun the coverage suite."
---

# Phase 3: quote-before-extract Verification Report

**Phase Goal:** Force the LLM to cite verbatim filing passages before emitting structured events.
**Verified:** 2026-03-28T10:02:48Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Raw extraction artifacts use a quote-first contract and reject legacy `evidence_refs` payloads. | ✓ VERIFIED | [skill_pipeline/models.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/models.py#L70) defines `QuoteEntry`, raw actor/event models use `quote_ids`, and [skill_pipeline/extract_artifacts.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/extract_artifacts.py#L35) only accepts `quote_first` or canonical payloads. |
| 2 | Prompt packets tell the extractor to emit verbatim quotes before structured actors or events. | ✓ VERIFIED | [skill_pipeline/compose_prompts.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/compose_prompts.py#L169) and [skill_pipeline/compose_prompts.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/compose_prompts.py#L235) inject the quote-before-extract instructions into actor and event packets; prefix assets and examples match in [actors_prefix.md](/home/austinli/Projects/bids_pipeline/skill_pipeline/prompt_assets/actors_prefix.md#L26), [events_prefix.md](/home/austinli/Projects/bids_pipeline/skill_pipeline/prompt_assets/events_prefix.md#L20), and [event_examples.md](/home/austinli/Projects/bids_pipeline/skill_pipeline/prompt_assets/event_examples.md#L3). |
| 3 | Canonicalize resolves quote-first outputs into canonical span-backed artifacts. | ✓ VERIFIED | [skill_pipeline/canonicalize.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/canonicalize.py#L88) resolves quotes to spans, [skill_pipeline/canonicalize.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/canonicalize.py#L145) maps `quote_ids` to `evidence_span_ids`, and [skill_pipeline/canonicalize.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/canonicalize.py#L403) upgrades `quote_first` payloads while logging orphaned quotes. |
| 4 | Verify and check enforce the quote-first evidence contract. | ✓ VERIFIED | [skill_pipeline/verify.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/verify.py#L78) validates quote text against filing text, [skill_pipeline/verify.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/verify.py#L169) checks `quote_id` integrity, and [skill_pipeline/check.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/check.py#L30) / [skill_pipeline/check.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/check.py#L82) use `quote_ids` and quote text in quote-first mode. |
| 5 | The extract-deal skill contract and Codex mirror document the same quote-first schema. | ✓ VERIFIED | [`.claude/skills/extract-deal/SKILL.md`](/home/austinli/Projects/bids_pipeline/.claude/skills/extract-deal/SKILL.md#L57) documents the protocol and schema, and `.claude` / `.codex` copies are byte-identical (`cmp` exit code `0`); `tests/test_skill_mirror_sync.py` also passes. |
| 6 | Active extract-artifact runtime consumers still work after removing `legacy` mode. | ✗ FAILED | [skill_pipeline/deal_agent.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/deal_agent.py#L75) still branches on `legacy`; `python -m pytest tests/test_skill_pipeline.py -q --tb=short` fails in [tests/test_skill_pipeline.py](/home/austinli/Projects/bids_pipeline/tests/test_skill_pipeline.py#L301) and [tests/test_skill_pipeline.py](/home/austinli/Projects/bids_pipeline/tests/test_skill_pipeline.py#L329). |
| 7 | Coverage-facing code and tests are migrated to the new extract contract. | ✗ FAILED | [skill_pipeline/coverage.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/coverage.py#L226) still dispatches on `legacy`, and [tests/test_skill_coverage.py](/home/austinli/Projects/bids_pipeline/tests/test_skill_coverage.py#L49) still writes legacy raw fixtures; `python -m pytest tests/test_skill_coverage.py -q --tb=short` reports 5 failures. |

**Score:** 5/7 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `skill_pipeline/models.py` | Quote-first raw schema | ✓ VERIFIED | `QuoteEntry`, top-level `quotes`, and raw `quote_ids` are present; `EvidenceRef` is gone. |
| `skill_pipeline/extract_artifacts.py` | Loader supports `quote_first` and canonical only | ✓ VERIFIED | `LoadedExtractArtifacts.mode` is `Literal["quote_first", "canonical"]`; legacy payloads are rejected. |
| `skill_pipeline/canonicalize.py` | Quote-to-span upgrade path | ✓ VERIFIED | Resolves quotes through `resolve_text_span`, upgrades raw artifacts, and writes orphaned-quote log entries. |
| `skill_pipeline/verify.py` | Quote validation and `quote_id` integrity | ✓ VERIFIED | Raw quote-first checks and canonical span checks coexist correctly. |
| `skill_pipeline/check.py` | Quote-first structural gate support | ✓ VERIFIED | Uses `quote_ids` / quote text before canonicalization and `evidence_span_ids` after canonicalization. |
| `skill_pipeline/compose_prompts.py` + prompt assets | Quote-before-extract instructions in rendered packets | ✓ VERIFIED | Task instructions, prefix assets, and examples all teach a quotes-first output. |
| `.claude/skills/extract-deal/SKILL.md` | Canonical skill contract updated | ✓ VERIFIED | Documents `quotes`, `quote_id`, and `quote_ids`; mirrored copy is synced. |
| `skill_pipeline/deal_agent.py` | Runtime consumer updated for `quote_first` | ✗ FAILED | Still keyed on removed `legacy` mode, causing `run_deal_agent()` crashes. |
| `skill_pipeline/coverage.py` + `tests/test_skill_coverage.py` | Coverage surface migrated to the supported extract schemas | ✗ FAILED | Code keeps a stale `legacy` branch and tests still build rejected legacy fixtures. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| [skill_pipeline/compose_prompts.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/compose_prompts.py#L204) | prompt renderer | `task_instructions` passed into `render_actor_packet` / `render_event_packet` | ✓ WIRED | Rendered-packet tests in [tests/test_skill_compose_prompts.py](/home/austinli/Projects/bids_pipeline/tests/test_skill_compose_prompts.py#L638) and [tests/test_skill_compose_prompts.py](/home/austinli/Projects/bids_pipeline/tests/test_skill_compose_prompts.py#L707) pass. |
| [skill_pipeline/extract_artifacts.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/extract_artifacts.py#L35) | [skill_pipeline/canonicalize.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/canonicalize.py#L402) | `load_extract_artifacts()` | ✓ WIRED | `run_canonicalize()` branches on `quote_first` and upgrades raw artifacts. |
| [skill_pipeline/canonicalize.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/canonicalize.py#L126) | provenance resolver | `resolve_text_span()` | ✓ WIRED | Quote text becomes canonical spans before later gates run. |
| [skill_pipeline/verify.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/verify.py#L65) | quote normalizer | `find_anchor_in_segment()` through `_resolve_quote_match()` | ✓ WIRED | Raw quote validation uses exact/normalized matching plus +/-3 line expansion. |
| [`.claude/skills/extract-deal/SKILL.md`](/home/austinli/Projects/bids_pipeline/.claude/skills/extract-deal/SKILL.md#L187) | [`.codex/skills/extract-deal/SKILL.md`](/home/austinli/Projects/bids_pipeline/.codex/skills/extract-deal/SKILL.md#L187) | mirror sync | ✓ WIRED | `cmp` returns `0` and `tests/test_skill_mirror_sync.py` passes. |
| [skill_pipeline/deal_agent.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/deal_agent.py#L79) | [skill_pipeline/extract_artifacts.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/extract_artifacts.py#L35) | `_summarize_extract()` | ✗ NOT WIRED | Loader returns `quote_first`, but consumer still tests for `legacy` and crashes. |
| [skill_pipeline/coverage.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/coverage.py#L226) | [skill_pipeline/extract_artifacts.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/extract_artifacts.py#L35) | `_cue_is_covered()` mode dispatch | ⚠️ PARTIAL | Canonical path works, but the raw-mode branch still targets removed `legacy` semantics. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| [skill_pipeline/canonicalize.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/canonicalize.py#L408) | `all_quotes` | `loaded.raw_actors.quotes` + `loaded.raw_events.quotes` from `load_extract_artifacts()` | Yes | ✓ FLOWING |
| [skill_pipeline/verify.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/verify.py#L96) | `all_quotes` | Raw quote arrays in quote-first artifacts | Yes | ✓ FLOWING |
| [skill_pipeline/deal_agent.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/deal_agent.py#L80) | `actors` / `events` | `load_extract_artifacts()` mode switch | No | ✗ DISCONNECTED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Quote-first core runtime/tests stay green | `python -m pytest tests/test_skill_verify.py tests/test_skill_check.py tests/test_skill_canonicalize.py tests/test_skill_enrich_core.py tests/test_skill_compose_prompts.py tests/test_skill_provenance.py -q --tb=short` | `94 passed in 0.19s` | ✓ PASS |
| Prompt-model + mirror-sync regression gate stays green | `python -m pytest tests/test_skill_prompt_models.py tests/test_skill_compose_prompts.py tests/test_skill_mirror_sync.py -q --tb=short` | `60 passed in 0.13s` | ✓ PASS |
| Deal-agent still summarizes current extract artifacts | `python -m pytest tests/test_skill_pipeline.py -q --tb=short` | `2 failed, 17 passed` | ✗ FAIL |
| Coverage surface is aligned with the new extract contract | `python -m pytest tests/test_skill_coverage.py -q --tb=short` | `5 failed, 3 passed` | ✗ FAIL |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| `PROMPT-05` | `03-01`, `03-02`, `03-03`, `03-04` | Quote-before-extract protocol forces the LLM to cite verbatim passages before emitting structured events. | ✓ SATISFIED | Prompt/task contract is explicit in [skill_pipeline/compose_prompts.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/compose_prompts.py#L180), prompt assets, the canonical [extract-deal skill doc](/home/austinli/Projects/bids_pipeline/.claude/skills/extract-deal/SKILL.md#L187), and the raw schema / canonicalize / verify pipeline. |

No orphaned Phase 03 requirements were found in [REQUIREMENTS.md](/home/austinli/Projects/bids_pipeline/.planning/REQUIREMENTS.md).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| [skill_pipeline/deal_agent.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/deal_agent.py#L80) | 80 | Stale mode switch on removed `legacy` contract | 🛑 Blocker | Quote-first extract artifacts crash `run_deal_agent()` instead of being summarized. |
| [skill_pipeline/coverage.py](/home/austinli/Projects/bids_pipeline/skill_pipeline/coverage.py#L227) | 227 | Dead `legacy` branch with removed `evidence_refs` access | ⚠️ Warning | Coverage mode handling is inconsistent with the live loader and obscures the supported contract. |
| [tests/test_skill_coverage.py](/home/austinli/Projects/bids_pipeline/tests/test_skill_coverage.py#L49) | 49 | Stale legacy raw-fixture shape | ⚠️ Warning | The suite no longer matches the supported extract schemas, so 5 coverage tests fail immediately at load time. |

### Human Verification Required

1. `stec` live extraction quality

**Test:** Run `compose-prompts`, `/extract-deal`, `canonicalize`, `check`, and `verify` on `stec`, then inspect that raw extraction outputs start with a `quotes` array and that the canonicalized run preserves recall.
**Expected:** The extractor emits verbatim quotes first, downstream gates pass, and quote grounding is at least as strong as the pre-phase baseline.
**Why human:** This requires an actual LLM extraction run and recall-quality judgment, not just static code verification.

2. `medivation` stress-case extraction quality

**Test:** Run the same quote-first flow on `medivation` and compare actor/event recall plus exact quote-grounding behavior to the prior baseline.
**Expected:** The quote-first protocol does not materially reduce recall on the complex deal and improves evidence grounding quality.
**Why human:** The comparison depends on live model behavior and qualitative extraction review.

### Gaps Summary

The quote-first extraction contract itself is implemented: the raw schema, loader, prompt packets, canonicalize, verify, check, extract-deal skill doc, and Codex mirror all reflect the new `quotes` + `quote_ids` design. The core Phase 03 suites for those surfaces pass.

The phase is not yet fully achieved in the live codebase because the migration stopped short of all downstream consumers. `skill_pipeline.deal_agent` still assumes the retired `legacy` mode, and the coverage surface still contains legacy assumptions and stale tests. The full pytest suite therefore remains red (`7 failed, 196 passed`). Until those consumers are migrated, Phase 03 should remain in `gaps_found` status.

---
_Verified: 2026-03-28T10:02:48Z_
_Verifier: Claude (gsd-verifier)_
