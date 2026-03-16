# Bids Pipeline Setup Design

## Goal

Set up persistent agent guidance for this project and create a public GitHub
repository named `bids_pipeline` without moving the current working directory.

## Chosen Approach

Use the current `bids_data` folder as the project root, add both `AGENTS.md`
and an always-on Cursor rule, initialize git in place, and create a GitHub
repository named `bids_pipeline` as the remote origin.

## Artifacts

- `AGENTS.md` at the repo root for human-readable project guidance
- `.cursor/rules/project-guidance.mdc` as an always-apply Cursor rule
- local `.git/` repository initialized in the current directory
- GitHub remote repository named `bids_pipeline`

## Guidance Content

The guidance should tell future agents that:

- `deal-extraction-skills/` is the reference specification
- `pipeline/` is the Python implementation attempt
- filings are the factual source of truth
- proposals are raw events first, judgments later
- frozen filing text must not be rewritten downstream
- deterministic policy logic belongs in Python, not hidden in prompts
- the current repo is not fully runnable end-to-end because the provider layer
  is still abstract

## Non-Goals

- renaming the local `bids_data` folder
- implementing the missing provider backend
- creating commits or pushing code unless explicitly requested later
