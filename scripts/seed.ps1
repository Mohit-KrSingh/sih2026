# scripts/seed.ps1 - Seed database with demo data (T03)
$ErrorActionPreference = "Stop"

Write-Host "=== Seeding Database and Generating Demo Data (T03) ==="
$backendDir = (Resolve-Path "backend").Path
$env:PYTHONPATH = $backendDir
$py = Resolve-Path ".venv\Scripts\python.exe"

& $py -m app.seed
if ($LASTEXITCODE -ne 0) {
    Write-Error "Database seeding failed!"
    exit $LASTEXITCODE
}
