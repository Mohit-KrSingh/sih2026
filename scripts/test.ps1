# scripts/test.ps1 - Run all test suites
$ErrorActionPreference = "Stop"

Write-Host "=== Running Backend Tests (pytest) ==="
$env:PYTHONPATH = (Resolve-Path "backend").Path
$py = if (Test-Path ".venv\Scripts\python.exe") { (Resolve-Path ".venv\Scripts\python.exe").Path } else { "python" }
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

Write-Host "`n=== Running E2E & Accessibility Tests (playwright) ==="
Push-Location frontend
try {
    & cmd.exe /c npx playwright test e2e/all_routes_axe.spec.ts e2e/lighthouse.spec.ts e2e/keyboard_only_journeys.spec.ts e2e/presentation_screenshots.spec.ts
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Playwright tests failed!"
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}

Write-Host "`nAll tests passed successfully!"
