# data_fetcher.py

import yfinance as yf
from datetime import datetime
import pandas as pd

# Map user‐friendly region names to index symbols
REGION_INDEX = {
    "US": "^GSPC",
    "Europe": "^STOXX50E",
    "UK": "^FTSE",
    "Asia": "^N225",
    "South America": "^SPLAC",
    "Africa": "^SPAFRUP",
    "Australia": "^XJO"
}

def fetch_price_data(symbol: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
    """
    Download OHLCV history for a single symbol via yfinance.
    Returns a flat DataFrame with columns: ['Open','High','Low','Close','Volume'].
    """
    df = yf.Ticker(symbol).history(period=period, interval=interval)
    return df


def fetch_index(region: str) -> dict:
    """
    Fetch the latest and previous closing price for the regional index.
    Uses yfinance Ticker.history; if there is only one or zero
    data points, it falls back to equal or zero values.
    """
    idx = REGION_INDEX.get(region, "^GSPC")
    hist = yf.Ticker(idx).history(period="2d", interval="1d")["Close"].dropna()

    if len(hist) >= 2:
        last_close = float(hist.iloc[-1])
        prev_close = float(hist.iloc[-2])
    elif len(hist) == 1:
        last_close = prev_close = float(hist.iloc[0])
    else:
        last_close = prev_close = 0.0

    return {
        "symbol": idx,
        "last_close": last_close,
        "prev_close": prev_close,
    }
