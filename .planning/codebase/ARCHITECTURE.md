# Architecture

**Analysis Date:** 2026-03-26

## Pattern Overview

**Overall:** File-backed hybrid pipeline with deterministic Python CLI stages in `skill_pipeline/` and LLM skill stages in `.claude/skills/`

**Key Characteristics:**
- The only installed runtime surface is the `skill_pipeline` package declared in `pyproject.toml`, with the `skill-pipeline` console entrypoint bound to `skill_pipeline/cli.py`.
- Stage boundaries are artifact boundaries. Deterministic code reads and writes JSON, JSONL, CSV, and frozen filing text under `raw/`, `data/deals/`, and `data/skill/` instead of using a service bus or database.
- Deal-specific filesystem layout is centralized in `skill_pipeline/paths.py` via `build_skill_paths()` and the `SkillPathSet` model in `skill_pipeline/models.py`.
- The active deterministic chain is `raw-fetch` -> `preprocess-source` -> `canonicalize` -> `check` -> `verify` -> `coverage` -> `enrich-core`, dispatched from `skill_pipeline/cli.py`.
- The active LLM skill surface is external to the package: `.claude/skills/extract-deal/SKILL.md`, `.claude/skills/verify-extraction/SKILL.md`, `.claude/skills/enrich-deal/SKILL.md`, `.claude/skills/export-csv/SKILL.md`, `.claude/skills/reconcile-alex/SKILL.md`, with mirrors under `.codex/skills/` and `.cursor/skills/`.
- Runtime validation is fail-fast. The code raises on missing inputs, malformed schemas, unresolved provenance, and failed gate prerequisites rather than degrading into partial output.
- `docs/workflow-contract.md` is the detailed stage inventory, and `tests/test_workflow_contract_surface.py` guards that contract at the repository level.

## Layers

**CLI Dispatch Layer:**
- Purpose: expose deterministic commands and translate CLI arguments into stage function calls.
- Location: `skill_pipeline/cli.py`
- Contains: `argparse` parser construction, `--deal` argument handling, lazy imports for raw/preprocess commands, JSON printing for ingress commands, integer exit codes for gate stages.
- Depends on: `skill_pipeline/config.py`, `skill_pipeline/seeds.py`, `skill_pipeline/deal_agent.py`, `skill_pipeline/canonicalize.py`, `skill_pipeline/check.py`, `skill_pipeline/verify.py`, `skill_pipeline/coverage.py`, `skill_pipeline/enrich_core.py`.
- Used by: the `skill-pipeline` executable declared in `pyproject.toml`.

**Contract and Path Layer:**
- Purpose: define shared constants, schema models, and filesystem path conventions.
- Location: `skill_pipeline/config.py`, `skill_pipeline/models.py`, `skill_pipeline/pipeline_models/common.py`, `skill_pipeline/pipeline_models/raw.py`, `skill_pipeline/pipeline_models/source.py`, `skill_pipeline/paths.py`
- Contains: artifact envelopes, actor/event schemas, verification and coverage schemas, `SkillPathSet`, primary filing preferences, repo root constants.
- Depends on: `pydantic`, `pathlib`, standard library enums and dates.
- Used by: every deterministic stage and summary surface.

**Seed and Raw Ingress Layer:**
- Purpose: resolve a deal seed, derive a discovery manifest, fetch SEC filing text, and freeze immutable raw artifacts.
- Location: `skill_pipeline/seeds.py`, `skill_pipeline/raw/discover.py`, `skill_pipeline/raw/fetch.py`, `skill_pipeline/raw/stage.py`, `skill_pipeline/source/ranking.py`
- Contains: `load_seed_entry()`, seed-to-manifest translation, accession parsing, EDGAR identity setup, immutable raw file writes, raw manifest and registry creation.
- Depends on: `data/seeds.csv`, `edgartools` at runtime, raw/source pipeline models.
- Used by: `skill-pipeline raw-fetch --deal <slug>` and `skill-pipeline source-discover --deal <slug>`.

**Source Preparation Layer:**
- Purpose: validate frozen raw documents, localize the chronology section, split it into blocks, and scan evidence cues.
- Location: `skill_pipeline/preprocess/source.py`, `skill_pipeline/source/locate.py`, `skill_pipeline/source/blocks.py`, `skill_pipeline/source/evidence.py`, `skill_pipeline/source_validation.py`
- Contains: chronology candidate scoring, section selection confidence, block generation, evidence scanning, raw-file checksum and path validation, source artifact materialization.
- Depends on: `raw/<slug>/document_registry.json`, `raw/<slug>/filings/*.txt`, source models in `skill_pipeline/pipeline_models/source.py`.
- Used by: `skill-pipeline preprocess-source --deal <slug>` and `skill_pipeline/deal_agent.py` shared-input validation.

