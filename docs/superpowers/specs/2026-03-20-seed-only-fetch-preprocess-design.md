# Seed-Only Fetch And Preprocess Design

**Status:** DRAFT
**Date:** 2026-03-20
**Confidence:** 9/10

## Goal

Make fetch and preprocess use one explicit, approved SEC filing per deal so extraction artifacts stay bounded to a single known source.

## Context

The current pipeline still performs broad EDGAR discovery in `raw-fetch` and `source-discover`. It searches across multiple filing types, fetches multiple candidate filings, and then preprocess scans evidence across the fetched set. That widens the factual boundary beyond the filing explicitly approved for a deal.

For the 9 `is_reference=true` deals, the approved filing in `data/seeds.csv.primary_url` matches `example/deal_details_Alex_2026.xlsx` exactly, one URL per deal. The user has decided to apply the same repo-wide rule to all deals: `data/seeds.csv.primary_url` is the approved filing source for fetch and preprocess.

The design should stay simple for now. We are not designing multi-file allowlists in this spec. If bounded multi-file support is needed later, it should be designed separately.

## Decision Summary

1. `data/seeds.csv.primary_url` is the source of truth for fetch for every deal.
2. The CSV field `primary_url` maps to `SeedDeal.primary_url_seed` inside the pipeline; both names refer to the same approved filing input.
3. `raw-fetch` must not perform open-ended EDGAR search by company name or filing form.
4. `raw-fetch` must extract the accession number from `primary_url` and fetch that filing through `edgar.get_by_accession_number(...)`.
5. If the seed URL is missing, malformed, or the accession cannot be fetched through `edgar`, the pipeline fails closed.
6. `preprocess-source` must only localize chronology, build blocks, and scan evidence from the single fetched filing.
7. Supplementary evidence scanning and supplementary snippet generation are removed from the fetch/preprocess path.

## Chosen Approach

Use a strict single-seed filing design while preserving the existing artifact envelope shape where that avoids unnecessary downstream churn.

This means the pipeline still writes `discovery.json` and `document_registry.json`, but those artifacts become deterministic descriptions of one approved filing rather than the output of EDGAR discovery. Keeping those files avoids unnecessary interface breakage for the rest of the pipeline while still tightening the true source boundary.

## Fetch Design

### Policy

- Only the filing at `data/seeds.csv.primary_url` is approved for fetch.
- No unrestricted search by `Company.get_filings(...)`.
- No form-family candidate expansion.
- No supplementary filing fetch.
- If `deal_slug` does not exist in `data/seeds.csv`, fail immediately with a precise error.

### Behavioral changes

- `skill-pipeline source-discover --deal <slug>` becomes a deterministic report of the approved seed filing rather than a search command.
- `source-discover` must not require EDGAR access, `EDGAR_IDENTITY`, or network calls. It is a seed-parse command only.
- `skill-pipeline raw-fetch --deal <slug>` builds exactly one `FilingCandidate` from `primary_url`, fetches exactly one filing by accession, and writes a registry containing exactly one document.
- The fetched filing should still be frozen into `raw/<slug>/filings/` as today.
- `raw-fetch` keeps the current identity lookup behavior for live EDGAR access: `PIPELINE_SEC_IDENTITY`, then `SEC_IDENTITY`, then `EDGAR_IDENTITY`.

### Failure policy

- Missing `primary_url`: raise a precise error.
- Unparseable accession from `primary_url`: raise a precise error.
- Accession parsing must be deterministic. The extracted accession must normalize to the dashed SEC form `##########-##-######`; if not, fail.
- Accepted seed URLs are standard SEC Archives filing URLs that contain one unambiguous accession for the filing. If the URL shape is non-standard or ambiguous, fail.
- `edgar.get_by_accession_number(...)` missing or returning no text: raise a precise error.
- No HTTP fallback to the SEC webpage URL.

### Filing semantics

The single approved filing is defined as the accession identified by `primary_url` and retrieved through `edgar.get_by_accession_number(...)`. The frozen artifact boundary is whatever filing text and HTML that accession-based EDGAR retrieval returns. If EDGAR cannot provide usable filing text for that accession, the pipeline fails; it does not switch to webpage scraping.

## Preprocess Design

### Policy

- Preprocess operates on the one fetched filing only.
- Chronology localization is performed on that filing only.
- Chronology blocks are built from that filing only.
- Evidence items are scanned from that filing only.

### Behavioral changes

- `preprocess-source` should expect exactly one usable primary filing in the raw registry under the new policy.
- The normative single-file invariant is:
  - `len(discovery.primary_candidates) == 1`
  - `len(discovery.supplementary_candidates) == 0`
  - `len(document_registry.documents) == 1`
