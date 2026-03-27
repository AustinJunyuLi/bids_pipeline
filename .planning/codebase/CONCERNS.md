# Codebase Concerns

**Analysis Date:** 2026-03-27

## Tech Debt

**EdgarTools Deprecation Risk (High Priority):**
- Issue: `pyproject.toml` pins `edgartools>=5.23`, but CLAUDE.md documents that v6 emits deprecation warnings. The live fetch path will break on v6 release.
- Files: `pyproject.toml`, `skill_pipeline/raw/fetch.py`
- Impact: All deals using `skill-pipeline raw-fetch` will fail silently with warnings; actual v6 breaking changes will cause crashes.
- Fix approach: Pin `edgartools<6.0` and plan migration to v6 API before v6 release becomes unavoidable.

**Broad Exception Handler in Enrich Core:**
- Issue: `skill_pipeline/enrich_core.py` line 361-362 has bare `except Exception:` that swallows all errors and only invalidates outputs, masking upstream failures.
- Files: `skill_pipeline/enrich_core.py:361-362`
- Impact: Silent corruption possible if deterministic enrichment partially fails; caller gets unclear exit code without error context.
- Fix approach: Replace with specific exception types or log the exception before re-raising.

**Silent Pass in CLI:**
- Issue: `skill_pipeline/cli.py:219` has bare `pass` in the main command dispatcher's fallback. If an unknown command is passed, help is printed but exit code is 1 without logging why.
- Files: `skill_pipeline/cli.py:219`
- Impact: Caller receives unhelpful failure signal; hard to debug CLI misuse.
- Fix approach: Remove the bare pass, add explicit logging, or raise an exception before returning 1.

## Known Bugs

**Quote Resolution Edge Case in Character Position Calculation:**
- Symptoms: Off-by-one errors in `_segment_offset_to_line_position` may occur when char_offset falls exactly at line boundary or end-of-file.
- Files: `skill_pipeline/provenance.py:103-118`
- Trigger: Anchor text at line boundary or EOF in provenance resolution.
- Cause: Line 114-116 handles the equality case (`char_offset == running`) after a length check, but final fallback on line 118 may return incorrect char position for the last line.
- Workaround: Verify span records manually for edge cases.

**Span Registry Sidecar Requirement Not Enforced Early:**
- Symptoms: `canonicalize` converts legacy artifacts to canonical form but does not validate that `spans.json` exists immediately after writing.
- Files: `skill_pipeline/canonicalize.py:280-290`
- Trigger: Canonicalization succeeds but `spans.json` missing.
- Cause: No inline check after `_write_spans_registry()` at line 291.
- Workaround: Always run `check` immediately after `canonicalize`.

## Security Considerations

**No Explicit Input Validation on File Paths:**
- Risk: Path traversal vulnerabilities in `_load_document_lines()` and similar functions if deal_slug or document_id are user-controlled and not validated.
- Files: `skill_pipeline/canonicalize.py:25-34`, `skill_pipeline/verify.py:29-43`
- Current mitigation: Deal slugs are from `data/seeds.csv` hardcoded list; document paths derived from fixed raw filing directory.
- Recommendations: Add explicit path validation or assertions that resolved paths stay within expected subtree.

**Environment Variable Secrets Not Protected:**
- Risk: LLM API keys (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) may be logged accidentally or exposed in error traces.
- Files: `skill_pipeline/config.py` (implicit env var access), CLI error paths
- Current mitigation: None observed.
- Recommendations: Mask API keys in error messages and logs; use `getpass`-style secrets where possible.

## Performance Bottlenecks

**Inefficient Span Lookup in Enrich Core:**
- Problem: `_populate_invited_from_count_assertions` (line 282-342) rebuilds `name_to_id` lookup for every invocation and scans all events in a nested loop.
- Files: `skill_pipeline/enrich_core.py:282-342`
- Cause: O(n*m) actor-event matching without caching.
- Improvement path: Build lookup once; use set-based matching instead of substring search.

**No Memoization of Chronology Selection:**
- Problem: `skill_pipeline/source/locate.py:select_chronology()` can be called multiple times per deal; performs full regex scanning and scoring each time.
- Files: `skill_pipeline/source/locate.py:70-100`
- Cause: No caching of parsed candidates.
- Improvement path: Cache results keyed by (document_id, filing_type, file hash).

## Fragile Areas

**Provenance Resolution Anchor Matching:**
- Files: `skill_pipeline/provenance.py:16-100`, `skill_pipeline/normalize/quotes.py`
- Why fragile: Multi-step quote normalization with fallback expansion is sensitive to line boundary offsets and character encoding. If normalization rules change, all historical spans may need recomputation.
- Safe modification: Add integration tests for edge cases (quotes at line start/end, multi-byte characters, control characters). Test against real filing samples before deploying.
- Test coverage: `tests/test_skill_provenance.py` exists but may not cover all normalization edge cases.

