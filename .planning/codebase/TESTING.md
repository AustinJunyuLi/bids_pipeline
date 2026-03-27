# Testing Patterns

**Analysis Date:** 2026-03-27

## Test Framework

**Runner:**
- `pytest` (8.0+) - configured in `pyproject.toml`
- Config file: `pytest.ini`
- Configuration:
  ```ini
  [pytest]
  pythonpath = .
  testpaths = tests
  addopts = -ra
  ```

**Assertion Library:**
- pytest's built-in assertions (no external library)
- `assert` statements with expressions
- `pytest.raises()` context manager for exception testing

**Run Commands:**
```bash
pytest -q                           # Run all tests, quiet output
pytest -q tests/test_skill_check.py # Run single test file
pytest -q tests/test_skill_check.py::test_name -v  # Run single test with verbose
```

## Test File Organization

**Location:**
- All tests in `tests/` directory at project root
- Co-located with source code (not embedded in packages)
- Separate from `skill_pipeline/` source tree

**Naming:**
- Test files: `test_<stage_or_module>.py`
- Test functions: `test_<behavior_or_scenario>()`
- Fixture helper functions: `_write_<artifact_type>_fixture()` (leading underscore, not a test)

**File Structure:**
```
tests/
├── test_skill_check.py              # Tests for check stage
├── test_skill_canonicalize.py       # Tests for canonicalize stage
├── test_skill_coverage.py           # Tests for coverage stage
├── test_skill_enrich_core.py        # Tests for enrich-core stage
├── test_skill_pipeline.py           # Integration/pipeline tests
├── test_skill_preprocess_source.py  # Tests for preprocess-source stage
├── test_skill_raw_stage.py          # Tests for raw fetch/stage
├── test_skill_verify.py             # Tests for verify stage
├── test_skill_provenance.py         # Tests for span resolution
├── test_benchmark_separation_policy.py  # Policy validation tests
└── test_skill_mirror_sync.py        # Tests for skill sync script
```

## Test Structure

**Suite Organization:**
- One test function per scenario
- Helper fixtures create artifacts for each test
- No conftest.py (fixtures local to test files)
- Clear test names describing what is being validated

**Example Test from `test_skill_check.py`:**
```python
def test_run_check_fails_on_missing_proposal_terms(tmp_path: Path) -> None:
    """When proposal event has no terms, check should fail."""
    _write_check_fixture(
        tmp_path,
        slug="imprivata",
        proposal_terms=False,  # Omit terms
    )
    paths = build_skill_paths("imprivata", project_root=tmp_path)
    result = run_check("imprivata", project_root=tmp_path)
    assert result == 1
    report = SkillCheckReport.model_validate_json(
        paths.check_report_path.read_text(encoding="utf-8")
    )
    assert report.summary.status == "fail"
    assert any(f.check_id == "proposal_terms_required" for f in report.findings)
```

**Patterns:**
1. **Setup:** Call helper fixture `_write_<type>_fixture()` to create input files
2. **Execute:** Call the function being tested with temporary directory
3. **Assert:** Validate return codes, artifacts, and parsed outputs

**Fixture Functions:**
- Named `_write_<artifact>_fixture()` with leading underscore
- Accept `tmp_path: Path` parameter from pytest
- Parameters control test scenarios (e.g., `proposal_terms=False`)
- Create directory structure and write JSON/JSONL files
- Example from `test_skill_check.py`:
  ```python
  def _write_check_fixture(
      tmp_path: Path,
      *,
      slug: str = "imprivata",
      bidder_kind: str | None = "financial",
      proposal_terms: bool = True,
      proposal_formality_signals: bool = True,
      anchor_text: str = "indication of interest",
  ) -> None:
      """Write minimal extract artifacts for check tests."""
  ```

## Mocking

**Framework:** `pytest.MonkeyPatch` for environment and module patching

**Patterns:**
- Use `monkeypatch` fixture (pytest built-in) for:
  - Environment variable manipulation
  - Module attribute patching
- No `unittest.mock` used
- No `pytest-mock` dependency

**Examples from `test_skill_raw_stage.py`:**
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

**What to Mock:**
- Environment variables (for identity/configuration tests)
- External module functions (rarely used)
- `edgartools` fetch operations (in raw fetch tests)

**What NOT to Mock:**
- File I/O: Use `tmp_path` fixture for real filesystem operations
- Pydantic models: Instantiate real models with test data
- Pipeline stage logic: Test real behavior, not mocked stubs
- Internal helper functions: Test through public API

## Fixtures and Test Data

**Test Data Creation:**
- Fixtures build synthetic artifacts matching schema
- Minimal but valid: only required fields and test-specific variations
- JSONL format: one dict per line for chronology/evidence
- Seed CSV: minimal entries sufficient for stage under test

