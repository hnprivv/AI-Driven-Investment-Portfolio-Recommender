"""Transactional email sending via Gmail SMTP + Jinja2 templates.

Every send_* function fails silently (logs and returns) on error — email is
a side-effect of account actions, never something that should break the
underlying API request if SMTP is misconfigured or unreachable.
"""
import datetime
import logging
import os
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger("aiprs.email")

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(APP_DIR))

TEMPLATE_DIR = os.path.join(APP_DIR, "email_templates")
_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=select_autoescape(["html"]))

LOGO_PATH = os.path.join(ROOT, "assets", "aiprs_home.png")
LOGO_CID = "aiprs_logo"

APP_URL = os.getenv("APP_URL", "http://localhost:5173")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))


def _send(to_email: str, subject: str, template_name: str, context: dict) -> bool:
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    if not smtp_user or not smtp_password:
        logger.warning("SMTP_USER/SMTP_PASSWORD not configured — skipping email %r to %s", subject, to_email)
        return False

    try:
        html = _env.get_template(template_name).render(
            logo_cid=LOGO_CID, year=datetime.datetime.now().year, app_url=APP_URL, **context
        )
    except Exception:
        logger.exception("Failed to render email template %s", template_name)
        return False

    msg = MIMEMultipart("related")
    msg["Subject"] = subject
    msg["From"] = f"AIPRS <{smtp_user}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))

    if os.path.exists(LOGO_PATH):
        try:
            with open(LOGO_PATH, "rb") as f:
                logo = MIMEImage(f.read())
            logo.add_header("Content-ID", f"<{LOGO_CID}>")
            logo.add_header("Content-Disposition", "inline", filename="aiprs_logo.png")
            msg.attach(logo)
        except Exception:
            logger.exception("Failed to attach logo image")

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, [to_email], msg.as_string())
        return True
    except Exception:
        logger.exception("Failed to send email %r to %s", subject, to_email)
        return False


def send_welcome_email(name: str, email: str, risk_profile: str) -> bool:
    return _send(
        email, "Welcome to AIPRS", "welcome.html",
        {"name": name, "risk_profile": risk_profile},
    )


def send_holdings_updated_email(name: str, email: str, holdings: list[dict]) -> bool:
    return _send(
        email, "Your AIPRS holdings were updated", "holdings_updated.html",
        {"name": name, "holdings": holdings},
    )


def send_credentials_updated_email(name: str, email: str, what_changed: str, extra: str = "") -> bool:
    return _send(
        email, f"Your AIPRS {what_changed} was changed", "credentials_updated.html",
        {"name": name, "what_changed": what_changed, "extra": extra},
    )


def send_account_deleted_email(name: str, email: str) -> bool:
    return _send(email, "Your AIPRS account has been deleted", "account_deleted.html", {"name": name})
