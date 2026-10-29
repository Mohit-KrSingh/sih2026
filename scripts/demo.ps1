# scripts/demo.ps1 - Reset to scripted demo state (T40)
# Usage: make demo  (or: powershell -ExecutionPolicy Bypass -File scripts/demo.ps1)
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  APAAR Platform - Resetting to Scripted Demo State (T40)      " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$backendDir = (Resolve-Path "backend").Path
$env:PYTHONPATH = $backendDir
$py = if (Test-Path ".venv\Scripts\python.exe") { (Resolve-Path ".venv\Scripts\python.exe").Path } else { "python" }

& $py scripts/demo_reset.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Demo reset failed!"
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  Demo state ready. Start the stack with: make up              " -ForegroundColor Green
Write-Host "  Then follow demo/DEMO.md for the click-by-click walkthrough. " -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
