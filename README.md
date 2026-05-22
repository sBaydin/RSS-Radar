# 📡 RSS-Radar for Academic Papers

> Your daily, AI-summarized literature radar — runs on autopilot, costs $0.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Made with Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Powered by Gemini & Groq](https://img.shields.io/badge/LLM-Gemini%20%2B%20Groq-orange.svg)](#-llm-providers)
[![GitHub Actions](https://img.shields.io/badge/Automated-GitHub%20Actions-2088FF.svg?logo=githubactions&logoColor=white)](https://github.com/features/actions)
[![Free Tier](https://img.shields.io/badge/Cost-%240%2Fmonth-success.svg)](#-cost)

**RSS-Radar** scans dozens of academic RSS feeds every day (arXiv, MDPI,
Elsevier, Wiley, Springer, ASCE, …), filters them through your custom
keywords, and uses a free LLM (Gemini or Groq) to summarize the most
relevant papers in your own language with a 1–10 relevance score.

Built for PhD students, researchers, and anyone who wants to stay on top
of a fast-moving field without drowning in alerts.

---

## ✨ What you get

- 🤖 **Daily auto-scan** — runs on GitHub Actions on a cron schedule
- 🎯 **Smart pre-filtering** — 3-tier keyword weighting (critical × 3, core × 2, related × 1) minus exclude
- 🆓 **LLM summaries in your language** — free tier of Gemini 2.5 Flash or Groq Llama 3.3 70B
- ⭐ **1–10 relevance scoring** — "must read" badge on the top picks
- 🏷️ **Auto-tagging** — clickable tag filter
- 🔍 **Local dashboard** — no public URL, no privacy concerns, just `file://` on your machine
- ⚙️ **Browser-based admin panel** — edit keywords, feeds, schedule from the dashboard, commits directly to GitHub
- ▶️ **"Run now" button** — trigger a scan on demand via the GitHub Actions API
- 🔒 **Security-first** — secrets in GitHub Secrets, gitleaks pre-commit hook, no dashboard exposed publicly

---

## 🚀 Quick Start (10 minutes)

See [**DEPLOY.md**](DEPLOY.md) for the full step-by-step guide. TL;DR:

1. Fork this repo (or use it as a template)
2. Get **free** API keys:
   - Google Gemini: <https://aistudio.google.com/apikey> (no credit card)
   - Groq (backup): <https://console.groq.com/keys> (no credit card)
3. Add them as GitHub Secrets (`GEMINI_API_KEY`, `GROQ_API_KEY`)
4. Edit `config.yaml` with your keywords + RSS feeds
5. Trigger the workflow once from the **Actions** tab
6. Open `docs/index.html` locally — done!

---

## 🏗 Architecture

```
GitHub Actions (cron)
        ↓
scripts/fetch_and_report.py
        ↓
  ┌──────────────┐
  │ feedparser   │  RSS feeds (config.yaml)
  └──────┬───────┘
         ↓
  ┌──────────────┐
  │ pre-filter   │  3-tier keyword weights minus exclude
  └──────┬───────┘
         ↓
  ┌──────────────────────────┐
  │ LLM with provider chain  │  Groq → Gemini → … (auto-fallback)
  │ + per-provider rate ctrl │  + disables a provider after 3 errors
  └──────┬───────────────────┘
         ↓
  data/items.json  +  docs/index.html
         ↓
   Commit back to repo (private results, public code)
         ↓
   You pull locally → open dashboard
```

---

## 🎛 Dashboard preview

The dashboard shows:

- ⭐ Relevance score (1–10) with a **MUST READ** badge for ≥ 8
- 🏷️ Tag cloud filtering
- 🔍 Full-text search (title, summary, tags)
- 📊 Source breakdown + 14-day run history
- ⚙️ Built-in admin panel:
  - Add/remove keywords across 4 tiers
  - Toggle feeds on/off, add new ones
  - Set local time + timezone + weekdays → auto-converts to UTC cron
  - Switch LLM provider (Gemini, Groq, Ollama, OpenAI, Anthropic)
  - 🚀 One-click "Commit to GitHub" (updates both `config.yaml` and the workflow's cron)

---

## ⚙️ Configuration

Everything lives in **`config.yaml`**. Edit it directly, or use the
admin panel inside the dashboard.

### Keywords (the most important part)

Four tiers, each with a different weight in the pre-filter score:

```yaml
keywords:
  critical:        # weight × 3  — the heart of your topic
    - "post-earthquake"
    - "crack detection"
    - "rapid visual screening"
  core:            # weight × 2  — your field's backbone
    - "reinforced concrete"
    - "YOLO"
    - "U-Net"
  related:         # weight × 1  — contextual
    - "dataset"
    - "transfer learning"
  exclude:         # weight × -3 — off-topic terms that share vocabulary
    - "medical imaging"
    - "autonomous driving"
```

A paper's pre-score is computed from its title + abstract. Only papers
with score ≥ 2 go to the LLM, saving free-tier quota.

### Feeds

Each feed has `name`, `url`, `category`, and `enabled` flag:

```yaml
feeds:
  - name: "arXiv cs.CV"
    url: "http://export.arxiv.org/rss/cs.CV"
    category: "preprint"
    enabled: true

  - name: "MDPI Sensors"
    url: "https://www.mdpi.com/rss/journal/sensors"
    category: "journal"
    enabled: true
```

The repo ships with 24 academic feeds covering computer vision, civil
engineering, structural health monitoring, earthquake engineering, and
more. Use them as inspiration or replace them with your own.

### LLM provider chain

Primary + automatic fallback:

```yaml
llm:
  provider: "groq"
  model: "llama-3.3-70b-versatile"
  fallback_provider: "gemini"
  fallback_model: "gemini-2.5-flash"
  language: "en"   # summary language — "tr", "es", "fr", "de", ...
  max_items_per_run: 60
  relevance_threshold: 4
```

If a provider returns 3 consecutive errors (rate limit, server error),
it gets disabled **for that run only** and the fallback takes over. No
quota wasted.

### Schedule

Set the time in your local timezone — the cron expression updates automatically when you save from the dashboard:

```yaml
schedule_utc: "0 17 * * 1"   # Monday 20:00 Europe/Istanbul
schedule_local:
  hour: 20
  minute: 0
  tz_offset: 3
  days: "1"                  # 1 = Monday, "*" = every day, "1,4" = Mon+Thu
```

---

## 🤖 LLM providers

| Provider | Free? | Speed | Quality | Daily limit |
|---|---|---|---|---|
| **Groq** (Llama 3.3 70B) | ✅ no card | ⚡ ultra fast | very good | ~1000 req |
| **Gemini** (2.5 Flash) | ✅ no card | fast | excellent | ~250 req |
| **Ollama** (local) | ✅ offline | depends on model | depends on model | unlimited |
| OpenAI (gpt-4o-mini) | 💵 paid | fast | excellent | — |
| Anthropic (Claude) | 💵 paid | medium | excellent | — |

For typical use (~60 papers/day), the free tiers are more than enough.

---

## 💰 Cost

| Component | Monthly cost |
|---|---|
| GitHub Actions (public repo) | $0 |
| Gemini API (free tier) | $0 |
| Groq API (free tier) | $0 |
| GitHub Pages | not used (dashboard is local) |
| **Total** | **$0** 🎉 |

---

## 🔒 Privacy & Security

- 🔑 **API keys** live only in GitHub Secrets (encrypted, never readable, masked in logs)
- 🌐 **Dashboard is not publicly hosted** — GitHub Pages is intentionally disabled. You open `docs/index.html` locally with `file://`, no URL anyone can find
- 🛡️ **gitleaks pre-commit hook + Actions check** — prevents accidentally committing keys
- 🎫 **Optional PAT for the panel** — stored only in your browser's `localStorage`, never sent anywhere except GitHub API directly
- 📂 The repo (code) is public, the **results** (your daily summaries) are committed to it too — these are just public paper abstracts, no personal data

---

## 🧪 Local development

```bash
git clone https://github.com/<your-username>/rss-radar.git
cd rss-radar
pip install -r requirements.txt

# Set API keys
cp .env.example .env
# edit .env, paste your keys

# Run
bash scripts/run_local.sh        # Linux/macOS
scripts\open_dashboard.bat       # Windows
```

The dashboard opens in your browser automatically.

---

## 🤝 Contributing

PRs welcome! See [CONTRIBUTING.md](CONTRIBUTING.md). Easy first issues:

- Add more academic feeds for underrepresented fields
- Improve the prompt for non-English summaries
- Add a Telegram/Slack/Discord notifier
- Add Zotero/Mendeley integration for must-read items
- Translate the dashboard UI to your language

---

## 📜 License

MIT — see [LICENSE](LICENSE). Use, fork, modify, sell — just don't hold me liable.

---

## 🙏 Acknowledgments

Built originally for tracking literature on **post-earthquake damage
detection in RC buildings using computer vision**, then generalized so
anyone can adapt it to any field. If it helps you stay on top of your
field, a ⭐ on GitHub means a lot.

---

<sub>Made with ❤️ for researchers who'd rather read papers than write feed parsers.</sub>
