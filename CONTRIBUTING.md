# Contributing to RSS-Radar

Thanks for your interest! This is a small project but it works for a lot of
people, so contributions are very welcome.

## Easy first issues

- 📰 **Add academic feeds for your field** — open `config.yaml`, add to the `feeds:` list, send a PR
- 🌍 **Translate the dashboard UI** — `scripts/dashboard_template.html`
- 🎯 **Add example keyword profiles** — for chemistry, biology, ML, economics, etc. as separate `examples/*.yaml`
- 🔔 **Add notifiers** — Telegram, Slack, Discord, email
- 🔗 **Add Zotero/Mendeley integration** — auto-export must-read items

## Development setup

```bash
git clone https://github.com/<you>/rss-radar.git
cd rss-radar
pip install -r requirements.txt
pip install pre-commit
pre-commit install        # runs gitleaks on every commit

cp .env.example .env
# edit .env with your API keys

bash scripts/run_local.sh
```

## Code style

- Python 3.11+
- Keep dependencies minimal (current: feedparser, PyYAML, requests, jinja2, python-dateutil)
- Format with `black` (line length 100), lint with `ruff` if you have them
- One-file scripts are fine — readability over architecture

## Pull request checklist

- [ ] `gitleaks` passes (`pre-commit run --all-files`)
- [ ] Script runs end-to-end without errors (`bash scripts/run_local.sh`)
- [ ] If you changed `dashboard_template.html`, open `docs/index.html` in browser and verify
- [ ] README updated if you added a user-facing feature
- [ ] No API keys in commits, ever

## Reporting bugs

Open an issue with:

1. What you expected
2. What happened
3. Relevant log (from `actions` or local run)
4. Your `config.yaml` (with secrets removed!)

## License

By contributing, you agree your contributions will be licensed under MIT.
