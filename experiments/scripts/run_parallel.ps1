# Runs the remaining SROIE transfer tests and the LiLT training in parallel, each job with its own
# output file and a fixed number of CPU threads (4 jobs x 4 threads on a 16-core CPU).
# Every job is resumable; logs are written next to the outputs.
param([int]$Threads = 4)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not $env:UV_PROJECT_ENVIRONMENT) { $env:UV_PROJECT_ENVIRONMENT = "$env:LOCALAPPDATA\cuebind\venv" }
$env:PYTHONUTF8 = '1'
$env:HF_HUB_DISABLE_PROGRESS_BARS = '1'
$env:OMP_NUM_THREADS = "$Threads"
$env:MKL_NUM_THREADS = "$Threads"
$uv = if (Get-Command uv -ErrorAction SilentlyContinue) { (Get-Command uv).Source } else { "$env:USERPROFILE\.local\bin\uv.exe" }
New-Item -ItemType Directory -Force "$root\runs\sroie", "$root\runs\lilt" | Out-Null
$jobs = @(
    @{ Args = @("$root\scripts\run_sroie.py", '--part', 'competence', '--condition', 'F2'); Log = "$root\runs\sroie\competence_F2.log" },
    @{ Args = @("$root\scripts\run_sroie.py", '--part', 'competence', '--condition', 'F4'); Log = "$root\runs\sroie\competence_F4.log" },
    @{ Args = @("$root\scripts\run_sroie.py", '--part', 'removal'); Log = "$root\runs\sroie\removal_F4.log" },
    @{ Args = @("$root\scripts\train_lilt.py"); Log = "$root\runs\lilt\run.log" }
)
$processes = foreach ($job in $jobs) {
    Start-Process -FilePath $uv -ArgumentList (@('run', '--no-sync', '--project', "`"$root`"", 'python') + ($job.Args | ForEach-Object { "`"$_`"" })) `
        -RedirectStandardOutput $job.Log -RedirectStandardError ($job.Log -replace '\.log$', '.err.log') -NoNewWindow -PassThru
}
$processes | Wait-Process
$failed = $processes | Where-Object { $_.ExitCode -ne 0 }
if ($failed) { throw "$(@($failed).Count) job(s) failed; see the .err.log files" }
