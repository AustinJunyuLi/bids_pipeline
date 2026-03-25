# Requirements: Bids Data Pipeline

**Defined:** 2026-03-25
**Core Value:** Produce filing-grounded deal data that remains auditable back to SEC source text and reproducible across machines.

## v1 Requirements

### Workflow Contracts

- [x] **WFLO-01**: Contributor can identify the entrypoint, required inputs, outputs, and fail-fast prerequisites for every active stage from `raw-fetch` through `/export-csv`.
- [ ] **WFLO-02**: Contributor can run each deterministic CLI stage against documented artifact paths without manual file surgery.
- [x] **WFLO-03**: Skill-driven stages write artifacts that deterministic stages can consume without manual schema edits or ad hoc file renaming.

### Quality and Verification

- [x] **QUAL-01**: Contributor can run targeted regression tests for raw, preprocess, canonicalize, verify, coverage, enrich-core, and repo policy boundaries from committed commands.
- [ ] **QUAL-02**: Contributor can detect benchmark-boundary drift and skill-mirror drift with automated checks before merging.
- [ ] **QUAL-03**: Contributor can trace workflow failures to the stage and artifact that violated the contract rather than debug from scratch.

### Operations

- [ ] **OPS-01**: Contributor can switch between Windows and Linux clones without tracked line-ending churn in committed text files.
- [ ] **OPS-02**: Contributor can keep local-only state out of `git status` by default.

### Risk Management

- [ ] **RISK-01**: Contributor can identify external dependency risks that could break live SEC fetches before they interrupt active deal work.
- [x] **RISK-02**: Contributor can recover project context and next steps from committed planning docs without relying on private local notes.

## v2 Requirements

### Workflow Expansion

- **WFLO-04**: Operator can run the entire hybrid workflow from one tracked orchestration command.
- **MULTI-01**: Operator can process a bounded, human-approved multi-filing allowlist per deal without reopening broad discovery.

### Post-Export QA

- **BENCH-01**: Contributor can run post-export benchmark reconciliation as automated QA without turning it into a generation prerequisite.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Open-ended EDGAR discovery beyond the approved filing seed | Conflicts with the seed-only source boundary |
| Pre-export benchmark matching | Violates the filing-grounded generation contract |
| Manual editing of `.codex/skills` or `.cursor/skills` | Those trees are derived mirrors from `.claude/skills` |
| Hosted web service or multi-user UI | The current project is a local research pipeline |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| WFLO-01 | Phase 1 | Complete |
| RISK-02 | Phase 1 | Complete |
| WFLO-02 | Phase 2 | Pending |
| WFLO-03 | Phase 2 | Complete |
| QUAL-03 | Phase 2 | Pending |
| QUAL-01 | Phase 3 | Complete |
| QUAL-02 | Phase 3 | Pending |
| OPS-01 | Phase 4 | Pending |
| OPS-02 | Phase 4 | Pending |
| RISK-01 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0

---
*Requirements defined: 2026-03-25*
*Last updated: 2026-03-25 after initial definition*
