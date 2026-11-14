# One-time setup for Pinterest Bulk Downloader (Windows PowerShell)
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Check($step) {
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed: $step" -ForegroundColor Red
        exit 1
    }
}

# 1. find Python
$py = $null
foreach ($candidate in @("py", "python", "python3")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) { $py = $candidate; break }
}
if (-not $py) {
    Write-Host "Python was not found. Install it from https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "and tick 'Add python.exe to PATH' during install, then run this again." -ForegroundColor Red
    exit 1
}

# 2. private virtual environment (keeps your system Python clean)
Write-Host "Creating virtual environment (.venv)..." -ForegroundColor Cyan
& $py -m venv .venv
Check "create virtual environment"
$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

# 3. dependencies
Write-Host "Installing requirements..." -ForegroundColor Cyan
& $venvPy -m pip install --upgrade pip
Check "upgrade pip"
& $venvPy -m pip install -r requirements.txt
Check "install requirements"

# 4. Chromium for Playwright (one time, ~150 MB)
Write-Host "Downloading Chromium (one time, ~150 MB)..." -ForegroundColor Cyan
& $venvPy -m playwright install chromium
Check "install Chromium"

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Next: edit topics.txt, then run:  .\run.ps1 download" -ForegroundColor Green
