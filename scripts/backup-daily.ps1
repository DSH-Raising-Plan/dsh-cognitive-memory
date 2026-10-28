# Daily SQLite backup for cognitive-memory.
# Usage:
#   pwsh scripts/backup-daily.ps1
#   pwsh scripts/backup-daily.ps1 -DataDir "D:\data\cognitive-memory"
param(
  [string]$DataDir = "",
  [string]$Python = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Service = Join-Path $Root "service"
if (-not (Test-Path (Join-Path $Service "src\cognitive_memory\main.py"))) {
  throw "service/ missing next to plugin root: $Service"
}

$py = if ($Python) { $Python } elseif ($env:DSH_MEMORY_PYTHON) { $env:DSH_MEMORY_PYTHON } else { "python" }
$env:PYTHONPATH = (Join-Path $Service "src") + [IO.Path]::PathSeparator + ($env:PYTHONPATH)

$args = @("-m", "cognitive_memory.cli", "backup")
if ($DataDir) { $args += @("--data-dir", $DataDir) }

& $py @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
