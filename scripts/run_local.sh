#!/usr/bin/env bash
# RSS Radar - Lokal koşturma (kendi bilgisayarında, GitHub Actions'ı tetiklemeden)
# .env dosyasını okur, key'leri yükler, taramayı çalıştırır, dashboard'u açar.

set -e
cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  echo "❌ .env yok. Önce:"
  echo "   cp .env.example .env"
  echo "   nano .env  # key'leri doldur"
  exit 1
fi

# .env'deki KEY=value satırlarını yükle
set -a
source .env
set +a

echo "🔎 Tarama başlıyor..."
python scripts/fetch_and_report.py

echo ""
echo "✅ Tamamlandı. Dashboard açılıyor..."
exec scripts/open_dashboard.sh --no-pull
