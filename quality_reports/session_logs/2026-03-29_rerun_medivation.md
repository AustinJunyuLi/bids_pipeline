# Rerun Log: medivation

- Start time: 2026-03-29T14:39:14+01:00
- Deal: medivation
- Workflow: canonical /deal-agent route through enrich-deal; stop before db-load/db-export

## Run Log


### medivation: raw-fetch

Command: skill-pipeline raw-fetch --deal medivation
{
  "deal_slug": "medivation",
  "cik": "1011835",
  "primary_candidate_count": 1,
  "supplementary_candidate_count": 0,
  "frozen_count": 1,
  "discovery_path": "raw/medivation/discovery.json",
  "document_registry_path": "raw/medivation/document_registry.json"
}

### medivation: preprocess-source

Command: skill-pipeline preprocess-source --deal medivation
{
  "selected_document_id": "0001193125-16-696911",
  "selected_accession_number": "0001193125-16-696911",
  "confidence": "high",
  "confidence_factors": {
    "section_length": 562,
    "score_gap": 4744,
    "ambiguity_risk": "low",
    "coverage_assessment": "full"
  },
  "block_count": 165,
  "evidence_count": 511,
  "candidate_count": 1,
  "top_primary_candidate_id": "0001193125-16-696911",
  "scanned_document_count": 1
}

### medivation: compose-prompts-actors

