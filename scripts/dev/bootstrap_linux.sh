#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")"/../.. && pwd)"
python_path="$repo_root/.venv/bin/python"
cli_path="$repo_root/.venv/bin/skill-pipeline"

if ! command -v uv >/dev/null 2>&1; then
  echo "Missing required command: uv" >&2
  exit 1
fi

cd "$repo_root"

if [[ ! -x "$python_path" ]]; then
  uv venv .venv --python 3.13
fi

uv pip install --python "$python_path" -e .

if [[ ! -x "$cli_path" ]]; then
  echo "Expected CLI entrypoint was not created: $cli_path" >&2
  exit 1
fi

"$cli_path" --help >/dev/null
"$python_path" scripts/sync_skill_mirrors.py --check

echo "Bootstrap completed for $repo_root"
