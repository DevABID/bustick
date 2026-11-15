"""
Keep buses on sale: repeat every existing daily departure for the next N days.

    python manage.py extend_schedules            # next 30 days
    python manage.py extend_schedules --days 60

A "departure" is a bus + route + departure time. The newest schedule of each
departure is copied (price, AC type, seat type) to every day that doesn't have it yet.
Run it once a day (cron / Task Scheduler) and schedules never run out.
Delete a departure's future schedules in the admin to stop repeating it.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from booking.models import Schedule


class Command(BaseCommand):
    help = "Repeat existing daily departures for the next N days."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=30)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, days, dry_run, **opts):
        today = timezone.localdate()
        latest = {}
        for s in Schedule.objects.order_by("date"):
            latest[(s.bus_id, s.route_id, s.departure_time)] = s  # newest wins

        created = 0
        for (bus_id, route_id, dep), template in latest.items():
            existing = set(Schedule.objects.filter(bus_id=bus_id, route_id=route_id, departure_time=dep,
                                                   date__gte=today).values_list("date", flat=True))
            for d in range(days):
                day = today + timedelta(days=d)
                if day in existing:
                    continue
                if not dry_run:
                    Schedule.objects.create(bus_id=bus_id, route_id=route_id, departure_time=dep, date=day,
                                            price=template.price, bus_type=template.bus_type,
                                            seat_type=template.seat_type)
                created += 1
        verb = "Would create" if dry_run else "Created"
        self.stdout.write(self.style.SUCCESS(f"{verb} {created} schedules from {len(latest)} departures."))
