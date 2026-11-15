import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models

import booking.models


def normalize_seat_types(apps, schema_editor):
    """Old data mixed ECONOMY40 / ECONOMY_40 / BUSINESS_26; the UI only knows ECONOMY and BUSINESS."""
    Schedule = apps.get_model("booking", "Schedule")
    Bus = apps.get_model("booking", "Bus")
    for model, field in ((Schedule, "seat_type"), (Bus, "seat_layout")):
        for obj in model.objects.all():
            value = (getattr(obj, field) or "").upper()
            setattr(obj, field, "BUSINESS" if value.startswith("BUSINESS") else "ECONOMY")
            obj.save(update_fields=[field])


class Migration(migrations.Migration):

    dependencies = [
        ("booking", "0011_booking_status"),
    ]

    operations = [
        migrations.AlterModelOptions(name="route", options={"ordering": ["from_city", "to_city"]}),
        migrations.AlterModelOptions(name="bus", options={"verbose_name_plural": "buses"}),
        migrations.AlterModelOptions(name="schedule", options={"ordering": ["date", "departure_time"]}),
        migrations.AlterModelOptions(name="booking", options={"ordering": ["-created_at"]}),
        migrations.AlterField(
            model_name="bus",
            name="seat_layout",
            field=models.CharField(default="ECONOMY", max_length=20),
        ),
        migrations.AlterField(
            model_name="schedule",
            name="seat_type",
            field=models.CharField(
                choices=[("ECONOMY", "Economy (40 seats, 2+2)"), ("BUSINESS", "Business (24 seats, 1+2)")],
                default="ECONOMY",
                max_length=20,
            ),
        ),
        migrations.RunPython(normalize_seat_types, migrations.RunPython.noop),
        migrations.CreateModel(
            name="Payment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tran_id", models.CharField(default=booking.models.generate_tran_id, editable=False, max_length=40, unique=True)),
                ("customer_name", models.CharField(max_length=100)),
                ("customer_email", models.EmailField(max_length=254)),
                ("phone", models.CharField(max_length=20)),
                ("amount", models.IntegerField()),
                ("currency", models.CharField(default="BDT", max_length=3)),
                ("provider", models.CharField(choices=[("sslcommerz", "SSLCommerz"), ("stripe", "Stripe"), ("demo", "Demo")], max_length=20)),
                ("provider_ref", models.CharField(blank=True, help_text="Gateway session / validation id", max_length=255)),
                ("status", models.CharField(choices=[("Pending", "Pending"), ("Paid", "Paid"), ("Failed", "Failed"), ("Cancelled", "Cancelled"), ("Expired", "Expired")], default="Pending", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("hold_expires_at", models.DateTimeField()),
                ("ticket_emailed", models.BooleanField(default=False)),
                ("note", models.TextField(blank=True, help_text="Problems that need staff action, e.g. refunds")),
                ("schedule", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="payments", to="booking.schedule")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddField(
            model_name="booking",
            name="payment",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="bookings", to="booking.payment"),
        ),
        migrations.AddField(
            model_name="booking",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
        migrations.AlterField(
            model_name="booking",
            name="schedule",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bookings", to="booking.schedule"),
        ),
        migrations.AlterField(
            model_name="booking",
            name="status",
            field=models.CharField(choices=[("Pending", "Pending"), ("Paid", "Paid"), ("Cancelled", "Cancelled"), ("Expired", "Expired")], default="Pending", max_length=10),
        ),
        migrations.AlterUniqueTogether(name="booking", unique_together=set()),
        migrations.AddConstraint(
            model_name="booking",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status__in", ["Pending", "Paid"])),
                fields=("schedule", "seat_number"),
                name="unique_active_seat_per_schedule",
            ),
        ),
    ]
