#!/usr/bin/env bash
set -euo pipefail

echo "=== Running Brand Check (R01) ==="

FORBIDDEN_REGEX="APAAR Platform|apaar-platform|APAAR Central Portal|APAAR Verification Engine|apaar-frontend|apaar-backend|APAAR Student Data Management|AICTE APAAR Platform|AICTE APAAR System|AICTE APAAR"

if git grep -i -I -E "$FORBIDDEN_REGEX" -- ':!node_modules' ':!.venv' ':!.agents' ':!dist' ':!scripts/brand_check*' ; then
    echo ""
    echo "ERROR: Brand check failed! Found old product name references above."
    exit 1
fi

echo "No old product name references found across repository."
echo "Brand check passed successfully!"
exit 0
