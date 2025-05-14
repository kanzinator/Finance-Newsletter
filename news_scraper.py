# news_scraper.py

import os
import datetime as dt
import requests
import re

import streamlit as st

# Load API keys from env OR Streamlit secrets
NEWS_KEY    = os.getenv("NEWS_API_KEY", "").strip() or st.secrets["NEWS_API_KEY"]
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY", "").strip() or st.secrets["FINNHUB_API_KEY"]

FINNHUB_URL = "https://finnhub.io/api/v1/company-news"

HQ_DOMAINS = [
    "bloomberg.com", "ft.com", "wsj.com",
    "cnbc.com", "reuters.com", "markets.ft.com",
    "marketwatch.com",
]
TICKER_RE = re.compile(r"^[A-Z0-9\.\-]{1,6}$")


def _fetch_newsapi(symbol: str, company: str, max_items: int, domains: str | None) -> list[dict]:
    if not NEWS_KEY:
        return []
    params = {
        "apiKey":   NEWS_KEY,
        "qInTitle": f"{symbol} OR \"{company}\"",
        "pageSize": max_items,
        "language": "en",
        "sortBy":   "publishedAt",
    }
    if domains:
        params["domains"] = domains

    try:
        r = requests.get("https://newsapi.org/v2/everything", params=params, timeout=5)
        r.raise_for_status()
    except Exception:
        return []

    articles = r.json().get("articles", []) or []
    return [
        {
            "title":  a.get("title",     "No headline"),
            "url":    a.get("url",       ""),
            "source": a.get("source", {}).get("name", "")
        }
        for a in articles[:max_items]
    ]


def _fetch_finnhub(symbol: str, days: int, max_items: int) -> list[dict]:
    if not FINNHUB_KEY:
        return []

    today = dt.date.today()
    frm   = today - dt.timedelta(days=days)
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
    return [
        {"title": it.get("headline","No headline"),
         "url":   it.get("url",""),
         "source":it.get("source","Finnhub")}
        for it in data[:max_items]
    ]


def get_news_for_symbol(symbol: str, company: str, max_items: int = 5) -> list[dict]:
    # 1) HQ domains
    hq = _fetch_newsapi(symbol, company, max_items, domains=",".join(HQ_DOMAINS))
    if len(hq) >= max_items:
        return hq[:max_items]

    # 2) General NewsAPI
    needed   = max_items - len(hq)
    loose    = _fetch_newsapi(symbol, company, needed, domains=None)
    combined = hq + loose
    if len(combined) >= max_items:
        return combined[:max_items]

    # 3) Fallback to Finnhub if ticker‐like
    if TICKER_RE.fullmatch(symbol):
        fb = _fetch_finnhub(symbol, days=7, max_items=max_items - len(combined))
        combined.extend(fb)

    return combined[:max_items]
