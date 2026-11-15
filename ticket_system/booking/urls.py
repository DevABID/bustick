from django.urls import path

from . import views

urlpatterns = [
    # Search
    path("routes/", views.RouteList.as_view(), name="route-list"),
    path("schedules/", views.ScheduleSearch.as_view(), name="schedule-search"),
    path("schedules/next-dates/", views.NextDates.as_view(), name="schedule-next-dates"),
    path("schedules/<int:schedule_id>/", views.ScheduleDetail.as_view(), name="schedule-detail"),

    # Booking + payment
    path("bookings/", views.CreateBooking.as_view(), name="create-booking"),
    path("payments/<str:tran_id>/", views.PaymentDetail.as_view(), name="payment-detail"),
    path("payments/<str:tran_id>/checkout/", views.StartCheckout.as_view(), name="payment-checkout"),
    path("payments/<str:tran_id>/cancel/", views.CancelPayment.as_view(), name="payment-cancel"),
    path("payments/<str:tran_id>/ticket.pdf", views.TicketPdf.as_view(), name="ticket-pdf"),

    # Gateway callbacks (configure these URLs in the gateway dashboards)
    path("gateway/sslcommerz/success/", views.sslcommerz_success, name="sslcommerz-success"),
    path("gateway/sslcommerz/fail/", views.sslcommerz_fail, name="sslcommerz-fail"),
    path("gateway/sslcommerz/cancel/", views.sslcommerz_cancel, name="sslcommerz-cancel"),
    path("gateway/sslcommerz/ipn/", views.sslcommerz_ipn, name="sslcommerz-ipn"),
    path("gateway/stripe/webhook/", views.stripe_webhook, name="stripe-webhook"),

    # Help page contact form
    path("support/", views.SupportCreate.as_view(), name="support"),

    # Manage ticket
    path("tickets/lookup/", views.TicketLookup.as_view(), name="ticket-lookup"),
    path("tickets/return/", views.ReturnTicket.as_view(), name="ticket-return"),
]
