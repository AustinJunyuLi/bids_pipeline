from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
HOME = Path.home()
USER_CODEX_CONFIG = HOME / ".codex" / "config.toml"
USER_CODEX_STATE = HOME / ".codex" / ".codex-global-state.json"
REQUIRED_TOOLS = ("rg", "jq", "fd", "uv", "gh", "delta", "bat", "fzf", "codex")
REQUIRED_MCPS = ("github", "filesystem", "playwright", "context7", "openaiDeveloperDocs")
OPTIONAL_ENV_VARS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "BIDS_LLM_PROVIDER",
    "BIDS_LLM_MODEL",
    "GITHUB_PAT",
)
EDGAR_ENV_VARS = ("PIPELINE_SEC_IDENTITY", "SEC_IDENTITY", "EDGAR_IDENTITY")


@dataclass
class CheckResult:
    status: str
    name: str
    detail: str
    required: bool = True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit local Codex readiness for this repository.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when any required check fails.",
    )
    return parser.parse_args()


def run_command(args: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        check=False,
        capture_output=True,
        text=True,
    )


def resolve_command(name: str) -> str | None:
    candidates = [name]
    if platform.system() == "Windows" and not Path(name).suffix:
        candidates.extend(f"{name}{extension}" for extension in (".exe", ".cmd", ".bat", ".ps1"))

    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    if platform.system() == "Windows" and name == "pwsh":
        default_pwsh = Path(r"C:\Program Files\PowerShell\7\pwsh.exe")
        if default_pwsh.exists():
            return str(default_pwsh)
    return None


def status_line(result: CheckResult) -> str:
    return f"[{result.status}] {result.name}: {result.detail}"


def check_tools() -> list[CheckResult]:
    results: list[CheckResult] = []
    for tool in REQUIRED_TOOLS:
        resolved = resolve_command(tool)
        if resolved:
            results.append(CheckResult("PASS", f"tool:{tool}", resolved))
        else:
            results.append(CheckResult("FAIL", f"tool:{tool}", "Command not found"))
    if platform.system() == "Windows":
        resolved = resolve_command("pwsh")
        if resolved:
            results.append(CheckResult("PASS", "tool:pwsh", resolved))
        else:
            results.append(CheckResult("FAIL", "tool:pwsh", "PowerShell 7 is not installed"))
    return results


def expected_python_path() -> Path:
    if platform.system() == "Windows":
        return REPO_ROOT / ".venv" / "Scripts" / "python.exe"
    return REPO_ROOT / ".venv" / "bin" / "python"


def expected_cli_path() -> Path:
    if platform.system() == "Windows":
        return REPO_ROOT / ".venv" / "Scripts" / "skill-pipeline.exe"
    return REPO_ROOT / ".venv" / "bin" / "skill-pipeline"


def check_venv() -> list[CheckResult]:
    results: list[CheckResult] = []
    python_path = expected_python_path()
    cli_path = expected_cli_path()

    if python_path.exists():
        results.append(CheckResult("PASS", "venv:python", str(python_path)))
    else:
        results.append(CheckResult("FAIL", "venv:python", f"Missing {python_path}"))
        return results

    if cli_path.exists():
        results.append(CheckResult("PASS", "venv:skill-pipeline", str(cli_path)))
    else:
        results.append(CheckResult("FAIL", "venv:skill-pipeline", f"Missing {cli_path}"))

    pip_show = run_command([str(python_path), "-m", "pip", "show", "bids-data-pipeline"], cwd=REPO_ROOT)
    if pip_show.returncode != 0:
        results.append(CheckResult("FAIL", "venv:editable-install", pip_show.stderr.strip() or "pip show failed"))
    else:
        editable_location = None
        for line in pip_show.stdout.splitlines():
            if line.startswith("Editable project location:"):
                editable_location = line.split(":", 1)[1].strip()
                break
        if editable_location:
            try:
                same_location = Path(editable_location).resolve() == REPO_ROOT.resolve()
            except FileNotFoundError:
                same_location = False
            if same_location:
                results.append(CheckResult("PASS", "venv:editable-install", editable_location))
            else:
                results.append(
                    CheckResult(
                        "FAIL",
                        "venv:editable-install",
                        f"Editable install points to {editable_location}, expected {REPO_ROOT}",
                    )
                )
        else:
            results.append(CheckResult("WARN", "venv:editable-install", "Editable project location not reported", required=False))

    help_run = run_command([str(cli_path), "--help"], cwd=REPO_ROOT) if cli_path.exists() else None
    if help_run and help_run.returncode == 0:
        results.append(CheckResult("PASS", "venv:cli-help", "skill-pipeline --help succeeded"))
    elif help_run:
        results.append(CheckResult("FAIL", "venv:cli-help", help_run.stderr.strip() or "skill-pipeline --help failed"))

    sync_run = run_command([str(python_path), "scripts/sync_skill_mirrors.py", "--check"], cwd=REPO_ROOT)
    if sync_run.returncode == 0:
        results.append(CheckResult("PASS", "skills:sync-check", sync_run.stdout.strip() or "Skill mirrors are in sync"))
    else:
        results.append(CheckResult("FAIL", "skills:sync-check", sync_run.stderr.strip() or "sync_skill_mirrors.py --check failed"))

    return results