**Extract Artifact Adapter and Provenance Layer:**
- Purpose: load extract outputs in either raw or canonical mode and resolve evidence to span-backed provenance.
- Location: `skill_pipeline/extract_artifacts.py`, `skill_pipeline/provenance.py`, `skill_pipeline/normalize/dates.py`, `skill_pipeline/normalize/quotes.py`
- Contains: `LoadedExtractArtifacts`, raw-versus-canonical detection, `spans.json` sidecar enforcement, quote normalization, relative-date parsing, span resolution against raw filing lines.
- Depends on: `data/skill/<slug>/extract/`, `data/deals/<slug>/source/`, raw filing text under `raw/<slug>/filings/`.
- Used by: `skill_pipeline/canonicalize.py`, `skill_pipeline/check.py`, `skill_pipeline/verify.py`, `skill_pipeline/coverage.py`, `skill_pipeline/enrich_core.py`, `skill_pipeline/deal_agent.py`.

**Deterministic Gate Layer:**
- Purpose: upgrade extract schema and enforce structural, referential, quote, and coverage constraints before enrichment.
- Location: `skill_pipeline/canonicalize.py`, `skill_pipeline/check.py`, `skill_pipeline/verify.py`, `skill_pipeline/coverage.py`
- Contains: raw-to-canonical upgrade, span registry creation, event and actor deduplication, NDA gating, unnamed-party recovery, structural checks, quote verification, coverage cue auditing.
- Depends on: extract artifacts in `data/skill/<slug>/extract/`, source artifacts in `data/deals/<slug>/source/`, raw filings and document registry under `raw/<slug>/`.
- Used by: `skill-pipeline canonicalize`, `skill-pipeline check`, `skill-pipeline verify`, `skill-pipeline coverage`, and the external `/verify-extraction` skill.

**Deterministic Enrichment and Summary Layer:**
- Purpose: derive deterministic process structure after gates pass and summarize artifact status for orchestration.
- Location: `skill_pipeline/enrich_core.py`, `skill_pipeline/deal_agent.py`
- Contains: round pairing, proposal classification, cycle segmentation, formal boundary computation, deal-stage status summaries, preflight validation.
- Depends on: canonical extract artifacts plus passing `check`, `verify`, and `coverage` outputs.
- Used by: `skill-pipeline enrich-core --deal <slug>` and `skill-pipeline deal-agent --deal <slug>`.

**Skill Orchestration and Mirror Layer:**
- Purpose: host the LLM-operated workflow stages and keep agent-specific skill trees aligned.
- Location: `.claude/skills/`, `.codex/skills/`, `.cursor/skills/`, `scripts/sync_skill_mirrors.py`
- Contains: the canonical skill instructions in `.claude/skills/*/SKILL.md`, mirrored copies for other agents, and the sync/check utility.
- Depends on: deterministic artifacts produced by `skill_pipeline/` and repository policy in `CLAUDE.md`.
- Used by: human operators and coding agents invoking `/deal-agent`, `/extract-deal`, `/verify-extraction`, `/enrich-deal`, `/export-csv`, and `/reconcile-alex`.

## Data Flow

**Deterministic and Skill Deal Flow:**

