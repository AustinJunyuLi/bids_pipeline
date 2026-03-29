# Rerun Log: saks

- Start time: 2026-03-29T14:39:14+01:00
- Deal: saks
- Workflow: canonical /deal-agent route through db-export

## Run Log


### saks: raw-fetch

Command: skill-pipeline raw-fetch --deal saks
{
  "deal_slug": "saks",
  "cik": "812900",
  "primary_candidate_count": 1,
  "supplementary_candidate_count": 0,
  "frozen_count": 1,
  "discovery_path": "raw/saks/discovery.json",
  "document_registry_path": "raw/saks/document_registry.json"
}

### saks: preprocess-source

Command: skill-pipeline preprocess-source --deal saks
{
  "selected_document_id": "0001193125-13-390275",
  "selected_accession_number": "0001193125-13-390275",
  "confidence": "high",
  "confidence_factors": {
    "section_length": 240,
    "score_gap": 4033,
    "ambiguity_risk": "low",
    "coverage_assessment": "full"
  },
  "block_count": 65,
  "evidence_count": 965,
  "candidate_count": 1,
  "top_primary_candidate_id": "0001193125-13-390275",
  "scanned_document_count": 1
}

### saks: compose-prompts-actors

Command: skill-pipeline compose-prompts --deal saks --mode actors
{
  "schema_version": "2.0.0",
  "artifact_type": "prompt_packet_manifest",
  "created_at": "2026-03-29T13:40:31.601495Z",
  "pipeline_version": "0.1.0",
  "run_id": "compose-a71448d2",
  "deal_slug": "saks",
  "source_accession_number": "0001193125-13-390275",
  "packets": [
    {
      "packet_id": "actors-w0",
      "packet_family": "actors",
      "chunk_mode": "single_pass",
      "window_id": "w0",
      "prefix_path": "/home/austinli/Projects/bids_pipeline/data/skill/saks/prompt/packets/actors-w0/prefix.md",
      "body_path": "/home/austinli/Projects/bids_pipeline/data/skill/saks/prompt/packets/actors-w0/body.md",
      "rendered_path": "/home/austinli/Projects/bids_pipeline/data/skill/saks/prompt/packets/actors-w0/rendered.md",
      "evidence_ids": [
        "0001193125-13-390275:E0270",
        "0001193125-13-390275:E0271",
        "0001193125-13-390275:E0272",
        "0001193125-13-390275:E0273",
        "0001193125-13-390275:E0274",
        "0001193125-13-390275:E0275",
        "0001193125-13-390275:E0276",
        "0001193125-13-390275:E0277",
        "0001193125-13-390275:E0278",
        "0001193125-13-390275:E0279",
        "0001193125-13-390275:E0280",
        "0001193125-13-390275:E0281",
        "0001193125-13-390275:E0282",
        "0001193125-13-390275:E0283",
        "0001193125-13-390275:E0284",
        "0001193125-13-390275:E0285",
        "0001193125-13-390275:E0286",
        "0001193125-13-390275:E0287",
        "0001193125-13-390275:E0288",
        "0001193125-13-390275:E0289",
        "0001193125-13-390275:E0290",
        "0001193125-13-390275:E0291",
        "0001193125-13-390275:E0292",
        "0001193125-13-390275:E0293",
        "0001193125-13-390275:E0294",
        "0001193125-13-390275:E0295",
        "0001193125-13-390275:E0296",
        "0001193125-13-390275:E0297",
        "0001193125-13-390275:E0298",
        "0001193125-13-390275:E0299",
        "0001193125-13-390275:E0300",
        "0001193125-13-390275:E0301",
        "0001193125-13-390275:E0302",
        "0001193125-13-390275:E0303",
        "0001193125-13-390275:E0304",
        "0001193125-13-390275:E0305",
        "0001193125-13-390275:E0306",
        "0001193125-13-390275:E0307",
        "0001193125-13-390275:E0308",
        "0001193125-13-390275:E0309",
        "0001193125-13-390275:E0310",
        "0001193125-13-390275:E0311",
        "0001193125-13-390275:E0312",
        "0001193125-13-390275:E0313",
        "0001193125-13-390275:E0314",
        "0001193125-13-390275:E0315",
        "0001193125-13-390275:E0316",
        "0001193125-13-390275:E0317",
        "0001193125-13-390275:E0318",
        "0001193125-13-390275:E0319",
        "0001193125-13-390275:E0320",
        "0001193125-13-390275:E0321",
        "0001193125-13-390275:E0322",
        "0001193125-13-390275:E0323",
        "0001193125-13-390275:E0324",
        "0001193125-13-390275:E0325",
        "0001193125-13-390275:E0326",
        "0001193125-13-390275:E0327",
        "0001193125-13-390275:E0328",
        "0001193125-13-390275:E0329",
        "0001193125-13-390275:E0330",
        "0001193125-13-390275:E0331",
        "0001193125-13-390275:E0332",
        "0001193125-13-390275:E0333",
        "0001193125-13-390275:E0334",
        "0001193125-13-390275:E0335",
        "0001193125-13-390275:E0336",
        "0001193125-13-390275:E0337",
        "0001193125-13-390275:E0338",
        "0001193125-13-390275:E0339",
        "0001193125-13-390275:E0340",
        "0001193125-13-390275:E0341",
        "0001193125-13-390275:E0342",
        "0001193125-13-390275:E0343",
        "0001193125-13-390275:E0344",
        "0001193125-13-390275:E0345",
        "0001193125-13-390275:E0346",
        "0001193125-13-390275:E0347",
        "0001193125-13-390275:E0348",
        "0001193125-13-390275:E0349",
        "0001193125-13-390275:E0350",
        "0001193125-13-390275:E0351",
        "0001193125-13-390275:E0352",
        "0001193125-13-390275:E0353",
        "0001193125-13-390275:E0354",
        "0001193125-13-390275:E0355",
        "0001193125-13-390275:E0356",
        "0001193125-13-390275:E0357",
        "0001193125-13-390275:E0358",
        "0001193125-13-390275:E0359",
        "0001193125-13-390275:E0360",
        "0001193125-13-390275:E0361",
        "0001193125-13-390275:E0362",
        "0001193125-13-390275:E0363",
        "0001193125-13-390275:E0364",
        "0001193125-13-390275:E0365",
        "0001193125-13-390275:E0366",
        "0001193125-13-390275:E0367",
        "0001193125-13-390275:E0368",
        "0001193125-13-390275:E0369",
        "0001193125-13-390275:E0370",
        "0001193125-13-390275:E0371",
        "0001193125-13-390275:E0372",
        "0001193125-13-390275:E0373",
        "0001193125-13-390275:E0374",
        "0001193125-13-390275:E0375",
        "0001193125-13-390275:E0376",
        "0001193125-13-390275:E0377",
        "0001193125-13-390275:E0378",
        "0001193125-13-390275:E0379",
        "0001193125-13-390275:E0380",
        "0001193125-13-390275:E0381",
        "0001193125-13-390275:E0382",
        "0001193125-13-390275:E0383",
        "0001193125-13-390275:E0384",
        "0001193125-13-390275:E0385",
        "0001193125-13-390275:E0386",
        "0001193125-13-390275:E0387",
        "0001193125-13-390275:E0388",
        "0001193125-13-390275:E0389",
        "0001193125-13-390275:E0390",
        "0001193125-13-390275:E0391",
        "0001193125-13-390275:E0392",
        "0001193125-13-390275:E0393",
        "0001193125-13-390275:E0394",
        "0001193125-13-390275:E0395",
        "0001193125-13-390275:E0396"
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
    "source_blocks=65",
    "source_evidence_items=965",
    "chunk_windows=1",
    "complexity=simple"
  ]
}

### saks: validate-actors

Command: python scripts/validate_prompt_packets.py --deal saks --expect-sections
PASS: All prompt packets valid for saks.

### saks: extraction-worker-handoff

- The earlier full-flow worker was stopped for orchestration/throughput reasons before any intended `saks` extract artifacts were accepted as checkpoint state.
- This focused extraction worker is taking over from the validated actor-packet checkpoint and will stop after writing schema-valid `actors_raw.json` and `events_raw.json`.

### saks: compose-prompts-events

Command: skill-pipeline compose-prompts --deal saks --mode events
{
  "schema_version": "2.0.0",
  "artifact_type": "prompt_packet_manifest",
  "created_at": "2026-03-29T13:59:07.435695Z",
  "pipeline_version": "0.1.0",
  "run_id": "compose-2d0684a2",
  "deal_slug": "saks",
  "source_accession_number": "0001193125-13-390275",
  "packets": [
    {
      "packet_id": "events-w0",
      "packet_family": "events",
      "chunk_mode": "single_pass",
      "window_id": "w0",
      "prefix_path": "/home/austinli/Projects/bids_pipeline/data/skill/saks/prompt/packets/events-w0/prefix.md",
      "body_path": "/home/austinli/Projects/bids_pipeline/data/skill/saks/prompt/packets/events-w0/body.md",
      "rendered_path": "/home/austinli/Projects/bids_pipeline/data/skill/saks/prompt/packets/events-w0/rendered.md",
      "evidence_ids": [
        "0001193125-13-390275:E0270",
        "0001193125-13-390275:E0271",
        "0001193125-13-390275:E0272",
        "0001193125-13-390275:E0273",
        "0001193125-13-390275:E0274",
        "0001193125-13-390275:E0275",
        "0001193125-13-390275:E0276",
        "0001193125-13-390275:E0277",
        "0001193125-13-390275:E0278",
        "0001193125-13-390275:E0279",
        "0001193125-13-390275:E0280",
        "0001193125-13-390275:E0281",
        "0001193125-13-390275:E0282",
        "0001193125-13-390275:E0283",
        "0001193125-13-390275:E0284",
        "0001193125-13-390275:E0285",
        "0001193125-13-390275:E0286",
        "0001193125-13-390275:E0287",
        "0001193125-13-390275:E0288",
        "0001193125-13-390275:E0289",
        "0001193125-13-390275:E0290",
        "0001193125-13-390275:E0291",
        "0001193125-13-390275:E0292",
        "0001193125-13-390275:E0293",
        "0001193125-13-390275:E0294",
        "0001193125-13-390275:E0295",
        "0001193125-13-390275:E0296",
        "0001193125-13-390275:E0297",
        "0001193125-13-390275:E0298",
        "0001193125-13-390275:E0299",
        "0001193125-13-390275:E0300",
        "0001193125-13-390275:E0301",
        "0001193125-13-390275:E0302",
        "0001193125-13-390275:E0303",
        "0001193125-13-390275:E0304",
        "0001193125-13-390275:E0305",
        "0001193125-13-390275:E0306",
        "0001193125-13-390275:E0307",
        "0001193125-13-390275:E0308",
        "0001193125-13-390275:E0309",
        "0001193125-13-390275:E0310",
        "0001193125-13-390275:E0311",
        "0001193125-13-390275:E0312",
        "0001193125-13-390275:E0313",
        "0001193125-13-390275:E0314",
        "0001193125-13-390275:E0315",
        "0001193125-13-390275:E0316",
        "0001193125-13-390275:E0317",
        "0001193125-13-390275:E0318",
        "0001193125-13-390275:E0319",
        "0001193125-13-390275:E0320",
        "0001193125-13-390275:E0321",
        "0001193125-13-390275:E0322",
        "0001193125-13-390275:E0323",
        "0001193125-13-390275:E0324",
        "0001193125-13-390275:E0325",
        "0001193125-13-390275:E0326",
        "0001193125-13-390275:E0327",
        "0001193125-13-390275:E0328",
        "0001193125-13-390275:E0329",
        "0001193125-13-390275:E0330",
        "0001193125-13-390275:E0331",
        "0001193125-13-390275:E0332",
        "0001193125-13-390275:E0333",
        "0001193125-13-390275:E0334",
        "0001193125-13-390275:E0335",
        "0001193125-13-390275:E0336",
        "0001193125-13-390275:E0337",
        "0001193125-13-390275:E0338",
        "0001193125-13-390275:E0339",
        "0001193125-13-390275:E0340",
        "0001193125-13-390275:E0341",
        "0001193125-13-390275:E0342",
        "0001193125-13-390275:E0343",
        "0001193125-13-390275:E0344",
        "0001193125-13-390275:E0345",
        "0001193125-13-390275:E0346",
        "0001193125-13-390275:E0347",
        "0001193125-13-390275:E0348",
        "0001193125-13-390275:E0349",
        "0001193125-13-390275:E0350",
        "0001193125-13-390275:E0351",
        "0001193125-13-390275:E0352",
        "0001193125-13-390275:E0353",
        "0001193125-13-390275:E0354",
        "0001193125-13-390275:E0355",
        "0001193125-13-390275:E0356",
        "0001193125-13-390275:E0357",
        "0001193125-13-390275:E0358",
        "0001193125-13-390275:E0359",
        "0001193125-13-390275:E0360",
        "0001193125-13-390275:E0361",
        "0001193125-13-390275:E0362",
        "0001193125-13-390275:E0363",
        "0001193125-13-390275:E0364",
        "0001193125-13-390275:E0365",
        "0001193125-13-390275:E0366",
        "0001193125-13-390275:E0367",
        "0001193125-13-390275:E0368",
        "0001193125-13-390275:E0369",
        "0001193125-13-390275:E0370",
        "0001193125-13-390275:E0371",
        "0001193125-13-390275:E0372",
        "0001193125-13-390275:E0373",
        "0001193125-13-390275:E0374",
        "0001193125-13-390275:E0375",
        "0001193125-13-390275:E0376",
        "0001193125-13-390275:E0377",
        "0001193125-13-390275:E0378",
        "0001193125-13-390275:E0379",
        "0001193125-13-390275:E0380",
        "0001193125-13-390275:E0381",
        "0001193125-13-390275:E0382",
        "0001193125-13-390275:E0383",
        "0001193125-13-390275:E0384",
        "0001193125-13-390275:E0385",
        "0001193125-13-390275:E0386",
        "0001193125-13-390275:E0387",
        "0001193125-13-390275:E0388",
        "0001193125-13-390275:E0389",
        "0001193125-13-390275:E0390",
        "0001193125-13-390275:E0391",
        "0001193125-13-390275:E0392",
        "0001193125-13-390275:E0393",
        "0001193125-13-390275:E0394",
        "0001193125-13-390275:E0395",
        "0001193125-13-390275:E0396"
      ],
      "actor_roster_source_path": "/home/austinli/Projects/bids_pipeline/data/skill/saks/extract/actors_raw.json"
    }
  ],
  "asset_files": [
    "/home/austinli/Projects/bids_pipeline/skill_pipeline/prompt_assets/events_prefix.md",
    "/home/austinli/Projects/bids_pipeline/skill_pipeline/prompt_assets/event_examples.md"
  ],
  "notes": [
    "mode=events",
    "chunk_budget=6000",
    "routing=auto",
    "effective_budget=single-pass",
    "source_blocks=65",
    "source_evidence_items=965",
    "chunk_windows=1",
    "complexity=simple"
  ]
}

### saks: validate-events

Command: python scripts/validate_prompt_packets.py --deal saks --expect-sections
PASS: All prompt packets valid for saks.

### saks: write-events

- Timestamp: 2026-03-29T15:14:00+01:00
- Action: Wrote filing-grounded quote-first `data/skill/saks/extract/events_raw.json` from the validated `events-w0` packet and current source blocks.
- Validation: `RawSkillEventsArtifact` schema pass (`events=19`, `quotes=19`).

### saks: quote-verification-fix

- `verify` initially failed on `span_0019` / `evt_007` / `B024`.
- Root cause: the stored anchor text was not an exact contiguous excerpt from the filing block.
- Fix applied: shortened the anchor in `data/skill/saks/extract/spans.json` to the exact contiguous text `Sponsor A and Sponsor E, on the other hand, were each preliminarily prepared to proceed`.
- Result: `verify` passed.

### saks: coverage-wall-and-shared-fix

- `coverage` initially failed on contextual NDA cues at `B025` and `B042`.
- Root cause:
  - `B025` referenced already-executed confidentiality agreements inside a board-process sentence;
  - `B042` described Saks' separate Company B diligence track, not a bidder-to-Saks NDA event.
- Shared-code fix applied in `skill_pipeline/coverage.py`:
  - ignore prior-state confidentiality-agreement references such as `which had executed a confidentiality agreement`;
  - ignore confidentiality-agreement language used solely for the target to conduct diligence on another company.
- Regression tests added in `tests/test_skill_coverage.py`.
- Result:
  - `coverage` passed at blocker/error level;
  - `gates` passed;
  - `enrich-core` passed.

### saks: enrichment-and-export

- Wrote filing-grounded `data/skill/saks/enrich/enrichment.json` after deterministic repair work cleared.
- `uv run skill-pipeline db-load --deal saks` passed.
- `uv run skill-pipeline db-export --deal saks` passed.
- Output written: `data/skill/saks/export/deal_events.csv` with 21 lines including header.
