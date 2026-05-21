# 🚀 RSS Radar — Güvenli Deploy Rehberi (TAMAMEN ÜCRETSİZ)

Bu kurulum **gizlilik öncelikli**:

| Bileşen | Nerede | Görünürlük |
|---|---|---|
| Repo (kod) | GitHub Public | 🌍 herkese açık (ama Secrets gizli) |
| API key'ler | GitHub Secrets | 🔒 sadece sen + Actions |
| Tarama (cron) | GitHub Actions | 🔒 sadece sen yönetirsin |
| Sonuçlar (data + dashboard HTML) | Repo'daki `data/` ve `docs/` | 🌍 dosyalar public, ama URL'i kimse bilmiyor |
| Dashboard | **Sadece senin bilgisayarın** | 🔒 lokal `file://` |

Sonuç: Public repo'nun avantajlarını (ücretsiz Actions) kullanırız ama
dashboard'a kimse browser ile erişemez. Dashboard'u sen `scripts/open_dashboard.sh`
ile lokal aç, repo'dan son `docs/index.html` çekilip tarayıcında açılır.

---

## ADIM 1 — Ücretsiz API key'leri al (~3 dk)

### 1A. Google Gemini (birincil)
1. <https://aistudio.google.com/apikey>
2. **"Create API Key"** → projeyle birlikte
3. `AIzaSy...` ile başlayan anahtarı kopyala

✅ Kredi kartı YOK · 500 istek/gün · biz 60 kullanıyoruz

### 1B. Groq (yedek — önerilir)
1. <https://console.groq.com/keys>
2. **"Create API Key"** → ad ver → `gsk_...` kopyala

✅ Kredi kartı YOK · 1000 istek/gün

---

## ADIM 2 — GitHub repo oluştur

1. <https://github.com/new>
2. Name: `rss-radar` · **Public** seç (ücretsiz Actions için)
3. README ekleme, boş bırak → Create

> **Public ama güvenli mi?** Evet. Kod açık, **Secrets şifreli**. Kimse
> key'lerini göremez, fork edenler bile. Pages açmadığımız için
> dashboard URL'i de yok.

---

## ADIM 3 — Yerel klasörü push'la

```bash
cd rss-radar
git init
git add .
git commit -m "init: RSS Radar"
git branch -M main
git remote add origin https://github.com/<KULLANICI_ADIN>/rss-radar.git
git push -u origin main
```

---

## ADIM 4 — Secrets ekle

Repo → **Settings → Secrets and variables → Actions → New repository secret**

