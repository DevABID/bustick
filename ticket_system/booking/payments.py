"""
Payment gateways: SSLCommerz (BDT; cards, bKash, Nagad, Rocket, net banking),
Stripe Checkout (cards), and a Demo provider for local development.

All three use hosted checkout pages, so card data never touches this server.
The seat is only marked Paid after the gateway itself confirms the payment
(SSLCommerz validation API / Stripe session or signed webhook).
"""

import hashlib
import hmac
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Booking, Payment

log = logging.getLogger("booking")


class PaymentError(Exception):
    pass


# ---------------------------------------------------------------- helpers

def _http(method, url, data=None, headers=None, timeout=20):
    body = urllib.parse.urlencode(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        raise PaymentError(f"Gateway HTTP {e.code}: {detail}") from e
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        raise PaymentError(f"Gateway unreachable: {e}") from e


def frontend(path):
    return f"{settings.FRONTEND_URL}{path}"


def backend(path):
    return f"{settings.BACKEND_URL}{path}"


# ------------------------------------------------------- state transitions

def mark_paid(payment_id, provider_ref="", amount=None, currency=None):
    """Idempotently mark a payment and its seats as Paid. Returns the payment."""
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment_id)
        if payment.status == "Paid":
            return payment

        if amount is not None and int(round(float(amount))) != payment.amount:
            payment.status = "Failed"
            payment.note = f"Amount mismatch: gateway {amount} vs expected {payment.amount}. Refund required."
            payment.save(update_fields=["status", "note"])
            log.error("Payment %s amount mismatch", payment.tran_id)
            return payment
        if currency and currency.upper() != payment.currency.upper():
            payment.status = "Failed"
            payment.note = f"Currency mismatch: {currency}. Refund required."
            payment.save(update_fields=["status", "note"])
            return payment

        bookings = list(payment.bookings.select_for_update())
        # If the hold expired before the gateway confirmed, re-claim the seats if still free.
        for b in bookings:
            if b.status != "Pending":
                taken = Booking.objects.filter(
                    schedule_id=b.schedule_id, seat_number=b.seat_number,
                    status__in=Booking.ACTIVE_STATUSES,
                ).exclude(pk=b.pk).exists()
                if taken:
                    payment.status = "Failed"
                    payment.provider_ref = provider_ref or payment.provider_ref
                    payment.note = f"Paid after hold expired and seat {b.seat_number} was resold. Refund required."
                    payment.save(update_fields=["status", "provider_ref", "note"])
                    log.error("Payment %s: seat %s resold, refund needed", payment.tran_id, b.seat_number)
                    return payment

        for b in bookings:
            b.status = "Paid"
            b.save(update_fields=["status"])
        payment.status = "Paid"
        payment.paid_at = timezone.now()
        if provider_ref:
            payment.provider_ref = provider_ref
        payment.save(update_fields=["status", "paid_at", "provider_ref"])

    # Outside the transaction: email failures must not undo a payment.
    from .tickets import send_ticket_email
    send_ticket_email(payment)
    return payment


def release(payment, status):
    """Cancel / fail a pending payment and free its seats."""
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if payment.status != "Pending":
            return payment
        payment.status = status
        payment.save(update_fields=["status"])
        payment.bookings.filter(status="Pending").update(status="Cancelled" if status == "Cancelled" else "Expired")
    return payment


# -------------------------------------------------------------- SSLCommerz

def _ssl_base():
    return "https://sandbox.sslcommerz.com" if settings.SSLCOMMERZ_SANDBOX else "https://securepay.sslcommerz.com"


def sslcommerz_checkout(payment):
    if not (settings.SSLCOMMERZ_STORE_ID and settings.SSLCOMMERZ_STORE_PASSWORD):
        raise PaymentError("SSLCommerz is not configured (SSLCOMMERZ_STORE_ID / SSLCOMMERZ_STORE_PASSWORD).")
    seats = ", ".join(payment.bookings.values_list("seat_number", flat=True))
    data = {
        "store_id": settings.SSLCOMMERZ_STORE_ID,
        "store_passwd": settings.SSLCOMMERZ_STORE_PASSWORD,
        "total_amount": f"{payment.amount:.2f}",
        "currency": payment.currency,
        "tran_id": payment.tran_id,
        "success_url": backend("/api/gateway/sslcommerz/success/"),
        "fail_url": backend("/api/gateway/sslcommerz/fail/"),
        "cancel_url": backend("/api/gateway/sslcommerz/cancel/"),
        "ipn_url": backend("/api/gateway/sslcommerz/ipn/"),
        "cus_name": payment.customer_name,
        "cus_email": payment.customer_email,
        "cus_phone": payment.phone,
        "cus_add1": "N/A",
        "cus_city": payment.schedule.route.from_city,
        "cus_country": "Bangladesh",
        "shipping_method": "NO",
        "num_of_item": payment.bookings.count(),
        "product_name": f"Bus ticket {payment.schedule.route} ({seats})"[:250],
        "product_category": "Travel",
        "product_profile": "general",
        "value_a": payment.tran_id,
    }
    res = _http("POST", f"{_ssl_base()}/gwprocess/v4/api.php", data)
    if res.get("status") != "SUCCESS" or not res.get("GatewayPageURL"):
        raise PaymentError(res.get("failedreason") or "SSLCommerz did not return a payment page.")
    payment.provider_ref = res.get("sessionkey", "")
    payment.save(update_fields=["provider_ref"])
    return res["GatewayPageURL"]


