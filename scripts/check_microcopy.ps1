# scripts/check_microcopy.ps1 - Audit microcopy compliance (Task R12)
$ErrorActionPreference = "Stop"

Write-Host "=== Microcopy Compliance Check ==="
Push-Location frontend
try {
    & node scripts/check-microcopy.mjs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Microcopy check failed!"
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}

Write-Host "Microcopy check passed!"
