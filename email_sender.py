# email_sender.py

import os, smtplib, re
from email.mime.text     import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image    import MIMEImage
from dotenv              import load_dotenv

load_dotenv()  # read .env

SMTP_SERVER   = os.getenv("SMTP_SERVER", "smtp.sendgrid.net")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_SENDER   = os.getenv("SMTP_SENDER")
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "apikey")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# simple email‐address validator
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

def send_email(
    recipient: str,
    subject: str,
    html_body: str,
    inline_images: list[MIMEImage] | None = None,
) -> None:
    """
    Send an HTML e-mail. Recipient must be a single valid address.
    """

    if not all([SMTP_SENDER, SMTP_PASSWORD]):
        raise RuntimeError("SMTP credentials missing in .env")

    # 1) Clean & validate
    recip = recipient.strip()
    if not _EMAIL_RE.match(recip):
        raise ValueError(f"Invalid recipient address: {repr(recip)}")

    # 2) Build the message
    msg = MIMEMultipart("related")
    msg["From"]    = SMTP_SENDER
    msg["To"]      = recip
    msg["Subject"] = subject

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html_body, "html"))
    msg.attach(alt)

    if inline_images:
        for img in inline_images:
            msg.attach(img)

    # 3) Send via SMTP.sendmail (avoids header‐parsing issues)
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(
            SMTP_SENDER,
            [recip],
            msg.as_string()
        )

    print(f"📨 Digest sent to {recip}")