**Canonicalization Deduplication Logic:**
- Files: `skill_pipeline/canonicalize.py:240-298`
- Why fragile: Event deduplication compares event_type, actor_ids, and dates but not evidence. Semantically different events may be incorrectly merged if dates happen to align.
- Safe modification: Require changes to pass full test suite including regression tests on real deals (imprivata, mac-gray, etc.). Add explicit handling for event properties that should disable deduplication.
- Test coverage: `tests/test_skill_canonicalize.py` has some coverage but edge cases around date precision may not be tested.

**NDA Gate Enforcement:**
- Files: `skill_pipeline/canonicalize.py:310-340`
- Why fragile: Drop events are filtered if actor never had prior NDA. Logic depends on event ordering and correct actor_id matching. If actor_ids are corrupted or mismatched, drops may be silently removed.
- Safe modification: Audit all drop filtering decisions with explicit logging. Add pre-canonicalize validation that all actor IDs in events exist in actors roster.
- Test coverage: No explicit test for NDA gate logic visibility.

## Scaling Limits

**In-Memory Event and Actor Lists:**
- Current capacity: All deals fit in memory; typical deal has <500 actors and <5000 events.
- Limit: No pagination or streaming in any stage; entire artifact set loaded into memory.
- Scaling path: For deals with >50k events, would need to introduce chunked processing or streaming JSON parsing.

**Linearly Scanning Document Text for Provenance:**
- Current capacity: Filing text up to 10MB per document.
- Limit: `resolve_text_span()` reconstructs quoted text by reading full line ranges from memory.
- Scaling path: For filings >50MB, would need mmap-based or streaming span resolution.

## Dependencies at Risk

**Pydantic v2 Strict Mode:**
- Risk: `ConfigDict(extra="forbid")` on all SkillModel subclasses will reject unknown fields. If LLM-produced extract artifacts include unexpected keys, parsing fails hard.
- Files: `skill_pipeline/models.py:15`
- Impact: Agent-produced artifacts incompatible with new schema version will crash entire pipeline.
- Migration plan: Add a compatibility shim or lenient parsing mode that logs unknown fields before validation.

**OpenPyXL Optional:**
- Risk: `openpyxl>=3.1` is a dependency but not used in core pipeline; may be vestigial from historical export phases.
- Files: `pyproject.toml:14`
- Impact: Adds ~5MB to install; unclear if still needed.
- Migration plan: Remove from `pyproject.toml` if export-csv stage doesn't generate `.xlsx` output.

## Missing Critical Features

**No Checksum Validation on Immutable Files:**
- Problem: Raw filing `.txt` files are immutable but checksums not recorded. If file is silently corrupted on disk, detection is difficult.
- Blocks: Audit trail and recovery procedures.
- Recommendation: Write SHA256 sidecar for each raw filing and validate on load.

**No Transaction-Style Rollback on Pipeline Failure:**
- Problem: If a middle stage fails (e.g., verify), upstream outputs remain; no way to atomically roll back without manual intervention.
- Blocks: Safe re-running of failed deals.
- Recommendation: Add an optional `--cleanup-on-fail` flag or transaction wrapper.

**Insufficient Logging in Deterministic Stages:**
- Problem: `check`, `verify`, `coverage`, `enrich-core` produce JSON reports but minimal logs. Debugging why a gate failed requires reading JSON carefully.
- Blocks: Rapid troubleshooting.
- Recommendation: Add structured logging (level INFO for summaries, DEBUG for per-item details) to all stages.

## Test Coverage Gaps

**Provenance Span Resolution Edge Cases:**
- What's not tested: Off-by-one boundaries, multi-byte UTF-8 characters in quotes, quotes split across normalization collapsing.
- Files: `skill_pipeline/provenance.py`, `skill_pipeline/normalize/quotes.py`
- Risk: Silent corruption of char positions in SpanRecord; hard to detect in downstream use.
- Priority: High

**Canonicalization Cross-Deal Regression:**
- What's not tested: Full end-to-end canonicalize on all 9 active deals (imprivata, mac-gray, medivation, penford, petsmart-inc, providence-worcester, saks, stec, zep). Currently only local unit tests.
- Files: `skill_pipeline/canonicalize.py`, `tests/test_skill_canonicalize.py`
- Risk: Silent event deduplication or NDA filtering errors only visible on real artifacts.
- Priority: High

**Enrich Core Round Pairing Logic:**
- What's not tested: Complex `_pair_rounds()` logic with multiple restarts and selective bidder scenarios not exercised.
- Files: `skill_pipeline/enrich_core.py:68-100`
- Risk: Incorrect round boundaries or active bidder counts on deals with complex bid sequences.
- Priority: Medium

**CLI Error Path Handling:**
- What's not tested: Malformed JSON in artifacts, missing files at runtime, env var misconfiguration.
- Files: `skill_pipeline/cli.py`
- Risk: Unhelpful error messages on real failures.
- Priority: Medium

---

*Concerns audit: 2026-03-27*
