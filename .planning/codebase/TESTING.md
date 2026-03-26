# Testing Patterns

**Analysis Date:** 2026-03-26

## Test Framework

**Runner:**
- `pytest` `>=8.0`, declared in `pyproject.toml`
- Config: `pytest.ini`
- `pytest.ini` sets `pythonpath = .`, `testpaths = tests`, and `addopts = -ra`
- CI workflow: Not detected. `.github/` is absent in the repository root.

**Assertion Library:**
- Pytest built-in assertions
- Error assertions use `pytest.raises(..., match=...)`
- Environment and dependency overrides use `pytest.MonkeyPatch`

**Run Commands:**
```bash
pytest -q
pytest -q tests/test_skill_raw_stage.py tests/test_skill_preprocess_source.py
pytest -q tests/test_skill_pipeline.py::test_run_deal_agent_summarizes_existing_skill_artifacts -v
```
Watch mode: Not detected in the repository.
Coverage command: Not detected in the repository.

## Test File Organization

**Location:**
- All tracked tests live in the top-level `tests/` directory. Source files are not colocated with tests.
- There is no tracked `conftest.py`; fixture helpers are local to individual test modules.

**Naming:**
- Use `test_skill_<stage>.py` for deterministic stage suites, for example `tests/test_skill_check.py`, `tests/test_skill_verify.py`, `tests/test_skill_coverage.py`, `tests/test_skill_canonicalize.py`, and `tests/test_skill_enrich_core.py`.
- Use descriptive policy or contract filenames for repo-wide safeguards, for example `tests/test_benchmark_separation_policy.py`, `tests/test_skill_mirror_sync.py`, and `tests/test_workflow_contract_surface.py`.
- Use `test_<behavior>()` function names with full behavioral statements, for example `test_preprocess_source_rejects_tampered_raw_filing_text()` in `tests/test_skill_preprocess_source.py` and `test_run_deal_agent_reports_deterministic_enrichment_when_interpretive_artifact_is_missing()` in `tests/test_skill_pipeline.py`.

**Structure:**
```text
tests/
├── test_benchmark_separation_policy.py
├── test_skill_canonicalize.py
├── test_skill_check.py
├── test_skill_coverage.py
├── test_skill_enrich_core.py
├── test_skill_mirror_sync.py
├── test_skill_pipeline.py
├── test_skill_preprocess_source.py
├── test_skill_provenance.py
├── test_skill_raw_stage.py
├── test_skill_verify.py
└── test_workflow_contract_surface.py
```

Current suite size: 12 files and 116 `test_` functions under `tests/`.

## Test Structure

**Suite Organization:**
```python
def _write_check_fixture(
    tmp_path: Path,
    *,
    slug: str = "imprivata",
    bidder_kind: str | None = "financial",
    proposal_terms: bool = True,
    proposal_formality_signals: bool = True,
    anchor_text: str = "indication of interest",
    actors_payload: dict | None = None,
    events_payload: dict | None = None,
) -> None:
    data_dir = tmp_path / "data"
    deals_source_dir = data_dir / "deals" / slug / "source"
    raw_dir = tmp_path / "raw" / slug
    extract_dir = data_dir / "skill" / slug / "extract"


def test_run_check_fails_on_missing_proposal_terms(tmp_path: Path) -> None:
    _write_check_fixture(tmp_path, proposal_terms=False)
    exit_code = run_check("imprivata", project_root=tmp_path)
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    report = json.loads(paths.check_report_path.read_text(encoding="utf-8"))

    assert exit_code == 1
    assert report["summary"]["status"] == "fail"
```
Pattern shown in `tests/test_skill_check.py`.

**Patterns:**
- Prefer plain test functions over `class Test...` suites. No class-based pytest suites are present in `tests/`.
- Build isolated temp artifact trees with `tmp_path`, usually under `tmp_path / "data"` and `tmp_path / "raw"`.
- Put fixture-building helpers at the top of each test file, for example `_write_check_fixture()` in `tests/test_skill_check.py`, `_write_verify_fixture_for_clean_pass()` in `tests/test_skill_verify.py`, `_write_coverage_fixture()` in `tests/test_skill_coverage.py`, `_write_seed_only_raw_fixture()` in `tests/test_skill_preprocess_source.py`, and `_write_enrich_core_fixture()` in `tests/test_skill_enrich_core.py`.
- Assert both the returned exit code or summary object and the on-disk artifact content. This pattern is consistent in `tests/test_skill_check.py`, `tests/test_skill_verify.py`, `tests/test_skill_coverage.py`, `tests/test_skill_canonicalize.py`, and `tests/test_skill_pipeline.py`.
- Use direct stage-function calls for most coverage. CLI parser tests are narrow and explicit, for example `test_skill_cli_supports_check_subcommand()` in `tests/test_skill_check.py`, `test_skill_cli_supports_coverage_subcommand()` in `tests/test_skill_coverage.py`, and `test_skill_cli_supports_deal_agent_subcommand()` in `tests/test_skill_pipeline.py`.
- Use `@pytest.mark.parametrize(...)` sparingly for compact invalid-input matrices. The current example is `test_preprocess_source_fails_when_primary_candidate_count_is_not_one()` in `tests/test_skill_preprocess_source.py`.

## Mocking

**Framework:** Pytest `monkeypatch`, direct dependency injection, and lightweight local stubs.

**Patterns:**
```python
def test_set_identity_requires_configured_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(stage, "set_identity", lambda value: None)
    monkeypatch.delenv("PIPELINE_SEC_IDENTITY", raising=False)
    monkeypatch.delenv("SEC_IDENTITY", raising=False)
    monkeypatch.delenv("EDGAR_IDENTITY", raising=False)

    with pytest.raises(ValueError, match="EDGAR_IDENTITY"):
        stage._set_identity()
```
Pattern shown in `tests/test_skill_raw_stage.py`.

