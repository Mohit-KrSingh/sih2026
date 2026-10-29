#!/usr/bin/env bash
set -e
echo "=== Running Backend Tests (pytest) ==="
PYTHONPATH=backend python -m pytest backend/tests

echo "=== Running Frontend Tests (vitest) ==="
cd frontend && npm test
