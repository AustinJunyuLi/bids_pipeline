# Coverage Omission Audit Design

**Date:** 2026-03-22  
**Status:** Proposed  
**Goal:** Reduce systematic structural omissions while preserving the pipeline's filing-grounded verification model.

## Problem

Reconciliation has shown a repeatable omission pattern in the current skill workflow. The pipeline is generally strong on directly extracted proposals, NDAs, executed events, and explicit bidder actions, but it under-detects several structural event classes that appear in the filing text and matter for review:

- round announcements and round deadlines
- target-caused exclusion events
- adviser / IB retention events
- go-shop ending events

The current deterministic `coverage` stage is too narrow to catch these omissions systematically. It primarily audits broad cue families such as proposals, NDAs, drops, and process initiation. As a result, the pipeline can complete with a clean structural surface while still missing important filing-grounded events.

The wrong fix would be to create a new stage that invents events after canonicalization. That would weaken the current trust model because post-canonicalize events are expected to be span-backed and verifiable. Instead, the design should strengthen omission detection while keeping actual artifact edits inside the existing repair layer.

## Design Principles

1. **Filing-grounded first.** Benchmark reconciliation can motivate the redesign, but the generation workflow must continue to rely only on the filing text and deterministic repo rules.
2. **Detection and repair stay separate.** `coverage` identifies likely missing events; `/verify-extraction` remains the only stage that can add or modify events in response.
3. **No unverifiable synthetic events.** The design must not introduce event records that bypass the canonical `evidence_span_ids` contract or the strict verification stage.
4. **Block only on explicit support.** The system should fail closed only when the filing clearly states an omitted event. Strong but ambiguous signals should become warnings.
5. **Phase in carefully.** Start with a narrow family set and warning-heavy rollout before promoting stable patterns to blocking errors.

## Scope

Phase 1 covers four omission families:

- `round_event`
- `target_caused_drop`
- `ib_retention`
- `go_shop_end`

This is intentionally narrower than "everything Alex tracks." The purpose is to catch the highest-signal structural misses without reopening all benchmark boundary questions or changing the event taxonomy.

Non-goals for this phase:

- adding a new pipeline stage
- writing synthetic events directly from coverage
- converting partial-company exclusions into standard events
- changing export conventions such as first-row-only bidder type population
- using benchmark materials during generation

## Pipeline Position

The stage sequence does not change:

```text
/extract-deal
  -> skill-pipeline canonicalize
  -> skill-pipeline check
  -> skill-pipeline verify
  -> skill-pipeline coverage
  -> /verify-extraction
  -> skill-pipeline enrich-core
  -> /enrich-deal
  -> /export-csv
```

The change is internal to `skill-pipeline coverage`. It gains a second responsibility:

1. existing source-coverage audit over broad cue families
2. new omission audit over explicit structural event families

Coverage remains read-only. It writes richer findings, not new events.

## Omission Detection Model

Each omission finding should answer:

- what event family appears to be missing
- how strong the filing support is
- which blocks / evidence items support the finding
- which concrete event type should likely exist
- whether the issue should block or warn
- what `/verify-extraction` should try to repair

Two support levels:

- `explicit`: the filing directly states the event
- `suggestive`: the filing strongly implies the event, but the exact event boundary or direction is still ambiguous

Two severities:

- `error`: explicit filing support; the pipeline should stop until repair succeeds or the finding is consciously resolved
- `warning`: suggestive support; the issue should feed review / repair, but not automatically fail the pipeline

### Family 1: Round Events

Catch omissions for:

- `final_round_inf_ann`
- `final_round_inf`
- `final_round_ann`
- `final_round`
- `final_round_ext_ann`
- `final_round_ext`

`error` examples:

- process letters were sent requesting final bids
- bidders were invited to a final round
- a final-bid deadline is stated
- the deadline was extended

`warning` examples:

- dense proposal clustering with language that suggests a narrowed process
- vague references to a later-stage submission without a clean announcement / deadline sentence

### Family 2: Target-Caused Drops

Catch omissions where the filing clearly says the target or its advisers excluded a bidder.

`error` examples:

- bidder was not invited to continue
- company informed the bidder it would not move the bidder to the next round
- advisers cut the field and excluded named parties

`warning` examples:

- bidder disappears after a narrowing step, but the filing does not clearly distinguish target action from bidder withdrawal

Important directionality rule: target-caused drop findings must not fire when the bidder first says it will not improve or will not proceed. In that case, the event belongs in the normal drop family, not the target-caused omission family.

### Family 3: IB Retention

Catch omissions where the filing explicitly states that the company or another party retained / engaged a financial adviser.

`error` examples:

- "retained X as financial adviser"
- "engaged X"
- named banker described as the company's adviser in the context of a clear retention event

