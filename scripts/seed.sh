#!/usr/bin/env bash
# scripts/seed.sh - Seed database with demo data
set -e

echo "=== Seeding Database and Generating Demo Data ==="
export PYTHONPATH="$(cd backend && pwd)"

if [ -f ".venv/bin/python" ]; then
    .venv/bin/python -m app.seed
else
    python3 -m app.seed
fi
