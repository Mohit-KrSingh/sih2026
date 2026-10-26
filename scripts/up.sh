#!/usr/bin/env bash
set -e

if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    echo "Starting stack with Docker Compose..."
    docker compose up -d
else
    echo "Docker not detected. Starting services..."
    mkdir -p data/redis storage/uploads
    redis-server --dir data/redis --port 6379 --daemonize yes 2>/dev/null || true
    PYTHONPATH=backend python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
    (cd frontend && npm run dev &)
fi
