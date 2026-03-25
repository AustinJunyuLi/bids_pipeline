# Testing Patterns

**Analysis Date:** 2026-03-25

## Test Framework

**Runner:**
- `pytest`
- Config: `pytest.ini` in the repo root sets `pythonpath = .`, `testpaths = tests`, and `addopts = -ra`

**Assertion style:**
- Pytest built-in assertions
- Common helpers: `pytest.raises`, `monkeypatch`, and `tmp_path`

**Run Commands:**
```bash
pytest -q
pytest -q tests/test_skill_raw_stage.py tests/test_skill_preprocess_source.py
pytest -q tests/test_skill_verify.py tests/test_skill_coverage.py
pytest -q tests/test_benchmark_separation_policy.py tests/test_skill_mirror_sync.py
```

## Test File Organization

**Location:**
- All tracked tests live in the top-level `tests/` directory
- Test files are separated from source files rather than colocated with modules

**Naming:**
- Deterministic stage tests use `test_skill_<stage>.py`
- Policy tests use descriptive names such as `test_benchmark_separation_policy.py`
- Repo hygiene checks use names like `test_skill_mirror_sync.py`

**Structure:**
```text
tests/
|-- test_skill_raw_stage.py
|-- test_skill_preprocess_source.py
|-- test_skill_canonicalize.py
|-- test_skill_verify.py
|-- test_skill_coverage.py
|-- test_skill_enrich_core.py
|-- test_skill_pipeline.py
|-- test_benchmark_separation_policy.py
`-- test_skill_mirror_sync.py
```

## Test Structure

**Suite organization:**
- Tests are usually plain functions, not nested `class Test...` suites
- Many files define small helper builders near the top of the file instead of shared fixtures
- Complex stage tests build temp directories and write minimal JSON payloads directly

**Patterns:**
- Use `tmp_path` to build isolated `raw/` and `data/` trees
- Call stage functions directly rather than shelling out to the CLI when possible
- Assert both returned summaries and on-disk artifact contents

## Mocking

**Framework:**
- Pytest `monkeypatch` plus function injection

**Patterns:**
- Replace SEC identity setup in `skill_pipeline/raw/stage.py` with a lambda during tests
- Inject `fetch_contents_fn` or `get_filing_fn` into raw-fetch helpers instead of hitting live EDGAR
- Use inline lambdas or simple local classes rather than large mocking frameworks

**What gets mocked:**
- EDGAR network access
- Environment variables
- File-system roots via `tmp_path`

**What usually stays real:**
- Pydantic validation
- JSON serialization and file writes
- Deterministic stage logic

## Fixtures and Factories

**Test data style:**
- Inline dict payloads are common for actors, events, verification logs, and coverage summaries
- Small helper constructors such as `_seed()` and `_write_shared_inputs()` are preferred over a large shared fixture library

**Location:**
- Helpers are usually local to the test module where they are used
- There is no tracked global `conftest.py`

## Coverage Expectations

**Requirements:**
- No numeric coverage threshold is tracked
- The repo relies on targeted regression coverage for each stage boundary and on policy tests for benchmark separation and skill-mirror drift

**Verification philosophy:**
- Add a focused regression test for every bug or contract change
- Prefer artifact-level assertions to generic smoke tests

## Test Types

**Unit-ish stage tests:**
- Exercise one stage in isolation with temp artifacts
- Examples: `tests/test_skill_raw_stage.py`, `tests/test_skill_preprocess_source.py`

**Cross-stage integration tests:**
- Exercise multiple artifacts or stage assumptions together
- Examples: `tests/test_skill_pipeline.py`, `tests/test_skill_enrich_core.py`

**Policy tests:**
- Enforce repo boundaries and workflow rules
- Examples: `tests/test_benchmark_separation_policy.py`, `tests/test_skill_mirror_sync.py`

## Common Patterns

**Error testing:**
- `pytest.raises(..., match="...")` is heavily used for fail-fast behavior

**Filesystem testing:**
- Tests write minimal discovery, registry, chronology, and extract artifacts under `tmp_path`
- Assertions frequently inspect generated JSON files directly after the stage runs

**Gaps to remember:**
- There is no tracked CI workflow yet
- The skill-driven LLM stages are documented and boundary-tested, but the deterministic pytest suite does not run those stages end to end

---

*Testing analysis: 2026-03-25*
*Update when test patterns change*