def check_git() -> list[CheckResult]:
    results: list[CheckResult] = []
    gitattributes_path = REPO_ROOT / ".gitattributes"
    if gitattributes_path.is_file():
        text = gitattributes_path.read_text(encoding="utf-8")
        if "eol=lf" in text:
            results.append(CheckResult("PASS", "git:.gitattributes", str(gitattributes_path)))
        else:
            results.append(CheckResult("FAIL", "git:.gitattributes", "Missing eol=lf policy"))
    else:
        results.append(CheckResult("FAIL", "git:.gitattributes", "File is missing"))

    attr_check = run_command(["git", "check-attr", "eol", "--", "pyproject.toml"], cwd=REPO_ROOT)
    if attr_check.returncode == 0 and "lf" in attr_check.stdout:
        results.append(CheckResult("PASS", "git:eol-attr", attr_check.stdout.strip()))
    else:
        results.append(CheckResult("FAIL", "git:eol-attr", attr_check.stderr.strip() or attr_check.stdout.strip() or "git check-attr failed"))

    autocrlf = run_command(["git", "config", "--global", "--get", "core.autocrlf"], cwd=REPO_ROOT)
    autocrlf_value = autocrlf.stdout.strip() if autocrlf.returncode == 0 else ""
    if platform.system() == "Windows":
        if autocrlf_value == "false":
            results.append(CheckResult("PASS", "git:core.autocrlf", "false"))
        else:
            results.append(CheckResult("FAIL", "git:core.autocrlf", f"Expected false, found {autocrlf_value or 'UNSET'}"))
    else:
        if autocrlf_value in {"", "false"}:
            results.append(CheckResult("PASS", "git:core.autocrlf", autocrlf_value or "UNSET"))
        else:
            results.append(CheckResult("WARN", "git:core.autocrlf", autocrlf_value, required=False))
    return results


def check_codex_config() -> list[CheckResult]:
    results: list[CheckResult] = []
    if not USER_CODEX_CONFIG.is_file():
        return [CheckResult("FAIL", "codex:config", f"Missing {USER_CODEX_CONFIG}")]

    with USER_CODEX_CONFIG.open("rb") as handle:
        config = tomllib.load(handle)

    model = config.get("model")
    if model == "gpt-5.4":
        results.append(CheckResult("PASS", "codex:model", model))
    else:
        results.append(CheckResult("FAIL", "codex:model", f"Expected gpt-5.4, found {model!r}"))

    reasoning = config.get("model_reasoning_effort")
    if reasoning == "xhigh":
        results.append(CheckResult("PASS", "codex:default-reasoning", reasoning))
    else:
        results.append(CheckResult("FAIL", "codex:default-reasoning", f"Expected xhigh, found {reasoning!r}"))

    fast_profile = config.get("profiles", {}).get("fast", {})
    fast_reasoning = fast_profile.get("model_reasoning_effort")
    fast_service_tier = fast_profile.get("service_tier")
    if fast_service_tier == "fast" and fast_reasoning in {"minimal", "low", "medium", "high"}:
        results.append(CheckResult("PASS", "codex:fast-profile", f"service_tier={fast_service_tier}, reasoning={fast_reasoning}"))
    else:
        results.append(CheckResult("FAIL", "codex:fast-profile", "Missing profiles.fast with lower reasoning and service_tier=fast"))

    trusted_projects = config.get("projects", {})
    repo_config = trusted_projects.get(str(REPO_ROOT))
    if isinstance(repo_config, dict) and repo_config.get("trust_level") == "trusted":
        results.append(CheckResult("PASS", "codex:trusted-project", str(REPO_ROOT)))
    else:
        results.append(CheckResult("FAIL", "codex:trusted-project", f"Missing trusted-project entry for {REPO_ROOT}"))

    if platform.system() == "Windows":
        windows_config = config.get("windows", {})
        sandbox = windows_config.get("sandbox")
        if sandbox == "elevated":
            results.append(CheckResult("PASS", "codex:windows-sandbox", sandbox))
        else:
            results.append(CheckResult("FAIL", "codex:windows-sandbox", f"Expected elevated, found {sandbox!r}"))

    return results


