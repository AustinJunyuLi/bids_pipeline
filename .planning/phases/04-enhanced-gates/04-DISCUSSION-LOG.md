# Phase 4: Enhanced Gates - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-28
**Phase:** 04-enhanced-gates
**Areas discussed:** Gate architecture, Finding severity policy, Cross-event domain rules, Attention decay output

---

## Gate Architecture

| Option | Description | Selected |
|--------|-------------|----------|
| New dedicated stage | A new file that runs after check+verify+coverage. Clean separation. Adds new CLI command. | ✓ |
| Extend check.py | Add 4 new check functions into check.py. Keeps one place but mixes structural and semantic. | |
| Split by type | Distribute across check/verify/coverage by affinity. Scatters related logic. | |

**User's choice:** New dedicated stage
**Notes:** Recommended approach selected. Pipeline ordering: check -> verify -> coverage -> gates -> enrich-core.

---

## Finding Severity Policy

| Option | Description | Selected |
|--------|-------------|----------|
| Tiered severity | Each rule has pre-assigned severity. High-confidence = blocker, lower-confidence = warning. | ✓ |
| All warnings | Never block pipeline. Report-only. | |
| All blockers | Any violation stops pipeline. | |

**User's choice:** Tiered severity
**Notes:** Per-rule severity, not per-gate. A single gate can produce both blockers and warnings.

---

## Cross-Event Domain Rules

| Option | Description | Selected |
|--------|-------------|----------|
| Core invariants only (5-7 rules) | High-confidence rules almost never wrong. Add more based on real data. | ✓ |
| Comprehensive rule set (15-20) | All known invariants upfront. Higher false-positive risk. | |
| Minimal starter set (2-3) | Just obvious rules. Get framework working first. | |

**User's choice:** Core invariants only
**Notes:** Initial 5-7 rules. Expand based on false-positive data from 9-deal corpus runs.

---

## Attention Decay Output

| Option | Description | Selected |
|--------|-------------|----------|
| Report only | Diagnostic report with quartile counts, hot spots, decay score. No auto action. | ✓ |
| Report + re-extraction trigger | Auto-flag for re-extraction if decay exceeds threshold. | |
| Embedded in verify | Add position metadata to verify findings. Simpler but less visible. | |

**User's choice:** Report only
**Notes:** Consumes verify findings and spans. Produces position-clustered diagnostic. No automatic action.

## Claude's Discretion

- Module naming and internal organization
- Exact attention decay thresholds
- Small-deal handling for statistical clustering
- Pydantic model names for report

## Deferred Ideas

- Comprehensive 15-20 rule set — add based on real false-positive data
- Automatic re-extraction from attention decay — future phase
- Rule suppression mechanism — wait for observed edge cases
