#!/usr/bin/env bash
if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    docker compose down 2>/dev/null || true
fi
pkill -f uvicorn 2>/dev/null || true
pkill -f vite 2>/dev/null || true
redis-cli shutdown 2>/dev/null || true
echo "Services stopped."
