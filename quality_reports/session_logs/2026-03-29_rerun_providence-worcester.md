# Rerun Log: providence-worcester

- Start time: 2026-03-29T14:39:14+01:00
- Deal: providence-worcester
- Workflow: canonical /deal-agent route through db-export

## Run Log


### providence-worcester: raw-fetch

Command: skill-pipeline raw-fetch --deal providence-worcester
{
  "deal_slug": "providence-worcester",
  "cik": "831968",
  "primary_candidate_count": 1,
  "supplementary_candidate_count": 0,
  "frozen_count": 1,
  "discovery_path": "raw/providence-worcester/discovery.json",
  "document_registry_path": "raw/providence-worcester/document_registry.json"
}

### providence-worcester: preprocess-source

Command: skill-pipeline preprocess-source --deal providence-worcester
{
  "selected_document_id": "0001193125-16-713780",
  "selected_accession_number": "0001193125-16-713780",
  "confidence": "high",
  "confidence_factors": {
    "section_length": 192,
    "score_gap": 4785,
    "ambiguity_risk": "low",
    "coverage_assessment": "full"
  },
  "block_count": 41,
  "evidence_count": 1189,
  "candidate_count": 1,
  "top_primary_candidate_id": "0001193125-16-713780",
  "scanned_document_count": 1
}

### providence-worcester: compose-prompts-actors

Command: skill-pipeline compose-prompts --deal providence-worcester --mode actors
{
  "schema_version": "2.0.0",
  "artifact_type": "prompt_packet_manifest",
  "created_at": "2026-03-29T13:40:24.481891Z",
  "pipeline_version": "0.1.0",
  "run_id": "compose-b643f5cc",
  "deal_slug": "providence-worcester",
  "source_accession_number": "0001193125-16-713780",
  "packets": [
    {
      "packet_id": "actors-w0",
      "packet_family": "actors",
      "chunk_mode": "single_pass",
      "window_id": "w0",
      "prefix_path": "/home/austinli/Projects/bids_pipeline/data/skill/providence-worcester/prompt/packets/actors-w0/prefix.md",
      "body_path": "/home/austinli/Projects/bids_pipeline/data/skill/providence-worcester/prompt/packets/actors-w0/body.md",
      "rendered_path": "/home/austinli/Projects/bids_pipeline/data/skill/providence-worcester/prompt/packets/actors-w0/rendered.md",
      "evidence_ids": [
        "0001193125-16-713780:E0315",
        "0001193125-16-713780:E0316",
        "0001193125-16-713780:E0317",
        "0001193125-16-713780:E0318",
        "0001193125-16-713780:E0319",
        "0001193125-16-713780:E0320",
        "0001193125-16-713780:E0321",
        "0001193125-16-713780:E0322",
        "0001193125-16-713780:E0323",
        "0001193125-16-713780:E0324",
        "0001193125-16-713780:E0325",
        "0001193125-16-713780:E0326",
        "0001193125-16-713780:E0327",
        "0001193125-16-713780:E0328",
        "0001193125-16-713780:E0329",
        "0001193125-16-713780:E0330",
        "0001193125-16-713780:E0331",
        "0001193125-16-713780:E0332",
        "0001193125-16-713780:E0333",
        "0001193125-16-713780:E0334",
        "0001193125-16-713780:E0335",
        "0001193125-16-713780:E0336",
        "0001193125-16-713780:E0337",
        "0001193125-16-713780:E0338",
        "0001193125-16-713780:E0339",
        "0001193125-16-713780:E0340",
        "0001193125-16-713780:E0341",
        "0001193125-16-713780:E0342",
        "0001193125-16-713780:E0343",
        "0001193125-16-713780:E0344",
        "0001193125-16-713780:E0345",
        "0001193125-16-713780:E0346",
        "0001193125-16-713780:E0347",
        "0001193125-16-713780:E0348",
        "0001193125-16-713780:E0349",
        "0001193125-16-713780:E0350",
        "0001193125-16-713780:E0351",
        "0001193125-16-713780:E0352",
        "0001193125-16-713780:E0353",
        "0001193125-16-713780:E0354",
        "0001193125-16-713780:E0355",
        "0001193125-16-713780:E0356",
        "0001193125-16-713780:E0357",
        "0001193125-16-713780:E0358",
        "0001193125-16-713780:E0359",
        "0001193125-16-713780:E0360",
        "0001193125-16-713780:E0361",
        "0001193125-16-713780:E0362",
        "0001193125-16-713780:E0363",
        "0001193125-16-713780:E0364",
        "0001193125-16-713780:E0365",
        "0001193125-16-713780:E0366",
        "0001193125-16-713780:E0367",
        "0001193125-16-713780:E0368",
        "0001193125-16-713780:E0369",
        "0001193125-16-713780:E0370",
        "0001193125-16-713780:E0371",
        "0001193125-16-713780:E0372",
        "0001193125-16-713780:E0373",
        "0001193125-16-713780:E0374",
        "0001193125-16-713780:E0375",
        "0001193125-16-713780:E0376",
        "0001193125-16-713780:E0377",
        "0001193125-16-713780:E0378",
        "0001193125-16-713780:E0379",
        "0001193125-16-713780:E0380",
        "0001193125-16-713780:E0381",
        "0001193125-16-713780:E0382",
        "0001193125-16-713780:E0383",
        "0001193125-16-713780:E0384",
        "0001193125-16-713780:E0385",
        "0001193125-16-713780:E0386",
        "0001193125-16-713780:E0387",
        "0001193125-16-713780:E0388",
        "0001193125-16-713780:E0389",
        "0001193125-16-713780:E0390",
        "0001193125-16-713780:E0391",
        "0001193125-16-713780:E0392",
        "0001193125-16-713780:E0393",
        "0001193125-16-713780:E0394",
        "0001193125-16-713780:E0395",
        "0001193125-16-713780:E0396",
        "0001193125-16-713780:E0397",
        "0001193125-16-713780:E0398",
        "0001193125-16-713780:E0399",
        "0001193125-16-713780:E0400",
        "0001193125-16-713780:E0401",
        "0001193125-16-713780:E0402",
        "0001193125-16-713780:E0403",
        "0001193125-16-713780:E0404",
        "0001193125-16-713780:E0405",
        "0001193125-16-713780:E0406",
        "0001193125-16-713780:E0407",
        "0001193125-16-713780:E0408",
        "0001193125-16-713780:E0409",
        "0001193125-16-713780:E0410",
        "0001193125-16-713780:E0411",
        "0001193125-16-713780:E0412",
        "0001193125-16-713780:E0413",
        "0001193125-16-713780:E0414"
      ],
      "actor_roster_source_path": null
    }
  ],
  "asset_files": [
    "/home/austinli/Projects/bids_pipeline/skill_pipeline/prompt_assets/actors_prefix.md"
  ],
  "notes": [
    "mode=actors",
    "chunk_budget=6000",
    "routing=auto",
    "effective_budget=single-pass",
    "source_blocks=41",
    "source_evidence_items=1189",
    "chunk_windows=1",
    "complexity=simple"
  ]
}

