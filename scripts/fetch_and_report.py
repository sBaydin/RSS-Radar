#!/usr/bin/env python3
"""
RSS Radar - Akademik makale tarayıcı + LLM özetleyici + dashboard üretici.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import yaml
from dateutil import parser as dateparser
from jinja2 import Template

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"
DATA_PATH = ROOT / "data" / "items.json"
RUNS_PATH = ROOT / "data" / "runs.json"
DOCS_PATH = ROOT / "docs" / "index.html"
DOCS_CONFIG_PATH = ROOT / "docs" / "config.json"
TEMPLATE_PATH = ROOT / "scripts" / "dashboard_template.html"


# --------------------------------------------------------------------------- 
# Yardımcılar
# --------------------------------------------------------------------------- 

def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_json(path: Path, default):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def make_id(entry: dict) -> str:
    raw = (entry.get("id") or entry.get("link") or entry.get("title") or "").strip()
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def clean_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_date(entry: dict) -> str:
    for key in ("published", "updated", "created"):
        if entry.get(key):
            try:
                return dateparser.parse(entry[key]).astimezone(timezone.utc).isoformat()
            except Exception:
                pass
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- 
# Ön filtreleme
# --------------------------------------------------------------------------- 

WEIGHTS = {"critical": 3, "core": 2, "related": 1}

def keyword_prescore(text: str, kw: dict) -> tuple[int, list[str]]:
    text_l = text.lower()
    score = 0
    matched: list[str] = []
    for tier, weight in WEIGHTS.items():
        for k in kw.get(tier, []) or []:
            if k.lower() in text_l:
                score += weight
                matched.append(f"{tier}:{k}")
    for k in kw.get("exclude", []) or []:
        if k.lower() in text_l:
            score -= 3
            matched.append(f"EXCL:{k}")
    return score, matched


# --------------------------------------------------------------------------- 
# LLM - dinamik provider yönetimi
# --------------------------------------------------------------------------- 

LLM_SYSTEM = (
    "Sen bir inşaat mühendisliği doktora öğrencisinin literatür asistanısın. "
    "Doktora konusu: 'Deprem sonrası oluşan betonarme yapılardaki hasarların "
    "görsel işleme/derin öğrenme metodları ile tespiti'. "
    "Sana akademik makale başlığı + özeti vereceğim. Sen bana JSON döndüreceksin."
)

LLM_USER_TEMPLATE = """Aşağıdaki yayını değerlendir.

BAŞLIK: {title}
KAYNAK: {source}
ÖZET (İngilizce): {summary}

