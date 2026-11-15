import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Count, Min, Q
from django.core.mail import EmailMessage
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from . import payments
from .models import Booking, Payment, Route, Schedule, SupportMessage, expire_stale_holds
from .serializers import (BookingSerializer, CreateBookingSerializer, PaymentSerializer,
                          RouteSerializer, ScheduleDetailSerializer, ScheduleSerializer,
                          SupportMessageSerializer)
from .tickets import build_ticket_pdf

log = logging.getLogger("booking")


class LookupThrottle(AnonRateThrottle):
    """Slow down PNR guessing."""
    rate = "20/min"


# ------------------------------------------------------------- health

class Health(APIView):
    """GET /api/health/ — used by Render to check the app and database are up."""

    def get(self, request):
        from django.db import connection
        try:
            with connection.cursor() as c:
                c.execute("SELECT 1")
            db = "ok"
        except Exception:
            db = "error"
        configured = {
            "sslcommerz": bool(settings.SSLCOMMERZ_STORE_ID and settings.SSLCOMMERZ_STORE_PASSWORD),
            "stripe": bool(settings.STRIPE_SECRET_KEY),
            "demo": True,
        }.get(settings.PAYMENT_PROVIDER, False)
        return Response({
            "status": "ok" if db == "ok" else "degraded", "database": db,
            "payment_provider": settings.PAYMENT_PROVIDER, "payment_configured": configured,
            "sslcommerz_mode": "sandbox" if settings.SSLCOMMERZ_SANDBOX else "live",
            "backend_url": settings.BACKEND_URL, "frontend_url": settings.FRONTEND_URL,
        }, status=200 if db == "ok" else 503)


# ------------------------------------------------------------- search

class RouteList(APIView):
    """All routes, with the lowest upcoming fare and next travel date (null if none scheduled)."""

    def get(self, request):
        today = timezone.localdate()
        upcoming = Q(schedule__date__gte=today)
        routes = Route.objects.annotate(
            min_price=Min("schedule__price", filter=upcoming),
            next_date=Min("schedule__date", filter=upcoming),
            trips=Count("schedule", filter=upcoming),
        ).order_by("-trips", "from_city", "to_city")
        data = RouteSerializer(routes, many=True).data
        for row, r in zip(data, routes):
            row.update(min_price=r.min_price, next_date=r.next_date, trips=r.trips)
        return Response(data)


class NextDates(APIView):
    """GET /api/schedules/next-dates/?from=&to=  → up to 5 upcoming dates that have departures."""

    def get(self, request):
        f, t = request.GET.get("from"), request.GET.get("to")
        if not (f and t):
            return Response([])
        now = timezone.localtime()
        qs = (Schedule.objects.filter(route__from_city__iexact=f, route__to_city__iexact=t, date__gte=now.date())
              .exclude(date=now.date(), departure_time__lte=now.time())
              .values("date").annotate(trips=Count("id"), min_price=Min("price")).order_by("date")[:5])
        return Response([{"date": r["date"], "trips": r["trips"], "min_price": r["min_price"]} for r in qs])


class ScheduleSearch(APIView):
    """GET /api/schedules/?from=Dhaka&to=Sylhet&date=2026-11-20"""

    def get(self, request):
        expire_stale_holds()
        f, t, d = request.GET.get("from"), request.GET.get("to"), request.GET.get("date")
        if not (f and t and d):
            return Response({"error": "from, to and date are required."}, status=400)
        try:
            day = datetime.strptime(d, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "date must be YYYY-MM-DD."}, status=400)

        now = timezone.localtime()
        qs = (Schedule.objects.select_related("bus", "route")
              .filter(route__from_city__iexact=f, route__to_city__iexact=t, date=day)
              .annotate(taken_count=Count("bookings", filter=Q(bookings__status__in=Booking.ACTIVE_STATUSES))))
        if day < now.date():
            qs = qs.none()
        elif day == now.date():
            qs = qs.filter(departure_time__gt=now.time())

        sort = request.GET.get("sort", "time")
        qs = qs.order_by({"price": "price", "-price": "-price"}.get(sort, "departure_time"))
        return Response(ScheduleSerializer(qs, many=True).data)


class ScheduleDetail(APIView):
    def get(self, request, schedule_id):
        expire_stale_holds()
        s = get_object_or_404(Schedule.objects.select_related("bus", "route"), pk=schedule_id)
        return Response(ScheduleDetailSerializer(s).data)


# ------------------------------------------------------------ booking

