# Codebase Concerns

**Analysis Date:** 2026-03-25

## Tech Debt

**Hybrid workflow split across code and skill docs:**
- Files: `skill_pipeline/cli.py`, `CLAUDE.md`, `.claude/skills/`
- Issue: the documented end-to-end workflow spans deterministic Python stages plus skill-driven stages that are not exposed through one installed runner
- Why: the repo intentionally separates deterministic artifact gates from LLM-assisted extraction and interpretation
- Impact: onboarding and roadmap work can drift if stage ownership is not documented precisely
- Fix approach: keep stage contracts explicit in docs and planning, and add targeted handoff verification where possible

**Dependency declarations are broader than the deterministic package surface:**
- Files: `pyproject.toml`, `requirements.txt`
- Issue: dependencies such as `anthropic` and `openpyxl` are declared even though the tracked deterministic package does not import them directly
- Why: the repo supports adjacent skill-driven workflows and workbook-adjacent tasks
- Impact: dependency upgrades can create noise or confusion about what the installed CLI actually requires
- Fix approach: document which dependencies are deterministic-runtime critical versus hybrid-workflow supporting

## Documentation and Contract Drifts (Phase 01)

**`supplementary_snippets.jsonl` is not part of the live source contract:**
- Files: `skill_pipeline/preprocess/source.py`, `.claude/skills/enrich-deal/SKILL.md`
- Issue: `preprocess-source` actively deletes stale `supplementary_snippets.jsonl` and does not regenerate it; the file was historically listed as a skill-stage read input
- Resolution: Phase 01 plan 02 removed the stale reference from enrich-deal SKILL.md; future docs must not list this file as a required input
- Status: resolved in Phase 01

**Legacy `data/deals/<slug>/{extract,qa}` artifacts are not the active contract surface:**
- Files: `data/deals/*/extract/`, `data/deals/*/qa/`
- Issue: the checked-in dataset still contains outputs from an earlier pipeline layout, but current code and skill docs target `data/skill/<slug>/...`
- Impact: contributors or docs that reference `data/deals/<slug>/extract` for current extraction output will be wrong
- Status: labeled as historical/non-authoritative in Phase 01; no cleanup needed unless later phases intentionally revive that layout

**Historical docs look plausible but are not authoritative for the current runtime:**
- Files: `docs/plans/2026-03-16-pipeline-design-v3.md`, `quality_reports/session_logs/2026-03-18_skill-pipeline-design.md`
- Issue: those documents describe earlier transition states (all-filings preprocess, "Alex-compatible" export framing) that no longer match the seed-only, filing-grounded contract
- Resolution: Phase 01 published `docs/workflow-contract.md` as the single canonical stage inventory; historical docs are background context, not live contracts
- Status: documented in Phase 01

**deal-agent name collision between CLI summary and skill orchestrator:**
- Files: `skill_pipeline/deal_agent.py`, `.claude/skills/deal-agent/SKILL.md`, `CLAUDE.md`
- Issue: both surfaces share the name "deal-agent" but have different responsibilities; contributors may assume the CLI command runs end-to-end extraction
- Resolution: Phase 01 plan 02 added a disambiguation section to CLAUDE.md and the workflow contract
- Status: documented in Phase 01

## Known Bugs / Operational Risks

**Future `edgartools` compatibility break risk:**
- Files: `pyproject.toml`, `requirements.txt`, `skill_pipeline/raw/fetch.py`, `skill_pipeline/raw/stage.py`
- Symptoms: live `raw-fetch` can fail if upstream `edgartools` changes its API or identity requirements
- Trigger: upgrading into a breaking `edgartools` release
- Workaround: pin or cap the dependency and verify live fetch behavior before upgrading
- Root cause: the repo depends on a live third-party SEC client with changing semantics

**Chronology localization is heuristic and text-shape sensitive:**
- Files: `skill_pipeline/source/locate.py`, `tests/test_skill_preprocess_source.py`
- Symptoms: unusual filing headings or malformed text may produce `review_required` or fail to select a chronology section
- Trigger: non-standard SEC formatting, OCR-like artifacts, or edge-case headings
- Workaround: inspect `chronology_selection.json` and raw filing text before trusting downstream outputs
- Root cause: regex-driven heading detection and scoring against semi-structured SEC text

