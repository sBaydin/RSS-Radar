#!/usr/bin/env bash
# RSS Radar - Lokal dashboard görüntüleyici
# Her gün çalıştırırsın:
#   1) Repo'dan en son değişiklikleri çeker (data/ + docs/)
#   2) Dashboard'u tarayıcıda açar
#
# Kullanım:
#   ./scripts/open_dashboard.sh         # güncelleyip aç
#   ./scripts/open_dashboard.sh --no-pull # sadece aç, internet kullanma

set -e

cd "$(dirname "$0")/.."

if [[ "$1" != "--no-pull" ]]; then
  echo "📥 Son değişiklikler çekiliyor..."
  git pull --ff-only
fi

DASHBOARD="docs/index.html"
if [[ ! -f "$DASHBOARD" ]]; then
  echo "❌ $DASHBOARD bulunamadı. Önce bir kez 'python scripts/fetch_and_report.py' çalıştır."
  exit 1
fi

echo "🌐 Dashboard açılıyor: $DASHBOARD"
# OS-bağımsız aç
if command -v xdg-open &> /dev/null; then
  xdg-open "$DASHBOARD"        # Linux
elif command -v open &> /dev/null; then
  open "$DASHBOARD"            # macOS
elif command -v cmd.exe &> /dev/null; then
  cmd.exe /c start "" "$DASHBOARD"  # WSL
else
  echo "Tarayıcıyı elle aç: file://$(pwd)/$DASHBOARD"
fi
