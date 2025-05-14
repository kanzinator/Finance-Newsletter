# newsletter.py

from dotenv import load_dotenv
load_dotenv()

import os
from datetime import datetime
import openai
import yfinance as yf

from utils import to_ticker, fill_random_tickers
from data_fetcher import fetch_index
from quote_fetcher import get_stock_quote
from news_scraper import get_news_for_symbol
from chart_maker import performance_charts
from email_sender import send_email

openai.api_key = os.getenv("OPENAI_API_KEY")
CHAT_MODEL = "gpt-3.5-turbo"

INDEX_DISPLAY = {
    "US":            "S&P 500",
    "Europe":        "STOXX Europe 50",
    "UK":            "FTSE 100",
    "Asia":          "Nikkei 225",
    "South America": "S&P Latin America 40",
    "Africa":        "S&P Africa BMI",
    "Australia":     "ASX 200",
}

def _color_pct(pct: float) -> str:
    color = "#008000" if pct >= 0 else "#D00000"
    return f"<span style='color:{color};font-weight:bold'>{pct:+.1f}%</span>"

def generate_intro(region: str) -> str:
    # 1) Global politics & macro
    gh = get_news_for_symbol("world", "global economy", max_items=5)
    gp = (
        "Here are five recent headlines about global politics and macroeconomics:\n\n"
        + "\n".join(f"- {h['title']}" for h in gh)
        + "\n\nSummarize the current global political and macroeconomic environment in ~120 words from an investor's perspective."
        + "\n Focus on actually important news that have broad implications."
        + "\n Give a 1 sentence recommendation at the end on what to do or keep your eyes on."
    )
    gr = openai.ChatCompletion.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": "You are an investor-focused financial journalist."},
            {"role": "user",   "content": gp},
        ],
        max_tokens=260,
        temperature=0.7,
    ).choices[0].message.content.strip()

    # 2) Region-specific market update
    rh = get_news_for_symbol(region, f"{region} market economy", max_items=5)
    rp = (
        f"Here are five recent market headlines specifically from or affecting the {region} region:\n\n"
        + "\n".join(f"- {h['title']}" for h in rh)
        + f"\n\nSummarize the recent market developments and investment implications in {region} in ~100 words."
        + f"\n Focus on actually important news that have broad implications for {region}."
        + "\n Give a 1 sentence recommendation at the end on what to do or keep your eyes on."
    )
    rr = openai.ChatCompletion.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": "You are an investor-focused financial journalist."},
            {"role": "user",   "content": rp},
        ],
        max_tokens=220,
        temperature=0.7,
    ).choices[0].message.content.strip()

    # Wrap in same font/size as headline roundup
    return (
        "<div style='font-size:16px; line-height:1.5;"
        " font-family:Arial,sans-serif; padding:0 1em; text-align:justify;'>"
        f"<p style='margin:0 0 1em;'>{gr}</p>"
        f"<p style='margin:0;'>{rr}</p>"
        "</div>"
    )

def generate_stock_blurb(symbol: str, company: str, analyst_rec: str, target: float, news: list[dict]) -> str:
    prompt = (
        f"Here are recent headlines for {symbol} ({company}):\n\n"
        + "\n".join(f"- {n['title']}" for n in news)
        + (
            f"\n\nWrite a ~100-word investor update on {symbol}, including the consensus analyst "
            f"recommendation ({analyst_rec}) and average target price (${target:.2f})."
        )
    )
    resp = openai.ChatCompletion.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": "You are a clear and succinct equity analyst."},
            {"role": "user",   "content": prompt},
        ],
        max_tokens=250,
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip()

