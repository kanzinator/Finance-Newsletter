# email_sender.py

import os
import smtplib
import re
from email.mime.text     import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image    import MIMEImage
from bs4                 import BeautifulSoup
import streamlit as st   # ← NEW

# Load SMTP creds from env OR Streamlit secrets
SMTP_SERVER   = os.getenv("SMTP_SERVER") or st.secrets.get("SMTP_SERVER")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_SENDER   = os.getenv("SMTP_SENDER") or st.secrets.get("SMTP_SENDER")
SMTP_USERNAME = os.getenv("SMTP_USERNAME") or st.secrets.get("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD") or st.secrets.get("SMTP_PASSWORD")


def send_email(recipient: str, subject: str, html_body: str, inline_images=None):
    # 1) Build multipart message
    msg = MIMEMultipart("related")
    msg["From"]           = f"Finance News <{SMTP_SENDER}>"
    msg["To"]             = recipient
    msg["Subject"]        = subject
    msg["Reply-To"]       = SMTP_SENDER
    msg["List-Unsubscribe"] = f"<mailto:{SMTP_SENDER}?subject=Unsubscribe>"

    # 2) Plain-text fallback + HTML
    plain_text = BeautifulSoup(html_body, "html.parser").get_text()
    alt        = MIMEMultipart("alternative")
    alt.attach(MIMEText(plain_text, "plain"))
    alt.attach(MIMEText(html_body, "html"))
    msg.attach(alt)

    # 3) Attach inline images if any
    if inline_images:
        for img in inline_images:
            msg.attach(img)

    # 4) Send via SMTP with TLS
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_SENDER, [recipient], msg.as_string())
