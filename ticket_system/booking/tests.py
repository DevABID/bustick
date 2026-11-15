import hashlib
import hmac
import json
import time
from datetime import time as dtime, timedelta
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from . import payments
from .models import Booking, Bus, Payment, Route, Schedule, expire_stale_holds


@override_settings(PAYMENT_PROVIDER="demo", DEBUG=True,
                   EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class BookingFlowTests(TestCase):
    def setUp(self):
        self.c = APIClient()
        bus = Bus.objects.create(name="Green Line", type="AC", seat_layout="BUSINESS")
        route = Route.objects.create(from_city="Dhaka", to_city="Sylhet")
        self.s = Schedule.objects.create(bus=bus, route=route, date=timezone.localdate() + timedelta(days=3),
                                         departure_time=dtime(9, 0), price=1200, seat_type="BUSINESS")

    def book(self, seats, **extra):
        body = {"schedule": self.s.id, "seats": seats, "customer_name": "Rahim Uddin",
                "customer_email": "rahim@example.com", "phone": "01712345678", **extra}
        return self.c.post("/api/bookings/", body, format="json")

    def test_search_returns_seats_left(self):
        r = self.c.get("/api/schedules/", {"from": "dhaka", "to": "sylhet", "date": str(self.s.date)})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()[0]["seats_left"], 24)

    def test_book_and_pay_demo(self):
        r = self.book(["A1", "B2"])
        self.assertEqual(r.status_code, 201, r.content)
        tran = r.json()["tran_id"]
        self.assertEqual(r.json()["amount"], 2400)
        r = self.c.post(f"/api/payments/{tran}/checkout/")
        self.assertIn("/confirmation?tran_id=", r.json()["redirect_url"])
        p = Payment.objects.get(tran_id=tran)
        self.assertEqual(p.status, "Paid")
        self.assertEqual(set(p.bookings.values_list("status", flat=True)), {"Paid"})
        self.assertTrue(p.ticket_emailed)

    def test_same_seat_cannot_be_held_twice(self):
        self.assertEqual(self.book(["A1"]).status_code, 201)
        r = self.book(["A1", "A2"])
        self.assertEqual(r.status_code, 409)
        self.assertEqual(Booking.objects.filter(seat_number="A2").count(), 0)  # all-or-nothing

    def test_invalid_seat_rejected(self):
        self.assertEqual(self.book(["Z9"]).status_code, 400)

    def test_expired_hold_frees_seat(self):
        tran = self.book(["A1"]).json()["tran_id"]
        Payment.objects.filter(tran_id=tran).update(hold_expires_at=timezone.now() - timedelta(seconds=1))
        expire_stale_holds()
        self.assertEqual(self.book(["A1"]).status_code, 201)

    def test_amount_mismatch_is_not_marked_paid(self):
        tran = self.book(["A1"]).json()["tran_id"]
        p = Payment.objects.get(tran_id=tran)
        payments.mark_paid(p.pk, amount=1)
        p.refresh_from_db()
        self.assertEqual(p.status, "Failed")

    def test_lookup_needs_matching_email(self):
        tran = self.book(["A1"]).json()["tran_id"]
        self.c.post(f"/api/payments/{tran}/checkout/")
        pnr = Booking.objects.get(seat_number="A1").pnr_number
        self.assertEqual(self.c.get("/api/tickets/lookup/", {"pnr": pnr, "email": "x@y.com"}).status_code, 404)
        self.assertEqual(self.c.get("/api/tickets/lookup/", {"pnr": pnr, "email": "RAHIM@example.com"}).status_code, 200)

    def test_return_marks_cancelled_and_frees_seat(self):
        tran = self.book(["A1"]).json()["tran_id"]
        self.c.post(f"/api/payments/{tran}/checkout/")
        pnr = Booking.objects.get(seat_number="A1").pnr_number
        r = self.c.post("/api/tickets/return/", {"pnr": pnr, "email": "rahim@example.com"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(Booking.objects.get(pnr_number=pnr).status, "Cancelled")
        self.assertEqual(self.book(["A1"]).status_code, 201)

    def test_return_blocked_close_to_departure(self):
        self.s.date = timezone.localdate()
        self.s.departure_time = (timezone.localtime() + timedelta(hours=2)).time().replace(microsecond=0)
        self.s.save()
        if self.s.date != timezone.localdate():  # near midnight; skip
            return
        tran = self.book(["A1"]).json()["tran_id"]
        self.c.post(f"/api/payments/{tran}/checkout/")
        pnr = Booking.objects.get(seat_number="A1").pnr_number
        r = self.c.post("/api/tickets/return/", {"pnr": pnr, "email": "rahim@example.com"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_ticket_pdf(self):
        tran = self.book(["A1"]).json()["tran_id"]
        self.c.post(f"/api/payments/{tran}/checkout/")
        r = self.c.get(f"/api/payments/{tran}/ticket.pdf")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b"%PDF"))


@override_settings(STRIPE_WEBHOOK_SECRET="whsec_test")
class StripeSignatureTests(TestCase):
    def sign(self, payload, secret="whsec_test", ts=None):
        ts = ts or int(time.time())
        sig = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
        return f"t={ts},v1={sig}"

    def test_valid_signature(self):
        body = json.dumps({"type": "ping"}).encode()
        self.assertEqual(payments.stripe_verify_webhook(body, self.sign(body))["type"], "ping")

    def test_bad_signature(self):
        body = b'{"type":"ping"}'
        with self.assertRaises(payments.PaymentError):
            payments.stripe_verify_webhook(body, self.sign(body, secret="wrong"))

    def test_old_timestamp(self):
        body = b'{"type":"ping"}'
        with self.assertRaises(payments.PaymentError):
            payments.stripe_verify_webhook(body, self.sign(body, ts=int(time.time()) - 3600))


@override_settings(SSLCOMMERZ_STORE_ID="test", SSLCOMMERZ_STORE_PASSWORD="test")
class SslcommerzTests(TestCase):
    def test_success_requires_validation(self):
        bus = Bus.objects.create(name="B")
        route = Route.objects.create(from_city="A", to_city="B")
        s = Schedule.objects.create(bus=bus, route=route, date=timezone.localdate() + timedelta(days=2),
                                    departure_time=dtime(9), price=500)
        p = Payment.objects.create(schedule=s, customer_name="X", customer_email="x@example.com",
                                   phone="01712345678", amount=500, provider="sslcommerz")
        Booking.objects.create(schedule=s, payment=p, seat_number="A1", customer_name="X",
                               customer_email="x@example.com", phone="01712345678")
        with mock.patch.object(payments, "_http", return_value={"status": "INVALID_TRANSACTION"}):
            r = self.client.post("/api/gateway/sslcommerz/success/", {"tran_id": p.tran_id, "val_id": "v"})
        self.assertIn("failed=1", r["Location"])
        p.refresh_from_db()
        self.assertEqual(p.status, "Pending")

        with mock.patch.object(payments, "_http", return_value={"status": "VALID", "tran_id": p.tran_id,
                                                                "amount": "500.00", "currency": "BDT"}):
            r = self.client.post("/api/gateway/sslcommerz/success/", {"tran_id": p.tran_id, "val_id": "v"})
        self.assertIn("/confirmation?tran_id=", r["Location"])
        p.refresh_from_db()
        self.assertEqual(p.status, "Paid")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", SUPPORT_EMAIL="support@example.com")
class SupportAndDiscoveryTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()  # reset throttles
        self.c = APIClient()
        bus = Bus.objects.create(name="Hanif")
        self.route = Route.objects.create(from_city="Cox's Bazar", to_city="Dhaka")
        for d, price in ((2, 900), (5, 800)):
            Schedule.objects.create(bus=bus, route=self.route, date=timezone.localdate() + timedelta(days=d),
                                    departure_time=dtime(9), price=price)

    def test_support_message_is_saved_and_emailed(self):
        from django.core import mail
        from .models import SupportMessage
        r = self.c.post("/api/support/", {"name": "Rahim", "email": "rahim@example.com", "topic": "payment",
                                          "message": "I was charged twice for my ticket."}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["support@example.com"])
        self.assertEqual(mail.outbox[0].reply_to, ["rahim@example.com"])
        self.assertTrue(SupportMessage.objects.get().emailed)

    def test_support_validation(self):
        r = self.c.post("/api/support/", {"name": "R", "email": "bad", "message": "hi"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_next_dates(self):
        r = self.c.get("/api/schedules/next-dates/", {"from": "Cox's Bazar", "to": "Dhaka"})
        self.assertEqual([x["min_price"] for x in r.json()], [900, 800])

    def test_routes_include_min_price(self):
        row = self.c.get("/api/routes/").json()[0]
        self.assertEqual(row["min_price"], 800)

    def test_extend_schedules(self):
        from django.core.management import call_command
        import io
        call_command("extend_schedules", days=10, stdout=io.StringIO())
        self.assertEqual(Schedule.objects.filter(date__gte=timezone.localdate()).count(), 10)


@override_settings(EMAIL_BACKEND="booking.email_backends.BrevoEmailBackend", BREVO_API_KEY="test-key",
                   DEFAULT_FROM_EMAIL="BusTick <tickets@example.com>")
class BrevoBackendTests(TestCase):
    def test_sends_html_attachment_and_reply_to(self):
        from django.core.mail import EmailMultiAlternatives
        captured = {}

        class FakeResp:
            status = 201
            def __enter__(self): return self
            def __exit__(self, *a): return False

        def fake_urlopen(req, timeout=0):
            captured["headers"] = dict(req.header_items())
            captured["body"] = json.loads(req.data)
            return FakeResp()

        msg = EmailMultiAlternatives("Hi", "text", to=["a@example.com"], reply_to=["r@example.com"])
        msg.attach_alternative("<b>hi</b>", "text/html")
        msg.attach("t.pdf", b"%PDF-1", "application/pdf")
        with mock.patch("booking.email_backends.urllib.request.urlopen", fake_urlopen):
            self.assertEqual(msg.send(), 1)
        body = captured["body"]
        self.assertEqual(body["sender"], {"email": "tickets@example.com", "name": "BusTick"})
        self.assertEqual(body["replyTo"], {"email": "r@example.com"})
        self.assertEqual(body["htmlContent"], "<b>hi</b>")
        self.assertEqual(body["attachment"][0]["name"], "t.pdf")
        self.assertEqual(captured["headers"]["Api-key"], "test-key")


class HealthTests(TestCase):
    def test_health_and_root(self):
        self.assertEqual(self.client.get("/api/health/").json()["database"], "ok")
        self.assertEqual(self.client.get("/").json()["service"], "BusTick API")


@override_settings(SSLCOMMERZ_STORE_ID="", SSLCOMMERZ_STORE_PASSWORD="", PAYMENT_PROVIDER="sslcommerz")
class CheckoutErrorTests(TestCase):
    def setUp(self):
        bus = Bus.objects.create(name="B")
        route = Route.objects.create(from_city="A", to_city="B")
        s = Schedule.objects.create(bus=bus, route=route, date=timezone.localdate() + timedelta(days=2),
                                    departure_time=dtime(9), price=500)
        self.p = Payment.objects.create(schedule=s, customer_name="X", customer_email="x@example.com",
                                        phone="01712345678", amount=500, provider="sslcommerz")

    def test_missing_keys_is_503_and_health_reports_it(self):
        r = self.client.post(f"/api/payments/{self.p.tran_id}/checkout/")
        self.assertEqual(r.status_code, 503)
        self.assertFalse(self.client.get("/api/health/").json()["payment_configured"])

    @override_settings(SSLCOMMERZ_STORE_ID="x", SSLCOMMERZ_STORE_PASSWORD="y")
    def test_gateway_reason_is_logged(self):
        with mock.patch.object(payments, "_http", return_value={"status": "FAILED", "failedreason": "Store Credential Error Or Store is De-active"}):
            with self.assertLogs("booking", level="ERROR") as logs:
                r = self.client.post(f"/api/payments/{self.p.tran_id}/checkout/")
        self.assertEqual(r.status_code, 503)
        self.assertIn("Store Credential Error", "\n".join(logs.output))


@override_settings(SSLCOMMERZ_STORE_ID="busti_test", SSLCOMMERZ_STORE_PASSWORD="pw", PAYMENT_PROVIDER="sslcommerz")
class SslcommerzRequestFieldsTests(TestCase):
    def test_all_mandatory_fields_sent(self):
        bus = Bus.objects.create(name="Green Line")
        route = Route.objects.create(from_city="Dhaka", to_city="Sylhet")
        s = Schedule.objects.create(bus=bus, route=route, date=timezone.localdate() + timedelta(days=2),
                                    departure_time=dtime(9), price=800)
        p = Payment.objects.create(schedule=s, customer_name="Rahim", customer_email="r@example.com",
                                   phone="01712345678", amount=800, provider="sslcommerz")
        Booking.objects.create(schedule=s, payment=p, seat_number="A1", customer_name="Rahim",
                               customer_email="r@example.com", phone="01712345678")
        sent = {}

        def fake_http(method, url, data=None, headers=None, timeout=30):
            sent.update(data)
            return {"status": "SUCCESS", "GatewayPageURL": "https://sandbox.sslcommerz.com/pay/x", "sessionkey": "k"}

        with mock.patch.object(payments, "_http", fake_http):
            url = payments.start_checkout(p)
        self.assertTrue(url.startswith("https://sandbox.sslcommerz.com"))
        for field in ["store_id", "store_passwd", "total_amount", "currency", "tran_id", "success_url", "fail_url",
                      "cancel_url", "cus_name", "cus_email", "cus_add1", "cus_city", "cus_postcode", "cus_country",
                      "cus_phone", "shipping_method", "product_name", "product_category", "product_profile"]:
            self.assertTrue(str(sent.get(field, "")).strip(), f"{field} missing")
        self.assertEqual(sent["total_amount"], "800.00")
        self.assertEqual(sent["cus_postcode"], "1000")
