# quote_fetcher.py

import yfinance as yf
import pandas as pd
from datetime import datetime

def get_stock_quote(symbol:str) -> dict:
    hist = yf.Ticker(symbol).history(period="1y")
    closes = hist.get("Close",pd.Series()).dropna()

    if closes.empty:
        return {"symbol":symbol,"last_close":0.0,"day_pct":0.0,"ytd_pct":0.0}
    if len(closes)==1:
        v=float(closes.iloc[0])
        return {"symbol":symbol,"last_close":v,"day_pct":0.0,"ytd_pct":0.0}

    last,prev = float(closes.iloc[-1]),float(closes.iloc[-2])
    day_pct = (last-prev)/prev*100 if prev else 0.0

    idx = closes.index
    if getattr(idx,"tz",None):
        ys = pd.Timestamp(datetime.now().year,1,1,tz=idx.tz)
    else:
        ys = pd.Timestamp(datetime.now().year,1,1)
    ytds = closes.loc[closes.index>=ys]
    ytd_pct = (last - float(ytds.iloc[0]))/float(ytds.iloc[0])*100 if not ytds.empty and ytds.iloc[0] else 0.0

    return {"symbol":symbol,"last_close":last,"day_pct":day_pct,"ytd_pct":ytd_pct}