class CreateBooking(APIView):
    """Hold seats and create a pending payment. All seats succeed or none do."""

    def post(self, request):
        ser = CreateBookingSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        schedule = data["schedule"]

        departure = timezone.make_aware(datetime.combine(schedule.date, schedule.departure_time))
        if departure <= timezone.now():
            return Response({"error": "This bus has already departed."}, status=400)

        expire_stale_holds()
        try:
            with transaction.atomic():
                # Lock the schedule row so two people cannot grab the same seat at once.
                Schedule.objects.select_for_update().get(pk=schedule.pk)
                taken = set(Booking.objects.filter(schedule=schedule, seat_number__in=data["seats"],
                                                   status__in=Booking.ACTIVE_STATUSES)
                            .values_list("seat_number", flat=True))
                if taken:
                    return Response({"error": f"Sorry, seat {', '.join(sorted(taken))} was just booked by someone else.",
                                     "taken": sorted(taken)}, status=409)
                payment = Payment.objects.create(
                    schedule=schedule,
                    customer_name=data["customer_name"],
                    customer_email=data["customer_email"],
                    phone=data["phone"],
                    amount=schedule.price * len(data["seats"]),
                    currency=settings.CURRENCY,
                    provider=settings.PAYMENT_PROVIDER,
                )
                for seat in data["seats"]:
                    Booking.objects.create(schedule=schedule, payment=payment, seat_number=seat,
                                           customer_name=payment.customer_name,
                                           customer_email=payment.customer_email, phone=payment.phone)
        except IntegrityError:
            return Response({"error": "One of those seats was just taken. Please pick another."}, status=409)

        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


class PaymentDetail(APIView):
    def get(self, request, tran_id):
        expire_stale_holds()
        payment = get_object_or_404(Payment.objects.select_related("schedule__bus", "schedule__route"), tran_id=tran_id)
        payment = payments.stripe_refresh(payment)
        return Response(PaymentSerializer(payment).data)


class StartCheckout(APIView):
    def post(self, request, tran_id):
        expire_stale_holds()
        payment = get_object_or_404(Payment, tran_id=tran_id)
        if payment.status == "Paid":
            return Response({"redirect_url": payments.frontend(f"/confirmation?tran_id={tran_id}")})
        if payment.status != "Pending":
            return Response({"error": "Your seat hold has expired. Please select your seats again."}, status=410)
        try:
            url = payments.start_checkout(payment)
        except payments.GatewayConfigError as e:
            log.error("Checkout misconfigured for %s: %s", tran_id, e)
            return Response({"error": "Online payment isn't set up correctly yet. Please contact support.",
                             "detail": str(e) if settings.DEBUG else None}, status=503)
        except payments.PaymentError as e:
            log.error("Checkout failed for %s: %s", tran_id, e)
            return Response({"error": "The payment gateway didn't respond. Please try again in a moment.",
                             "detail": str(e) if settings.DEBUG else None}, status=502)
        return Response({"redirect_url": url})


class CancelPayment(APIView):
    def post(self, request, tran_id):
        payment = get_object_or_404(Payment, tran_id=tran_id)
        payments.release(payment, "Cancelled")
        return Response({"message": "Your seats have been released."})


class TicketPdf(APIView):
    def get(self, request, tran_id):
        payment = get_object_or_404(Payment, tran_id=tran_id, status="Paid")
        resp = HttpResponse(build_ticket_pdf(payment), content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="Ticket_{tran_id}.pdf"'
        return resp


# --------------------------------------------------------- manage ticket

def _find_booking(pnr, email):
    pnr = (pnr or "").strip().upper()
    email = (email or "").strip()
    if not pnr or not email:
        return None
    return (Booking.objects.select_related("schedule", "bus", "route", "payment")
            .filter(pnr_number=pnr, customer_email__iexact=email).first())


class TicketLookup(APIView):
    throttle_classes = [LookupThrottle]

    def get(self, request):
        b = _find_booking(request.GET.get("pnr"), request.GET.get("email"))
        if not b:
            return Response({"error": "No ticket matches that PNR and email."}, status=404)
        data = BookingSerializer(b).data
        data["tran_id"] = b.payment.tran_id if b.payment and b.status == "Paid" else None
        return Response(data)


class ReturnTicket(APIView):
    throttle_classes = [LookupThrottle]

    def post(self, request):
        b = _find_booking(request.data.get("pnr"), request.data.get("email"))
        if not b:
            return Response({"error": "No ticket matches that PNR and email."}, status=404)
        if b.status != "Paid":
            return Response({"error": f"This ticket is {b.status.lower()} and cannot be returned."}, status=400)
        departure = timezone.make_aware(datetime.combine(b.date, b.departure_time))
        if departure - timezone.now() < timedelta(hours=settings.RETURN_CUTOFF_HOURS):
            return Response({"error": f"Tickets can only be returned at least {settings.RETURN_CUTOFF_HOURS} hours before departure."}, status=400)
        b.status = "Cancelled"
        b.save(update_fields=["status"])
        if b.payment:
            b.payment.note = (b.payment.note + f"\nSeat {b.seat_number} returned {timezone.now():%Y-%m-%d %H:%M}. Refund {b.price} {b.payment.currency}.").strip()
            b.payment.save(update_fields=["note"])
        log.info("Ticket %s returned", b.pnr_number)
        return Response({"message": f"Seat {b.seat_number} has been returned. Your refund of {settings.CURRENCY} {b.price:,} will be processed to your original payment method."})


# ---------------------------------------------------------------- support

class SupportThrottle(AnonRateThrottle):
    rate = "5/hour"


class SupportCreate(APIView):
    """Help page contact form. Saved to the database and emailed to SUPPORT_EMAIL."""
    throttle_classes = [SupportThrottle]

    def post(self, request):
        if request.data.get("website"):  # honeypot field, hidden from humans
            return Response({"message": "Thanks! We'll get back to you soon."}, status=201)
        ser = SupportMessageSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        msg = ser.save()
        msg.emailed = send_support_email(msg)
        msg.save(update_fields=["emailed"])
        return Response({"id": msg.id, "message": "Thanks! Your message has been sent. We usually reply within 24 hours."}, status=201)


def send_support_email(msg):
    body = (
        f"New support message #{msg.id}\n\n"
        f"Name:  {msg.name}\nEmail: {msg.email}\nPhone: {msg.phone or '-'}\n"
        f"Topic: {msg.get_topic_display()}\nPNR:   {msg.pnr or '-'}\n\n{msg.message}\n"
    )
    email = EmailMessage(
        subject=f"[{settings.BRAND_NAME} support] {msg.get_topic_display()} · {msg.name}",
        body=body, from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.SUPPORT_EMAIL], reply_to=[msg.email],
    )
    try:
        email.send(fail_silently=False)
        return True
    except Exception:
        log.exception("Support email #%s failed", msg.id)
        return False


