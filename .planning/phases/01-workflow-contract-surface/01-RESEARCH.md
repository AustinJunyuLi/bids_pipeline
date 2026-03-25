# Phase 1: Workflow Contract Surface - Research

**Researched:** 2026-03-25
**Domain:** Brownfield hybrid SEC-filing workflow contract
**Confidence:** MEDIUM

<user_constraints>
## User Constraints

No `01-CONTEXT.md` exists for this phase.

### Locked Decisions

None recorded in a phase-specific context file.

### Claude's Discretion

Research scope is constrained by the repo-wide contract already recorded in `CLAUDE.md`, `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, and `.planning/ROADMAP.md`:
- Treat the current `skill_pipeline` hybrid workflow as the brownfield baseline.
- Focus on making the active workflow, artifact paths, and project memory explicit.
- Give special weight to the deterministic vs. skill-driven split, handoff boundaries, and contributor discovery surfaces.

### Deferred Ideas (OUT OF SCOPE)

None recorded in a phase-specific context file.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WFLO-01 | Contributor can identify the entrypoint, required inputs, outputs, and fail-fast prerequisites for every active stage from `raw-fetch` through `/export-csv`. | This research maps the live stage graph, classifies each stage as deterministic/skill/hybrid, identifies authoritative sources for each contract, and calls out the current drifts that make the workflow hard to infer today. |
| RISK-02 | Contributor can recover project context and next steps from committed planning docs without relying on private local notes. | This research identifies the current shared-memory spine (`CLAUDE.md`, `.planning/*`, `docs/design.md`, tests), distinguishes authoritative vs. historical surfaces, and recommends what later planning should make explicit so phase work is resumable. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- `CLAUDE.md` is the authoritative repository instruction file.
- `skill_pipeline/` is the only active Python package and `skill-pipeline` is the only installed CLI; historical references to `pipeline/` are not current implementation guidance.
- `.planning/` is the tracked planning surface, but it does not replace `CLAUDE.md` as the repo contract.
- The active runtime is a hybrid workflow: deterministic CLI stages around skill-driven LLM stages.
- `skill-pipeline raw-fetch` and `skill-pipeline preprocess-source` are seed-only and single-primary-document in this worktree.
- `skill-pipeline deal-agent --deal <slug>` is preflight/summary only; it is not the end-to-end runner.
- `skill-pipeline canonicalize`, `check`, `verify`, `coverage`, and `enrich-core` are fail-fast deterministic gates; do not add fallback behavior.
- `data/skill/<slug>/extract/spans.json` is required once extract artifacts are canonicalized; missing sidecars are errors.
- `enrich-core` must not write success artifacts unless `check`, `verify`, and `coverage` all pass.
- Filing `.txt` files under `raw/` are immutable truth sources and must not be rewritten.
- Filing text is the only factual source for generation; benchmark materials are forbidden until `/export-csv` completes.
- `/reconcile-alex` is post-export diagnostic only and must not rewrite generation artifacts or become a prerequisite.
- `.claude/skills/` is the canonical skill tree; `.codex/skills/` and `.cursor/skills/` are derived mirrors synced by `python scripts/sync_skill_mirrors.py`.
- `.gitattributes` is the source of truth for tracked line endings; tracked text files stay `LF` across Windows and Linux.
- Target Python is 3.11+; use type hints on public functions and follow Pydantic-first schema patterns.
- Add targeted pytest regressions for stage-contract bugs and repo policy boundaries.

## Summary

The current workflow is a deterministic/skill sandwich, not a monolithic CLI and not a pure agent flow. The live stage sequence is: `raw-fetch` -> `preprocess-source` -> `/extract-deal` -> `canonicalize` -> `check` -> `verify` -> `coverage` -> `/verify-extraction` -> `enrich-core` -> `/enrich-deal` -> `/export-csv`, with `/reconcile-alex` as optional post-export QA. The deterministic stages own artifact validity and fail-fast gating; the skill stages own extraction, repair, interpretation, export formatting, and benchmark comparison.

Planning Phase 1 well means treating workflow discovery itself as a brownfield problem. The contract exists, but it is split across `CLAUDE.md`, `docs/design.md`, `skill_pipeline/{cli,paths,models,extract_artifacts}.py`, `.claude/skills/*/SKILL.md`, and focused stage tests. Contributors can infer the workflow today, but only by cross-reading code, skills, and tests. There is no single current document that names every stage owner, every handoff artifact, every fail-fast prerequisite, and every authoritative source.

The main brownfield drifts are real and should be surfaced explicitly in planning, not silently “fixed” by assumption. The repo currently contains legacy `data/deals/<slug>/{extract,qa}` artifacts and no committed `data/skill/` tree, even though the active contract points new skill and deterministic handoffs to `data/skill/<slug>/...`. Also, current `preprocess-source` deletes stale `supplementary_snippets.jsonl` and does not regenerate it, while `extract-deal` and `enrich-deal` still claim to read it. These are documentation-and-contract clarity problems first.

**Primary recommendation:** Plan Phase 1 as a contract-publication phase: consolidate stage owner, entrypoint, required reads/writes, fail-fast conditions, and authoritative source per stage, while explicitly labeling legacy paths and historical docs as non-authoritative.

## Current Authority Map

| Surface | What it tells contributors | Reliability | Planning use |
|---------|----------------------------|-------------|--------------|
| `CLAUDE.md` | Authoritative runtime shape, stage order, invariants, benchmark boundary, skill-tree ownership | HIGH | Primary repo contract |
| `docs/design.md` | Short current workflow index and artifact flow | HIGH | Best concise workflow summary |
| `skill_pipeline/cli.py` | Deterministic CLI entrypoints and dispatch | HIGH | Source of deterministic stage inventory |
| `skill_pipeline/paths.py` | Canonical deal artifact roots and filenames | HIGH | Source of path contract |
| `skill_pipeline/models.py` and `skill_pipeline/extract_artifacts.py` | Raw vs canonical artifact schemas and loader behavior | HIGH | Source of handoff/schema expectations |
| `skill_pipeline/*stage*.py`, `canonicalize.py`, `check.py`, `verify.py`, `coverage.py`, `enrich_core.py` | Fail-fast prerequisites and deterministic output behavior | HIGH | Source of gate conditions |
| `.claude/skills/*/SKILL.md` | Skill-stage reads, writes, procedure, and benchmark boundary | HIGH for intent, MEDIUM where drift exists | Source of LLM-stage contracts |
| `tests/test_skill_*.py`, `tests/test_benchmark_separation_policy.py`, `tests/test_skill_mirror_sync.py` | Which contracts are actually enforced today | HIGH | Source of verified behavior |
| `.planning/{PROJECT,REQUIREMENTS,ROADMAP,STATE}.md` | Shared project memory and phase intent | HIGH | Source of RISK-02 planning context |
| `.planning/codebase/*.md` | Useful brownfield synthesis of repo structure | MEDIUM | Helpful summary, not primary authority |
| `docs/plans/*` and `quality_reports/session_logs/*` | Historical design and transition context | LOW for current runtime | Use only as history, not as live contract |

## Standard Stack

### Core

| Library / Surface | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `skill-pipeline` console entrypoint | `0.1.0` | Deterministic runtime for `raw-fetch`, `preprocess-source`, `canonicalize`, `check`, `verify`, `coverage`, `enrich-core`, and summary-only `deal-agent` | It is the only installed CLI in this repo and the only deterministic stage surface contributors can invoke directly. |
| Python | `3.13.5` installed, repo requires `>=3.11` | Runtime for the package, scripts, and tests | All tracked code is Python; phase planning should assume Python-first implementation and verification. |
| Pydantic | `2.12.5` installed, declared `>=2.0` | Artifact schema validation at stage boundaries | Every deterministic stage reads/writes through validated models or schema-aware loaders. |
| `pytest` | `8.3.4` installed, declared `>=8.0` | Stage and policy regression surface | Existing contract verification is pytest-based and already covers the major deterministic boundaries. |
| `edgartools` | `5.23.3` installed, declared `>=5.23` | Live SEC filing access for `raw-fetch` | `raw-fetch` depends on it directly and the environment currently emits v6 deprecation warnings. |

### Supporting

| Library / Surface | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `.claude/skills/` canonical tree | 6 active skills | Defines `/deal-agent`, `/extract-deal`, `/verify-extraction`, `/enrich-deal`, `/export-csv`, `/reconcile-alex` | Use whenever planning or documenting skill-driven stages. |
| `scripts/sync_skill_mirrors.py` | current repo script | Keeps `.codex/skills/` and `.cursor/skills/` aligned with `.claude/skills/` | Use after any skill doc change; do not hand-edit mirrors. |
| `.planning/*` | initialized `2026-03-25` | Shared project memory for roadmap, requirements, state, and project context | Use for RISK-02 continuity and later phase planning. |
| `docs/design.md` | current repo doc | Minimal current workflow index | Use as the concise doc-level workflow reference. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `CLAUDE.md` + `docs/design.md` + code/tests as the current workflow authority | Historical `docs/plans/*` or `quality_reports/session_logs/*` | Historical docs are useful context but are not safe as the live contract because several paths and responsibilities changed. |
| `data/skill/<slug>/...` as the active extract/QA/enrich/export root | `data/deals/<slug>/{extract,qa}` | The checked-in dataset still contains the legacy `data/deals` outputs, but current code and skill docs target `data/skill`; planning must document the split rather than blur it. |
| `/deal-agent` for orchestration and `skill-pipeline deal-agent` for summary only | Treat both `deal-agent` names as equivalent | This creates onboarding bugs because the skill orchestrator and CLI summary command have different responsibilities. |

**Installation:**
```bash
pip install -e .
```

**Version verification:**
```bash
skill-pipeline --version
python3 --version
pytest --version
python3 - <<'PY'
import importlib.metadata as m
for pkg in ["pydantic", "edgartools", "openpyxl"]:
    print(f"{pkg}=={m.version(pkg)}")
PY
```

**Observed in this environment on 2026-03-25:** `skill-pipeline 0.1.0`, `Python 3.13.5`, `pytest 8.3.4`, `pydantic 2.12.5`, `edgartools 5.23.3`, `openpyxl 3.1.5`.

## Architecture Patterns

### Recommended Project Structure

```text
CLAUDE.md                         # authoritative repo contract
.planning/{PROJECT,REQUIREMENTS,ROADMAP,STATE}.md
docs/design.md                    # concise current workflow index
skill_pipeline/
├── cli.py                        # deterministic entrypoints
├── paths.py                      # artifact root contract
├── models.py                     # raw/canonical/gate schemas
├── extract_artifacts.py          # legacy vs canonical loader boundary
├── raw/                          # seed-only ingress
├── preprocess/                   # chronology/evidence materialization
├── canonicalize.py               # raw -> canonical upgrade
├── check.py                      # structural gate
├── verify.py                     # strict quote/reference gate
├── coverage.py                   # source-cue audit gate
└── enrich_core.py                # deterministic enrichment
.claude/skills/                   # canonical skill-stage contracts
tests/                            # contract and policy verification
```

### Pattern 1: Deterministic Gate Sandwich
**What:** The workflow uses deterministic stages before and after LLM/skill stages. Extraction and interpretation are skill-driven, but artifact validity is enforced by deterministic Python.
**When to use:** Any Phase 1 contract inventory should present the workflow in this shape rather than as a single CLI or a pure skill chain.
**Example:**
```text
raw-fetch -> preprocess-source -> /extract-deal
-> canonicalize -> check -> verify -> coverage
-> /verify-extraction -> enrich-core -> /enrich-deal -> /export-csv
```
Source: `CLAUDE.md`, `docs/design.md`

### Pattern 2: PathSet-Backed Artifact Contract
**What:** Deterministic stages do not hand-roll artifact paths; they derive them from one deal-scoped path object.
**When to use:** Any new documentation, tests, or contract checks should anchor to `SkillPathSet` and `build_skill_paths()` rather than restating paths ad hoc.
**Example:**
```python
from skill_pipeline.paths import build_skill_paths

paths = build_skill_paths("imprivata")
print(paths.chronology_blocks_path)
print(paths.actors_raw_path)
print(paths.deterministic_enrichment_path)
```
Source: `skill_pipeline/paths.py`

### Pattern 3: Canonicalize-In-Place Boundary
**What:** `/extract-deal` writes legacy raw artifacts with `evidence_refs`; `canonicalize` overwrites those files into canonical span-backed artifacts and adds `spans.json`.
**When to use:** Any stage after extraction must state whether it accepts legacy artifacts, canonical artifacts, or both. The loader already supports both modes.
**Example:**
```python
from skill_pipeline.extract_artifacts import load_extract_artifacts

artifacts = load_extract_artifacts(paths)
if artifacts.mode == "canonical":
    spans = artifacts.span_index
else:
    # legacy artifacts still use evidence_refs
    ...
```
Source: `skill_pipeline/extract_artifacts.py`

### Pattern 4: Summary Surface vs Orchestrator Surface
**What:** The repo has two similarly named `deal-agent` surfaces with different jobs.
**When to use:** Phase 1 docs should name both explicitly.
**Example:**
```text
skill-pipeline deal-agent --deal <slug>   # preflight/status summary only
/deal-agent <slug>                        # skill orchestrator for extract->verify->enrich->export
```
Source: `skill_pipeline/deal_agent.py`, `.claude/skills/deal-agent/SKILL.md`

### Anti-Patterns to Avoid
- **Treating `skill-pipeline deal-agent` as the end-to-end runner:** the CLI command summarizes and verifies prerequisites; it does not execute the skill chain.
- **Using `data/deals/<slug>/{extract,qa}` as the active contract surface:** those artifacts exist in the repo but are legacy relative to the current `data/skill/<slug>/...` contract.
- **Inferring the live workflow from `docs/plans/*` or `quality_reports/session_logs/*`:** those files preserve history, not the current runtime surface.
- **Assuming `supplementary_snippets.jsonl` exists because skill docs mention it:** the current preprocess code removes stale copies and does not regenerate the file.
- **Hand-editing `.codex/skills` or `.cursor/skills`:** `.claude/skills` is canonical and the mirrors are generated.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Deal-specific artifact paths | Ad hoc `Path("data") / ...` strings in every doc/test | `build_skill_paths()` and `SkillPathSet` | The repo already has one path contract; duplicating it is how doc drift starts. |
| Legacy/canonical mode detection | Custom heuristics in each stage or doc | `load_extract_artifacts()` | The loader already centralizes the `evidence_refs` vs `evidence_span_ids` boundary and enforces `spans.json`. |
| Skill mirror management | Manual edits to `.codex/skills` and `.cursor/skills` | `python3 scripts/sync_skill_mirrors.py` | Mirrors are derived, and a tested sync/check flow already exists. |
| Benchmark-boundary enforcement | Informal reminders only | Existing policy language plus `tests/test_benchmark_separation_policy.py` | Benchmark contamination is already a tested repo policy; keep using that mechanism. |
| New orchestration logic in Phase 1 | A new end-to-end runner | Explicit documentation of the existing split | Phase 1 is about surfacing the current brownfield contract, not redesigning runtime orchestration. |

**Key insight:** For this phase, the risk is not missing primitives. The repo already contains the primitives for stage inventory, path mapping, fail-fast gates, and policy enforcement. The planning problem is to expose them coherently and to label the historical surfaces that currently compete with them.

## Common Pitfalls

### Pitfall 1: `deal-agent` Means Two Different Things
**What goes wrong:** Contributors assume `skill-pipeline deal-agent` runs extraction through export.
**Why it happens:** The skill orchestrator and CLI summary command share the same name.
**How to avoid:** Always document both surfaces together and describe the CLI one as summary/preflight only.
**Warning signs:** Contributors talk about “running deal-agent” without specifying whether they mean the CLI or the skill.

### Pitfall 2: Active Artifact Root vs Checked-In Dataset Root
**What goes wrong:** Contributors infer that `data/deals/<slug>/extract` and `qa` are still the active handoff roots because those directories are committed for every deal.
**Why it happens:** The repo contains historical pipeline outputs, but current code and skills target `data/skill/<slug>/...`.
**How to avoid:** Explicitly mark `data/deals/<slug>/{extract,qa}` as legacy/historical in Phase 1 workflow docs unless or until the runtime is changed back.
**Warning signs:** A proposed plan references `data/deals/<slug>/extract` for current extraction output.

### Pitfall 3: `supplementary_snippets.jsonl` Contract Drift
**What goes wrong:** Skill docs say they read `supplementary_snippets.jsonl`, but current preprocess removes stale copies and does not write new ones.
**Why it happens:** The file survived from the historical all-filings design, while the current seed-only preprocess implementation no longer materializes it.
**How to avoid:** Treat this as an explicit open contract question in Phase 1 and do not assume the file is part of the live source bundle.
**Warning signs:** New docs or skills refer to cross-filing hints without pointing to the code path that generates them.

### Pitfall 4: Canonical Sidecar Requirement Is Easy to Miss
**What goes wrong:** Downstream logic or docs assume canonical actors/events are self-contained and forget `spans.json`.
**Why it happens:** `canonicalize` rewrites the main extract files in place, so the sidecar requirement is easy to overlook.
**How to avoid:** Every post-canonicalize contract should name `spans.json` explicitly.
**Warning signs:** A stage or doc mentions canonical `evidence_span_ids` but not the span registry.

### Pitfall 5: Historical Docs Still Look Plausible
**What goes wrong:** Contributors plan against `docs/plans/2026-03-16-pipeline-design-v3.md` or `quality_reports/session_logs/2026-03-18_skill-pipeline-design.md` and import stale assumptions like all-filings preprocess or “Alex-compatible” framing.
**Why it happens:** Those docs are detailed and checked in, but they describe earlier transition states.
**How to avoid:** Phase 1 should publish an authority map and explicitly label those docs as historical background only.
**Warning signs:** Plans mention `pipeline/` modules, `data/deals/<slug>/qa`, or benchmark-oriented export language.

### Pitfall 6: Benchmark Separation Is a Workflow Boundary, Not Just a Style Note
**What goes wrong:** Contributors treat `example/`, `diagnosis/`, or `/reconcile-alex` as optional helpful context before export.
**Why it happens:** Benchmark materials live in the repo and are easy to consult casually.
**How to avoid:** Keep the pre-/post-export boundary explicit in workflow docs and keep the policy tests green.
**Warning signs:** A generation-stage doc references benchmark files or “Alex-compatible” guidance.

## Code Examples

Verified patterns from local primary sources:

### Derive a Deal's Contract Surface from One Place
```python
from skill_pipeline.paths import build_skill_paths

paths = build_skill_paths("imprivata")
required = [
    paths.chronology_blocks_path,
    paths.evidence_items_path,
    paths.document_registry_path,
]
```
Source: `skill_pipeline/paths.py`

### Fail Closed Before Deterministic Enrichment
```python
from skill_pipeline.models import CoverageSummary, SkillCheckReport, SkillVerificationLog

check_report = SkillCheckReport.model_validate(_read_json(paths.check_report_path))
verify_log = SkillVerificationLog.model_validate(_read_json(paths.verification_log_path))
coverage_summary = CoverageSummary.model_validate(_read_json(paths.coverage_summary_path))

if check_report.summary.status != "pass":
    raise ValueError(...)
if verify_log.summary.status != "pass":
    raise ValueError(...)
if coverage_summary.status != "pass":
    raise ValueError(...)
```
Source: `skill_pipeline/enrich_core.py`

### Verification Writes a Compatible Gate Log for the Skill Repair Loop
```python
findings, total_checks = _collect_verification_findings(paths)
paths.verification_findings_path.write_text(...)
paths.verification_log_path.write_text(
    _build_compatible_log(findings, total_checks=total_checks).model_dump_json(indent=2),
    encoding="utf-8",
)
```
Source: `skill_pipeline/verify.py`

### Current Preprocess Invalidates Partial Outputs on Failure
```python
try:
    ...
    _atomic_write_json(source_dir / "chronology_selection.json", ...)
    _atomic_write_jsonl(source_dir / "chronology_blocks.jsonl", ...)
    _atomic_write_jsonl(source_dir / "evidence_items.jsonl", ...)
except Exception:
    _invalidate_source_artifacts(source_dir)
    raise
```
Source: `skill_pipeline/preprocess/source.py`

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Historical `pipeline/` / all-filings design in `docs/plans/2026-03-16-pipeline-design-v3.md` | Seed-only `skill_pipeline` hybrid workflow documented in `CLAUDE.md` and `docs/design.md` | Current docs updated by `2026-03-25` | Phase 1 should plan against the live `skill_pipeline` contract, not the v3 rewrite plan. |
| `data/deals/<slug>/{extract,qa}` as extraction/QA outputs | `data/skill/<slug>/...` as the active current contract for extract/check/verify/coverage/enrich/export | Transition documented by `2026-03-18` session log and `2026-03-25` repo docs | The checked-in dataset still contains legacy outputs, so docs must distinguish runtime contract from historical artifacts. |
| `supplementary_snippets.jsonl` as part of the source bundle | Current preprocess code deletes stale snippet files and does not regenerate them | Current code as of `2026-03-25` | Phase 1 should make this drift explicit and either document the omission or queue a later contract fix. |
| “Alex-compatible” export framing | Repo review CSV with benchmark comparison fenced to post-export `/reconcile-alex` | Benchmark-boundary docs/tests tightened by `2026-03-25` | Workflow docs should describe `/export-csv` as the filing-grounded export contract, not benchmark matching. |

**Deprecated/outdated:**
- `docs/plans/2026-03-16-pipeline-design-v3.md` as a live runtime contract.
- `quality_reports/session_logs/2026-03-18_skill-pipeline-design.md` as the current authority for path and export semantics.
- Any workflow note that implies `.codex/skills` or `.cursor/skills` are authoring surfaces.

## Open Questions

1. **Should Phase 1 explicitly label the committed `data/deals/<slug>/{extract,qa}` artifacts as legacy?**
   - What we know: current code and current skills target `data/skill/<slug>/...`, while the checked-in dataset still holds `data/deals/<slug>/{extract,qa}` outputs for every active deal.
   - What's unclear: whether those legacy artifacts are intentionally preserved as brownfield reference data or simply stale from the transition.
   - Recommendation: document them as historical/non-authoritative unless a later phase intentionally revives that layout.

2. **Is `supplementary_snippets.jsonl` still part of the live source contract?**
   - What we know: `extract-deal` and `enrich-deal` still list it in their Reads tables, but `preprocess_source_deal()` deletes stale copies and never rewrites it.
   - What's unclear: whether the omission is deliberate seed-only simplification or an unfinished contract migration.
   - Recommendation: treat this as a named Phase 1 drift item and avoid presenting the file as guaranteed output until the contract is reconciled.

3. **What should contributors use as the single top-level workflow entrypoint?**
   - What we know: `/deal-agent` is the skill orchestrator; `skill-pipeline deal-agent` is summary/preflight only.
   - What's unclear: whether Phase 1 should recommend one of them as the “start here” entrypoint or document both as parallel surfaces.
   - Recommendation: make the distinction explicit and choose one documented “operator start” surface for new contributors, without changing runtime behavior in this phase.

4. **How much of RISK-02 should live in `CLAUDE.md` vs `.planning/*` vs `docs/design.md`?**
   - What we know: `CLAUDE.md` is authoritative, `.planning/*` is new project memory, and `docs/design.md` is the shortest current workflow summary.
   - What's unclear: which document should own the stage contract table, authority map, and brownfield drift register.
   - Recommendation: keep repo-wide invariants in `CLAUDE.md`, put concise workflow index material in `docs/design.md`, and store roadmap/phase continuity in `.planning/*`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All deterministic stages, tests, sync script | ✓ | `3.13.5` | — |
| `skill-pipeline` console entrypoint | Deterministic CLI execution | ✓ | `0.1.0` | `python3 -m skill_pipeline.cli` |
| `pytest` | Validation and regression commands | ✓ | `8.3.4` | — |
| `edgartools` | Live `raw-fetch` | ✓ | `5.23.3` | None for live fetch |
| LLM provider credentials (`ANTHROPIC_API_KEY` / `OPENAI_API_KEY`) | Skill-driven stages | Not checked in research run | — | Use whichever documented provider is configured locally |

**Missing dependencies with no fallback:**
- None observed for Phase 1 documentation/planning work.

**Missing dependencies with fallback:**
- LLM credentials were not probed during research; the repo supports either Anthropic or OpenAI provider configuration for skill-driven stages.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest 8.3.4` |
| Config file | `pytest.ini` |
| Quick run command | `pytest -q tests/test_skill_pipeline.py tests/test_benchmark_separation_policy.py tests/test_skill_mirror_sync.py` |
| Full suite command | `pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WFLO-01 | Stage inventory, artifact roots, and boundary rules stay aligned with the live contract | policy + integration + manual doc audit | `pytest -q tests/test_skill_pipeline.py tests/test_skill_raw_stage.py tests/test_skill_preprocess_source.py tests/test_skill_canonicalize.py tests/test_skill_check.py tests/test_skill_verify.py tests/test_skill_coverage.py tests/test_skill_enrich_core.py tests/test_benchmark_separation_policy.py tests/test_skill_mirror_sync.py` | ✅ partial |
| RISK-02 | Committed planning/docs are sufficient to recover project context and next steps | manual-only today | `pytest -q tests/test_benchmark_separation_policy.py tests/test_skill_mirror_sync.py` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest -q tests/test_skill_pipeline.py tests/test_benchmark_separation_policy.py tests/test_skill_mirror_sync.py`
- **Per wave merge:** `pytest -q tests/test_skill_raw_stage.py tests/test_skill_preprocess_source.py tests/test_skill_canonicalize.py tests/test_skill_check.py tests/test_skill_verify.py tests/test_skill_coverage.py tests/test_skill_enrich_core.py tests/test_skill_pipeline.py tests/test_benchmark_separation_policy.py tests/test_skill_mirror_sync.py`
- **Phase gate:** `pytest -q` plus manual review that the published workflow contract still matches the authority map above

### Wave 0 Gaps
- [ ] Add an automated doc-contract test that asserts the current stage list, stage owner, and artifact roots agree across `CLAUDE.md`, `docs/design.md`, and the skill READMEs.
- [ ] Add an automated check for `supplementary_snippets.jsonl` drift so current docs cannot claim it is required unless preprocess actually writes it.
- [ ] Add an automated continuity check for `.planning/{PROJECT,REQUIREMENTS,ROADMAP,STATE}.md` so RISK-02 is not purely manual.
- [ ] Add a brownfield path-policy check that explicitly marks `data/deals/<slug>/{extract,qa}` as legacy if that remains the intended contract.

## Sources

### Primary (HIGH confidence)
- Local repo: `CLAUDE.md` - authoritative repo contract, workflow order, invariants, benchmark boundary
- Local repo: `docs/design.md` - concise current workflow index and artifact flow
- Local repo: `skill_pipeline/cli.py` - deterministic entrypoints
- Local repo: `skill_pipeline/paths.py` - artifact roots and filenames
- Local repo: `skill_pipeline/models.py` and `skill_pipeline/extract_artifacts.py` - schema and raw/canonical boundary
- Local repo: `skill_pipeline/raw/stage.py`, `skill_pipeline/preprocess/source.py`, `skill_pipeline/canonicalize.py`, `skill_pipeline/check.py`, `skill_pipeline/verify.py`, `skill_pipeline/coverage.py`, `skill_pipeline/enrich_core.py` - fail-fast stage behavior
- Local repo: `.claude/skills/README.md` and `.claude/skills/*/SKILL.md` - skill-stage contracts
- Local repo: `tests/test_skill_pipeline.py`, `tests/test_skill_raw_stage.py`, `tests/test_skill_preprocess_source.py`, `tests/test_skill_canonicalize.py`, `tests/test_skill_check.py`, `tests/test_skill_verify.py`, `tests/test_skill_coverage.py`, `tests/test_skill_enrich_core.py`, `tests/test_benchmark_separation_policy.py`, `tests/test_skill_mirror_sync.py` - enforced behavior and policy boundaries
- Local commands run during research: `skill-pipeline --version`, `python3 scripts/sync_skill_mirrors.py --check`, and focused pytest commands

### Secondary (MEDIUM confidence)
- Local repo: `.planning/codebase/{ARCHITECTURE,STACK,STRUCTURE,TESTING,CONCERNS,CONVENTIONS,INTEGRATIONS}.md` - useful synthesis of the current brownfield repo, but derivative from primary sources
- Local repo: `quality_reports/session_logs/2026-03-18_skill-pipeline-design.md` - transition history that explains current brownfield artifacts and naming drift

### Tertiary (LOW confidence)
- Local repo: `docs/plans/2026-03-16-pipeline-design-v3.md` - valuable historical context, but intentionally not authoritative for the current runtime surface

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - verified from local environment, `pyproject.toml`, and the installed console entrypoint
- Architecture: MEDIUM - the deterministic/skill split is clear in code and docs, but current docs and checked-in artifacts still contain brownfield drift
- Pitfalls: HIGH - each pitfall is directly supported by current code, skill docs, checked-in artifacts, or tests

**Research date:** 2026-03-25
**Valid until:** 2026-04-08