def build_and_send(name: str, region: str, tickers: list[str], email: str):
    # 1) Normalize & fill empty
    tickers = [to_ticker(t) for t in tickers]
    tickers = fill_random_tickers(tickers)

    # 2) Fetch data + analyst info
    stocks = []
    for t in tickers:
        quote = get_stock_quote(t)
        tk = yf.Ticker(t)
        info = tk.info
        company = info.get("shortName", t)
        rec = info.get("recommendationMean", None)
        rec_map = {1:"Strong Buy",1.5:"Buy",2:"Buy",2.5:"Hold",3:"Hold",4:"Sell",5:"Strong Sell"}
        analyst_rec = rec_map.get(round(rec,1), "n/a") if rec else "n/a"
        target = info.get("targetMeanPrice", 0.0) or 0.0
        stocks.append({
            "symbol": t,
            "company": company,
            "quote": quote,
            "analyst_rec": analyst_rec,
            "target": target
        })

    # 3) Fetch index
    idx = fetch_index(region)
    idx_sym = idx["symbol"]
    idx["company"] = INDEX_DISPLAY.get(region, idx_sym)

    # 4) Intro
    intro_html = generate_intro(region)

    # 5) Performance table
    rows = ""
    for item in [idx] + [s["quote"] for s in stocks]:
        sym, comp = item["symbol"], item.get("company", item["symbol"])
        last, prev = item["last_close"], item.get("prev_close", 0.0) or 0.0
        day = item.get("day_pct", (last - prev)/prev*100 if prev else 0.0)
        ytd = item.get("ytd_pct", 0.0) or 0.0
        rows += (
            "<tr>"
            f"<td style='padding:8px;border:1px solid #ddd'>{comp}</td>"
            f"<td style='padding:8px;border:1px solid #ddd;text-align:center'><strong>{sym}</strong></td>"
            f"<td style='padding:8px;border:1px solid #ddd;text-align:right'>{last:,.2f}</td>"
            f"<td style='padding:8px;border:1px solid #ddd;text-align:right'>{_color_pct(day)}</td>"
            f"<td style='padding:8px;border:1px solid #ddd;text-align:right'>{_color_pct(ytd)}</td>"
            "</tr>"
        )
    perf_table = (
        "<div style='overflow-x:auto;margin:1.5em 0;'>"
        "<table style='width:100%;border-collapse:collapse;font-size:16px;'>"
        "<thead style='background:#002E5D;color:#fff;font-size:18px;'>"
        "<tr>"
        "<th style='padding:12px;border:1px solid #ddd;'>Company</th>"
        "<th style='padding:12px;border:1px solid #ddd;'>Ticker</th>"
        "<th style='padding:12px;border:1px solid #ddd;'>Last Close</th>"
        "<th style='padding:12px;border:1px solid #ddd;'>1 Day</th>"
        "<th style='padding:12px;border:1px solid #ddd;'>YTD</th>"
        "</tr></thead><tbody>"
        + rows +
        "</tbody></table></div>"
    )

    # 6) Charts
    symbols = tickers + [idx_sym]
    charts = performance_charts(symbols)
    cid1, img1 = charts["1M"]
    cid2, img2 = charts["1Y"]
    charts_html = (
        "<div style='text-align:center;margin:2em 0;'>"
        "<h2 style='font-size:24px;color:#002E5D;'>1-Month Performance</h2>"
        f"<img src='cid:{cid1}' style='max-width:100%;height:auto;'/>"
        "<h2 style='font-size:24px;color:#002E5D;margin-top:2em;'>1-Year Performance</h2>"
        f"<img src='cid:{cid2}' style='max-width:100%;height:auto;'/>"
        "</div>"
    )

    # 7) Weekly Top News
    weekly = get_news_for_symbol("world", "global economy", max_items=5)
    weekly_html = (
        "<h2 style='text-align:center;font-size:24px;margin-top:2em;color:#002E5C;'>Weekly Top News</h2>"
        "<ul style='font-size:16px;padding-left:1.2em;margin-bottom:2em;'>"
        + "".join(
            f"<li style='margin:4px 0'>{h['title']} "
            f"(<a href='{h['url']}' target='_blank'>{h['source']}</a>)</li>"
            for h in weekly
        )
        + "</ul>"
    )

    # 8) Headline Roundup – dedupe by URL & title
    seen_urls = set()
    seen_titles = set()
    hr_html = (
        "<h2 style='text-align:center;font-size:24px;margin-top:2em;color:#5B2C6F;'>Headline Roundup</h2>"
        "<ul style='font-size:16px;padding-left:1.2em;'>"
    )
    for stock in stocks:
        cname = stock["company"]
        arts = get_news_for_symbol(cname, cname, max_items=7)
        for art in arts:
            title = art["title"].strip()
            url   = art["url"].strip()
            if url in seen_urls or title in seen_titles:
                continue
            seen_urls.add(url)
            seen_titles.add(title)
            hr_html += (
                f"<li style='margin:4px 0'>{title} "
                f"(<a href='{url}' target='_blank'>{art['source']}</a>)</li>"
            )
    hr_html += "</ul>"

    # 9) Stock blurbs
    details = ""
    for s in stocks:
        recent = get_news_for_symbol(s["company"], s["company"], max_items=7)
        blurb = generate_stock_blurb(
            s["symbol"],
            s["company"],
            s["analyst_rec"],
            s["target"],
            recent
        )
        details += (
            f"<h3 style='font-size:20px;margin-top:1.5em;text-align:center;"
            f"'>{s['symbol']} — {s['company']}</h3>"
            f"<p style='font-size:16px;line-height:1.5;padding:0 1em;text-align:justify;'>"
            f"{blurb}</p>"
        )

    # 10) Assemble and send
    html = (
        "<div style='background:#F0F0F0;padding:2em;'>"
        "<div style='background:#FFFFFF;max-width:640px;margin:0 auto;"
        "padding:2em;font-family:Arial,sans-serif;border-radius:12px;'>"
        "<h1 style='text-align:center;font-size:32px;color:#002E5D;margin:0;'>Financial Digest</h1>"
        f"<p style='font-size:16px;margin-top:1em;'>Good morning, <strong>{name}</strong></p>"
        f"{intro_html}"
        f"{perf_table}"
        f"{charts_html}"
        f"{weekly_html}"
        f"{hr_html}"
        f"{details}"
        "</div></div>"
    )

    subject = f"Financial Digest for {datetime.now():%B %d, %Y}"
    send_email(
        recipient=email,
        subject=subject,
        html_body=html,
        inline_images=[img1, img2]
    )
