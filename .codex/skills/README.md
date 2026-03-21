# Skills

5 active skills for the deal extraction quick workflow:

| Skill | Purpose |
|---|---|
| `deal-agent` | Orchestrator — runs all 4 skills in sequence |
| `extract-deal` | Actor + event extraction from SEC filing text |
| `verify-extraction` | Fact-check extraction, 2-round fix loop |
| `enrich-deal` | Classify bids, segment cycles, judge initiation |
| `export-csv` | Format to the repo review 14-column CSV |

Usage: `/deal-agent <slug>` for end-to-end, or invoke individual skills.
