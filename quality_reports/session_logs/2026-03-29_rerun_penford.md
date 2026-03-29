# Rerun Log: penford

- Start time: 2026-03-29T14:39:14+01:00
- Deal: penford
- Workflow: canonical /deal-agent route through enrich-deal; stop before db-load/db-export

## Run Log

### penford: extraction-handoff

Command: manual orchestration handoff before local-agent extraction

- The earlier full-flow worker was stopped for orchestration/throughput reasons before any extraction artifacts were written.
- Confirmed absent at handoff:
  - `data/skill/penford/extract/actors_raw.json`
  - `data/skill/penford/extract/events_raw.json`
- This focused worker is taking over from the validated actor-packet checkpoint and will run only the extraction half through schema-valid `actors_raw.json` and `events_raw.json`.

### penford: resume-checkpoint

Command: manual resume from validated actor-packet checkpoint

- Loaded `CLAUDE.md` and the canonical workflow docs:
  - `.claude/skills/deal-agent/SKILL.md`
  - `.claude/skills/extract-deal/SKILL.md`
  - `.claude/skills/verify-extraction/SKILL.md`
  - `.claude/skills/enrich-deal/SKILL.md`
- Confirmed prior completed stages and artifacts:
  - `skill-pipeline raw-fetch --deal penford`
  - `skill-pipeline preprocess-source --deal penford`
  - `skill-pipeline compose-prompts --deal penford --mode actors`
  - `python scripts/validate_prompt_packets.py --deal penford --expect-sections`
- Gate result: continue from local-agent extraction stage.
- Notes:
  - Filing-grounded boundary reaffirmed. No benchmark, reconcile, or export artifacts consulted.
  - Ownership restricted to `raw/penford/`, `data/deals/penford/`, `data/skill/penford/`, and this session log.


### penford: raw-fetch

Command: skill-pipeline raw-fetch --deal penford
{
  "deal_slug": "penford",
  "cik": "739608",
  "primary_candidate_count": 1,
  "supplementary_candidate_count": 0,
  "frozen_count": 1,
  "discovery_path": "raw/penford/discovery.json",
  "document_registry_path": "raw/penford/document_registry.json"
}

### penford: preprocess-source

Command: skill-pipeline preprocess-source --deal penford
{
  "selected_document_id": "0001193125-14-455030",
  "selected_accession_number": "0001193125-14-455030",
  "confidence": "high",
  "confidence_factors": {
    "section_length": 388,
    "score_gap": 5595,
    "ambiguity_risk": "low",
    "coverage_assessment": "full"
  },
  "block_count": 95,
  "evidence_count": 1368,
  "candidate_count": 1,
  "top_primary_candidate_id": "0001193125-14-455030",
  "scanned_document_count": 1
}

### penford: compose-prompts-actors