**What to Mock:**
- EDGAR-facing calls and identity setup in `tests/test_skill_raw_stage.py`
- Environment variables via `monkeypatch.setenv()` and `monkeypatch.delenv()` in `tests/test_skill_raw_stage.py`
- Script execution boundaries via `subprocess.run(..., check=False, text=True)` in `tests/test_skill_mirror_sync.py`
- Optional dependency seams and injected fetch helpers such as `fetch_contents_fn` and `get_filing_fn` in `tests/test_skill_raw_stage.py`

**What NOT to Mock:**
- Pydantic model validation in `skill_pipeline/models.py` and `skill_pipeline/pipeline_models/`
- JSON serialization and file writes
- `Path`-based filesystem layout under `tmp_path`
- Deterministic stage logic such as quote matching, coverage finding generation, actor deduplication, NDA gating, and enrich-core classification rules

## Fixtures and Factories

**Test Data:**
```python
evidence_items = [
    {
        "evidence_id": "DOC001:E0001",
        "document_id": "DOC001",
        "accession_number": "DOC001",
        "filing_type": "DEFM14A",
        "start_line": 1,
        "end_line": 1,
        "raw_text": "Party A submitted an indication of interest.",
        "evidence_type": "dated_action",
        "confidence": "high",
        "matched_terms": ["submitted", "indication of interest"],
        "date_text": "July 5, 2016",
        "actor_hint": "Party A",
        "value_hint": None,
        "note": None,
    }
]
```
Pattern shown in `tests/test_skill_coverage.py`.

**Location:**
- Keep data builders local to the suite that owns them. There is no shared fixture module.
- Common helper naming uses `_write_*_fixture`, `_write_shared_inputs`, `_seed`, `_actor`, `_event`, and `_read_*` patterns across `tests/test_skill_check.py`, `tests/test_skill_preprocess_source.py`, `tests/test_skill_pipeline.py`, `tests/test_skill_raw_stage.py`, and `tests/test_skill_verify.py`.

## Coverage

**Requirements:** No numeric coverage threshold is enforced by repo config.

**View Coverage:**
```bash
# Not detected: pytest-cov, coverage.py, or a repo-specific coverage command
```

**Current practice:**
- Coverage is regression-oriented rather than percentage-driven.
- The suite focuses on deterministic boundary conditions:
  - fail-fast input validation in `tests/test_skill_preprocess_source.py` and `tests/test_skill_raw_stage.py`
  - structural and provenance gates in `tests/test_skill_check.py`, `tests/test_skill_verify.py`, and `tests/test_skill_provenance.py`
  - canonicalization edge cases in `tests/test_skill_canonicalize.py`
  - source-cue audit behavior in `tests/test_skill_coverage.py`
  - downstream deterministic enrichment logic in `tests/test_skill_enrich_core.py`
  - documentation and mirror hygiene in `tests/test_benchmark_separation_policy.py`, `tests/test_skill_mirror_sync.py`, and `tests/test_workflow_contract_surface.py`

## Test Types

**Unit Tests:**
- Most files are unit-ish deterministic stage tests that exercise one stage against minimal artifacts under `tmp_path`.
- Representative files: `tests/test_skill_raw_stage.py`, `tests/test_skill_preprocess_source.py`, `tests/test_skill_check.py`, `tests/test_skill_verify.py`, `tests/test_skill_coverage.py`, `tests/test_skill_canonicalize.py`, and `tests/test_skill_provenance.py`.

**Integration Tests:**
- `tests/test_skill_pipeline.py` covers the `deal-agent` summary surface across multiple artifact directories.
- `tests/test_skill_enrich_core.py` exercises cross-artifact dependencies by requiring check, verify, and coverage artifacts before writing deterministic enrichment outputs.
- `tests/test_skill_mirror_sync.py` is an integration test for the mirror-sync script in `scripts/sync_skill_mirrors.py`.

**E2E Tests:**
- Not used. No test invokes the full LLM-assisted workflow end to end.
- The suite covers deterministic contracts around the LLM boundary instead, especially in `tests/test_workflow_contract_surface.py` and `tests/test_benchmark_separation_policy.py`.

## Common Patterns

**Async Testing:**
```python
# Not applicable: no async tests, no asyncio plugin usage, and no async fixtures detected.
```

**Error Testing:**
```python
def test_enrich_core_requires_gate_artifacts(tmp_path: Path) -> None:
    _write_enrich_core_fixture(tmp_path)

    with pytest.raises(FileNotFoundError, match="check_report.json"):
        run_enrich_core("imprivata", project_root=tmp_path)
```
Pattern shown in `tests/test_skill_enrich_core.py`.

**Artifact assertion pattern:**
```python
exit_code = run_coverage("imprivata", project_root=tmp_path)
paths = build_skill_paths("imprivata", project_root=tmp_path)
findings = json.loads(paths.coverage_findings_path.read_text(encoding="utf-8"))
summary = json.loads(paths.coverage_summary_path.read_text(encoding="utf-8"))

assert exit_code == 1
assert summary["status"] == "fail"
assert findings["findings"][0]["cue_family"] == "proposal"
```
Pattern shown in `tests/test_skill_coverage.py`.

**Subprocess script testing:**
- `tests/test_skill_mirror_sync.py` uses a local `_run()` wrapper around `subprocess.run()` with `capture_output=True`, `check=False`, and `text=True`, then asserts on `returncode`, `stdout`, and filesystem side effects.

---

*Testing analysis: 2026-03-26*