| Name | Value |
|---|---|
| `GEMINI_API_KEY` | `AIzaSy...` (1A'dan) |
| `GROQ_API_KEY` | `gsk_...` (1B'den, opsiyonel ama önerilir) |

> Secret bir kez girilince **geri okuyamazsın** (sadece üstüne yazabilirsin).
> Actions log'ları otomatik `***` ile maskeler.

---

## ADIM 5 — GitHub Pages'i AÇMA (önemli!)

Settings → Pages → Source: **None** olarak kalsın.

Dashboard URL'i public'te olmayacak, sadece senin lokalinde açılacak.

---

## ADIM 6 — Pre-commit hook'u kur (kazara key push'lamayı engeller)

```bash
pip install pre-commit
pre-commit install
```

Bundan sonra her `git commit`'te **gitleaks** otomatik çalışır. Eğer kazara
bir API key'i bir dosyaya yazıp commit'lersen, **commit reddedilir** ve
sen düzeltmeden push edemezsin. Aynı tarama GitHub Actions'da da çalışıyor —
yani iki katmanlı koruma.

---

## ADIM 7 — Lokal `.env` dosyasını oluştur (lokal koşturma için)

```bash
cp .env.example .env
nano .env   # veya: code .env / notepad .env
```

`.env` dosyası `.gitignore`'da olduğu için **asla push'lanmaz**, sadece
senin makinende kalır.

---

## ADIM 8 — İlk koşuyu tetikle

### A. Lokal'den (önerilen, hızlı)
```bash
bash scripts/run_local.sh
```
Dashboard otomatik tarayıcıda açılır.

### B. GitHub Actions'dan
1. Repo'da **Actions** sekmesi
2. **"Daily RSS Radar"** → **Run workflow**
3. ~2-3 dakika bekle (yeşil ✓)
4. Lokal'de:
   ```bash
   bash scripts/open_dashboard.sh
   ```
   (Repo'dan son halini çekip dashboard'u açar.)

---

## 🔁 Günlük kullanım

### Senin yapacağın tek şey: her akşam bir komut

**Linux / macOS:**
```bash
cd rss-radar
./scripts/open_dashboard.sh
```

**Windows:**
```cmd
cd rss-radar
scripts\open_dashboard.bat
```

Bu komut:
1. GitHub'dan son `data/items.json` + `docs/index.html`'i çeker (Actions her gece koşmuş)
2. Dashboard'u tarayıcında açar
3. Kimse internetten URL'ine erişemez

İstersen alias yap:
```bash
# ~/.bashrc veya ~/.zshrc'e ekle
alias rss='cd ~/projects/rss-radar && ./scripts/open_dashboard.sh'
```

Sonra her akşam sadece `rss` yazman yeter.

---

## 🛠️ Yönetim paneli (lokal dashboard'da)

Dashboard'u açtıktan sonra:
- ⚙️ **Ayarlar** ile anahtar kelime, feed, saat değiştir
- ▶️ **Şimdi Tara** ile Actions'ı tetikle (PAT gerekiyor)

### Personal Access Token (sadece panel için, opsiyonel)
Panel commit / Şimdi Tara için PAT gerekiyor. **Sadece kendi cihazından**
kullanırsan localStorage'da güvenli kalır:

1. <https://github.com/settings/personal-access-tokens/new>
2. Repository access: `rss-radar` seç
3. Permissions:
   - Contents: Read & write
   - Actions: Read & write
4. Generate token → dashboard ⚙️ → 🐙 GitHub sekmesi → yapıştır

> **Başka cihazda asla yapma** — sadece kendi laptop/desktop'unda.

> Panel commit özelliğini kullanmak istemiyorsan: `config.yaml`'ı elle
> düzenle, `git commit && git push`. Aynı sonuç, PAT gerekmez.

---

## 💰 Maliyet

| Bileşen | Aylık |
|---|---|
| GitHub Actions (public repo) | $0 |
| Gemini API (free tier) | $0 |
| Groq API (free tier) | $0 |
| **TOPLAM** | **$0** 🎉 |

---

## 🔒 Güvenlik özeti — ne yapılmış?

| Risk | Çözüm |
|---|---|
| Key'ler kod içinde | ✅ GitHub Secrets + `.env` (gitignore'da) |
| Pages public, dashboard URL'i sızar | ✅ Pages kapalı, sadece lokal `file://` |
| Kazara key commit'lemek | ✅ `gitleaks` pre-commit hook + Actions kontrolü |
| PAT'in başkasının cihazına geçmesi | ✅ Sadece kendi tarayıcı localStorage'ında |
| Free tier kötüye kullanımı | ✅ `max_items_per_run` + RPM rate limiter |
| API key sızsa ne olur? | Gemini/Groq free tier, yenisini al, eskisini sil |

---

## 🆘 Sorun giderme

### "gitleaks not found" pre-commit hatası
```bash
pre-commit install --install-hooks
```
gitleaks binary'sini otomatik indirir.

### Lokal dashboard "config yüklenemedi" hatası
`docs/index.html` doğrudan tarayıcıda açılıyor olabilir. `inline-config`
otomatik gömülüyor — eğer eski bir dashboard varsa `scripts/run_local.sh`
ile yeniden üret.

### Pages 404
Beklenen davranış — Pages bilerek kapalı.

### "Rate-limit (429)"
Gemini saatlik limit doldu, Groq devraldı. Bir sonraki koşuda Gemini geri gelir.

### `git pull` "conflict" diyor
Sen lokal `config.yaml` değiştirdin, Actions başka değişiklik commit'ledi:
```bash
git pull --rebase
```
