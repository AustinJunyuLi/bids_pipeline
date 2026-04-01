# Phase 24: V1 Retirement + Git-History Preservation - Context

**Gathered:** 2026-04-01
**Status:** Ready for planning
**Mode:** Auto-generated from the user-directed retirement follow-on and current repo state

<domain>
## Phase Boundary

Retire the legacy v1 runtime from the working tree without weakening the live
v2 pipeline or the post-`db-export-v2` benchmark boundary.

This phase covers:

1. removing v1-only CLI commands, skill docs, mirrored skill trees, tests,
   scripts, prompt assets, and archived `data/legacy/v1/` artifacts from the
   working tree
2. extracting any live v2 dependencies that still point into legacy-labeled
   modules into neutral shared modules
3. documenting recoverability through GitHub-visible history, milestone
   archives, and an explicit Git tag

This phase does not reopen v2.2 derive/export semantics, benchmark usage, or
the live extraction contract beyond the changes required to remove v1.

</domain>

<decisions>
## Implementation Decisions

### Retirement Scope
- **D-01:** Treat v1 retirement as working-tree removal, not mere de-emphasis.
  Legacy commands, skills, data archives, migration shims, and v1-only tests
  should leave the tree once recovery is pinned elsewhere.
- **D-02:** Keep the live branch usable throughout; shared logic needed by v2
  should move into neutral modules instead of leaving hidden imports from
  legacy files.

### Recovery Path
- **D-03:** Use an explicit Git tag on the already-pushed pre-retirement commit
  (`82a4966`) so recovery is visible on GitHub without depending on local
  reflog state.
- **D-04:** Repo docs should point recovery to Git history and archived
  milestone documents rather than preserving legacy artifacts in the working
  tree.

### Safety Constraints
- **D-05:** Do not weaken the benchmark boundary while touching skills or docs.
- **D-06:** Do not revert or rewrite unrelated in-progress v2.2 work already
  present in the dirty tree.

### the agent's Discretion
- Exact neutral module names and how much legacy-internal schema code is moved,
  provided the live v2 path no longer imports legacy runtime modules.
- Whether some dead internal helpers are deleted immediately or left for a
  later cleanup, provided they are no longer part of the live repo surface.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` — Phase 24 goal and success criteria
- `.planning/REQUIREMENTS.md` — RETIRE-01 through RETIRE-04
- `.planning/STATE.md` — current milestone state and blocker framing
- `CLAUDE.md` — authoritative repo instructions and benchmark boundary
- `skill_pipeline/cli.py`
- `skill_pipeline/models.py`
- `skill_pipeline/extract_artifacts_v2.py`
- `skill_pipeline/coverage_v2.py`
- `skill_pipeline/db_export_v2.py`
- `skill_pipeline/paths.py`
- `tests/test_skill_mirror_sync.py`
- `tests/test_runtime_contract_docs.py`
- `tests/test_benchmark_separation_policy.py`
- commit `82a4966` — pre-retirement cleanup anchor to tag for recovery

</canonical_refs>

<specifics>
## Specific Ideas

- `models.py`, `coverage.py`, and `db_export.py` currently leak shared types or
  constants into the live v2 path; that shared logic should move first.
- Skill mirror sync tests should flip from asserting live/legacy coexistence to
  asserting that only the live v2 skills remain mirrored.
- `data/legacy/v1/` should disappear from the tree only after the recovery tag
  name is recorded in docs and verification.

</specifics>

<deferred>
## Deferred Ideas

- deeper dead-code pruning of old helper functions that become unreachable but
  are not part of the live repo surface
- any future milestone dedicated to package-level renaming beyond the concrete
  retirement work required here

</deferred>