1. `skill_pipeline/cli.py` receives `skill-pipeline raw-fetch --deal <slug>` or `skill-pipeline source-discover --deal <slug>`.
2. `skill_pipeline/seeds.py` loads the requested seed row from `data/seeds.csv`.
3. `skill_pipeline/raw/discover.py` turns the seed URL into a `RawDiscoveryManifest`, and `skill_pipeline/raw/stage.py` calls `skill_pipeline/raw/fetch.py` to freeze filing text into `raw/<slug>/filings/` and write `raw/<slug>/discovery.json` plus `raw/<slug>/document_registry.json`.
4. `skill_pipeline/preprocess/source.py` validates `raw/<slug>/document_registry.json`, loads the frozen `.txt` filing from `raw/<slug>/filings/`, calls `skill_pipeline/source/locate.py` to select the chronology section, then writes `data/deals/<slug>/source/chronology_selection.json`, `data/deals/<slug>/source/chronology_blocks.jsonl`, `data/deals/<slug>/source/evidence_items.jsonl`, `data/deals/<slug>/source/chronology.json`, and copied filing snapshots under `data/deals/<slug>/source/filings/`.
5. `.claude/skills/extract-deal/SKILL.md` consumes the source artifacts and writes `data/skill/<slug>/extract/actors_raw.json` and `data/skill/<slug>/extract/events_raw.json`. The current tree also contains per-chunk artifacts under `data/skill/<slug>/extract/chunks/` for `petsmart-inc` and `stec`.
6. `skill_pipeline/canonicalize.py` reads those raw extract files plus source artifacts, upgrades evidence references into span-backed provenance, overwrites `data/skill/<slug>/extract/actors_raw.json` and `data/skill/<slug>/extract/events_raw.json` with canonical schema, writes `data/skill/<slug>/extract/spans.json`, and writes `data/skill/<slug>/canonicalize/canonicalize_log.json`.
7. `skill_pipeline/check.py` writes `data/skill/<slug>/check/check_report.json`; `skill_pipeline/verify.py` writes `data/skill/<slug>/verify/verification_findings.json` and `data/skill/<slug>/verify/verification_log.json`; `skill_pipeline/coverage.py` writes `data/skill/<slug>/coverage/coverage_findings.json` and `data/skill/<slug>/coverage/coverage_summary.json`.
8. `.claude/skills/verify-extraction/SKILL.md` may repair the canonical extract files when the deterministic findings are repairable.
9. `skill_pipeline/enrich_core.py` reads the gate artifacts, refuses to proceed unless they all pass, and writes `data/skill/<slug>/enrich/deterministic_enrichment.json`.
10. `.claude/skills/enrich-deal/SKILL.md` may add `data/skill/<slug>/enrich/enrichment.json`, `.claude/skills/export-csv/SKILL.md` may add `data/skill/<slug>/export/deal_events.csv`, and `.claude/skills/reconcile-alex/SKILL.md` may add `data/skill/<slug>/reconcile/` outputs after export completes.

**State Management:**
- Repository files are the runtime state. The codebase does not define a database, queue, or long-lived service process.
- `skill_pipeline/extract_artifacts.py` determines whether extract artifacts are in `legacy` or `canonical` mode by inspecting payload shape, then requires `data/skill/<slug>/extract/spans.json` when canonical evidence is present.
- `skill_pipeline/deal_agent.py` summarizes stage state by inspecting the presence and schema validity of artifact files rather than by calling live services.

## Key Abstractions

**Artifact Families:**
- Purpose: carry typed data across every stage boundary.
- Examples: `RawDiscoveryManifest` and `RawDocumentRegistry` in `skill_pipeline/pipeline_models/raw.py`; `ChronologySelection`, `ChronologyBlock`, `EvidenceItem`, and `FrozenDocument` in `skill_pipeline/pipeline_models/source.py`; `SkillActorsArtifact`, `SkillEventsArtifact`, `SpanRegistryArtifact`, `SkillCheckReport`, `SkillVerificationLog`, and `DeterministicEnrichmentArtifact` in `skill_pipeline/models.py`.
- Pattern: validate at read time with `model_validate()` and serialize to explicit artifact files.

**Deal Path Set:**
- Purpose: make every deterministic stage derive the same file layout from a deal slug.
- Examples: `build_skill_paths()` in `skill_pipeline/paths.py`, `SkillPathSet` in `skill_pipeline/models.py`.
- Pattern: compute all stage input and output paths once, then pass the resulting `SkillPathSet` through the stage.

**Mode-Aware Extract Loader:**
- Purpose: let downstream stages operate on either raw extract payloads or canonical span-backed payloads.
- Examples: `LoadedExtractArtifacts` and `load_extract_artifacts()` in `skill_pipeline/extract_artifacts.py`.
- Pattern: detect canonical mode by `evidence_span_ids`, then require `spans.json` and expose a `span_index` for downstream checks.

**Span-Backed Provenance:**
- Purpose: preserve a deterministic link from extracted actors and events back to exact filing text ranges.
- Examples: `resolve_text_span()` in `skill_pipeline/provenance.py`, `SpanRecord` and `SpanRegistryArtifact` in `skill_pipeline/models.py`.
- Pattern: convert block/evidence references into explicit span IDs, store them in `data/skill/<slug>/extract/spans.json`, and reject fuzzy or unresolved matches in verification.

**Chronology Selection Contract:**
- Purpose: isolate the filing subsection that downstream extraction is allowed to consume.
- Examples: `ChronologyCandidate` and `ChronologySelection` in `skill_pipeline/pipeline_models/source.py`, `select_chronology()` in `skill_pipeline/source/locate.py`.
- Pattern: score candidate headings and section context, emit a selected candidate with confidence metadata, and treat missing or ambiguous chronology as a hard failure.

