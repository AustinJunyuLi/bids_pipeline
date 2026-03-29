# Rerun Log: mac-gray

- Start time: 2026-03-29T14:46:23+01:00
- Deal: mac-gray
- Workflow: canonical `/deal-agent` route from `.claude/skills/`; resume after deterministic front half
- Scope ownership: `raw/mac-gray/`, `data/deals/mac-gray/`, `data/skill/mac-gray/`, `quality_reports/session_logs/2026-03-29_rerun_mac-gray.md`
- Shared-code boundary: do not edit repo code, shared scripts, benchmark materials, `stec`, `imprivata`, or `data/pipeline.duckdb`

## Handoff State

- Inherited completed stages from prior runner:
  - `skill-pipeline raw-fetch --deal mac-gray`
  - `skill-pipeline preprocess-source --deal mac-gray`
  - `skill-pipeline compose-prompts --deal mac-gray --mode actors`
  - `python scripts/validate_prompt_packets.py --deal mac-gray --expect-sections`
- Verified prompt manifest state before resuming:
  - `deal_slug`: `mac-gray`
  - `source_accession_number`: `0001047469-13-010973`
  - actor packet count: `3`
  - actor packets: `actors-w0`, `actors-w1`, `actors-w2`

## Run Log

- 2026-03-29T14:46:23+01:00: Resumed worker after deterministic front-half completion. Using canonical `.claude/skills/deal-agent`, `.claude/skills/extract-deal`, `.claude/skills/verify-extraction`, and `.claude/skills/enrich-deal`.
- 2026-03-29T14:46:23+01:00: Preflight check passed for owned paths. Worktree contains unrelated changes outside scope; those paths will not be touched.

### mac-gray: compose-prompts-events

