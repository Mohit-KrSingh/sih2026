#!/usr/bin/env bash
set -e
echo "=== Running Backend Tests (pytest) ==="
PYTHONPATH=backend python -m pytest backend/tests

echo "=== Running Frontend Tests (vitest) ==="
cd frontend && npm test

echo "=== Running E2E & Accessibility Tests (playwright) ==="
npx playwright test e2e/all_routes_axe.spec.ts e2e/lighthouse.spec.ts e2e/keyboard_only_journeys.spec.ts