## Entry Points

**Deterministic CLI:**
- Location: `skill_pipeline/cli.py`
- Triggers: `skill-pipeline deal-agent`, `skill-pipeline raw-fetch`, `skill-pipeline preprocess-source`, `skill-pipeline source-discover`, `skill-pipeline canonicalize`, `skill-pipeline check`, `skill-pipeline verify`, `skill-pipeline coverage`, `skill-pipeline enrich-core`
- Responsibilities: parse arguments, load seeds when needed, dispatch to stage functions, print JSON for discovery/fetch/preprocess/summary commands, and return exit codes for gate commands.

**Preflight Summary Command:**
- Location: `skill_pipeline/deal_agent.py`
- Triggers: `skill-pipeline deal-agent --deal <slug>`
- Responsibilities: validate shared inputs, ensure output directories exist, and summarize extract/check/coverage/verify/enrich/export status.

**Skill Workflow Surface:**
- Location: `.claude/skills/deal-agent/SKILL.md`, `.claude/skills/extract-deal/SKILL.md`, `.claude/skills/verify-extraction/SKILL.md`, `.claude/skills/enrich-deal/SKILL.md`, `.claude/skills/export-csv/SKILL.md`, `.claude/skills/reconcile-alex/SKILL.md`
- Triggers: explicit skill invocation by a human or agent.
- Responsibilities: run the LLM-owned extraction, repair, interpretive enrichment, export, and reconciliation stages around the deterministic artifact contracts.

**Skill Mirror Maintenance:**
- Location: `scripts/sync_skill_mirrors.py`
- Triggers: `python scripts/sync_skill_mirrors.py` and `python scripts/sync_skill_mirrors.py --check`
- Responsibilities: copy the canonical `.claude/skills/` tree into `.codex/skills/` and `.cursor/skills/`, normalize line endings, and fail on drift when run in check mode.

## Error Handling

**Strategy:** deterministic stages reject untrusted state early and remove incomplete success artifacts when a stage cannot finish coherently.

**Patterns:**
- Required inputs are checked before work begins. Examples: `run_canonicalize()` in `skill_pipeline/canonicalize.py`, `run_verify()` in `skill_pipeline/verify.py`, `run_coverage()` in `skill_pipeline/coverage.py`, and `run_enrich_core()` in `skill_pipeline/enrich_core.py` all raise `FileNotFoundError` for missing stage inputs.
- Source-file integrity is validated against registry metadata. `validate_frozen_document()` in `skill_pipeline/source_validation.py` checks path confinement, byte counts, and SHA-256 hashes.
- Partial source outputs are invalidated on failure. `preprocess_source_deal()` in `skill_pipeline/preprocess/source.py` deletes generated source files and copied filings if an exception occurs after work starts.
- Partial deterministic enrichment is invalidated on failure. `run_enrich_core()` in `skill_pipeline/enrich_core.py` removes `data/skill/<slug>/enrich/deterministic_enrichment.json` if the stage raises.
- `check`, `verify`, and `coverage` write machine-readable reports even when they fail, then return a non-zero exit code based on blocker or error findings.
- Canonical provenance is mandatory. `load_extract_artifacts()` in `skill_pipeline/extract_artifacts.py` raises if canonical evidence is detected without `data/skill/<slug>/extract/spans.json`.

## Cross-Cutting Concerns

**Logging:** No dedicated logging framework is configured. Deterministic commands primarily communicate through artifact files and JSON printed by `skill_pipeline/cli.py`.

**Validation:** Pydantic models in `skill_pipeline/models.py` and `skill_pipeline/pipeline_models/` define the contract for every artifact family. Deterministic stages validate on both load and save paths.

**Authentication:** `skill_pipeline/raw/stage.py` sets the EDGAR identity from `PIPELINE_SEC_IDENTITY`, `SEC_IDENTITY`, or `EDGAR_IDENTITY` and raises when no identity is available for live SEC access.

**Boundary Policy:** `CLAUDE.md`, `docs/workflow-contract.md`, `example/README.md`, `diagnosis/README.md`, and `tests/test_benchmark_separation_policy.py` define a hard separation between filing-grounded generation artifacts and benchmark materials under `example/` and `diagnosis/`.

**Skill Tree Ownership:** `.claude/skills/` is the canonical skill source. `.codex/skills/` and `.cursor/skills/` are mirrors maintained by `scripts/sync_skill_mirrors.py`.

---

*Architecture analysis: 2026-03-26*
