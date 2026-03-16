# Project Skills

These skills are a self-contained repo-local bundle under `.codex/skills`.
Each skill includes its full instructions and reference files. There is no
indirection to any other skill tree.

This install is repo-local only. Nothing is copied into `~/.codex/skills`.

To use them in Codex:
1. Start Codex from this repo with `CODEX_HOME` pointed at `.codex`, for example:
   `export CODEX_HOME="$PWD/.codex"`
2. Restart Codex so it reloads repo-local skills.

Each skill directory contains:
- `SKILL.md` -- full instructions with YAML frontmatter (name, description)
- `references/` -- local reference files (e.g., schemas, rules) used by the skill

All required reading paths use local relative paths like `references/foo.md`.
