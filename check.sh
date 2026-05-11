#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate

echo "==> Black check..."
black --check .

echo "==> isort check..."
isort . --check-only --profile black --filter-files

echo "==> Tests + coverage..."
pytest --cov=. --cov-report=term-missing

echo "==> Bandit..."
bandit -r . -c .bandit.yaml -ll

echo "✅ All checks passed!"
