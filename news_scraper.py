# news_scraper.py

import os
import time
import datetime as dt
import requests
import re

# NewsAPI.org key (in your .env)
NEWS_KEY = os.getenv("NEWS_API_KEY", "").strip()

# Only truly high-quality business/finance sites:
HQ_DOMAINS = [
    "bloomberg.com",
    "ft.com",
    "wsj.com",
    "cnbc.com",
    "reuters.com",
    "markets.ft.com",
    "marketwatch.com",
]

# Finnhub fallback (unchanged)
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY", "").strip()
FINNHUB_URL = "https://finnhub.io/api/v1/company-news"

# Valid tickers only
TICKER_RE = re.compile(r"^[A-Z]{1,5}$")


def _fetch_newsapi(symbol: str, company: str, max_items: int, domains: str | None) -> list[dict]:
    """
    Query NewsAPI.org:
      - If `domains` is a comma-joined string of HQ_DOMAINS, we restrict to those.
      - If `domains` is None, we search everything.
    """
    if not NEWS_KEY:
        return []
    params = {
        "apiKey": NEWS_KEY,
        "qInTitle": f"{symbol} OR \"{company}\"",
        "pageSize": max_items,
        "language": "en",
        "sortBy": "publishedAt",
    }
    if domains:
        params["domains"] = domains

    try:
        r = requests.get("https://newsapi.org/v2/everything", params=params, timeout=5)
        r.raise_for_status()
        arts = r.json().get("articles", [])
        return [
            {"title": a["title"], "url": a["url"], "source": a["source"]["name"]}
            for a in arts
        ]
    except Exception:
        return []


def _fetch_finnhub(symbol: str, days: int = 7, max_items: int = 3) -> list[dict]:
    if not FINNHUB_KEY:
        return []
    try:
        today = dt.date.today()
        frm = today - dt.timedelta(days=days)
        params = {
            "symbol": symbol,
            "from": frm.isoformat(),
            "to": today.isoformat(),
            "token": FINNHUB_KEY,
        }
        r = requests.get(FINNHUB_URL, params=params, timeout=5)
        r.raise_for_status()
        data = r.json()[:max_items]
        out = []
        for it in data:
            out.append({
                "title":  it.get("headline",    "No headline"),
                "url":    it.get("url",         ""),
                "source": it.get("source",      "Finnhub"),
            })
            time.sleep(1)
        return out
    except Exception:
        return []


def get_news_for_symbol(symbol: str, company: str, max_items: int = 5) -> list[dict]:
    """
    1) Try NewsAPI restricted to HQ_DOMAINS.
    2) If fewer than max_items, top up with a looser NewsAPI search.
    3) If still none AND it's a ticker, fallback to Finnhub.
    """
    # 1) HQ domains
    hq = _fetch_newsapi(symbol, company, max_items, domains=",".join(HQ_DOMAINS))
    if len(hq) >= max_items:
        return hq[:max_items]

    # 2) Top up with general search
    needed = max_items - len(hq)
    loose = _fetch_newsapi(symbol, company, needed, domains=None)
    combined = hq + loose
    if len(combined) >= max_items:
        return combined[:max_items]

    # 3) If still short *and* symbol is a real ticker, try Finnhub
    if TICKER_RE.fullmatch(symbol):
        fb = _fetch_finnhub(symbol, days=7, max_items=max_items - len(combined))
        combined.extend(fb)

    return combined[:max_items]
