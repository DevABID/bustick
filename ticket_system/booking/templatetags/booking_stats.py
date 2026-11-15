from datetime import timedelta

from django import template
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from booking.models import Booking, Payment, Schedule

register = template.Library()


@register.simple_tag
def booking_stats():
    today = timezone.localdate()
    paid = Payment.objects.filter(status="Paid")
    week_start = today - timedelta(days=6)
    by_day = dict(
        paid.filter(paid_at__date__gte=week_start)
        .annotate(day=TruncDate("paid_at")).values("day")
        .annotate(total=Sum("amount")).values_list("day", "total")
    )
    week = [{"day": week_start + timedelta(days=i), "total": by_day.get(week_start + timedelta(days=i)) or 0} for i in range(7)]
    peak = max([d["total"] for d in week] + [1])
    for d in week:
        d["pct"] = round(d["total"] * 100 / peak)

    top_routes = (Booking.objects.filter(status="Paid").values("route__from_city", "route__to_city")
                  .annotate(n=Count("id")).order_by("-n")[:5])
    return {
        "revenue_today": paid.filter(paid_at__date=today).aggregate(s=Sum("amount"))["s"] or 0,
        "revenue_total": paid.aggregate(s=Sum("amount"))["s"] or 0,
        "seats_today": Booking.objects.filter(status="Paid", payment__paid_at__date=today).count(),
        "trips_today": Schedule.objects.filter(date=today).count(),
        "needs_action": Payment.objects.exclude(note="").count(),
        "week": week,
        "top_routes": top_routes,
        "recent": Payment.objects.select_related("schedule__route").order_by("-created_at")[:8],
    }