### providence-worcester: validate-actors

Command: python scripts/validate_prompt_packets.py --deal providence-worcester --expect-sections
PASS: All prompt packets valid for providence-worcester.

### providence-worcester: main-thread extraction takeover

- Prior providence extraction attempts exited without a trusted final result file.
- Resuming from the validated actor-packet checkpoint only; scope limited to providence extract artifacts and this log.

### providence-worcester: actor-schema fix

- `compose-prompts --mode events` initially failed because raw `count_assertions` cannot include a `notes` field in this worktree.
- Removed only that extra field and retried.

### providence-worcester: compose-prompts-events

- `skill-pipeline compose-prompts --deal providence-worcester --mode events` passed.
- `python scripts/validate_prompt_packets.py --deal providence-worcester --expect-sections` passed.

### providence-worcester: extraction complete

- Wrote non-empty `actors_raw.json` and `events_raw.json`.
- Final counts: 11 actors, 20 events.

### providence-worcester: nda-count-wall-and-fix

- `check` initially failed because `nda_signed_strategic_buyers=11` and `nda_signed_financial_buyers=14` exceeded the grounded NDA-backed bidder count in the canonical extract.
- Filing-grounded extract fix:
  - added grouped bidder cohorts for the unnamed NDA signers in `actors_raw.json`;
  - expanded `evt_002` to represent the full strategic and financial NDA-signing cohorts described in `B007`.
- Shared-code fix applied in `skill_pipeline/check.py`:
  - grouped bidder actors now contribute `group_size` rather than a weight of `1` when reconciling NDA count assertions.
- Regression test added in `tests/test_skill_check.py`.
- Result: `check` passed.

### providence-worcester: verify-and-coverage-fixes

- `verify` then failed on `span_0005` because the stored committee anchor was stale and the span still carried `match_type=\"fuzzy\"`.
- Fix applied:
  - changed the anchor to `The Transaction Committee`;
  - normalized the span metadata to `match_type=\"exact\"`.
- `coverage` then failed on an uncovered withdrawal cue in `B027`.
- Fix applied:
  - added `evt_015` as a filing-grounded `drop` event for Party D using existing `span_0032`.
- Result:
  - `verify` passed;
  - `coverage` passed at blocker/error level;
  - `gates` passed;
  - `enrich-core` passed.

### providence-worcester: enrichment-and-export

- Wrote filing-grounded `data/skill/providence-worcester/enrich/enrichment.json` after the grouped-NDA and Party D drop repairs cleared.
- `uv run skill-pipeline db-load --deal providence-worcester` passed.
- `uv run skill-pipeline db-export --deal providence-worcester` passed.
- Output written: `data/skill/providence-worcester/export/deal_events.csv` with 20 lines including header.
