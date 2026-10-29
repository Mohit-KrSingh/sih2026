# scripts/lint.ps1 - Run linters
$ErrorActionPreference = "Stop"

Write-Host "=== Linting Backend (ruff) ==="
$ruff = Resolve-Path ".venv\Scripts\ruff.exe"
& $ruff check backend
if ($LASTEXITCODE -ne 0) {
    Write-Error "Backend linting failed!"
    exit $LASTEXITCODE
}

Write-Host "`n=== Linting Frontend (eslint) ==="
Push-Location frontend
try {
    & cmd.exe /c npm run lint
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Frontend linting failed!"
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}

Write-Host "`nAll lint checks passed successfully!"
