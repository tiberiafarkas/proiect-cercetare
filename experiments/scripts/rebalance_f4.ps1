# When the F2 competence job and the LiLT training have finished, restarts the two F4 jobs with more
# threads so that the freed cores are used. Both F4 jobs resume from their stored outputs.
param([int]$Threads = 8)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not $env:UV_PROJECT_ENVIRONMENT) { $env:UV_PROJECT_ENVIRONMENT = "$env:LOCALAPPDATA\cuebind\venv" }
$env:PYTHONUTF8 = '1'
$env:HF_HUB_DISABLE_PROGRESS_BARS = '1'
$uv = if (Get-Command uv -ErrorAction SilentlyContinue) { (Get-Command uv).Source } else { "$env:USERPROFILE\.local\bin\uv.exe" }

function Find-PythonJob([string]$pattern) {
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match $pattern }
}

while (Find-PythonJob 'competence --condition F2|train_lilt\.py') { Start-Sleep 30 }
$f4 = @(Find-PythonJob 'run_sroie\.py" --part (competence --condition F4|removal)')
# Running jobs are stopped and restarted; finished jobs restart too, and exit at once because their
# outputs are complete.
foreach ($p in $f4) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep 5

$env:OMP_NUM_THREADS = "$Threads"
$env:MKL_NUM_THREADS = "$Threads"
$jobs = @(
    @{ Args = @("$root\scripts\run_sroie.py", '--part', 'competence', '--condition', 'F4'); Log = "$root\runs\sroie\competence_F4.part2.log" },
    @{ Args = @("$root\scripts\run_sroie.py", '--part', 'removal'); Log = "$root\runs\sroie\removal_F4.part2.log" }
)
$processes = foreach ($job in $jobs) {
    Start-Process -FilePath $uv -ArgumentList (@('run', '--no-sync', '--project', "`"$root`"", 'python') + ($job.Args | ForEach-Object { "`"$_`"" })) `
        -RedirectStandardOutput $job.Log -RedirectStandardError ($job.Log -replace '\.log$', '.err.log') -NoNewWindow -PassThru
}
Write-Output "Restarted $($processes.Count) F4 job(s) with $Threads threads at $(Get-Date -Format s)"
$processes | Wait-Process
$failed = $processes | Where-Object { $_.ExitCode -ne 0 }
if ($failed) { throw "$(@($failed).Count) job(s) failed; see the .part2.err.log files" }
Write-Output "F4 jobs finished at $(Get-Date -Format s)"
