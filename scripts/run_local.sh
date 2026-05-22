#!/usr/bin/env bash
# RSS-Radar — local run (uses .env keys, doesn't trigger GitHub Actions)
# Reads .env, runs the scan, then opens the dashboard.

set -e
cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  echo "❌ .env not found. First:"
  echo "   cp .env.example .env"
  echo "   nano .env   # fill in your API keys"
  exit 1
fi

# Load KEY=value lines from .env
set -a
source .env
set +a

echo "🔎 Starting scan..."
python scripts/fetch_and_report.py

echo ""
echo "✅ Done. Opening dashboard..."
exec scripts/open_dashboard.sh --no-pull
