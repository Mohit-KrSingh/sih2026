# scripts/brand_check.ps1 - Verify no old product brand names remain in the codebase
$ErrorActionPreference = "Stop"

Write-Host "=== Running Brand Check (R01) ===" -ForegroundColor Cyan

$forbiddenPatterns = @(
    "APAAR Platform",
    "apaar-platform",
    "APAAR Central Portal",
    "APAAR Verification Engine",
    "apaar-frontend",
    "apaar-backend",
    "APAAR Student Data Management",
    "AICTE APAAR Platform",
    "AICTE APAAR System",
    "AICTE APAAR"
)

$violations = @()

foreach ($pattern in $forbiddenPatterns) {
    $results = git grep -i -I -E "$pattern" -- ":!node_modules" ":!.venv" ":!.agents" ":!dist" 2>$null
    if ($results) {
        foreach ($line in $results) {
            if ($line -notmatch "scripts/brand_check") {
                $violations += $line
            }
        }
    }
}

if ($violations.Count -gt 0) {
    Write-Host "`n[ERROR] Brand check failed! Found forbidden old product name references:" -ForegroundColor Red
    foreach ($v in $violations) {
        Write-Host "  $v" -ForegroundColor Red
    }
    exit 1
}

Write-Host "No old product name references found across repository." -ForegroundColor Green
Write-Host "Brand check passed successfully!" -ForegroundColor Green
exit 0
