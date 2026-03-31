# Phase 16: Extraction Contract + Migration - Context

**Gathered:** 2026-03-31
**Status:** Complete
**Mode:** Auto-generated from live Phase 16 execution

<domain>
## Phase Boundary

Complete the migration boundary between the legacy flat extraction contract and
the additive v2 observation graph:

1. Add a v2 prompt-composition contract under `prompt_v2/`
2. Publish v2 skill docs for extraction and verification
3. Bootstrap v2 extraction artifacts from the verified v1 corpus
4. Validate STEC end-to-end through the full v2 runtime
5. Migrate the remaining 8 deals and document benchmark deltas

</domain>

<decisions>
## Implementation Decisions

- **D-01:** Keep Phase 16 additive. The v1 `prompt/`, `extract/`, and export
  surfaces remain live beside `prompt_v2/` and `extract_v2/`.
- **D-02:** Use a deterministic bridge (`migrate-extract-v1-to-v2`) so the
  9-deal corpus can move through the live v2 runtime without waiting on a fresh
  manual LLM pass for every deal.
- **D-03:** Patch the live v2 runtime only where migration exposed missing
  semantics: literal bidder-interest rows, extension round compilation, and
  coverage parity for ignored cue severities / multi-match NDA blocks.
- **D-04:** Treat the legacy adapter comparison as an analytical benchmark, not
  a byte-identity target on real deals. Row-count deltas are now informative.

</decisions>

<specifics>
## Specific Ideas

- `compose-prompts --contract v2 --mode observations` should write only to
  `prompt_v2/`.
- V2 prompt packets must instruct the model to emit `quotes`, `parties`,
  `cohorts`, `observations`, `exclusions`, and `coverage` in that order.
- Grouped v1 bidder actors migrate into `CohortRecord` rather than fake party
  slots so anonymous expansion stays export-only.
- Round announcement/deadline pairs migrate into solicitation observations, with
  separate `selected_to_advance` status observations when invitee lists exist.

</specifics>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md`
- `.planning/STATE.md`
- `CLAUDE.md`
- `skill_pipeline/compose_prompts.py`
- `skill_pipeline/migrate_extract_v1_to_v2.py`
- `skill_pipeline/derive.py`
- `skill_pipeline/coverage_v2.py`
- `.claude/skills/extract-deal-v2/SKILL.md`
- `.claude/skills/verify-extraction-v2/SKILL.md`

</canonical_refs>

<deferred>
## Deferred Ideas

- Native per-deal manual `/extract-deal-v2` reruns replacing the migration
  bridge
- Shared deterministic `verify-v2` runtime stage
- Milestone audit / cleanup after the user confirms the Phase 16 landing

</deferred>
