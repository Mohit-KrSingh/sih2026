#!/usr/bin/env bash
# scripts/seed.sh - Seed database with demo data (T03)
set -e

echo "=== Seeding Database and Generating Demo Data (T03) ==="
export PYTHONPATH="$(cd backend && pwd)"

if [ -f ".venv/bin/python" ]; then
    .venv/bin/python -m app.seed
else
    python3 -m app.seed
fi
