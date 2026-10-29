#!/usr/bin/env bash
set -e
echo "=== Generating docs/RULES.md from Rule Registry (T18) ==="
export PYTHONPATH=backend
python -m app.validation.rules_doc
echo "docs/RULES.md generated successfully."

