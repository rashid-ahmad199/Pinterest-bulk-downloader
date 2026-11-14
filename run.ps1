# Run Pinterest Bulk Downloader (Windows PowerShell)
#   .\run.ps1 download                      download 500 images per topic
#   .\run.ps1 filter                        remove corrupt / tiny / duplicate images
#   .\run.ps1 status                        show kept / rejected counts
#   .\run.ps1 download -Target 1000 -Topics topics\tshirt_design.txt
param(
    [Parameter(Position = 0)]
    [ValidateSet("download", "filter", "status")]
    [string]$Command = "download",
    [int]$Target = 500,
    [string]$Topics = "topics.txt",
    [int]$MinSize = 500
)

Set-Location $PSScriptRoot
$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Host "Run the setup first:  powershell -ExecutionPolicy Bypass -File .\setup.ps1" -ForegroundColor Yellow
    exit 1
}

& $venvPy pinterest_downloader.py $Command --target $Target --topics $Topics --min-size $MinSize
