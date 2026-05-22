# 🎯 RSS-Radar — Cheat Sheet

All commands run in Git Bash from the repo root.

---

## ✨ The one command you'll always use

```bash
git pull && start docs/index.html         # Windows
git pull && open docs/index.html          # macOS
git pull && xdg-open docs/index.html      # Linux
```

Or use the helper:
```bash
bash scripts/open_dashboard.sh
```

---

## 🔁 Daily usage

| When | What |
|---|---|
| After a scheduled scan ran | `git pull && open docs/index.html` |
| You want to scan now | Actions tab → "Run workflow" → wait → `git pull` |
| Edit keywords / feeds | Dashboard ⚙️ Settings → 🚀 Save to GitHub |
| Something looks weird | Check the latest Actions log |

---

## ⚡ Trigger a manual scan

In your browser, open: `https://github.com/<your-user>/<your-repo>/actions`

Then: "Daily RSS Radar" → top right "Run workflow" → "Run workflow"

Wait ~3 min, then locally:
```bash
git pull
open docs/index.html
```

---

## ⏰ Change the schedule

Edit `.github/workflows/daily.yml`, change the `cron:` line:

| You want | cron expression |
|---|---|
| Every Monday 20:00 (Istanbul) | `"0 17 * * 1"` |
| Mon + Thu 20:00 | `"0 17 * * 1,4"` |
| Every day 20:00 | `"0 17 * * *"` |
| Weekdays only | `"0 17 * * 1-5"` |
| Every day 9 AM (UTC) | `"0 9 * * *"` |

Cron helper: <https://crontab.guru/>

Then:
```bash
git add .github/workflows/daily.yml
git commit -m "schedule: updated cron"
git push
```

---

## 🔑 Rotate / change API keys

`https://github.com/<your-user>/<your-repo>/settings/secrets/actions`

- Click on `GEMINI_API_KEY` or `GROQ_API_KEY` → **Update** → paste new value
- Will be used on the next run automatically

Get a new key:
- Gemini: <https://aistudio.google.com/apikey>
- Groq: <https://console.groq.com/keys>

---

## 🆘 Troubleshooting

### `git pull` says "conflict"
```bash
git stash
git pull
git stash pop
```

### Tracking a 7-day idle warning?
GitHub disables scheduled workflows after 60 days of repo inactivity.
Just hit "Run workflow" once to re-enable.

### Failed run in Actions
- Click the failed run → expand the failing step
- Most common cause: a provider returning errors → check your Secrets are still valid
- Send me the log if you can't tell what's wrong

---

## 🎓 Shell alias (optional, makes life nicer)

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
alias rss='cd ~/path/to/rss-radar && git pull && open docs/index.html'
```

Then just type `rss` from anywhere.

---

## 📌 TL;DR

**90% of the time, the only command you need is:**

```bash
bash scripts/open_dashboard.sh
```