Command: skill-pipeline compose-prompts --deal medivation --mode actors
{
  "schema_version": "2.0.0",
  "artifact_type": "prompt_packet_manifest",
  "created_at": "2026-03-29T13:40:04.708731Z",
  "pipeline_version": "0.1.0",
  "run_id": "compose-ceffc538",
  "deal_slug": "medivation",
  "source_accession_number": "0001193125-16-696911",
  "packets": [
    {
      "packet_id": "actors-w0",
      "packet_family": "actors",
      "chunk_mode": "chunked",
      "window_id": "w0",
      "prefix_path": "/home/austinli/Projects/bids_pipeline/data/skill/medivation/prompt/packets/actors-w0/prefix.md",
      "body_path": "/home/austinli/Projects/bids_pipeline/data/skill/medivation/prompt/packets/actors-w0/body.md",
      "rendered_path": "/home/austinli/Projects/bids_pipeline/data/skill/medivation/prompt/packets/actors-w0/rendered.md",
      "evidence_ids": [
        "0001193125-16-696911:E0096",
        "0001193125-16-696911:E0097",
        "0001193125-16-696911:E0098",
        "0001193125-16-696911:E0099",
        "0001193125-16-696911:E0100",
        "0001193125-16-696911:E0101",
        "0001193125-16-696911:E0102",
        "0001193125-16-696911:E0103",
        "0001193125-16-696911:E0104",
        "0001193125-16-696911:E0105",
        "0001193125-16-696911:E0106",
        "0001193125-16-696911:E0107",
        "0001193125-16-696911:E0108",
        "0001193125-16-696911:E0109",
        "0001193125-16-696911:E0110",
        "0001193125-16-696911:E0111",
        "0001193125-16-696911:E0112",
        "0001193125-16-696911:E0113",
        "0001193125-16-696911:E0114",
        "0001193125-16-696911:E0115",
        "0001193125-16-696911:E0116",
        "0001193125-16-696911:E0117",
        "0001193125-16-696911:E0118",
        "0001193125-16-696911:E0119",
        "0001193125-16-696911:E0120",
        "0001193125-16-696911:E0121",
        "0001193125-16-696911:E0122",
        "0001193125-16-696911:E0123",
        "0001193125-16-696911:E0124",
        "0001193125-16-696911:E0125",
        "0001193125-16-696911:E0126",
        "0001193125-16-696911:E0127",
        "0001193125-16-696911:E0128",
        "0001193125-16-696911:E0129",
        "0001193125-16-696911:E0130",
        "0001193125-16-696911:E0131",
        "0001193125-16-696911:E0132",
        "0001193125-16-696911:E0133",
        "0001193125-16-696911:E0134",
        "0001193125-16-696911:E0135",
        "0001193125-16-696911:E0136",
        "0001193125-16-696911:E0137",
        "0001193125-16-696911:E0138",
        "0001193125-16-696911:E0139",
        "0001193125-16-696911:E0140",
        "0001193125-16-696911:E0141",
        "0001193125-16-696911:E0142",
        "0001193125-16-696911:E0143",
        "0001193125-16-696911:E0144",
        "0001193125-16-696911:E0145",
        "0001193125-16-696911:E0146",
        "0001193125-16-696911:E0147",
        "0001193125-16-696911:E0148",
        "0001193125-16-696911:E0149",
        "0001193125-16-696911:E0150",
        "0001193125-16-696911:E0151",
        "0001193125-16-696911:E0152",
        "0001193125-16-696911:E0153",
        "0001193125-16-696911:E0154",
        "0001193125-16-696911:E0155",
        "0001193125-16-696911:E0156",
        "0001193125-16-696911:E0157",
        "0001193125-16-696911:E0158",
        "0001193125-16-696911:E0159",
        "0001193125-16-696911:E0160",
        "0001193125-16-696911:E0161",
        "0001193125-16-696911:E0162",
        "0001193125-16-696911:E0163",
        "0001193125-16-696911:E0164",
        "0001193125-16-696911:E0165",
        "0001193125-16-696911:E0166",
        "0001193125-16-696911:E0167",
        "0001193125-16-696911:E0168",
        "0001193125-16-696911:E0169",
        "0001193125-16-696911:E0170",
        "0001193125-16-696911:E0171",
        "0001193125-16-696911:E0172",
        "0001193125-16-696911:E0173",
        "0001193125-16-696911:E0174",
        "0001193125-16-696911:E0175",
        "0001193125-16-696911:E0176",
        "0001193125-16-696911:E0177",
        "0001193125-16-696911:E0178",
        "0001193125-16-696911:E0179",
        "0001193125-16-696911:E0180",
        "0001193125-16-696911:E0181",
        "0001193125-16-696911:E0182",
        "0001193125-16-696911:E0183",
        "0001193125-16-696911:E0184",
        "0001193125-16-696911:E0185",
        "0001193125-16-696911:E0186",
        "0001193125-16-696911:E0187",
        "0001193125-16-696911:E0188",
        "0001193125-16-696911:E0189",
        "0001193125-16-696911:E0190",
        "0001193125-16-696911:E0191",
        "0001193125-16-696911:E0192",
        "0001193125-16-696911:E0193",
        "0001193125-16-696911:E0194",
        "0001193125-16-696911:E0195",
        "0001193125-16-696911:E0196",
        "0001193125-16-696911:E0197",
        "0001193125-16-696911:E0198",
        "0001193125-16-696911:E0199",
        "0001193125-16-696911:E0200",
        "0001193125-16-696911:E0201",
        "0001193125-16-696911:E0202",
        "0001193125-16-696911:E0203",
        "0001193125-16-696911:E0204",
        "0001193125-16-696911:E0205",
        "0001193125-16-696911:E0206",
        "0001193125-16-696911:E0207",
        "0001193125-16-696911:E0208",
        "0001193125-16-696911:E0209",
        "0001193125-16-696911:E0210",
        "0001193125-16-696911:E0211",
        "0001193125-16-696911:E0212",
        "0001193125-16-696911:E0213",
        "0001193125-16-696911:E0214",
        "0001193125-16-696911:E0215",
        "0001193125-16-696911:E0216",
        "0001193125-16-696911:E0217",
        "0001193125-16-696911:E0218",
        "0001193125-16-696911:E0219",
        "0001193125-16-696911:E0220",
        "0001193125-16-696911:E0221",
        "0001193125-16-696911:E0222",
        "0001193125-16-696911:E0223",
        "0001193125-16-696911:E0224",
        "0001193125-16-696911:E0225",
        "0001193125-16-696911:E0226",
        "0001193125-16-696911:E0227",
        "0001193125-16-696911:E0228"
      ],
      "actor_roster_source_path": null
    },
    {
      "packet_id": "actors-w1",
      "packet_family": "actors",
      "chunk_mode": "chunked",
      "window_id": "w1",
      "prefix_path": "/home/austinli/Projects/bids_pipeline/data/skill/medivation/prompt/packets/actors-w1/prefix.md",
      "body_path": "/home/austinli/Projects/bids_pipeline/data/skill/medivation/prompt/packets/actors-w1/body.md",
      "rendered_path": "/home/austinli/Projects/bids_pipeline/data/skill/medivation/prompt/packets/actors-w1/rendered.md",
      "evidence_ids": [
        "0001193125-16-696911:E0218",
        "0001193125-16-696911:E0219",
        "0001193125-16-696911:E0220",
        "0001193125-16-696911:E0221",
        "0001193125-16-696911:E0222",
        "0001193125-16-696911:E0223",
        "0001193125-16-696911:E0224",
        "0001193125-16-696911:E0225",
        "0001193125-16-696911:E0226",
        "0001193125-16-696911:E0227",
        "0001193125-16-696911:E0228",
        "0001193125-16-696911:E0229",

### medivation: extraction-completion

- Narrow-scope takeover from the validated events-packet checkpoint.
- Wrote `data/skill/medivation/extract/events_raw.json` from the current filing-grounded prompt/source artifacts.
- Left `actors_raw.json` unchanged.
        "0001193125-16-696911:E0230",
        "0001193125-16-696911:E0231",
        "0001193125-16-696911:E0232",
        "0001193125-16-696911:E0233",
        "0001193125-16-696911:E0234",
        "0001193125-16-696911:E0235",
        "0001193125-16-696911:E0236",
        "0001193125-16-696911:E0237",
        "0001193125-16-696911:E0238",
        "0001193125-16-696911:E0239",
        "0001193125-16-696911:E0240",
        "0001193125-16-696911:E0241",
        "0001193125-16-696911:E0242",
        "0001193125-16-696911:E0243",
        "0001193125-16-696911:E0244",
        "0001193125-16-696911:E0245",
        "0001193125-16-696911:E0246",
        "0001193125-16-696911:E0247",
        "0001193125-16-696911:E0248",
        "0001193125-16-696911:E0249",
        "0001193125-16-696911:E0250",
        "0001193125-16-696911:E0251",
        "0001193125-16-696911:E0252",
        "0001193125-16-696911:E0253",
        "0001193125-16-696911:E0254",
        "0001193125-16-696911:E0255",
        "0001193125-16-696911:E0256",
        "0001193125-16-696911:E0257",
        "0001193125-16-696911:E0258",
        "0001193125-16-696911:E0259",
        "0001193125-16-696911:E0260",
        "0001193125-16-696911:E0261",
        "0001193125-16-696911:E0262",
        "0001193125-16-696911:E0263",
        "0001193125-16-696911:E0264",
        "0001193125-16-696911:E0265",
        "0001193125-16-696911:E0266",
        "0001193125-16-696911:E0267",
        "0001193125-16-696911:E0268",
        "0001193125-16-696911:E0269",

        "0001193125-16-696911:E0270",
        "0001193125-16-696911:E0271",
        "0001193125-16-696911:E0272",
        "0001193125-16-696911:E0273",
        "0001193125-16-696911:E0274",
        "0001193125-16-696911:E0275",
        "0001193125-16-696911:E0276",
        "0001193125-16-696911:E0277",
        "0001193125-16-696911:E0278",
        "0001193125-16-696911:E0279",
        "0001193125-16-696911:E0280",
        "0001193125-16-696911:E0281",
        "0001193125-16-696911:E0282",
        "0001193125-16-696911:E0283",
        "0001193125-16-696911:E0284",
        "0001193125-16-696911:E0285",
        "0001193125-16-696911:E0286",
        "0001193125-16-696911:E0287",
        "0001193125-16-696911:E0288",
        "0001193125-16-696911:E0289"
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
    "effective_budget=6000",
    "source_blocks=165",
    "source_evidence_items=511",
    "chunk_windows=2",
    "complexity=complex"
  ]
}

### medivation: validate-actors

Command: python scripts/validate_prompt_packets.py --deal medivation --expect-sections
PASS: All prompt packets valid for medivation.

### medivation: resume-point

Command: resume nondeterministic half after actor prompt validation

Canonical instructions consulted:
- `CLAUDE.md`
- `.claude/skills/deal-agent/SKILL.md`
- `.claude/skills/extract-deal/SKILL.md`
- `.claude/skills/verify-extraction/SKILL.md`
- `.claude/skills/enrich-deal/SKILL.md`

Current artifact state at resume:
- `raw/medivation/` present with immutable filing text and refreshed discovery metadata
- `data/deals/medivation/source/` present from successful preprocess
- `data/skill/medivation/prompt/` present with actor packets only
- No `extract/`, `check/`, `verify/`, `coverage/`, `gates/`, or `enrich/` outputs yet

Gate result: resume approved from `extract-deal` forward

### medivation: output-directories

Command: mkdir -p data/skill/medivation/{extract,check,verify,coverage,gates,enrich,export,canonicalize}

Gate result: downstream medivation output directories present

### medivation: extraction-worker-handoff

Note: the earlier full-flow worker was stopped for orchestration and throughput reasons before any trusted extract artifacts were written for this rerun checkpoint. This focused extraction worker is taking over from the validated actor-packet checkpoint and will stop after filing-grounded `actors_raw.json` and `events_raw.json` exist and pass schema validation.

### medivation: compose-prompts-events

Command: skill-pipeline compose-prompts --deal medivation --mode events
{
  "schema_version": "2.0.0",
  "artifact_type": "prompt_packet_manifest",
  "created_at": "2026-03-29T13:59:07.122171Z",
  "pipeline_version": "0.1.0",
  "run_id": "compose-74ddbe5e",
  "deal_slug": "medivation",
  "source_accession_number": "0001193125-16-696911",
  "packets": [
    {
      "packet_id": "events-w0",
      "packet_family": "events",
      "chunk_mode": "chunked",
      "window_id": "w0",
      "prefix_path": "/home/austinli/Projects/bids_pipeline/data/skill/medivation/prompt/packets/events-w0/prefix.md",
      "body_path": "/home/austinli/Projects/bids_pipeline/data/skill/medivation/prompt/packets/events-w0/body.md",
      "rendered_path": "/home/austinli/Projects/bids_pipeline/data/skill/medivation/prompt/packets/events-w0/rendered.md",
      "evidence_ids": [
        "0001193125-16-696911:E0096",
        "0001193125-16-696911:E0097",
        "0001193125-16-696911:E0098",
        "0001193125-16-696911:E0099",
        "0001193125-16-696911:E0100",
        "0001193125-16-696911:E0101",
        "0001193125-16-696911:E0102",
        "0001193125-16-696911:E0103",
        "0001193125-16-696911:E0104",
        "0001193125-16-696911:E0105",
        "0001193125-16-696911:E0106",
        "0001193125-16-696911:E0107",
        "0001193125-16-696911:E0108",
        "0001193125-16-696911:E0109",
        "0001193125-16-696911:E0110",
        "0001193125-16-696911:E0111",
        "0001193125-16-696911:E0112",
        "0001193125-16-696911:E0113",
        "0001193125-16-696911:E0114",
        "0001193125-16-696911:E0115",
        "0001193125-16-696911:E0116",
        "0001193125-16-696911:E0117",
        "0001193125-16-696911:E0118",
        "0001193125-16-696911:E0119",
        "0001193125-16-696911:E0120",
        "0001193125-16-696911:E0121",
        "0001193125-16-696911:E0122",
        "0001193125-16-696911:E0123",
        "0001193125-16-696911:E0124",
        "0001193125-16-696911:E0125",
        "0001193125-16-696911:E0126",
        "0001193125-16-696911:E0127",
        "0001193125-16-696911:E0128",
        "0001193125-16-696911:E0129",
        "0001193125-16-696911:E0130",
        "0001193125-16-696911:E0131",
        "0001193125-16-696911:E0132",
        "0001193125-16-696911:E0133",
        "0001193125-16-696911:E0134",
        "0001193125-16-696911:E0135",
        "0001193125-16-696911:E0136",
        "0001193125-16-696911:E0137",
        "0001193125-16-696911:E0138",
        "0001193125-16-696911:E0139",
        "0001193125-16-696911:E0140",
        "0001193125-16-696911:E0141",
        "0001193125-16-696911:E0142",
        "0001193125-16-696911:E0143",
        "0001193125-16-696911:E0144",
        "0001193125-16-696911:E0145",
        "0001193125-16-696911:E0146",
        "0001193125-16-696911:E0147",
        "0001193125-16-696911:E0148",
        "0001193125-16-696911:E0149",
        "0001193125-16-696911:E0150",
        "0001193125-16-696911:E0151",
        "0001193125-16-696911:E0152",
        "0001193125-16-696911:E0153",
        "0001193125-16-696911:E0154",
        "0001193125-16-696911:E0155",
        "0001193125-16-696911:E0156",
        "0001193125-16-696911:E0157",
        "0001193125-16-696911:E0158",
        "0001193125-16-696911:E0159",
        "0001193125-16-696911:E0160",
        "0001193125-16-696911:E0161",
        "0001193125-16-696911:E0162",
        "0001193125-16-696911:E0163",
        "0001193125-16-696911:E0164",
        "0001193125-16-696911:E0165",
        "0001193125-16-696911:E0166",
        "0001193125-16-696911:E0167",
        "0001193125-16-696911:E0168",
        "0001193125-16-696911:E0169",
        "0001193125-16-696911:E0170",
        "0001193125-16-696911:E0171",
        "0001193125-16-696911:E0172",
        "0001193125-16-696911:E0173",
        "0001193125-16-696911:E0174",
        "0001193125-16-696911:E0175",
        "0001193125-16-696911:E0176",
        "0001193125-16-696911:E0177",
        "0001193125-16-696911:E0178",
        "0001193125-16-696911:E0179",
        "0001193125-16-696911:E0180",
        "0001193125-16-696911:E0181",
        "0001193125-16-696911:E0182",
        "0001193125-16-696911:E0183",
        "0001193125-16-696911:E0184",
        "0001193125-16-696911:E0185",
        "0001193125-16-696911:E0186",
        "0001193125-16-696911:E0187",
        "0001193125-16-696911:E0188",
        "0001193125-16-696911:E0189",
        "0001193125-16-696911:E0190",
        "0001193125-16-696911:E0191",
        "0001193125-16-696911:E0192",
        "0001193125-16-696911:E0193",
        "0001193125-16-696911:E0194",
        "0001193125-16-696911:E0195",
        "0001193125-16-696911:E0196",
        "0001193125-16-696911:E0197",
        "0001193125-16-696911:E0198",
        "0001193125-16-696911:E0199",
        "0001193125-16-696911:E0200",
        "0001193125-16-696911:E0201",
        "0001193125-16-696911:E0202",
        "0001193125-16-696911:E0203",
        "0001193125-16-696911:E0204",
        "0001193125-16-696911:E0205",
        "0001193125-16-696911:E0206",
        "0001193125-16-696911:E0207",
        "0001193125-16-696911:E0208",
        "0001193125-16-696911:E0209",
        "0001193125-16-696911:E0210",
        "0001193125-16-696911:E0211",
        "0001193125-16-696911:E0212",
        "0001193125-16-696911:E0213",
        "0001193125-16-696911:E0214",
        "0001193125-16-696911:E0215",
        "0001193125-16-696911:E0216",
        "0001193125-16-696911:E0217",
        "0001193125-16-696911:E0218",
        "0001193125-16-696911:E0219",
        "0001193125-16-696911:E0220",
        "0001193125-16-696911:E0221",
        "0001193125-16-696911:E0222",
        "0001193125-16-696911:E0223",
        "0001193125-16-696911:E0224",
        "0001193125-16-696911:E0225",
        "0001193125-16-696911:E0226",
        "0001193125-16-696911:E0227",
        "0001193125-16-696911:E0228"
      ],
      "actor_roster_source_path": "/home/austinli/Projects/bids_pipeline/data/skill/medivation/extract/actors_raw.json"
    },
    {
      "packet_id": "events-w1",
      "packet_family": "events",
      "chunk_mode": "chunked",
      "window_id": "w1",
      "prefix_path": "/home/austinli/Projects/bids_pipeline/data/skill/medivation/prompt/packets/events-w1/prefix.md",
      "body_path": "/home/austinli/Projects/bids_pipeline/data/skill/medivation/prompt/packets/events-w1/body.md",
      "rendered_path": "/home/austinli/Projects/bids_pipeline/data/skill/medivation/prompt/packets/events-w1/rendered.md",
      "evidence_ids": [
        "0001193125-16-696911:E0218",
        "0001193125-16-696911:E0219",
        "0001193125-16-696911:E0220",
        "0001193125-16-696911:E0221",
        "0001193125-16-696911:E0222",
        "0001193125-16-696911:E0223",
        "0001193125-16-696911:E0224",
        "0001193125-16-696911:E0225",
        "0001193125-16-696911:E0226",
        "0001193125-16-696911:E0227",
        "0001193125-16-696911:E0228",
        "0001193125-16-696911:E0229",
        "0001193125-16-696911:E0230",
        "0001193125-16-696911:E0231",
        "0001193125-16-696911:E0232",
        "0001193125-16-696911:E0233",
        "0001193125-16-696911:E0234",
        "0001193125-16-696911:E0235",
        "0001193125-16-696911:E0236",
        "0001193125-16-696911:E0237",
        "0001193125-16-696911:E0238",
        "0001193125-16-696911:E0239",
        "0001193125-16-696911:E0240",
        "0001193125-16-696911:E0241",
        "0001193125-16-696911:E0242",
        "0001193125-16-696911:E0243",
        "0001193125-16-696911:E0244",
        "0001193125-16-696911:E0245",
        "0001193125-16-696911:E0246",
        "0001193125-16-696911:E0247",
        "0001193125-16-696911:E0248",
        "0001193125-16-696911:E0249",
        "0001193125-16-696911:E0250",
        "0001193125-16-696911:E0251",
        "0001193125-16-696911:E0252",
        "0001193125-16-696911:E0253",
        "0001193125-16-696911:E0254",
        "0001193125-16-696911:E0255",
        "0001193125-16-696911:E0256",
        "0001193125-16-696911:E0257",
        "0001193125-16-696911:E0258",
        "0001193125-16-696911:E0259",
        "0001193125-16-696911:E0260",
        "0001193125-16-696911:E0261",
        "0001193125-16-696911:E0262",
        "0001193125-16-696911:E0263",
        "0001193125-16-696911:E0264",
        "0001193125-16-696911:E0265",
        "0001193125-16-696911:E0266",
        "0001193125-16-696911:E0267",
        "0001193125-16-696911:E0268",
        "0001193125-16-696911:E0269",
        "0001193125-16-696911:E0270",
        "0001193125-16-696911:E0271",
        "0001193125-16-696911:E0272",
        "0001193125-16-696911:E0273",
        "0001193125-16-696911:E0274",
        "0001193125-16-696911:E0275",
        "0001193125-16-696911:E0276",
        "0001193125-16-696911:E0277",
        "0001193125-16-696911:E0278",
        "0001193125-16-696911:E0279",
        "0001193125-16-696911:E0280",
        "0001193125-16-696911:E0281",
        "0001193125-16-696911:E0282",
        "0001193125-16-696911:E0283",
        "0001193125-16-696911:E0284",
        "0001193125-16-696911:E0285",
        "0001193125-16-696911:E0286",
        "0001193125-16-696911:E0287",
        "0001193125-16-696911:E0288",
        "0001193125-16-696911:E0289"
      ],
      "actor_roster_source_path": "/home/austinli/Projects/bids_pipeline/data/skill/medivation/extract/actors_raw.json"
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
    "effective_budget=6000",
    "source_blocks=165",
    "source_evidence_items=511",
    "chunk_windows=2",
    "complexity=complex"
  ]
}

### medivation: validate-events

Command: python scripts/validate_prompt_packets.py --deal medivation --expect-sections
PASS: All prompt packets valid for medivation.

### medivation: extraction-complete

- Wrote `data/skill/medivation/extract/events_raw.json` from the validated events-packet checkpoint.
- Left `data/skill/medivation/extract/actors_raw.json` unchanged.

### medivation: normalization-fixes

- Wall hit after extraction normalization audit:
  - overlapping actor/event quote ids in canonicalization inputs;
  - proposal `terms.consideration_type=\"cash_and_cvr\"` values rejected by the live raw schema;
  - raw `round_scope=\"extension\"` values not accepted in the live deterministic route.
- Fixes applied:
  - renumbered event-side quote ids above the actor-side max;
  - changed proposal `consideration_type` to `mixed` for `evt_008`, `evt_016`, and `evt_017`;
  - changed raw `round_scope` to `formal` for `evt_028` and `evt_030`.

### medivation: deterministic-core

- `canonicalize` passed after normalization.
- `check` passed.
- `verify` passed.
- `coverage` passed at blocker/error level.
- `gates` passed.
- `enrich-core` passed.

### medivation: enrichment-and-export

- Filing-grounded `data/skill/medivation/enrich/enrichment.json` was materialized.
- `skill-pipeline db-load --deal medivation` passed.
- `skill-pipeline db-export --deal medivation` passed.
- Output: `data/skill/medivation/export/deal_events.csv` (`35` lines including header).
