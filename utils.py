# utils.py

import os
import pandas as pd
import random
import requests
import openai
import time

import streamlit as st  # ← NEW

# Preload S&P 500 for the randomizer
_SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
_sp500_df = pd.read_html(_SP500_URL)[0]
_ALL_TICKERS_LIST = _sp500_df["Symbol"].astype(str).tolist()

# Initialize OpenAI: env OR Streamlit secrets
_api_key = os.getenv("OPENAI_API_KEY", "").strip()
if not _api_key:
    _api_key = st.secrets.get("OPENAI_API_KEY", "").strip()
openai.api_key = _api_key

GPT_MODEL = "gpt-3.5-turbo"


def _ask_gpt_for_ticker(name: str) -> str | None:
    """
    Ask OpenAI: 'What is the primary U.S. stock ticker for {name}?'
    Expects a plain ticker in the response.
    """
    prompt = (
        f"What is the primary U.S. stock ticker for the company “{name}”? "
        "Reply with the ticker symbol only, e.g. AAPL."
    )
    try:
        resp = openai.ChatCompletion.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system",  "content": "You are a financial data assistant."},
                {"role": "user",    "content": prompt},
            ],
            max_tokens=5,
            temperature=0.0,
        )
        text = resp.choices[0].message.content.strip().upper()
        if text.isalpha() and 1 <= len(text) <= 5:
            return text
    except Exception:
        pass
    return None


def to_ticker(input_str: str) -> str:
    """
    Normalize any user input into a clean U.S. equity ticker:
      1. Try Yahoo Finance search (quoteType=EQUITY, prefer no dot), with exponential backoff.
      2. If that fails, ask GPT.
      3. Finally, uppercase raw input as a last resort.
    """
    s = input_str.strip()
    if not s:
        return ""

    url = "https://query1.finance.yahoo.com/v1/finance/search"
    params = {"q": s}
    backoff, max_backoff, retries, max_retries = 1, 60, 0, 3
    equities = []

    while retries < max_retries:
        try:
            resp = requests.get(url, params=params, timeout=5)
            resp.raise_for_status()
            data = resp.json().get("quotes", [])
            equities = [q for q in data if q.get("quoteType") == "EQUITY"]
            break
        except requests.HTTPError as e:
            if resp.status_code == 429:
                time.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
                retries += 1
                continue
            break
        except Exception:
            break

    if equities:
        for q in equities:
            sym = q.get("symbol", "").upper()
            if "." not in sym:
                return sym
        return equities[0].get("symbol", "").upper()

    gpt = _ask_gpt_for_ticker(s)
    if gpt:
        return gpt

    return s.upper()


def fill_random_tickers(tickers: list[str]) -> list[str]:
    """
    Fill only the empty slots in `tickers` with random S&P 500 symbols.
    """
    empties = [i for i, t in enumerate(tickers) if not t]
    if not empties:
        return tickers

    picks = random.sample(_ALL_TICKERS_LIST, len(empties))
    for slot, pick in zip(empties, picks):
        tickers[slot] = pick
    return tickers
