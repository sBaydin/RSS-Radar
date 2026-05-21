#!/usr/bin/env python3
"""
RSS Radar - Akademik makale tarayıcı + LLM özetleyici + dashboard üretici.

Desteklenen LLM'ler (hepsi ÜCRETSİZ):
  - gemini  : Google Gemini (önerilen, free tier kredi kartı istemez)
  - groq    : Groq Cloud (Llama 3.3 70B, ultra hızlı, free)
  - ollama  : Yerel model (tam ücretsiz, internet bile gerekmez)
  - openai  : OpenAI (ücretli)
  - anthropic: Anthropic Claude (ücretli)
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
# LLM çağrısı - çoklu provider + rate limiting
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


# Provider başına free tier rate limits (RPM = requests per minute)
RATE_LIMITS = {
    "gemini":    {"rpm": 10,  "env_key": "GEMINI_API_KEY"},
    "groq":      {"rpm": 28,  "env_key": "GROQ_API_KEY"},      # 30 RPM'in altında kal
    "openai":    {"rpm": 60,  "env_key": "OPENAI_API_KEY"},
    "anthropic": {"rpm": 50,  "env_key": "ANTHROPIC_API_KEY"},
    "ollama":    {"rpm": 999, "env_key": None},
}


def extract_json(content: str) -> dict:
    """LLM cevabından JSON'u çıkar, markdown code fence varsa temizle."""
    if not content:
        raise ValueError("boş yanıt")
    content = content.strip()
    # ```json ... ``` veya ``` ... ``` temizle
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```\s*$", "", content)
    # İlk { ile son } arasını al (LLM bazen önce/sonra açıklama yazar)
    m = re.search(r"\{[\s\S]*\}", content)
    if m:
        content = m.group(0)
    return json.loads(content)


def call_provider(provider: str, model: str, prompt: str) -> str:
    """Tek bir provider'a çağrı yapar, ham yanıtı döner."""

    if provider == "gemini":
        import requests
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY environment değişkeni yok")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        body = {
            "system_instruction": {"parts": [{"text": LLM_SYSTEM}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }
        r = requests.post(url, json=body, timeout=60)
        if r.status_code == 429:
            raise RuntimeError("rate-limit (429)")
        r.raise_for_status()
        j = r.json()
        return j["candidates"][0]["content"]["parts"][0]["text"]

    elif provider == "groq":
        import requests
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY environment değişkeni yok")
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}",
                     "Content-Type": "application/json"},
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
            raise RuntimeError("rate-limit (429)")
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    elif provider == "openai":
        from openai import OpenAI
        client = OpenAI()
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": LLM_SYSTEM},
                {"role": "user", "content": prompt},
            ],
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
            json={"model": model,
                  "prompt": LLM_SYSTEM + "\n\n" + prompt,
                  "stream": False, "format": "json"},
            timeout=180,
        )
        r.raise_for_status()
        return r.json().get("response", "{}")

    else:
        raise RuntimeError(f"Bilinmeyen provider: {provider}")


def call_llm(title: str, summary: str, source: str, cfg: dict) -> dict | None:
    """Birincil provider + opsiyonel yedek ile dene."""
    primary = cfg["llm"]["provider"]
    model = cfg["llm"]["model"]
    fallback_provider = cfg["llm"].get("fallback_provider")
    fallback_model = cfg["llm"].get("fallback_model")

    prompt = LLM_USER_TEMPLATE.format(
        title=title[:300], source=source[:120], summary=summary[:2000]
    )

    attempts = [(primary, model)]
    if fallback_provider and fallback_model:
        attempts.append((fallback_provider, fallback_model))

    last_err = None
    for prov, mdl in attempts:
        try:
            content = call_provider(prov, mdl, prompt)
            return extract_json(content)
        except Exception as e:
            last_err = f"{prov}/{mdl}: {e}"
            print(f"  ! {last_err}", file=sys.stderr)
            # Rate-limit'se kısa bekle, sonra yedeğe geç
            if "429" in str(e) or "rate" in str(e).lower():
                time.sleep(8)
    return None


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

    provider = cfg["llm"]["provider"]
    env_key = RATE_LIMITS.get(provider, {}).get("env_key")
    has_key = (env_key is None) or bool(os.getenv(env_key))
    rpm = RATE_LIMITS.get(provider, {}).get("rpm", 30)
    delay = max(0.2, 60.0 / rpm + 0.3)   # rate-limit'e ekstra güvenlik payı

    print(f"\n→ {len(candidates)} aday | LLM'e gidecek: {len(to_process)}")
    print(f"  Provider: {provider} | Model: {cfg['llm']['model']} | "
          f"Bekleme: {delay:.1f}s/istek (RPM~{rpm})")
    if not has_key:
        print(f"  ⚠ {env_key} bulunamadı → offline mod (sadece ön-skor)")
    print()

    llm_ok = llm_fail = 0
    for i, c in enumerate(to_process, 1):
        print(f"[{i}/{len(to_process)}] [{c['pre_score']:>2}] {c['title'][:80]}")
        if not has_key:
            result = {
                "summary_tr": "(LLM çağrılmadı – API key yok) " + c["summary_en"][:400],
                "relevance": min(10, max(1, c["pre_score"])),
                "why_relevant": f"Ön-skor: {c['pre_score']} "
                                f"({len(c['matched_keywords'])} eşleşme)",
                "tags": ["offline-mode"],
                "must_read": c["pre_score"] >= 8,
            }
        else:
            result = call_llm(c["title"], c["summary_en"], c["source"], cfg)
            if result:
                llm_ok += 1
            else:
                llm_fail += 1
                # LLM tamamen başarısızsa ön-skoru kullan
                result = {
                    "summary_tr": "(LLM başarısız) " + c["summary_en"][:400],
                    "relevance": min(10, max(1, c["pre_score"])),
                    "why_relevant": "LLM hata verdi, ön-skor kullanıldı.",
                    "tags": ["llm-failed"],
                    "must_read": False,
                }
            time.sleep(delay)

        item = {**c, **result, "processed_at": datetime.now(timezone.utc).isoformat()}
        seen_items[c["id"]] = item
        new_items.append(item)

    save_json(DATA_PATH, {"items": seen_items})
    runs["runs"].append({
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "new_count": len(new_items),
        "processed_count": len(to_process),
        "candidates": len(candidates),
        "provider": provider,
        "llm_ok": llm_ok,
        "llm_fail": llm_fail,
    })
    runs["runs"] = runs["runs"][-90:]
    save_json(RUNS_PATH, runs)

    save_json(DOCS_CONFIG_PATH, cfg)
    render_dashboard(seen_items, runs, cfg)
    print(f"\n✓ Tamam. {len(new_items)} yeni item | LLM: ✓{llm_ok}  ✗{llm_fail}")
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
    # Lokal kullanım için config'i HTML'e inline göm (file:// CORS sorununu çözer)
    inline = '<script id="inline-config" type="application/json">' + \
             json.dumps(cfg, ensure_ascii=False) + '</script>'
    html = html.replace('</body>', inline + '\n</body>')
    DOCS_PATH.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
