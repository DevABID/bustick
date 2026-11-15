import secrets
import string
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

PNR_ALPHABET = string.ascii_uppercase + string.digits


def generate_pnr():
    return "".join(secrets.choice(PNR_ALPHABET) for _ in range(8))


def generate_tran_id():
    return "BT" + uuid.uuid4().hex[:18].upper()


SEAT_LAYOUTS = {
    # None = aisle. Keep in sync with ticket-ui/src/seatLayouts.js
    "BUSINESS": [
        "A1", None, "A2", "A3",
        "B1", None, "B2", "B3",
        "C1", None, "C2", "C3",
        "D1", None, "D2", "D3",
        "E1", None, "E2", "E3",
        "F1", None, "F2", "F3",
        "G1", None, "G2", "G3",
        "H1", None, "H2", "H3",
    ],
    # 2 + 2 per row: A1 A2 | A3 A4 ... J1 J2 | J3 J4
    "ECONOMY": [
        s for row in "ABCDEFGHIJ" for s in (f"{row}1", f"{row}2", None, f"{row}3", f"{row}4")
    ],
}


class Route(models.Model):
    from_city = models.CharField(max_length=100)
    to_city = models.CharField(max_length=100)

    class Meta:
        ordering = ["from_city", "to_city"]

    def __str__(self):
        return f"{self.from_city} to {self.to_city}"


class Bus(models.Model):
    name = models.CharField(max_length=100)
    type = models.CharField(max_length=50, default="AC")
    seat_layout = models.CharField(max_length=20, default="ECONOMY")

    class Meta:
        verbose_name_plural = "buses"

    def __str__(self):
        return self.name


class Schedule(models.Model):
    TYPE_CHOICES = [("AC", "AC"), ("Non-AC", "Non-AC")]
    SEAT_TYPE_CHOICES = [("ECONOMY", "Economy (40 seats, 2+2)"), ("BUSINESS", "Business (24 seats, 1+2)")]

    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    route = models.ForeignKey(Route, on_delete=models.CASCADE)
    date = models.DateField()
    departure_time = models.TimeField()
    price = models.IntegerField()
    bus_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default="AC")
    seat_type = models.CharField(max_length=20, choices=SEAT_TYPE_CHOICES, default="ECONOMY")

    class Meta:
        ordering = ["date", "departure_time"]

    def __str__(self):
        return f"{self.bus.name} · {self.route} · {self.date} {self.departure_time:%H:%M}"

    @property
    def seats(self):
        return [s for s in SEAT_LAYOUTS.get(self.seat_type, SEAT_LAYOUTS["ECONOMY"]) if s]


class Payment(models.Model):
    """One checkout covering one or more seats."""

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Paid", "Paid"),
        ("Failed", "Failed"),
        ("Cancelled", "Cancelled"),
        ("Expired", "Expired"),
    ]
    PROVIDER_CHOICES = [("sslcommerz", "SSLCommerz"), ("stripe", "Stripe"), ("demo", "Demo")]

    tran_id = models.CharField(max_length=40, unique=True, default=generate_tran_id, editable=False)
    schedule = models.ForeignKey(Schedule, on_delete=models.PROTECT, related_name="payments")
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField()
    phone = models.CharField(max_length=20)
    amount = models.IntegerField()
    currency = models.CharField(max_length=3, default="BDT")
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    provider_ref = models.CharField(max_length=255, blank=True, help_text="Gateway session / validation id")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    hold_expires_at = models.DateTimeField()
    ticket_emailed = models.BooleanField(default=False)
    note = models.TextField(blank=True, help_text="Problems that need staff action, e.g. refunds")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tran_id} · {self.amount} {self.currency} · {self.status}"

    def save(self, *args, **kwargs):
        if not self.hold_expires_at:
            minutes = getattr(settings, "SEAT_HOLD_MINUTES", 10)
            self.hold_expires_at = timezone.now() + timedelta(minutes=minutes)
        super().save(*args, **kwargs)

    @property
    def hold_expired(self):
        return self.status == "Pending" and timezone.now() >= self.hold_expires_at


class Booking(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Paid", "Paid"),
        ("Cancelled", "Cancelled"),
        ("Expired", "Expired"),
    ]
    ACTIVE_STATUSES = ("Pending", "Paid")

    schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE, related_name="bookings")
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name="bookings")
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField()
    phone = models.CharField(max_length=20)
    seat_number = models.CharField(max_length=5)
    pnr_number = models.CharField(max_length=10, unique=True, editable=False, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    # Snapshot of the trip at booking time
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, null=True, blank=True)
    route = models.ForeignKey(Route, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    departure_time = models.TimeField(null=True, blank=True)
    price = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # A seat can be re-sold after a booking is cancelled or expires.
            models.UniqueConstraint(
                fields=["schedule", "seat_number"],
                condition=Q(status__in=["Pending", "Paid"]),
                name="unique_active_seat_per_schedule",
            )
        ]

    def save(self, *args, **kwargs):
        if not self.pnr_number:
            pnr = generate_pnr()
            while Booking.objects.filter(pnr_number=pnr).exists():
                pnr = generate_pnr()
            self.pnr_number = pnr
        if self.schedule_id and not self.price:
            s = self.schedule
            self.bus, self.route, self.date = s.bus, s.route, s.date
            self.departure_time, self.price = s.departure_time, s.price
        super().save(*args, **kwargs)

    @property
    def bus_name(self):
        return self.bus.name if self.bus else ""

    @property
    def bus_type(self):
        return self.schedule.bus_type if self.schedule_id else ""

    @property
    def route_name(self):
        return str(self.route) if self.route else ""

    def __str__(self):
        return f"{self.customer_name} ({self.pnr_number}) - {self.seat_number} [{self.status}]"


def expire_stale_holds():
    """Release seats whose payment window has passed. Called before seat checks."""
    now = timezone.now()
    stale = Payment.objects.filter(status="Pending", hold_expires_at__lte=now)
    ids = list(stale.values_list("id", flat=True))
    if ids:
        Booking.objects.filter(payment_id__in=ids, status="Pending").update(status="Expired")
        Payment.objects.filter(id__in=ids).update(status="Expired")
    # Legacy pending bookings created without a payment
    Booking.objects.filter(
        payment__isnull=True, status="Pending",
        created_at__lte=now - timedelta(minutes=getattr(settings, "SEAT_HOLD_MINUTES", 10)),
    ).update(status="Expired")


class SupportMessage(models.Model):
    TOPIC_CHOICES = [
        ("booking", "Booking problem"),
        ("payment", "Payment or refund"),
        ("return", "Ticket return"),
        ("other", "Something else"),
    ]
    STATUS_CHOICES = [("Open", "Open"), ("Resolved", "Resolved")]

    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    topic = models.CharField(max_length=20, choices=TOPIC_CHOICES, default="other")
    pnr = models.CharField(max_length=10, blank=True)
    message = models.TextField(max_length=3000)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Open")
    emailed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.pk} {self.get_topic_display()} from {self.name}"
