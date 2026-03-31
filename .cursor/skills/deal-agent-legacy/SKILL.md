---
name: deal-agent-legacy
description: Use when you explicitly need the archived v1 event-first workflow with interpretive enrichment and legacy db-export outputs.
---

# deal-agent-legacy

## Status

This is the retired v1 workflow. It is preserved for explicit legacy reruns and
inspection only. The live default is `/deal-agent`.

## Purpose

Run the pre-cutover v1 event-first workflow from filing fetch through
`db-export`, including the mandatory interpretive enrichment layer.

## Benchmark Boundary

Benchmark materials are forbidden during generation. Do not consult benchmark
files, benchmark notes, `example/`, `diagnosis/`,
`data/skill/<slug>/reconcile/*`, or `/reconcile-alex-legacy` before
`skill-pipeline db-export --deal <slug>` completes.

## Procedure

```text
1. skill-pipeline raw-fetch --deal <slug>
2. skill-pipeline preprocess-source --deal <slug>
3. skill-pipeline compose-prompts --deal <slug> --mode actors
4. /extract-deal <slug>
5. skill-pipeline compose-prompts --deal <slug> --mode events
6. skill-pipeline canonicalize --deal <slug>
7. skill-pipeline check --deal <slug>
8. skill-pipeline verify --deal <slug>
9. skill-pipeline coverage --deal <slug>
10. skill-pipeline gates --deal <slug>
11. /verify-extraction <slug>
12. skill-pipeline enrich-core --deal <slug>
13. /enrich-deal <slug>    (mandatory interpretive enrichment)
14. skill-pipeline db-load --deal <slug>
15. skill-pipeline db-export --deal <slug>
16. /reconcile-alex-legacy <slug>    (optional post-export diagnostic)
```

## Live / Archive Split

- Live v2 outputs belong under `data/skill/<slug>/{prompt_v2,extract_v2,...}`.
- Archived v1 outputs belong under `data/legacy/v1/`.
- Do not mix legacy artifacts back into the live v2 surface.
