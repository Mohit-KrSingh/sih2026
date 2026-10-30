# scripts/seed.ps1 - Seed database with demo data
$ErrorActionPreference = "Stop"

Write-Host "=== Seeding Database and Generating Demo Data ==="
$backendDir = (Resolve-Path "backend").Path
$env:PYTHONPATH = $backendDir
$py = if (Test-Path ".venv\Scripts\python.exe") { (Resolve-Path ".venv\Scripts\python.exe").Path } else { "python" }

& $py -m app.seed
if ($LASTEXITCODE -ne 0) {
    Write-Error "Database seeding failed!"
    exit $LASTEXITCODE
}