def sslcommerz_validate(val_id):
    """Ask SSLCommerz whether val_id is a real, completed payment. Returns its response dict."""
    q = urllib.parse.urlencode({
        "val_id": val_id,
        "store_id": settings.SSLCOMMERZ_STORE_ID,
        "store_passwd": settings.SSLCOMMERZ_STORE_PASSWORD,
        "format": "json",
    })
    res = _http("GET", f"{_ssl_base()}/validator/api/validationserverAPI.php?{q}")
    if res.get("status") not in ("VALID", "VALIDATED"):
        raise PaymentError(f"SSLCommerz validation status: {res.get('status')}")
    return res


def sslcommerz_confirm(val_id, tran_id):
    res = sslcommerz_validate(val_id)
    if res.get("tran_id") != tran_id:
        raise PaymentError("SSLCommerz tran_id mismatch.")
    payment = Payment.objects.get(tran_id=tran_id)
    return mark_paid(payment.pk, provider_ref=val_id, amount=res.get("amount"), currency=res.get("currency"))


# ------------------------------------------------------------------ Stripe

STRIPE_API = "https://api.stripe.com/v1"


def _stripe_headers():
    if not settings.STRIPE_SECRET_KEY:
        raise PaymentError("Stripe is not configured (STRIPE_SECRET_KEY).")
    return {"Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}"}


def stripe_checkout(payment):
    seats = ", ".join(payment.bookings.values_list("seat_number", flat=True))
    data = {
        "mode": "payment",
        "client_reference_id": payment.tran_id,
        "customer_email": payment.customer_email,
        "success_url": frontend(f"/confirmation?tran_id={payment.tran_id}"),
        "cancel_url": frontend(f"/payment?tran_id={payment.tran_id}&cancelled=1"),
        "expires_at": int(max(payment.hold_expires_at.timestamp(), time.time() + 31 * 60)),
        "metadata[tran_id]": payment.tran_id,
        "line_items[0][quantity]": 1,
        "line_items[0][price_data][currency]": payment.currency.lower(),
        "line_items[0][price_data][unit_amount]": payment.amount * 100,
        "line_items[0][price_data][product_data][name]": f"Bus ticket: {payment.schedule.route}",
        "line_items[0][price_data][product_data][description]": f"{payment.schedule.bus.name} · {payment.schedule.date} · Seats {seats}",
    }
    res = _http("POST", f"{STRIPE_API}/checkout/sessions", data, _stripe_headers())
    payment.provider_ref = res["id"]
    payment.save(update_fields=["provider_ref"])
    return res["url"]


def stripe_refresh(payment):
    """Poll Stripe for the session status. Lets local dev work without a webhook."""
    if payment.provider != "stripe" or payment.status != "Pending" or not payment.provider_ref:
        return payment
    try:
        s = _http("GET", f"{STRIPE_API}/checkout/sessions/{payment.provider_ref}", headers=_stripe_headers())
    except PaymentError as e:
        log.warning("Stripe refresh failed for %s: %s", payment.tran_id, e)
        return payment
    if s.get("payment_status") == "paid":
        return mark_paid(payment.pk, provider_ref=s["id"], amount=s["amount_total"] / 100, currency=s.get("currency"))
    if s.get("status") == "expired":
        return release(payment, "Expired")
    return payment


def stripe_verify_webhook(payload: bytes, sig_header: str, tolerance=300):
    secret = settings.STRIPE_WEBHOOK_SECRET
    if not secret:
        raise PaymentError("STRIPE_WEBHOOK_SECRET is not set.")
    parts = dict(p.split("=", 1) for p in sig_header.split(",") if "=" in p)
    timestamp = parts.get("t")
    signatures = [v for k, v in (p.split("=", 1) for p in sig_header.split(",") if "=" in p) if k == "v1"]
    if not timestamp or not signatures:
        raise PaymentError("Malformed Stripe-Signature header.")
    expected = hmac.new(secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, s) for s in signatures):
        raise PaymentError("Invalid Stripe signature.")
    if abs(time.time() - int(timestamp)) > tolerance:
        raise PaymentError("Stripe webhook timestamp outside tolerance.")
    return json.loads(payload.decode())


# ---------------------------------------------------------------- dispatch

def start_checkout(payment):
    """Returns the URL the browser should go to."""
    if payment.provider == "sslcommerz":
        return sslcommerz_checkout(payment)
    if payment.provider == "stripe":
        return stripe_checkout(payment)
    if payment.provider == "demo":
        if not (settings.DEBUG or settings.ALLOW_DEMO_PAYMENTS):
            raise PaymentError("Demo payments are disabled in production.")
        mark_paid(payment.pk, provider_ref="DEMO")
        return frontend(f"/confirmation?tran_id={payment.tran_id}")
    raise PaymentError(f"Unknown payment provider: {payment.provider}")
