# utils.py

import os
import pandas as pd
import random
import requests
import openai
import time

# Preload S&P 500 for the randomizer
_SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
_sp500_df = pd.read_html(_SP500_URL)[0]
_ALL_TICKERS_LIST = _sp500_df["Symbol"].astype(str).tolist()

# Initialize OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")
GPT_MODEL = "gpt-3.5-turbo"

def _ask_gpt_for_ticker(name: str) -> str | None:
    prompt = (
        f"What is the primary U.S. stock ticker for the company “{name}”? "
        "Reply with the ticker symbol only, e.g. AAPL."
    )
    try:
        resp = openai.ChatCompletion.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": "You are a financial data assistant."},
                {"role": "user",   "content": prompt},
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
      1. Try Yahoo Finance search (quoteType=EQUITY, prefer no dot), with
         exponential backoff on 429 and a max retry count.
      2. Ask OpenAI if Yahoo fails.
      3. Finally, uppercase raw input.
    """
    s = input_str.strip()
    if not s:
        return ""

    # 1) Yahoo Search with exponential backoff and retry limit
    url = f"https://query1.finance.yahoo.com/v1/finance/search?q={s}"
    backoff = 1
    max_backoff = 60
    retries = 0
    max_retries = 3

    while retries < max_retries:
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json().get("quotes", [])
            equities = [q for q in data if q.get("quoteType") == "EQUITY"]
            # pick first with no dot
            for q in equities:
                sym = q.get("symbol", "")
                if "." not in sym:
                    return sym.upper()
            # fallback to first equity
            if equities and "symbol" in equities[0]:
                return equities[0]["symbol"].upper()
            # no equities found – break to fallback
            break
        except requests.HTTPError as e:
            status = getattr(e.response, "status_code", None)
            if status == 429:
                time.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
                retries += 1
                continue
            # other HTTP errors – give up
            break
        except Exception:
            # network error or JSON error – give up
            break

    # 2) Ask GPT
    gpt = _ask_gpt_for_ticker(s)
    if gpt:
        return gpt

    # 3) Final fallback
    return s.upper()

def fill_random_tickers(tickers: list[str]) -> list[str]:
    """
    Fill only the empty slots in `tickers` with random S&P 500 symbols.
    """
    empties = [i for i, t in enumerate(tickers) if not t]
    if not empties:
        return tickers

    picks = random.sample(_ALL_TICKERS_LIST, len(empties))
    for idx, slot in enumerate(empties):
        tickers[slot] = picks[idx]
    return tickers
