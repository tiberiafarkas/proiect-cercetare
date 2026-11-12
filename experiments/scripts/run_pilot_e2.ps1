# Runs the E2 pilot for conditions F1, F2 and F4 in sequence (about 3 hours on a 32-core CPU).
# Resumable: rerunning skips queries whose raw outputs are already stored.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not $env:UV_PROJECT_ENVIRONMENT) { $env:UV_PROJECT_ENVIRONMENT = "$env:LOCALAPPDATA\cuebind\venv" }
$env:PYTHONUTF8 = '1'
$env:HF_HUB_DISABLE_PROGRESS_BARS = '1'
$uv = if (Get-Command uv -ErrorAction SilentlyContinue) { 'uv' } else { "$env:USERPROFILE\.local\bin\uv.exe" }
foreach ($condition in 'F1', 'F2', 'F4') {
    & $uv run --no-sync --project $root python "$root\scripts\run_e2.py" --condition $condition
    if ($LASTEXITCODE -ne 0) { throw "Condition $condition failed with exit code $LASTEXITCODE" }
}
