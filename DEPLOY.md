# 🚀 RSS-Radar — Deploy Guide (Completely Free, Privacy-First)

This setup is privacy-conscious:

| Component | Where | Visibility |
|---|---|---|
| Code (repo) | GitHub Public | 🌍 public (Secrets stay private) |
| API keys | GitHub Secrets | 🔒 only you + Actions |
| Scanning (cron) | GitHub Actions | 🔒 only you control it |
| Results (`data/` + `docs/`) | The same public repo | 🌍 files public, but no one knows the URL |
| Dashboard | **Your machine only** | 🔒 local `file://` |

You get the benefits of a public repo (free Actions, free hosting) **without**
exposing a dashboard URL anyone can find. You pull the latest `docs/index.html`
locally and open it in your browser.

---

## STEP 1 — Get free API keys (~3 min)

### 1A. Google Gemini (primary)
1. <https://aistudio.google.com/apikey>
2. Sign in with your Google account
3. Click **"Create API Key"** → create in a new project
4. Copy the `AIzaSy...` key

✅ No credit card · ~250 requests/day · we use ~60

### 1B. Groq (backup, highly recommended)
1. <https://console.groq.com/keys>
2. Sign in with Google or GitHub
3. **"Create API Key"** → name it → copy the `gsk_...` key

✅ No credit card · ~1000 requests/day · ultra fast

---

## STEP 2 — Create your GitHub repo

### Option A: Fork
1. Go to <https://github.com/sBaydin/RSS-Radar>
2. Click **Fork** (top right)
3. Done

### Option B: Use as template / clone
1. <https://github.com/new>
2. Name: `rss-radar` · **Public** (required for free Actions)
3. Don't add README · Create

Then clone:
```bash
git clone https://github.com/sBaydin/RSS-Radar.git rss-radar
cd rss-radar
git remote set-url origin https://github.com/<your-username>/rss-radar.git
git push -u origin main
```

> **Public but safe?** Yes. Code is open, **Secrets are encrypted**.
> Nobody can read your API keys — not even forkers.

---

## STEP 3 — Add Secrets

In your repo → **Settings → Secrets and variables → Actions → New repository secret**

| Name | Value |
|---|---|
| `GEMINI_API_KEY` | `AIzaSy...` (from 1A) |
| `GROQ_API_KEY` | `gsk_...` (from 1B, optional but recommended) |

> Once you save a secret, you can **never read it back** — only overwrite.
> Actions logs auto-mask them as `***`.

---

## STEP 4 — DO NOT enable GitHub Pages

In **Settings → Pages**, leave Source as **None**.

This is intentional: the dashboard is local-only, no public URL.

---

## STEP 5 — Install the pre-commit hook (prevents accidental key commits)

```bash
pip install pre-commit
pre-commit install
```

From now on, every `git commit` runs **gitleaks** automatically. If you ever
accidentally write an API key into a file and try to commit it, the commit is
**rejected** before it reaches GitHub. The same scan also runs inside Actions
as a second layer.

---

## STEP 6 — Create your local `.env` file

```bash
cp .env.example .env
nano .env       # or: code .env / notepad .env
```

`.env` is in `.gitignore`, so it **never gets pushed**. It's only used for
local runs.

---

## STEP 7 — Customize `config.yaml`

Open `config.yaml` and replace the example **keywords** and **feeds** with
your own field's terms. The repo ships with a config for "post-earthquake
RC damage detection" — use it as inspiration, but you'll get much better
results with your own keywords.

You can also edit through the dashboard UI later (Settings → Keywords).

---

## STEP 8 — First run

### A. Local first (faster, easier to debug)
```bash
bash scripts/run_local.sh
```
The dashboard opens in your browser automatically.

### B. Or via GitHub Actions
1. In your repo → **Actions** tab
2. **"Daily RSS Radar"** → **"Run workflow"** → **"Run workflow"**
3. Wait ~3-4 min (green ✓)
4. Locally:
   ```bash
   bash scripts/open_dashboard.sh
   ```
   Pulls the latest `docs/` and opens the dashboard.

---

## 🔁 Daily usage

### The only thing you do day-to-day:

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

This script:
1. Pulls the latest `data/items.json` + `docs/index.html` (Actions ran overnight)
2. Opens the dashboard in your browser

Optional shell alias:
```bash
# add to ~/.bashrc or ~/.zshrc
alias rss='cd ~/projects/rss-radar && ./scripts/open_dashboard.sh'
```

Then just type `rss` from anywhere.

---

## 🛠️ Admin panel (in the local dashboard)

After opening the dashboard:
- ⚙️ **Settings** modal — edit keywords, feeds, schedule, threshold
- ▶️ **Run now** button — trigger an Actions run (requires a PAT, see below)

### Personal Access Token (only needed for panel commit / "Run now")

If you want the panel to commit changes back to GitHub or trigger workflows:

1. <https://github.com/settings/personal-access-tokens/new>
2. Repository access: only your `rss-radar` repo
3. Permissions:
   - Contents: Read & write
   - Actions: Read & write
4. Generate → paste into dashboard ⚙️ → 🐙 GitHub tab → Save

> **Only use this on your own device.** The token is stored only in your
> browser's `localStorage`, never sent anywhere except GitHub directly.

> Don't want to use the panel commit? Just edit `config.yaml` by hand,
> `git commit && git push`. Same result, no PAT needed.

---

## 💰 Cost

| Component | Monthly |
|---|---|
| GitHub Actions (public repo) | $0 |
| Gemini API (free tier) | $0 |
| Groq API (free tier) | $0 |
| **TOTAL** | **$0** 🎉 |

---

## 🆘 Troubleshooting

### "rate-limit (429)" repeatedly
The primary provider's rate limit was hit. After 3 consecutive errors the
script auto-disables it for that run and the fallback takes over.
If it's a recurring problem, lower `max_items_per_run` in `config.yaml`.

### Local dashboard says "config could not be loaded"
The dashboard now embeds the config inline at build time. If you see this
error, your `docs/index.html` is from an old build. Run
`bash scripts/run_local.sh` once to regenerate.

### "Workflow not triggering on schedule"
GitHub disables scheduled workflows if a repo has no activity for 60 days.
Just run it manually once from the Actions tab — schedules become active again.

### `git pull` "conflict"
You edited `config.yaml` locally, Actions committed a different change:
```bash
git pull --rebase
```

### "gitleaks not found" during commit
```bash
pre-commit install --install-hooks
```
This downloads the gitleaks binary automatically.

### Pages 404
Expected — Pages is intentionally disabled.

---

## 🔒 Security summary

| Risk | Mitigation |
|---|---|
| Keys in code | ✅ GitHub Secrets + `.env` (gitignored) |
| Dashboard URL leak | ✅ Pages off, local `file://` only |
| Accidental key commit | ✅ `gitleaks` pre-commit + Actions check |
| PAT on another device | ✅ stored only in your browser `localStorage` |
| Free-tier abuse | ✅ `max_items_per_run` + per-provider RPM limiter |
| If a key leaks anyway | Free-tier keys, rotate in 30 sec at provider |

---

## 🤝 Contributing

PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).
