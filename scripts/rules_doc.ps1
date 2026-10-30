# scripts/rules_doc.ps1 - Generate docs/RULES.md
$ErrorActionPreference = "Stop"

Write-Host "=== Generating docs/RULES.md from Rule Registry ==="
$backendDir = (Resolve-Path "backend").Path
$env:PYTHONPATH = $backendDir
$py = if (Test-Path ".venv\Scripts\python.exe") { (Resolve-Path ".venv\Scripts\python.exe").Path } else { "python" }

& $py -m app.validation.rules_doc
if ($LASTEXITCODE -ne 0) {
    Write-Error "Rules documentation generation failed!"
    exit $LASTEXITCODE
}
Write-Host "docs/RULES.md generated successfully."

