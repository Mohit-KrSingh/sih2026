#!/bin/sh
set -e

echo "=== EduTrace Backend Startup ==="

# Run Alembic migrations to ensure database schema is up-to-date
echo "Applying database migrations (Alembic)..."
alembic upgrade head

# Run seed script if AUTO_SEED is set to true
if [ "$AUTO_SEED" = "true" ]; then
    echo "Running database seed..."
    python -m app.seed || echo "Seed completed or skipped existing data."
fi

echo "Starting Uvicorn server on port 8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
