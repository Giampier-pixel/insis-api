import resend
from django.conf import settings


def send_email(*, to: str, subject: str, html: str, from_email: str | None = None) -> bool:
    """Send a transactional email via Resend. Returns True on success."""
    resend.api_key = settings.RESEND_API_KEY
    sender = from_email or settings.DEFAULT_FROM_EMAIL
    try:
        resend.Emails.send({"from": sender, "to": [to], "subject": subject, "html": html})
        return True
    except Exception:
        return False
