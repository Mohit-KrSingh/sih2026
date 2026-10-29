#!/usr/bin/env bash
set -e
echo "=== Linting Backend (ruff) ==="
ruff check backend

echo "=== Linting Frontend (eslint) ==="
cd frontend && npm run lint
