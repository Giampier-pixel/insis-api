import logging

import resend
from django.conf import settings

logger = logging.getLogger(__name__)


def send_email(*, to: str, subject: str, html: str, from_email: str | None = None) -> bool:
    resend.api_key = settings.RESEND_API_KEY
    sender = from_email or settings.DEFAULT_FROM_EMAIL
    try:
        resend.Emails.send({"from": sender, "to": [to], "subject": subject, "html": html})
        logger.info("Email sent to %s — subject: %s", to, subject)
        return True
    except Exception as exc:
        logger.error("Resend error sending to %s: %s", to, exc)
        return False
