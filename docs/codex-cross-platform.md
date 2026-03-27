# Codex Cross-Platform Setup

This repo is designed for one shared Git history and separate machine-local Codex environments.

## What stays in Git

- `.gitattributes` for LF normalization across Windows and Linux.
- `scripts/dev/bootstrap_windows.ps1` and `scripts/dev/bootstrap_linux.sh` for repo-local environment bootstrap.
- `scripts/dev/codex_doctor.py` for repeatable local audits.
- `.claude/skills/` as the canonical skill tree plus the mirrored `.codex/skills/` and `.cursor/skills/` trees.

## What stays local

Do not sync these through GitHub:

- `~/.codex/config.toml`
- `~/.codex/auth.json` and MCP login state
- Codex app preferences such as the integrated terminal shell
- `.venv/`
- `.env*`
- `.agents/`
- `.claude/settings.json`

## Windows setup

1. Install the native CLI tools:

```powershell
winget install BurntSushi.ripgrep.MSVC
winget install jqlang.jq
winget install sharkdp.fd
winget install astral-sh.uv
winget install GitHub.cli
winget install dandavison.delta
winget install sharkdp.bat
winget install junegunn.fzf
winget install Microsoft.PowerShell
```

2. Keep Git line endings machine-local and repo-safe:

```powershell
git config --global core.autocrlf false
```

3. Use this repo bootstrap:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev/bootstrap_windows.ps1
python scripts/dev/codex_doctor.py --strict
```

4. In the Codex app, keep the agent on native Windows and set the integrated terminal to the `PowerShell` option after installing PowerShell 7.

5. Add local project actions in the Codex app:

- Tests: `pytest -q tests/test_skill_pipeline.py tests/test_skill_mirror_sync.py`
- Skill sync: `python scripts/sync_skill_mirrors.py --check`

## Fedora setup

1. Install the Linux CLI tools:

```bash
sudo dnf install -y ripgrep jq fd-find gh delta bat fzf
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Mirror the user-level Codex config locally in `~/.codex/config.toml`. Keep the same model and profiles as Windows, but omit Windows-only keys.

3. Use this repo bootstrap:

```bash
bash scripts/dev/bootstrap_linux.sh
python scripts/dev/codex_doctor.py --strict
```

4. Add the same local project actions in the Codex app using the Linux command forms.

## Recommended local Codex config

Keep these settings local on each machine:

```toml
model = "gpt-5.4"
model_reasoning_effort = "xhigh"
personality = "pragmatic"

[features]
multi_agent = true

[profiles.fast]
model = "gpt-5.4"
model_reasoning_effort = "medium"
service_tier = "fast"
personality = "pragmatic"
```

Add machine-specific entries separately:

- Windows: `windows.sandbox = "elevated"`
- Trusted-project paths for the local clone
- MCP servers and auth details

## Notes

- `skill-pipeline` is intentionally env-local. Activate the repo `.venv` on each machine before using the CLI interactively.
- `context7` may remain unauthenticated without blocking the repo bootstrap.
- `edgartools-mcp` is intentionally out of scope for this setup.
