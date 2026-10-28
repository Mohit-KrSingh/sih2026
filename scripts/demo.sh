#!/usr/bin/env bash
# scripts/demo.sh - Reset to scripted demo state (T40)
# Usage: make demo  (or: bash scripts/demo.sh)
set -euo pipefail

echo ""
echo "================================================================"
echo "  APAAR Platform - Resetting to Scripted Demo State (T40)      "
echo "================================================================"
echo ""

export PYTHONPATH=backend
python scripts/demo_reset.py

echo ""
echo "================================================================"
echo "  Demo state ready. Start the stack with: make up              "
echo "  Then follow demo/DEMO.md for the click-by-click walkthrough. "
echo "================================================================"
echo ""
