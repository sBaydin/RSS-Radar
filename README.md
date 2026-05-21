# 📡 RSS Radar — Akademik Literatür Tarayıcı (Ücretsiz)

Her akşam saat **20:00 (TR)** otomatik çalışan akademik literatür tarayıcı.
arXiv, MDPI, Elsevier, Wiley, Springer, ASCE feed'lerini tarar; alanınla
ilgili yayınları LLM ile **Türkçe özetler**, **1–10 ilgi skoru** verir ve
güzel bir **web dashboard** üretir.

**🆓 Tamamen ücretsiz** — Google Gemini + Groq Llama free tier'ları kullanılır,
kredi kartı istemez.

## ⚡ Hızlı başlangıç

`DEPLOY.md` dosyasını oku. ~10 dakikada sıfırdan çalışır hale getirirsin:

1. Google AI Studio'dan ücretsiz Gemini API key al
2. Groq Console'dan ücretsiz Groq API key al (yedek için)
3. GitHub repo oluştur, klasörü push'la
4. Secrets'a iki key'i ekle
5. GitHub Pages'i aç
6. İlk koşuyu tetikle, dashboard hazır

## 🏗 Mimari

```
GitHub Actions (cron)
        ↓
scripts/fetch_and_report.py
        ↓
  ┌──────────────┐
  │ feedparser   │  RSS'ler  (config.yaml)
  └──────┬───────┘
         ↓
  ┌──────────────┐
  │ ön-filtre    │  3 ağırlık (critical×3, core×2, related×1)
  │              │  − exclude×3
  └──────┬───────┘
         ↓
  ┌──────────────┐
  │ LLM özet     │  Gemini → Groq → ...
  │ + skor       │  (yedek varsa otomatik düşer)
  └──────┬───────┘
         ↓
  data/items.json  +  docs/index.html
         ↓
   GitHub Pages   →  https://<user>.github.io/<repo>/
```

## 🎛 Dashboard özellikleri

- ⭐ İlgi skoru (1–10) + "MUTLAKA OKU" rozeti (≥8)
- 🏷️ Etiket bulutu — tıklayınca filtreler
- 🔍 Arama (başlık/özet/etiket)
- ▶️ "Şimdi Tara" — anlık manuel tetikleme (GitHub Actions API)
- ⚙️ Yönetim paneli:
  - Anahtar kelime ekle/sil (4 tier: critical/core/related/exclude)
  - Feed aç/kapat, yenisini ekle
  - Saat:dakika + timezone + hangi günler → otomatik cron'a çevirir
  - LLM provider değiştir (Gemini/Groq/Ollama/OpenAI/Anthropic)
  - 🚀 Tek tıkla GitHub'a commit (config.yaml + workflow)

## 🔌 Desteklenen LLM'ler

| Provider | Ücretsiz | Hız | Türkçe kalitesi | Limit (gün) |
|---|---|---|---|---|
| **gemini** (varsayılan) | ✅ | hızlı | çok iyi | ~500 istek |
| **groq** (yedek) | ✅ | ⚡ ultra hızlı | iyi | ~1000 istek |
| **ollama** | ✅ | yerel | model'e bağlı | sınırsız |
| openai | 💵 | hızlı | mükemmel | — |
| anthropic | 💵 | orta | mükemmel | — |

Birincil fail olursa otomatik yedeğe düşer.

## 📁 Yapı

```
rss-radar/
├── config.yaml                    ← RSS'ler + anahtar kelimeler + ayarlar
├── DEPLOY.md                      ← adım adım kurulum
├── README.md
├── requirements.txt
├── scripts/
│   ├── fetch_and_report.py        ← ana script
│   └── dashboard_template.html    ← web dashboard + yönetim paneli
├── data/
│   ├── items.json                 ← görülen tüm makaleler (dedup)
│   └── runs.json                  ← koşu geçmişi
├── docs/                          ← GitHub Pages'in yayınladığı klasör
│   ├── index.html                 ← dashboard
│   └── config.json                ← panel okuması için canlı kopya
└── .github/workflows/daily.yml    ← her gece otomatik
```

## 🧪 Yerel test

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=AIzaSy...
python scripts/fetch_and_report.py
# docs/index.html dosyasını tarayıcıda aç
```
