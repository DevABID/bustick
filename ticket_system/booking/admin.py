from django.contrib import admin, messages
from django.db.models import Count, Q

from .models import Booking, Bus, Payment, Route, Schedule, SupportMessage
from .tickets import send_ticket_email

admin.site.site_header = "BusTick Admin"
admin.site.site_title = "BusTick Admin"
admin.site.index_title = "Dashboard"


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("from_city", "to_city")
    search_fields = ("from_city", "to_city")


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "seat_layout")
    search_fields = ("name",)


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ("bus", "route", "date", "departure_time", "bus_type", "seat_type", "price", "seats_sold")
    list_filter = ("date", "bus_type", "seat_type", "route")
    search_fields = ("bus__name", "route__from_city", "route__to_city")
    date_hierarchy = "date"
    list_select_related = ("bus", "route")

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _sold=Count("bookings", filter=Q(bookings__status="Paid")))

    @admin.display(description="Seats sold", ordering="_sold")
    def seats_sold(self, obj):
        return f"{obj._sold} / {len(obj.seats)}"


class BookingInline(admin.TabularInline):
    model = Booking
    extra = 0
    can_delete = False
    fields = ("seat_number", "pnr_number", "status", "price")
    readonly_fields = fields


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("tran_id", "customer_name", "schedule", "amount", "provider", "status", "created_at", "needs_action")
    list_filter = ("status", "provider", "created_at")
    search_fields = ("tran_id", "customer_name", "customer_email", "phone", "bookings__pnr_number")
    readonly_fields = ("tran_id", "provider", "provider_ref", "amount", "currency", "created_at", "paid_at",
                       "hold_expires_at", "ticket_emailed")
    inlines = [BookingInline]
    actions = ["resend_ticket"]
    list_select_related = ("schedule__bus", "schedule__route")

    @admin.display(boolean=True, description="Needs action")
    def needs_action(self, obj):
        return bool(obj.note)

    @admin.action(description="Resend ticket email")
    def resend_ticket(self, request, queryset):
        sent = 0
        for p in queryset.filter(status="Paid"):
            Payment.objects.filter(pk=p.pk).update(ticket_emailed=False)
            p.ticket_emailed = False
            sent += send_ticket_email(p)
        self.message_user(request, f"Sent {sent} ticket email(s).", messages.SUCCESS)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("pnr_number", "customer_name", "phone", "route", "date", "departure_time", "seat_number", "price", "status")
    list_filter = ("status", "date", "route")
    search_fields = ("pnr_number", "customer_name", "customer_email", "phone")
    readonly_fields = ("pnr_number", "payment", "created_at")
    date_hierarchy = "date"
    list_select_related = ("route",)
    actions = ["cancel_bookings"]

    @admin.action(description="Cancel selected bookings (frees the seats)")
    def cancel_bookings(self, request, queryset):
        n = queryset.exclude(status="Cancelled").update(status="Cancelled")
        self.message_user(request, f"Cancelled {n} booking(s). Refund paid ones from the gateway dashboard.")


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "topic", "pnr", "status", "emailed", "created_at")
    list_filter = ("status", "topic", "created_at")
    search_fields = ("name", "email", "pnr", "message")
    readonly_fields = ("name", "email", "phone", "topic", "pnr", "message", "emailed", "created_at")
    list_editable = ("status",)