**Example Fixture Structure from `test_skill_canonicalize.py`:**
```python
def _write_canon_fixture(
    tmp_path: Path,
    *,
    slug: str = "imprivata",
    actors_payload: dict | None = None,
    events: list[dict],
) -> None:
    # Create directory structure
    data_dir = tmp_path / "data"
    deals_source_dir = data_dir / "deals" / slug / "source"
    extract_dir = data_dir / "skill" / slug / "extract"
    filings_dir = tmp_path / "raw" / slug / "filings"

    # Write seed CSV
    (data_dir / "seeds.csv").write_text("...")

    # Write extract artifacts
    (extract_dir / "actors_raw.json").write_text(json.dumps(actors_payload))
    (extract_dir / "events_raw.json").write_text(json.dumps(events_payload))

    # Write source artifacts (chronology blocks, evidence items)
    (deals_source_dir / "chronology_blocks.jsonl").write_text(...)
    (deals_source_dir / "evidence_items.jsonl").write_text(...)
```

**Location:**
- Fixtures defined at top of each test file
- Parametrized fixtures use `tmp_path` from pytest
- No shared fixtures module (each test file is independent)

**Coverage of Scenarios:**
- Normal/happy path
- Missing required fields
- Invalid values
- Boundary conditions (empty lists, None values)

## Assertion Patterns

**Exception Testing:**
- Use `pytest.raises()` context manager
- Match message patterns with `match=` parameter
- Example from multiple tests:
  ```python
  with pytest.raises(FileNotFoundError, match="Missing required input"):
      run_canonicalize("imprivata", project_root=tmp_path)
  ```

**Artifact Validation:**
- Parse artifacts into Pydantic models
- Assert model state using field checks
- Example from `test_skill_check.py`:
  ```python
  report = SkillCheckReport.model_validate_json(
      paths.check_report_path.read_text(encoding="utf-8")
  )
  assert report.summary.status == "fail"
  assert any(f.check_id == "proposal_terms_required" for f in report.findings)
  ```

**Return Code Checking:**
- Stage runners return `0` for success, `1` for failure
- Assert return code matches expectation:
  ```python
  result = run_check("imprivata", project_root=tmp_path)
  assert result == 1
  ```

**File Existence:**
- Use `path.exists()` to verify outputs written
- Use `json.loads(path.read_text())` to parse and validate

## Test Types

**Unit Tests:**
- Scope: Individual stage or helper function
- Approach: Create minimal inputs, validate outputs
- Coverage: Normal flow, error conditions, boundary cases
- Files: `test_skill_check.py`, `test_skill_verify.py`, etc.

**Integration Tests:**
- Scope: Multi-stage pipeline or full deal workflow
- Approach: Create complete artifacts, run full pipeline
- Coverage: End-to-end flows, cross-stage communication
- Files: `test_skill_pipeline.py`

**Policy Tests:**
- Scope: Validation of design constraints
- Approach: Scan documentation and code for violations
- Coverage: Benchmark separation, stage responsibilities
- Files: `test_benchmark_separation_policy.py`

**E2E Tests:**
- Status: Not used
- No external service mocking; no live API calls

## Test Coverage

**Requirements:** No explicit coverage target configured

**View Coverage:**
```bash
# No coverage tool configured in pyproject.toml
# To add coverage reporting:
pytest --cov=skill_pipeline --cov-report=html tests/
```

**Current Practice:**
- Regression tests added for each bug fixed
- Tests cover all deterministic stages
- High coverage for validation logic (check, verify, coverage, canonicalize)
- Lower coverage for pure data transformation stages

## Common Testing Patterns

**Async Testing:**
- Not used; no async code in pipeline
- All operations are synchronous

**Error Testing:**
- Exception type validated: `pytest.raises(FileNotFoundError)`
- Message pattern matched: `match="pattern"`
- Example:
  ```python
  with pytest.raises(ValueError, match="block_id"):
      run_canonicalize("deal", project_root=tmp_path)
  ```

**Parametrized Tests:**
- `@pytest.mark.parametrize` used occasionally
- Example from `test_skill_preprocess_source.py`:
  ```python
  @pytest.mark.parametrize("primary_count", [0, 2])
  def test_exactly_one_primary_candidate(primary_count: int, tmp_path: Path) -> None:
      # Test both zero and multiple primary candidates
  ```

**Temporary Files:**
- `tmp_path` fixture from pytest for isolated test directories
- Each test gets fresh directory under system temp
- No cleanup needed (pytest handles it)

## Key Testing Principles

**Fail-Fast Philosophy:**
- Tests validate that errors are raised correctly
- Missing files cause `FileNotFoundError`
- Invalid data causes `ValueError`
- Tests verify these exceptions are thrown appropriately

**Deterministic Tests:**
- All tests pass/fail consistently (no random data)
- No external service calls
- No time-dependent behavior
- File paths and IDs are fixed per test

**Isolated Tests:**
- Each test uses own `tmp_path` directory
- No shared state between tests
- No side effects in global filesystem

**Specific Test Names:**
- Test name describes what is being validated
- `test_run_check_fails_on_missing_proposal_terms` is clearer than `test_check_failure`
- Pattern: `test_<function>_<scenario>`

## Running Tests

**All Tests:**
```bash
pytest -q
```

**By Stage:**
```bash
pytest -q tests/test_skill_canonicalize.py tests/test_skill_check.py tests/test_skill_verify.py
```

**Single Test:**
```bash
pytest -q tests/test_skill_check.py::test_run_check_fails_on_missing_proposal_terms -v
```

**With Output:**
```bash
pytest -q tests/ -v  # Show test names
pytest -q tests/ -ra # Show summary of all outcomes
```

---

*Testing analysis: 2026-03-27*
