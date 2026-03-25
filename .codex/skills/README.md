# Skills

6 active skills for the deal extraction workflow:

| Skill | Purpose |
|---|---|
| `deal-agent` | Orchestrator - interleaves 4 LLM skills with deterministic CLI stages |
| `extract-deal` | Chunked sequential actor + event extraction from SEC filing text |
| `verify-extraction` | Consume deterministic verify/coverage findings, LLM repair loop |
| `enrich-deal` | Interpret deterministic enrichment: dropout, initiation, advisory, counts |
| `export-csv` | Flatten extraction + enrichment into the repo review CSV |
| `reconcile-alex` | Post-export benchmark QA against Alex's spreadsheet |

Usage: `/deal-agent <slug>` for end-to-end generation, or invoke individual
skills. `skill-pipeline deal-agent --deal <slug>` is a separate CLI command
for preflight/summary only. Use `/reconcile-alex <slug>` only after
`/export-csv` completes.