`warning` examples:

- adviser appears in process narrative, but retention timing is only loosely implied

This family may require actor-repair as well as event-repair if the adviser actor is absent from the roster.

### Family 4: Go-Shop End

Catch omissions where the filing clearly closes a go-shop contact path for a named party or named set of parties.

`error` examples:

- the go-shop expired without a proposal from a named bidder
- a named party signed an NDA during go-shop but did not submit a bid before the period ended

`warning` examples:

- late go-shop contact / NDA activity without an explicit closing sentence

This family is limited to explicit closing language. It should not infer a drop solely because a go-shop bidder never progressed.

## Data Model Changes

Add omission-specific metadata to `CoverageFinding` and the emitted `coverage_findings.json`. Keep the event schema unchanged.

Recommended new fields:

- `finding_kind`: `"source_coverage"` or `"structural_omission"`
- `omission_family`: optional string for omission findings
- `suggested_event_type`: optional string
- `source_support`: optional `"explicit"` or `"suggestive"`
- `repair_hint`: optional string
- `candidate_actor_ids`: list of actor IDs when identifiable from extraction + source text
- `supporting_block_ids`: explicit support blocks
- `supporting_evidence_ids`: explicit support evidence items

This preserves backwards compatibility for the broad cue audit while giving `/verify-extraction` enough structure to act deterministically.

## Coverage Behavior

`coverage.py` should continue to classify broad cue families as it does today, but it should also run omission-family detectors over chronology blocks and evidence items.

Implementation sketch:

1. build the existing cue-family coverage findings
2. build omission findings from explicit phrase / structure detectors
3. deduplicate omission findings against already-extracted event types
4. write a combined findings artifact
5. summarize counts by omission family and severity in `coverage_summary.json`

The new omission logic should prefer exact phrases and nearby chronology overlap over heuristic clustering. If the supporting filing basis is weak, downgrade to warning or skip.

## Repair Ownership

`/verify-extraction` becomes the sole owner of edits resulting from omission findings.

Expected repair flow:

1. read deterministic verification findings
2. read coverage findings, including omission findings
3. for each repairable omission finding with explicit support:
   - add the missing actor if needed and clearly grounded
   - add the missing event with canonical `evidence_span_ids`
   - preserve normal event schema and chronological order
4. rerun canonical deterministic checks as usual

This keeps a single repair layer responsible for modifications and prevents silent coverage-side mutation.

## Error Handling

| Condition | Behavior |
|---|---|
| Omission family detector sees no qualifying support | skip silently |
| Support is present but actor identity is ambiguous | warning |
| Support is explicit and concrete event type is clear | error |
| Support is explicit but no canonical span can be produced | warning, not synthetic event insertion |
| Existing event already covers the omission | no finding |
| Existing event family is present but subtype / direction is ambiguous | warning |

## Testing

Primary test file additions:

- `tests/test_skill_coverage.py`
- `tests/test_skill_verify.py` only if verify/repair interfaces need compatibility coverage
- `/verify-extraction` skill tests or equivalent repair-path tests if present in the repo

Coverage tests should include:

- explicit `final_round_ann` finding
- explicit `final_round` deadline finding
- extension-round finding
- explicit target-caused exclusion finding
- non-firing case where bidder withdrew first
- explicit adviser-retention finding
- explicit go-shop ending finding
- suggestive-only cases downgraded to warnings
- no finding when the matching event already exists

Repair-path tests should include:

- omission finding drives addition of a span-backed round event
- omission finding drives addition of a target-caused drop
- adviser omission can trigger actor + event repair when explicitly grounded
- repaired artifacts pass check / verify / enrich-core

Deal-level regression tests should use `stec` and `saks` as qualitative reference cases, but success should be measured by filing-grounded omission handling, not by matching Alex's workbook exactly.

## Rollout Plan

Phase 1:

- implement omission-family warnings only
- run on reference deals
- inspect false positives manually

Phase 2:

- promote the clearest explicit omission families to blocking errors
- likely candidates: round announcements, round deadlines, explicit target-caused exclusion, explicit adviser retention

Phase 3:

- expand phrase libraries and actor-resolution support
- only after stable precision is established

## Expected Outcome

This design should improve the pipeline's handling of systematic structural omissions without corrupting the verified layer. The likely result is:

- stronger pre-export detection of important missing structural events
- cleaner, more targeted `/verify-extraction` repair inputs
- better downstream round and dropout interpretation because repaired events remain filing-grounded
- improved post-export reconciliation as a consequence, not as the primary objective

The key tradeoff is deliberate conservatism: some benchmark rows will remain unmatched if they cannot be grounded cleanly in the filing. That is acceptable. The pipeline should prefer trustworthy omission detection over artificially maximizing benchmark match rate.
