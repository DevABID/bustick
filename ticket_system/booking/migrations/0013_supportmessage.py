from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("booking", "0012_payments_and_seat_holds"),
    ]

    operations = [
        migrations.CreateModel(
            name="SupportMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("email", models.EmailField(max_length=254)),
                ("phone", models.CharField(blank=True, max_length=20)),
                ("topic", models.CharField(choices=[("booking", "Booking problem"), ("payment", "Payment or refund"), ("return", "Ticket return"), ("other", "Something else")], default="other", max_length=20)),
                ("pnr", models.CharField(blank=True, max_length=10)),
                ("message", models.TextField(max_length=3000)),
                ("status", models.CharField(choices=[("Open", "Open"), ("Resolved", "Resolved")], default="Open", max_length=10)),
                ("emailed", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