Command: skill-pipeline compose-prompts --deal mac-gray --mode events
{
  "schema_version": "2.0.0",
  "artifact_type": "prompt_packet_manifest",
  "created_at": "2026-03-29T13:59:06.816930Z",
  "pipeline_version": "0.1.0",
  "run_id": "compose-27654dcc",
  "deal_slug": "mac-gray",
  "source_accession_number": "0001047469-13-010973",
  "packets": [
    {
      "packet_id": "events-w0",
      "packet_family": "events",
      "chunk_mode": "chunked",
      "window_id": "w0",
      "prefix_path": "/home/austinli/Projects/bids_pipeline/data/skill/mac-gray/prompt/packets/events-w0/prefix.md",
      "body_path": "/home/austinli/Projects/bids_pipeline/data/skill/mac-gray/prompt/packets/events-w0/body.md",
      "rendered_path": "/home/austinli/Projects/bids_pipeline/data/skill/mac-gray/prompt/packets/events-w0/rendered.md",
      "evidence_ids": [
        "0001047469-13-010973:E0356",
        "0001047469-13-010973:E0357",
        "0001047469-13-010973:E0358",
        "0001047469-13-010973:E0359",
        "0001047469-13-010973:E0360",
        "0001047469-13-010973:E0361",
        "0001047469-13-010973:E0362",
        "0001047469-13-010973:E0363",
        "0001047469-13-010973:E0364",
        "0001047469-13-010973:E0365",
        "0001047469-13-010973:E0366",
        "0001047469-13-010973:E0367",
        "0001047469-13-010973:E0368",
        "0001047469-13-010973:E0369",
        "0001047469-13-010973:E0370",
        "0001047469-13-010973:E0371",
        "0001047469-13-010973:E0372",
        "0001047469-13-010973:E0373",
        "0001047469-13-010973:E0374",
        "0001047469-13-010973:E0375",
        "0001047469-13-010973:E0376",
        "0001047469-13-010973:E0377",
        "0001047469-13-010973:E0378",
        "0001047469-13-010973:E0379",
        "0001047469-13-010973:E0380",
        "0001047469-13-010973:E0381",
        "0001047469-13-010973:E0382",
        "0001047469-13-010973:E0383",
        "0001047469-13-010973:E0384",
        "0001047469-13-010973:E0385",
        "0001047469-13-010973:E0386",
        "0001047469-13-010973:E0387",
        "0001047469-13-010973:E0388",
        "0001047469-13-010973:E0389",
        "0001047469-13-010973:E0390",
        "0001047469-13-010973:E0391",
        "0001047469-13-010973:E0392",
        "0001047469-13-010973:E0393",
        "0001047469-13-010973:E0394",
        "0001047469-13-010973:E0395",
        "0001047469-13-010973:E0396",
        "0001047469-13-010973:E0397",
        "0001047469-13-010973:E0398",
        "0001047469-13-010973:E0399",
        "0001047469-13-010973:E0400",
        "0001047469-13-010973:E0401",
        "0001047469-13-010973:E0402",
        "0001047469-13-010973:E0403",
        "0001047469-13-010973:E0404",
        "0001047469-13-010973:E0405",
        "0001047469-13-010973:E0406",
        "0001047469-13-010973:E0407",
        "0001047469-13-010973:E0408",
        "0001047469-13-010973:E0409",
        "0001047469-13-010973:E0410",
        "0001047469-13-010973:E0411",
        "0001047469-13-010973:E0412",
        "0001047469-13-010973:E0413",
        "0001047469-13-010973:E0414",
        "0001047469-13-010973:E0415",
        "0001047469-13-010973:E0416",
        "0001047469-13-010973:E0417",
        "0001047469-13-010973:E0418",
        "0001047469-13-010973:E0419",
        "0001047469-13-010973:E0420",
        "0001047469-13-010973:E0421",
        "0001047469-13-010973:E0422",
        "0001047469-13-010973:E0423",
        "0001047469-13-010973:E0424",
        "0001047469-13-010973:E0425",
        "0001047469-13-010973:E0426",
        "0001047469-13-010973:E0427",
        "0001047469-13-010973:E0428",
        "0001047469-13-010973:E0429",
        "0001047469-13-010973:E0430",
        "0001047469-13-010973:E0431",
        "0001047469-13-010973:E0432",
        "0001047469-13-010973:E0433",
        "0001047469-13-010973:E0434",
        "0001047469-13-010973:E0435",
        "0001047469-13-010973:E0436",
        "0001047469-13-010973:E0437",
        "0001047469-13-010973:E0438",
        "0001047469-13-010973:E0439",
        "0001047469-13-010973:E0440",
        "0001047469-13-010973:E0441"
      ],
      "actor_roster_source_path": "/home/austinli/Projects/bids_pipeline/data/skill/mac-gray/extract/actors_raw.json"
    },
    {
      "packet_id": "events-w1",
      "packet_family": "events",
      "chunk_mode": "chunked",
      "window_id": "w1",
      "prefix_path": "/home/austinli/Projects/bids_pipeline/data/skill/mac-gray/prompt/packets/events-w1/prefix.md",
      "body_path": "/home/austinli/Projects/bids_pipeline/data/skill/mac-gray/prompt/packets/events-w1/body.md",
      "rendered_path": "/home/austinli/Projects/bids_pipeline/data/skill/mac-gray/prompt/packets/events-w1/rendered.md",
      "evidence_ids": [
        "0001047469-13-010973:E0438",
        "0001047469-13-010973:E0439",
        "0001047469-13-010973:E0440",
        "0001047469-13-010973:E0441",
        "0001047469-13-010973:E0442",
        "0001047469-13-010973:E0443",
        "0001047469-13-010973:E0444",
        "0001047469-13-010973:E0445",
        "0001047469-13-010973:E0446",
        "0001047469-13-010973:E0447",
        "0001047469-13-010973:E0448",
        "0001047469-13-010973:E0449",
        "0001047469-13-010973:E0450",
        "0001047469-13-010973:E0451",
        "0001047469-13-010973:E0452",
        "0001047469-13-010973:E0453",
        "0001047469-13-010973:E0454",
        "0001047469-13-010973:E0455",
        "0001047469-13-010973:E0456",
        "0001047469-13-010973:E0457",
        "0001047469-13-010973:E0458",
        "0001047469-13-010973:E0459",
        "0001047469-13-010973:E0460",
        "0001047469-13-010973:E0461",
        "0001047469-13-010973:E0462",
        "0001047469-13-010973:E0463",
        "0001047469-13-010973:E0464",
        "0001047469-13-010973:E0465",
        "0001047469-13-010973:E0466",
        "0001047469-13-010973:E0467",
        "0001047469-13-010973:E0468",
        "0001047469-13-010973:E0469",
        "0001047469-13-010973:E0470",
        "0001047469-13-010973:E0471",
        "0001047469-13-010973:E0472",
        "0001047469-13-010973:E0473",
        "0001047469-13-010973:E0474",
        "0001047469-13-010973:E0475",
        "0001047469-13-010973:E0476",
        "0001047469-13-010973:E0477",
        "0001047469-13-010973:E0478",
        "0001047469-13-010973:E0479",
        "0001047469-13-010973:E0480",
        "0001047469-13-010973:E0481",
        "0001047469-13-010973:E0482",
        "0001047469-13-010973:E0483",
        "0001047469-13-010973:E0484",
        "0001047469-13-010973:E0485",
        "0001047469-13-010973:E0486",
        "0001047469-13-010973:E0487",
        "0001047469-13-010973:E0488",
        "0001047469-13-010973:E0489",
        "0001047469-13-010973:E0490",
        "0001047469-13-010973:E0491",
        "0001047469-13-010973:E0492",
        "0001047469-13-010973:E0493",
        "0001047469-13-010973:E0494",
        "0001047469-13-010973:E0495",
        "0001047469-13-010973:E0496",
        "0001047469-13-010973:E0497",
        "0001047469-13-010973:E0498",
        "0001047469-13-010973:E0499",
        "0001047469-13-010973:E0500",
        "0001047469-13-010973:E0501",
        "0001047469-13-010973:E0502",
        "0001047469-13-010973:E0503",
        "0001047469-13-010973:E0504",
        "0001047469-13-010973:E0505",
        "0001047469-13-010973:E0506",
        "0001047469-13-010973:E0507",
        "0001047469-13-010973:E0508",
        "0001047469-13-010973:E0509",
        "0001047469-13-010973:E0510",
        "0001047469-13-010973:E0511",
        "0001047469-13-010973:E0512",
        "0001047469-13-010973:E0513",
        "0001047469-13-010973:E0514",
        "0001047469-13-010973:E0515",
        "0001047469-13-010973:E0516",
        "0001047469-13-010973:E0517",
        "0001047469-13-010973:E0518",
        "0001047469-13-010973:E0519",
        "0001047469-13-010973:E0520",
        "0001047469-13-010973:E0521",
        "0001047469-13-010973:E0522",
        "0001047469-13-010973:E0523",
        "0001047469-13-010973:E0524",
        "0001047469-13-010973:E0525",
        "0001047469-13-010973:E0526",
        "0001047469-13-010973:E0527",
        "0001047469-13-010973:E0528",
        "0001047469-13-010973:E0529",
        "0001047469-13-010973:E0530",
        "0001047469-13-010973:E0531",
        "0001047469-13-010973:E0532",
        "0001047469-13-010973:E0533",
        "0001047469-13-010973:E0534",
        "0001047469-13-010973:E0535",
        "0001047469-13-010973:E0536",
        "0001047469-13-010973:E0537",
        "0001047469-13-010973:E0538",
        "0001047469-13-010973:E0539",
        "0001047469-13-010973:E0540",
        "0001047469-13-010973:E0541",
        "0001047469-13-010973:E0542",
        "0001047469-13-010973:E0543",
        "0001047469-13-010973:E0544",
        "0001047469-13-010973:E0545",
        "0001047469-13-010973:E0546",
        "0001047469-13-010973:E0547",
        "0001047469-13-010973:E0548",
        "0001047469-13-010973:E0549",
        "0001047469-13-010973:E0550",
        "0001047469-13-010973:E0551",
        "0001047469-13-010973:E0552",
        "0001047469-13-010973:E0553",
        "0001047469-13-010973:E0554",
        "0001047469-13-010973:E0555",
        "0001047469-13-010973:E0556",
        "0001047469-13-010973:E0557",
        "0001047469-13-010973:E0558",
        "0001047469-13-010973:E0559",
        "0001047469-13-010973:E0560",
        "0001047469-13-010973:E0561",
        "0001047469-13-010973:E0562",
        "0001047469-13-010973:E0563",
        "0001047469-13-010973:E0564",
        "0001047469-13-010973:E0565",
        "0001047469-13-010973:E0566"
      ],
      "actor_roster_source_path": "/home/austinli/Projects/bids_pipeline/data/skill/mac-gray/extract/actors_raw.json"
    },
    {
      "packet_id": "events-w2",
      "packet_family": "events",
      "chunk_mode": "chunked",
      "window_id": "w2",
      "prefix_path": "/home/austinli/Projects/bids_pipeline/data/skill/mac-gray/prompt/packets/events-w2/prefix.md",
      "body_path": "/home/austinli/Projects/bids_pipeline/data/skill/mac-gray/prompt/packets/events-w2/body.md",
      "rendered_path": "/home/austinli/Projects/bids_pipeline/data/skill/mac-gray/prompt/packets/events-w2/rendered.md",
      "evidence_ids": [
        "0001047469-13-010973:E0556",
        "0001047469-13-010973:E0557",
        "0001047469-13-010973:E0558",
        "0001047469-13-010973:E0559",
        "0001047469-13-010973:E0560",
        "0001047469-13-010973:E0561",
        "0001047469-13-010973:E0562",
        "0001047469-13-010973:E0563",
        "0001047469-13-010973:E0564",
        "0001047469-13-010973:E0565",
        "0001047469-13-010973:E0566",
        "0001047469-13-010973:E0567",
        "0001047469-13-010973:E0568",
        "0001047469-13-010973:E0569",
        "0001047469-13-010973:E0570",
        "0001047469-13-010973:E0571",
        "0001047469-13-010973:E0572",
        "0001047469-13-010973:E0573",
        "0001047469-13-010973:E0574",
        "0001047469-13-010973:E0575",
        "0001047469-13-010973:E0576",
        "0001047469-13-010973:E0577",
        "0001047469-13-010973:E0578",
        "0001047469-13-010973:E0579",
        "0001047469-13-010973:E0580",
        "0001047469-13-010973:E0581",
        "0001047469-13-010973:E0582"
      ],
      "actor_roster_source_path": "/home/austinli/Projects/bids_pipeline/data/skill/mac-gray/extract/actors_raw.json"
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
    "source_blocks=180",
    "source_evidence_items=1494",
    "chunk_windows=3",
    "complexity=complex"
  ]
}

### mac-gray: validate-events

Command: python scripts/validate_prompt_packets.py --deal mac-gray --expect-sections
PASS: All prompt packets valid for mac-gray.

### mac-gray: extraction-only handoff

- The earlier full-flow worker was stopped for orchestration and throughput reasons before continuing into the remaining extraction and downstream stages.
- The requested handoff state said no extract artifacts had been written, but at takeover time this worker observed `/home/austinli/Projects/bids_pipeline/data/skill/mac-gray/extract/actors_raw.json` already present in the owned worktree.
- This focused worker is taking over the extraction-only half, auditing the existing actor artifact before using it as the event-prompt roster source, and will stop after raw extraction artifacts exist and pass schema validation.

- 2026-03-29T15:10:49+01:00: Previous shell extraction owner had exited without an authoritative final result file. Resumed from the existing validated event-packet checkpoint and kept `actors_raw.json` unchanged.
- 2026-03-29T15:10:49+01:00: Wrote filing-grounded `extract/events_raw.json` from the current `events-w0`/`events-w1`/`events-w2` packets. Extraction handoff complete with both extract artifacts present.

### mac-gray: deterministic-core

- `canonicalize` passed without additional normalization.
- `check` passed.
- `verify` passed.
- `coverage` passed at blocker/error level.
- `gates` passed.
- `enrich-core` passed.

### mac-gray: enrichment-and-export

- Filing-grounded `data/skill/mac-gray/enrich/enrichment.json` was materialized.
- `skill-pipeline db-load --deal mac-gray` passed.
- `skill-pipeline db-export --deal mac-gray` passed.
- Output: `data/skill/mac-gray/export/deal_events.csv` (`29` lines including header).
