param([int]$Port = 8765)
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$incidentPython = $null
$incidentLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($incidentLauncher) {
    & $incidentLauncher.Source -3 -m incidentlens.server --port $Port
    exit $LASTEXITCODE
}
$incidentCommand = Get-Command python -ErrorAction SilentlyContinue
if ($incidentCommand -and $incidentCommand.Source -notlike "*WindowsApps*") {
    $incidentPython = $incidentCommand.Source
}
$incidentBundled = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if (-not $incidentPython -and (Test-Path -LiteralPath $incidentBundled)) {
    $incidentPython = $incidentBundled
}
if (-not $incidentPython) {
    throw "No usable Python 3.10+ found. Nothing has been installed. Select an existing Python interpreter."
}
& $incidentPython -m incidentlens.server --port $Port
