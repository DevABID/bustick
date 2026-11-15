"""E-ticket PDF and confirmation email. Built only from database records."""

import io
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

log = logging.getLogger("booking")

INK = colors.HexColor("#0F172A")
MUTED = colors.HexColor("#64748B")
BRAND = colors.HexColor("#16A34A")
LINE = colors.HexColor("#E2E8F0")
SOFT = colors.HexColor("#F1F5F9")


def money(amount, currency=None):
    return f"{currency or settings.CURRENCY} {amount:,}"


def fmt_time(t):
    return t.strftime("%I:%M %p").lstrip("0") if t else ""


def fmt_date(d):
    return d.strftime("%a, %d %b %Y") if d else ""


def build_ticket_pdf(payment):
    bookings = list(payment.bookings.filter(status="Paid").order_by("seat_number"))
    s = payment.schedule
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    x0, x1 = 20 * mm, W - 20 * mm

    # Header band
    c.setFillColor(INK)
    c.rect(0, H - 42 * mm, W, 42 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(x0, H - 22 * mm, settings.BRAND_NAME)
    c.setFont("Helvetica", 11)
    c.drawString(x0, H - 30 * mm, "E-ticket · Please show this at the counter 15 minutes before departure")
    c.setFillColor(BRAND)
    c.roundRect(x1 - 32 * mm, H - 27 * mm, 32 * mm, 10 * mm, 5 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(x1 - 16 * mm, H - 23.5 * mm, "PAID")

    y = H - 60 * mm
    # Route
    c.setFillColor(MUTED); c.setFont("Helvetica-Bold", 8)
    c.drawString(x0, y + 8 * mm, "FROM")
    c.drawString(W / 2 + 10 * mm, y + 8 * mm, "TO")
    c.setFillColor(INK); c.setFont("Helvetica-Bold", 22)
    c.drawString(x0, y, s.route.from_city)
    c.drawString(W / 2 + 10 * mm, y, s.route.to_city)
    c.setStrokeColor(LINE); c.setLineWidth(1)
    c.line(x0 + 62 * mm, y + 3 * mm, W / 2 + 4 * mm, y + 3 * mm)

    # Trip details grid
    y -= 22 * mm
    cells = [
        ("DATE", fmt_date(s.date)),
        ("DEPARTURE", fmt_time(s.departure_time)),
        ("BUS", s.bus.name),
        ("CLASS", f"{s.bus_type} · {s.get_seat_type_display().split(' (')[0]}"),
    ]
    cw = (x1 - x0) / 4
    for i, (label, value) in enumerate(cells):
        cx = x0 + i * cw
        c.setFillColor(MUTED); c.setFont("Helvetica-Bold", 8); c.drawString(cx, y + 6 * mm, label)
        c.setFillColor(INK); c.setFont("Helvetica-Bold", 11); c.drawString(cx, y, value[:26])

    # Passenger
    y -= 20 * mm
    c.setFillColor(SOFT); c.roundRect(x0, y - 8 * mm, x1 - x0, 22 * mm, 3 * mm, stroke=0, fill=1)
    c.setFillColor(MUTED); c.setFont("Helvetica-Bold", 8)
    c.drawString(x0 + 6 * mm, y + 7 * mm, "PASSENGER")
    c.drawString(x0 + 90 * mm, y + 7 * mm, "CONTACT")
    c.setFillColor(INK); c.setFont("Helvetica-Bold", 13)
    c.drawString(x0 + 6 * mm, y, payment.customer_name)
    c.setFont("Helvetica", 11)
    c.drawString(x0 + 90 * mm, y, payment.phone)
    c.drawString(x0 + 90 * mm, y - 5 * mm, payment.customer_email)

    # Seats table
    y -= 26 * mm
    c.setFillColor(MUTED); c.setFont("Helvetica-Bold", 8)
    c.drawString(x0, y, "SEAT"); c.drawString(x0 + 40 * mm, y, "PNR"); c.drawRightString(x1, y, "FARE")
    c.setStrokeColor(LINE); c.line(x0, y - 3 * mm, x1, y - 3 * mm)
    for b in bookings:
        y -= 10 * mm
        c.setFillColor(INK); c.setFont("Helvetica-Bold", 14); c.drawString(x0, y, b.seat_number)
        c.setFont("Courier-Bold", 13); c.drawString(x0 + 40 * mm, y, b.pnr_number)
        c.setFont("Helvetica", 12); c.drawRightString(x1, y, money(b.price, payment.currency))
        c.line(x0, y - 4 * mm, x1, y - 4 * mm)
    y -= 12 * mm
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x0, y, "Total paid")
    c.setFillColor(BRAND); c.drawRightString(x1, y, money(sum(b.price for b in bookings), payment.currency))

    # Footer
    c.setFillColor(MUTED); c.setFont("Helvetica", 9)
    c.drawString(x0, 20 * mm, f"Booking reference: {payment.tran_id}")
    c.drawString(x0, 15 * mm, f"Tickets can be returned online up to {settings.RETURN_CUTOFF_HOURS} hours before departure.")
    c.showPage(); c.save()
    return buf.getvalue()


def send_ticket_email(payment):
    if payment.status != "Paid" or payment.ticket_emailed:
        return False
    s = payment.schedule
    seats = ", ".join(payment.bookings.filter(status="Paid").values_list("seat_number", flat=True))
    pnrs = ", ".join(payment.bookings.filter(status="Paid").values_list("pnr_number", flat=True))
    subject = f"Your {settings.BRAND_NAME} ticket: {s.route} on {fmt_date(s.date)}"
    text = (
        f"Hi {payment.customer_name},\n\n"
        f"Your booking is confirmed.\n\n"
        f"Route: {s.route}\nDate: {fmt_date(s.date)} at {fmt_time(s.departure_time)}\n"
        f"Bus: {s.bus.name}\nSeats: {seats}\nPNR: {pnrs}\n"
        f"Total paid: {money(payment.amount, payment.currency)}\n\n"
        f"Your e-ticket is attached. Have a good trip!\n{settings.BRAND_NAME}"
    )
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;color:#0F172A">
      <div style="background:#0F172A;color:#fff;padding:20px 24px;border-radius:12px 12px 0 0">
        <b style="font-size:20px">{escape(settings.BRAND_NAME)}</b>
        <div style="color:#86EFAC;margin-top:4px">Booking confirmed</div>
      </div>
      <div style="border:1px solid #E2E8F0;border-top:0;padding:24px;border-radius:0 0 12px 12px">
        <p>Hi {escape(payment.customer_name)}, your seats are booked.</p>
        <p style="font-size:18px;margin:16px 0"><b>{escape(str(s.route))}</b><br>
        {fmt_date(s.date)} · {fmt_time(s.departure_time)} · {escape(s.bus.name)}</p>
        <p>Seats: <b>{escape(seats)}</b><br>PNR: <b style="font-family:monospace">{escape(pnrs)}</b><br>
        Total paid: <b>{money(payment.amount, payment.currency)}</b></p>
        <p style="color:#64748B;font-size:13px">Your e-ticket PDF is attached.</p>
      </div>
    </div>"""
    msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [payment.customer_email])
    msg.attach_alternative(html, "text/html")
    msg.attach(f"Ticket_{payment.tran_id}.pdf", build_ticket_pdf(payment), "application/pdf")
    try:
        msg.send(fail_silently=False)
    except Exception:
        log.exception("Ticket email failed for %s", payment.tran_id)
        return False
    type(payment).objects.filter(pk=payment.pk).update(ticket_emailed=True)
    return True
