# news_scraper.py

import os
import time
import datetime as dt
import requests
import re

import streamlit as st  # ← NEW

# --- Load API keys from env OR Streamlit secrets ---
NEWS_KEY = os.getenv("NEWS_API_KEY", "").strip()
if not NEWS_KEY:
    NEWS_KEY = st.secrets.get("NEWS_API_KEY", "").strip()

FINNHUB_KEY = os.getenv("FINNHUB_API_KEY", "").strip()
if not FINNHUB_KEY:
    FINNHUB_KEY = st.secrets.get("FINNHUB_API_KEY", "").strip()

FINNHUB_URL = "https://finnhub.io/api/v1/company-news"

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

# Regex to detect a ticker‐style symbol
TICKER_RE = re.compile(r"^[A-Z0-9\.\-]{1,6}$")

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
    except Exception:
        return []

    articles = r.json().get("articles", []) or []
    out = []
    for art in articles[:max_items]:
        out.append({
            "title":  art.get("title",      "No headline"),
            "url":    art.get("url",        ""),
            "source": art.get("source", {}).get("name", ""),
        })
    return out

def _fetch_finnhub(symbol: str, days: int, max_items: int) -> list[dict]:
    """
    Query Finnhub company-news endpoint for the last `days` days.
    """
    if not FINNHUB_KEY:
        return []

    today = dt.date.today()
    frm = today - dt.timedelta(days=days)

    params = {
        "symbol": symbol,
        "from":   frm.isoformat(),
        "to":     today.isoformat(),
        "token":  FINNHUB_KEY,
    }

    try:
        r = requests.get(FINNHUB_URL, params=params, timeout=5)
        r.raise_for_status()
    except Exception:
        return []

    data = r.json() or []
    out = []
    for it in data[:max_items]:
        out.append({
            "title":  it.get("headline", "No headline"),
            "url":    it.get("url",      ""),
            "source": it.get("source",   "Finnhub"),
        })
    return out

def get_news_for_symbol(symbol: str, company: str, max_items: int = 5) -> list[dict]:
    """
    Returns up to `max_items` news dicts for a given ticker + company name,
    pulling first from our HQ domain list, then a wider NewsAPI search,
    then Finnhub if still short.
    """
    # 1) Try high-quality domains only
    hq = _fetch_newsapi(symbol, company, max_items, domains=",".join(HQ_DOMAINS))
    if len(hq) >= max_items:
        return hq[:max_items]

    # 2) Top up with a general NewsAPI search
    needed = max_items - len(hq)
    loose = _fetch_newsapi(symbol, company, needed, domains=None)
    combined = hq + loose
    if len(combined) >= max_items:
        return combined[:max_items]

    # 3) Finally, if it's a plausible ticker, try Finnhub
    if TICKER_RE.fullmatch(symbol):
        fb = _fetch_finnhub(symbol, days=7, max_items=max_items - len(combined))
        combined.extend(fb)

    return combined[:max_items]
