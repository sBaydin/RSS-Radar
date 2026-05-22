#!/usr/bin/env bash
# RSS-Radar — local dashboard launcher
# Run daily:
#   1) git pull the latest data/ and docs/
#   2) Open the dashboard in your default browser
#
# Usage:
#   ./scripts/open_dashboard.sh           # pull then open
#   ./scripts/open_dashboard.sh --no-pull # just open

set -e

cd "$(dirname "$0")/.."

if [[ "$1" != "--no-pull" ]]; then
  echo "📥 Pulling latest changes..."
  git pull --ff-only
fi

DASHBOARD="docs/index.html"
if [[ ! -f "$DASHBOARD" ]]; then
  echo "❌ $DASHBOARD not found. Run 'python scripts/fetch_and_report.py' first."
  exit 1
fi

echo "🌐 Opening dashboard: $DASHBOARD"
if command -v xdg-open &> /dev/null; then
  xdg-open "$DASHBOARD"             # Linux
elif command -v open &> /dev/null; then
  open "$DASHBOARD"                 # macOS
elif command -v cmd.exe &> /dev/null; then
  cmd.exe /c start "" "$DASHBOARD"  # WSL
else
  echo "Open in your browser manually: file://$(pwd)/$DASHBOARD"
fi
