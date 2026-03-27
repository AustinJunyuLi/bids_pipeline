Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$pythonPath = Join-Path $repoRoot ".venv\Scripts\python.exe"
$cliPath = Join-Path $repoRoot ".venv\Scripts\skill-pipeline.exe"

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [string[]]$Arguments = @()
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
    }
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "Missing required command: uv"
}

Push-Location $repoRoot
try {
    if (-not (Test-Path $pythonPath)) {
        Invoke-CheckedCommand -FilePath "uv" -Arguments @("venv", ".venv", "--python", "3.13")
    }

    Invoke-CheckedCommand -FilePath "uv" -Arguments @("pip", "install", "--python", $pythonPath, "-e", ".")

    if (-not (Test-Path $cliPath)) {
        throw "Expected CLI entrypoint was not created: $cliPath"
    }

    Invoke-CheckedCommand -FilePath $cliPath -Arguments @("--help")
    Invoke-CheckedCommand -FilePath $pythonPath -Arguments @("scripts/sync_skill_mirrors.py", "--check")
}
finally {
    Pop-Location
}

Write-Host "Bootstrap completed for $repoRoot"
