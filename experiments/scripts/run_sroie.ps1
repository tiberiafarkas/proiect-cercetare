# Runs the SROIE transfer tests (report, Section 5.3): competence for F1, F2 and F4, then removal for F4.
# About 2.5 hours on a 32-core CPU. Resumable: rerunning skips queries whose raw outputs are already stored.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not $env:UV_PROJECT_ENVIRONMENT) { $env:UV_PROJECT_ENVIRONMENT = "$env:LOCALAPPDATA\cuebind\venv" }
$env:PYTHONUTF8 = '1'
$env:HF_HUB_DISABLE_PROGRESS_BARS = '1'
$uv = if (Get-Command uv -ErrorAction SilentlyContinue) { 'uv' } else { "$env:USERPROFILE\.local\bin\uv.exe" }
foreach ($condition in 'F1', 'F2', 'F4') {
    & $uv run --no-sync --project $root python "$root\scripts\run_sroie.py" --part competence --condition $condition
    if ($LASTEXITCODE -ne 0) { throw "Competence $condition failed with exit code $LASTEXITCODE" }
}
& $uv run --no-sync --project $root python "$root\scripts\run_sroie.py" --part removal
if ($LASTEXITCODE -ne 0) { throw "Removal failed with exit code $LASTEXITCODE" }
