# chart_maker.py

import datetime as _dt
import io
import uuid

import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from email.mime.image import MIMEImage

def performance_charts(symbols: list[str]) -> dict[str, tuple[str, MIMEImage]]:
    """
    Returns two inline charts (1M and 1Y) as { "1M": (cid, MIMEImage), "1Y": (cid, MIMEImage) }.
    Each plot shows cumulative % returns from day 0, with weekend/holiday gaps forward-filled.
    """
    if not symbols:
        raise ValueError("Must provide at least one symbol")

    end = _dt.date.today()
    spans = {
        "1M": _dt.timedelta(days=30),
        "1Y": _dt.timedelta(days=365),
    }
    out: dict[str, tuple[str, MIMEImage]] = {}

    for label, delta in spans.items():
        start = end - delta

        # 1) Download just the Close prices
        df = yf.download(
            symbols,
            start=start,
            end=end,
            progress=False
        )["Close"]

        # 2) Ensure DataFrame (single‐symbol download yields a Series)
        if not hasattr(df, "columns"):
            df = df.to_frame(name=symbols[0])

        # 3) Build a uniform business‐day index and forward-fill missing days
        bdays = pd.date_range(start=df.index.min(), end=df.index.max(), freq="B")
        df = df.reindex(bdays).ffill()

        # 4) Drop rows where *all* symbols are still NaN
        df = df.dropna(how="all")
        if df.empty:
            raise ValueError(f"No price data available for {label} window")

        # 5) Compute cumulative % return from first row
        cum_pct = (df / df.iloc[0] - 1) * 100

        # 6) Plot into a standalone figure
        fig, ax = plt.subplots(figsize=(6, 3), dpi=120)
        for col in cum_pct.columns:
            ax.plot(cum_pct.index, cum_pct[col], label=col)
        ax.set_title(f"{label} Performance", fontsize=12, pad=8)
        ax.set_ylabel("% Return", fontsize=10)
        ax.legend(fontsize=8, loc="upper left")
        ax.grid(alpha=0.3)
        fig.autofmt_xdate()
        plt.tight_layout()

        # 7) Serialize to PNG in memory
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=120)
        plt.close(fig)
        buf.seek(0)
        png_bytes = buf.read()
        buf.close()

        # 8) Wrap as inline MIMEImage with a unique CID
        cid = f"perf_{label.lower()}_{uuid.uuid4().hex}@digest"
        img = MIMEImage(png_bytes, _subtype="png")
        img.add_header("Content-ID", f"<{cid}>")
        img.add_header("Content-Disposition", "inline")

        out[label] = (cid, img)

    return out
