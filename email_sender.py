# email_sender.py

import os
import smtplib
import re
from email.mime.text     import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image    import MIMEImage
from dotenv              import load_dotenv
from bs4                 import BeautifulSoup  # pip install beautifulsoup4

load_dotenv()

SMTP_SERVER   = os.getenv("SMTP_SERVER")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_SENDER   = os.getenv("SMTP_SENDER")   # e.g. 64001@novasbe.pt
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

def send_email(recipient: str, subject: str, html_body: str, inline_images=None):
    # --- 1) Build message with alternative parts ---
    msg = MIMEMultipart("related")
    # Friendly From header
    msg["From"] = f"📈 Finance News"
    msg["To"]      = recipient
    msg["Subject"] = subject
    msg["Reply-To"] = SMTP_SENDER
    # Unsubscribe header (very spam-filter–friendly)
    msg["List-Unsubscribe"] = f"<mailto:{SMTP_SENDER}?subject=Unsubscribe>"

    # Plain-text fallback: strip tags
    plain_text = BeautifulSoup(html_body, "html.parser").get_text()
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(plain_text, "plain"))
    alt.attach(MIMEText(html_body, "html"))
    msg.attach(alt)

    # --- 2) Attach inline images if any ---
    if inline_images:
        for img in inline_images:
            msg.attach(img)

    # --- 3) Send via SMTP TLS ---
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_SENDER, [recipient], msg.as_string())