- If either invariant is violated, preprocess should fail instead of choosing silently.
- `discovery.json` and `document_registry.json` are the source of truth for this invariant. Extra orphan files under `raw/<slug>/filings/` are not part of the contract.
- Any candidate listed in `discovery.json` must have a matching frozen document in `document_registry.json`. Missing registry coverage is an error, not a skip path.
- `supplementary_snippets.jsonl` is no longer generated.
- `data/deals/<slug>/source/filings/` should still contain the selected filing copy for manual inspection and downstream debugging.

## Compatibility Boundary

Keep external artifact shapes where they are still useful:

- `raw/<slug>/discovery.json` still exists.
- `RawDiscoveryManifest.primary_candidates` contains one candidate.
- `RawDiscoveryManifest.supplementary_candidates` may remain as `[]` for compatibility.
- `raw/<slug>/document_registry.json` still exists and contains one document.

This preserves downstream expectations while changing the actual factual boundary to one approved filing.

## Files In Scope

### `skill_pipeline/cli.py`

- Change `source-discover` to emit the deterministic single-candidate manifest derived from the seed URL.
- Remove search-based wiring from `source-discover`.
- Make `source-discover` fully offline with respect to EDGAR.

### `skill_pipeline/raw/discover.py`

- Replace search-driven candidate collection with deterministic construction of one `FilingCandidate` from `SeedDeal.primary_url_seed`.
- Preserve the manifest model shape, but populate only one primary candidate and no supplementary candidates.

### `skill_pipeline/raw/stage.py`

- Remove company/form search from the fetch path.
- Keep EDGAR identity setup only for accession-based filing retrieval.
- Fetch exactly the seed-derived candidate.

### `skill_pipeline/fetch_utils.py`

- Make `fetch_filing_contents()` require accession-based EDGAR retrieval.
- Remove the SEC URL HTTP fallback path.
- Fail fast if EDGAR retrieval does not provide filing text.

### `skill_pipeline/preprocess/source.py`

- Enforce the single-file raw boundary.
- Localize chronology, build chronology blocks, and scan evidence from exactly one filing.
- Stop generating `supplementary_snippets.jsonl`.

### `skill_pipeline/source/discovery.py`

- Remove it from the active fetch path. Broader discovery logic should no longer be used by `source-discover` or `raw-fetch`.
- Full deletion is optional in this change; it can be follow-up cleanup if leaving it in place is less disruptive.

### `skill_pipeline/source/ranking.py`

- Keep only helpers still needed by the seed-only path.
- Search ranking logic no longer drives fetch behavior.
- Deleting unused ranking helpers is optional cleanup, not required for the policy change itself.

### Documentation

- Update `CLAUDE.md` to describe the new fetch boundary accurately.
- Update any skill docs that still imply broad discovery or supplementary snippet use in fetch/preprocess.

## What Stays Unchanged

- The downstream deterministic stages remain unchanged in purpose: `canonicalize`, `check`, `verify`, and `enrich-core`.
- Chronology localization itself is still done by `select_chronology(...)`; only the input filing set changes.
- Frozen raw filing text remains immutable once written.

## Risks And Tradeoffs

### Benefits

- Cleaner provenance for extraction artifacts.
- No leakage from nearby but unapproved filings.
- Simpler mental model: one deal, one approved filing, one raw source package.
- Easier debugging because all downstream facts trace back to one filing.

### Tradeoffs

- No automatic rescue if the approved filing is malformed or incomplete.
- Deals that genuinely require multiple approved filings are out of scope for this design.
- Some older search-oriented code may remain temporarily unused unless explicitly cleaned up in implementation.

These tradeoffs are intentional. The rule is correctness through explicit source control, not robustness through uncontrolled discovery.

## Future Extension Out Of Scope

If later needed, a separate design can support a small approved filing allowlist per deal:

- all filings must still come from an explicit human-approved list
- ranking/selection may only happen within that bounded list
- cross-file evidence may only come from that bounded list
- failure remains closed if the approved set is unusable

That is not part of this spec.

## Verification

1. `source-discover` returns exactly one primary candidate derived from `primary_url`.
2. `source-discover` does not require network access or `EDGAR_IDENTITY`.
3. `raw-fetch` fetches exactly one filing and does not perform form-based EDGAR search.
4. `raw-fetch` fails with a precise error on missing or malformed `primary_url`.
5. `raw-fetch` fails with a precise error if `edgar.get_by_accession_number(...)` cannot supply filing text.
6. `raw-fetch` writes `discovery.json` with one primary candidate and `document_registry.json` with one document.
7. `raw-fetch` preserves the current EDGAR identity env lookup order: `PIPELINE_SEC_IDENTITY`, `SEC_IDENTITY`, then `EDGAR_IDENTITY`.
8. `preprocess-source` fails if the single-file invariants are violated.
9. `preprocess-source` fails if any candidate listed in `discovery.json` lacks a matching registry document.
10. `preprocess-source` scans evidence from only the one fetched filing.
11. `supplementary_snippets.jsonl` is not generated.
12. Tests and any runtime readers that assumed supplementary snippets or broad discovery are updated to the new contract.
13. Downstream deterministic stages still consume the resulting source artifacts successfully.
