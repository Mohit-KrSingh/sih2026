# scripts/test.ps1 - Run all test suites
$ErrorActionPreference = "Stop"

Write-Host "=== Running Backend Tests (pytest) ==="
$env:PYTHONPATH = (Resolve-Path "backend").Path
$py = Resolve-Path ".venv\Scripts\python.exe"
& $py -m pytest backend/tests
if ($LASTEXITCODE -ne 0) {
    Write-Error "Backend tests failed!"
    exit $LASTEXITCODE
}

Write-Host "`n=== Running Frontend Tests (vitest) ==="
Push-Location frontend
try {
    & cmd.exe /c npm test
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Frontend tests failed!"
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}

Write-Host "`nAll tests passed successfully!"
