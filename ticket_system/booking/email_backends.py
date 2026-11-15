"""
Send Django emails through Brevo's HTTPS API instead of SMTP.

Use this where SMTP ports are blocked (Render's free web services block 25/465/587).
    EMAIL_BACKEND=booking.email_backends.BrevoEmailBackend
    BREVO_API_KEY=xkeysib-...
    DEFAULT_FROM_EMAIL=BusTick <you@yourdomain.com>     # must be a sender verified in Brevo

Works with send_mail, EmailMessage and EmailMultiAlternatives, including
HTML alternatives, attachments (the PDF ticket) and reply_to.
"""

import base64
import json
import logging
import urllib.error
import urllib.request
from email.utils import parseaddr

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

log = logging.getLogger("booking")
BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def _contact(addr):
    name, email = parseaddr(addr)
    return {"email": email, "name": name} if name else {"email": email}


class BrevoEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        if not settings.BREVO_API_KEY:
            if not self.fail_silently:
                raise RuntimeError("BREVO_API_KEY is not set.")
            return 0
        sent = 0
        for msg in email_messages:
            try:
                self._send(msg)
                sent += 1
            except Exception:
                log.exception("Brevo send failed: %s", msg.subject)
                if not self.fail_silently:
                    raise
        return sent

    def _send(self, msg):
        payload = {
            "sender": _contact(msg.from_email or settings.DEFAULT_FROM_EMAIL),
            "to": [_contact(a) for a in msg.to],
            "subject": msg.subject,
            "textContent": msg.body or " ",
        }
        if msg.cc:
            payload["cc"] = [_contact(a) for a in msg.cc]
        if msg.bcc:
            payload["bcc"] = [_contact(a) for a in msg.bcc]
        if msg.reply_to:
            payload["replyTo"] = _contact(msg.reply_to[0])
        for content, mimetype in getattr(msg, "alternatives", []):
            if mimetype == "text/html":
                payload["htmlContent"] = content
        attachments = []
        for att in msg.attachments:
            if not isinstance(att, tuple):  # pre-built MIME parts are not supported
                continue
            filename, content = att[0], att[1]
            if isinstance(content, str):
                content = content.encode()
            attachments.append({"name": filename, "content": base64.b64encode(content).decode()})
        if attachments:
            payload["attachment"] = attachments

        req = urllib.request.Request(
            BREVO_URL, data=json.dumps(payload).encode(), method="POST",
            headers={"api-key": settings.BREVO_API_KEY, "Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                if resp.status >= 300:
                    raise RuntimeError(f"Brevo HTTP {resp.status}")
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Brevo HTTP {e.code}: {e.read().decode(errors='replace')[:300]}") from e