Command: skill-pipeline compose-prompts --deal penford --mode actors
{
  "schema_version": "2.0.0",
  "artifact_type": "prompt_packet_manifest",
  "created_at": "2026-03-29T13:40:13.114155Z",
  "pipeline_version": "0.1.0",
  "run_id": "compose-21801a1d",
  "deal_slug": "penford",
  "source_accession_number": "0001193125-14-455030",
  "packets": [
    {
      "packet_id": "actors-w0",
      "packet_family": "actors",
      "chunk_mode": "single_pass",
      "window_id": "w0",
      "prefix_path": "/home/austinli/Projects/bids_pipeline/data/skill/penford/prompt/packets/actors-w0/prefix.md",
      "body_path": "/home/austinli/Projects/bids_pipeline/data/skill/penford/prompt/packets/actors-w0/body.md",
      "rendered_path": "/home/austinli/Projects/bids_pipeline/data/skill/penford/prompt/packets/actors-w0/rendered.md",
      "evidence_ids": [
        "0001193125-14-455030:E0302",
        "0001193125-14-455030:E0303",
        "0001193125-14-455030:E0304",
        "0001193125-14-455030:E0305",
        "0001193125-14-455030:E0306",
        "0001193125-14-455030:E0307",
        "0001193125-14-455030:E0308",
        "0001193125-14-455030:E0309",
        "0001193125-14-455030:E0310",
        "0001193125-14-455030:E0311",
        "0001193125-14-455030:E0312",
        "0001193125-14-455030:E0313",
        "0001193125-14-455030:E0314",
        "0001193125-14-455030:E0315",
        "0001193125-14-455030:E0316",
        "0001193125-14-455030:E0317",
        "0001193125-14-455030:E0318",
        "0001193125-14-455030:E0319",
        "0001193125-14-455030:E0320",
        "0001193125-14-455030:E0321",
        "0001193125-14-455030:E0322",
        "0001193125-14-455030:E0323",
        "0001193125-14-455030:E0324",
        "0001193125-14-455030:E0325",
        "0001193125-14-455030:E0326",
        "0001193125-14-455030:E0327",
        "0001193125-14-455030:E0328",
        "0001193125-14-455030:E0329",
        "0001193125-14-455030:E0330",
        "0001193125-14-455030:E0331",
        "0001193125-14-455030:E0332",
        "0001193125-14-455030:E0333",
        "0001193125-14-455030:E0334",
        "0001193125-14-455030:E0335",
        "0001193125-14-455030:E0336",
        "0001193125-14-455030:E0337",
        "0001193125-14-455030:E0338",
        "0001193125-14-455030:E0339",
        "0001193125-14-455030:E0340",
        "0001193125-14-455030:E0341",
        "0001193125-14-455030:E0342",
        "0001193125-14-455030:E0343",
        "0001193125-14-455030:E0344",
        "0001193125-14-455030:E0345",
        "0001193125-14-455030:E0346",
        "0001193125-14-455030:E0347",
        "0001193125-14-455030:E0348",
        "0001193125-14-455030:E0349",
        "0001193125-14-455030:E0350",
        "0001193125-14-455030:E0351",
        "0001193125-14-455030:E0352",
        "0001193125-14-455030:E0353",
        "0001193125-14-455030:E0354",
        "0001193125-14-455030:E0355",
        "0001193125-14-455030:E0356",
        "0001193125-14-455030:E0357",
        "0001193125-14-455030:E0358",
        "0001193125-14-455030:E0359",
        "0001193125-14-455030:E0360",
        "0001193125-14-455030:E0361",
        "0001193125-14-455030:E0362",
        "0001193125-14-455030:E0363",
        "0001193125-14-455030:E0364",
        "0001193125-14-455030:E0365",
        "0001193125-14-455030:E0366",
        "0001193125-14-455030:E0367",
        "0001193125-14-455030:E0368",
        "0001193125-14-455030:E0369",
        "0001193125-14-455030:E0370",
        "0001193125-14-455030:E0371",
        "0001193125-14-455030:E0372",
        "0001193125-14-455030:E0373",
        "0001193125-14-455030:E0374",
        "0001193125-14-455030:E0375",
        "0001193125-14-455030:E0376",
        "0001193125-14-455030:E0377",
        "0001193125-14-455030:E0378",
        "0001193125-14-455030:E0379",
        "0001193125-14-455030:E0380",
        "0001193125-14-455030:E0381",
        "0001193125-14-455030:E0382",
        "0001193125-14-455030:E0383",
        "0001193125-14-455030:E0384",
        "0001193125-14-455030:E0385",
        "0001193125-14-455030:E0386",
        "0001193125-14-455030:E0387",
        "0001193125-14-455030:E0388",
        "0001193125-14-455030:E0389",
        "0001193125-14-455030:E0390",
        "0001193125-14-455030:E0391",
        "0001193125-14-455030:E0392",
        "0001193125-14-455030:E0393",
        "0001193125-14-455030:E0394",
        "0001193125-14-455030:E0395",
        "0001193125-14-455030:E0396",
        "0001193125-14-455030:E0397",
        "0001193125-14-455030:E0398",
        "0001193125-14-455030:E0399",
        "0001193125-14-455030:E0400",
        "0001193125-14-455030:E0401",
        "0001193125-14-455030:E0402",
        "0001193125-14-455030:E0403",
        "0001193125-14-455030:E0404",
        "0001193125-14-455030:E0405",
        "0001193125-14-455030:E0406",
        "0001193125-14-455030:E0407",
        "0001193125-14-455030:E0408",
        "0001193125-14-455030:E0409",
        "0001193125-14-455030:E0410",
        "0001193125-14-455030:E0411",
        "0001193125-14-455030:E0412",
        "0001193125-14-455030:E0413",
        "0001193125-14-455030:E0414",
        "0001193125-14-455030:E0415",
        "0001193125-14-455030:E0416",
        "0001193125-14-455030:E0417",
        "0001193125-14-455030:E0418",
        "0001193125-14-455030:E0419",
        "0001193125-14-455030:E0420",
        "0001193125-14-455030:E0421",
        "0001193125-14-455030:E0422",
        "0001193125-14-455030:E0423",
        "0001193125-14-455030:E0424",
        "0001193125-14-455030:E0425",
        "0001193125-14-455030:E0426",
        "0001193125-14-455030:E0427",
        "0001193125-14-455030:E0428",
        "0001193125-14-455030:E0429",
        "0001193125-14-455030:E0430",
        "0001193125-14-455030:E0431",
        "0001193125-14-455030:E0432",
        "0001193125-14-455030:E0433",
        "0001193125-14-455030:E0434",
        "0001193125-14-455030:E0435",
        "0001193125-14-455030:E0436",
        "0001193125-14-455030:E0437",
        "0001193125-14-455030:E0438",
        "0001193125-14-455030:E0439",
        "0001193125-14-455030:E0440",
        "0001193125-14-455030:E0441",
        "0001193125-14-455030:E0442",
        "0001193125-14-455030:E0443",
        "0001193125-14-455030:E0444",
        "0001193125-14-455030:E0445",
        "0001193125-14-455030:E0446",
        "0001193125-14-455030:E0447",
        "0001193125-14-455030:E0448",
        "0001193125-14-455030:E0449",
        "0001193125-14-455030:E0450",
        "0001193125-14-455030:E0451",
        "0001193125-14-455030:E0452",
        "0001193125-14-455030:E0453",
        "0001193125-14-455030:E0454",
        "0001193125-14-455030:E0455",
        "0001193125-14-455030:E0456",
        "0001193125-14-455030:E0457",
        "0001193125-14-455030:E0458",
        "0001193125-14-455030:E0459",
        "0001193125-14-455030:E0460",
        "0001193125-14-455030:E0461",
        "0001193125-14-455030:E0462",
        "0001193125-14-455030:E0463",
        "0001193125-14-455030:E0464",
        "0001193125-14-455030:E0465",
        "0001193125-14-455030:E0466",
        "0001193125-14-455030:E0467",
        "0001193125-14-455030:E0468",
        "0001193125-14-455030:E0469",
        "0001193125-14-455030:E0470",
        "0001193125-14-455030:E0471",
        "0001193125-14-455030:E0472",
        "0001193125-14-455030:E0473",
        "0001193125-14-455030:E0474",
        "0001193125-14-455030:E0475",
        "0001193125-14-455030:E0476",
        "0001193125-14-455030:E0477",
        "0001193125-14-455030:E0478",
        "0001193125-14-455030:E0479",
        "0001193125-14-455030:E0480",
        "0001193125-14-455030:E0481",
        "0001193125-14-455030:E0482",
        "0001193125-14-455030:E0483",
        "0001193125-14-455030:E0484",
        "0001193125-14-455030:E0485",
        "0001193125-14-455030:E0486",
        "0001193125-14-455030:E0487"
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
    "source_blocks=95",
    "source_evidence_items=1368",
    "chunk_windows=1",
    "complexity=simple"
  ]
}

### penford: validate-actors

Command: python scripts/validate_prompt_packets.py --deal penford --expect-sections
PASS: All prompt packets valid for penford.

### penford: compose-prompts-events

Command: skill-pipeline compose-prompts --deal penford --mode events
{
  "schema_version": "2.0.0",
  "artifact_type": "prompt_packet_manifest",
  "created_at": "2026-03-29T13:59:59.772600Z",
  "pipeline_version": "0.1.0",
  "run_id": "compose-8e4de804",
  "deal_slug": "penford",
  "source_accession_number": "0001193125-14-455030",
  "packets": [
    {
      "packet_id": "events-w0",
      "packet_family": "events",
      "chunk_mode": "single_pass",
      "window_id": "w0",
      "prefix_path": "/home/austinli/Projects/bids_pipeline/data/skill/penford/prompt/packets/events-w0/prefix.md",
      "body_path": "/home/austinli/Projects/bids_pipeline/data/skill/penford/prompt/packets/events-w0/body.md",
      "rendered_path": "/home/austinli/Projects/bids_pipeline/data/skill/penford/prompt/packets/events-w0/rendered.md",
      "evidence_ids": [
        "0001193125-14-455030:E0302",
        "0001193125-14-455030:E0303",
        "0001193125-14-455030:E0304",
        "0001193125-14-455030:E0305",
        "0001193125-14-455030:E0306",
        "0001193125-14-455030:E0307",
        "0001193125-14-455030:E0308",
        "0001193125-14-455030:E0309",
        "0001193125-14-455030:E0310",
        "0001193125-14-455030:E0311",
        "0001193125-14-455030:E0312",
        "0001193125-14-455030:E0313",
        "0001193125-14-455030:E0314",
        "0001193125-14-455030:E0315",
        "0001193125-14-455030:E0316",
        "0001193125-14-455030:E0317",
        "0001193125-14-455030:E0318",
        "0001193125-14-455030:E0319",
        "0001193125-14-455030:E0320",
        "0001193125-14-455030:E0321",
        "0001193125-14-455030:E0322",
        "0001193125-14-455030:E0323",
        "0001193125-14-455030:E0324",
        "0001193125-14-455030:E0325",
        "0001193125-14-455030:E0326",
        "0001193125-14-455030:E0327",
        "0001193125-14-455030:E0328",
        "0001193125-14-455030:E0329",
        "0001193125-14-455030:E0330",
        "0001193125-14-455030:E0331",
        "0001193125-14-455030:E0332",
        "0001193125-14-455030:E0333",
        "0001193125-14-455030:E0334",
        "0001193125-14-455030:E0335",
        "0001193125-14-455030:E0336",
        "0001193125-14-455030:E0337",
        "0001193125-14-455030:E0338",
        "0001193125-14-455030:E0339",
        "0001193125-14-455030:E0340",
        "0001193125-14-455030:E0341",
        "0001193125-14-455030:E0342",
        "0001193125-14-455030:E0343",
        "0001193125-14-455030:E0344",
        "0001193125-14-455030:E0345",
        "0001193125-14-455030:E0346",
        "0001193125-14-455030:E0347",
        "0001193125-14-455030:E0348",
        "0001193125-14-455030:E0349",
        "0001193125-14-455030:E0350",
        "0001193125-14-455030:E0351",
        "0001193125-14-455030:E0352",
        "0001193125-14-455030:E0353",
        "0001193125-14-455030:E0354",
        "0001193125-14-455030:E0355",
        "0001193125-14-455030:E0356",
        "0001193125-14-455030:E0357",
        "0001193125-14-455030:E0358",
        "0001193125-14-455030:E0359",
        "0001193125-14-455030:E0360",
        "0001193125-14-455030:E0361",
        "0001193125-14-455030:E0362",
        "0001193125-14-455030:E0363",
        "0001193125-14-455030:E0364",
        "0001193125-14-455030:E0365",
        "0001193125-14-455030:E0366",
        "0001193125-14-455030:E0367",
        "0001193125-14-455030:E0368",
        "0001193125-14-455030:E0369",
        "0001193125-14-455030:E0370",
        "0001193125-14-455030:E0371",
        "0001193125-14-455030:E0372",
        "0001193125-14-455030:E0373",
        "0001193125-14-455030:E0374",
        "0001193125-14-455030:E0375",
        "0001193125-14-455030:E0376",
        "0001193125-14-455030:E0377",
        "0001193125-14-455030:E0378",
        "0001193125-14-455030:E0379",
        "0001193125-14-455030:E0380",
        "0001193125-14-455030:E0381",
        "0001193125-14-455030:E0382",
        "0001193125-14-455030:E0383",
        "0001193125-14-455030:E0384",
        "0001193125-14-455030:E0385",
        "0001193125-14-455030:E0386",
        "0001193125-14-455030:E0387",
        "0001193125-14-455030:E0388",
        "0001193125-14-455030:E0389",
        "0001193125-14-455030:E0390",
        "0001193125-14-455030:E0391",
        "0001193125-14-455030:E0392",
        "0001193125-14-455030:E0393",
        "0001193125-14-455030:E0394",
        "0001193125-14-455030:E0395",
        "0001193125-14-455030:E0396",
        "0001193125-14-455030:E0397",
        "0001193125-14-455030:E0398",
        "0001193125-14-455030:E0399",
        "0001193125-14-455030:E0400",
        "0001193125-14-455030:E0401",
        "0001193125-14-455030:E0402",
        "0001193125-14-455030:E0403",
        "0001193125-14-455030:E0404",
        "0001193125-14-455030:E0405",
        "0001193125-14-455030:E0406",
        "0001193125-14-455030:E0407",
        "0001193125-14-455030:E0408",
        "0001193125-14-455030:E0409",
        "0001193125-14-455030:E0410",
        "0001193125-14-455030:E0411",
        "0001193125-14-455030:E0412",
        "0001193125-14-455030:E0413",
        "0001193125-14-455030:E0414",
        "0001193125-14-455030:E0415",
        "0001193125-14-455030:E0416",
        "0001193125-14-455030:E0417",
        "0001193125-14-455030:E0418",
        "0001193125-14-455030:E0419",
        "0001193125-14-455030:E0420",
        "0001193125-14-455030:E0421",
        "0001193125-14-455030:E0422",
        "0001193125-14-455030:E0423",
        "0001193125-14-455030:E0424",
        "0001193125-14-455030:E0425",
        "0001193125-14-455030:E0426",
        "0001193125-14-455030:E0427",
        "0001193125-14-455030:E0428",
        "0001193125-14-455030:E0429",
        "0001193125-14-455030:E0430",
        "0001193125-14-455030:E0431",
        "0001193125-14-455030:E0432",
        "0001193125-14-455030:E0433",
        "0001193125-14-455030:E0434",
        "0001193125-14-455030:E0435",
        "0001193125-14-455030:E0436",
        "0001193125-14-455030:E0437",
        "0001193125-14-455030:E0438",
        "0001193125-14-455030:E0439",
        "0001193125-14-455030:E0440",
        "0001193125-14-455030:E0441",
        "0001193125-14-455030:E0442",
        "0001193125-14-455030:E0443",
        "0001193125-14-455030:E0444",
        "0001193125-14-455030:E0445",
        "0001193125-14-455030:E0446",
        "0001193125-14-455030:E0447",
        "0001193125-14-455030:E0448",
        "0001193125-14-455030:E0449",
        "0001193125-14-455030:E0450",
        "0001193125-14-455030:E0451",
        "0001193125-14-455030:E0452",
        "0001193125-14-455030:E0453",
        "0001193125-14-455030:E0454",
        "0001193125-14-455030:E0455",
        "0001193125-14-455030:E0456",
        "0001193125-14-455030:E0457",
        "0001193125-14-455030:E0458",
        "0001193125-14-455030:E0459",
        "0001193125-14-455030:E0460",
        "0001193125-14-455030:E0461",
        "0001193125-14-455030:E0462",
        "0001193125-14-455030:E0463",
        "0001193125-14-455030:E0464",
        "0001193125-14-455030:E0465",
        "0001193125-14-455030:E0466",
        "0001193125-14-455030:E0467",
        "0001193125-14-455030:E0468",
        "0001193125-14-455030:E0469",
        "0001193125-14-455030:E0470",
        "0001193125-14-455030:E0471",
        "0001193125-14-455030:E0472",
        "0001193125-14-455030:E0473",
        "0001193125-14-455030:E0474",
        "0001193125-14-455030:E0475",
        "0001193125-14-455030:E0476",
        "0001193125-14-455030:E0477",
        "0001193125-14-455030:E0478",
        "0001193125-14-455030:E0479",
        "0001193125-14-455030:E0480",
        "0001193125-14-455030:E0481",
        "0001193125-14-455030:E0482",
        "0001193125-14-455030:E0483",
        "0001193125-14-455030:E0484",
        "0001193125-14-455030:E0485",
        "0001193125-14-455030:E0486",
        "0001193125-14-455030:E0487"
      ],
      "actor_roster_source_path": "/home/austinli/Projects/bids_pipeline/data/skill/penford/extract/actors_raw.json"
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
    "source_blocks=95",
    "source_evidence_items=1368",
    "chunk_windows=1",
    "complexity=simple"
  ]
}

### penford: validate-events

Command: python scripts/validate_prompt_packets.py --deal penford --expect-sections
PASS: All prompt packets valid for penford.

### penford: extraction-recovery-handoff

Command: manual takeover from validated events-packet checkpoint

- `prompt/manifest.json` remained in validated `events` mode and `extract/actors_raw.json` was already present.
- A later main-thread recovery pass exited without writing `data/skill/penford/extract/events_raw.json` or a final extraction result.
- This takeover resumed directly from the validated events checkpoint, reread the filing-grounded chronology blocks, and wrote a fresh `events_raw.json` without changing shared code or other deal artifacts.

### penford: canonicalize-wall-and-fix

- `skill-pipeline canonicalize --deal penford` initially failed with `Duplicate quote_id 'Q001' in quotes array`.
- Root cause: event-side top-level `quote_id` values restarted at `Q001` and collided with actor-side quote ids.
- Fix applied: renumbered event-side quote ids and their event references above the actor-side max (`Q017` through `Q046`) in `data/skill/penford/extract/events_raw.json`.
- Result: `canonicalize` passed on retry.

### penford: deterministic-core

- `skill-pipeline check --deal penford` passed.
- `skill-pipeline verify --deal penford` passed.
- `skill-pipeline coverage --deal penford` passed.
- `skill-pipeline gates --deal penford` passed.
- `skill-pipeline enrich-core --deal penford` passed.

### penford: enrichment-and-export

- Filing-grounded `data/skill/penford/enrich/enrichment.json` was materialized.
- `skill-pipeline db-load --deal penford` passed.
- `skill-pipeline db-export --deal penford` passed.
- Output: `data/skill/penford/export/deal_events.csv` (`25` lines including header).
