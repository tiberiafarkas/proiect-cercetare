# Fine-tunes LiLT (condition F3) on the training templates and answers the E2 pilot items.
# About 20 minutes on a 32-core CPU.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not $env:UV_PROJECT_ENVIRONMENT) { $env:UV_PROJECT_ENVIRONMENT = "$env:LOCALAPPDATA\cuebind\venv" }
$env:PYTHONUTF8 = '1'
$env:HF_HUB_DISABLE_PROGRESS_BARS = '1'
$uv = if (Get-Command uv -ErrorAction SilentlyContinue) { 'uv' } else { "$env:USERPROFILE\.local\bin\uv.exe" }
& $uv run --no-sync --project $root python "$root\scripts\train_lilt.py"
if ($LASTEXITCODE -ne 0) { throw "LiLT training failed with exit code $LASTEXITCODE" }
