# Runs the E3 pilot (vision-language model on the duplicate/edit stimuli); about 1.5 hours on CPU.
# Resumable: rerunning skips queries whose raw outputs are already stored.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not $env:UV_PROJECT_ENVIRONMENT) { $env:UV_PROJECT_ENVIRONMENT = "$env:LOCALAPPDATA\cuebind\venv" }
$env:PYTHONUTF8 = '1'
$env:HF_HUB_DISABLE_PROGRESS_BARS = '1'
$uv = if (Get-Command uv -ErrorAction SilentlyContinue) { 'uv' } else { "$env:USERPROFILE\.local\bin\uv.exe" }
& $uv run --no-sync --project $root python "$root\scripts\run_e3.py"
if ($LASTEXITCODE -ne 0) { throw "E3 run failed with exit code $LASTEXITCODE" }