## Security Considerations

**Local secret handling depends on developer discipline:**
- Files: `.gitignore`, `CLAUDE.md`
- Risk: developers may create additional local secret files beyond `.env.local`
- Current mitigation: `.env.local` is ignored and repo docs instruct contributors not to commit API keys
- Recommendation: keep secret locations narrow and run secret scans on newly generated docs before committing

**Benchmark contamination remains a policy risk:**
- Files: `CLAUDE.md`, `tests/test_benchmark_separation_policy.py`, `.claude/skills/`
- Risk: future docs or skill updates could accidentally reintroduce benchmark material into pre-export generation
- Current mitigation: explicit repo instructions plus regression tests
- Recommendation: keep policy tests updated whenever docs or skills change

## Performance Bottlenecks

**Large filing processing is local-file and regex heavy:**
- Files: `skill_pipeline/preprocess/source.py`, `skill_pipeline/source/locate.py`, `skill_pipeline/source/evidence.py`
- Problem: preprocessing and evidence scans operate over full filing text in memory
- Measurement: no tracked benchmark numbers
- Cause: the design prioritizes deterministic local artifact generation over streaming optimization
- Improvement path: add timing instrumentation before attempting optimization

## Fragile Areas

**Canonical provenance upgrade path:**
- Files: `skill_pipeline/canonicalize.py`, `skill_pipeline/extract_artifacts.py`, `skill_pipeline/provenance.py`
- Why fragile: canonical and legacy extract modes must coexist, and canonical mode requires `spans.json`
- Common failures: missing span sidecars, mismatched evidence references, or unexpected raw extract structure
- Safe modification: change schema and loaders together, then add regression coverage for both legacy and canonical inputs
- Test coverage: good targeted coverage, but end-to-end hybrid extraction remains outside the deterministic suite

**Raw and preprocess artifact invariants:**
- Files: `skill_pipeline/raw/discover.py`, `skill_pipeline/raw/stage.py`, `skill_pipeline/preprocess/source.py`
- Why fragile: the current contract assumes exactly one approved filing, one registry document, and no supplementary candidates
- Common failures: stale legacy artifacts, malformed seed URLs, or manual edits to raw manifests
- Safe modification: preserve the seed-only invariant unless the repo intentionally redesigns upstream ingestion
- Test coverage: strong targeted coverage in `tests/test_skill_raw_stage.py` and `tests/test_skill_preprocess_source.py`

## Dependencies at Risk

**`edgartools`:**
- Risk: upstream API or deprecation changes could break live SEC fetches
- Impact: active deal refresh work stalls at the ingress stage
- Migration plan: add compatibility checks before upgrades and pin aggressively if behavior changes

## Missing Critical Features

**No tracked CI pipeline:**
- Problem: repo verification depends on local discipline
- Current workaround: run focused pytest commands manually
- Blocks: automatic regression detection on every push
- Implementation complexity: low to medium; mostly repository plumbing

**No single tracked end-to-end runner for the full hybrid workflow:**
- Problem: operators must combine CLI stages with skill invocations manually
- Current workaround: rely on `CLAUDE.md` and skill docs for orchestration
- Blocks: one-command reproducibility and tighter end-to-end automation
- Implementation complexity: medium; it requires careful boundary design rather than just shelling stages together

## Test Coverage Gaps

**Skill-driven stages are not executed in the tracked pytest suite:**
- What's not tested: `/extract-deal`, `/verify-extraction`, `/enrich-deal`, `/export-csv`, and `/reconcile-alex`
- Risk: contract drift between the deterministic Python stages and the skill-driven stages may go unnoticed until manual runs
- Priority: high
- Difficulty to test: medium; requires stable test fixtures or harnesses for the agent workflow

---

*Concerns audit: 2026-03-25*
*Updated: 2026-03-25 after Phase 01 plan 03*
*Update as issues are fixed or new ones are discovered*
