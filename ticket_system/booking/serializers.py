import re

from django.conf import settings
from rest_framework import serializers

from .models import SEAT_LAYOUTS, Booking, Payment, Route, Schedule, SupportMessage


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ["id", "from_city", "to_city"]


class ScheduleSerializer(serializers.ModelSerializer):
    bus_name = serializers.CharField(source="bus.name", read_only=True)
    from_city = serializers.CharField(source="route.from_city", read_only=True)
    to_city = serializers.CharField(source="route.to_city", read_only=True)
    seats_total = serializers.SerializerMethodField()
    seats_left = serializers.SerializerMethodField()

    class Meta:
        model = Schedule
        fields = ["id", "bus_name", "bus_type", "from_city", "to_city", "date", "departure_time",
                  "price", "seat_type", "seats_total", "seats_left"]

    def get_seats_total(self, obj):
        return len(obj.seats)

    def get_seats_left(self, obj):
        taken = getattr(obj, "taken_count", None)
        if taken is None:
            taken = obj.bookings.filter(status__in=Booking.ACTIVE_STATUSES).count()
        return max(len(obj.seats) - taken, 0)


class ScheduleDetailSerializer(ScheduleSerializer):
    layout = serializers.SerializerMethodField()
    booked_seats = serializers.SerializerMethodField()

    class Meta(ScheduleSerializer.Meta):
        fields = ScheduleSerializer.Meta.fields + ["layout", "booked_seats"]

    def get_layout(self, obj):
        return SEAT_LAYOUTS.get(obj.seat_type, SEAT_LAYOUTS["ECONOMY"])

    def get_booked_seats(self, obj):
        return list(obj.bookings.filter(status__in=Booking.ACTIVE_STATUSES).values_list("seat_number", flat=True))


class CreateBookingSerializer(serializers.Serializer):
    schedule = serializers.PrimaryKeyRelatedField(queryset=Schedule.objects.select_related("bus", "route"))
    seats = serializers.ListField(child=serializers.CharField(max_length=5), min_length=1)
    customer_name = serializers.CharField(max_length=100, trim_whitespace=True)
    customer_email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)

    def validate_customer_name(self, v):
        if len(v) < 2:
            raise serializers.ValidationError("Please enter the passenger's full name.")
        return v

    def validate_phone(self, v):
        digits = re.sub(r"[^\d+]", "", v)
        if not re.fullmatch(r"\+?\d{10,15}", digits):
            raise serializers.ValidationError("Enter a valid phone number, e.g. 01712345678.")
        return digits

    def validate(self, data):
        seats = [s.upper() for s in data["seats"]]
        if len(set(seats)) != len(seats):
            raise serializers.ValidationError({"seats": "Each seat can only be selected once."})
        if len(seats) > settings.MAX_SEATS_PER_BOOKING:
            raise serializers.ValidationError({"seats": f"You can book up to {settings.MAX_SEATS_PER_BOOKING} seats at a time."})
        valid = set(data["schedule"].seats)
        bad = [s for s in seats if s not in valid]
        if bad:
            raise serializers.ValidationError({"seats": f"Unknown seat(s): {', '.join(bad)}"})
        data["seats"] = seats
        return data


class BookingSerializer(serializers.ModelSerializer):
    bus_type = serializers.CharField(read_only=True)
    bus_name = serializers.CharField(read_only=True)
    route_name = serializers.CharField(read_only=True)
    from_city = serializers.CharField(source="route.from_city", read_only=True, default="")
    to_city = serializers.CharField(source="route.to_city", read_only=True, default="")

    class Meta:
        model = Booking
        fields = ["id", "pnr_number", "seat_number", "status", "customer_name", "customer_email", "phone",
                  "bus_name", "bus_type", "route_name", "from_city", "to_city", "date", "departure_time", "price"]


class PaymentSerializer(serializers.ModelSerializer):
    bookings = BookingSerializer(many=True, read_only=True)
    schedule = ScheduleSerializer(read_only=True)
    seconds_left = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = ["tran_id", "status", "provider", "amount", "currency", "customer_name", "customer_email",
                  "phone", "created_at", "paid_at", "hold_expires_at", "seconds_left", "schedule", "bookings"]

    def get_seconds_left(self, obj):
        from django.utils import timezone
        if obj.status != "Pending":
            return 0
        return max(int((obj.hold_expires_at - timezone.now()).total_seconds()), 0)


class SupportMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportMessage
        fields = ["name", "email", "phone", "topic", "pnr", "message"]

    def validate_name(self, v):
        if len(v.strip()) < 2:
            raise serializers.ValidationError("Please enter your name.")
        return v.strip()

    def validate_message(self, v):
        if len(v.strip()) < 10:
            raise serializers.ValidationError("Please describe the problem in a little more detail.")
        return v.strip()

    def validate_pnr(self, v):
        return v.strip().upper()