Bana SADECE şu JSON şemasında cevap ver, başka hiçbir şey yazma. Markdown veya açıklama EKLEME:
{{
  "summary_tr": "<3-5 cümle Türkçe özet: ne yapılmış / hangi yöntem / hangi sonuç>",
  "relevance": <1-10 arası tam sayı, doktora konusuna uygunluk>,
  "why_relevant": "<1 cümle: doktora konusuyla bağlantısı>",
  "tags": ["<en fazla 5 etiket: kebab-case, ör. crack-detection, YOLO, RC-column, dataset>"],
  "must_read": <true/false, ilgi >=8 ise true>
}}"""


# Provider başına free tier limitleri (Mayıs 2026 itibarıyla)
RATE_LIMITS = {
    "gemini":    {"rpm": 8,   "env_key": "GEMINI_API_KEY"},     # 10 RPM'in altında kal
    "groq":      {"rpm": 25,  "env_key": "GROQ_API_KEY"},       # 30 RPM'in altında kal
    "openai":    {"rpm": 60,  "env_key": "OPENAI_API_KEY"},
    "anthropic": {"rpm": 50,  "env_key": "ANTHROPIC_API_KEY"},
    "ollama":    {"rpm": 999, "env_key": None},
}


def extract_json(content: str) -> dict:
    if not content:
        raise ValueError("boş yanıt")
    content = content.strip()
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```\s*$", "", content)
    m = re.search(r"\{[\s\S]*\}", content)
    if m:
        content = m.group(0)
    return json.loads(content)


def call_provider(provider: str, model: str, prompt: str) -> str:
    """Tek bir provider'a çağrı yapar, ham yanıtı döner. Hata varsa exception fırlatır."""

    if provider == "gemini":
        import requests
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("no-key")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        body = {
            "system_instruction": {"parts": [{"text": LLM_SYSTEM}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
        }
        r = requests.post(url, json=body, timeout=60)
        if r.status_code == 429:
            raise RuntimeError("429")
        r.raise_for_status()
        j = r.json()
        return j["candidates"][0]["content"]["parts"][0]["text"]

    elif provider == "groq":
        import requests
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("no-key")
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": LLM_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            },
            timeout=60,
        )
        if r.status_code == 429:
            raise RuntimeError("429")
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    elif provider == "openai":
        from openai import OpenAI
        client = OpenAI()
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": LLM_SYSTEM},
                      {"role": "user", "content": prompt}],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        return resp.choices[0].message.content

    elif provider == "anthropic":
        import anthropic
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=model, max_tokens=800,
            system=LLM_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text

    elif provider == "ollama":
        import requests
        host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        r = requests.post(
            f"{host}/api/generate",
            json={"model": model, "prompt": LLM_SYSTEM + "\n\n" + prompt,
                  "stream": False, "format": "json"},
            timeout=180,
        )
        r.raise_for_status()
        return r.json().get("response", "{}")

    else:
        raise RuntimeError(f"bilinmeyen provider: {provider}")


class LLMRunner:
    """
    Birincil → yedek provider zinciri yönetir.
    Bir provider 3 kez üst üste 429/hata alırsa o koşu için DEVRE DIŞI bırakır.
    """

    def __init__(self, cfg: dict):
        self.attempts = []   # [(provider, model, delay), ...]
        prov = cfg["llm"]["provider"]
        if os.getenv(RATE_LIMITS.get(prov, {}).get("env_key") or ""):
            self.attempts.append(self._make(prov, cfg["llm"]["model"]))
        fb_prov = cfg["llm"].get("fallback_provider")
        fb_mdl = cfg["llm"].get("fallback_model")
        if fb_prov and fb_mdl and fb_prov != prov:
            if RATE_LIMITS.get(fb_prov, {}).get("env_key") is None or \
               os.getenv(RATE_LIMITS.get(fb_prov, {}).get("env_key") or ""):
                self.attempts.append(self._make(fb_prov, fb_mdl))

        self.disabled = set()        # devre dışı bırakılan provider'lar
        self.fail_streak = {}        # provider -> üst üste hata sayısı
        self.last_call = {}          # provider -> son çağrı zamanı (rate limit için)
        self.usage = {}              # provider -> başarılı çağrı sayısı

    @staticmethod
    def _make(provider, model):
        rpm = RATE_LIMITS.get(provider, {}).get("rpm", 30)
        delay = max(0.2, 60.0 / rpm + 0.5)
        return (provider, model, delay)

    def active_providers(self):
        return [a for a in self.attempts if a[0] not in self.disabled]

    def call(self, title: str, summary: str, source: str) -> tuple[dict | None, str | None]:
        """Aktif provider zincirini sırayla dene. (sonuç, kullanılan_provider) döner."""
        prompt = LLM_USER_TEMPLATE.format(
            title=title[:300], source=source[:120], summary=summary[:2000]
        )
        active = self.active_providers()
        if not active:
            return None, None

        for provider, model, delay in active:
            # Bu provider için rate-limit bekleyişi
            last = self.last_call.get(provider, 0)
            wait = delay - (time.time() - last)
            if wait > 0:
                time.sleep(wait)

            try:
                self.last_call[provider] = time.time()
                content = call_provider(provider, model, prompt)
                self.fail_streak[provider] = 0
                self.usage[provider] = self.usage.get(provider, 0) + 1
                result = extract_json(content)
                return result, provider
            except Exception as e:
                err = str(e)
                self.fail_streak[provider] = self.fail_streak.get(provider, 0) + 1
                streak = self.fail_streak[provider]
                print(f"  ! {provider}/{model}: {err}  (üst üste hata: {streak})",
                      file=sys.stderr)

                # 3 üst üste hata = bu koşu için devre dışı
                if streak >= 3:
                    self.disabled.add(provider)
                    remaining = [a[0] for a in self.active_providers()]
                    print(f"  ⊘ {provider} DEVRE DIŞI bırakıldı. "
                          f"Kalan provider'lar: {remaining or '(yok, offline moda geçilecek)'}",
                          file=sys.stderr)
                    if not remaining:
                        return None, None
                # 429'da extra bekleme (sadece o provider için)
                if "429" in err:
                    self.last_call[provider] = time.time() + 5  # +5sn ceza
                # Sonraki provider'a otomatik geçer (loop devam eder)
        return None, None