# -------------------------------------------- gateway callbacks (no DRF)

@csrf_exempt
@require_POST
def sslcommerz_success(request):
    tran_id, val_id = request.POST.get("tran_id", ""), request.POST.get("val_id", "")
    try:
        p = payments.sslcommerz_confirm(val_id, tran_id)
        if p.status == "Paid":
            return HttpResponseRedirect(payments.frontend(f"/confirmation?tran_id={tran_id}"))
    except (payments.PaymentError, Payment.DoesNotExist) as e:
        log.error("SSLCommerz success callback rejected for %s: %s", tran_id, e)
    return HttpResponseRedirect(payments.frontend(f"/payment?tran_id={tran_id}&failed=1"))


@csrf_exempt
@require_POST
def sslcommerz_fail(request):
    tran_id = request.POST.get("tran_id", "")
    p = Payment.objects.filter(tran_id=tran_id).first()
    if p:
        payments.release(p, "Failed")
    return HttpResponseRedirect(payments.frontend(f"/payment?tran_id={tran_id}&failed=1"))


@csrf_exempt
@require_POST
def sslcommerz_cancel(request):
    tran_id = request.POST.get("tran_id", "")
    # Keep the hold so the customer can try again before it expires.
    return HttpResponseRedirect(payments.frontend(f"/payment?tran_id={tran_id}&cancelled=1"))


@csrf_exempt
@require_POST
def sslcommerz_ipn(request):
    """Server-to-server notification. Confirms payments even if the browser never returns."""
    tran_id, val_id = request.POST.get("tran_id", ""), request.POST.get("val_id", "")
    if request.POST.get("status") in ("VALID", "VALIDATED") and val_id:
        try:
            payments.sslcommerz_confirm(val_id, tran_id)
        except (payments.PaymentError, Payment.DoesNotExist) as e:
            log.error("SSLCommerz IPN rejected for %s: %s", tran_id, e)
            return HttpResponse(status=400)
    return HttpResponse("OK")


@csrf_exempt
@require_POST
def stripe_webhook(request):
    try:
        event = payments.stripe_verify_webhook(request.body, request.headers.get("Stripe-Signature", ""))
    except payments.PaymentError as e:
        log.warning("Stripe webhook rejected: %s", e)
        return HttpResponse(status=400)
    obj = event.get("data", {}).get("object", {})
    tran_id = obj.get("client_reference_id")
    p = Payment.objects.filter(tran_id=tran_id).first() if tran_id else None
    if p:
        if event["type"] in ("checkout.session.completed", "checkout.session.async_payment_succeeded") \
                and obj.get("payment_status") == "paid":
            payments.mark_paid(p.pk, provider_ref=obj["id"], amount=obj["amount_total"] / 100, currency=obj.get("currency"))
        elif event["type"] in ("checkout.session.expired", "checkout.session.async_payment_failed"):
            payments.release(p, "Expired" if event["type"].endswith("expired") else "Failed")
    return HttpResponse("OK")
