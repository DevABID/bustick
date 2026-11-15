"""python manage.py seed_demo  → routes, buses and 14 days of schedules for demos."""

from datetime import time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from booking.models import Bus, Route, Schedule

ROUTES = [
    ("Dhaka", "Cox's Bazar", 1400), ("Dhaka", "Chattogram", 900), ("Dhaka", "Sylhet", 800),
    ("Dhaka", "Rajshahi", 750), ("Dhaka", "Khulna", 850), ("Dhaka", "Rangpur", 800),
    ("Dhaka", "Barishal", 700), ("Chattogram", "Cox's Bazar", 500), ("Sylhet", "Dhaka", 800),
    ("Cox's Bazar", "Dhaka", 1400),
]
BUSES = [
    ("Green Line Paribahan", "AC", "BUSINESS"), ("Hanif Enterprise", "Non-AC", "ECONOMY"),
    ("Shyamoli Paribahan", "AC", "ECONOMY"), ("Ena Transport", "AC", "BUSINESS"),
    ("S.R Travels", "Non-AC", "ECONOMY"), ("Shohagh Paribahan", "AC", "BUSINESS"),
]
DEPARTURES = [time(7, 30), time(10, 0), time(14, 30), time(21, 0), time(23, 15)]


class Command(BaseCommand):
    help = "Create demo routes, buses and schedules for the next 14 days."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=14)

    def handle(self, *args, days, **opts):
        buses = [Bus.objects.get_or_create(name=n, defaults={"type": t, "seat_layout": l})[0] for n, t, l in BUSES]
        today = timezone.localdate()
        created = 0
        for i, (a, b, base) in enumerate(ROUTES):
            route, _ = Route.objects.get_or_create(from_city=a, to_city=b)
            for d in range(days):
                day = today + timedelta(days=d)
                for j, dep in enumerate(DEPARTURES[: 3 + (i % 3)]):
                    bus = buses[(i + j) % len(buses)]
                    premium = 1.4 if bus.seat_layout == "BUSINESS" else 1.0
                    ac = 1.0 if bus.type == "AC" else 0.8
                    _, new = Schedule.objects.get_or_create(
                        bus=bus, route=route, date=day, departure_time=dep,
                        defaults={"price": int(round(base * premium * ac, -1)),
                                  "bus_type": bus.type, "seat_type": bus.seat_layout},
                    )
                    created += new
        self.stdout.write(self.style.SUCCESS(f"Seeded {created} schedules across {len(ROUTES)} routes."))
