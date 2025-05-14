# email_sender.py

import os
import smtplib
from email.mime.text     import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image    import MIMEImage
from bs4                 import BeautifulSoup

import streamlit as st

# Load SMTP creds from env OR Streamlit secrets
SMTP_SERVER   = os.getenv("SMTP_SERVER") or st.secrets["SMTP_SERVER"]
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_SENDER   = os.getenv("SMTP_SENDER") or st.secrets["SMTP_SENDER"]
SMTP_USERNAME = os.getenv("SMTP_USERNAME") or st.secrets["SMTP_USERNAME"]
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD") or st.secrets["SMTP_PASSWORD"]


def send_email(recipient: str, subject: str, html_body: str, inline_images=None):
    msg = MIMEMultipart("related")
    msg["From"]            = f"Finance News <{SMTP_SENDER}>"
    msg["To"]              = recipient
    msg["Subject"]         = subject
    msg["Reply-To"]        = SMTP_SENDER
    msg["List-Unsubscribe"]= f"<mailto:{SMTP_SENDER}?subject=Unsubscribe>"

    # Fallback to plain text
    plain = BeautifulSoup(html_body, "html.parser").get_text()
    alt   = MIMEMultipart("alternative")
    alt.attach(MIMEText(plain, "plain"))
    alt.attach(MIMEText(html_body, "html"))
    msg.attach(alt)

    # Attach images if provided
    if inline_images:
        for img in inline_images:
            msg.attach(img)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_SENDER, [recipient], msg.as_string())