def check_terminal_state() -> list[CheckResult]:
    if platform.system() != "Windows":
        return []
    if not USER_CODEX_STATE.is_file():
        return [CheckResult("FAIL", "codex:global-state", f"Missing {USER_CODEX_STATE}")]

    payload = json.loads(USER_CODEX_STATE.read_text(encoding="utf-8-sig"))
    shell = payload.get("integratedTerminalShell")
    if shell == "powershell":
        return [CheckResult("PASS", "codex:integrated-terminal", shell)]
    return [CheckResult("FAIL", "codex:integrated-terminal", f"Expected powershell, found {shell!r}")]


def check_mcp() -> list[CheckResult]:
    if platform.system() == "Windows":
        output = run_command(["powershell", "-NoProfile", "-Command", "codex mcp list"], cwd=REPO_ROOT)
    else:
        output = run_command(["codex", "mcp", "list"], cwd=REPO_ROOT)
    if output.returncode != 0:
        return [CheckResult("FAIL", "codex:mcp-list", output.stderr.strip() or "codex mcp list failed")]

    results: list[CheckResult] = [CheckResult("PASS", "codex:mcp-list", "codex mcp list succeeded")]
    stdout = output.stdout
    for name in REQUIRED_MCPS:
        if name in stdout:
            results.append(CheckResult("PASS", f"codex:mcp:{name}", "configured"))
        else:
            results.append(CheckResult("FAIL", f"codex:mcp:{name}", "missing from codex mcp list"))

    if "context7" in stdout and "Not logged in" in stdout:
        results.append(CheckResult("WARN", "codex:mcp:context7-auth", "Context7 is configured but not logged in", required=False))

    return results


def check_env_vars() -> list[CheckResult]:
    results: list[CheckResult] = []
    for key in OPTIONAL_ENV_VARS:
        value = os.environ.get(key)
        if value:
            results.append(CheckResult("PASS", f"env:{key}", "set", required=False))
        else:
            results.append(CheckResult("WARN", f"env:{key}", "unset", required=False))

    if any(os.environ.get(key) for key in EDGAR_ENV_VARS):
        results.append(CheckResult("PASS", "env:EDGAR_IDENTITY", "one of PIPELINE_SEC_IDENTITY/SEC_IDENTITY/EDGAR_IDENTITY is set", required=False))
    else:
        results.append(CheckResult("WARN", "env:EDGAR_IDENTITY", "no EDGAR identity environment variable is set", required=False))
    return results


def gather_results() -> list[CheckResult]:
    results: list[CheckResult] = []
    results.extend(check_tools())
    results.extend(check_venv())
    results.extend(check_git())
    results.extend(check_codex_config())
    results.extend(check_terminal_state())
    results.extend(check_mcp())
    results.extend(check_env_vars())
    return results


def main() -> int:
    args = parse_args()
    results = gather_results()

    for result in results:
        print(status_line(result))

    failures = [result for result in results if result.required and result.status == "FAIL"]
    warnings = [result for result in results if result.status == "WARN"]
    print(f"Summary: {len(failures)} required failure(s), {len(warnings)} warning(s)")

    if args.strict and failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
