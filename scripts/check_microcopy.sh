#!/usr/bin/env bash
# scripts/check_microcopy.sh - Audit microcopy compliance
set -e

echo "=== Microcopy Compliance Check ==="
cd frontend && node scripts/check-microcopy.mjs
echo "Microcopy check passed!"