# --------------------------------------------------------------------------- 
# Ana akış
# --------------------------------------------------------------------------- 

def fetch_feed(feed_cfg: dict) -> list[dict]:
    if feed_cfg.get("enabled") is False:
        print(f"⊘ {feed_cfg['name']} (kapalı)")
        return []
    print(f"→ {feed_cfg['name']}")
    try:
        parsed = feedparser.parse(feed_cfg["url"])
        entries = parsed.entries or []
        print(f"  {len(entries)} item")
        return entries
    except Exception as e:
        print(f"  ! feed hatası: {e}", file=sys.stderr)
        return []


def main() -> int:
    cfg = load_config()
    seen = load_json(DATA_PATH, {"items": {}})
    runs = load_json(RUNS_PATH, {"runs": []})

    seen_items: dict = seen.get("items", {})
    new_items: list[dict] = []

    candidates: list[dict] = []
    for feed_cfg in cfg["feeds"]:
        for entry in fetch_feed(feed_cfg):
            iid = make_id(entry)
            if iid in seen_items:
                continue
            title = clean_html(entry.get("title", ""))
            summary = clean_html(entry.get("summary", "") or entry.get("description", ""))
            text = f"{title} {summary}"
            pre, matched = keyword_prescore(text, cfg["keywords"])
            if pre < 2:
                seen_items[iid] = {
                    "skipped": True, "pre_score": pre,
                    "title": title[:200],
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
                continue
            candidates.append({
                "id": iid,
                "title": title,
                "summary_en": summary,
                "link": entry.get("link", ""),
                "source": feed_cfg["name"],
                "category": feed_cfg["category"],
                "published": parse_date(entry),
                "pre_score": pre,
                "matched_keywords": matched[:10],
            })

    candidates.sort(key=lambda x: x["pre_score"], reverse=True)
    budget = cfg["llm"].get("max_items_per_run", 60)
    to_process = candidates[:budget]

    runner = LLMRunner(cfg)
    chain = [f"{p}/{m}" for p, m, _ in runner.attempts]

    print(f"\n→ {len(candidates)} aday | LLM'e gidecek: {len(to_process)}")
    if chain:
        print(f"  Provider zinciri: {' → '.join(chain)}")
    else:
        print(f"  ⚠ Hiç aktif provider yok → offline mod (sadece ön-skor)")
    print()

    llm_ok = llm_fail = 0
    used_by: dict[str, int] = {}

    for i, c in enumerate(to_process, 1):
        print(f"[{i}/{len(to_process)}] [{c['pre_score']:>2}] {c['title'][:80]}")

        if not runner.attempts:
            result = {
                "summary_tr": "(API key yok – offline) " + c["summary_en"][:400],
                "relevance": min(10, max(1, c["pre_score"])),
                "why_relevant": f"Ön-skor: {c['pre_score']} ({len(c['matched_keywords'])} eşleşme)",
                "tags": ["offline-mode"],
                "must_read": c["pre_score"] >= 8,
            }
            llm_provider_used = "offline"
        else:
            result, llm_provider_used = runner.call(c["title"], c["summary_en"], c["source"])
            if result:
                llm_ok += 1
                used_by[llm_provider_used] = used_by.get(llm_provider_used, 0) + 1
                print(f"      ✓ {llm_provider_used}  (skor: {result.get('relevance','?')}/10)")
            else:
                llm_fail += 1
                llm_provider_used = "failed"
                result = {
                    "summary_tr": "(LLM zinciri başarısız) " + c["summary_en"][:400],
                    "relevance": min(10, max(1, c["pre_score"])),
                    "why_relevant": "Tüm provider'lar hata verdi, ön-skor kullanıldı.",
                    "tags": ["llm-failed"],
                    "must_read": False,
                }

        item = {**c, **result,
                "llm_provider_used": llm_provider_used,
                "processed_at": datetime.now(timezone.utc).isoformat()}
        seen_items[c["id"]] = item
        new_items.append(item)

        # Eğer tüm provider'lar devre dışıysa erken çık ve kalan makaleleri ön-skorla işle
        if runner.attempts and not runner.active_providers():
            print(f"\n  ⚠ Tüm provider'lar devre dışı. Kalan {len(to_process)-i} makale "
                  f"offline modda (ön-skor) işlenecek.\n", file=sys.stderr)

    save_json(DATA_PATH, {"items": seen_items})
    runs["runs"].append({
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "new_count": len(new_items),
        "processed_count": len(to_process),
        "candidates": len(candidates),
        "provider_chain": chain,
        "used_by": used_by,
        "llm_ok": llm_ok,
        "llm_fail": llm_fail,
    })
    runs["runs"] = runs["runs"][-90:]
    save_json(RUNS_PATH, runs)

    save_json(DOCS_CONFIG_PATH, cfg)
    render_dashboard(seen_items, runs, cfg)
    print(f"\n✓ Tamam. {len(new_items)} yeni item | LLM: ✓{llm_ok}  ✗{llm_fail}")
    print(f"  Kullanım: {used_by}")
    print(f"  Dashboard: {DOCS_PATH}")
    return 0


def render_dashboard(items: dict, runs: dict, cfg: dict) -> None:
    threshold = cfg["llm"].get("relevance_threshold", 4)
    processed = [
        v for v in items.values()
        if not v.get("skipped") and (v.get("relevance") or 0) >= threshold
    ]
    processed.sort(key=lambda x: (
        x.get("must_read", False),
        x.get("relevance", 0),
        x.get("processed_at", "")
    ), reverse=True)

    all_tags: dict[str, int] = {}
    sources: dict[str, int] = {}
    for it in processed:
        for t in (it.get("tags") or []):
            all_tags[t] = all_tags.get(t, 0) + 1
        s = it.get("source", "?")
        sources[s] = sources.get(s, 0) + 1

    kw_counts = {tier: len(cfg["keywords"].get(tier, []) or []) for tier in ["critical","core","related","exclude"]}

    tpl = Template(TEMPLATE_PATH.read_text(encoding="utf-8"))
    html = tpl.render(
        items=processed,
        tags=sorted(all_tags.items(), key=lambda x: -x[1]),
        sources=sorted(sources.items(), key=lambda x: -x[1]),
        runs=runs.get("runs", [])[-14:][::-1],
        profile=cfg["profile"],
        total_seen=len(items),
        total_shown=len(processed),
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        threshold=threshold,
        kw_counts=kw_counts,
        feed_count=sum(1 for f in cfg["feeds"] if f.get("enabled", True)),
        feed_total=len(cfg["feeds"]),
        llm_provider=cfg["llm"]["provider"],
        llm_model=cfg["llm"]["model"],
    )
    DOCS_PATH.parent.mkdir(parents=True, exist_ok=True)
    inline = '<script id="inline-config" type="application/json">' + \
             json.dumps(cfg, ensure_ascii=False) + '</script>'
    html = html.replace('</body>', inline + '\n</body>')
    DOCS_PATH.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
